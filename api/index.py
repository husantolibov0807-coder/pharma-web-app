import os
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

# Sozlamalar
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

client = OpenAI(api_key=OPENAI_KEY)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. OpenAI orqali Oxford javobini olish funksiyasi
def get_oxford_response(user_input: str):
    try:
        # Thread yaratish
        thread = client.beta.threads.create()
        # Xabar yuborish
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
        # Run qilish
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            return messages.data[0].content[0].text.value
        return "Uzr, javob tayyorlashda kechikish bo'ldi."
    except Exception as e:
        return f"OpenAI xatosi: {str(e)}"

# 2. Telegramga xabar yuborish funksiyasi
def send_telegram_msg(chat_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # START komandasi - Menyu bilan
        if text == "/start":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💊 Dori qidirish (WebApp)", "web_app": {"url": "https://pharma-web-app-31d5.vercel.app/index.html"}}],
                    [{"text": "📖 Oxford AI Tutor (Chat)", "callback_data": "activate_oxford"}]
                ]
            }
            welcome_text = (
                "Assalomu alaykum! Kerakli bo'limni tanlang:\n\n"
                "1. **Dori qidirish** - WebApp tugmasini bosing.\n"
                "2. **Oxford AI** - Tibbiy terminlar bo'yicha botni o'zida gaplashish."
            )
            send_telegram_msg(chat_id, welcome_text, keyboard)

        # Agar foydalanuvchi Oxford rejimida bo'lsa yoki shunchaki tekst yozsa
        elif text and not text.startswith("/"):
            # Oxford AI javobi
            wait_msg = f"🔍 '{text}' bo'yicha Oxford kitoblari tahlil qilinmoqda..."
            send_telegram_msg(chat_id, wait_msg)
            
            answer = get_oxford_response(text)
            send_telegram_msg(chat_id, answer)

    # Tugma bosilganda (Callback Query)
    elif "callback_query" in data:
        callback_data = data["callback_query"]["data"]
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        
        if callback_data == "activate_oxford":
            send_telegram_msg(chat_id, "✅ Oxford AI rejimi faol. Istalgan tibbiy termin yoki kasallik nomini yozing:")

    return {"status": "ok"}

# Eski WebApp uchun /api/chat yo'lini saqlab qolamiz (xalaqit bermaydi)
@app.post("/api/chat")
async def legacy_chat(request: Request):
    req_data = await request.json()
    msg = req_data.get("message")
    reply = get_oxford_response(msg)
    return {"reply": reply}
