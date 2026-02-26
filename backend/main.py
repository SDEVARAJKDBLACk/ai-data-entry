import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Gemini Configuration ---
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)
# Intha model name thaan unga connection error-ai fix pannirukku
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

# --- Memory Storage (For Render) ---
#
history_data = []
field_memory = []

# --- AI Logic ---
async def extract_ai_data(content, is_image=False, image_data=None):
    custom_str = ", ".join(field_memory)
    prompt = f"Extract Name, Phone, Email, Company, Amount, Date, and these custom fields: {custom_str}. Return ONLY JSON. Use 'N/A' if missing."
    
    try:
        response = model.generate_content([prompt, image_data]) if is_image else model.generate_content(f"{prompt}\nText: {content}")
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "Format Error"}
    except Exception as e:
        return {"Error": str(e)}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        content = text
        if file:
            f_bytes = await file.read()
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                res = await extract_ai_data("", True, Image.open(io.BytesIO(f_bytes)))
            else:
                if file.filename.endswith('.pdf'):
                    with pdfplumber.open(io.BytesIO(f_bytes)) as pdf:
                        content += "\n" + "".join([p.extract_text() or "" for p in pdf.pages])
                elif file.filename.endswith('.docx'):
                    doc = docx.Document(io.BytesIO(f_bytes))
                    content += "\n" + "\n".join([p.text for p in doc.paragraphs])
                res = await extract_ai_data(content)
        else:
            res = await extract_ai_data(content)

        if "Error" not in res:
            res['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_data.insert(0, res)
        return res
    except Exception as e:
        return {"Error": str(e)}

@app.post("/add_field")
async def add_field(data: dict):
    f = data.get("field")
    if f and f not in field_memory: field_memory.append(f)
    return {"status": "success"}

@app.get("/export_excel")
async def export():
    if not history_data: raise HTTPException(400, "No data")
    df = pd.DataFrame(history_data)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    out.seek(0)
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=data.xlsx"})

@app.get("/history")
async def get_history(): return history_data[:10]

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Data Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0b0f1a; color: #f1f5f9; }
            .glass { background: rgba(23, 32, 53, 0.9); border: 1px solid #2d3748; }
            .loader { border: 2px solid #1e293b; border-top: 2px solid #3b82f6; border-radius: 50%; width: 16px; height: 16px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <h1 class="text-3xl font-bold text-blue-500">AI DATA MASTER</h1>
                <button onclick="location.href='/export_excel'" class="bg-green-600 px-6 py-2 rounded-xl font-bold">Export Excel</button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <input type="file" id="fIn" class="mb-4 text-xs text-slate-500">
                        <textarea id="tIn" rows="5" class="w-full bg-slate-950 p-4 rounded-xl border border-slate-800 outline-none" placeholder="Paste data..."></textarea>
                        <button onclick="run()" id="btn" class="mt-4 bg-blue-600 px-8 py-3 rounded-xl font-bold flex gap-2">
                            <span id="bt">Analyze</span>
                            <div id="ld" class="loader hidden"></div>
                        </button>
                    </div>
                    <div id="res" class="glass p-6 rounded-3xl grid grid-cols-2 gap-4"></div>
                </div>
                <div class="space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-blue-400 font-bold mb-4">Custom Fields</h3>
                        <input type="text" id="nf" class="w-full bg-slate-900 p-2 rounded mb-2 border border-slate-700" placeholder="GST, Bill No, etc.">
                        <button onclick="addField()" class="w-full bg-indigo-600 py-2 rounded font-bold">Add Field</button>
                    </div>
                    <div id="hist" class="glass p-4 rounded-3xl space-y-2 h-80 overflow-y-auto"></div>
                </div>
            </div>
        </div>
        <script>
            async function run() {
                const b = document.getElementById('btn'); const l = document.getElementById('ld');
                b.disabled = true; l.classList.remove('hidden');
                const fd = new FormData();
                fd.append('text', document.getElementById('tIn').value);
                const file = document.getElementById('fIn').files[0];
                if(file) fd.append('file', file);

                try {
                    const res = await fetch('/analyze', { method: 'POST', body: fd });
                    const data = await res.json();
                    if(data.Error) alert(data.Error);
                    else {
                        document.getElementById('res').innerHTML = Object.entries(data).map(([k,v]) => 
                            k !== 'timestamp' ? `<div class='bg-slate-900 p-3 rounded-xl border border-slate-800'><b class='text-slate-500'>${k}</b><br>${v}</div>` : ''
                        ).join('');
                        loadHistory();
                    }
                } catch(e) { alert("Error!"); }
                finally { b.disabled = false; l.classList.add('hidden'); }
            }
            async function addField() {
                const field = document.getElementById('nf').value;
                if(!field) return;
                await fetch('/add_field', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({field}) });
                alert("Field Registered!"); document.getElementById('nf').value = '';
            }
            async function loadHistory() {
                const res = await fetch('/history'); const data = await res.json();
                document.getElementById('hist').innerHTML = data.map(h => `<div class='bg-slate-900 p-2 rounded text-[10px] border border-slate-800'><b>${h.Name || 'Record'}</b> - ${h.timestamp}</div>`).join('');
            }
            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """
