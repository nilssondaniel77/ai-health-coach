# main.py
# Daniel's AI-coach webhook (FastAPI)

from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json
import os

# === Miljönyckel (lägg samma värde i Render & Health Auto Export) ===
API_KEY = os.getenv("API_KEY", "supersecret")

app = FastAPI()


@app.get("/health")
def health():
    """Enkel hälsokontroll för Render."""
    return {"status": "ok"}


def _val(obj: dict, path: str, default=0):
    """
    Hämtar ett djupt värde ur nästlade dicts med 'a/b/c'-syntax.
    Returnerar default om något saknas.
    """
    cur = obj
    for p in path.split("/"):
        cur = cur.get(p, {})
    return cur or default


@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    # --- kontrollera auth-token ---
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    # --- hämta JSON-payload ---
    data = await request.json()

    # --- spara rådata för felsökning ---
    ts_iso = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts_iso}.json", "w") as f:
        json.dump(data, f)

    # --- extrahera nyckelvärden ---
    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kcal_in": _val(data, "aggregated/nutrition/energyConsumed"),
        "protein": _val(data, "aggregated/nutrition/protein"),
        "fat": _val(data, "aggregated/nutrition/fatTotal"),
        "carbs": _val(data, "aggregated/nutrition/carbsTotal"),
        "water": _val(data, "aggregated/nutrition/water"),
        "steps": _val(data, "aggrega_
