import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai

# 1. API Setup using NEW SDK
API_KEY = os.getenv("GEMINI_API_KEY")
client = None

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    print("Error: GEMINI_API_KEY not found!")

app = FastAPI()

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
        <title>AI Chatbot - Modern SDK</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:20px; }
            #chatbox { background:#1e293b; padding:15px; border-radius:12px; max-width:500px; margin:auto; height:400px; overflow-y:auto; text-align:left; border:1px solid #334155; }
            .input-area { max-width:500px; margin:20px auto; display:flex; gap:10px; }
            input { flex:1; padding:12px; border-radius:8px; border:none; outline:none; color:black; }
            button { padding:12px 24px; background:#3b82f6; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
        </style>
    </head>
    <body>
        <h2>🤖 Gemini Modern Chatbot</h2>
        <div id="chatbox"><p style="color:#64748b;">AI: System Online. How can I help?</p></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Ask something...">
            <button onclick="send()">SEND</button>
        </div>
        <script>
            async function send() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;
                chat.innerHTML += `<div><b>You:</b> ${msg}</div>`;
                input.value = "";
                try {
                    const formData = new FormData();
                    formData.append('message', msg);
                    const response = await fetch('/chat', { method: 'POST', body: formData });
                    const data = await response.json();
                    chat.innerHTML += `<div style="color:#60a5fa;"><b>AI:</b> ${data.reply}</div>`;
                } catch(e) {
                    chat.innerHTML += `<p style="color:red;">Error: Connection lost.</p>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(message: str = Form(...)):
    if not client:
        return {"reply": "API Key Error"}
    try:
        # Using the new SDK syntax
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=message
        )
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Gemini Error: {str(e)}"}
    
