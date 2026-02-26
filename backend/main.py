from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import google.generativeai as genai
import os, json, io
import pandas as pd
from datetime import datetime
from PIL import Image
import PyPDF2
import docx

# ---------------- CONFIG ----------------
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

app = FastAPI()
history_store = []
last_result = {}

# ---------------- FILE READERS ----------------
def read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def read_docx(file):
    d = docx.Document(file)
    return "\n".join([p.text for p in d.paragraphs])

# ---------------- UI ----------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Data Entry Enterprise</title>
<style>
body{margin:0;font-family:Arial;background:#0f172a;color:white}
.container{max-width:1100px;margin:auto;padding:20px}
.card{background:#111827;border-radius:12px;padding:20px;margin-bottom:15px}
textarea,input{width:100%;padding:10px;border-radius:6px;border:none}
button{padding:10px 15px;border:none;border-radius:6px;margin:5px;cursor:pointer}
.btn1{background:#06b6d4}
.btn2{background:#6366f1}
.btn3{background:#22c55e}
table{width:100%;border-collapse:collapse}
td,th{border-bottom:1px solid #334155;padding:8px;text-align:left}
@media(max-width:600px){
table,thead,tbody,tr,td,th{font-size:12px}
}
</style>
</head>
<body>
<div class="container">

<h2>AI Data Entry – Automated Data Worker</h2>

<div class="card">
<input type="file" id="fileInput"><br><br>
<textarea id="textInput" rows="8" placeholder="Paste text / message / notes here..."></textarea><br>
<button class="btn1" onclick="analyze()">Analyze</button>
<button class="btn2" onclick="clearAll()">Clear</button>
<button class="btn3" onclick="exportExcel()">Export Excel</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<table id="resultTable">
<tr><th>Field</th><th>Value</th></tr>
</table>
</div>

<div class="card">
<h3>Custom Fields</h3>
<input id="cfield" placeholder="Field name">
<input id="cvalue" placeholder="Value">
<button onclick="addCustom()">Add</button>
</div>

<div class="card">
<h3>Last Analysis</h3>
<ul id="history"></ul>
</div>

</div>

<script>
async function analyze(){
    let fd = new FormData();
    let text = document.getElementById("textInput").value;
    let file = document.getElementById("fileInput").files[0];
    if(file){fd.append("file",file);}
    fd.append("text",text);

    let res = await fetch("/api/analyze",{method:"POST",body:fd});
    let data = await res.json();

    let table = document.getElementById("resultTable");
    table.innerHTML="<tr><th>Field</th><th>Value</th></tr>";

    for(let k in data){
        let row = `<tr><td>${k}</td><td>${JSON.stringify(data[k])}</td></tr>`;
        table.innerHTML+=row;
    }
    loadHistory();
}

function clearAll(){
    document.getElementById("textInput").value="";
    document.getElementById("fileInput").value="";
    document.getElementById("resultTable").innerHTML="<tr><th>Field</th><th>Value</th></tr>";
}

async function exportExcel(){
    window.open("/api/export","_blank");
}

function addCustom(){
    let f=document.getElementById("cfield").value;
    let v=document.getElementById("cvalue").value;
    let table=document.getElementById("resultTable");
    table.innerHTML+=`<tr><td>${f}</td><td>${v}</td></tr>`;
}

async function loadHistory(){
    let r=await fetch("/api/history");
    let d=await r.json();
    let h=document.getElementById("history");
    h.innerHTML="";
    d.forEach(i=>{h.innerHTML+=`<li>${i}</li>`})
}
</script>
</body>
</html>
"""

# ---------------- ANALYZE ----------------
@app.post("/api/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    content = ""

    if file:
        fname = file.filename.lower()
        if fname.endswith(".pdf"):
            content = read_pdf(file.file)
        elif fname.endswith(".docx"):
            content = read_docx(file.file)
        elif fname.endswith((".png",".jpg",".jpeg",".webp")):
            img = Image.open(file.file)
            response = model.generate_content([
                "Extract structured data from this image and return JSON",
                img
            ])
            raw = response.text.replace("```json","").replace("```","")
            data = json.loads(raw)
            last_result.update(data)
            history_store.append(datetime.now().isoformat())
            return JSONResponse(data)
        else:
            content = file.file.read().decode(errors="ignore")

    content = content + "\n" + text

    prompt = f"""
Extract structured enterprise data and return ONLY JSON.
Fields:
Persons (human names only)
PersonalDetails
AddressDetails
FinancialInfo
ProductDetails
Dates
TransactionDetails
Notes

Text:
{content}
"""

    response = model.generate_content(prompt)
    raw = response.text.replace("```json","").replace("```","")

    data = json.loads(raw)
    last_result.clear()
    last_result.update(data)

    history_store.append(datetime.now().isoformat())
    if len(history_store)>10:
        history_store.pop(0)

    return JSONResponse(data)

# ---------------- EXPORT ----------------
@app.get("/api/export")
def export_excel():
    if not last_result:
        df = pd.DataFrame([{"info":"No data"}])
    else:
        rows=[]
        for k,v in last_result.items():
            rows.append({"Field":k,"Value":json.dumps(v)})
        df = pd.DataFrame(rows)

    stream = io.BytesIO()
    df.to_excel(stream,index=False)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=ai_data_entry.xlsx"}
    )

# ---------------- HISTORY ----------------
@app.get("/api/history")
def history():
    return history_store
