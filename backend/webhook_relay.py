from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

PREDICT_URL = "http://127.0.0.1:5102/predict_event"


# ── Common event type aliases from TradingView alert messages ─────────
EVENT_ALIASES = {
    "cpi": "cpi", "inflation": "cpi", "consumer price": "cpi",
    "gdp": "gdp", "gross domestic": "gdp",
    "rate": "rate", "interest rate": "rate", "fomc": "rate", "boe": "rate", "ecb": "rate",
    "nfp": "nfp", "non-farm": "nfp", "payroll": "nfp",
    "employment": "employment", "unemployment": "employment", "jobs": "employment",
    "ppi": "ppi", "producer price": "ppi",
    "retail": "retail_sales", "retail sales": "retail_sales",
    "pmi": "pmi", "purchasing manager": "pmi",
    "trade": "trade_balance", "trade balance": "trade_balance",
    "housing": "housing", "home sales": "housing", "building permits": "housing",
}


def normalize_event_type(raw):
    """Map common names/aliases to our canonical event types."""
    raw_lower = raw.lower().strip()
    return EVENT_ALIASES.get(raw_lower, raw_lower)


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    """
    Receives TradingView alert webhooks and forwards to the prediction API.

    Expected JSON from TradingView alert:
    {
        "symbol": "EURUSD",
        "price": 1.0850,
        "timeframe": "5",
        "window": "15m",
        "events": [
            {"type": "CPI", "importance": 3, "direction": "positive", "surprise": 0.02}
        ],
        "facts": {"momentum": 0.05, "volatility": 0.02}
    }

    Or simplified format:
    {
        "symbol": "EURUSD",
        "price": 1.0850,
        "event": "CPI",
        "direction": "positive",
        "importance": 3
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    # Support both detailed and simplified event format
    if "events" in data:
        events = data["events"]
        # Normalize event type aliases
        for ev in events:
            ev["type"] = normalize_event_type(ev.get("type", "macro"))
    elif "event" in data:
        events = [{
            "type": normalize_event_type(data.get("event", "macro")),
            "importance": data.get("importance", 2),
            "direction": data.get("direction", "neutral"),
            "surprise": data.get("surprise", 0.0),
            "region": data.get("region", "US"),
        }]
    else:
        events = []

    facts = data.get("facts", {})

    payload = {
        "symbol": data.get("symbol", data.get("ticker", "EURUSD")),
        "timeframe": data.get("timeframe", "5"),
        "current_price": data.get("price", data.get("close", 1.0)),
        "window": data.get("window", "15m"),
        "events": events,
        "facts": facts,
    }

    try:
        r = requests.post(PREDICT_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e), "payload": payload}), 500

    result = r.json()
    print(f"TV webhook -> {result.get('signal')} | "
          f"movement={result.get('movement_score')} | "
          f"confidence={result.get('confidence')} | "
          f"source={result.get('prediction_source')}")

    return jsonify({
        "status": "ok",
        "action": result.get("signal", "NEUTRAL"),
        "movement_score": result.get("movement_score"),
        "liquidity_score": result.get("liquidity_score"),
        "confidence": result.get("confidence"),
        "predicted_point_diff": result.get("predicted_point_diff"),
        "prediction_source": result.get("prediction_source"),
        "similar_events": result.get("similar_events", []),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200, debug=True)
