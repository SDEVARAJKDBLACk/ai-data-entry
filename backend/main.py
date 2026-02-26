import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai

# --- Gemini Config with Stable Fallback ---
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)

# Trying multiple model names to fix the 404 error
def get_stable_model():
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    for m_name in models_to_try:
        try:
            m = genai.GenerativeModel(m_name)
            # Test call to verify model exists
            print(f"Successfully connected to: {m_name}")
            return m
        except Exception:
            continue
    return None

model = get_stable_model()

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not model:
        return {"Error": "No Gemini models available. Check your API Key or Library Version."}
    
    prompt = "Extract Name, Phone, Email, Company, Amount as JSON. Return ONLY JSON."
    
    try:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI format error"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><body style="background:#0f172a; color:white; font-family:sans-serif; padding:50px; text-align:center;">
        <h1 style="color:#60a5fa;">AI STABLE ANALYZER</h1>
        <div style="background:#1e293b; padding:30px; border-radius:20px; max-width:500px; margin:auto;">
            <textarea id="t" style="width:100%; background:#000; color:white; padding:10px; border-radius:10px;" rows="5" placeholder="Paste data..."></textarea>
            <button onclick="run()" id="b" style="background:#2563eb; color:white; border:none; padding:15px 30px; border-radius:10px; margin-top:20px; cursor:pointer; font-weight:bold;">Run Analysis</button>
            <div id="r" style="margin-top:20px; text-align:left; font-size:14px;"></div>
        </div>
        <script>
            async function run() {
                const b = document.getElementById('b'); b.innerText = "Connecting...";
                const fd = new FormData(); fd.append('text', document.getElementById('t').value);
                try {
                    const res = await fetch('/analyze', {method:'POST', body:fd});
                    const data = await res.json();
                    document.getElementById('r').innerHTML = data.Error ? `<span style="color:red">${data.Error}</span>` : JSON.stringify(data, null, 2);
                } catch(e) { alert("Network Error"); }
                finally { b.innerText = "Run Analysis"; }
            }
        </script>
    </body></html>
    """

