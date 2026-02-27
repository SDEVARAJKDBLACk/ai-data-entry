import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# API Key check
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    # VERSION-ai 'v1' nu force pannuvom, v1beta-va thavirkka
    genai.configure(api_key=API_KEY, transport='rest') 
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <body style="background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:50px;">
            <h1 style="color:#60a5fa;">AI Data Entry - Automated Data Worker</h1>
            <div style="background:#1e293b; padding:30px; border-radius:15px; display:inline-block; border:1px solid #334155;">
                <input type="text" id="userInput" placeholder="Type here..." style="padding:12px; width:300px; border-radius:8px; border:none;">
                <button onclick="process()" style="padding:12px 20px; background:#3b82f6; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">Process</button>
                <div id="result" style="margin-top:20px; color:#94a3b8; font-style:italic;"></div>
            </div>
            <script>
                async function process() {
                    const resDiv = document.getElementById('result');
                    resDiv.innerText = "Processing...";
                    const fd = new FormData();
                    fd.append('text', document.getElementById('userInput').value);
                    try {
                        const response = await fetch('/automate', { method: 'POST', body: fd });
                        const data = await response.json();
                        resDiv.innerText = data.result;
                    } catch(e) {
                        resDiv.innerText = "Connection Error";
                    }
                }
            </script>
        </body>
    </html>
    """

@app.post("/automate")
async def automate(text: str = Form(...)):
    if not model: return {"result": "API Key Missing"}
    try:
        # Generate content with forced v1 version
        response = model.generate_content(text)
        return {"result": response.text}
    except Exception as e:
        # Inga dhaan 404 catch aagum, version issue irundhaa kaattum
        return {"result": f"System Message: {str(e)}"}
        
