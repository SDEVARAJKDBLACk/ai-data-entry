from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import openai, os, json, sqlite3, pytesseract
from PIL import Image
import fitz  # PyMuPDF
import pandas as pd
import uuid

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "history.db"

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS history(id TEXT, input TEXT, result TEXT)")
    con.commit()
    con.close()

init_db()

def ocr_image(file):
    img = Image.open(file)
    return pytesseract.image_to_string(img)

def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@app.post("/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    raw_text = text

    if file:
        if file.filename.endswith(".pdf"):
            raw_text += read_pdf(file.file)
        elif file.filename.lower().endswith((".png",".jpg",".jpeg")):
            raw_text += ocr_image(file.file)

    prompt = f"""
    Extract structured data fields, auto-detect fields, map values, create JSON, unlimited fields supported:
    {raw_text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    result = response.choices[0].message.content
    rid = str(uuid.uuid4())

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("INSERT INTO history VALUES(?,?,?)",(rid, raw_text, result))
    con.commit()
    con.close()

    return {"id":rid,"result":result}

@app.get("/history")
def history():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute("SELECT * FROM history").fetchall()
    con.close()
    return rows

@app.get("/export")
def export_excel():
    con = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM history", con)
    con.close()
    file = "export.xlsx"
    df.to_excel(file, index=False)
    return FileResponse(file, filename="ai_data_entry_export.xlsx")
