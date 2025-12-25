import os
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

# 1. SOZLAMALAR (Vercel Environment Variables dan oladi)
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID") # Oxford Assistant uchun

client = OpenAI(api_key=OPENAI_KEY)
app = FastAPI()

# Foydalanuvchi rejimini vaqtincha saqlash
user_modes = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- YORDAMCHI FUNKSIYALAR ---

def to_cyrillic(text):
    """Lotincha so'rovni kirillchaga o'giradi (Excel bazasi uchun)"""
    mapping = {"a":"а","b":"б","v":"в","g":"г","d":"д","e":"е","yo":"ё","j":"ж","z":"з","i":"и","y":"й","k":"к","l":"л","m":"м","n":"н","o":"о","p":"п","r":"р","s":"с","t":"т","u":"у","f":"ф","x":"х","ts":"ц","ch":"ч","sh":"ш","q":"қ","h":"ҳ"}
    text = text.lower()
    for lat, cyr in {"sh":"ш","ch":"ч","yo":"ё","yu":"ю","ya":"я"}.items():
        text = text.replace(lat, cyr)
    return "".join(mapping.get(c, c) for c in text)

def get_oxford_ai_response(query):
    """Oxford Assistant orqali javob olish"""
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=query)
        run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=ASSISTANT_ID)
        if run.status == 'completed':
            msgs = client.beta.threads.messages.list(thread_id=thread.id)
            return msgs.data[0].content[0].text.value
        return "Javob olishda xatolik yuz berdi."
    except Exception as e:
        return f"AI xatosi: {str(e)}"

def send_telegram(chat_id, text, keyboard=None, edit_id=None):
    """Xabar yuborish yoki tahrirlash"""
    method = "editMessageText" if edit_id else "sendMessage"
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if edit_id: payload["message_id"] = edit_id
    if keyboard: payload["reply_markup"] = keyboard
    return requests.post(url, json=payload)

# --- ASOSIY WEBHOOK ---

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    
    # CALLBACK (Tugmalar bosilganda)
    if "callback_query" in data:
        q = data["callback_query"]
        chat_id = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        c_data = q["data"]
        
        if c_data == "activate_drugs":
            user_modes[chat_id] = "drug_search"
            kb = {"inline_keyboard": [[{"text": "🔍 Savdo nomi", "callback_data": "mode_brand"}, {"text": "🧪 MNN", "callback_data": "mode_mnn"}]]}
            send_telegram(chat_id, "💊 **Dori qidirish bo'limi.**\nQidiruv usulini tanlang:", kb, edit_id=mid)
        
        elif c_data == "activate_oxford":
            user_modes[chat_id] = "oxford"
            send_telegram(chat_id, "📖 **Oxford AI Tutor rejimi faol.**\nTermin yozing:", edit_id=mid)
            
        return {"status": "ok"}

    # MESSAGE (Xabarlar kelganda)
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            user_modes[chat_id] = "default"
            kb = {"inline_keyboard": [
                [{"text": "💊 Dori qidirish", "callback_data": "activate_drugs"}],
                [{"text": "📖 Oxford AI Tutor", "callback_data": "activate_oxford"}]
            ]}
            send_telegram(chat_id, "Assalomu alaykum! Kerakli bo'limni tanlang:", kb)
            return {"status": "ok"}

        if text and not text.startswith("/"):
            mode = user_modes.get(chat_id, "drug_search")
            
            if mode == "oxford":
                # Oxford AI tahlili
                wait = send_telegram(chat_id, "🔍 Oxford tahlil qilmoqda...")
                res = get_oxford_ai_response(text)
                send_telegram(chat_id, res)
            else:
                # Dori qidirish logikasi (Sizning Excel funksiyangizni bu yerda chaqirasiz)
                cyrillic_query = to_cyrillic(text)
                # 1. Exceldan qidirish: results = find_drugs(cyrillic_query)
                # 2. AI Tahlili (WebApp AI): analysis = get_drug_analysis(text)
                send_telegram(chat_id, f"🔍 '{text}' (Kirill: {cyrillic_query}) bo'yicha bazadan qidirilyapti...")
                # Natija va uning ostidan WebApp'dagi kabi AI tahlilini yuborish...

    return {"status": "ok"}
