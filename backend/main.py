import os
import json
import requests
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# Render-ல நீங்க செட் பண்ண API KEY
API_KEY = os.getenv("GEMINI_API_KEY")

# நேரடியா கூகுள் சர்வர் அட்ரஸ் (Stable v1)
# இதுல வெர்ஷன் மிஸ்மேட்ச் ஆக வாய்ப்பே இல்ல
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

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
            <h1 class="text-4xl font-bold mb-4 text-blue-400">AI Data Entry - Automated Data Worker</h1>
            <p class="mb-8 text-slate-400">Paste your raw data below</p>
            
            <textarea id="rawInput" class="w-full h-40 bg-slate-800 border border-slate-700 p-4 rounded-xl mb-4 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Ex: Ramesh, age 25, from Salem working as Teacher..."></textarea>
            
            <button onclick="processData()" id="btn" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-bold">Start Automation</button>
            
            <div id="loader" class="hidden mt-4 text-blue-400">AI is thinking...</div>

            <div class="mt-10 grid grid-cols-2 gap-4 text-left bg-slate-800 p-6 rounded-2xl border border-slate-700">
                <div><label class="text-xs text-slate-500">NAME</label><input id="name" class="w-full bg-transparent border-b border-slate-600 p-2" readonly></div>
                <div><label class="text-xs text-slate-500">AGE</label><input id="age" class="w-full bg-transparent border-b border-slate-600 p-2" readonly></div>
                <div><label class="text-xs text-slate-500">LOCATION</label><input id="loc" class="w-full bg-transparent border-b border-slate-600 p-2" readonly></div>
                <div><label class="text-xs text-slate-500">JOB</label><input id="job" class="w-full bg-transparent border-b border-slate-600 p-2" readonly></div>
            </div>
        </div>

        <script>
            async function processData() {
                const btn = document.getElementById('btn');
                const loader = document.getElementById('loader');
                const text = document.getElementById('rawInput').value;
                if(!text) return alert("Please enter text");

                btn.disabled = true; loader.classList.remove('hidden');

                const fd = new FormData();
                fd.append('data', text);

                const response = await fetch('/extract', { method: 'POST', body: fd });
                const result = await response.json();

                if(result.success) {
                    document.getElementById('name').value = result.info.name || '-';
                    document.getElementById('age').value = result.info.age || '-';
                    document.getElementById('loc').value = result.info.location || '-';
                    document.getElementById('job').value = result.info.job || '-';
                } else {
                    alert("Error: " + result.error);
                }
                btn.disabled = false; loader.classList.add('hidden');
            }
        </script>
    </body>
    </html>
    """

@app.post("/extract")
async def extract(data: str = Form(...)):
    prompt = f"Extract Name, Age, Location, Job from this text: '{data}'. Return ONLY JSON like {{'name':'','age':'','location':'','job':''}}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        # நேரடியா Requests மூலமா கூகுளுக்கு அனுப்புறோம் (No Library Needed)
        resp = requests.post(GEMINI_URL, json=payload)
        resp_json = resp.json()

        if resp.status_code != 200:
            return {"success": False, "error": resp_json.get('error', {}).get('message', 'API Error')}

        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        
        # Clean the AI output to get JSON
        import re
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            extracted_json = json.loads(match.group().replace("'", '"'))
            return {"success": True, "info": extracted_json}
        
        return {"success": False, "error": "AI could not parse data"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
