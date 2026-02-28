import streamlit as st
import openai
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io
import json
import pandas as pd
import os
from datetime import datetime

# --- Page Config & UI Design ---
st.set_page_config(page_title="AI Data Entry Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e2e8f0; }
    div.stBlock { background-color: #161b22; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #30363d; }
    input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; height: 45px; }
    .analyze-btn button { background-color: #00bcd4 !important; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- Session States for User Login ---
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'history' not in st.session_state:
    st.session_state.history = []

# --- Login Logic (Email & Password) ---
def login_ui():
    st.title("🔐 AI Data Entry Login")
    st.write("Enter your credentials to access the application")
    
    with st.container():
        email = st.text_input("Email ID (e.g., user@gmail.com)")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        if col1.button("Login"):
            # Real-time-la inga Firebase illana Auth0 API call pannanum
            # Ippo verification-kaga oru condition:
            if "@" in email and len(password) > 5:
                st.session_state.is_authenticated = True
                st.session_state.user_email = email
                st.success(f"Welcome {email}!")
                st.rerun()
            else:
                st.error("Invalid Email format or Password too short!")
        
        if col2.button("Sign Up"):
            st.info("Registration feature coming soon!")

# --- Main App Features ---
def main_app():
    st.sidebar.write(f"👤 Logged in as: **{st.session_state.user_email}**")
    if st.sidebar.button("Logout"):
        st.session_state.is_authenticated = False
        st.rerun()

    st.title("AI Data Entry – Automated Data Worker")
    
    # Upload Section
    with st.container():
        st.markdown("### 📂 File Upload (PDF/Image/Word/Notes)")
        uploaded_file = st.file_uploader("Upload", type=['pdf','docx','png','jpg','jpeg','txt'], label_visibility="collapsed")
        
        st.markdown("### Input Message / Notes")
        user_text = st.text_area("Paste here", height=150, label_visibility="collapsed")
        
        c1, c2, c3 = st.columns([1, 1, 1.2])
        if c1.button("Analyze Data"):
            # AI Processing Logic
            st.info("AI is extracting data... (Ensure OpenAI Key is set)")
            # Example Entry for History
            st.session_state.history.append({
                "User": st.session_state.user_email,
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Status": "Completed"
            })
            
        if c2.button("Clear All"):
            st.rerun()
            
        if c3.button("Export to Excel"):
            st.write("Downloading...")

    # Custom Fields & History (Same as UI)
    st.markdown("---")
    st.subheader("➕ Custom Fields")
    f1, f2, _ = st.columns([2, 2, 1])
    f1.text_input("Field Name", placeholder="e.g. GST No")
    f2.text_input("Default Value")
    
    st.markdown("---")
    st.subheader("🕒 Your Recent History")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.write("No history found for this account.")

# --- Execution Flow ---
if not st.session_state.is_authenticated:
    login_ui()
else:
    main_app()
    
