import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
# Render-la 'GEMINI_API_KEY' environment variable-ah add panna marakatheenga
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("Warning: GEMINI_API_KEY not found!")

app = FastAPI()

# --- DB Persistence ---
USERS_FILE = "users.json"
HISTORY_FILE = "history.json"
MEMORY_FILE = "field_memory.json"

def load_db(file):
    if os.path.exists(file):
        with open(file, "r") as f: return json.load(f)
    return [] if "history" in file else {}

def save_db(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    memory = load_db(MEMORY_FILE)
    custom_fields = ", ".join(memory.keys()) if memory else "None"

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
        
        # Extracting JSON from AI response
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI response was not in JSON format"}
    except Exception as e:
        return {"Error": str(e)}

# --- Auth Routes ---
@app.post("/register")
async def register(data: dict):
    users = load_db(USERS_FILE)
    users[data['email']] = data
    save_db(USERS_FILE, users)
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    users = load_db(USERS_FILE)
    user = users.get(data['email'])
    if user and user['password'] == data['password']:
        return {"status": "success", "user": user}
    raise HTTPException(status_code=401)

# --- Analysis Routes ---
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

        # Learning & History
        if "Error" not in extracted:
            history = load_db(HISTORY_FILE)
            extracted['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history.insert(0, extracted)
            save_db(HISTORY_FILE, history[:10])
        
        return extracted
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

@app.post("/learn")
async def learn(data: dict):
    memory = load_db(MEMORY_FILE)
    memory[data['field']] = True
    save_db(MEMORY_FILE, memory)
    return {"status": "learned"}

@app.get("/history")
async def get_history():
    return load_db(HISTORY_FILE)

@app.get("/", response_class=HTMLResponse)
def home():
    # Frontend code follows the structure in your screenshot
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
        <div id="authBox" class="max-w-md mx-auto mt-20 glass p-8 rounded-3xl text-center shadow-2xl">
            <h2 id="authTitle" class="text-2xl font-bold mb-6 text-blue-400">Login</h2>
            <input type="email" id="email" placeholder="Email" class="w-full mb-4 p-3 rounded bg-slate-900 border border-slate-700 outline-none">
            <input type="password" id="pass" placeholder="Password" class="w-full mb-6 p-3 rounded bg-slate-900 border border-slate-700 outline-none">
            <button onclick="auth()" class="w-full bg-blue-600 py-3 rounded-xl font-bold hover:bg-blue-500">Continue</button>
            <p class="mt-4 text-sm text-gray-500 cursor-pointer" onclick="isLoginMode=!isLoginMode; renderAuth()">New user? Register</p>
        </div>

        <div id="appBox" class="max-w-5xl mx-auto hidden">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-2xl font-bold text-blue-400">AI DATA WORKER PRO</h1>
                <button onclick="location.reload()" class="bg-red-500/10 text-red-400 px-4 py-1 rounded-lg border border-red-500/20 text-sm">Logout</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl shadow-lg">
                        <input type="file" id="fileIn" class="mb-4 text-sm text-slate-400">
                        <textarea id="textIn" rows="8" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:border-blue-500" placeholder="Enter or paste input..."></textarea>
                        <div class="flex gap-4 mt-4">
                            <button onclick="analyze()" id="anBtn" class="bg-blue-600 px-8 py-3 rounded-xl font-bold flex items-center gap-2">
                                <span id="btnText">Analyze</span>
                                <div id="btnLoad" class="loader hidden"></div>
                            </button>
                            <button onclick="clearAll()" class="bg-slate-800 px-6 py-3 rounded-xl">Clear</button>
                        </div>
                    </div>

                    <div class="glass p-6 rounded-3xl">
                        <h3 class="font-bold text-blue-300 mb-4">Extracted Results</h3>
                        <div id="resTable" class="space-y-2 text-sm"></div>
                        
                        <div class="mt-8 pt-6 border-t border-slate-800">
                            <h4 class="text-xs font-bold text-slate-500 uppercase mb-4">+ Custom Fields</h4>
                            <div class="flex gap-2">
                                <input type="text" id="cfName" placeholder="Field name" class="bg-slate-900 border border-slate-800 p-2 rounded-lg flex-1">
                                <input type="text" id="cfVal" placeholder="Value" class="bg-slate-900 border border-slate-800 p-2 rounded-lg flex-1">
                                <button onclick="addCustom()" class="bg-indigo-600 px-4 py-2 rounded-lg text-sm font-bold">Add</button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="glass p-6 rounded-3xl h-fit">
                    <h3 class="font-bold text-cyan-400 mb-4">🕒 Last 10 Analysis</h3>
                    <div id="histList" class="space-y-2 overflow-y-auto max-h-[500px]"></div>
                </div>
            </div>
        </div>

        <script>
            let isLoginMode = true;
            let currentData = {};

            function renderAuth() {
                document.getElementById('authTitle').innerText = isLoginMode ? "Login" : "Register";
            }

            async function auth() {
                const email = document.getElementById('email').value;
                const password = document.getElementById('pass').value;
                if(!email || !password) return alert("Fill fields");

                const route = isLoginMode ? '/login' : '/register';
                const res = await fetch(route, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email, password})
                });

                if(res.ok) {
                    if(!isLoginMode) { alert("Success! Now login"); isLoginMode=true; renderAuth(); }
                    else {
                        document.getElementById('authBox').classList.add('hidden');
                        document.getElementById('appBox').classList.remove('hidden');
                        loadHistory();
                    }
                } else alert("Auth failed!");
            }

            async function analyze() {
                const text = document.getElementById('textIn').value;
                const file = document.getElementById('fileIn').files[0];
                if(!text && !file) return alert("Please enter or paste data!");

                const btn = document.getElementById('anBtn');
                const load = document.getElementById('btnLoad');
                btn.disabled = true;
                load.classList.remove('hidden');
                document.getElementById('btnText').innerText = "Analyzing...";

                const fd = new FormData();
                fd.append('text', text);
                if(file) fd.append('file', file);

                setTimeout(async () => {
                    try {
                        const res = await fetch('/analyze', { method: 'POST', body: fd });
                        const data = await res.json();
                        if(data.Error) throw new Error(data.Error);
                        currentData = data;
                        renderTable();
                        loadHistory();
                    } catch(e) { 
                        console.error(e);
                        alert("Error analyzing!"); 
                    } finally {
                        btn.disabled = false;
                        load.classList.add('hidden');
                        document.getElementById('btnText').innerText = "Analyze";
                    }
                }, 3000);
            }

            function renderTable() {
                const container = document.getElementById('resTable');
                container.innerHTML = Object.entries(currentData).map(([k,v]) => {
                    if(k==='timestamp' || k==='Error') return '';
                    return `<div class="flex justify-between border-b border-slate-800 py-2">
                        <span class="text-slate-500 font-bold">${k}</span>
                        <span class="text-blue-200">${v}</span>
                    </div>`;
                }).join('');
            }

            async function addCustom() {
                const field = document.getElementById('cfName').value;
                const val = document.getElementById('cfVal').value;
                if(!field || !val) return;
                currentData[field] = val;
                renderTable();
                await fetch('/learn', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({field})
                });
                document.getElementById('cfName').value = '';
                document.getElementById('cfVal').value = '';
            }

            async function loadHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `
                    <div class="bg-slate-900/50 p-3 rounded-xl border border-slate-800 text-xs cursor-pointer hover:border-blue-500" onclick='viewHist(${JSON.stringify(h)})'>
                        <div class="flex justify-between font-bold text-blue-400">
                            <span>${h.Name || 'Record'}</span>
                            <span class="text-slate-600">${h.timestamp}</span>
                        </div>
                    </div>
                `).join('');
            }

            function viewHist(h) { currentData = h; renderTable(); }

            function clearAll() {
                document.getElementById('textIn').value = '';
                document.getElementById('fileIn').value = '';
                document.getElementById('resTable').innerHTML = '';
                currentData = {};
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
