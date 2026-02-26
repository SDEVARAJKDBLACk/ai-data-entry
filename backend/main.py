import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai

# --- Gemini Configuration ---
# Render Environment Variables-la 'GEMINI_API_KEY' add panna marakatheenga
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)

# Connection Fix: Using 'latest' to avoid 404 error
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

# --- AI Core Logic ---
async def extract_basic_data(content, is_image=False, image_data=None):
    prompt = """
    Extract Name, Phone, Email, Company, Amount, and Date from the input.
    Return the result ONLY as a valid JSON object. 
    If a value is missing, use 'N/A'.
    """
    try:
        if is_image:
            response = model.generate_content([prompt, image_data])
        else:
            response = model.generate_content(f"{prompt}\nInput: {content}")
        
        # JSON extraction using Regex
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI format error"}
    except Exception as e:
        return {"Error": str(e)}

# --- API Route ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            f_bytes = await file.read()
            img = Image.open(io.BytesIO(f_bytes))
            result = await extract_basic_data("", is_image=True, image_data=img)
        else:
            result = await extract_basic_data(text)
        return result
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

# --- Frontend UI ---
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Gemini AI Core</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0f172a; color: white; }
            .card { background: #1e293b; border: 1px solid #334155; }
        </style>
    </head>
    <body class="p-10">
        <div class="max-w-3xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-400 mb-8 text-center">AI DATA ANALYZER</h1>
            
            <div class="card p-6 rounded-2xl shadow-xl mb-8">
                <textarea id="tIn" rows="5" class="w-full bg-slate-900 p-4 rounded-xl border border-slate-700 mb-4 outline-none focus:border-blue-500" placeholder="Paste text here..."></textarea>
                <input type="file" id="fIn" class="mb-4 block text-sm text-slate-400">
                <button onclick="run()" id="btn" class="w-full bg-blue-600 hover:bg-blue-500 py-3 rounded-xl font-bold transition">Analyze with Gemini</button>
            </div>

            <div id="res" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                </div>
        </div>

        <script>
            async function run() {
                const b = document.getElementById('btn');
                const resDiv = document.getElementById('res');
                b.innerText = "Processing...";
                b.disabled = true;

                const fd = new FormData();
                fd.append('text', document.getElementById('tIn').value);
                const file = document.getElementById('fIn').files[0];
                if(file) fd.append('file', file);

                try {
                    const response = await fetch('/analyze', { method: 'POST', body: fd });
                    const data = await response.json();
                    
                    if(data.Error) {
                        alert("AI Error: " + data.Error);
                    } else {
                        resDiv.innerHTML = Object.entries(data).map(([k, v]) => `
                            <div class="card p-4 rounded-xl border-l-4 border-blue-500">
                                <span class="text-xs text-slate-400 font-bold uppercase">${k}</span>
                                <div class="text-lg text-blue-100">${v}</div>
                            </div>
                        `).join('');
                    }
                } catch (e) {
                    alert("Connection Error!");
                } finally {
                    b.innerText = "Analyze with Gemini";
                    b.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
        
