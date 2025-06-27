from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json, os

API_KEY = os.getenv("API_KEY", "supersecret")
app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def _first_metric(metrics: dict, name: str, field: str = "qty", default=0):
    """Summerar fältet *field* i alla dataposter för vald metric."""
    block = metrics.get(name, {})
    return sum(item.get(field, 0) for item in block.get("data", [])) or default


def _last_qty(metrics: dict, name: str, default=0):
    """Tar senaste (högst tidstämplade) qty-värdet för metricen."""
    block = metrics.get(name, {})
    if not block.get("data"):
        return default
    return block["data"][-1].get("qty", default)


@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await request.json()

    # 1. Spara råfil för felsökning/historik
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts}.json", "w") as f:
        json.dump(data, f)

    # 2. Gör uppslags­dict {name: block}
    metrics = {m["name"]: m for m in data.get("data", {}).get("metrics", [])}

    # 3. Plocka ut totalsiffror
    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kcal_in":   _first_metric(metrics, "dietary_energy"),
        "protein":   _first_metric(metrics, "protein"),
        "fat":       _first_metric(metrics, "total_fat"),
        "carbs":     _first_metric(metrics, "carbohydrates"),
    #    "water":     _first_metric(metrics, "water"),
        "weight":    _last_metric(metrics, "weight_body_mass"),
    #    "rest_hr":   _first_metric(metrics, "resting_heart_rate"),
        "sleep_h": round(
            metrics.get("sleep_analysis", {}).get("data", [{}])[0].get("asleep", 0), 2
        ),
    }

    # 4. Steg & aktiv energi → ta senaste ackumulerade värdet (INTE summera minut för minut)
    summary.update({
        "steps":  _last_qty(metrics, "step_count"),
        # kJ → kcal (1 kJ = 0.239006 kcal)
        "active": round(_last_qty(metrics, "active_energy") * 0.239006, 1)
    })

    # 5. Bygg prompten
    prompt = (
        f"📊 Hälsodata {summary['date']}\n"
        f"• Kalorier in: {summary['kcal_in']} kcal\n"
        f"• Makro (P/F/K): {summary['protein']}/{summary['fat']}/{summary['carbs']} g\n"
        f"• Aktiv energi: {summary['active']} kcal • Steg: {summary['steps']}\n"
        f"• Sömn: {summary['sleep_h']} h • Vilopuls: {summary['rest_hr']} bpm\n"
        f"• Vikt: {summary['weight']} kg"
    )

    with open("latest_prompt.txt", "w") as f:
        f.write(prompt)

    print("Prompt saved:\n", prompt)
    return {"status": "ok", "summary": summary}
