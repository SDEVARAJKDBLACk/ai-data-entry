import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
# Render Environment Variables-la GEMINI_API_KEY irukanum
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    # Backup for local testing (Unga screenshot key)
    API_KEY = "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- Memory Handling (File storage-ai remove panniten for Render) ---
field_memory = {}
history_data = []

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    custom_fields = ", ".join(field_memory.keys()) if field_memory else "None"
    
    prompt = f"""
    Extract data from the text in JSON format. 
    Fields: Name, Reference Name, Age, Gender, Phone, Email, City, State, Country, Pincode, 
    Company, Job Title, Salary, Amount, Product Name, Price, Quantity, Date, Transaction Number.
    Additional Custom Fields to look for: {custom_fields}
    
    Rules: 
    1. Multi-value fields should be comma-separated strings.
    2. If any data is missing, use 'N/A'.
    3. Return ONLY a valid JSON object.
    """
    
    try:
        if is_image:
            response = model.generate_content([prompt, image_data])
        else:
            response = model.generate_content(f"{prompt} \nText: {content}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI response was not in JSON format"}
    except Exception as e:
        return {"Error": str(e)}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    content = text
    extracted = {}
    
    try:
        if file:
            f_bytes = await file.read()
            f_name = file.filename.lower()
            if f_name.endswith(('.png', '.jpg', '.jpeg')):
                extracted = await extract_data("", is_image=True, image_data=Image.open(io.BytesIO(f_bytes)))
            else:
                if f_name.endswith('.pdf'):
                    with pdfplumber.open(io.BytesIO(f_bytes)) as pdf:
                        content += "\n" + "".join([p.extract_text() or "" for p in pdf.pages])
                elif f_name.endswith('.docx'):
                    doc = docx.Document(io.BytesIO(f_bytes))
                    content += "\n" + "\n".join([p.text for p in doc.paragraphs])
                extracted = await extract_data(content)
        else:
            extracted = await extract_data(content)

        if "Error" not in extracted:
            extracted['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_data.insert(0, extracted)
        
        return extracted
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

@app.get("/history")
async def get_history():
    return history_data[:10]

@app.get("/", response_class=HTMLResponse)
def home():
    # Frontend logic (Analyzing spinner + Table + History)
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Master Worker</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0b0f1a; color: #f1f5f9; font-family: sans-serif; }
            .glass { background: rgba(23, 32, 53, 0.9); border: 1px solid #2d3748; }
            .loader { border: 3px solid #1a202c; border-top: 3px solid #3b82f6; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .hidden { display: none; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div id="appBox" class="max-w-6xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-400 mb-8">AI DATA WORKER PRO</h1>
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl shadow-lg">
                        <input type="file" id="fileIn" class="mb-4 text-sm text-slate-400">
                        <textarea id="textIn" rows="8" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:border-blue-500" placeholder="Enter text here..."></textarea>
                        <div class="flex gap-4 mt-4">
                            <button onclick="runAnalyze()" id="anBtn" class="bg-blue-600 px-8 py-3 rounded-xl font-bold flex items-center gap-2">
                                <span id="btnText">Analyze</span>
                                <div id="btnLoad" class="loader hidden"></div>
                            </button>
                            <button onclick="clearAll()" class="bg-slate-800 px-6 py-3 rounded-xl">Clear</button>
                        </div>
                    </div>
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="font-bold text-blue-300 mb-4">Results</h3>
                        <div id="resTable" class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm"></div>
                    </div>
                </div>
                <div class="glass p-6 rounded-3xl h-fit">
                    <h3 class="font-bold text-cyan-400 mb-4">🕒 History</h3>
                    <div id="histList" class="space-y-2"></div>
                </div>
            </div>
        </div>
        <script>
            let currentData = {};
            async function runAnalyze() {
                const text = document.getElementById('textIn').value;
                const file = document.getElementById('fileIn').files[0];
                if(!text && !file) return alert("Empty input!");

                const btn = document.getElementById('anBtn');
                const load = document.getElementById('btnLoad');
                btn.disabled = true; load.classList.remove('hidden');
                document.getElementById('btnText').innerText = "Analyzing...";

                const fd = new FormData();
                fd.append('text', text);
                if(file) fd.append('file', file);

                try {
                    const res = await fetch('/analyze', { method: 'POST', body: fd });
                    const data = await res.json();
                    if(data.Error) throw new Error(data.Error);
                    currentData = data;
                    renderTable();
                    updateHistory();
                } catch(e) {
                    alert("Error analyzing: " + e.message);
                } finally {
                    btn.disabled = false; load.classList.add('hidden');
                    document.getElementById('btnText').innerText = "Analyze";
                }
            }
            function renderTable() {
                document.getElementById('resTable').innerHTML = Object.entries(currentData).map(([k,v]) => {
                    if(k==='timestamp') return '';
                    return `<div class="bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                        <div class="text-[10px] text-slate-500 font-bold uppercase">${k}</div>
                        <div class="text-blue-200">${v}</div>
                    </div>`;
                }).join('');
            }
            async function updateHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `
                    <div class="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs">
                        <div class="flex justify-between text-blue-400"><b>${h.Name || 'Record'}</b><span>${h.timestamp}</span></div>
                    </div>`).join('');
            }
            function clearAll() {
                document.getElementById('textIn').value = '';
                document.getElementById('fileIn').value = '';
                document.getElementById('resTable').innerHTML = '';
            }
            window.onload = updateHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
