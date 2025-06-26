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
        "steps": _val(data, "aggregated/activity/steps"),
        "active": _val(data, "aggregated/activity/activeEnergyBurned"),
        "sleep_h": round(_val(data, "aggregated/sleep/sleepDuration_g", 0) / 3600, 2),
        "weight": _val(data, "latest/weight/weight"),
        "rest_hr": _val(data, "latest/heartRate/restingHeartRate"),
    }

    # --- skapa GPT-prompt ---
    prompt = (
        f"📊 Hälsodata {summary['date']}\n"
        f"• Kalorier in: {summary['kcal_in']} kcal\n"
        f"• Makro (P/F/K): {summary['protein']}/{summary['fat']}/{summary['carbs']} g\n"
        f"• Vatten: {summary['water']} ml\n"
        f"• Aktiv energi: {summary['active']} kcal • Steg: {summary['steps']}\n"
        f"• Sömn: {summary['sleep_h']} h • Vilopuls: {summary['rest_hr']} bpm\n"
        f"• Vikt: {summary['weight']} kg"
    )

    # --- spara prompt så du kan hämta den ---
    with open("latest_prompt.txt", "w") as f:
        f.write(prompt)

    # logga i Render-console
    print("Prompt saved:\n", prompt)

    return {"status": "ok", "summary": summary}
