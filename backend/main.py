import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from PIL import Image
import google.generativeai as genai

# API Key configuration
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# Simplest way to call Gemini 1.5 Flash
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        prompt = "Extract Name, Phone, Email, and Amount as JSON. Return ONLY JSON."
        
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        # Finding JSON in AI text
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI format mismatch"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><body style="background:#0f172a; color:white; padding:50px; font-family:sans-serif; text-align:center;">
        <div style="max-width:500px; margin:auto; background:#1e293b; padding:30px; border-radius:20px; border:1px solid #334155;">
            <h2 style="color:#3b82f6">Gemini Data Analyzer</h2>
            <textarea id="t" style="width:100%; height:100px; background:#020617; color:white; border-radius:10px; padding:10px; margin-bottom:15px; border:1px solid #334155;" placeholder="Paste text..."></textarea>
            <input type="file" id="f" style="margin-bottom:20px; display:block; width:100%; font-size:12px;">
            <button onclick="run()" id="btn" style="width:100%; padding:15px; background:#2563eb; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer;">Analyze Now</button>
            <div id="res" style="margin-top:20px; text-align:left; color:#93c5fd; background:#020617; padding:15px; border-radius:10px;"></div>
        </div>
        <script>
            async function run() {
                const b = document.getElementById('btn'); b.innerText = "Analyzing...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                if(document.getElementById('f').files[0]) fd.append('file', document.getElementById('f').files[0]);
                try {
                    const res = await fetch('/analyze', {method:'POST', body:fd});
                    const data = await res.json();
                    document.getElementById('res').innerHTML = data.Error ? `<span style="color:red">${data.Error}</span>` : `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch(e) { alert("Error connecting!"); }
                finally { b.innerText = "Analyze Now"; }
            }
        </script>
    </body></html>
    """
