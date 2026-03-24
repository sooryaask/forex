from flask import Flask, request, jsonify
import datetime
import os
import joblib
import numpy as np

from event_history import (
    predict_event_impact,
    load_db,
    get_db_stats,
    add_manual_event,
    EVENT_CATEGORIES,
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Asset class detection — broad pattern matching instead of hardcoded symbols
# ---------------------------------------------------------------------------
FOREX_CODES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF",
    "SEK", "NOK", "DKK", "SGD", "HKD", "MXN", "ZAR", "TRY",
}

METAL_SYMBOLS = {"GC=F", "SI=F", "PL=F", "HG=F", "XAUUSD", "XAGUSD", "GOLD", "SILVER"}
CRYPTO_SUFFIXES = ("-USD", "-USDT", "-BTC", "-ETH")


def get_asset_class(symbol):
    symbol = symbol.upper().replace("/", "")

    # Metals
    if symbol in METAL_SYMBOLS or "GOLD" in symbol or "SILVER" in symbol:
        return "metals"

    # Crypto (ends with -USD, -USDT, etc. or common names)
    for suffix in CRYPTO_SUFFIXES:
        if symbol.endswith(suffix):
            return "crypto"
    if symbol in ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD"):
        return "crypto"

    # Forex — 6-char pairs where both halves are currency codes
    stripped = symbol.replace("=X", "")
    if len(stripped) == 6:
        base, quote = stripped[:3], stripped[3:]
        if base in FOREX_CODES and quote in FOREX_CODES:
            return "forex"

    # Default to stocks for anything else (indices, equities, ETFs)
    return "stocks"


# ---------------------------------------------------------------------------
# Load ML models if they exist (kept as fallback / enhancement)
# ---------------------------------------------------------------------------
models = {}
scalers = {}
for asset_class in ["forex", "stocks", "metals", "crypto"]:
    model_dir = "models"
    clf_path = f"{model_dir}/xgb_classifier_{asset_class}.pkl"
    if os.path.exists(clf_path):
        models[asset_class] = {
            "classifier": joblib.load(clf_path),
            "regressor": joblib.load(f"{model_dir}/rf_regressor_{asset_class}.pkl"),
        }
        scalers[asset_class] = joblib.load(f"{model_dir}/scaler_{asset_class}.pkl")
    else:
        models[asset_class] = None


# ---------------------------------------------------------------------------
# Fallback rule-based scoring (used when event DB is empty)
# ---------------------------------------------------------------------------
def event_impact_score(events):
    score = 0.0
    liquidity_impact = 0.0
    for e in events:
        importance = float(e.get("importance", 1))
        direction = e.get("direction", "neutral")
        etype = e.get("type", "macro")

        if etype == "inflation" or etype == "cpi":
            score += (1 if direction == "positive" else -1) * importance * 0.8
            liquidity_impact -= importance * 2
        elif etype == "gdp":
            score += (1 if direction == "positive" else -1) * importance * 1.1
            liquidity_impact += importance * 1
        elif etype == "rate":
            score += (-1 if direction == "positive" else 1) * importance * 1.2
            liquidity_impact -= importance * 1.5
        elif etype in ("employment", "nfp"):
            score += (1 if direction == "positive" else -1) * importance * 0.9
            liquidity_impact -= importance * 1
        else:
            score += (1 if direction == "positive" else -1) * importance * 0.5

    return score, max(min(100 - liquidity_impact * 2, 100), 0)


def movement_from_market(facts, event_score):
    base = facts.get("momentum", 0.0) * 50
    gdp = facts.get("gdp_growth", 0.02)
    inflation = facts.get("inflation", 0.02)
    rate = facts.get("rate", 0.03)

    movement_score = event_score * 6 + base + (gdp - inflation) * 100 + (0.03 - rate) * 80
    return max(min(movement_score, 100), -100)


# ---------------------------------------------------------------------------
# /predict_event — main prediction endpoint
# ---------------------------------------------------------------------------
@app.route("/predict_event", methods=["POST"])
def predict_event():
    payload = request.get_json(force=True, silent=True) or {}
    symbol = payload.get("symbol", "EURUSD")
    timeframe = payload.get("timeframe", "5")
    events = payload.get("events", [])
    facts = payload.get("facts", {})
    current_price = float(payload.get("current_price", 1.0))
    window = payload.get("window", "15m")  # outcome window to predict

    asset_class = get_asset_class(symbol)

    # -------------------------------------------------------------------
    # Try the historical similarity engine first
    # -------------------------------------------------------------------
    db = load_db()
    history_predictions = []

    for ev in events:
        query = {
            "type": ev.get("type", "macro"),
            "category": EVENT_CATEGORIES.get(ev.get("type", ""), ev.get("type", "")),
            "importance": ev.get("importance", 2),
            "direction": ev.get("direction", "neutral"),
            "surprise": ev.get("surprise", 0.0),
            "region": ev.get("region", "US"),
        }
        pred = predict_event_impact(query, asset_class, db=db, window=window)
        if pred["n_similar_events"] > 0:
            history_predictions.append(pred)

    # -------------------------------------------------------------------
    # Combine predictions
    # -------------------------------------------------------------------
    if history_predictions:
        # Weighted average across events, weighted by confidence
        total_conf = sum(p["confidence"] for p in history_predictions)
        if total_conf > 0:
            movement = sum(
                p["movement_score"] * p["confidence"] for p in history_predictions
            ) / total_conf
            liquidity = sum(
                p["liquidity_score"] * p["confidence"] for p in history_predictions
            ) / total_conf
            point_diff = sum(
                p["predicted_point_diff"] * p["confidence"]
                for p in history_predictions
            ) / total_conf
            confidence = max(p["confidence"] for p in history_predictions)
        else:
            movement = sum(p["movement_score"] for p in history_predictions) / len(
                history_predictions
            )
            liquidity = sum(p["liquidity_score"] for p in history_predictions) / len(
                history_predictions
            )
            point_diff = sum(
                p["predicted_point_diff"] for p in history_predictions
            ) / len(history_predictions)
            confidence = 0.3

        # Blend with ML model if available
        if models[asset_class]:
            event_score, _ = event_impact_score(events)
            feature_keys = ["momentum", "volatility", "gdp_growth", "inflation", "rate"]
            features = [event_score, liquidity] + [
                facts.get(k, 0.0) for k in feature_keys
            ]
            X = np.array([features])
            X_scaled = scalers[asset_class].transform(X)
            ml_prob = models[asset_class]["classifier"].predict_proba(X_scaled)[0][1]
            ml_mag = models[asset_class]["regressor"].predict(X_scaled)[0]
            ml_movement = (1 if ml_prob > 0.5 else -1) * ml_mag * 100
            # Blend: 60% history, 40% ML
            movement = movement * 0.6 + ml_movement * 0.4
            confidence = min(confidence * 0.6 + max(ml_prob, 1 - ml_prob) * 0.4, 1.0)

        prediction_source = "historical_similarity"
        similar_events_info = []
        for p in history_predictions:
            similar_events_info.extend(p.get("top_similar", []))

    else:
        # -------------------------------------------------------------------
        # Fallback: rule-based + ML (no historical data available)
        # -------------------------------------------------------------------
        event_score, liquidity = event_impact_score(events)

        if models[asset_class]:
            feature_keys = ["momentum", "volatility", "gdp_growth", "inflation", "rate"]
            features = [event_score, liquidity] + [
                facts.get(k, 0.0) for k in feature_keys
            ]
            X = np.array([features])
            X_scaled = scalers[asset_class].transform(X)
            direction_prob = models[asset_class]["classifier"].predict_proba(X_scaled)[
                0
            ][1]
            magnitude = models[asset_class]["regressor"].predict(X_scaled)[0]
            movement = (1 if direction_prob > 0.5 else -1) * magnitude * 100
            confidence = max(direction_prob, 1 - direction_prob)
        else:
            movement = movement_from_market(facts, event_score)
            confidence = min(abs(movement) / 50, 1.0)

        point_diff = abs(movement) * 0.1
        prediction_source = "rule_based"
        similar_events_info = []

    # Clamp values
    movement = max(min(round(movement, 2), 100), -100)
    liquidity = max(min(round(liquidity, 2), 100), 0)
    point_diff = round(max(min(point_diff, 10.0), 0.1), 2)
    confidence = round(confidence, 3)

    # Signal
    signal = "NEUTRAL"
    if movement > 12 and liquidity > 55:
        signal = "BUY"
    elif movement < -12 and liquidity > 55:
        signal = "SELL"

    return jsonify(
        {
            "symbol": symbol,
            "asset_class": asset_class,
            "timeframe": timeframe,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "signal": signal,
            "movement_score": movement,
            "liquidity_score": liquidity,
            "predicted_point_diff": point_diff,
            "confidence": confidence,
            "prediction_source": prediction_source,
            "similar_events": similar_events_info[:5],
            "events": events,
            "facts": facts,
        }
    )


# ---------------------------------------------------------------------------
# /add_event — record a new event and its market outcomes
# ---------------------------------------------------------------------------
@app.route("/add_event", methods=["POST"])
def api_add_event():
    """Add a new event to the historical database with its market outcomes."""
    payload = request.get_json(force=True, silent=True) or {}
    event_type = payload.get("type", "macro")
    region = payload.get("region", "US")
    importance = int(payload.get("importance", 2))
    actual = float(payload.get("actual", 0))
    previous = float(payload.get("previous", 0))
    direction = payload.get("direction")
    event_date = payload.get("date")
    fetch = payload.get("fetch_outcomes", True)

    event = add_manual_event(
        event_type, region, importance, actual, previous,
        direction=direction, event_date=event_date, fetch_outcomes=fetch,
    )

    return jsonify({"status": "ok", "event": event})


# ---------------------------------------------------------------------------
# /db_stats — check what's in the event database
# ---------------------------------------------------------------------------
@app.route("/db_stats", methods=["GET"])
def api_db_stats():
    return jsonify(get_db_stats())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5102, debug=True)
