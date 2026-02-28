import streamlit as st
import re
import pandas as pd
import nltk
from datetime import datetime

# --- NLP Setup (Lightweight) ---
@st.cache_resource
def setup_nltk():
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')

setup_nltk()

# --- Custom Styling (Exact Screenshot Look) ---
st.set_page_config(page_title="AI Data Entry", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b1120; color: #e2e8f0; }
    .main-container { background-color: #161b22; padding: 25px; border-radius: 15px; border: 1px solid #30363d; margin-top: 10px; }
    
    /* Input Area Styling */
    textarea { background-color: #ffffff !important; color: #000000 !important; border-radius: 10px !important; }
    
    /* Button Styling */
    .stButton>button { border-radius: 8px; font-weight: 600; padding: 10px 25px; transition: 0.3s; color: white; border: none; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #00bcd4 !important; } 
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button { background-color: #3f51b5 !important; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #673ab7 !important; }
    
    /* Table Styling (Match Screenshot) */
    .styled-table { width: 100%; border-collapse: collapse; margin: 25px 0; font-size: 16px; border-radius: 10px; overflow: hidden; }
    .styled-table thead tr { background-color: #1c2536; color: #ffffff; text-align: left; }
    .styled-table th, .styled-table td { padding: 12px 15px; border-bottom: 1px solid #232d3f; }
    .styled-table tbody tr { background-color: #111827; }
    
    .section-header { color: #ffffff; font-weight: bold; margin-top: 20px; margin-bottom: 10px; }
    .custom-field-box { background-color: #1c2536; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Session States
if 'history' not in st.session_state: st.session_state.history = []
if 'extracted' not in st.session_state: st.session_state.extracted = {}
if 'custom_fields' not in st.session_state: st.session_state.custom_fields = {}

# --- Advanced Regex Extraction ---
def extract_all(text):
    results = {}
    
    # Pre-defined Patterns
    patterns = {
        "Name": r"(?i)(?:my name is|i am)\s+([a-zA-Z\s]{2,20})(?=\.|\n)",
        "Reference Name": r"(?i)(?:reference name is|ref name)\s+([a-zA-Z\s]{2,20})",
        "Age": r"\b\d{1,3}\s?(?:years? old|yrs?|age)\b",
        "Gender": r"\b(male|female|other)\b",
        "Phone": r"\b(?:\+91|91|0)?[6-9]\d{9}\b",
        "Email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "Address": r"\d+,\s[a-zA-Z\s,]+(?=\.|\n)",
        "City": r"(?i)city is\s+([a-zA-Z]+)",
        "State": r"(?i)state is\s+([a-zA-Z\s]+)",
        "Country": r"(?i)country is\s+([a-zA-Z]+)",
        "Job Title": r"(?i)(?:designation is|works as|as)\s+([a-zA-Z\s]{3,25})",
        "Amount": r"\b\d{4,10}\b(?=.*paid|.*salary|.*price)",
        "Product Name": r"(?i)product name is\s+([a-zA-Z\s]+)",
        "Date": r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
    }

    for key, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            # Cleaning results
            clean_matches = [m[0] if isinstance(m, tuple) else m for m in matches]
            results[key] = ", ".join(list(dict.fromkeys(clean_matches))).lower()

    return results

# --- Header ---
st.title("AI Data Entry – Automated Data Worker")

with st.container():
    st.markdown("📂 **Upload text / notes / message / PDF / Word**")
    st.file_uploader("", type=['pdf','docx','txt'], label_visibility="collapsed")
    
    st.markdown("Enter or paste input")
    user_input = st.text_area("", height=200, placeholder="Paste data here...", label_visibility="collapsed")
    
    c1, c2, c3 = st.columns([0.5, 0.5, 3])
    with c1:
        if st.button("Analyze"):
            if user_input:
                st.session_state.extracted = extract_all(user_input)
                st.session_state.history.append({"Time": datetime.now().strftime("%H:%M"), **st.session_state.extracted})
    with c2:
        if st.button("Clear"):
            st.session_state.extracted = {}
            st.session_state.custom_fields = {}
            st.rerun()
    with c3:
        st.button("Export Excel")

# --- Results Table (Exactly like Screenshot) ---
st.markdown('<div class="section-header">Extracted Data:</div>', unsafe_allow_html=True)

if st.session_state.extracted or st.session_state.custom_fields:
    # Combining auto and custom fields
    all_data = {**st.session_state.extracted, **st.session_state.custom_fields}
    
    table_html = '<table class="styled-table"><thead><tr><th>Field</th><th>Values</th></tr></thead><tbody>'
    for field, value in all_data.items():
        table_html += f'<tr><td><b>{field}</b></td><td>{value}</td></tr>'
    table_html += '</tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("No data extracted yet.")

# --- Custom Fields (Exactly like Screenshot) ---
st.markdown('<div class="custom-field-box">', unsafe_allow_html=True)
st.markdown('➕ **Custom Fields**')
cc1, cc2, cc3 = st.columns([1, 1, 0.5])
with cc1:
    f_name = st.text_input("Field name", key="fn", label_visibility="collapsed", placeholder="Field name")
with cc2:
    f_val = st.text_input("Value", key="fv", label_visibility="collapsed", placeholder="Value")
with cc3:
    if st.button("Add"):
        if f_name and f_val:
            st.session_state.custom_fields[f_name] = f_val
st.markdown('</div>', unsafe_allow_html=True)

# --- History ---
st.markdown('<div class="section-header">🕒 Last 10 Analysis</div>', unsafe_allow_html=True)
if st.session_state.history:
    st.table(pd.DataFrame(st.session_state.history).tail(10))
    
