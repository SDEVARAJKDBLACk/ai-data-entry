import streamlit as st
import re
import pandas as pd
import io
import os
import nltk
from datetime import datetime

# --- NLP setup with NLTK (Lightweight Replacement for Spacy) ---
@st.cache_resource
def setup_nltk():
    try:
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('maxent_ne_chunker')
        nltk.download('words')
        nltk.download('punkt_tab')
    except Exception as e:
        st.error(f"NLTK Download Error: {e}")

setup_nltk()

def extract_entities_nltk(text):
    names = []
    locations = []
    try:
        for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(text))):
            if hasattr(chunk, 'label'):
                if chunk.label() == 'PERSON':
                    names.append(' '.join(c[0] for c in chunk))
                elif chunk.label() in ['GPE', 'LOCATION']:
                    locations.append(' '.join(c[0] for c in chunk))
    except:
        pass
    return list(set(names)), list(set(locations))

# --- Page Configuration & Dark UI ---
st.set_page_config(page_title="AI Data Entry Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e2e8f0; }
    div.stBlock { background-color: #161b22; padding: 25px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 20px; }
    textarea, input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; font-size: 16px !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; height: 50px; transition: 0.3s; }
    
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #00bcd4 !important; color: white; border: none; } 
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button { background-color: #3f51b5 !important; color: white; border: none; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #673ab7 !important; color: white; border: none; }
    
    .extracted-box { background-color: #1c2128; padding: 15px; border-radius: 10px; border-left: 5px solid #00bcd4; margin-bottom: 10px; }
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

if 'history' not in st.session_state: st.session_state.history = []
if 'extracted_results' not in st.session_state: st.session_state.extracted_results = {}

# --- 30+ Regex Patterns ---
PATTERNS = {
    "Aadhar_Card": r'\b\d{4}\s\d{4}\s\d{4}\b',
    "PAN_Card": r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',
    "GST_No": r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b',
    "Phone_Number": r'\b(?:\+91|91|0)?[6-9]\d{9}\b',
    "Email_Address": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    "Pincode": r'\b\d{6}\b',
    "Amount_INR": r'(?:Rs\.?|INR|₹)\s?(\d+(?:,\d+)*(?:\.\d+)?)',
    "Date_DDMMYYYY": r'\b\d{2}[/-]\d{2}[/-]\d{4}\b',
    "OTP_Code": r'\b\d{4,6}\b(?=.*otp|.*code|.*verification|.*sent)',
    "UPI_ID": r'\b[\w.-]+@[a-zA-Z]{3,}\b',
    "Credit_Card": r'\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b',
    "IFSC_Code": r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
    "Bank_Acc_No": r'\b\d{9,18}\b(?=.*account|.*acc|.*bank)',
    "Voter_ID": r'\b[A-Z]{3}[0-9]{7}\b',
    "Passport_No": r'\b[A-Z]{1}[0-9]{7}\b',
    "Vehicle_No": r'\b[A-Z]{2}\s?[0-9]{2}\s?[A-Z]{1,2}\s?[0-9]{4}\b',
    "Age": r'\b\d{1,3}\s?(years?|yrs?|age)\b',
    "Quantity": r'\b\d+\s?(pcs|units|nos|items|quantity)\b',
    "Password": r'(?i)password[:\s]+(\S+)',
    "Time": r'\b(?:[01]\d|2[0-3]):[0-5]\d\b',
    "Weight": r'\b\d+(\.\d+)?\s?(kg|gram|g|mg)\b',
    "Distance": r'\b\d+(\.\d+)?\s?(km|m|cm|miles)\b',
    "URL": r'https?://[^\s]+',
    "IP_Address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "Designation": r'(?i)(?:as|is a|works as)\s+([a-zA-Z\s]{3,25})(?=\.|\s+at)',
    "Salary": r'(?i)(?:salary|income|pay)\s?(?:is)?[:\s₹]+(\d+)',
    "Reference_No": r'(?i)(?:ref|reference|txn)\s?(?:no|id)?[:\s#]+([A-Z0-9]+)',
    "Company": r'(?i)(?:in|at)\s+([a-zA-Z0-9\s]{3,30})\s+(?:company|office|corp)',
    "Gender": r'\b(Male|Female|Other|m/f)\b',
    "Price": r'(?i)(?:price|cost|rate)\s?(?:is)?[:\s₹$]+(\d+)'
}

def deep_analyze(text):
    found = {}
    # 1. Regex Match
    for key, pattern in PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            val = matches if len(matches) > 1 else matches[0]
            found[key] = val[0] if isinstance(val, tuple) else val

    # 2. NLP Replacement (NLTK)
    names, locations = extract_entities_nltk(text)
    if names: found["Detected_Names"] = names
    if locations: found["Detected_Locations"] = locations
    
    return found

# --- UI Layout ---
st.title("AI Data Entry – Automated Data Worker")

with st.container():
    st.markdown("### 📂 Upload text / PDF / Word")
    file = st.file_uploader("", type=['pdf','docx','txt'], label_visibility="collapsed")
    
    st.markdown("### Enter or paste input")
    raw_input = st.text_area("", height=250, label_visibility="collapsed", placeholder="Paste your bulk data here...")
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    
    if c1.button("Analyze"):
        if raw_input:
            with st.spinner("Scanning Patterns..."):
                results = deep_analyze(raw_input)
                st.session_state.extracted_results = results
                if results:
                    st.session_state.history.append({"Timestamp": datetime.now().strftime("%H:%M:%S"), **results})
        else:
            st.warning("Input box-la data paste pannunga!")

    if c2.button("Clear"):
        st.session_state.extracted_results = {}
        st.rerun()
        
    if c3.button("Export Excel"):
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "data_export.csv", "text/csv")

st.markdown("---")
st.markdown("### Extracted Data:")
if st.session_state.extracted_results:
    col_a, col_b = st.columns(2)
    for i, (k, v) in enumerate(st.session_state.extracted_results.items()):
        target_col = col_a if i % 2 == 0 else col_b
        target_col.markdown(f"""<div class="extracted-box"><b>{k}:</b><br>{v}</div>""", unsafe_allow_html=True)
else:
    st.info("Results will appear here.")

st.markdown("---")
st.markdown("### 🕒 Last 10 Analysis")
if st.session_state.history:
    st.dataframe(pd.DataFrame(st.session_state.history).tail(10), use_container_width=True)
