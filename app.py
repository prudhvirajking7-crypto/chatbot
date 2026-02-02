import streamlit as st
import time
import os
from dotenv import load_dotenv
from rag_engine import RAGChatbot

load_dotenv()

st.set_page_config(
    page_title="AI Assistant",
    page_icon="👋",
    layout="wide", # Wide mode for better responsiveness
    initial_sidebar_state="collapsed"
)

# --- UIDesign/CSS ---
st.markdown("""
<style>
    /* Import Font */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Roboto', sans-serif;
    }

    /* Main Background */
    .stApp {
        background-color: #f2f4f7;
    }

    /* Hide default Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}

    /* RESPONSIVE HEADER CONTAINER */
    .header-container {
        background: linear-gradient(135deg, #2b5ae2 0%, #1c92f4 100%);
        padding: 1rem 2rem;
        color: white;
        text-align: left;
        
        /* Fixed positioning */
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 80px; 
        display: flex;
        flex-direction: column;
        justify-content: center;
        z-index: 9999;
        
        box-shadow: 0 4px 12px rgba(43, 90, 226, 0.2);
    }
    
    .header-content-wrapper {
        max-width: 1000px;
        margin: 0 auto;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Adjust content container */
    .block-container {
        padding-top: 100px !important; 
        padding-bottom: 100px !important;
        max-width: 1000px !important;
        margin: 0 auto !important;
    }
    
    .header-title {
        font-size: 20px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .header-subtitle {
        font-size: 13px;
        opacity: 0.9;
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.2);
        padding: 4px 10px;
        border-radius: 20px;
    }
    
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #4ade80; 
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 5px #4ade80;
    }

    /* Chat Area */
    div[data-testid="stChatMessage"] {
        background-color: transparent;
        border: none;
        padding: 1rem 0;
    }

    /* Assistant Bubble (Left)*/
    [data-testid="stChatMessage"]:has([aria-label="assistant"]) {
        flex-direction: row !important;
        justify-content: flex-start !important;
    }

    [data-testid="stChatMessage"]:has([aria-label="assistant"]) [data-testid="stChatMessageContent"] {
        background-color: #ffffff;
        color: #1d1d1d;
        border-radius: 15px 15px 15px 0px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        padding: 1rem !important;
        max-width: 80% !important;
    }

    /* User Bubble (Right) */
    [data-testid="stChatMessage"]:has([aria-label="user"]) {
        flex-direction: row-reverse !important;
        justify-content: flex-end !important;
    }
    
    /* Ensure only inner content is reversed if needed, but usually text stays LTR */
    [data-testid="stChatMessage"]:has([aria-label="user"]) .stChatMessageContent {
        text-align: right; 
    }

    [data-testid="stChatMessage"]:has([aria-label="user"]) [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, #2b5ae2 0%, #246bfd 100%);
        color: white;
        border-radius: 15px 15px 0px 15px;
        box-shadow: 0 4px 10px rgba(43, 90, 226, 0.2);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 1rem !important;
        max-width: 80% !important;
        margin-left: auto !important;
    }

    /* Input Area - Centered and Aligned */
    .stChatInputContainer {
        padding-bottom: 2rem;
        background-color: transparent; /* Transparent to blend */
        max-width: 1000px !important;
        margin: 0 auto !important;
    }
    
    /* Inner form container adjustments if needed */
    [data-testid="stChatInput"] {
        background-color: white !important;
        border-radius: 30px !important;
        border: 1px solid #e1e4e8 !important;
        box-shadow: 0 5px 20px rgba(0,0,0,0.06) !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Remove Icons/Avatars */
    [data-testid="chatAvatarIcon-user"], [data-testid="chatAvatarIcon-assistant"] {
        display: none;
    }

    /* Button Polish */
    .stButton button {
        border-radius: 12px !important;
        font-weight: 500 !important;
        border: 1px solid #e1e4e8 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="header-container">
    <div class="header-content-wrapper">
        <div class="header-title">
            <span>RAG Chatbot 🤖</span>
        </div>
        <div class="header-subtitle">
            <span class="status-dot"></span>
            Online
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- State Init ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bot" not in st.session_state:
    st.session_state.bot = None

# Auto-init bot
if not st.session_state.bot:
    try:
        # RAGChatbot will check st.secrets or os.environ
        st.session_state.bot = RAGChatbot()
    except Exception:
        # Silent fail if keys missing (handled by UI warning)
        pass

# --- Helper Functions ---
def generate_response(prompt):
    """
    Generates a response for the given prompt, handling UI updates and RAG logic.
    """
    # Display user message if not already displayed (controlled by calling code)
    # This function assumes the message is already in session_state.messages
    
    with st.chat_message("assistant"):
        # 1. Check for specific meta-questions (Hardcoded fallbacks)
        meta_responses = {
            "Tell me about this chatbot.": "I am an intelligent document assistant built with RAG (Retrieval-Augmented Generation). I can read your uploaded PDF/Text documents and answer questions based on their content.",
            "How does this RAG system work?": "I assume a RAG architecture: 1. You upload documents. 2. I split them into chunks and store them in a vector database (MongoDB). 3. When you ask a question, I find the most relevant chunks and use Google Gemini to generate an answer.",
            "How many documents are currently indexed?": "I can check that for you. (This feature requires a live database connection check).",
            "What can you help me with?": "I can summarize long documents, extract specific details, compare information across files, and answer specific questions about your uploaded content."
        }
        
        if prompt in meta_responses and not st.session_state.bot:
             # Fallback if bot is not init but user clicked a button
             full_response = meta_responses[prompt]
             st.markdown(full_response)
             st.session_state.messages.append({"role": "assistant", "content": full_response})
             return

        if st.session_state.bot:
            try:
                # Placeholder for streaming
                response_placeholder = st.empty()
                full_response = ""
                
                # Check for meta-response override first, or use RAG
                if prompt in meta_responses:
                     answer = meta_responses[prompt]
                     sources = []
                else:
                    # Get Response from RAG
                    answer, sources = st.session_state.bot.get_response(prompt)
                
                # Simple Stream Simulation
                words = answer.split(' ')
                for i, word in enumerate(words):
                    full_response += word + " "
                    response_placeholder.markdown(full_response + "▌")
                    time.sleep(0.015) 
                
                response_placeholder.markdown(full_response)
                
                # Append sources if available
                if sources:
                    with st.expander("🔍 Verified Sources", expanded=False):
                        for i, doc in enumerate(sources[:2], 1): # Limit to 2 for cleaner UI
                            st.markdown(f"**Source {i}:**")
                            st.caption(doc.page_content[:200] + "...")
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                err_msg = f"⚠️ Error: {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
        else:
            msg = "⚠️ Knowledge base not initialized. Please check API key."
            st.warning(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})

# --- Suggested Topics ---
# Only show if no messages yet
if not st.session_state.messages:
    st.markdown("<div style='text-align: center; color: #666; margin-bottom: 20px; font-size: 14px;'>Please choose one of the topics listed below 👇</div>", unsafe_allow_html=True)
    
    # Grid for buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❓ About Chatbot"):
            msg = "Tell me about this chatbot."
            st.session_state.messages.append({"role": "user", "content": msg})
            # Force a rerun to display the user message then we will handle response at end of script if needed? 
            # Actually, standard Streamlit flow: update state -> rerun. 
            # But we want to trigger response generation.
            # We can use a flag.
            st.session_state.mk_run_response = msg
            st.rerun()
            
        if st.button("⚙️ How it works"):
             msg = "How does this RAG system work?"
             st.session_state.messages.append({"role": "user", "content": msg})
             st.session_state.mk_run_response = msg
             st.rerun()
             
    with col2:
        if st.button("📁 Documents"):
            msg = "How many documents are currently indexed?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.mk_run_response = msg
            st.rerun()
            
        if st.button("🚀 Capabilities"):
            msg = "What can you help me with?"
            st.session_state.messages.append({"role": "user", "content": msg})
            st.session_state.mk_run_response = msg
            st.rerun()

# --- Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Response Logic Handling ---
# Check if a button click triggered a response need
if "mk_run_response" in st.session_state and st.session_state.mk_run_response:
    prompt = st.session_state.mk_run_response
    # Clear flag
    st.session_state.mk_run_response = None
    # Generate response
    generate_response(prompt)

# --- Input & Response ---
if prompt := st.chat_input("Hit the buttons or type here..."):
    # Render user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Generate response
    generate_response(prompt)
