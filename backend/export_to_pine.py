"""
Export Event Database → Pine Script Lookup Tables

Reads the event_db.json and produces a Pine Script file containing
hardcoded arrays of historical average reactions per (event_type, direction,
asset_class).  This lets the TradingView indicator work 100 % offline
without calling any external API.

Usage:
    python export_to_pine.py                     # default output
    python export_to_pine.py -o my_indicator.pine # custom output path

The generated Pine Script can be pasted directly into TradingView.
"""

import json
import os
import argparse
from collections import defaultdict
from datetime import datetime

import numpy as np

from event_history import load_db, EVENT_CATEGORIES

# ── Which time windows to export ──────────────────────────────────────────
WINDOWS = ["5m", "15m", "60m"]

# ── Asset class order (must stay consistent in Pine arrays) ───────────────
ASSET_CLASSES = ["forex", "stocks", "metals", "crypto"]

# ── Event types we generate lookup entries for ────────────────────────────
EVENT_TYPES = [
    "cpi", "gdp", "rate", "employment", "nfp",
    "ppi", "retail_sales", "pmi", "trade_balance", "housing",
]

DIRECTIONS = ["positive", "negative"]


def aggregate_reactions(db):
    """
    Walk every event in the DB and build a nested dict:

        result[event_type][direction][asset_class][window]
            = list of pct moves

    Then collapse each list into (mean, std, count).
    """
    raw = defaultdict(              # event_type
        lambda: defaultdict(        # direction
            lambda: defaultdict(    # asset_class
                lambda: defaultdict(list)  # window -> [moves]
            )
        )
    )

    for event in db.get("events", []):
        etype = event.get("type", "")
        direction = event.get("direction", "neutral")
        if direction == "neutral":
            continue
        outcomes = event.get("outcomes", {})

        for ac, symbols in outcomes.items():
            for sym, windows in symbols.items():
                for win, pct_move in windows.items():
                    if win in WINDOWS:
                        raw[etype][direction][ac][win].append(pct_move)

    # Collapse to stats
    stats = {}
    for etype in EVENT_TYPES:
        stats[etype] = {}
        for direction in DIRECTIONS:
            stats[etype][direction] = {}
            for ac in ASSET_CLASSES:
                stats[etype][direction][ac] = {}
                for win in WINDOWS:
                    moves = raw[etype][direction][ac][win]
                    if moves:
                        stats[etype][direction][ac][win] = {
                            "mean": round(float(np.mean(moves)) * 100, 4),  # pct
                            "std": round(float(np.std(moves)) * 100, 4),
                            "count": len(moves),
                        }
                    else:
                        stats[etype][direction][ac][win] = {
                            "mean": 0.0, "std": 0.0, "count": 0,
                        }
    return stats


def _pine_float(val):
    """Format a float for Pine Script."""
    return f"{val:.4f}"


def generate_pine_script(stats):
    """
    Generate a complete self-contained Pine Script v5 indicator.

    The indicator uses flat arrays indexed by
        idx = event_type_index * 8 + direction_index * 4 + asset_class_index

    For each (event, direction, asset_class) combo we store:
        avg_move_5m, avg_move_15m, avg_move_60m, std_15m, sample_count
    """
    n_events = len(EVENT_TYPES)
    n_dirs = len(DIRECTIONS)
    n_ac = len(ASSET_CLASSES)
    total = n_events * n_dirs * n_ac  # flat array length

    # Build flat arrays
    avg_5m = []
    avg_15m = []
    avg_60m = []
    std_15m = []
    counts = []

    for etype in EVENT_TYPES:
        for direction in DIRECTIONS:
            for ac in ASSET_CLASSES:
                entry = stats[etype][direction][ac]
                avg_5m.append(entry["5m"]["mean"])
                avg_15m.append(entry["15m"]["mean"])
                avg_60m.append(entry["60m"]["mean"])
                std_15m.append(entry["15m"]["std"])
                counts.append(entry["15m"]["count"])

    # ── Build the Pine Script string ──────────────────────────────────────
    lines = []
    lines.append("// ═══════════════════════════════════════════════════════════════")
    lines.append("// AI Event Similarity Predictor (Self-Contained)")
    lines.append(f"// Auto-generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append(f"// Event DB: {sum(counts)} total outcome samples")
    lines.append("// ═══════════════════════════════════════════════════════════════")
    lines.append("")
    lines.append("//@version=5")
    lines.append('indicator("AI Event Predictor", overlay=true, max_labels_count=50)')
    lines.append("")

    # ── User inputs ───────────────────────────────────────────────────────
    lines.append("// ─── Inputs ───────────────────────────────────────────────────")
    event_options = ", ".join(f'"{e.upper()}"' for e in EVENT_TYPES)
    lines.append(f'i_event_type  = input.string("CPI", "Event Type", options=[{event_options}])')
    lines.append('i_direction   = input.string("Positive", "Surprise Direction", options=["Positive", "Negative"])')
    lines.append('i_importance  = input.int(3, "Importance (1-3)", minval=1, maxval=3)')
    lines.append('i_window      = input.string("15m", "Prediction Window", options=["5m", "15m", "60m"])')
    lines.append('i_show_table  = input.bool(true, "Show Stats Table")')
    lines.append('i_show_target = input.bool(true, "Show Target Lines")')
    lines.append("")

    # ── Asset class detection ─────────────────────────────────────────────
    lines.append("// ─── Asset Class Detection ────────────────────────────────────")
    lines.append("// 0=forex, 1=stocks, 2=metals, 3=crypto")
    lines.append("f_detect_asset() =>")
    lines.append('    sym = syminfo.ticker')
    lines.append('    base = syminfo.basecurrency')
    lines.append('    quote = syminfo.currency')
    lines.append('    stype = syminfo.type')
    lines.append('    if stype == "crypto"')
    lines.append("        3")
    lines.append('    else if stype == "forex"')
    lines.append("        0")
    lines.append('    else if str.contains(sym, "GOLD") or str.contains(sym, "XAUUSD") or str.contains(sym, "GC") or str.contains(sym, "SILVER") or str.contains(sym, "XAGUSD") or str.contains(sym, "SI")')
    lines.append("        2")
    lines.append('    else if base == "XAU" or base == "XAG" or quote == "XAU" or quote == "XAG"')
    lines.append("        2")
    lines.append("    else")
    lines.append("        1  // stocks / indices / ETFs")
    lines.append("")
    lines.append("asset_class = f_detect_asset()")
    lines.append("")

    # ── Event type index mapping ──────────────────────────────────────────
    lines.append("// ─── Map inputs to array indices ──────────────────────────────")
    lines.append("f_event_idx() =>")
    for i, etype in enumerate(EVENT_TYPES):
        cond = "if" if i == 0 else "else if"
        lines.append(f'    {cond} i_event_type == "{etype.upper()}"')
        lines.append(f"        {i}")
    lines.append("    else")
    lines.append("        0")
    lines.append("")
    lines.append("event_idx = f_event_idx()")
    lines.append('dir_idx   = i_direction == "Positive" ? 0 : 1')
    lines.append("")

    # ── Flat array index ──────────────────────────────────────────────────
    lines.append(f"// Flat index = event_idx * {n_dirs * n_ac} + dir_idx * {n_ac} + asset_class")
    lines.append(f"flat_idx = event_idx * {n_dirs * n_ac} + dir_idx * {n_ac} + asset_class")
    lines.append("")

    # ── Data arrays ───────────────────────────────────────────────────────
    lines.append("// ─── Historical Reaction Data ─────────────────────────────────")
    lines.append(f"// {total} entries: {n_events} event types × {n_dirs} directions × {n_ac} asset classes")
    lines.append("")

    def _pine_array(name, values, as_int=False):
        """Generate a Pine Script array.from() call, splitting across lines."""
        formatted = []
        for v in values:
            formatted.append(str(int(v)) if as_int else _pine_float(v))
        # Pine has a limit on line length, so chunk it
        chunk_size = 10
        arr_lines = []
        arr_lines.append(f"var {name} = array.new<{'int' if as_int else 'float'}>({total}, 0{'.' if not as_int else ''})")
        for ci in range(0, len(formatted), chunk_size):
            chunk = formatted[ci:ci + chunk_size]
            for j, val in enumerate(chunk):
                idx = ci + j
                arr_lines.append(f"array.set({name}, {idx}, {'int' if as_int else 'float'}({val}))")
        return arr_lines

    # Use a more compact init approach
    def _pine_array_compact(name, values, as_int=False):
        """Generate array using array.from() in chunks."""
        result = []
        fmt = lambda v: str(int(v)) if as_int else _pine_float(v)
        type_name = "int" if as_int else "float"

        # Use a switch-like approach for compactness
        result.append(f"f_get_{name}(int idx) =>")
        chunk = 20
        for i in range(0, len(values), chunk):
            vals = values[i:i + chunk]
            for j, v in enumerate(vals):
                idx = i + j
                cond = "if" if idx == 0 else "else if"
                result.append(f"    {cond} idx == {idx}")
                result.append(f"        {fmt(v)}")
        result.append("    else")
        result.append(f"        {'0' if as_int else '0.0'}")
        result.append("")
        return result

    # For smaller arrays, use a simpler approach with conditional lookups
    lines.append("// Average moves (%) after event for each window")

    # Generate lookup functions
    for arr_name, arr_data, is_int in [
        ("avg5m", avg_5m, False),
        ("avg15m", avg_15m, False),
        ("avg60m", avg_60m, False),
        ("dev15m", std_15m, False),
        ("cnt", counts, True),
    ]:
        lines.extend(_pine_array_compact(arr_name, arr_data, is_int))

    # ── Main prediction logic ─────────────────────────────────────────────
    lines.append("// ─── Prediction Logic ─────────────────────────────────────────")
    lines.append("pred_5m  = f_get_avg5m(flat_idx)")
    lines.append("pred_15m = f_get_avg15m(flat_idx)")
    lines.append("pred_60m = f_get_avg60m(flat_idx)")
    lines.append("std_dev  = f_get_dev15m(flat_idx)")
    lines.append("n_samples = f_get_cnt(flat_idx)")
    lines.append("")
    lines.append("// Select prediction based on chosen window")
    lines.append('pred_move = i_window == "5m" ? pred_5m : i_window == "15m" ? pred_15m : pred_60m')
    lines.append("")

    # ── Movement score and signal ─────────────────────────────────────────
    lines.append("// ─── Movement Score & Signal ──────────────────────────────────")
    lines.append("// Scale: ±0.5% move → ±50 movement score")
    lines.append("movement_score = math.max(math.min(pred_move * 100.0, 100.0), -100.0)")
    lines.append("")
    lines.append("// Confidence based on sample count and importance")
    lines.append("sample_conf  = math.min(n_samples / 10.0, 1.0)")
    lines.append("imp_conf     = i_importance / 3.0")
    lines.append("std_penalty  = std_dev > 0 ? math.max(1.0 - std_dev / 2.0, 0.1) : 0.5")
    lines.append("confidence   = sample_conf * 0.4 + imp_conf * 0.2 + std_penalty * 0.4")
    lines.append("confidence  := math.min(math.max(confidence, 0.0), 1.0)")
    lines.append("")
    lines.append("// Liquidity estimate: drops during high-importance events")
    lines.append("liquidity = 85.0 - i_importance * 8.0 + (confidence - 0.5) * 20.0")
    lines.append("liquidity := math.max(math.min(liquidity, 100.0), 20.0)")
    lines.append("")
    lines.append("// Signal generation")
    lines.append("is_buy  = movement_score > 12 and liquidity > 55 and confidence > 0.4 and n_samples > 2")
    lines.append("is_sell = movement_score < -12 and liquidity > 55 and confidence > 0.4 and n_samples > 2")
    lines.append("")

    # ── Price target lines ────────────────────────────────────────────────
    lines.append("// ─── Target Price Lines ───────────────────────────────────────")
    lines.append("pred_pct     = pred_move / 100.0  // convert from % to decimal")
    lines.append("target_price = close * (1.0 + pred_pct)")
    lines.append("stop_price   = close * (1.0 - pred_pct * 0.6)")
    lines.append("")
    lines.append("var line target_line = na")
    lines.append("var line stop_line   = na")
    lines.append("var label target_lbl = na")
    lines.append("")
    lines.append("if barstate.islast and i_show_target and n_samples > 0")
    lines.append("    // Clean up old lines")
    lines.append("    if not na(target_line)")
    lines.append("        line.delete(target_line)")
    lines.append("    if not na(stop_line)")
    lines.append("        line.delete(stop_line)")
    lines.append("    if not na(target_lbl)")
    lines.append("        label.delete(target_lbl)")
    lines.append("")
    lines.append("    t_color = pred_move > 0 ? color.green : color.red")
    lines.append("    target_line := line.new(bar_index - 10, target_price, bar_index + 10, target_price, color=t_color, width=2, style=line.style_dashed)")
    lines.append("    stop_line   := line.new(bar_index - 10, stop_price, bar_index + 10, stop_price, color=color.orange, width=1, style=line.style_dotted)")
    lines.append('    target_lbl  := label.new(bar_index + 11, target_price, "Target: " + str.tostring(target_price, format.mintick) + " (" + str.tostring(pred_move, "#.##") + "%)", color=color.new(t_color, 80), textcolor=color.white, style=label.style_label_left)')
    lines.append("")

    # ── Signal labels ─────────────────────────────────────────────────────
    lines.append("// ─── Signal Labels ────────────────────────────────────────────")
    lines.append('plotshape(is_buy  and barstate.islast, title="BUY",  location=location.belowbar, color=color.lime, style=shape.labelup,   text="BUY",  size=size.normal)')
    lines.append('plotshape(is_sell and barstate.islast, title="SELL", location=location.abovebar, color=color.red,  style=shape.labeldown, text="SELL", size=size.normal)')
    lines.append("")

    # ── Background color ──────────────────────────────────────────────────
    lines.append("// ─── Background ───────────────────────────────────────────────")
    lines.append("bg_color = is_buy ? color.new(color.green, 92) : is_sell ? color.new(color.red, 92) : na")
    lines.append("bgcolor(barstate.islast ? bg_color : na)")
    lines.append("")

    # ── Info table ────────────────────────────────────────────────────────
    lines.append("// ─── Stats Table ──────────────────────────────────────────────")
    lines.append("if barstate.islast and i_show_table")
    lines.append('    var table t = table.new(position.top_right, 2, 10, bgcolor=color.new(color.black, 80), border_width=1)')
    lines.append("")
    lines.append('    ac_name = asset_class == 0 ? "FOREX" : asset_class == 1 ? "STOCKS" : asset_class == 2 ? "METALS" : "CRYPTO"')
    lines.append('    signal_txt = is_buy ? "BUY" : is_sell ? "SELL" : "NEUTRAL"')
    lines.append('    signal_clr = is_buy ? color.lime : is_sell ? color.red : color.gray')
    lines.append("")

    rows = [
        ('"Event"',          'i_event_type + " (" + i_direction + ")"'),
        ('"Asset Class"',    'ac_name'),
        ('"Signal"',         'signal_txt'),
        ('"Movement"',       'str.tostring(movement_score, "#.#")'),
        ('"Confidence"',     'str.tostring(confidence * 100, "#.#") + "%"'),
        ('"Liquidity"',      'str.tostring(liquidity, "#.#")'),
        ('"Avg Move 5m"',    'str.tostring(pred_5m, "#.####") + "%"'),
        ('"Avg Move 15m"',   'str.tostring(pred_15m, "#.####") + "%"'),
        ('"Avg Move 60m"',   'str.tostring(pred_60m, "#.####") + "%"'),
        ('"Sample Count"',   'str.tostring(n_samples)'),
    ]

    for i, (label, value) in enumerate(rows):
        lines.append(f'    table.cell(t, 0, {i}, {label}, text_color=color.gray, text_size=size.small)')
        color_str = "signal_clr" if label == '"Signal"' else "color.white"
        lines.append(f'    table.cell(t, 1, {i}, {value}, text_color={color_str}, text_size=size.small)')
    lines.append("")

    # ── Alerts ────────────────────────────────────────────────────────────
    lines.append("// ─── Alerts ───────────────────────────────────────────────────")
    lines.append('alertcondition(is_buy,  title="Event BUY Signal",  message="AI Event Predictor: BUY on {{ticker}} | Movement: " + str.tostring(movement_score) + " | Confidence: " + str.tostring(confidence))')
    lines.append('alertcondition(is_sell, title="Event SELL Signal", message="AI Event Predictor: SELL on {{ticker}} | Movement: " + str.tostring(movement_score) + " | Confidence: " + str.tostring(confidence))')
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export event DB to Pine Script")
    parser.add_argument(
        "-o", "--output",
        default=os.path.join(
            os.path.dirname(__file__), "..", "tradingview", "ai_event_predictor.pine"
        ),
        help="Output Pine Script file path",
    )
    parser.add_argument(
        "--seed", action="store_true",
        help="Generate with seed/placeholder data if DB is empty",
    )
    args = parser.parse_args()

    db = load_db()

    if not db["events"] and args.seed:
        print("Event DB is empty. Generating with seed data...")
        db = _generate_seed_db()
    elif not db["events"]:
        print("Event DB is empty. Run `python event_history.py build <FRED_KEY>` first,")
        print("or use --seed to generate with example data.")
        return

    print(f"Processing {len(db['events'])} events...")
    stats = aggregate_reactions(db)

    # Show summary
    total_samples = 0
    for etype in EVENT_TYPES:
        for d in DIRECTIONS:
            for ac in ASSET_CLASSES:
                total_samples += stats[etype][d][ac]["15m"]["count"]
    print(f"Total outcome samples (15m window): {total_samples}")

    pine_code = generate_pine_script(stats)

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(pine_code)

    print(f"\nPine Script written to: {output_path}")
    print(f"Lines: {len(pine_code.splitlines())}")
    print("\nTo use:")
    print("  1. Open TradingView → Pine Editor")
    print("  2. Paste the contents of the generated file")
    print("  3. Click 'Add to Chart'")
    print("  4. Select event type + direction from the indicator settings")


def _generate_seed_db():
    """
    Generate realistic seed data so the Pine Script has something to show
    even before the user runs the full FRED data pipeline.

    Based on typical market reactions from academic research:
    - CPI surprise → forex ±0.15%, stocks ±0.3%, metals ±0.4%, crypto ±0.8%
    - GDP surprise → forex ±0.1%, stocks ±0.4%, metals ±0.2%, crypto ±0.5%
    - Rate decision → forex ±0.25%, stocks ±0.5%, metals ±0.6%, crypto ±1.0%
    - NFP/Employment → forex ±0.2%, stocks ±0.35%, metals ±0.3%, crypto ±0.6%
    """
    np.random.seed(42)

    # Typical reaction profiles: (mean_pct, std_pct) for 15-minute window
    profiles = {
        "cpi": {
            "positive": {
                "forex": (0.12, 0.08), "stocks": (-0.15, 0.12),
                "metals": (-0.25, 0.15), "crypto": (-0.40, 0.30),
            },
            "negative": {
                "forex": (-0.10, 0.07), "stocks": (0.12, 0.10),
                "metals": (0.20, 0.12), "crypto": (0.35, 0.25),
            },
        },
        "gdp": {
            "positive": {
                "forex": (0.08, 0.05), "stocks": (0.30, 0.15),
                "metals": (-0.10, 0.08), "crypto": (0.20, 0.18),
            },
            "negative": {
                "forex": (-0.07, 0.04), "stocks": (-0.25, 0.12),
                "metals": (0.15, 0.10), "crypto": (-0.15, 0.15),
            },
        },
        "rate": {
            "positive": {  # rate hike
                "forex": (0.20, 0.12), "stocks": (-0.35, 0.20),
                "metals": (-0.40, 0.18), "crypto": (-0.60, 0.35),
            },
            "negative": {  # rate cut
                "forex": (-0.18, 0.10), "stocks": (0.40, 0.18),
                "metals": (0.35, 0.15), "crypto": (0.55, 0.30),
            },
        },
        "employment": {
            "positive": {
                "forex": (0.10, 0.06), "stocks": (0.20, 0.12),
                "metals": (-0.08, 0.06), "crypto": (0.12, 0.10),
            },
            "negative": {
                "forex": (-0.08, 0.05), "stocks": (-0.18, 0.10),
                "metals": (0.10, 0.07), "crypto": (-0.10, 0.09),
            },
        },
        "nfp": {
            "positive": {
                "forex": (0.15, 0.09), "stocks": (0.25, 0.14),
                "metals": (-0.12, 0.08), "crypto": (0.15, 0.12),
            },
            "negative": {
                "forex": (-0.12, 0.07), "stocks": (-0.22, 0.12),
                "metals": (0.15, 0.09), "crypto": (-0.12, 0.10),
            },
        },
        "ppi": {
            "positive": {
                "forex": (0.06, 0.04), "stocks": (-0.10, 0.08),
                "metals": (-0.12, 0.08), "crypto": (-0.15, 0.12),
            },
            "negative": {
                "forex": (-0.05, 0.03), "stocks": (0.08, 0.06),
                "metals": (0.10, 0.06), "crypto": (0.12, 0.10),
            },
        },
        "retail_sales": {
            "positive": {
                "forex": (0.05, 0.03), "stocks": (0.18, 0.10),
                "metals": (-0.05, 0.04), "crypto": (0.08, 0.07),
            },
            "negative": {
                "forex": (-0.04, 0.03), "stocks": (-0.15, 0.08),
                "metals": (0.06, 0.04), "crypto": (-0.06, 0.06),
            },
        },
        "pmi": {
            "positive": {
                "forex": (0.07, 0.04), "stocks": (0.22, 0.12),
                "metals": (-0.06, 0.05), "crypto": (0.10, 0.09),
            },
            "negative": {
                "forex": (-0.06, 0.04), "stocks": (-0.20, 0.10),
                "metals": (0.08, 0.05), "crypto": (-0.08, 0.08),
            },
        },
        "trade_balance": {
            "positive": {
                "forex": (0.08, 0.05), "stocks": (0.10, 0.07),
                "metals": (-0.03, 0.03), "crypto": (0.04, 0.05),
            },
            "negative": {
                "forex": (-0.07, 0.04), "stocks": (-0.08, 0.06),
                "metals": (0.04, 0.03), "crypto": (-0.03, 0.04),
            },
        },
        "housing": {
            "positive": {
                "forex": (0.04, 0.03), "stocks": (0.12, 0.08),
                "metals": (-0.03, 0.03), "crypto": (0.05, 0.05),
            },
            "negative": {
                "forex": (-0.03, 0.02), "stocks": (-0.10, 0.07),
                "metals": (0.04, 0.03), "crypto": (-0.04, 0.04),
            },
        },
    }

    # Window scaling: 5m ≈ 0.5×, 15m = 1.0×, 60m ≈ 1.8×
    window_scale = {"5m": 0.5, "15m": 1.0, "60m": 1.8}

    outcome_symbols = {
        "forex": ["EURUSD=X", "GBPUSD=X"],
        "stocks": ["SPY", "QQQ"],
        "metals": ["GC=F"],
        "crypto": ["BTC-USD"],
    }

    from datetime import datetime, timedelta

    events = []
    base_date = datetime(2023, 1, 15)

    for etype, dir_profiles in profiles.items():
        for direction, ac_profiles in dir_profiles.items():
            # Generate 15-25 synthetic events per (type, direction)
            n_events = np.random.randint(15, 26)
            for i in range(n_events):
                event_date = base_date + timedelta(days=np.random.randint(0, 900))
                surprise = np.random.uniform(0.001, 0.05)
                if direction == "negative":
                    surprise = -surprise

                outcomes = {}
                for ac, (mean_pct, std_pct) in ac_profiles.items():
                    symbols = outcome_symbols[ac]
                    ac_outcomes = {}
                    for sym in symbols:
                        sym_windows = {}
                        for win, scale in window_scale.items():
                            move = np.random.normal(
                                mean_pct * scale / 100.0,
                                std_pct * scale / 100.0,
                            )
                            sym_windows[win] = round(float(move), 6)
                        ac_outcomes[sym] = sym_windows
                    outcomes[ac] = ac_outcomes

                event = {
                    "id": f"{etype}_US_{event_date.strftime('%Y%m%d')}_{i}",
                    "date": event_date.isoformat() + "Z",
                    "type": etype,
                    "category": EVENT_CATEGORIES.get(etype, etype),
                    "region": "US",
                    "importance": np.random.choice([1, 2, 3], p=[0.15, 0.35, 0.5]),
                    "actual": round(float(np.random.uniform(0.5, 5.0)), 2),
                    "previous": round(float(np.random.uniform(0.5, 5.0)), 2),
                    "surprise": round(float(surprise), 6),
                    "direction": direction,
                    "outcomes": outcomes,
                }
                events.append(event)

    db = {"events": events, "meta": {"last_updated": datetime.utcnow().isoformat(), "version": 1, "source": "seed"}}
    return db


if __name__ == "__main__":
    main()
