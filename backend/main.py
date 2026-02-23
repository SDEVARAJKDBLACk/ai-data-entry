from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests, pandas as pd, sqlite3, os, json
from datetime import datetime

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_FILE = "history.db"
EXPORT_FILE = "export.xlsx"

app = FastAPI(title="AI Data Entry Enterprise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DB =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_text TEXT,
        structured_json TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def save_history(raw, structured):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (raw_text, structured_json, created_at) VALUES (?,?,?)",
        (raw, json.dumps(structured), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ================= AI =================
def call_openai_structured(prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    schema_prompt = f"""
Return ONLY valid JSON in this exact schema:

{{
  "fields": [{{"field": "...", "value": "..."}}],
  "core_fields": {{}},
  "custom_fields": {{}}
}}

Rules:
- Detect unlimited fields
- Map values correctly
- Auto-create missing fields
- Core fields must include: name, phone, email, address, dob, gender, company, amount, date, id, account, city, state, country, zip, product, invoice, tax, total
- JSON only, no text, no explanation

DATA:
{prompt}
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a structured data extraction engine."},
            {"role": "user", "content": schema_prompt}
        ]
    }

    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
    data = r.json()
    return data["choices"][0]["message"]["content"]

# ================= API =================

@app.get("/")
def root():
    return {"status": "AI Data Entry Enterprise Backend Running"}

@app.post("/analyze")
async def analyze_data(payload: dict):
    raw_text = payload.get("text", "")

    ai_response = call_openai_structured(raw_text)

    try:
        structured = json.loads(ai_response)
    except:
        structured = {
            "fields": [],
            "core_fields": {},
            "custom_fields": {},
            "raw_ai_output": ai_response
        }

    save_history(raw_text, structured)

    return {
        "success": True,
        "structured": structured
    }

@app.get("/history")
def history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, raw_text, structured_json, created_at FROM history ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "raw_text": r[1],
            "structured": json.loads(r[2]),
            "created_at": r[3]
        })

    return data

@app.get("/export")
def export_excel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT structured_json FROM history")
    rows = c.fetchall()
    conn.close()

    records = []

    for r in rows:
        js = json.loads(r[0])

        row = {}
        for f in js.get("fields", []):
            row[f["field"]] = f["value"]

        for k,v in js.get("core_fields", {}).items():
            row[k] = v

        for k,v in js.get("custom_fields", {}).items():
            row[k] = v

        records.append(row)

    if not records:
        df = pd.DataFrame([{"status": "no data"}])
    else:
        df = pd.DataFrame(records)

    df.to_excel(EXPORT_FILE, index=False)
    return FileResponse(EXPORT_FILE, filename="ai_data_entry_export.xlsx")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode(errors="ignore")

    ai_response = call_openai_structured(text)

    try:
        structured = json.loads(ai_response)
    except:
        structured = {
            "fields": [],
            "core_fields": {},
            "custom_fields": {},
            "raw_ai_output": ai_response
        }

    save_history(text, structured)

    return {"success": True, "structured": structured}

@app.post("/ocr")
def cloud_ocr_stub():
    return {"status": "OCR not enabled (cloud OCR phase next)"}
