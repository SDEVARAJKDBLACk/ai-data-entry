import os, re, io, json, uuid, datetime
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Optional libs (safe import)
try:
    import pytesseract
    from PIL import Image
except:
    pytesseract = None
    Image = None

try:
    import PyPDF2
except:
    PyPDF2 = None

try:
    import docx
except:
    docx = None

# ---------------- APP INIT ----------------

app = FastAPI(title="AI Data Entry Enterprise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MEMORY DB ----------------

HISTORY = []
FIELD_MEMORY = {}      # auto learning
PATTERN_MEMORY = {}    # pattern learning

# ---------------- NLP CORE ----------------

NAME_REGEX = re.compile(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b")
PHONE_REGEX = re.compile(r"\b[6-9]\d{9}\b")
EMAIL_REGEX = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
AMOUNT_REGEX = re.compile(r"\b\d{3,}\b")
DATE_REGEX = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
PIN_REGEX = re.compile(r"\b\d{6}\b")

# ---------------- AI FIELD ENGINE ----------------

def ai_extract(text:str)->Dict:
    data = {}

    names = NAME_REGEX.findall(text)
    phones = PHONE_REGEX.findall(text)
    emails = EMAIL_REGEX.findall(text)
    amounts = AMOUNT_REGEX.findall(text)
    dates = DATE_REGEX.findall(text)
    pins = PIN_REGEX.findall(text)

    # filtering logic
    human_names = [n for n in names if len(n.split())<=3]

    salary = []
    amount = []
    for a in amounts:
        if int(a) > 10000:
            salary.append(a)
        else:
            amount.append(a)

    data["Name"] = list(set(human_names))
    data["Phone"] = list(set(phones))
    data["Email"] = list(set(emails))
    data["Salary"] = list(set(salary))
    data["Amount"] = list(set(amount))
    data["Date"] = list(set(dates))
    data["Pincode"] = list(set(pins))

    # auto learning
    for k,v in data.items():
        if k not in FIELD_MEMORY:
            FIELD_MEMORY[k] = set()
        for item in v:
            FIELD_MEMORY[k].add(item)

    return data

# ---------------- FILE PARSERS ----------------

def read_pdf(file:bytes):
    if not PyPDF2: return ""
    reader = PyPDF2.PdfReader(io.BytesIO(file))
    text = ""
    for p in reader.pages:
        text += p.extract_text() or ""
    return text

def read_docx(file:bytes):
    if not docx: return ""
    d = docx.Document(io.BytesIO(file))
    return "\n".join([p.text for p in d.paragraphs])

def read_image(file:bytes):
    if not pytesseract or not Image: return ""
    img = Image.open(io.BytesIO(file))
    return pytesseract.image_to_string(img)

# ---------------- FRONTEND UI ----------------

HTML_UI = """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry – Automated Data Worker</title>
<style>
body{margin:0;font-family:Arial;background:#0b1220;color:white}
.container{max-width:1200px;margin:auto;padding:20px}
.card{background:#121b2f;border-radius:12px;padding:20px;margin-bottom:20px}
textarea,input{width:100%;padding:10px;border-radius:8px;border:none;margin:5px 0}
button{padding:10px 15px;border-radius:8px;border:none;cursor:pointer}
.btn{background:#00e0ff;color:black}
.btn2{background:#6c5ce7;color:white}
.table{width:100%;border-collapse:collapse}
th,td{border-bottom:1px solid #333;padding:8px;text-align:left}
</style>
</head>
<body>
<div class="container">
<h2>AI Data Entry – Automated Data Worker</h2>

<div class="card">
<input type="file" id="file">
<textarea id="text" rows="8" placeholder="Enter or paste input"></textarea>
<button class="btn" onclick="analyze()">Analyze</button>
<button class="btn2" onclick="clearAll()">Clear</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<table class="table">
<thead><tr><th>Field</th><th>Values</th></tr></thead>
<tbody id="result"></tbody>
</table>
</div>

<div class="card">
<h3>+ Custom Fields</h3>
<input id="cf_name" placeholder="Field name">
<input id="cf_val" placeholder="Value">
<button class="btn" onclick="addCustom()">Add</button>
</div>

<div class="card">
<h3>Last 10 Analysis</h3>
<ul id="history"></ul>
</div>

</div>

<script>
async function analyze(){
    let text = document.getElementById("text").value;
    let file = document.getElementById("file").files[0];
    let fd = new FormData();
    fd.append("text",text);
    if(file) fd.append("file",file);

    let r = await fetch("/analyze",{method:"POST",body:fd});
    let j = await r.json();

    let res = document.getElementById("result");
    res.innerHTML="";
    for(let k in j.data){
        let tr = document.createElement("tr");
        tr.innerHTML = `<td>${k}</td><td>${j.data[k].join(", ")}</td>`;
        res.appendChild(tr);
    }

    let h = document.getElementById("history");
    h.innerHTML="";
    j.history.forEach(x=>{
        let li=document.createElement("li");
        li.innerText=x;
        h.appendChild(li);
    })
}

function clearAll(){
    document.getElementById("text").value="";
    document.getElementById("result").innerHTML="";
}

function addCustom(){
    let n=document.getElementById("cf_name").value;
    let v=document.getElementById("cf_val").value;
    if(!n||!v) return;
    let res=document.getElementById("result");
    let tr=document.createElement("tr");
    tr.innerHTML=`<td>${n}</td><td>${v}</td>`;
    res.appendChild(tr);
}
</script>
</body>
</html>
"""

# ---------------- ROUTES ----------------

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_UI

@app.post("/analyze")
async def analyze(text:str=Form(""), file:UploadFile=File(None)):
    content = text

    if file:
        raw = await file.read()
        if file.filename.lower().endswith(".pdf"):
            content += read_pdf(raw)
        elif file.filename.lower().endswith(".docx"):
            content += read_docx(raw)
        elif file.filename.lower().endswith((".png",".jpg",".jpeg")):
            content += read_image(raw)
        else:
            try:
                content += raw.decode()
            except:
                pass

    data = ai_extract(content)

    ts = datetime.datetime.utcnow().isoformat()
    HISTORY.append(ts)
    if len(HISTORY)>10:
        HISTORY.pop(0)

    return {
        "data": data,
        "history": HISTORY
    }

# ---------------- RUN ----------------
# uvicorn backend.main:app --host 0.0.0.0 --port 10000
