# TradingView AI CFD Predictor Add-on

This project scaffolds a TradingView add-on that uses an external AI prediction backend and a Pine Script indicator to show market movement and liquidity signals for CFDs on a 5-minute timeframe.

## Components

1. `tradingview/ai_cfd_predictor.pine` - Pine Script indicator to display signals and accept webhook updates.
2. `backend/predictor.py` - Python Flask API for generating prediction values from fundamental/economic context.
3. `backend/requirements.txt` - Python dependencies.

## How it works

- The Python backend fetches economic/fundamental data (mocked for now), computes signal and liquidity scores, and returns JSON.
- You can call this API from an external automation script and send signals to TradingView alerts.
- Pine Script draws movement and liquidity band overlays on the 5-minute chart.

## Running

1. Create a Python venv and install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run backend API:

```bash
python predictor.py
```

3. In TradingView, add `tradingview/ai_cfd_predictor.pine` as a new indicator, set `timeframe = "5"` and configure signal inputs.
4. To run automated strategy, add `tradingview/ai_cfd_strategy.pine` as a strategy on a 5m chart.
5. (Optional) Implement webhook forwarder to push JSON predictions into TradingView via alerts.

### Event-driven strategy endpoint

- Start the event strategy API:

```bash
cd backend
python3 strategy_predictor.py
```

- POST to `http://127.0.0.1:5101/predict_event` with events and facts to get signal, movement score, liquidity, and predicted point difference.

## Notes

- Real AI integration requires data collection and model training. This project includes an easy scaffold of the workflow.
- The Pine Script cannot natively call external APIs; it receives signals from alerts or manual input.
