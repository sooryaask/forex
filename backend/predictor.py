from flask import Flask, request, jsonify
import random
import datetime

app = Flask(__name__)

# Sample economic facts and fundamental feature preprocessing
# In production, replace with real data sources like FRED, Alpha Vantage, economic calendar, and CFD liquidity APIs.

def score_from_factors(factors):
    # factors: dict with keys like gdp, inflation, interest_rate, volume, bid_ask_spread
    # Simple engineered score: movement from macro + momentum + liquidity
    macro_score = 0.4 * (factors.get("gdp_growth", 0.02) - 0.01)
    macro_score += 0.3 * (0.03 - factors.get("inflation", 0.02))
    macro_score += 0.3 * (0.05 - factors.get("rate", 0.03))

    liquidity_score = 100 - factors.get("bid_ask_spread", 20)
    momentum = factors.get("volume_delta_pct", 0.0) * 10

    movement_score = max(min((macro_score + momentum) * 100, 100), -100)
    liquidity_score = max(min(liquidity_score, 100), 0)

    # Add random jitter for demonstration
    movement_score = movement_score + random.uniform(-3, 3)
    liquidity_score = liquidity_score + random.uniform(-3, 3)

    return round(movement_score, 1), round(liquidity_score, 1)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True, silent=True) or {}
    symbol = data.get("symbol", "EURUSD")
    timeframe = data.get("timeframe", "5")
    facts = data.get("facts", {})

    # Default sample facts if none provided
    defaults = {
        "gdp_growth": 0.025,
        "inflation": 0.023,
        "rate": 0.035,
        "volume_delta_pct": 0.05,
        "bid_ask_spread": 12,
    }
    defaults.update(facts)
    movement, liquidity = score_from_factors(defaults)

    response = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "movement_score": movement,
        "liquidity_score": liquidity,
        "signal": "BUY" if movement > 10 and liquidity > 60 else "SELL" if movement < -10 and liquidity > 60 else "NEUTRAL",
        "details": defaults,
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
