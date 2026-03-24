"""
Aurion Markets — Prediction Engine
Generates trading signals from technical + fundamental analysis.
"""

import numpy as np
import pandas as pd


def compute_signal(df: pd.DataFrame) -> dict:
    """
    Analyse a DataFrame with indicators and return a trading signal.
    Returns dict with: signal, confidence, entry, stop_loss, take_profit,
    movement_score, analysis_points.
    """
    if df.empty or len(df) < 5:
        return _neutral("Insufficient data for analysis.")

    last = df.iloc[-1]
    close = last["close"]
    analysis = []
    score = 0  # positive = bullish, negative = bearish

    # ── RSI ────────────────────────────────────────────────────────────────
    if "rsi" in df.columns:
        rsi = last["rsi"]
        if rsi < 30:
            score += 2
            analysis.append(f"RSI oversold at {rsi:.1f} — bullish reversal likely")
        elif rsi < 40:
            score += 1
            analysis.append(f"RSI approaching oversold at {rsi:.1f}")
        elif rsi > 70:
            score -= 2
            analysis.append(f"RSI overbought at {rsi:.1f} — bearish reversal likely")
        elif rsi > 60:
            score -= 1
            analysis.append(f"RSI approaching overbought at {rsi:.1f}")
        else:
            analysis.append(f"RSI neutral at {rsi:.1f}")

    # ── MACD ───────────────────────────────────────────────────────────────
    if "macd" in df.columns and "macd_signal" in df.columns:
        macd = last["macd"]
        sig = last["macd_signal"]
        prev_macd = df.iloc[-2]["macd"] if len(df) > 1 else macd
        prev_sig = df.iloc[-2]["macd_signal"] if len(df) > 1 else sig

        if prev_macd <= prev_sig and macd > sig:
            score += 2
            analysis.append("MACD bullish crossover detected")
        elif prev_macd >= prev_sig and macd < sig:
            score -= 2
            analysis.append("MACD bearish crossover detected")
        elif macd > sig:
            score += 1
            analysis.append("MACD above signal line — bullish momentum")
        else:
            score -= 1
            analysis.append("MACD below signal line — bearish momentum")

    # ── Bollinger Bands ────────────────────────────────────────────────────
    if "bb_upper" in df.columns:
        if close <= last["bb_lower"]:
            score += 2
            analysis.append("Price at lower Bollinger Band — potential bounce")
        elif close >= last["bb_upper"]:
            score -= 2
            analysis.append("Price at upper Bollinger Band — potential pullback")
        else:
            bb_range = last["bb_upper"] - last["bb_lower"]
            if bb_range > 0:
                bb_pos = (close - last["bb_lower"]) / bb_range
                analysis.append(f"Price at {bb_pos:.0%} of Bollinger Band range")

    # ── EMA Trend ──────────────────────────────────────────────────────────
    if "ema_9" in df.columns and "ema_21" in df.columns:
        if last["ema_9"] > last["ema_21"]:
            score += 1
            analysis.append("EMA 9 above EMA 21 — short-term uptrend")
        else:
            score -= 1
            analysis.append("EMA 9 below EMA 21 — short-term downtrend")

    # ── Price action (last 5 candles) ──────────────────────────────────────
    recent = df.tail(5)
    green_candles = (recent["close"] > recent["open"]).sum()
    if green_candles >= 4:
        score += 1
        analysis.append(f"Strong bullish momentum: {green_candles}/5 green candles")
    elif green_candles <= 1:
        score -= 1
        analysis.append(f"Strong bearish momentum: {5 - green_candles}/5 red candles")

    # ── Volume analysis ────────────────────────────────────────────────────
    if "volume" in df.columns and df["volume"].mean() > 0:
        vol_ratio = last["volume"] / df["volume"].rolling(20).mean().iloc[-1]
        if vol_ratio > 1.5:
            analysis.append(f"Volume surge: {vol_ratio:.1f}x average — strong conviction")
            score = int(score * 1.3)
        elif vol_ratio < 0.5:
            analysis.append(f"Low volume: {vol_ratio:.1f}x average — weak conviction")

    # ── Compute final signal ───────────────────────────────────────────────
    max_score = 9
    confidence = min(abs(score) / max_score, 0.97)
    confidence = max(confidence, 0.15)

    atr = last.get("atr", close * 0.01)

    if score >= 2:
        signal = "BUY"
        entry = close
        stop_loss = close - (atr * 2)
        take_profit = close + (atr * 3)
    elif score <= -2:
        signal = "SELL"
        entry = close
        stop_loss = close + (atr * 2)
        take_profit = close - (atr * 3)
    else:
        return _neutral("Mixed signals — no clear directional bias.", analysis)

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "movement_score": score,
        "entry": round(entry, 5),
        "stop_loss": round(stop_loss, 5),
        "take_profit": round(take_profit, 5),
        "risk_reward": round(abs(take_profit - entry) / abs(entry - stop_loss), 2) if abs(entry - stop_loss) > 0 else 0,
        "analysis": analysis,
    }


def _neutral(reason: str, analysis=None) -> dict:
    return {
        "signal": "NEUTRAL",
        "confidence": 0.0,
        "movement_score": 0,
        "entry": 0,
        "stop_loss": 0,
        "take_profit": 0,
        "risk_reward": 0,
        "analysis": (analysis or []) + [reason],
    }


def analyse_screenshot_data(price_levels: list) -> dict:
    """
    Analyse extracted price levels from a screenshot.
    Expects a list of recent price points (oldest → newest).
    """
    if not price_levels or len(price_levels) < 3:
        return _neutral("Need at least 3 price points from screenshot.")

    prices = np.array(price_levels, dtype=float)
    df = pd.DataFrame({
        "open": prices[:-1],
        "high": np.maximum(prices[:-1], prices[1:]),
        "low": np.minimum(prices[:-1], prices[1:]),
        "close": prices[1:],
        "volume": np.ones(len(prices) - 1) * 1000,
    })

    from core.data_fetcher import add_indicators
    df = add_indicators(df)
    if df.empty:
        # Fallback: simple trend analysis
        trend = (prices[-1] - prices[0]) / prices[0] * 100
        if trend > 0.5:
            return {
                "signal": "BUY",
                "confidence": min(abs(trend) / 5, 0.85),
                "movement_score": 3,
                "entry": prices[-1],
                "stop_loss": prices[-1] * 0.98,
                "take_profit": prices[-1] * 1.03,
                "risk_reward": 1.5,
                "analysis": [f"Uptrend of {trend:.2f}% detected from price sequence"],
            }
        elif trend < -0.5:
            return {
                "signal": "SELL",
                "confidence": min(abs(trend) / 5, 0.85),
                "movement_score": -3,
                "entry": prices[-1],
                "stop_loss": prices[-1] * 1.02,
                "take_profit": prices[-1] * 0.97,
                "risk_reward": 1.5,
                "analysis": [f"Downtrend of {trend:.2f}% detected from price sequence"],
            }
        else:
            return _neutral(f"Flat trend ({trend:.2f}%) — no clear direction.")

    return compute_signal(df)
