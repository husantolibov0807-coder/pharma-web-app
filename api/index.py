from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware # CORS uchun
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# --- CORS SOZLAMASI (MUHIM!) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Barcha saytlardan so'rovga ruxsat beradi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def get_ai_response(user_message: str):
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        # runs.create_and_poll — bu eng to'g'ri usul (kutish shart emas)
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            return messages.data[0].content[0].text.value
        else:
            return f"Xatolik yuz berdi: {run.status}"
    except Exception as e:
        return f"OpenAI xatosi: {str(e)}"

# --- WEB APP UCHUN (POST) ---
# GET emas, POST qilish xavfsizroq va matn uzun bo'lsa ham xato bermaydi
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message")
    if not user_message:
        return {"reply": "Xabar bo'sh"}
    
    response_text = get_ai_response(user_message)
    return {"reply": response_text}

# --- TELEGRAM BOT WEBHOOK ---
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    # Sizning hozirgi kodingiz shu yerda qoladi...
    try:
        data = await request.json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_text = data["message"].get("text", "")
            if user_text:
                ai_reply = get_ai_response(user_text)
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": ai_reply}
                requests.post(url, json=payload)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error"}
