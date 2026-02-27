import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 1. API Key Setup (Render Environment Variables-ilirundhu)
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Simple setup - Render-la error varaamal irukka idhu dhaan best
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

# 2. CORS Middleware (Frontend connect aaga mukhya vishayam)
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
    </head>
    <body style="background:#121212; color:white; font-family:sans-serif; text-align:center; padding:20px;">
        <h2>🤖 AI Chatbot (Live)</h2>
        <div id="chatbox" style="background:#1e1e1e; padding:15px; border-radius:10px; max-width:500px; margin:auto; height:350px; overflow-y:auto; text-align:left; border:1px solid #333; font-size: 14px;">
            <p style="color:#888;">AI: Ready! Type something to start chatting...</p>
        </div>
        <br>
        <div style="max-width:500px; margin:auto; display:flex; gap:10px;">
            <input type="text" id="userInput" style="flex:1; padding:12px; border-radius:8px; border:none;" placeholder="Type here...">
            <button onclick="send()" style="padding:12px 20px; background:#2563eb; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">SEND</button>
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
                        chat.innerHTML += `<p style="color:red;"><b>Error:</b> ${data.error || 'Unknown error'}</p>`;
                    }
                } catch(e) {
                    chat.innerHTML += `<p style="color:red;"><b>Error:</b> Server offline or connection lost.</p>`;
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
        return {"reply": "Error: API Key is not set in Render environment."}
    try:
        # Standard generation call
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        # Inga varra actual error-ai report pannuvom (e.g., Quota limit)
        return {"reply": f"Gemini Error: {str(e)}"}
        
