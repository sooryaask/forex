"""
Historical Event Similarity Engine

Maintains a database of past economic events and their actual market outcomes.
When a new event occurs, finds the most similar past events and predicts
the likely market reaction based on weighted historical outcomes.

Supports: forex, stocks, metals, crypto
"""

import json
import os
import math
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import yfinance as yf
from fredapi import Fred

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "event_db.json")

# FRED series that map to event types
EVENT_FRED_MAP = {
    "cpi": {
        "US": "CPIAUCSL",
        "UK": "GBRCPIALLMINMEI",
    },
    "gdp": {
        "US": "GDP",
        "UK": "UKNGDP",
    },
    "rate": {
        "US": "FEDFUNDS",
        "UK": "BOERUKM",
    },
    "employment": {
        "US": "UNRATE",
    },
    "ppi": {
        "US": "PPIACO",
    },
    "retail_sales": {
        "US": "RSXFS",
    },
}

# Symbols to track outcomes for each asset class
OUTCOME_SYMBOLS = {
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
    "stocks": ["SPY", "QQQ"],
    "metals": ["GC=F", "SI=F"],
    "crypto": ["BTC-USD", "ETH-USD"],
}

# Map event types to a category for similarity matching
EVENT_CATEGORIES = {
    "cpi": "inflation",
    "ppi": "inflation",
    "gdp": "growth",
    "rate": "monetary",
    "employment": "labor",
    "nfp": "labor",
    "retail_sales": "consumption",
    "trade_balance": "trade",
    "pmi": "growth",
    "housing": "consumption",
}


def load_db():
    """Load the event database from disk."""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {"events": [], "meta": {"last_updated": None, "version": 1}}


def save_db(db):
    """Save the event database to disk."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db["meta"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2, default=str)


def get_price_reaction(symbol, event_time, windows_minutes=(5, 15, 60)):
    """
    Fetch the price change after an event for a given symbol.

    Returns dict of {window: pct_change} e.g. {"5m": 0.0012, "15m": -0.0005}
    """
    try:
        start = event_time - timedelta(hours=1)
        end = event_time + timedelta(hours=2)
        data = yf.download(symbol, start=start, end=end, interval="1m", progress=False)
        if data.empty:
            # Try 5m interval for less liquid assets
            data = yf.download(symbol, start=start, end=end, interval="5m", progress=False)
        if data.empty:
            return None

        # Handle multi-level columns from yfinance
        if hasattr(data.columns, 'levels') and len(data.columns.levels) > 1:
            data.columns = data.columns.get_level_values(0)

        # Find the closest price at event time
        if data.index.tz is not None:
            event_time_tz = event_time.replace(tzinfo=data.index.tz)
        else:
            event_time_tz = event_time

        # Get price at or just before event
        mask = data.index <= event_time_tz
        if not mask.any():
            base_price = float(data["Close"].iloc[0])
        else:
            base_price = float(data["Close"][mask].iloc[-1])

        reactions = {}
        for window in windows_minutes:
            target_time = event_time_tz + timedelta(minutes=window)
            mask_after = data.index <= target_time
            if mask_after.any():
                end_price = float(data["Close"][mask_after].iloc[-1])
                pct = (end_price - base_price) / base_price
                reactions[f"{window}m"] = round(pct, 6)

        return reactions if reactions else None
    except Exception as e:
        print(f"  Price reaction error for {symbol}: {e}")
        return None


def build_event_from_fred_release(
    event_type, region, series_id, fred, lookback_years=3
):
    """
    Build event records from FRED data releases.

    Each data point release is treated as an event. The "surprise" is
    computed as actual - previous (since FRED doesn't store forecasts).
    """
    try:
        end = datetime.now()
        start = end - timedelta(days=lookback_years * 365)
        series = fred.get_series(series_id, observation_start=start)
        if series is None or series.empty:
            return []

        events = []
        values = series.dropna()

        for i in range(1, len(values)):
            actual = float(values.iloc[i])
            previous = float(values.iloc[i - 1])
            release_date = values.index[i].to_pydatetime()

            # Skip future dates
            if release_date > datetime.now():
                continue

            # Compute surprise as % deviation from previous
            if previous != 0:
                surprise = (actual - previous) / abs(previous)
            else:
                surprise = 0.0

            # Determine importance based on event type
            importance = 3  # default high
            if event_type in ("ppi", "retail_sales"):
                importance = 2
            elif event_type in ("rate", "gdp", "cpi"):
                importance = 3

            # Direction based on surprise
            if event_type == "rate":
                # Rate hikes are typically negative for risk assets
                direction = "negative" if surprise > 0 else "positive"
            else:
                direction = "positive" if surprise > 0 else "negative"

            event = {
                "id": f"{event_type}_{region}_{release_date.strftime('%Y%m%d')}",
                "date": release_date.isoformat() + "Z",
                "type": event_type,
                "category": EVENT_CATEGORIES.get(event_type, event_type),
                "region": region,
                "importance": importance,
                "actual": round(actual, 4),
                "previous": round(previous, 4),
                "surprise": round(surprise, 6),
                "direction": direction,
                "outcomes": {},
            }
            events.append(event)

        return events
    except Exception as e:
        print(f"  FRED error for {series_id}: {e}")
        return []


def populate_outcomes(events, asset_classes=None):
    """
    For each event, fetch the actual price reaction across asset classes.
    This is the key step: recording what ACTUALLY happened.
    """
    if asset_classes is None:
        asset_classes = list(OUTCOME_SYMBOLS.keys())

    for i, event in enumerate(events):
        if event.get("outcomes"):
            continue  # Already populated

        event_time = datetime.fromisoformat(event["date"].replace("Z", ""))
        print(f"  [{i+1}/{len(events)}] Fetching outcomes for {event['id']}...")

        for ac in asset_classes:
            symbols = OUTCOME_SYMBOLS.get(ac, [])
            ac_outcomes = {}
            for sym in symbols:
                reaction = get_price_reaction(sym, event_time)
                if reaction:
                    ac_outcomes[sym] = reaction
            if ac_outcomes:
                event["outcomes"][ac] = ac_outcomes

    return events


def compute_similarity(event_a, event_b):
    """
    Compute similarity score (0-1) between two events.

    Factors:
    - Same event type (0.35 weight)
    - Same category (0.15 weight)
    - Similar importance (0.10 weight)
    - Similar surprise magnitude (0.20 weight)
    - Same surprise direction (0.10 weight)
    - Same region (0.10 weight)
    """
    score = 0.0

    # Type match (exact)
    if event_a.get("type") == event_b.get("type"):
        score += 0.35
    # Category match (broader)
    elif event_a.get("category") == event_b.get("category"):
        score += 0.15

    # Importance similarity
    imp_a = event_a.get("importance", 2)
    imp_b = event_b.get("importance", 2)
    imp_sim = 1.0 - abs(imp_a - imp_b) / 3.0
    score += 0.10 * max(imp_sim, 0)

    # Surprise magnitude similarity (using log scale for robustness)
    surp_a = abs(event_a.get("surprise", 0))
    surp_b = abs(event_b.get("surprise", 0))
    if surp_a > 0 and surp_b > 0:
        log_ratio = abs(math.log(surp_a + 1e-6) - math.log(surp_b + 1e-6))
        surp_sim = max(1.0 - log_ratio / 3.0, 0)
    elif surp_a == 0 and surp_b == 0:
        surp_sim = 1.0
    else:
        surp_sim = 0.3
    score += 0.20 * surp_sim

    # Direction match
    if event_a.get("direction") == event_b.get("direction"):
        score += 0.10

    # Region match
    if event_a.get("region") == event_b.get("region"):
        score += 0.10

    return round(score, 4)


def find_similar_events(query_event, db, top_k=20, min_similarity=0.3):
    """
    Find the top_k most similar historical events to the query event.

    Returns list of (event, similarity_score) tuples sorted by similarity desc.
    """
    scored = []
    for hist_event in db["events"]:
        # Skip events without outcomes
        if not hist_event.get("outcomes"):
            continue
        # Don't match against itself
        if hist_event.get("id") == query_event.get("id"):
            continue

        sim = compute_similarity(query_event, hist_event)
        if sim >= min_similarity:
            scored.append((hist_event, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def predict_from_similar(similar_events, asset_class, window="15m"):
    """
    Predict market reaction by computing a similarity-weighted average
    of historical outcomes.

    Returns dict with:
    - predicted_move: weighted average % move
    - confidence: based on agreement among similar events
    - n_events: how many events contributed
    - direction_ratio: % of events that moved in predicted direction
    - details: per-symbol breakdown
    """
    if not similar_events:
        return {
            "predicted_move": 0.0,
            "confidence": 0.0,
            "n_events": 0,
            "direction_ratio": 0.5,
            "details": {},
        }

    # Collect all outcomes for this asset class
    symbol_moves = defaultdict(list)  # symbol -> [(move, weight)]
    total_weight = 0.0

    for event, similarity in similar_events:
        outcomes = event.get("outcomes", {}).get(asset_class, {})
        for symbol, windows in outcomes.items():
            if window in windows:
                move = windows[window]
                symbol_moves[symbol].append((move, similarity))
                total_weight += similarity

    if not symbol_moves:
        return {
            "predicted_move": 0.0,
            "confidence": 0.0,
            "n_events": len(similar_events),
            "direction_ratio": 0.5,
            "details": {},
        }

    # Compute weighted average per symbol
    details = {}
    all_moves = []
    all_weights = []
    direction_counts = {"positive": 0, "negative": 0}

    for symbol, moves_weights in symbol_moves.items():
        moves = [m for m, w in moves_weights]
        weights = [w for m, w in moves_weights]
        weighted_avg = np.average(moves, weights=weights)
        details[symbol] = {
            "predicted_move_pct": round(weighted_avg * 100, 4),
            "n_samples": len(moves),
            "std": round(float(np.std(moves)) * 100, 4),
            "min": round(min(moves) * 100, 4),
            "max": round(max(moves) * 100, 4),
        }
        all_moves.append(weighted_avg)
        all_weights.append(sum(weights))

        for m in moves:
            if m > 0:
                direction_counts["positive"] += 1
            else:
                direction_counts["negative"] += 1

    # Overall prediction (average across symbols in this asset class)
    if all_moves:
        overall_move = float(np.average(all_moves, weights=all_weights))
    else:
        overall_move = 0.0

    total_dir = direction_counts["positive"] + direction_counts["negative"]
    if total_dir > 0:
        dominant = max(direction_counts.values())
        direction_ratio = dominant / total_dir
    else:
        direction_ratio = 0.5

    # Confidence: based on direction agreement + number of samples + avg similarity
    avg_sim = np.mean([s for _, s in similar_events]) if similar_events else 0
    sample_factor = min(len(similar_events) / 10.0, 1.0)  # saturates at 10 events
    confidence = direction_ratio * 0.4 + avg_sim * 0.3 + sample_factor * 0.3
    confidence = round(min(confidence, 1.0), 3)

    return {
        "predicted_move": round(overall_move * 100, 4),  # as percentage
        "confidence": confidence,
        "n_events": len(similar_events),
        "direction_ratio": round(direction_ratio, 3),
        "details": details,
    }


def predict_event_impact(query_event, asset_class, db=None, window="15m", top_k=20):
    """
    Main prediction function. Given a new event and asset class,
    finds similar historical events and predicts the market impact.

    Args:
        query_event: dict with type, importance, direction, surprise, region
        asset_class: one of forex, stocks, metals, crypto
        db: event database (loaded from disk if None)
        window: time window for outcome ("5m", "15m", "60m")
        top_k: number of similar events to use

    Returns:
        prediction dict with movement_score, liquidity, confidence, etc.
    """
    if db is None:
        db = load_db()

    similar = find_similar_events(query_event, db, top_k=top_k)
    prediction = predict_from_similar(similar, asset_class, window=window)

    # Convert predicted_move (%) to movement_score (-100 to 100)
    # Scale: ±1% move maps to ±50 movement score
    raw_move = prediction["predicted_move"]
    movement_score = raw_move * 50.0
    movement_score = max(min(movement_score, 100), -100)

    # Liquidity: higher when more events agree, lower during high-impact events
    importance = query_event.get("importance", 2)
    base_liquidity = 80 - importance * 5
    agreement_boost = (prediction["direction_ratio"] - 0.5) * 40
    liquidity = base_liquidity + agreement_boost
    liquidity = max(min(liquidity, 100), 20)

    # Point diff: scaled from predicted move
    point_diff = abs(raw_move) * 0.5
    point_diff = round(max(min(point_diff, 10.0), 0.1), 2)

    return {
        "movement_score": round(movement_score, 2),
        "liquidity_score": round(liquidity, 2),
        "confidence": prediction["confidence"],
        "predicted_point_diff": point_diff,
        "predicted_move_pct": prediction["predicted_move"],
        "n_similar_events": prediction["n_events"],
        "direction_ratio": prediction["direction_ratio"],
        "similar_event_details": prediction["details"],
        "top_similar": [
            {
                "id": e["id"],
                "date": e["date"],
                "type": e["type"],
                "surprise": e.get("surprise", 0),
                "similarity": sim,
            }
            for e, sim in similar[:5]
        ],
    }


def build_database(fred_api_key, lookback_years=3, fetch_outcomes=True):
    """
    Build/update the event database from FRED releases.

    This fetches historical economic data releases and (optionally)
    the actual price reactions for each event.

    Args:
        fred_api_key: FRED API key
        lookback_years: how far back to look
        fetch_outcomes: whether to fetch price reactions (slow, uses Yahoo)
    """
    fred = Fred(api_key=fred_api_key)
    db = load_db()
    existing_ids = {e["id"] for e in db["events"]}

    new_events = []
    for event_type, regions in EVENT_FRED_MAP.items():
        for region, series_id in regions.items():
            print(f"Fetching {event_type} ({region}) from FRED series {series_id}...")
            events = build_event_from_fred_release(
                event_type, region, series_id, fred, lookback_years
            )
            for e in events:
                if e["id"] not in existing_ids:
                    new_events.append(e)
                    existing_ids.add(e["id"])

    print(f"\nFound {len(new_events)} new events.")

    if fetch_outcomes and new_events:
        print("Fetching price reactions (this may take a while)...")
        new_events = populate_outcomes(new_events)

    db["events"].extend(new_events)
    save_db(db)
    print(
        f"Database updated: {len(db['events'])} total events. Saved to {DB_PATH}"
    )
    return db


def add_manual_event(
    event_type,
    region,
    importance,
    actual,
    previous,
    direction=None,
    event_date=None,
    fetch_outcomes=True,
):
    """
    Manually add an event to the database (e.g., for events not in FRED).

    Useful for: NFP, PMI, trade balance, housing data, central bank speeches, etc.
    """
    db = load_db()

    if event_date is None:
        event_date = datetime.utcnow()
    elif isinstance(event_date, str):
        event_date = datetime.fromisoformat(event_date.replace("Z", ""))

    surprise = (actual - previous) / abs(previous) if previous != 0 else 0.0

    if direction is None:
        if event_type == "rate":
            direction = "negative" if surprise > 0 else "positive"
        else:
            direction = "positive" if surprise > 0 else "negative"

    event = {
        "id": f"{event_type}_{region}_{event_date.strftime('%Y%m%d_%H%M')}",
        "date": event_date.isoformat() + "Z",
        "type": event_type,
        "category": EVENT_CATEGORIES.get(event_type, event_type),
        "region": region,
        "importance": importance,
        "actual": actual,
        "previous": previous,
        "surprise": round(surprise, 6),
        "direction": direction,
        "outcomes": {},
    }

    if fetch_outcomes:
        print(f"Fetching price reactions for {event['id']}...")
        populate_outcomes([event])

    db["events"].append(event)
    save_db(db)
    print(f"Added event: {event['id']}")
    return event


def get_db_stats():
    """Get summary statistics about the event database."""
    db = load_db()
    events = db["events"]

    if not events:
        return {"total_events": 0, "message": "Database is empty. Run build_database() first."}

    type_counts = defaultdict(int)
    category_counts = defaultdict(int)
    region_counts = defaultdict(int)
    with_outcomes = 0
    asset_class_coverage = defaultdict(int)

    for e in events:
        type_counts[e.get("type", "unknown")] += 1
        category_counts[e.get("category", "unknown")] += 1
        region_counts[e.get("region", "unknown")] += 1
        if e.get("outcomes"):
            with_outcomes += 1
            for ac in e["outcomes"]:
                asset_class_coverage[ac] += 1

    date_range = None
    dates = [e.get("date", "") for e in events if e.get("date")]
    if dates:
        date_range = {"earliest": min(dates), "latest": max(dates)}

    return {
        "total_events": len(events),
        "with_outcomes": with_outcomes,
        "by_type": dict(type_counts),
        "by_category": dict(category_counts),
        "by_region": dict(region_counts),
        "asset_class_coverage": dict(asset_class_coverage),
        "date_range": date_range,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "build":
        # Read FRED API key from environment or data_prep.py
        api_key = os.environ.get("FRED_API_KEY", "")
        if not api_key:
            print("Set FRED_API_KEY environment variable or pass as argument.")
            print("Usage: python event_history.py build [FRED_API_KEY]")
            if len(sys.argv) > 2:
                api_key = sys.argv[2]
            else:
                sys.exit(1)

        years = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        build_database(api_key, lookback_years=years)

    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = get_db_stats()
        print(json.dumps(stats, indent=2))

    else:
        print("Historical Event Similarity Engine")
        print("===================================")
        print("Usage:")
        print("  python event_history.py build [FRED_API_KEY] [YEARS]")
        print("  python event_history.py stats")
        print()
        print("Or import and use in code:")
        print("  from event_history import predict_event_impact, build_database")
