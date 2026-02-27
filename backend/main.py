import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# Force connection mode to avoid 404
os.environ["GRPC_DNS_RESOLVER"] = "native"

API_KEY = os.getenv("GEMINI_API_KEY")

# API Setup with Error Handling
try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
        # 1.5-flash-latest stable-aana version
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        model = None
except Exception as e:
    print(f"Startup Error: {e}")
    model = None

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <body style="background:#111; color:white; font-family:sans-serif; text-align:center; padding:50px;">
            <h1>AI Data Entry - Automated Data Worker</h1>
            <div style="background:#222; padding:20px; border-radius:10px; display:inline-block;">
                <input type="text" id="msg" placeholder="Type data..." style="padding:10px; width:300px;">
                <button onclick="send()" style="padding:10px; background:blue; color:white; border:none; cursor:pointer;">Process</button>
                <div id="out" style="margin-top:20px; color:cyan;"></div>
            </div>
            <script>
                async function send() {
                    const out = document.getElementById('out');
                    out.innerText = "Processing...";
                    const fd = new FormData();
                    fd.append('text', document.getElementById('msg').value);
                    const res = await fetch('/automate', {method:'POST', body:fd});
                    const data = await res.json();
                    out.innerText = data.result;
                }
            </script>
        </body>
    </html>
    """

@app.post("/automate")
async def automate(text: str = Form(...)):
    if not model:
        return {"result": "API Key Missing or Config Error"}
    try:
        # Simplest call to test connectivity
        response = model.generate_content(text)
        return {"result": response.text}
    except Exception as e:
        # Inga dhaan 404 error catch aagum
        return {"result": f"Google API Error: {str(e)}"}
        
