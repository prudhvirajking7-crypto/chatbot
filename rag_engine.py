import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

class RAGChatbot:
    def __init__(self, api_key):
        self.api_key = api_key
        if not api_key:
            raise ValueError("API Key is required")
        
        os.environ["GOOGLE_API_KEY"] = api_key
        
        # Initialize Embeddings (Local -> Free & No Rate Limits)
        # Using a small, fast model ideal for CPU
        # Initialize Embeddings (Local -> Free & No Rate Limits)
        # Using a small, fast model ideal for CPU
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Persistence Directory
        self.persist_directory = "chroma_db"
        
        # Initialize Vector Store (Persistent)
        self.vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
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

        # Add to Vector Store
        self.vector_store.add_documents(chunks)
        
        return f"Processed and saved {len(chunks)} chunks from {len(uploaded_files)} files to persistent storage."

    def get_response(self, query):
        if not self.retriever:
            return "Please upload documents first to initialize the knowledge base.", []
        
        # Retrieve documents
        docs = self.retriever.invoke(query)
        context_text = "\n\n".join([doc.page_content for doc in docs])
        
        prompt_template = """Use the following pieces of context to answer the question at the end. 
if you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Question: {question}
Answer:"""
        
        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        # Generate response using LCEL or direct invocation
        chain = prompt | self.llm | StrOutputParser()
        
        response = chain.invoke({"context": context_text, "question": query})
        
        return response, docs
