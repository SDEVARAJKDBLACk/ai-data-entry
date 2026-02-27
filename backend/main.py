import os  # 'i' should be lowercase
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from google.generativeai.types import RequestOptions
from fastapi.middleware.cors import CORSMiddleware

# API Key check
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash'
    )
else:
    model = None

app = FastAPI()

# Frontend connect aaga idhu mukkiyam
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
    <head><title>AI Stable Chat</title></head>
    <body style="background:#121212; color:white; font-family:sans-serif; text-align:center; padding:50px;">
        <h2>🤖 AI Chatbot (V1 Stable)</h2>
        <div id="chatbox" style="background:#1e1e1e; padding:20px; border-radius:10px; max-width:500px; margin:auto; height:300px; overflow-y:auto; text-align:left; border:1px solid #333;">
            <p style="color:#888;">AI: Ready for stable chat. Type something...</p>
        </div>
        <br>
        <input type="text" id="userInput" style="width:300px; padding:12px; border-radius:8px; border:none;" placeholder="Say Hi...">
        <button onclick="send()" style="padding:12px 20px; background:#2563eb; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">SEND</button>

        <script>
            async function send() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;

                chat.innerHTML += `<p><b>You:</b> ${msg}</p>`;
                input.value = "";

                try {
                    const formData = new FormData();
                    formData.append('message', msg);

                    const response = await fetch('/chat', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    chat.innerHTML += `<p style="color:#60a5fa;"><b>AI:</b> ${data.reply}</p>`;
                } catch(e) {
                    chat.innerHTML += `<p style="color:red;"><b>Error:</b> Could not connect.</p>`;
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
        return {"reply": "Error: GEMINI_API_KEY missing in Render environment."}
    try:
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Gemini Error: {str(e)}"}
        
