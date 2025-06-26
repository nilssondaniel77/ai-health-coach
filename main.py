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

    # Nutrition (kan vara 0 om Lifesum inte synkat ännu)
    "kcal_in": _sum_qty("dietary_energy"),        # kcal
    "protein": _sum_qty("protein"),               # g
    "fat":     _sum_qty("total_fat"),             # g
    "carbs":   _sum_qty("carbohydrates"),         # g
    "water":   _sum_qty("water"),                 # ml

    # Aktivitet
    "steps":   _sum_qty("step_count"),            # count
    "active":  round(_sum_qty("active_energy") * 0.239006, 0),  # kJ → kcal

    # Sömn (tar första posten)
    "sleep_h": round(metrics.get("sleep_analysis", {}).get("data", [{}])[0].get("asleep", 0), 2),

    # Vikt & vilopuls (kommer som egna metrics om du exporterar dem)
    "weight":  _sum_qty("body_mass"),             # kg (eller 0)
    "rest_hr": _sum_qty("resting_heart_rate"),    # bpm (eller 0)
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
