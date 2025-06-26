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

    def _val(obj, path, default=0):
    cur = obj
    for p in path.split("/"):
        cur = cur.get(p, {})
    return cur or default

# ------------- Sammanfattning -------------
summary = {
    "date": datetime.utcnow().strftime("%Y-%m-%d"),
    "kcal_in":  _val(data, "aggregated/nutrition/energyConsumed"),
    "protein":  _val(data, "aggregated/nutrition/protein"),
    "fat":      _val(data, "aggregated/nutrition/fatTotal"),
    "carbs":    _val(data, "aggregated/nutrition/carbsTotal"),
    "water":    _val(data, "aggregated/nutrition/water"),
    "steps":    _val(data, "aggregated/activity/steps"),
    "active":   _val(data, "aggregated/activity/activeEnergyBurned"),
    "sleep_h":  round(_val(data, "aggregated/sleep/sleepDuration_g", 0)/3600, 2),
    "weight":   _val(data, "latest/weight/weight"),
    "rest_hr":  _val(data, "latest/heartRate/restingHeartRate")
}

prompt = (
    f"📊 Hälsodata {summary['date']}\n"
    f"• Kalorier in: {summary['kcal_in']} kcal\n"
    f"• Makro (P/F/K): {summary['protein']}/{summary['fat']}/{summary['carbs']} g\n"
    f"• Vatten: {summary['water']} ml\n"
    f"• Aktiv energi: {summary['active']} kcal • Steg: {summary['steps']}\n"
    f"• Sömn: {summary['sleep_h']} h • Vilopuls: {summary['rest_hr']} bpm\n"
    f"• Vikt: {summary['weight']} kg"
)

with open("latest_prompt.txt", "w") as f:
    f.write(prompt)
print("Prompt saved:\n", prompt)

    return {"status": "ok"}
