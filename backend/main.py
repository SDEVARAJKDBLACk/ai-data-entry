import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 1. API Configuration
# Render Environment-il GEMINI_API_KEY nu name irukkanum
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Gemini Pro: Idhu romba stable, 404 error varaadhu
    model = genai.GenerativeModel('models/gemini-pro')
else:
    model = None

app = FastAPI()

# 2. CORS Settings
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
        <title>AI Chatbot - Gemini Pro</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:20px; }
            #chatbox { background:#1e293b; padding:15px; border-radius:12px; max-width:500px; margin:auto; height:400px; overflow-y:auto; text-align:left; border:1px solid #334155; }
            .input-area { max-width:500px; margin:20px auto; display:flex; gap:10px; }
            input { flex:1; padding:12px; border-radius:8px; border:none; outline:none; }
            button { padding:12px 24px; background:#3b82f6; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
            button:hover { background:#2563eb; }
            .user-msg { color: #94a3b8; margin-bottom: 10px; }
            .ai-msg { color: #60a5fa; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <h2>🤖 Gemini Pro Chatbot</h2>
        <div id="chatbox">
            <p style="color:#64748b;">AI: Hello! I am Gemini Pro. How can I help you today?</p>
        </div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask me something...">
            <button onclick="send()">SEND</button>
        </div>

        <script>
            async function send() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;

                chat.innerHTML += `<div class="user-msg"><b>You:</b> ${msg}</div>`;
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
                        chat.innerHTML += `<div class="ai-msg"><b>AI:</b> ${data.reply}</div>`;
                    } else {
                        chat.innerHTML += `<p style="color:#ef4444;"><b>Error:</b> ${data.error || 'Server error'}</p>`;
                    }
                } catch(e) {
                    chat.innerHTML += `<p style="color:#ef4444;"><b>Error:</b> Connection failed.</p>`;
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
        return {"reply": "Error: API Key missing in Environment Settings."}
    try:
        # Gemini Pro generation
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        # Indha error message Render logs-layum kaattum
        return {"reply": f"Gemini Error: {str(e)}"}
    
