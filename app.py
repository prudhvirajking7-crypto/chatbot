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
    
    /* Global scroll fix */
    html, body {
        overflow-x: hidden !important;
        width: 100%;
        margin: 0;
        padding: 0;
    }

    /* Main background - WhatsApp Web pattern */
    .stApp {
        background-color: #0c1317;
    }
    
    /* Container */
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    
    /* Header - Modern WhatsApp Navbar */
    h1 {
        background-color: #202c33 !important;
        color: #e9edef !important;
        padding: 1rem 2rem !important;
        margin: 0 !important;
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #2a3942 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4) !important;
    }
    
    /* Message bubbles - Forced Contrast & Shape */
    div[data-testid="stChatMessageContent"] {
        padding: 10px 15px !important;
        border-radius: 15px !important;
        max-width: 80% !important;
        box-shadow: 0 1px 1px rgba(0, 0, 0, 0.4) !important;
        border: none !important;
    }
    
    /* User: Vibrant Green with Crisp White Text */
    [data-testid="stChatMessage"]:has([aria-label="user"]) {
        flex-direction: row-reverse !important;
        text-align: right !important;
    }
    
    [data-testid="stChatMessage"]:has([aria-label="user"]) [data-testid="stChatMessageContent"] {
        background: #005c4b !important;
        color: #e9edef !important;
        margin-left: auto !important;
        border-top-right-radius: 0px !important;
    }
    
    /* Assistant: Clear Gray with Crisp White Text */
    [data-testid="stChatMessage"]:has([aria-label="assistant"]) [data-testid="stChatMessageContent"] {
        background: #202c33 !important;
        color: #e9edef !important;
        margin-right: auto !important;
        border-top-left-radius: 0px !important;
    }
    
    /* Force all text inside bubbles to be 100% visible */
    [data-testid="stChatMessageContent"] p, 
    [data-testid="stChatMessageContent"] span,
    [data-testid="stChatMessageContent"] li,
    [data-testid="stChatMessageContent"] div {
        color: #e9edef !important;
        font-size: 15.5px !important;
        line-height: 1.5 !important;
        font-weight: 400 !important;
    }

    /* Markdown Specifics */
    [data-testid="stChatMessageContent"] strong {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    [data-testid="stChatMessageContent"] ul, [data-testid="stChatMessageContent"] ol {
        margin-left: 20px !important;
        padding-left: 0px !important;
        color: #e9edef !important;
    }

    [data-testid="stChatMessageContent"] li {
        margin-bottom: 5px !important;
    }
    
    /* Chat input container - Fixing visibility and colors */
    [data-testid="stChatInput"] {
        background-color: #202c33 !important;
        border-radius: 10px !important;
        padding: 5px !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #2a3942 !important;
        color: #ffffff !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        border: 1px solid #3d4a52 !important;
    }

    /* Fixed white background issue */
    .stChatInputContainer {
        background-color: #0c1317 !important;
        padding: 20px !important;
        border-top: 1px solid #2a3942 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-thumb {
        background: #374045;
        border-radius: 3px;
    }

    /* Hide Avatars for true Minimal Chatbot look */
    [data-testid="chatAvatarIcon-user"],
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="stChatMessageAvatar"] {
        display: none !important;
    }

    @media (max-width: 768px) {
        div[data-testid="stChatMessageContent"] {
            max-width: 90% !important;
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
                # Get AI Response
                answer, sources = st.session_state.bot.get_response(prompt)
                
                # Faster Streaming with preserved markdown formatting
                response_placeholder = st.empty()
                full_response = ""
                
                # Split by words but KEEP whitespace for formatting
                words = answer.split(' ')
                for i, word in enumerate(words):
                    full_response += word + (" " if i < len(words) - 1 else "")
                    response_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01) # Faster than per-char
                
                response_placeholder.markdown(full_response)
                
                if sources:
                    with st.expander("📎 View Sources"):
                        for i, doc in enumerate(sources[:3], 1):
                            st.caption(f"**Source {i}:** {doc.page_content[:150]}...")
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    st.error("🚫 **Rate Limit Exceeded**: You've hit the Gemini API free tier limit. Please wait about 30-60 seconds before trying again.")
                    st.session_state.messages.append({"role": "assistant", "content": "⚠️ Rate limit reached. I'll be ready again in a minute!"})
                else:
                    st.error(f"Failed to get response: {error_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Sorry, I encountered an error: {error_msg}"})
        else:
            msg = "⚠️ The knowledge base hasn't been initialized yet. Please contact the administrator to upload documents."
            st.write(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})
