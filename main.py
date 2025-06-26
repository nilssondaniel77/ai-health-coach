from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import os, json

API_KEY = os.getenv("API_KEY", "supersecret")
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

def _first(obj, paths, default=0):
    """Testar flera 'a/b/c'-paths tills en träffar."""
    for path in paths:
        cur = obj
        for part in path.split("/"):
            cur = cur.get(part, {})
        if cur:
            return cur
    return default

@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await request.json()
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts}.json", "w") as f:
        json.dump(data, f)

    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kcal_in": _first(data, [
            "aggregated/nutrition/energyConsumed",           # äldre namn
            "aggregated/nutrition/dietaryEnergy"             # nya Apple-namnet
        ]),
        "protein": _first(data, ["aggregated/nutrition/protein"]),
        "fat":     _first(data, ["aggregated/nutrition/fatTotal", "aggregated/nutrition/totalFat"]),
        "carbs":   _first(data, ["aggregated/nutrition/carbsTotal", "aggregated/nutrition/carbohydrates"]),
        "water":   _first(data, ["aggregated/nutrition/water"]),
        "steps":   _first(data, ["aggregated/activity/steps", "aggregated/activity/stepCount"]),
        "active":  _first(data, ["aggregated/activity/activeEnergyBurned", "aggregated/activity/activeEnergy"]),
        "sleep_h": round(_first(data, [
                        "aggregated/sleep/sleepDuration_g",
                        "aggregated/sleep/sleepAnalysisSeconds"
                    ], 0) / 3600, 2),
        "weight":  _first(data, ["latest/weight/weight", "latest/weight/bodyMass"]),
        "rest_hr": _first(data, ["latest/heartRate/restingHeartRate"]),
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
    return {"status": "ok", "summary": summary}
