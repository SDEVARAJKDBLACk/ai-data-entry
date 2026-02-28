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

# Screenshot-la irukkira athe Dark UI Theme
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e2e8f0; }
    div.stBlock { background-color: #161b22; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #30363d; }
    textarea, input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; height: 45px; }
    /* Button Colors from Screenshot */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #00bcd4 !important; color: white; } 
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button { background-color: #3f51b5 !important; color: white; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #673ab7 !important; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []

# --- Logic Functions ---
def extract_text(file):
    fname = file.name.lower()
    content = file.read()
    if fname.endswith('.pdf'):
        pdf = PyPDF2.PdfReader(io.BytesIO(content))
        return " ".join([p.extract_text() for p in pdf.pages])
    elif fname.endswith('.docx'):
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([p.text for p in doc.paragraphs])
    elif fname.endswith(('.png', '.jpg', '.jpeg')):
        return pytesseract.image_to_string(Image.open(io.BytesIO(content)))
    return content.decode('utf-8')

def ai_process(text, fields):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return {"Error": "OpenAI API Key-ai Environment Variables-la set pannunga!"}
    openai.api_key = api_key
    prompt = f"Extract these fields as a JSON object: {fields}. Text to analyze: {text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are an expert data entry AI."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e: return {"Error": str(e)}

# --- Main Dashboard ---
st.title("AI Data Entry – Automated Data Worker")

with st.container():
    st.markdown("### 📂 Upload text / notes / message / PDF / Word")
    file = st.file_uploader("", type=['pdf','docx','png','jpg','jpeg','txt'], label_visibility="collapsed")
    
    st.markdown("### Enter or paste input")
    raw_input = st.text_area("", height=150, label_visibility="collapsed")
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    
    if c1.button("Analyze"):
        data_src = extract_text(file) if file else raw_input
        if data_src:
            with st.spinner("AI is analyzing..."):
                res = ai_process(data_src, "Extract all available details like Name, Date, Amount, etc.")
                st.session_state.current_res = res
                st.session_state.history.append({"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **res})
        else:
            st.warning("Ethavathu file upload pannunga illana text paste pannunga!")

    if c2.button("Clear"):
        st.session_state.current_res = None
        st.rerun()
        
    if c3.button("Export Excel"):
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.download_button("Download Excel", data=df.to_csv().encode('utf-8'), file_name="data.csv")

# Result Display
st.markdown("---")
st.markdown("### Extracted Data:")
if 'current_res' in st.session_state and st.session_state.current_res:
    st.json(st.session_state.current_res)

# Custom Fields
st.markdown("---")
st.markdown("### ➕ Custom Fields")
f1, f2, f3 = st.columns([2, 2, 1])
f1.text_input("Field name", placeholder="e.g. Bill Number", label_visibility="collapsed")
f2.text_input("Value", placeholder="Default value", label_visibility="collapsed")
f3.button("Add")

# History
st.markdown("---")
st.markdown("### 🕒 Last 10 Analysis")
if st.session_state.history:
    st.table(pd.DataFrame(st.session_state.history).tail(10))
    
