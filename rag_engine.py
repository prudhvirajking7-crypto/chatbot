import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pymongo import MongoClient
from config_utils import get_config

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
        
        self.client = MongoClient(self.mongodb_uri)
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
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3
        )

    def process_files(self, uploaded_files):
        documents = []
        for uploaded_file in uploaded_files:
            # Create a temporary file to save the uploaded content
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            try:
                if uploaded_file.name.endswith(".pdf"):
                    loader = PyPDFLoader(tmp_file_path)
                    documents.extend(loader.load())
                elif uploaded_file.name.endswith(".txt"):
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
        
        return f"Processed and saved {len(chunks)} chunks from {len(uploaded_files)} files to MongoDB Atlas."

    def get_direct_llm_response(self, query: str) -> str:
        """
        Get a response directly from the LLM without using RAG.
        Use this for greetings, general questions, or when RAG mode is disabled.

        Args:
            query: User's query

        Returns:
            LLM response as string
        """
        prompt_template = """You are a helpful and friendly AI assistant. Answer the user's question naturally and conversationally.

Question: {question}

Answer:"""

        prompt = PromptTemplate(template=prompt_template, input_variables=["question"])
        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({"question": query})
        return response

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

        prompt_template = """You are an intelligent and helpful AI assistant with expertise in analyzing and explaining information. Your goal is to provide clear, comprehensive, and natural answers based on the context provided.

**Instructions:**
1. **Synthesize Information**: Read through ALL the context carefully and synthesize the information into a coherent, natural response. Don't just copy-paste text.

2. **Natural Conversation**: Write your answer as if you're having a conversation with the user. Be clear, friendly, and informative.

3. **No Technical References**: DO NOT mention page numbers, document sources, or metadata. DO NOT say things like "According to page X" or "The document states". Just provide the information naturally.

4. **Comprehensive & Structured**:
   - If the question requires multiple points, organize them clearly with bullet points or numbered lists
   - Explain concepts thoroughly with context and examples when relevant
   - Connect related ideas to provide a complete understanding

5. **Accuracy First**: Only use information from the provided context. If the context doesn't contain the answer, politely say: "I don't have information about that in the available documents."

6. **Be Specific**: Provide specific details, numbers, names, and examples from the context to make your answer concrete and useful.

Context:
{context}

Question: {question}

Answer (natural and conversational):"""

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        # Generate response using LCEL
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"context": context_text, "question": query})

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
