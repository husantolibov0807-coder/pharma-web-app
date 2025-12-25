from fastapi import FastAPI, Request
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# FastAPI sozlamalari
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# OpenAI sozlamalari
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # Vercel-ga buni ham qo'shing

# --- ASOSIY OPENAI FUNKSIYASI ---
def get_ai_response(user_message: str):
    try:
        # 1. Thread yaratish
        thread = client.beta.threads.create()
        
        # 2. Xabar qo'shish
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        
        # 3. Assistant-ni ishga tushirish (Run)
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

# --- WEB APP UCHUN (GET) ---
@app.get("/api/chat")
async def chat(message: str):
    response_text = get_ai_response(message)
    return {"reply": response_text}

# --- TELEGRAM BOT UCHUN (POST) ---
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        # Telegramdan kelgan xabarni ajratib olish
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_text = data["message"].get("text", "")
            
            if user_text:
                # OpenAI-dan javob olish
                ai_reply = get_ai_response(user_text)
                
                # Telegramga javob qaytarish
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                payload = {"chat_id": chat_id, "text": ai_reply}
                requests.post(url, json=payload)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}
