from fastapi import FastAPI
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

@app.get("/api/chat")
async def chat(message: str):
    try:
        # 1. Thread yaratish
        thread = client.beta.threads.create()
        
        # 2. Xabar qo'shish
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # 3. Assistant-ni ishga tushirish (Run)
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            return {"reply": messages.data[0].content[0].text.value}
        else:
            return {"reply": "Xatolik yuz berdi: " + run.status}
            
    except Exception as e:
        return {"reply": f"Backend xatosi: {str(e)}"}
