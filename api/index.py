import os, requests
from fastapi import FastAPI, Request

TOKEN = os.getenv("TELEGRAM_TOKEN")
user_modes = {} # Foydalanuvchi rejimini saqlash uchun

app = FastAPI()

# 1. Telegramga javob yuborish funksiyasi
def send_msg(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: payload["reply_markup"] = reply_markup
    return requests.post(url, json=payload)

# 2. Xabarni tahrirlash (Menyular chalkashmasligi uchun)
def edit_msg(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: payload["reply_markup"] = reply_markup
    return requests.post(url, json=payload)

@app.post("/api/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    
    # --- CALLBACK QUERY (Tugmalar) ---
    if "callback_query" in data:
        q = data["callback_query"]
        chat_id = q["message"]["chat"]["id"]
        mid = q["message"]["message_id"]
        c_data = q["data"]
        
        # A) Dori qidirish tanlanganda
        if c_data == "activate_drugs":
            user_modes[chat_id] = "drug_search"
            keyboard = {"inline_keyboard": [
                [{"text": "🔍 Savdo nomi", "callback_data": "mode_brand"}, {"text": "🧪 MNN", "callback_data": "mode_mnn"}],
                [{"text": "📄 PDF Konspekt yuklash", "callback_data": "download_pdf"}]
            ]}
            edit_msg(chat_id, mid, "💊 **Dori qidirish bo'limi.** Qidiruv usulini tanlang:", keyboard)
        
        # B) Oxford AI tanlanganda
        elif c_data == "activate_oxford":
            user_modes[chat_id] = "oxford"
            edit_msg(chat_id, mid, "📖 **Oxford AI Tutor rejimi faol.**\nTermin yoki kasallik nomini yozing:")

        # C) PDF yuklash
        elif c_data == "download_pdf":
            # Bu yerda send_pdf_konspekt funksiyasini chaqiring
            send_msg(chat_id, "📄 PDF konspekt tayyorlanmoqda, iltimos kuting...")
            
        return {"status": "ok"}

    # --- MESSAGE (Xabarlar) ---
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            user_modes[chat_id] = "default"
            keyboard = {"inline_keyboard": [
                [{"text": "💊 Dori qidirish", "callback_data": "activate_drugs"}],
                [{"text": "📖 Oxford AI Tutor", "callback_data": "activate_oxford"}]
            ]}
            send_msg(chat_id, "Assalomu alaykum! Kerakli bo'limni tanlang:", keyboard)
            return {"status": "ok"}

        # Matnli xabarlarni qayta ishlash
        if text and not text.startswith("/"):
            mode = user_modes.get(chat_id)
            
            if mode == "oxford":
                # Oxford AI tahlili
                res = get_oxford_response(text)
                send_msg(chat_id, res)
            else:
                # Dori qidirish + AI Tahlili (WebApp o'rniga)
                # 1. Exceldan qidirish (to_cyrillic bilan)
                # 2. Topilgan dori haqida ma'lumot yuborish
                # 3. AI Tahlilini (WebApp logikasi) yuborish
                send_msg(chat_id, f"🔍 '{text}' bo'yicha ma'lumot va AI tahlili tayyorlanmoqda...")
                # Bu yerda dori_qidirish_va_tahlil() funksiyangizni chaqirasiz

    return {"status": "ok"}
