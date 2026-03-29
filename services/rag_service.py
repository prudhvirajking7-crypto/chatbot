import os
import tempfile
from typing import Iterable, Iterator, List, Tuple
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pymongo import MongoClient
from huggingface_hub import InferenceClient
from core.config import get_config

HF_ROUTER_BASE_URL = "https://router.huggingface.co/v1"
HF_LLM_MODEL       = "meta-llama/Llama-3.3-70B-Instruct:novita"
HF_EMBED_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"


class HFInferenceEmbeddings(Embeddings):
    """LangChain-compatible embeddings using HuggingFace InferenceClient.feature_extraction."""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self._client = InferenceClient(provider="hf-inference", api_key=api_key)

    def _embed(self, text: str) -> list:
        result = self._client.feature_extraction(text, model=self.model)
        # result is a numpy array or nested list; flatten to 1-D list
        import numpy as np
        arr = np.array(result)
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        return arr.tolist()

    def embed_documents(self, texts: List[str]) -> List[list]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list:
        return self._embed(text)


class RAGChatbot:
    def __init__(self, api_key=None, mongodb_uri=None):
        # HuggingFace token for both LLM and embeddings
        self.api_key = api_key or get_config("HF_TOKEN")
        if not self.api_key:
            raise ValueError("HF_TOKEN is required")

        # Embeddings via HF InferenceClient (cloud, no local model)
        embed_model = get_config("EMBEDDING_MODEL", HF_EMBED_MODEL)
        self.embeddings = HFInferenceEmbeddings(model=embed_model, api_key=self.api_key)

        # MongoDB
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

        # Vector Store
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.collection,
            embedding=self.embeddings,
            index_name="vector_index",
            text_key="text",
            embedding_key="embedding",
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})

        # LLM — Llama 3.3 70B via HuggingFace router (OpenAI-compatible)
        llm_model = get_config("LLM_MODEL", HF_LLM_MODEL)
        self.llm = ChatOpenAI(
            model=llm_model,
            base_url=HF_ROUTER_BASE_URL,
            api_key=self.api_key,
            temperature=0.3,
            streaming=True,
        )

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
        prompt_template = """You are an intelligent AI assistant that answers questions strictly based on the provided documentation context.

## Instructions
1. Answer using ONLY information found in the context below.
2. For code samples: use ONLY the syntax, function names, arguments, and patterns shown in the context. Do not invent API calls not present in the context.
3. If the context contains a code example relevant to the question, reproduce or adapt it exactly — do not rewrite it from general knowledge.
4. Cite the relevant part of the context with a brief inline note like: *(from docs: ...)*
5. Start with a one-line conclusion or direct answer.
6. Keep response around 120-220 words unless the user asks for more detail.
7. Do not mention page numbers, metadata, retrieval details, or source counts.
8. If the context does not contain the answer, say exactly: "The uploaded documents do not cover this topic."

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
