import streamlit as st
import time
import os
from dotenv import load_dotenv
from rag_engine import RAGChatbot

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="Gemini RAG Assistant",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for "Rich Aesthetics"
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Main App Background */
    .stApp {
        background-color: #0b0f19;
        background-image: radial-gradient(circle at 50% 10%, #1f293a 0%, #0b0f19 50%);
        color: #e0e0e0;
    }

    /* Chat Messages - General */
    .stChatMessage {
        background-color: rgba(42, 47, 60, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(12px);
    }

    /* Brighter Text */
    .stMarkdown p {
        color: #e2e8f0;
        line-height: 1.6;
        font-size: 1.05rem;
    }

    /* Code blocks */
    code {
        color: #fca5a5;
        background: rgba(0,0,0,0.3);
    }


    /* User Message Specifics (Optional if you can target specific roles, 
       but Streamlit custom CSS for specific roles is tricky. 
       We stick to general improvements) */

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
        text-transform: uppercase;
        font-size: 0.9rem;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
        transform: translateY(-1px);
    }

    /* Headings */
    h1 {
        background: linear-gradient(to right, #c084fc, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -1px;
        padding-bottom: 0.5rem;
    }
    
    h3 {
        color: #94a3b8;
        font-weight: 600;
    }

    /* Input Fields */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f8fafc;
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f131d;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: transparent;
        color: #94a3b8;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "bot" not in st.session_state:
    st.session_state.bot = None

# Sidebar Configuration
with st.sidebar:
    st.title("🔧 Configuration")
    
    # Try to get key from environment variable first
    env_api_key = os.getenv("GOOGLE_API_KEY", "")
    api_key = st.text_input("Enter Google Gemini API Key", value=env_api_key, type="password")
    
    # Auto-initialize bot if key is present
    if api_key and st.session_state.bot is None:
        try:
            st.session_state.bot = RAGChatbot(api_key)
        except Exception as e:
            st.error(f"Error initializing bot: {e}")

    st.divider()
    
    uploaded_files = st.file_uploader(
        "Upload Documents (PDF, TXT)", 
        type=["pdf", "txt"], 
        accept_multiple_files=True
    )
    
    if st.button("🚀 Process Documents"):
        if not api_key:
            st.error("Please provide an API Key first!")
        elif not uploaded_files:
            st.error("Please upload some files!")
        else:
            with st.spinner("Processing documents..."):
                try:
                    if st.session_state.bot is None:
                         st.session_state.bot = RAGChatbot(api_key)
                    
                    result = st.session_state.bot.process_files(uploaded_files)
                    st.success(result)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.divider()
    st.markdown("### About")
    st.info(
        "This chatbot uses **RAG (Retrieval-Augmented Generation)** "
        "to answer questions based on your uploaded documents. "
        "Powered by **Google Gemini**."
    )

# Main Chat Interface
st.title("🤖 Intelligent Document Assistant")
st.caption("Ask questions about your documents in real-time.")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("What would you like to know?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        if st.session_state.bot:
            try:
                with st.spinner("Thinking..."):
                    answer, sources = st.session_state.bot.get_response(prompt)
                    
                    # Simulate typing effect
                    for chunk in answer.split():
                        full_response += chunk + " "
                        time.sleep(0.02)
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                    
                    # Show sources
                    if sources:
                        with st.expander("View Sources"):
                            for doc in sources:
                                st.markdown(f"- **{doc.metadata.get('source', 'Unknown')}**: {doc.page_content[:100]}...")
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
        else:
            st.warning("Please configure the system and upload documents first.")

    st.session_state.messages.append({"role": "assistant", "content": full_response})
