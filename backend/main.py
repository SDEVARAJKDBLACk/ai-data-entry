from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import re, io, json, os
from datetime import datetime
from typing import Dict, List
import pandas as pd

app = FastAPI()

# -------------------- STORAGE --------------------
HISTORY = []
LEARNING_DB = {}
CUSTOM_FIELDS = []

# -------------------- NLP / AI ENGINE --------------------
def extract_fields(text: str):
    fields = {}

    # --- Name extraction (human names only) ---
    name_pattern = r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b"
    names = re.findall(name_pattern, text)
    if names:
        fields["name"] = list(set(names))

    # --- Amount extraction ---
    amount_pattern = r"(₹\s?\d+(?:,\d+)*(?:\.\d+)?|\$\s?\d+(?:,\d+)*(?:\.\d+)?|\d+(?:,\d+)*(?:\.\d+)?\s?(?:INR|USD|rupees|rs|salary|amount))"
    amounts = re.findall(amount_pattern, text, re.IGNORECASE)
    if amounts:
        fields["amount"] = list(set(amounts))

    # --- Email ---
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if emails:
        fields["email"] = list(set(emails))

    # --- Phone ---
    phones = re.findall(r"\b\d{10}\b", text)
    if phones:
        fields["phone"] = list(set(phones))

    # --- Dates ---
    dates = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
    if dates:
        fields["date"] = list(set(dates))

    # --- Generic key:value detection ---
    kv_pattern = r"([A-Za-z ]+)\s*[:\-]\s*([A-Za-z0-9 ₹$.,/-]+)"
    kvs = re.findall(kv_pattern, text)
    for k,v in kvs:
        k = k.strip().lower()
        if k not in fields:
            fields[k] = v.strip()

    return fields

# -------------------- LEARNING ENGINE --------------------
def learn_fields(fields: Dict):
    for k,v in fields.items():
        if k not in LEARNING_DB:
            LEARNING_DB[k] = []
        LEARNING_DB[k].append(v)

# -------------------- FRONTEND UI --------------------
HTML_UI = """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry Enterprise</title>
<style>
body{font-family:Arial;background:#f4f6fb;margin:0;padding:0}
.header{background:#1e293b;color:white;padding:15px;text-align:center;font-size:22px}
.container{padding:20px}
.card{background:white;padding:20px;border-radius:10px;box-shadow:0 0 10px #ddd;margin-bottom:20px}
button{padding:10px 15px;border:none;background:#2563eb;color:white;border-radius:6px;cursor:pointer}
input,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:6px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:8px;text-align:left}
th{background:#f1f5f9}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
</style>
</head>
<body>

<div class="header">AI DATA ENTRY ENTERPRISE PLATFORM</div>

<div class="container">

<div class="card">
<h3>Upload File</h3>
<input type="file" id="file"/>
<button onclick="upload()">Upload & Analyze</button>
</div>

<div class="card">
<h3>Text Input</h3>
<textarea id="text" rows="6"></textarea>
<button onclick="analyzeText()">Analyze Text</button>
</div>

<div class="card">
<h3>Custom Field</h3>
<div class="grid">
<input id="cf_name" placeholder="Field Name"/>
<input id="cf_value" placeholder="Field Value"/>
</div>
<button onclick="addField()">Add Field</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<table id="table">
<tr><th>Field</th><th>Value</th></tr>
</table>
<button onclick="exportExcel()">Export Excel</button>
</div>

</div>

<script>
function render(data){
 let t=document.getElementById("table");
 t.innerHTML="<tr><th>Field</th><th>Value</th></tr>";
 for(let k in data){
   let v=data[k];
   if(Array.isArray(v)) v=v.join(", ");
   t.innerHTML+=`<tr><td>${k}</td><td>${v}</td></tr>`;
 }
}

async function analyzeText(){
 let text=document.getElementById("text").value;
 let res=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
 let data=await res.json();
 render(data.fields);
}

async function upload(){
 let f=document.getElementById("file").files[0];
 let fd=new FormData();
 fd.append("file",f);
 let res=await fetch('/upload',{method:'POST',body:fd});
 let data=await res.json();
 render(data.fields);
}

async function addField(){
 let name=document.getElementById("cf_name").value;
 let value=document.getElementById("cf_value").value;
 let res=await fetch('/custom',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,value})});
 let data=await res.json();
 render(data.fields);
}

async function exportExcel(){
 window.location='/export';
}
</script>

</body>
</html>
"""

# -------------------- ROUTES --------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_UI

@app.post("/analyze")
async def analyze(data: dict):
    text = data.get("text","")
    fields = extract_fields(text)
    learn_fields(fields)
    HISTORY.append({"time":str(datetime.now()),"fields":fields})
    return {"fields":fields}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode(errors="ignore")
    except:
        text = str(content)
    fields = extract_fields(text)
    learn_fields(fields)
    HISTORY.append({"time":str(datetime.now()),"fields":fields})
    return {"fields":fields}

@app.post("/custom")
async def custom(data: dict):
    name = data["name"]
    value = data["value"]
    CUSTOM_FIELDS.append({name:value})
    merged = {}
    for h in HISTORY[-1:]:
        merged.update(h["fields"])
    merged[name]=value
    return {"fields":merged}

@app.get("/export")
def export():
    if not HISTORY:
        return JSONResponse({"error":"No data"})
    rows=[]
    for h in HISTORY:
        rows.append(h["fields"])
    df=pd.DataFrame(rows)
    stream=io.BytesIO()
    df.to_excel(stream,index=False)
    stream.seek(0)
    return StreamingResponse(stream,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=ai_data_entry.xlsx"})
