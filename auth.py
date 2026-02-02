import streamlit as st
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    """Check if credentials are valid"""
    # Get credentials from environment
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass_hash = os.getenv("ADMIN_PASSWORD_HASH")
    
    # If no hash in env, use default (change this!)
    if not admin_pass_hash:
        admin_pass_hash = hash_password("admin123")
    
    return username == admin_user and hash_password(password) == admin_pass_hash

def login_page():
    """Display login page"""
    st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
    
    st.markdown("""
    <style>
        .stApp {background-color: #0b141a;}
        #MainMenu, footer, header {display: none;}
        h1 {color: #00a884; text-align: center;}
        .stButton button {
            background: #00a884 !important;
            color: white !important;
            width: 100%;
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔐 Admin Login")
    st.markdown("---")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.is_admin = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    st.markdown("---")
    st.info("💬 **Regular users**: Chat is available without login at the main page")

def logout():
    """Logout function"""
    st.session_state.authenticated = False
    st.session_state.is_admin = False
    st.rerun()

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
