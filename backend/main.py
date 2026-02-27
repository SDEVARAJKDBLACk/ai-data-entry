    import os
import requests
import json
import re
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
API_KEY = os.getenv("GEMINI_API_KEY")

# Direct Stable v1 URL
URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# FIX: Allow both GET and HEAD methods for Render health check
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request):
    if request.method == "HEAD":
        return HTMLResponse(content="", status_code=200)
    
    return """
    <html>
        <head><script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-900 text-white p-10">
            <div class="max-w-xl mx-auto bg-slate-800 p-8 rounded-3xl shadow-2xl border border-slate-700">
                <h1 class="text-3xl font-bold text-blue-400 mb-6">AI Data Extractor (Live ✅)</h1>
                <textarea id="inp" class="w-full bg-slate-900 p-4 rounded-xl mb-4 border border-slate-700 outline-none focus:border-blue-500" placeholder="Type data..."></textarea>
                <button onclick="send()" id="btn" class="w-full bg-blue-600 p-4 rounded-xl font-bold hover:bg-blue-700 transition">Process Data</button>
                <div id="out" class="mt-6 p-4 bg-slate-900 rounded-xl text-blue-300 font-mono text-sm min-h-[100px]">Result will appear here...</div>
            </div>
            <script>
                async function send() {
                    const out = document.getElementById('out');
                    const btn = document.getElementById('btn');
                    out.innerText = "AI is thinking...";
                    btn.disabled = true;
                    
                    const fd = new FormData();
                    fd.append('data', document.getElementById('inp').value);
                    
                    try {
                        const res = await fetch('/extract', { method: 'POST', body: fd });
                        const d = await res.json();
                        out.innerText = d.success ? JSON.stringify(d.info, null, 2) : "Error: " + d.error;
                    } catch(e) { out.innerText = "Connection Error"; }
                    finally { btn.disabled = false; }
                }
            </script>
        </body>
    </html>
    """

@app.post("/extract")
async def extract(data: str = Form(...)):
    prompt = f"Extract Name, Age, Location from: '{data}'. Return ONLY JSON: {{'name':'','age':'','location':''}}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        resp = requests.post(URL, json=payload, timeout=10)
        res_j = resp.json()
        
        if resp.status_code != 200:
            return {"success": False, "error": res_j.get('error', {}).get('message', 'API Error')}
        
        raw_text = res_j['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return {"success": True, "info": json.loads(match.group())}
        return {"success": False, "error": "AI response error"}
    except Exception as e:
        return {"success": False, "error": str(e)}
                            
