import os
import json
import requests
import re
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# 1. API KEY SETUP
API_KEY = os.getenv("GEMINI_API_KEY")

# 2. STABLE URL (v1beta-vai thookittu v1 nu maathittaen)
# Idhu dhaan 404 error-ai fix pannum
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Data Entry - Automated Data Worker</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white p-10 font-sans">
        <div class="max-w-2xl mx-auto text-center">
            <h1 class="text-4xl font-extrabold mb-4 text-blue-400">AI Data Entry - Automated Data Worker</h1>
            <p class="mb-8 text-slate-400 font-medium italic">Gemini 1.5 Flash (Stable v1) Powered Extraction</p>
            
            <textarea id="rawInput" class="w-full h-44 bg-slate-800 border border-slate-700 p-4 rounded-2xl mb-4 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-inner" 
            placeholder="Ex: Ramesh, age 25, from Salem working as Teacher..."></textarea>
            
            <button onclick="processData()" id="btn" class="w-full bg-blue-600 hover:bg-blue-700 py-4 rounded-xl font-bold text-lg transition shadow-lg active:scale-95">
                Start Automation
            </button>
            
            <div id="loader" class="hidden mt-6 text-blue-400 animate-pulse font-semibold">⚡ AI Worker is analyzing your data...</div>

            <div class="mt-10 grid grid-cols-2 gap-6 text-left bg-slate-800 p-8 rounded-3xl border border-slate-700 shadow-2xl">
                <div class="space-y-1">
                    <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Full Name</label>
                    <input id="name" class="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-blue-300 font-semibold" readonly>
                </div>
                <div class="space-y-1">
                    <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Age</label>
                    <input id="age" class="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-blue-300 font-semibold" readonly>
                </div>
                <div class="space-y-1">
                    <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Location</label>
                    <input id="loc" class="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-blue-300 font-semibold" readonly>
                </div>
                <div class="space-y-1">
                    <label class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Job Role</label>
                    <input id="job" class="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-blue-300 font-semibold" readonly>
                </div>
            </div>
        </div>

        <script>
            async function processData() {
                const btn = document.getElementById('btn');
                const loader = document.getElementById('loader');
                const text = document.getElementById('rawInput').value;
                if(!text) return alert("Please enter some text!");

                btn.disabled = true; 
                btn.classList.add('opacity-50');
                loader.classList.remove('hidden');

                const fd = new FormData();
                fd.append('data', text);

                try {
                    const response = await fetch('/extract', { method: 'POST', body: fd });
                    const result = await response.json();

                    if(result.success) {
                        document.getElementById('name').value = result.info.name || '-';
                        document.getElementById('age').value = result.info.age || '-';
                        document.getElementById('loc').value = result.info.location || '-';
                        document.getElementById('job').value = result.info.job || '-';
                    } else {
                        alert("AI Error: " + result.error);
                    }
                } catch(e) {
                    alert("Network Error: Could not connect to the backend.");
                } finally {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                    loader.classList.add('hidden');
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/extract")
async def extract(data: str = Form(...)):
    # Precise instruction for JSON format
    prompt = f"Extract Name, Age, Location, and Job Role from this text: '{data}'. Return ONLY a JSON object with keys: name, age, location, job. If any info is missing, use an empty string."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        # v1 (Stable) API request
        resp = requests.post(GEMINI_URL, json=payload, timeout=10)
        resp_json = resp.json()

        if resp.status_code != 200:
            error_msg = resp_json.get('error', {}).get('message', 'API Error')
            return {"success": False, "error": error_msg}

        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        
        # Regex to find JSON block in AI response
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            extracted_json = json.loads(match.group())
            return {"success": True, "info": extracted_json}
        
        return {"success": False, "error": "AI response was not in JSON format."}
    except Exception as e:
        return {"success": False, "error": str(e)}
