import os
import requests
import json
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 1. Gemini API Setup (Stable v1 - Direct URL)
# Friend code-la iruntha 'genai.GenerativeModel' thukiyaachu, athan error varala
API_KEY = "AIzaSyA4_LXv5St-1-u-xidvVWBakivc_HaetkE" # Unga key
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

@app.route('/')
def index():
    # Inga unga HTML file name kudunga
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_data():
    raw_text = request.form.get('data')
    if not raw_text:
        return jsonify({"success": False, "error": "No data provided"})

    # Prompt-ai 'app.py' maadhiri structure pandrom
    prompt = f"Extract Name, Age, Location, and Job from this text: '{raw_text}'. Return ONLY a JSON object with keys: name, age, location, job."
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        # Direct request to Google (No v1beta error)
        response = requests.post(GEMINI_URL, json=payload, timeout=15)
        res_json = response.json()

        if response.status_code != 200:
            return jsonify({"success": False, "error": res_json.get('error', {}).get('message', 'API Error')})

        ai_text = res_json['candidates'][0]['content']['parts'][0]['text']
        
        # Regex to filter JSON (Friend code-la illatha extra safety)
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            extracted_data = json.loads(match.group().replace("'", '"'))
            return jsonify({"success": True, "info": extracted_data})
        
        return jsonify({"success": False, "error": "AI could not structure data"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Render-kku port 10000 mukkiyam
    app.run(host='0.0.0.0', port=10000)
        
