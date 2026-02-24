import re, io, json, os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime
import pandas as pd
from PIL import Image
import pytesseract
import pdfplumber
from docx import Document
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY=[]
MODEL_PATH="ai_model.pkl"
MEMORY_PATH="field_memory.json"

# ---------- NLP ----------
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = spacy.blank("en")

# ---------- MEMORY ----------
if not os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH,"w") as f:
        json.dump({},f)

def load_memory():
    with open(MEMORY_PATH,"r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_PATH,"w") as f:
        json.dump(mem,f,indent=2)

# ---------- FILE READERS ----------
def read_pdf(file):
    text=""
    with pdfplumber.open(io.BytesIO(file)) as pdf:
        for p in pdf.pages:
            if p.extract_text():
                text+=p.extract_text()+"\n"
    return text

def read_docx(file):
    doc=Document(io.BytesIO(file))
    return "\n".join([p.text for p in doc.paragraphs])

def read_image(file):
    img=Image.open(io.BytesIO(file))
    return pytesseract.image_to_string(img)

# ---------- CORE AI ENGINE ----------
def ai_engine(text):
    memory=load_memory()
    data={}

    doc=nlp(text)

    # NLP ENTITY EXTRACTION
    for ent in doc.ents:
        label=ent.label_
        val=ent.text.strip()
        if label not in data:
            data[label]=[]
        data[label].append(val)

    # PATTERN LEARNING
    patterns={
        "Phone":r"\b[6-9]\d{9}\b",
        "Email":r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "Amount":r"\b\d{3,}\b",
        "Age":r"\b(\d{1,3})\s*years?\s*old\b"
    }

    for field,pat in patterns.items():
        found=re.findall(pat,text,re.IGNORECASE)
        if found:
            data.setdefault(field,[]).extend(found)

    # UNLIMITED FIELD DETECTION (AUTO SCHEMA)
    lines=text.split("\n")
    for l in lines:
        if ":" in l:
            k,v=l.split(":",1)
            key=k.strip().title()
            val=v.strip()
            if key and val:
                data.setdefault(key,[]).append(val)

    # FIELD AUTO LEARNING
    for k,v in data.items():
        if k not in memory:
            memory[k]={"patterns":[],"count":0}
        memory[k]["count"]+=len(v)
        for val in v:
            memory[k]["patterns"].append(val)

    save_memory(memory)
    return data

# ---------- API ----------
@app.post("/analyze")
async def analyze(text: str = Form(None), file: UploadFile = File(None)):
    content=""

    if file:
        raw=await file.read()
        name=file.filename.lower()
        if name.endswith(".pdf"):
            content=read_pdf(raw)
        elif name.endswith(".docx"):
            content=read_docx(raw)
        elif name.endswith((".png",".jpg",".jpeg")):
            content=read_image(raw)
        else:
            content=raw.decode(errors="ignore")
    else:
        content=text

    extracted=ai_engine(content)

    rec={
        "time":datetime.now().isoformat(),
        "input":content,
        "data":extracted
    }
    HISTORY.append(rec)
    if len(HISTORY)>20:
        HISTORY.pop(0)

    return {"status":"success","data":extracted}

@app.get("/history")
def history():
    return HISTORY[::-1]

@app.post("/custom-field")
async def custom_field(field: str = Form(...), value: str = Form(...)):
    if not HISTORY:
        return {"status":"error","msg":"No session"}
    HISTORY[-1]["data"].setdefault(field,[]).append(value)
    return {"status":"success","data":HISTORY[-1]["data"]}

@app.get("/export")
def export_excel():
    if not HISTORY:
        return {"status":"error","msg":"No data"}
    latest=HISTORY[-1]["data"]
    rows=[]
    for k,v in latest.items():
        rows.append({"Field":k,"Value":", ".join(v)})
    df=pd.DataFrame(rows)
    path="export.xlsx"
    df.to_excel(path,index=False)
    return FileResponse(path,filename="ai_export.xlsx")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app",host="0.0.0.0",port=8000)
