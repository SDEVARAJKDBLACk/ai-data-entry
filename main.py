from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import sqlite3
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import pandas as pd
import openai
import uuid
import json
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
DB_NAME = "enterprise.db"
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="AI Data Entry Enterprise Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DATABASE INIT
# =========================
def init_db():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id TEXT,
        input TEXT,
        result TEXT,
        created TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS custom_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_name TEXT,
        field_value TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS learned_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern TEXT,
        field_name TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

def get_db():
    return sqlite3.connect(DB_NAME)

# =========================
# OCR
# =========================
def ocr_image(file):
    img = Image.open(file)
    text = pytesseract.image_to_string(img)
    return text

# =========================
# PDF
# =========================
def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# =========================
# AI ENGINE
# =========================
def ai_extract(text):
    prompt = f"""
    You are an AI data extraction engine.

    Tasks:
    - Auto detect fields
    - Auto detect values
    - Structure data
    - Support unlimited fields
    - Return clean JSON only

    TEXT:
    {text}
    """

    res = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return res.choices[0].message["content"]

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "AI Data Entry Enterprise Backend Running"}

# =========================
# ANALYZE
# =========================
@app.post("/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    raw_text = text

    if file:
        if file.filename.lower().endswith(".pdf"):
            raw_text += "\n" + read_pdf(file.file)

        elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raw_text += "\n" + ocr_image(file.file)

        elif file.filename.lower().endswith((".txt",)):
            raw_text += "\n" + (await file.read()).decode()

    # AI Extraction
    ai_result = ai_extract(raw_text)

    record_id = str(uuid.uuid4())
    created = datetime.now().isoformat()

    con = get_db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO history VALUES (?,?,?,?)",
        (record_id, raw_text, ai_result, created)
    )
    con.commit()
    con.close()

    return JSONResponse(content={
        "id": record_id,
        "result": ai_result
    })

# =========================
# HISTORY
# =========================
@app.get("/history")
def get_history():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM history ORDER BY created DESC")
    rows = cur.fetchall()
    con.close()
    return rows

@app.get("/history/last10")
def last10():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM history ORDER BY created DESC LIMIT 10")
    rows = cur.fetchall()
    con.close()
    return rows

# =========================
# CUSTOM FIELDS
# =========================
@app.post("/custom-field")
def add_custom(field_name: str = Form(...), field_value: str = Form(...)):
    con = get_db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO custom_fields(field_name, field_value) VALUES (?,?)",
        (field_name, field_value)
    )
    con.commit()
    con.close()
    return {"status": "custom field saved"}

@app.get("/custom-fields")
def get_custom():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT field_name, field_value FROM custom_fields")
    rows = cur.fetchall()
    con.close()
    return rows

# =========================
# FIELD LEARNING
# =========================
@app.post("/learn")
def learn(pattern: str = Form(...), field_name: str = Form(...)):
    con = get_db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO learned_fields(pattern, field_name) VALUES (?,?)",
        (pattern, field_name)
    )
    con.commit()
    con.close()
    return {"status": "learning saved"}

@app.get("/learned")
def learned():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT pattern, field_name FROM learned_fields")
    rows = cur.fetchall()
    con.close()
    return rows

# =========================
# EXPORT EXCEL
# =========================
@app.post("/export")
def export_excel(data: dict):
    file_name = f"export_{uuid.uuid4().hex}.xlsx"
    df = pd.DataFrame(list(data.items()), columns=["Field", "Value"])
    df.to_excel(file_name, index=False)
    return FileResponse(file_name, filename=file_name)

# =========================
# RENDER ENTRY POINT
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
