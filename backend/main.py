from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, re, json, io
from typing import List
from PIL import Image
import pytesseract
from docx import Document
import pdfplumber

app = FastAPI(title="AI Data Entry Enterprise System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- AI NLP ENGINE ---------------- #

NAME_REGEX = r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b"
PHONE_REGEX = r"\b[6-9]\d{9}\b"
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
DATE_REGEX = r"\b\d{2}/\d{2}/\d{4}\b"
AMOUNT_REGEX = r"\b\d{3,7}\b"

def ai_extract(text: str):
    names = list(set(re.findall(NAME_REGEX, text)))
    phones = re.findall(PHONE_REGEX, text)
    emails = re.findall(EMAIL_REGEX, text)
    dates = re.findall(DATE_REGEX, text)
    amounts = re.findall(AMOUNT_REGEX, text)

    products = []
    if "laptop" in text.lower():
        products.append("Laptop")
    if "mobile" in text.lower():
        products.append("Mobile Phone")

    address_fields = {}
    if "street" in text.lower(): address_fields["street"] = "Detected"
    if "nagar" in text.lower(): address_fields["area"] = "Detected"
    if "chennai" in text.lower(): address_fields["city"] = "Chennai"
    if "tamil nadu" in text.lower(): address_fields["state"] = "Tamil Nadu"
    if "india" in text.lower(): address_fields["country"] = "India"

    structured = {
        "persons": names,
        "phones": phones,
        "emails": emails,
        "dates": dates,
        "amounts": amounts,
        "products": products,
        "address": address_fields
    }

    return structured

# ---------------- FILE PROCESSING ---------------- #

def extract_text_from_file(file: UploadFile):
    content = ""
    if file.filename.endswith(".txt"):
        content = file.file.read().decode()

    elif file.filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file.file.read())) as pdf:
            for page in pdf.pages:
                content += page.extract_text() or ""

    elif file.filename.endswith(".docx"):
        doc = Document(io.BytesIO(file.file.read()))
        for para in doc.paragraphs:
            content += para.text + "\n"

    elif file.filename.endswith((".png",".jpg",".jpeg")):
        image = Image.open(io.BytesIO(file.file.read()))
        content = pytesseract.image_to_string(image)

    return content

# ---------------- API ---------------- #

@app.post("/analyze")
async def analyze(text: str = Form(None), file: UploadFile = File(None)):
    raw_text = ""

    if text:
        raw_text += text

    if file:
        raw_text += "\n" + extract_text_from_file(file)

    result = ai_extract(raw_text)

    return JSONResponse({
        "raw_text": raw_text,
        "extracted": result
    })

# ---------------- UI ---------------- #

@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry Enterprise</title>
<style>
body{font-family:Arial;background:#f4f6f9;margin:0;padding:0}
.container{max-width:1200px;margin:auto;padding:20px}
h1{text-align:center}
.box{background:#fff;padding:15px;border-radius:8px;margin-bottom:15px}
textarea{width:100%;height:150px}
button{padding:10px 20px;background:#4CAF50;color:#fff;border:none;border-radius:5px;cursor:pointer}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{border:1px solid #ddd;padding:8px;text-align:left}
th{background:#eee}
</style>
</head>
<body>
<div class="container">
<h1>AI Data Entry Web Application</h1>

<div class="box">
<h3>Input Data</h3>
<textarea id="text"></textarea><br><br>
<input type="file" id="file"><br><br>
<button onclick="analyze()">Analyze</button>
</div>

<div class="box">
<h3>Extracted Structured Data</h3>
<pre id="json"></pre>
</div>

<div class="box">
<h3>Table View</h3>
<table id="table"></table>
</div>

</div>

<script>
async function analyze(){
    const fd = new FormData();
    fd.append("text",document.getElementById("text").value);
    const file=document.getElementById("file").files[0];
    if(file) fd.append("file",file);

    const res = await fetch("/analyze",{method:"POST",body:fd});
    const data = await res.json();

    document.getElementById("json").innerText = JSON.stringify(data.extracted,null,2);

    let table = "<tr><th>Field</th><th>Values</th></tr>";
    for(let key in data.extracted){
        table += `<tr><td>${key}</td><td>${JSON.stringify(data.extracted[key])}</td></tr>`;
    }
    document.getElementById("table").innerHTML = table;
}
</script>
</body>
</html>
"""

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
