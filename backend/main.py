import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 1. API Configuration
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # INDHA LINE THAAN FIX: Default settings use pannuvom, version force panna koodaadhu
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <title>AI Stable Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background:#121212; color:white; font-family:sans-serif; text-align:center; padding:20px; }
            #chatbox { background:#1e1e1e; padding:15px; border-radius:10px; max-width:500px; margin:auto; height:350px; overflow-y:auto; text-align:left; border:1px solid #333; }
            .input-area { max-width:500px; margin:20px auto; display:flex; gap:10px; }
            input { flex:1; padding:12px; border-radius:8px; border:none; }
            button { padding:12px 20px; background:#2563eb; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
        </style>
    </head>
    <body>
        <h2>🤖 AI Chatbot (Live)</h2>
        <div id="chatbox">
            <p style="color:#888;">AI: Ready! Type something...</p>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Type here...">
            <button onclick="send()">SEND</button>
        </div>

        <script>
            async function send() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;

                chat.innerHTML += `<p><b>You:</b> ${msg}</p>`;
                input.value = "";
                chat.scrollTop = chat.scrollHeight;

                try {
                    const formData = new FormData();
                    formData.append('message', msg);

                    const response = await fetch('/chat', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    
                    if(data.reply) {
                        chat.innerHTML += `<p style="color:#60a5fa;"><b>AI:</b> ${data.reply}</p>`;
                    } else {
                        chat.innerHTML += `<p style="color:red;"><b>Error:</b> ${data.error || 'Check logs'}</p>`;
                    }
                } catch(e) {
                    chat.innerHTML += `<p style="color:red;"><b>Error:</b> Connection failed.</p>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(message: str = Form(...)):
    if not model:
        return {"reply": "Error: API Key missing in Render Environment Settings."}
    try:
        # Simple generation call - No extra options to avoid 404
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Gemini Error: {str(e)}"}
    
