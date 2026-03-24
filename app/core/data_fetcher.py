"""
Aurion Markets — Market Data Fetcher
Pulls live and historical OHLCV data from Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange


# ── Symbol registry ──────────────────────────────────────────────────────────
ASSET_CATALOG = {
    "Forex": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X",
        "NZD/USD": "NZDUSD=X", "EUR/GBP": "EURGBP=X", "EUR/JPY": "EURJPY=X",
    },
    "Stocks": {
        "S&P 500": "SPY", "NASDAQ": "QQQ", "Apple": "AAPL",
        "Tesla": "TSLA", "Microsoft": "MSFT", "Amazon": "AMZN",
        "Google": "GOOGL", "NVIDIA": "NVDA", "Meta": "META",
    },
    "Metals": {
        "Gold": "GC=F", "Silver": "SI=F", "Platinum": "PL=F",
        "Copper": "HG=F", "Palladium": "PA=F",
    },
    "Crypto": {
        "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD",
        "Cardano": "ADA-USD", "XRP": "XRP-USD", "Dogecoin": "DOGE-USD",
    },
}

TIMEFRAMES = {
    "1D":  ("1d",  "5m"),
    "1W":  ("5d",  "15m"),
    "1M":  ("1mo", "1h"),
    "3M":  ("3mo", "1d"),
    "6M":  ("6mo", "1d"),
    "1Y":  ("1y",  "1d"),
    "5Y":  ("5y",  "1wk"),
}


def fetch_ohlcv(symbol: str, timeframe: str = "1M") -> pd.DataFrame:
    """Fetch OHLCV data for a symbol at the given timeframe."""
    period, interval = TIMEFRAMES.get(timeframe, ("1mo", "1h"))
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df.rename(columns=str.lower)
        df.index.name = "datetime"
        return df
    except Exception:
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to OHLCV dataframe."""
    if df.empty or len(df) < 20:
        return df

    close = df["close"]
    high = df["high"]
    low = df["low"]

    # RSI
    df["rsi"] = RSIIndicator(close, window=14).rsi()

    # MACD
    macd = MACD(close)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    # Bollinger Bands
    bb = BollingerBands(close, window=20)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()

    # EMAs
    df["ema_9"] = EMAIndicator(close, window=9).ema_indicator()
    df["ema_21"] = EMAIndicator(close, window=21).ema_indicator()
    df["sma_50"] = SMAIndicator(close, window=min(50, len(df) - 1)).sma_indicator()

    # ATR
    df["atr"] = AverageTrueRange(high, low, close, window=14).average_true_range()

    return df.dropna()


def get_current_price(symbol: str) -> dict:
    """Get current price and basic info for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        hist = ticker.history(period="2d", interval="1d")
        if hist.empty:
            return {}

        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = current - prev
        change_pct = (change / prev) * 100 if prev != 0 else 0

        return {
            "price": round(current, 5),
            "change": round(change, 5),
            "change_pct": round(change_pct, 2),
            "high": round(hist["High"].iloc[-1], 5),
            "low": round(hist["Low"].iloc[-1], 5),
            "volume": int(hist["Volume"].iloc[-1]) if hist["Volume"].iloc[-1] > 0 else 0,
        }
    except Exception:
        return {}


def get_market_overview() -> list:
    """Get quick overview of key markets."""
    watchlist = [
        ("EUR/USD", "EURUSD=X", "Forex"),
        ("Gold", "GC=F", "Metals"),
        ("Bitcoin", "BTC-USD", "Crypto"),
        ("S&P 500", "SPY", "Stocks"),
        ("GBP/USD", "GBPUSD=X", "Forex"),
        ("Silver", "SI=F", "Metals"),
        ("Ethereum", "ETH-USD", "Crypto"),
        ("NASDAQ", "QQQ", "Stocks"),
    ]
    results = []
    for name, symbol, asset_class in watchlist:
        data = get_current_price(symbol)
        if data:
            data["name"] = name
            data["symbol"] = symbol
            data["asset_class"] = asset_class
            results.append(data)
    return results
