# ================= ENTERPRISE AI DATA ENTRY PLATFORM =================
# SINGLE FILE FULLSTACK PRODUCTION VERSION
# OCR + PDF + WORD + AI TRAINING + AUTO FIELD LEARNING + OFFLINE NLP
# ====================================================================

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import re, io, os, json
from datetime import datetime
import pandas as pd

# Optional libs (graceful fallback)
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False

# ---------------- CONFIG ----------------
MEMORY_FILE = "field_memory.json"
MODEL_FILE = "ai_model.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE,"w") as f:
        json.dump({},f)

if not os.path.exists(MODEL_FILE):
    with open(MODEL_FILE,"w") as f:
        json.dump({"patterns":{}},f)

# ---------------- APP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY = []

# ---------------- MEMORY ----------------
def load_memory():
    with open(MEMORY_FILE,"r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_FILE,"w") as f:
        json.dump(mem,f,indent=2)

def load_model():
    with open(MODEL_FILE,"r") as f:
        return json.load(f)

def save_model(model):
    with open(MODEL_FILE,"w") as f:
        json.dump(model,f,indent=2)

# ---------------- FILE EXTRACT ----------------
def extract_from_file(file: UploadFile, raw: bytes):
    name = file.filename.lower()

    # IMAGE OCR
    if name.endswith((".png",".jpg",".jpeg")) and OCR_AVAILABLE:
        img = Image.open(io.BytesIO(raw))
        return pytesseract.image_to_string(img)

    # PDF
    if name.endswith(".pdf") and PDF_AVAILABLE:
        text = ""
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for p in pdf.pages:
                text += p.extract_text() or ""
        if text.strip()=="" and OCR_AVAILABLE:
            # OCR fallback
            for p in pdf.pages:
                img = p.to_image().original
                text += pytesseract.image_to_string(img)
        return text

    # DOCX
    if name.endswith(".docx") and DOCX_AVAILABLE:
        doc = Document(io.BytesIO(raw))
        return "\n".join([p.text for p in doc.paragraphs])

    # TXT
    try:
        return raw.decode()
    except:
        return ""

# ---------------- AI CORE ----------------
def ai_extract(text:str):
    mem = load_memory()
    model = load_model()
    data = {}
    t = text.lower()

    # ---------------- BASIC NLP ----------------
    # Names
    names = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", text)
    clean_names = [n for n in names if len(n.split())<=3]
    if clean_names:
        data["Name"] = ", ".join(set(clean_names))

    # Age
    age = re.findall(r"\b(\d{1,3})\s*years?\b", t)
    if age: data["Age"]=", ".join(set(age))

    # Gender
    g=[]
    if "male" in t: g.append("male")
    if "female" in t: g.append("female")
    if g: data["Gender"]=", ".join(set(g))

    # Phone
    phones = re.findall(r"\b\d{10}\b", text)
    if phones: data["Phone"]=", ".join(set(phones))

    # Email
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if emails: data["Email"]=", ".join(set(emails))

    # Pincode
    pin = re.findall(r"\b\d{6}\b", text)
    if pin: data["Pincode"]=", ".join(set(pin))

    # Date
    dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", text)
    if dates: data["Date"]=", ".join(set(dates))

    # Amount / Salary
    nums = re.findall(r"\b\d{3,}\b", text)
    if nums:
        data["Amount"]=", ".join(set(nums))
        data["Salary"]=", ".join(set(nums))

    # Product
    products = re.findall(r"\b(laptop|mobile|phone|computer|tablet|tv)\b", t)
    if products:
        data["Product Name"]=", ".join(set(products))

    # Company
    companies = re.findall(r"\b(infosys|tcs|google|amazon|wipro|hcl|microsoft)\b", t)
    if companies:
        data["Company"]=", ".join(set(companies))

    # Location
    cities = re.findall(r"\b(chennai|madurai|coimbatore|bangalore|delhi|mumbai)\b", t)
    if cities:
        data["City"]=", ".join(set(cities))
    if "india" in t:
        data["Country"]="India"

    # ---------------- AUTO FIELD LEARNING ----------------
    words = re.findall(r"\b[a-zA-Z_]{3,}\b", t)
    for w in words:
        if w not in mem:
            mem[w]=1
        else:
            mem[w]+=1

    save_memory(mem)

    # ---------------- PATTERN LEARNING ----------------
    for k,v in data.items():
        if k not in model["patterns"]:
            model["patterns"][k]=[]
        if v not in model["patterns"][k]:
            model["patterns"][k].append(v)

    save_model(model)

    return data

# ---------------- API ----------------
@app.post("/analyze")
async def analyze(file: UploadFile = File(None), text: str = ""):
    content = text
    if file:
        raw = await file.read()
        content = extract_from_file(file, raw)

    result = ai_extract(content)
    HISTORY.append({"time":str(datetime.now()),"data":result})
    return {"data":result,"history":HISTORY[-10:]}

@app.post("/export")
async def export_excel(payload: dict):
    df = pd.DataFrame(list(payload.items()), columns=["Field","Value"])
    stream = io.BytesIO()
    df.to_excel(stream,index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=extracted.xlsx"})

# ---------------- FRONTEND ----------------
@app.get("/", response_class=HTMLResponse)
def home():
    return open("main_ui.html","r").read() if os.path.exists("main_ui.html") else """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry – Automated Data Worker</title>
<style>
body{margin:0;font-family:Arial;background:#050b1e;color:white;}
.container{max-width:1000px;margin:auto;padding:20px;}
.card{background:rgba(255,255,255,0.05);border-radius:15px;padding:20px;margin-bottom:20px;}
textarea{width:100%;height:220px;border-radius:10px;padding:15px;}
button{padding:10px 20px;border-radius:8px;border:none;margin:5px;font-weight:bold;cursor:pointer;}
.btn1{background:#00c2ff;} .btn2{background:#6c63ff;color:white;} .btn3{background:#5a4bff;color:white;}
table{width:100%;border-collapse:collapse;}
th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,0.1);}
</style>
</head>
<body>
<div class="container">
<h2>AI Data Entry – Automated Data Worker</h2>
<div class="card">
<input type="file" id="file"><br><br>
<textarea id="inputText" placeholder="Enter or paste input"></textarea><br>
<button class="btn1" onclick="analyze()">Analyze</button>
<button class="btn2" onclick="clearAll()">Clear</button>
<button class="btn3" onclick="exportExcel()">Export Excel</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<table id="table"><tr><th>Field</th><th>Value</th></tr></table>
</div>

<div class="card">
<h3>+ Custom Fields</h3>
<input id="cf" placeholder="Field">
<input id="cv" placeholder="Value">
<button onclick="addCustom()">Add</button>
</div>
</div>

<script>
let extracted={}
async function analyze(){
const file=document.getElementById("file").files[0];
const text=document.getElementById("inputText").value;
let f=new FormData();
if(file) f.append("file",file);
f.append("text",text);
const r=await fetch("/analyze",{method:"POST",body:f});
const d=await r.json();
extracted=d.data; render();
}
function render(){
let t=document.getElementById("table");
t.innerHTML="<tr><th>Field</th><th>Value</th></tr>";
for(let k in extracted){
t.innerHTML+=`<tr><td>${k}</td><td>${extracted[k]}</td></tr>`;
}}
function clearAll(){
document.getElementById("inputText").value="";
document.getElementById("table").innerHTML="<tr><th>Field</th><th>Value</th></tr>";
extracted={};
}
function addCustom(){
let f=document.getElementById("cf").value;
let v=document.getElementById("cv").value;
if(f&&v){extracted[f]=v;render();}
}
async function exportExcel(){
const r=await fetch("/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(extracted)});
const b=await r.blob(); const u=URL.createObjectURL(b);
const a=document.createElement("a"); a.href=u; a.download="extracted.xlsx"; a.click();
}
</script>
</body>
</html>
"""

# ---------------- RUN ----------------
# uvicorn main:app --host 0.0.0.0 --port 10000
