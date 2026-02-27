import os
import tempfile
from typing import Iterable, Iterator, List, Tuple
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pymongo import MongoClient
from core.config import get_config

class RAGChatbot:
    def __init__(self, api_key=None, mongodb_uri=None):
        # 1. API Key Strategy: Argument -> Secrets -> Env
        self.api_key = api_key or get_config("GOOGLE_API_KEY")
                 
        if not self.api_key:
            raise ValueError("API Key is required")

        os.environ["GOOGLE_API_KEY"] = self.api_key

        # Initialize Embeddings (Local -> Free & No Rate Limits)
        # Using a small, fast model ideal for CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 2. MongoDB URI Strategy: Argument -> Secrets -> Env
        self.mongodb_uri = mongodb_uri or get_config("MONGODB_URI")

        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required")
        
        self.client = MongoClient(
            self.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        self.db = self.client["chatbot_db"]
        self.collection = self.db["documents"]
        
        # Initialize Vector Store (Persistent with MongoDB)
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.collection,
            embedding=self.embeddings,
            index_name="vector_index",
            text_key="text",
            embedding_key="embedding"
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 10})

        # Initialize LLM
        llm_kwargs = {
            "model": "gemini-2.5-flash",
            "temperature": 0.3,
            "streaming": True,
        }
        self.llm = ChatGoogleGenerativeAI(**llm_kwargs)

    def process_file_payloads(self, files: Iterable[Tuple[str, bytes]]) -> str:
        """
        Process uploaded file payloads.

        Args:
            files: Iterable of (filename, file_bytes)
        """
        documents = []
        file_count = 0
        for filename, file_bytes in files:
            file_count += 1
            suffix = f".{filename.split('.')[-1]}" if "." in filename else ".txt"
            # Create a temporary file to save the uploaded content
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name

            try:
                if filename.lower().endswith(".pdf"):
                    loader = PyPDFLoader(tmp_file_path)
                    documents.extend(loader.load())
                elif filename.lower().endswith(".txt"):
                    loader = TextLoader(tmp_file_path)
                    documents.extend(loader.load())
            finally:
                os.remove(tmp_file_path)

        if not documents:
            return "No documents to process."

        # Split text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)

        # Add to Vector Store (MongoDB)
        self.vector_store.add_documents(chunks)
        
        return f"Processed and saved {len(chunks)} chunks from {file_count} files to MongoDB Atlas."

    def process_files(self, uploaded_files):
        """
        Backward-compatible wrapper for legacy callers.
        Supports file-like objects with `name`/`filename` and `getvalue()`/`read()`.
        """
        payloads: List[Tuple[str, bytes]] = []
        for uploaded_file in uploaded_files:
            filename = getattr(uploaded_file, "name", None) or getattr(uploaded_file, "filename", None) or "file.txt"
            if hasattr(uploaded_file, "getvalue"):
                file_bytes = uploaded_file.getvalue()
            elif hasattr(uploaded_file, "read"):
                file_bytes = uploaded_file.read()
            else:
                continue
            payloads.append((filename, file_bytes))
        return self.process_file_payloads(payloads)

    def _build_direct_chain(self):
        prompt_template = """You are a helpful and friendly AI assistant.
Give a direct, informative, brief answer by default (about 120-220 words).
Start with the main answer in the first sentence.
Use short bullets only when clearly useful, and keep them minimal.
Only go long if the user explicitly asks for detailed output.

Question: {question}

Answer:"""
        prompt = PromptTemplate(template=prompt_template, input_variables=["question"])
        return prompt | self.llm | StrOutputParser()

    def _build_rag_chain(self):
        prompt_template = """You are an intelligent and helpful AI assistant with expertise in analyzing and explaining information.

Instructions:
1. Synthesize the context into a direct, informative, brief answer.
2. Keep response length around 120-220 words unless the user asks for detailed output.
3. Start with a one-line conclusion first.
4. Do not mention page numbers, metadata, retrieval details, or source counts.
5. Use only the provided context. If missing, say: "I don't have information about that in the available documents."
6. If listing items, keep to the top 3-5 most important points.

Context:
{context}

Question: {question}

Answer:"""
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        return prompt | self.llm | StrOutputParser()

    def get_direct_llm_response(self, query: str) -> str:
        """
        Get a response directly from the LLM without using RAG.
        Use this for greetings, general questions, or when RAG mode is disabled.

        Args:
            query: User's query

        Returns:
            LLM response as string
        """
        chain = self._build_direct_chain()
        response = chain.invoke({"question": query})
        return (response or "").strip()

    def stream_direct_llm_response(self, query: str) -> Iterator[str]:
        """Stream direct LLM response chunks."""
        chain = self._build_direct_chain()
        for chunk in chain.stream({"question": query}):
            if chunk:
                yield chunk

    def has_relevant_context(self, query: str, threshold: float = 0.5) -> bool:
        """
        Check if the RAG system has relevant context for the query.

        Args:
            query: User's query
            threshold: Minimum similarity score (0-1) to consider context relevant

        Returns:
            True if relevant context exists, False otherwise
        """
        if not self.retriever:
            return False

        try:
            # Retrieve documents
            docs = self.retriever.invoke(query)

            # If we have documents, consider it relevant
            # More sophisticated scoring could be added here
            return len(docs) > 0
        except:
            return False

    def get_rag_response_with_fallback(self, query: str):
        """
        Get RAG response, fallback to direct LLM if no relevant context found.

        Args:
            query: User's query

        Returns:
            Tuple of (response, source_type, docs)
            - source_type: "rag" or "rag_fallback"
            - docs: Retrieved documents (empty list for fallback)
        """
        if not self.retriever:
            # No retriever available, use direct LLM
            response = self.get_direct_llm_response(query)
            return response, "rag_fallback", []

        # Retrieve documents
        docs = self.retriever.invoke(query)

        # Check if we have meaningful context
        if not docs or len(docs) == 0:
            # No documents found, fallback to direct LLM
            response = self.get_direct_llm_response(query)
            return response, "rag_fallback", []

        # We have documents, use RAG
        context_text = "\n\n".join([doc.page_content for doc in docs])
        chain = self._build_rag_chain()
        response = chain.invoke({"context": context_text, "question": query})
        response = (response or "").strip()

        # Check if the LLM says it doesn't have information
        no_info_phrases = [
            "don't have information about that",
            "no information about",
            "not found in the documents",
            "documents don't contain"
        ]

        if any(phrase in response.lower() for phrase in no_info_phrases):
            # LLM found no relevant info in context, fallback to direct LLM
            response = self.get_direct_llm_response(query)
            return response, "rag_fallback", []

        return response, "rag", docs

    def stream_rag_response_with_fallback(self, query: str):
        """
        Stream RAG response, fallback to direct LLM stream when no docs are found.
        Returns (stream_iterator, source_type, docs).
        """
        if not self.retriever:
            return self.stream_direct_llm_response(query), "rag_fallback", []

        docs = self.retriever.invoke(query)
        if not docs:
            return self.stream_direct_llm_response(query), "rag_fallback", []

        context_text = "\n\n".join([doc.page_content for doc in docs])
        chain = self._build_rag_chain()
        return chain.stream({"context": context_text, "question": query}), "rag", docs

    def get_response(self, query):
        """
        Legacy method for backward compatibility.
        Use get_rag_response_with_fallback() for new code.
        """
        if not self.retriever:
            return "Please upload documents first to initialize the knowledge base.", []

        # Call the new method
        response, source_type, docs = self.get_rag_response_with_fallback(query)
        return response, docs
    
    def get_document_count(self):
        """Get the number of documents stored in MongoDB"""
        return self.collection.count_documents({})
    
    def clear_all_documents(self):
        """Clear all documents from MongoDB"""
        result = self.collection.delete_many({})
        return f"Deleted {result.deleted_count} documents from MongoDB."
