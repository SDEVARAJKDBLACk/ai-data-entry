from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn, io, re, json, os, pandas as pd
from PIL import Image
import pytesseract, pdfplumber, docx
from datetime import datetime
from typing import List, Dict

app = FastAPI()

# ---------------------------
# DB & AUTH SIMULATION
# ---------------------------
USERS_FILE = "users.json"
HISTORY_FILE = "analysis_history.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f: return json.load(f)
    return [] if "history" in filename else {}

def save_json(filename, data):
    with open(filename, "w") as f: json.dump(data, f, indent=4)

# ---------------------------
# EXTRACTION LOGIC
# ---------------------------
def ai_extract(text):
    def find_all(pattern, txt):
        matches = re.findall(pattern, txt, re.IGNORECASE | re.MULTILINE)
        return ", ".join(list(dict.fromkeys([m.strip() for m in matches if m.strip()]))) or "N/A"

    raw_names = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b', text)
    stop_words = ["Road", "Street", "City", "State", "Country", "Pincode", "Technologies", "Company", "Office", "Laptop", "Mobile"]
    filtered_names = [n for n in raw_names if not any(sw in n for sw in stop_words) and "Reference" not in n]
    
    return {
        "Name": ", ".join(list(dict.fromkeys(filtered_names))) or "N/A",
        "Reference Name": find_all(r'Reference name is ([\w\s]+)\.', text),
        "Age": find_all(r'(\d{1,3})\s*(?:years|age)', text),
        "Gender": find_all(r'\b(male|female)\b', text),
        "Phone": find_all(r'\b\d{10}\b', text),
        "Email": find_all(r'[\w\.-]+@[\w\.-]+\.\w+', text),
        "City": find_all(r'City\s*(?:is)?\s*([A-Za-z\s]+)', text),
        "Job Title": find_all(r'(?:designation|as)\s*(?:is)?\s*([A-Za-z\s]+?)(?=\.\n|Arun|My)', text),
        "Salary": find_all(r'salary\s*(?:is)?\s*(\d+)', text),
        "Transaction Number": find_all(r'TXN\d+', text),
    }

# ---------------------------
# ROUTES
# ---------------------------
@app.post("/register")
async def register(data: dict):
    users = load_json(USERS_FILE)
    if data['email'] in users: raise HTTPException(status_code=400, detail="User exists")
    users[data['email']] = data
    save_json(USERS_FILE, users)
    return {"status": "success"}

@app.post("/login")
async def login(data: dict):
    users = load_json(USERS_FILE)
    user = users.get(data['email'])
    if user and user['password'] == data['password']:
        return {"status": "success", "user": user}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    content = text
    if file:
        data = await file.read()
        if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            content += "\n" + pytesseract.image_to_string(Image.open(io.BytesIO(data)))
        elif file.filename.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                content += "\n" + "".join([p.extract_text() for p in pdf.pages])
    
    extracted = ai_extract(content)
    history = load_json(HISTORY_FILE)
    extracted['timestamp'] = datetime.now().strftime("%H:%M:%S")
    history.insert(0, extracted)
    save_json(HISTORY_FILE, history[:10])
    return extracted

@app.post("/export")
async def export(data: List[Dict]):
    df = pd.DataFrame(data)
    df.to_excel("Export.xlsx", index=False)
    return FileResponse("Export.xlsx")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>AI Data Entry - Auth</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #0f172a; color: white; font-family: sans-serif; }
        .loader { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .hidden { display: none; }
    </style>
</head>
<body class="p-4">
    <div id="authSection" class="max-w-md mx-auto mt-20 bg-slate-800 p-8 rounded-xl shadow-lg">
        <h2 id="authTitle" class="text-2xl font-bold mb-6 text-blue-400 text-center">Login</h2>
        <input type="email" id="authEmail" placeholder="Email" class="w-full mb-4 p-3 rounded bg-slate-900 border border-slate-700">
        <input type="password" id="authPass" placeholder="Password" class="w-full mb-6 p-3 rounded bg-slate-900 border border-slate-700">
        <button onclick="handleAuth()" id="authBtn" class="w-full bg-blue-600 py-3 rounded font-bold hover:bg-blue-500">Sign In</button>
        <p class="mt-4 text-sm text-center cursor-pointer text-gray-400" onclick="toggleAuthMode()">New user? Register here</p>
    </div>

    <div id="mainApp" class="max-w-5xl mx-auto hidden">
        <div class="flex justify-between items-center mb-8 bg-slate-800 p-4 rounded-lg">
            <div>
                <span class="text-blue-400 font-bold">👤 User:</span> <span id="userNameDisplay">User</span>
            </div>
            <button onclick="logout()" class="bg-red-600 px-4 py-1 rounded text-sm">Logout</button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-slate-800 p-6 rounded-xl">
                <input type="file" id="fileInput" class="mb-4 text-sm">
                <textarea id="textInput" rows="10" class="w-full p-3 rounded bg-slate-900 border border-slate-700" placeholder="Paste data here..."></textarea>
                <div class="mt-4 flex gap-2">
                    <button onclick="validateAndAnalyze()" id="analyzeBtn" class="bg-cyan-600 px-6 py-2 rounded flex items-center gap-2">
                        <span id="analyzeText">Analyze</span>
                        <div id="analyzeLoader" class="loader hidden"></div>
                    </button>
                    <button onclick="exportExcel()" id="exportBtn" class="bg-indigo-600 px-6 py-2 rounded flex items-center gap-2">
                        <span id="exportText">Export Excel</span>
                        <div id="exportLoader" class="loader hidden"></div>
                    </button>
                </div>
            </div>

            <div class="bg-slate-800 p-6 rounded-xl overflow-x-auto">
                <h3 class="font-bold mb-4 text-blue-300">Extracted Results</h3>
                <table class="w-full text-sm">
                    <tbody id="dataTable"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let isLoginMode = true;
        let currentUser = null;
        let currentData = {};

        function toggleAuthMode() {
            isLoginMode = !isLoginMode;
            document.getElementById('authTitle').innerText = isLoginMode ? "Login" : "Register";
            document.getElementById('authBtn').innerText = isLoginMode ? "Sign In" : "Sign Up";
        }

        async function handleAuth() {
            const email = document.getElementById('authEmail').value;
            const pass = document.getElementById('authPass').value;
            if(!email || !pass) return alert("Fill all fields");

            const endpoint = isLoginMode ? '/login' : '/register';
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password: pass})
            });

            if(res.ok) {
                const data = await res.json();
                if(isLoginMode) {
                    currentUser = data.user;
                    showApp();
                } else {
                    alert("Registered! Please login.");
                    toggleAuthMode();
                }
            } else {
                alert("Auth failed!");
            }
        }

        function showApp() {
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('mainApp').classList.remove('hidden');
            document.getElementById('userNameDisplay').innerText = currentUser.email;
        }

        function logout() {
            location.reload();
        }

        async function validateAndAnalyze() {
            const text = document.getElementById('textInput').value;
            const file = document.getElementById('fileInput').files[0];
            
            if(!text && !file) {
                alert("Please enter or paste data or upload a file!");
                return;
            }

            // Start Animation
            const btn = document.getElementById('analyzeBtn');
            const loader = document.getElementById('analyzeLoader');
            btn.disabled = true;
            loader.classList.remove('hidden');
            document.getElementById('analyzeText').innerText = "Analysing...";

            setTimeout(async () => {
                const fd = new FormData();
                fd.append('text', text);
                if(file) fd.append('file', file);

                const res = await fetch('/analyze', {method:'POST', body:fd});
                currentData = await res.json();
                
                // Stop Animation
                btn.disabled = false;
                loader.classList.add('hidden');
                document.getElementById('analyzeText').innerText = "Analyze";
                
                renderTable();
            }, 3000); // 3 Seconds Loading
        }

        function renderTable() {
            document.getElementById('dataTable').innerHTML = Object.entries(currentData).map(([k,v]) => 
                `<tr class="border-b border-slate-700"><td class="py-2 font-bold text-gray-400">${k}</td><td class="py-2 text-blue-200">${v}</td></tr>`
            ).join('');
        }

        async function exportExcel() {
            if(Object.keys(currentData).length === 0) return alert("No data to export!");

            const btn = document.getElementById('exportBtn');
            const loader = document.getElementById('exportLoader');
            btn.disabled = true;
            loader.classList.remove('hidden');
            document.getElementById('exportText').innerText = "Exporting...";

            setTimeout(async () => {
                const res = await fetch('/export', {
                    method:'POST', 
                    headers:{'Content-Type':'application/json'}, 
                    body:JSON.stringify([currentData])
                });
                const blob = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = "Data.xlsx";
                a.click();

                btn.disabled = false;
                loader.classList.add('hidden');
                document.getElementById('exportText').innerText = "Export Excel";
            }, 2000);
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

