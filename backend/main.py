import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# Render environment variables configuration
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)

# Force v1 API version to fix 404 errors
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    request_options=RequestOptions(api_version='v1')
)

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY JSON."
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        # Extracting JSON from AI response
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI format mismatch"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><body style="background:#0b0f1a; color:white; padding:50px; font-family:sans-serif; text-align:center;">
        <div style="max-width:500px; margin:auto; background:#1e293b; padding:30px; border-radius:20px; border:1px solid #334155;">
            <h2 style="color:#60a5fa">Gemini AI Stable Fix</h2>
            <textarea id="t" style="width:100%; height:120px; background:#020617; color:white; border-radius:10px; padding:10px; margin-bottom:15px;" placeholder="Paste text..."></textarea>
            <input type="file" id="f" style="margin-bottom:20px; font-size:12px; display:block; width:100%;">
            <button onclick="run()" id="b" style="width:100%; padding:15px; background:#2563eb; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer;">Analyze Now</button>
            <div id="r" style="margin-top:25px; text-align:left; color:#94a3b8; background:#0f172a; padding:15px; border-radius:10px;"></div>
        </div>
        <script>
            async function run() {
                const b = document.getElementById('b'); b.innerText = "Analyzing...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                if(document.getElementById('f').files[0]) fd.append('file', document.getElementById('f').files[0]);
                try {
                    const res = await fetch('/analyze', {method:'POST', body:fd});
                    const data = await res.json();
                    document.getElementById('r').innerHTML = data.Error ? `<span style="color:red">${data.Error}</span>` : `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch(e) { alert("Error!"); }
                finally { b.innerText = "Analyze Now"; }
            }
        </script>
    </body></html>
    """
