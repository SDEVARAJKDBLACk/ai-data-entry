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

# 1. Page Config
st.set_page_config(page_title="AI Data Entry Pro", layout="centered")

# 2. UI Design (Dark Theme)
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e2e8f0; }
    div.stBlock { background-color: #161b22; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #30363d; }
    textarea, input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; height: 45px; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #00bcd4 !important; color: white; } 
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button { background-color: #3f51b5 !important; color: white; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #673ab7 !important; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []

# 3. Main Dashboard (Direct Entry - No Login)
st.title("AI Data Entry – Automated Data Worker")

with st.container():
    st.markdown("### 📂 Upload text / notes / message / PDF / Word")
    file = st.file_uploader("", type=['pdf','docx','png','jpg','jpeg','txt'], label_visibility="collapsed")
    
    st.markdown("### Enter or paste input")
    raw_input = st.text_area("", height=150, label_visibility="collapsed")
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    
    if c1.button("Analyze"):
        st.info("AI is processing...")
        # extraction logic inga varum...

    if c2.button("Clear"):
        st.rerun()
        
    if c3.button("Export Excel"):
        st.write("Downloading...")

st.markdown("---")
st.markdown("### 🕒 Last 10 Analysis")
if st.session_state.history:
    st.table(pd.DataFrame(st.session_state.history))
