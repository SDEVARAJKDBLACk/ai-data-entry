import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# 1. API KEY SETUP
API_KEY = os.getenv("GEMINI_API_KEY")

# 2. VERSION-AH FORCE PANNA CONFIGURATION (Very Important)
if API_KEY:
    # transport='rest' matrum version='v1' use panna 404 kandeepa varaadhu
    genai.configure(api_key=API_KEY, transport='rest')
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
else:
    model = None

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>AI Data Entry - Automated Data Worker</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-900 text-white font-sans text-center p-10">
            <h1 class="text-3xl font-bold text-blue-400 mb-6">AI Data Entry - Automated Data Worker</h1>
            <div class="max-w-md mx-auto bg-slate-800 p-8 rounded-2xl border border-slate-700 shadow-xl">
                <input type="text" id="userInput" placeholder="Type data here..." 
                       class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 focus:outline-none focus:border-blue-500 mb-4">
                <button onclick="processData()" class="w-full bg-blue-600 hover:bg-blue-700 p-3 rounded-lg font-bold transition">Process</button>
                <div id="result" class="mt-6 text-slate-300 italic text-sm"></div>
            </div>
            <script>
                async function processData() {
                    const resDiv = document.getElementById('result');
                    const text = document.getElementById('userInput').value;
                    if(!text) return;
                    resDiv.innerText = "Processing...";
                    const fd = new FormData();
                    fd.append('text', text);
                    try {
                        const response = await fetch('/automate', { method: 'POST', body: fd });
                        const data = await response.json();
                        resDiv.innerText = data.output;
                    } catch(e) {
                        resDiv.innerText = "Error connecting to server.";
                    }
                }
            </script>
        </body>
    </html>
    """

@app.post("/automate")
async def automate(text: str = Form(...)):
    if not model:
        return {"output": "System Message: API Key Missing."}
    try:
        # Inga version 1-ah force panni response edukarom
        response = model.generate_content(text)
        return {"output": response.text}
    except Exception as e:
        # 404 varradhu ninnudum, vera edhavadhu prachanai irundha inga kaattum
        return {"output": f"System Alert: {str(e)}"}
    
