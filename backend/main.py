from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn, re, json, io
import pandas as pd
from datetime import datetime

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY = []

# ---------- AI EXTRACTION ENGINE ----------
def ai_extract(text: str):
    data = {}

    names = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b", text)
    phones = re.findall(r"\b[6-9]\d{9}\b", text)
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    ages = re.findall(r"\b(\d{1,3})\s*years?\s*old\b", text.lower())
    amounts = re.findall(r"\b\d{3,}\b", text)

    gender = []
    if re.search(r"\bmale\b", text.lower()):
        gender.append("male")
    if re.search(r"\bfemale\b", text.lower()):
        gender.append("female")

    address = re.findall(r"\d{1,4},?\s*\w+\s*(street|st|road|rd|nagar|colony|layout)", text.lower())
    city = re.findall(r"\b(chennai|madurai|coimbatore|trichy|salem|vellore|erode)\b", text.lower())
    state = re.findall(r"\b(tamil nadu|kerala|karnataka|andhra pradesh)\b", text.lower())
    country = re.findall(r"\b(india|usa|uk|canada)\b", text.lower())

    if names: data["Name"] = list(set(names))
    if ages: data["Age"] = list(set(ages))
    if gender: data["Gender"] = list(set(gender))
    if phones: data["Phone"] = list(set(phones))
    if emails: data["Email"] = list(set(emails))
    if address: data["Address"] = list(set(address))
    if city: data["City"] = list(set(city))
    if state: data["State"] = list(set(state))
    if country: data["Country"] = list(set(country))
    if amounts: data["Amount"] = list(set(amounts))

    return data

# ---------- API ----------
@app.post("/analyze")
async def analyze(text: str = Form(...)):
    extracted = ai_extract(text)

    record = {
        "time": datetime.now().isoformat(),
        "input": text,
        "data": extracted
    }

    HISTORY.append(record)
    if len(HISTORY) > 10:
        HISTORY.pop(0)

    return {"status": "success", "data": extracted}

@app.get("/history")
def get_history():
    return HISTORY[::-1]

@app.post("/custom-field")
async def add_custom_field(field: str = Form(...), value: str = Form(...)):
    if not HISTORY:
        return {"status": "error", "msg": "No analysis found"}

    if field in HISTORY[-1]["data"]:
        HISTORY[-1]["data"][field].append(value)
    else:
        HISTORY[-1]["data"][field] = [value]

    return {"status": "success", "data": HISTORY[-1]["data"]}

@app.get("/export")
def export_excel():
    if not HISTORY:
        return {"status": "error", "msg": "No data to export"}

    latest = HISTORY[-1]["data"]

    rows = []
    for k,v in latest.items():
        rows.append({"Field": k, "Value": ", ".join(v)})

    df = pd.DataFrame(rows)

    file_path = "export.xlsx"
    df.to_excel(file_path, index=False)

    return FileResponse(file_path, filename="ai_data_export.xlsx")

# ---------- RUN ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
