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

class RAGChatbot:
    def __init__(self, api_key, mongodb_uri=None):
        self.api_key = api_key
        if not api_key:
            raise ValueError("API Key is required")
        
        os.environ["GOOGLE_API_KEY"] = api_key
        
        # Initialize Embeddings (Local -> Free & No Rate Limits)
        # Using a small, fast model ideal for CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # MongoDB Connection
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI")
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
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})

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

    def get_response(self, query):
        if not self.retriever:
            return "Please upload documents first to initialize the knowledge base.", []
        
        # Retrieve documents
        docs = self.retriever.invoke(query)
        context_text = "\n\n".join([doc.page_content for doc in docs])
        
        prompt_template = """You are a helpful and professional AI assistant. Use the provided context to answer the user's question accurately.
        
Guidelines for your response:
1. **BE STRUCTURED**: Use clear headings, bullet points, or numbered lists if the answer has multiple parts or steps.
2. **FORMATTING**: Use **bold** for key terms and *italics* for emphasis where appropriate.
3. **READABILITY**: Break long paragraphs into smaller, digestible chunks.
4. **ACCURACY**: Base your answer ONLY on the provided context. If the answer isn't in the context, politely state that you can't find that information in the documents.
5. **TONE**: Maintain a helpful, clear, and professional tone.

Context:
{context}

Question: {question}

Helpful Structured Answer:"""
        
        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        # Generate response using LCEL or direct invocation
        chain = prompt | self.llm | StrOutputParser()
        
        response = chain.invoke({"context": context_text, "question": query})
        
        return response, docs
    
    def get_document_count(self):
        """Get the number of documents stored in MongoDB"""
        return self.collection.count_documents({})
    
    def clear_all_documents(self):
        """Clear all documents from MongoDB"""
        result = self.collection.delete_many({})
        return f"Deleted {result.deleted_count} documents from MongoDB."
