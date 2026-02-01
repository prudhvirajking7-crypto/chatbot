import streamlit as st
import os
import sys
import time
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth import logout, check_credentials
from rag_engine import RAGChatbot

load_dotenv()

st.set_page_config(
    page_title="Admin Panel",
    page_icon="🔐",
    layout="wide"
)

# Premium Admin CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    #MainMenu, footer, header {display: none;}
    
    .stApp {
        background-color: #0c1317;
    }
    
    /* Header */
    .admin-header {
        background: linear-gradient(135deg, #1f2c33 0%, #151f24 100%);
        color: #e9edef;
        padding: 1.2rem 2rem;
        margin: -4rem -4rem 2rem -4rem;
        border-bottom: 1px solid #2a3942;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Labels and Help Text */
    label, .stMarkdown p, .stText {
        color: #e9edef !important;
        font-weight: 500 !important;
        font-size: 15px !important;
    }

    /* Cards/Metrics - High Contrast */
    div[data-testid="stMetric"] {
        background: #1f2c33;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #2a3942;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    
    div[data-testid="stMetricLabel"] {
        color: #8696a0 !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #00ffca !important;
        font-weight: 800 !important;
    }
    
    /* Text Inputs */
    .stTextInput input {
        background: #2a3942 !important;
        color: #ffffff !important;
        border: 2px solid #3d4a52 !important;
        border-radius: 8px !important;
        font-size: 16px !important;
    }

    
    .stAlert {
        background: rgba(31, 44, 51, 0.6) !important;
        border: 1px solid #2a3942 !important;
        border-left: 4px solid #00a884 !important;
        color: #e9edef !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# Auth Logic
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #00a884;'>🔐 Admin Login</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8696a0;'>Enter credentials to manage documents</p>", unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=True):
        u = st.text_input("Username", placeholder="admin")
        p = st.text_input("Password", type="password", placeholder="••••••••")
        if st.form_submit_button("Sign In"):
            if check_credentials(u, p):
                st.session_state.authenticated = True
                st.success("Access Granted")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    if st.button("← Back to Chat"):
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Admin Header
st.markdown(f"""
    <div class="admin-header">
        <div style="font-size: 1.5rem; font-weight: 700; color: #00a884;">🚀 Admin Dashboard</div>
        <div style="color: #8696a0;">System Status: <span style="color: #00a884;">Online</span></div>
    </div>
""", unsafe_allow_html=True)

# Initialize Bot
if "bot" not in st.session_state:
    st.session_state.bot = None

if not st.session_state.bot:
    key = os.getenv("GOOGLE_API_KEY")
    if key:
        try: st.session_state.bot = RAGChatbot(key)
        except Exception as e: st.error(f"Init Error: {e}")

# Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📋 Document Management")
    uploaded_files = st.file_uploader(
        "Upload New Knowledge Base Files",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🚀 Process & Index Documents"):
            if not uploaded_files:
                st.warning("Please upload files first")
            else:
                with st.spinner("Indexing documents into MongoDB Atlas..."):
                    try:
                        res = st.session_state.bot.process_files(uploaded_files)
                        st.success(res)
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Index Error: {e}")
    
    with c2:
        if st.button("🗑️ Wipe Database", kind="secondary"):
            try:
                msg = st.session_state.bot.clear_all_documents()
                st.success(msg)
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Clear Error: {e}")

with col2:
    st.markdown("### 📊 Database Insight")
    if st.session_state.bot:
        try:
            count = st.session_state.bot.get_document_count()
            st.metric("Total Chunks", count)
            st.info(f"Connected to: **MongoDB Atlas**")
        except:
            st.error("Database connection failed")
    
    st.markdown("---")
    if st.button("🚪 Logout System"):
        st.session_state.authenticated = False
        st.rerun()

st.markdown("---")
st.markdown("### 📜 System Logs")
st.code(f"[{time.strftime('%H:%M:%S')}] Admin session active\n[{time.strftime('%H:%M:%S')}] MongoDB connection healthy", language="bash")

