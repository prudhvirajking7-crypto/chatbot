import streamlit as st
import time
import os
from dotenv import load_dotenv
from rag_engine import RAGChatbot

load_dotenv()

st.set_page_config(
    page_title="Chat Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Premium WhatsApp-inspired CSS
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer, header {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebarNav"] {display: none !important;}
    
    /* Main background - WhatsApp Web pattern */
    .stApp {
        background-color: #0c1317;
        background-image: 
            radial-gradient(at 20% 30%, rgba(0, 168, 132, 0.05) 0px, transparent 50%),
            radial-gradient(at 80% 70%, rgba(0, 92, 75, 0.05) 0px, transparent 50%);
    }
    
    /* Container */
    .main {
        padding: 0 !important;
    }
    
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Header */
    h1 {
        background-color: #202c33 !important;
        background-image: none !important;
        color: #ffffff !important;
        padding: 1.25rem 2rem !important;
        margin: 0 !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        border-bottom: 1px solid #2a3942 !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Message bubbles - Forced Contrast */
    div[data-testid="stChatMessageContent"] {
        padding: 0.8rem 1.2rem !important;
        border-radius: 12px !important;
        max-width: 75% !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* User: Vibrant WhatsApp Green with Pure White Text */
    [data-testid="stChatMessage"]:has([aria-label="user"]) [data-testid="stChatMessageContent"] {
        background: #008069 !important;
        color: #ffffff !important;
        border-bottom-right-radius: 2px !important;
    }
    
    /* Assistant: Clear Gray with Crisp White Text */
    [data-testid="stChatMessage"]:has([aria-label="assistant"]) [data-testid="stChatMessageContent"] {
        background: #202c33 !important;
        color: #ffffff !important;
        border-bottom-left-radius: 2px !important;
    }
    
    /* Force all text inside bubbles to be visible */
    [data-testid="stChatMessageContent"] p, 
    [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessageContent"] li {
        color: #ffffff !important;
        font-size: 16px !important;
        font-weight: 400 !important;
        line-height: 1.6 !important;
    }

    
    /* Chat input container */
    .stChatInputContainer {
        background: linear-gradient(180deg, #1f2c33 0%, #151f24 100%) !important;
        padding: 1.2rem 2rem !important;
        border-top: 1px solid #2a3942 !important;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
        position: sticky !important;
        bottom: 0 !important;
    }
    
    /* Chat input field */
    .stChatInput {
        max-width: 100% !important;
    }
    
    .stChatInput > div {
        background: #2a3942 !important;
        border-radius: 10px !important;
        border: 1px solid #3d4a52 !important;
        transition: all 0.2s ease !important;
    }
    
    .stChatInput > div:focus-within {
        border-color: #00a884 !important;
        box-shadow: 0 0 0 2px rgba(0, 168, 132, 0.1) !important;
    }
    
    textarea {
        background: transparent !important;
        color: #e9edef !important;
        border: none !important;
        font-size: 15px !important;
        padding: 12px 16px !important;
        min-height: 44px !important;
    }
    
    textarea::placeholder {
        color: #8696a0 !important;
    }
    
    textarea:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    
    /* Info/Alert styling */
    .stAlert {
        background: rgba(31, 44, 51, 0.6) !important;
        backdrop-filter: blur(10px) !important;
        color: #8696a0 !important;
        border: 1px solid #2a3942 !important;
        border-left: 3px solid #00a884 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin: 1rem 2rem !important;
        font-size: 14px !important;
    }
    
    /* Expander for sources */
    .streamlit-expanderHeader {
        background: rgba(42, 57, 66, 0.5) !important;
        border: 1px solid #3d4a52 !important;
        border-radius: 6px !important;
        color: #8696a0 !important;
        font-size: 13px !important;
        padding: 0.5rem 0.75rem !important;
        margin-top: 0.5rem !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(42, 57, 66, 0.8) !important;
        border-color: #00a884 !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(31, 44, 51, 0.5) !important;
        border: 1px solid #3d4a52 !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        padding: 0.75rem !important;
    }
    
    /* Captions in expander */
    .stCaptionContainer {
        color: #8696a0 !important;
        font-size: 13px !important;
        line-height: 1.4 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Avatar icons */
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-assistant"] {
        display: none !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0c1317;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2a3942;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #3d4a52;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        h1 {
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
        }
        
        .stChatMessage {
            padding: 0.5rem 1rem !important;
        }
        
        div[data-testid="stChatMessageContent"] {
            max-width: 80% !important;
            font-size: 14px !important;
        }
        
        .stChatInputContainer {
            padding: 1rem 1rem !important;
        }
        
        .stAlert {
            margin: 1rem 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bot" not in st.session_state:
    st.session_state.bot = None

# Auto-init bot
if not st.session_state.bot:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            st.session_state.bot = RAGChatbot(api_key)
        except:
            pass

# Header
st.title("💬 AI Document Assistant")

# Welcome message
if not st.session_state.messages:
    st.info("👋 Hello! I'm your AI assistant. Ask me anything about your documents and I'll help you find the answers.")

# Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        if st.session_state.bot:
            try:
                answer, sources = st.session_state.bot.get_response(prompt)
                
                response = st.empty()
                displayed = ""
                for word in answer.split():
                    displayed += word + " "
                    time.sleep(0.015)
                    response.write(displayed + "▌")
                response.write(displayed)
                
                if sources:
                    with st.expander("📎 View Sources"):
                        for i, doc in enumerate(sources[:3], 1):
                            st.caption(f"**Source {i}:** {doc.page_content[:150]}...")
                
                st.session_state.messages.append({"role": "assistant", "content": displayed})
            except Exception as e:
                err = f"⚠️ Error: {str(e)}"
                st.write(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
        else:
            msg = "⚠️ The knowledge base hasn't been initialized yet. Please contact the administrator to upload documents."
            st.write(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})
