from flask import Flask, request, jsonify
import datetime
import random

app = Flask(__name__)


def event_impact_score(events):
    # Economic events list of dict: [{"type":"GDP","importance":3,"direction":"positive"},...]
    score = 0.0
    liquidity_impact = 0.0
    for e in events:
        importance = float(e.get("importance", 1))
        direction = e.get("direction", "neutral")
        etype = e.get("type", "macro")

        if etype == "inflation":
            score += (1 if direction == "positive" else -1) * importance * 0.8
            liquidity_impact -= importance * 2
        elif etype == "gdp":
            score += (1 if direction == "positive" else -1) * importance * 1.1
            liquidity_impact += importance * 1
        elif etype == "rate":
            score += (-1 if direction == "positive" else 1) * importance * 1.2
            liquidity_impact -= importance * 1.5
        else:
            score += (1 if direction == "positive" else -1) * importance * 0.5

    return score, max(min(100 - liquidity_impact * 2, 100), 0)


def movement_from_market(facts, event_score):
    base = facts.get("momentum", 0.0) * 50
    volatility = facts.get("volatility", 0.02)
    gdp = facts.get("gdp_growth", 0.02)
    inflation = facts.get("inflation", 0.02)
    rate = facts.get("rate", 0.03)

    movement_score = (event_score * 6 + base + (gdp - inflation) * 100 + (0.03 - rate) * 80)
    movement_score = max(min(movement_score + random.uniform(-2, 2), 100), -100)
    return movement_score


@app.route("/predict_event", methods=["POST"])
def predict_event():
    payload = request.get_json(force=True, silent=True) or {}
    symbol = payload.get("symbol", "EURUSD")
    timeframe = payload.get("timeframe", "5")
    events = payload.get("events", [])
    facts = payload.get("facts", {})
    current_price = float(payload.get("current_price", 1.0))

    event_score, liquidity = event_impact_score(events)
    movement = movement_from_market(facts, event_score)

    # 1 point difference forecast for strategy: mean predicted move
    point_diff = abs(movement) * 0.1
    point_diff = round(max(min(point_diff, 5.0), 0.1), 2)

    signal = "NEUTRAL"
    if movement > 12 and liquidity > 55:
        signal = "BUY"
    elif movement < -12 and liquidity > 55:
        signal = "SELL"

    return jsonify({
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "signal": signal,
        "movement_score": round(movement, 2),
        "liquidity_score": round(liquidity, 2),
        "predicted_point_diff": point_diff,
        "events": events,
        "facts": facts,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5101, debug=True)
