# backend/main.py
import os, re, io, json, uuid
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import pandas as pd

# ---------- Optional Heavy Libs (Safe Import) ----------
OCR_AVAILABLE = False
PDF_AVAILABLE = False
DOC_AVAILABLE = False
NLP_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except:
    pass

try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    pass

try:
    from docx import Document
    DOC_AVAILABLE = True
except:
    pass

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    NLP_AVAILABLE = True
except:
    NLP_AVAILABLE = False
    nlp = None

# ---------- APP ----------
app = FastAPI(title="AI Data Entry Engine", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- STORAGE ----------
HISTORY: List[Dict] = []
MEMORY_PATH = "field_memory.json"
EXPORT_FILE = "export.xlsx"

if not os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, "w") as f:
        json.dump({}, f)

def load_memory():
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_PATH, "w") as f:
        json.dump(mem, f, indent=2)

# ---------- CORE AI ENGINE ----------

FIELD_SCHEMA = {
    "name": [],
    "age": [],
    "gender": [],
    "phone": [],
    "alternate_phone": [],
    "email": [],
    "address": [],
    "city": [],
    "state": [],
    "country": [],
    "pincode": [],
    "company": [],
    "job_title": [],
    "salary": [],
    "amount": [],
    "product_name": [],
    "price": [],
    "quantity": [],
    "date": [],
}

REGEX = {
    "phone": r"\b\d{10}\b",
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "pincode": r"\b\d{6}\b",
    "amount": r"\b\d{3,}\b",
    "date": r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
}

JOB_WORDS = ["developer","engineer","analyst","manager","designer","consultant"]
COMPANY_WORDS = ["ltd","limited","pvt","private","corp","company","technologies","infosys","tcs"]
PRODUCT_WORDS = ["laptop","mobile","phone","computer","tv","tablet"]

def clean(text):
    return text.replace("\n", " ").replace("\t", " ").strip().lower()

def unique_add(lst, val):
    if val not in lst:
        lst.append(val)

def extract_regex(text, pattern):
    return re.findall(pattern, text)

def nlp_entities(text):
    ents = []
    if NLP_AVAILABLE:
        doc = nlp(text)
        for e in doc.ents:
            ents.append((e.text.lower(), e.label_))
    return ents

def smart_extract(text:str):
    text_raw = text
    text = clean(text)

    data = {k:[] for k in FIELD_SCHEMA}

    # Regex extraction
    phones = extract_regex(text, REGEX["phone"])
    emails = extract_regex(text, REGEX["email"])
    pincodes = extract_regex(text, REGEX["pincode"])
    dates = extract_regex(text, REGEX["date"])
    nums = extract_regex(text, REGEX["amount"])

    for p in phones: unique_add(data["phone"], p)
    for e in emails: unique_add(data["email"], e)
    for p in pincodes: unique_add(data["pincode"], p)
    for d in dates: unique_add(data["date"], d)

    # NLP extraction
    ents = nlp_entities(text_raw)

    for val,label in ents:
        if label == "PERSON":
            unique_add(data["name"], val)
        elif label == "GPE":
            unique_add(data["city"], val)
        elif label == "ORG":
            unique_add(data["company"], val)
        elif label == "DATE":
            unique_add(data["date"], val)
        elif label == "MONEY":
            unique_add(data["amount"], re.sub(r"[^\d]","",val))

    # Heuristic extraction
    for word in JOB_WORDS:
        if word in text:
            unique_add(data["job_title"], word)

    for word in PRODUCT_WORDS:
        if word in text:
            unique_add(data["product_name"], word)

    for word in COMPANY_WORDS:
        for t in text.split():
            if word in t:
                unique_add(data["company"], t)

    # Age & Gender
    for n in nums:
        if 1 <= int(n) <= 120:
            unique_add(data["age"], n)
        elif int(n) > 1000:
            unique_add(data["amount"], n)

    if "male" in text: unique_add(data["gender"], "male")
    if "female" in text: unique_add(data["gender"], "female")

    # Salary logic
    if "salary" in text:
        for n in nums:
            if int(n) > 1000:
                unique_add(data["salary"], n)

    # Memory learning
    memory = load_memory()
    for k,v in data.items():
        if v:
            memory[k] = list(set(memory.get(k, []) + v))
    save_memory(memory)

    return data

# ---------- FILE PARSERS ----------

def parse_file(file:UploadFile):
    ext = file.filename.split(".")[-1].lower()
    content = ""

    if ext in ["txt"]:
        content = file.file.read().decode()

    elif ext in ["pdf"] and PDF_AVAILABLE:
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                content += page.extract_text() + "\n"

    elif ext in ["docx"] and DOC_AVAILABLE:
        doc = Document(file.file)
        for p in doc.paragraphs:
            content += p.text + "\n"

    elif ext in ["png","jpg","jpeg"] and OCR_AVAILABLE:
        img = Image.open(file.file)
        content = pytesseract.image_to_string(img)

    return content

# ---------- API ----------

@app.get("/health")
def health():
    return {"status":"ok","ocr":OCR_AVAILABLE,"nlp":NLP_AVAILABLE}

@app.post("/analyze")
def analyze(text: str = Form(...)):
    result = smart_extract(text)
    record = {
        "id": str(uuid.uuid4()),
        "time": datetime.utcnow().isoformat(),
        "data": result
    }
    HISTORY.append(record)
    return result

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    text = parse_file(file)
    result = smart_extract(text)
    record = {
        "id": str(uuid.uuid4()),
        "time": datetime.utcnow().isoformat(),
        "data": result
    }
    HISTORY.append(record)
    return result

@app.post("/custom-field")
def custom_field(field:str = Form(...), value:str = Form(...)):
    if not HISTORY:
        return {"error":"No analysis data"}
    HISTORY[-1]["data"].setdefault(field.lower(), [])
    unique_add(HISTORY[-1]["data"][field.lower()], value.lower())
    return HISTORY[-1]["data"]

@app.get("/history")
def history():
    return HISTORY[-10:]

@app.get("/export")
def export_excel():
    if not HISTORY:
        return {"error":"No data"}
    rows = []
    for rec in HISTORY:
        row = {}
        for k,v in rec["data"].items():
            row[k] = ", ".join(v)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_excel(EXPORT_FILE, index=False)
    return FileResponse(EXPORT_FILE)
