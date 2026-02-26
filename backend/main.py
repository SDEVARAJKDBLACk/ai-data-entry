import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    # Backup key from your screenshot to ensure it works immediately
    API_KEY = "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"

genai.configure(api_key=API_KEY)
# Using 'latest' to avoid the 404 models/gemini-1.5-flash not found error
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

# --- Memory Storage (Replacing JSON files for Render compatibility) ---
#
field_memory = [] # Custom fields
history_data = [] # Analysis results

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    base_fields = "Name, Age, Phone, Email, Company, Job Title, Amount, Date, Transaction Number"
    custom_str = ", ".join(field_memory)
    all_fields = f"{base_fields}, {custom_str}" if field_memory else base_fields
    
    prompt = f"""
    Extract data from the provided input in JSON format.
    Target Fields: {all_fields}
    Rules: 
    1. If a field is missing, use 'N/A'.
    2. Return ONLY a valid JSON object.
    """
    
    try:
        if is_image:
            response = model.generate_content([prompt, image_data])
        else:
            response = model.generate_content(f"{prompt}\nText Content: {content}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI did not return valid JSON"}
    except Exception as e:
        return {"Error": str(e)}

# --- API Routes ---

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        content = text
        extracted = {}
        
        if file:
            f_bytes = await file.read()
            f_name = file.filename.lower()
            if f_name.endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(io.BytesIO(f_bytes))
                extracted = await extract_data("", is_image=True, image_data=img)
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

@app.post("/add_field")
async def add_field(data: dict):
    new_field = data.get("field")
    if new_field and new_field not in field_memory:
        field_memory.append(new_field)
    return {"status": "success"}

@app.get("/export_excel")
async def export_excel():
    if not history_data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    df = pd.DataFrame(history_data)
    output = io.BytesIO()
    # openpyxl must be in requirements.txt
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ai_data_export.xlsx"}
    )

@app.get("/history")
async def get_history():
    return history_data[:15]

@app.get("/", response_class=HTMLResponse)
def home():
    # Frontend logic combining analysis, custom fields, and history
    #
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Master Worker Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0b0f1a; color: #f1f5f9; }
            .glass { background: rgba(23, 32, 53, 0.9); border: 1px solid #2d3748; }
            .loader { border: 3px solid #1a202c; border-top: 3px solid #3b82f6; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .hidden { display: none; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-3xl font-bold text-blue-400">AI ENTERPRISE WORKER</h1>
                <button onclick="window.location.href='/export_excel'" class="bg-green-600 hover:bg-green-500 px-6 py-2 rounded-xl font-bold transition">Export to Excel</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl shadow-xl">
                        <input type="file" id="fileIn" class="mb-4 text-sm text-slate-400">
                        <textarea id="textIn" rows="6" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:border-blue-500" placeholder="Paste data or text here..."></textarea>
                        <div class="flex gap-4 mt-4">
                            <button onclick="runAnalyze()" id="anBtn" class="bg-blue-600 px-10 py-3 rounded-xl font-bold flex items-center gap-2">
                                <span id="btnText">Analyze</span>
                                <div id="btnLoad" class="loader hidden"></div>
                            </button>
                            <button onclick="clearUI()" class="bg-slate-800 px-6 py-3 rounded-xl">Clear</button>
                        </div>
                    </div>
                    <div id="resTable" class="glass p-6 rounded-3xl grid grid-cols-1 md:grid-cols-2 gap-4">
                        <p class="text-slate-500 col-span-2 text-center italic">Results will appear here...</p>
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-cyan-400 font-bold mb-4">Add Custom Field</h3>
                        <p class="text-[10px] text-slate-500 mb-2">Teach AI to look for specific data</p>
                        <input type="text" id="newField" class="w-full bg-slate-900 border border-slate-800 p-2 rounded-lg mb-2" placeholder="Ex: GST Number">
                        <button onclick="addField()" class="w-full bg-indigo-600 py-2 rounded-lg font-bold">Register Field</button>
                    </div>
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="font-bold text-blue-300 mb-4 text-sm">🕒 Recent History</h3>
                        <div id="histList" class="space-y-3 max-h-80 overflow-y-auto pr-2"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function runAnalyze() {
                const text = document.getElementById('textIn').value;
                const file = document.getElementById('fileIn').files[0];
                if(!text && !file) return alert("Input required!");

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
                    renderResults(data);
                    loadHistory();
                } catch(e) {
                    alert("Analysis Failed: " + e.message);
                } finally {
                    btn.disabled = false; load.classList.add('hidden');
                    document.getElementById('btnText').innerText = "Analyze";
                }
            }

            function renderResults(data) {
                const container = document.getElementById('resTable');
                container.innerHTML = Object.entries(data).map(([k,v]) => {
                    if(k === 'timestamp') return '';
                    return `<div class="bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                        <div class="text-[10px] text-slate-500 font-bold uppercase mb-1">${k}</div>
                        <div class="text-blue-100">${v}</div>
                    </div>`;
                }).join('');
            }

            async function addField() {
                const val = document.getElementById('newField').value;
                if(!val) return;
                await fetch('/add_field', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({field: val})
                });
                alert("Field added: " + val);
                document.getElementById('newField').value = '';
            }

            async function loadHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `
                    <div class="bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs">
                        <div class="flex justify-between font-bold text-blue-400 mb-1">
                            <span>${h.Name || 'New Record'}</span>
                            <span class="text-slate-600">${h.timestamp.split(' ')[1]}</span>
                        </div>
                        <div class="text-slate-500 truncate">${h.Email || h.Company || ''}</div>
                    </div>
                `).join('');
            }

            function clearUI() {
                document.getElementById('textIn').value = '';
                document.getElementById('fileIn').value = '';
                document.getElementById('resTable').innerHTML = '<p class="text-slate-500 col-span-2 text-center italic">Results will appear here...</p>';
            }

            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
                                                 
