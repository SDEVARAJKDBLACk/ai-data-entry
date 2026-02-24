import os, re, io, json
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import pandas as pd
from PIL import Image
import pdfplumber
from docx import Document

# ================= OCR SAFE IMPORT =================
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception as e:
    OCR_AVAILABLE = False
    print("OCR disabled:", e)

# ================= APP =================
app = FastAPI(title="AI Data Entry Enterprise Engine", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STORAGE =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE_DIR, "field_memory.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
EXPORT_PATH = os.path.join(BASE_DIR, "export.xlsx")

if not os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, "w") as f:
        json.dump({}, f)

if not os.path.exists(HISTORY_PATH):
    with open(HISTORY_PATH, "w") as f:
        json.dump([], f)

# ================= UTILS =================
def load_memory():
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_PATH, "w") as f:
        json.dump(mem, f, indent=2)

def load_history():
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)

def save_history(hist):
    with open(HISTORY_PATH, "w") as f:
        json.dump(hist, f, indent=2)

# ================= FILE EXTRACTION =================
def extract_text_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for p in pdf.pages:
            if p.extract_text():
                text += p.extract_text() + "\n"
    return text

def extract_text_from_docx(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_image(file_bytes):
    if not OCR_AVAILABLE:
        return ""
    img = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(img)

# ================= OFFLINE NLP ENGINE =================
def regex_extract(text: str) -> Dict[str, List[str]]:
    patterns = {
        "name": r"(?:my name is|i am|name is)\s+([A-Z][a-z]+)",
        "reference_name": r"(?:reference name is)\s+([A-Z][a-z]+\s[A-Z][a-z]+)",
        "age": r"(\d{1,3})\s*(?:years old|yrs old|age)",
        "gender": r"\b(male|female|other)\b",
        "phone": r"\b\d{10}\b",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "amount": r"\b\d{3,}\b",
        "city": r"\b(chennai|bangalore|mumbai|delhi|hyderabad)\b",
        "state": r"\b(tamil nadu|kerala|karnataka|maharashtra)\b",
        "country": r"\b(india|usa|uk|canada)\b",
        "address": r"\b\d{1,4},\s.*?(street|road|nagar)\b"
    }

    extracted = {}
    lower = text.lower()

    for field, pattern in patterns.items():
        matches = re.findall(pattern, lower, re.IGNORECASE)
        if matches:
            extracted[field] = list(set(matches))

    return extracted

# ================= AI FIELD ENGINE =================
def ai_field_engine(text: str) -> Dict[str, Any]:
    memory = load_memory()
    extracted = regex_extract(text)

    # ---------- MEMORY LEARNING ----------
    for field, values in extracted.items():
        if field not in memory:
            memory[field] = []
        for v in values:
            if v not in memory[field]:
                memory[field].append(v)

    save_memory(memory)

    # ---------- STRUCTURED MAPPING ----------
    structured = {}
    for k, v in extracted.items():
        structured[k.replace("_", " ").title()] = ", ".join(v)

    return structured

# ================= API =================

@app.post("/analyze")
async def analyze(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    content = ""

    if file:
        data = await file.read()
        fname = file.filename.lower()

        if fname.endswith(".pdf"):
            content = extract_text_from_pdf(data)
        elif fname.endswith(".docx"):
            content = extract_text_from_docx(data)
        elif fname.endswith((".png", ".jpg", ".jpeg")):
            content = extract_text_from_image(data)
        else:
            content = data.decode(errors="ignore")

    if text:
        content += "\n" + text

    if not content.strip():
        return JSONResponse({"error": "No input data"}, status_code=400)

    fields = ai_field_engine(content)

    history = load_history()
    history.append({
        "time": datetime.now().isoformat(),
        "input": content[:300],
        "fields": fields
    })
    save_history(history[-50:])  # last 50 only

    return {
        "status": "success",
        "fields": fields
    }

@app.get("/history")
def get_history():
    return load_history()[-10:]

@app.post("/custom-field")
def add_custom_field(field: str = Form(...), value: str = Form(...)):
    memory = load_memory()
    if field not in memory:
        memory[field] = []
    memory[field].append(value)
    save_memory(memory)
    return {"status": "added"}

@app.get("/export")
def export_excel():
    history = load_history()
    rows = []

    for h in history:
        for k, v in h["fields"].items():
            rows.append({
                "time": h["time"],
                "field": k,
                "value": v
            })

    if not rows:
        return JSONResponse({"error": "No data"}, status_code=400)

    df = pd.DataFrame(rows)
    df.to_excel(EXPORT_PATH, index=False)

    return FileResponse(EXPORT_PATH, filename="ai_data_export.xlsx")

@app.get("/")
def root():
    return {"status": "AI Data Entry Enterprise Engine Running"}
