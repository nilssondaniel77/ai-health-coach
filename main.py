from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json, os

API_KEY = os.getenv("API_KEY", "supersecret")
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def _first_metric(metrics: dict, name: str, field: str = "qty", default=0):
    """Hämta summan av ett fält i metrics-listan."""
    block = metrics.get(name, {})
    total = sum(item.get(field, 0) for item in block.get("data", []))
    return total or default


@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await request.json()

    # Spara rå data
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts}.json", "w") as f:
        json.dump(data, f)

    # Bygg upp metrics-dict {name: block}
    metrics = {m["name"]: m for m in data.get("data", {}).get("metrics", [])}

    # Summera värden
    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kcal_in": _first_metric(metrics, "dietary_energy"),        # kcal
        "protein": _first_metric(metrics, "protein"),               # g
        "fat": _first_metric(metrics, "total_fat"),                 # g
        "carbs": _first_metric(metrics, "carbohydrates"),           # g
        "water": _first_metric(metrics, "water"),                   # ml
        "steps": _first_metric(metrics, "step_count"),              # count
        "active": round(_first_metric(metrics, "active_energy") * 0.239006, 0),  # kJ→kcal
        "sleep_h": round(metrics.get("sleep_analysis", {}).get("data", [{}])[0].get("asleep", 0), 2),
        "weight": _first_metric(metrics, "body_mass"),              # kg
        "rest_hr": _first_metric(metrics, "resting_heart_rate"),    # bpm
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
