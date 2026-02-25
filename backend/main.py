import os
import io
import re
import json
import uvicorn
import pandas as pd
from datetime import datetime
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from PIL import Image
import pdfplumber
import google.generativeai as genai

# --- Gemini Configuration ---
# Render-la 'Environment Variables'-la GEMINI_API_KEY-nu unga key-ai add pannunga
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- DB Simulation ---
USERS_FILE = "users.json"
HISTORY_FILE = "history.json"

def load_db(file):
    if os.path.exists(file):
        with open(file, "r") as f: return json.load(f)
    return [] if "history" in file else {}

def save_db(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

# --- AI Extraction via Gemini ---
async def extract_with_gemini(text_content):
    prompt = f"""
    Extract the following fields from the text in a JSON format. 
    Fields: Name, Reference Name, Age, Gender, Phone, Email, Address, City, State, Country, 
    Pincode, Company, Job Title, Location, Product Name, Quantity, Price, Salary, 
    Total Amount, Date, Transaction Number.
    
    If any data is missing, put "N/A".
    Text: {text_content}
    """
    try:
        response = model.generate_content(prompt)
        # Cleaning the response to get valid JSON
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(json_str)
    except Exception as e:
        return {"Error": str(e)}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not text and not file:
        raise HTTPException(status_code=400, detail="Data empty")
    
    content = text
    if file:
        file_bytes = await file.read()
        if file.filename.lower().endswith(('.pdf')):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                content += "\n" + "".join([p.extract_text() for p in pdf.pages])
        elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Direct Image Analysis using Gemini
            img = Image.open(io.BytesIO(file_bytes))
            response = model.generate_content(["Extract data from this image in JSON format", img])
            json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
            return json.loads(json_str)

    extracted_data = await extract_with_gemini(content)
    
    # Save History
    history = load_db(HISTORY_FILE)
    extracted_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.insert(0, extracted_data)
    save_db(HISTORY_FILE, history[:10])
    
    return extracted_data

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Data Entry - Gemini</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0f172a; color: white; }
            .loader { border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-400 mb-6">Gemini AI Data Entry</h1>
            
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl">
                <textarea id="textInput" rows="6" class="w-full p-4 rounded bg-slate-900 border border-slate-700 text-white outline-none focus:ring-2 focus:ring-blue-500" placeholder="Paste your data here..."></textarea>
                <input type="file" id="fileInput" class="mt-4 block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-600 file:text-white">
                
                <div class="mt-6 flex gap-4">
                    <button onclick="process('analyze')" id="btnAnalyze" class="bg-cyan-600 hover:bg-cyan-500 px-8 py-3 rounded-lg font-bold flex items-center gap-2">
                        <span>Analyze</span>
                        <div id="loadAnalyze" class="loader hidden"></div>
                    </button>
                </div>
            </div>

            <div class="mt-8 bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 class="text-xl font-semibold mb-4 text-blue-300">Extracted Results</h2>
                <div id="resultTable" class="overflow-x-auto text-sm"></div>
            </div>
        </div>

        <script>
            async function process(type) {
                const text = document.getElementById('textInput').value;
                const file = document.getElementById('fileInput').files[0];
                
                if(!text && !file) { alert("Data enter pannunga!"); return; }

                document.getElementById('loadAnalyze').classList.remove('hidden');
                
                const fd = new FormData();
                fd.append('text', text);
                if(file) fd.append('file', file);

                const res = await fetch('/analyze', { method: 'POST', body: fd });
                const data = await res.json();

                document.getElementById('loadAnalyze').classList.add('hidden');
                
                let html = '<table class="w-full"><thead><tr class="text-left border-b border-slate-700 text-gray-400"><th>Field</th><th>Value</th></tr></thead><tbody>';
                for(let [k,v] of Object.entries(data)) {
                    if(k !== 'timestamp')
                    html += `<tr class="border-b border-slate-700"><td class="py-2 text-blue-200">${k}</td><td>${v}</td></tr>`;
                }
                html += '</tbody></table>';
                document.getElementById('resultTable').innerHTML = html;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
