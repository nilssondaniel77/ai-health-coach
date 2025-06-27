from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json, os

API_KEY = os.getenv("API_KEY", "supersecret")
app = FastAPI()

# ----------------- Helper functions -----------------

def _first_metric(metrics: dict, name: str, field: str = "qty", default=0):
    """Sum all `field` values for the given metric name."""
    block = metrics.get(name, {})
    return sum(row.get(field, 0) for row in block.get("data", [])) or default

def _last_metric(metrics: dict, name: str, field: str = "qty", default=0):
    """Return the latest (chronologically last) `field` value for the metric."""
    block = metrics.get(name, {})
    if block.get("data"):
        return block["data"][ -1 ].get(field, default)
    return default
# ----------------------------------------------------

@app.post("/webhook")
async def webhook(request: Request, auth: str = ""):
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await request.json()

    # Save raw payload for troubleshooting
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    with open(f"raw_{ts}.json", "w") as f:
        json.dump(data, f)

    # Build lookup dict: {metric_name: block}
    metrics = {m["name"]: m for m in data.get("data", {}).get("metrics", [])}

    # ----------------- Daily summary -----------------
    summary = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kcal_in":   round(_first_metric(metrics, "dietary_energy") / 4.184, 1),  # kJ → kcal
        "protein":   _first_metric(metrics, "protein"),
        "fat":       _first_metric(metrics, "total_fat"),
        "carbs":     _first_metric(metrics, "carbohydrates"),
        # "water":     _first_metric(metrics, "water"),  # disabled for now
        "weight":    _last_metric(metrics, "weight_body_mass"),
        # "rest_hr":   _last_metric(metrics, "resting_heart_rate"),  # no source yet
        "sleep_h":   round(metrics.get("sleep_analysis", {}).get("data", [{}])[0].get("asleep", 0), 2),
        "steps":     _last_metric(metrics, "step_count"),
        "active":    round(_last_metric(metrics, "active_energy") * 0.239006, 1),  # kJ → kcal
    }

    # ----------------- Build prompt ------------------
    prompt_lines = [
        f"📊 Hälsodata {summary['date']}",
        f"• Kalorier in: {summary['kcal_in']} kcal",
        f"• Makro (P/F/K): {summary['protein']}/{summary['fat']}/{summary['carbs']} g",
        f"• Aktiv energi: {summary['active']} kcal • Steg: {summary['steps']}",
        f"• Sömn: {summary['sleep_h']} h",
    ]
    if summary["weight"]:
        prompt_lines.append(f"• Vikt: {summary['weight']} kg")
    prompt = "\n".join(prompt_lines)

    with open("latest_prompt.txt", "w") as f:
        f.write(prompt)

    print("Prompt saved:\n", prompt)
    return {"status": "ok", "summary": summary}

@app.get("/health")
def health():
    return {"status": "ok"}
