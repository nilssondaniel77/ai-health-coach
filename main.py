from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json, os

API_KEY = os.getenv("API_KEY", "supersecret")  # sätt egen i Render

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await request.json()

    # spara rå payload för felsökning
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts}.json", "w") as f:
        json.dump(data, f)

    # TODO: här kan du summera datan till GPT-prompt
    # ex: prompt = create_prompt_from(data)

    return {"status": "ok"}
