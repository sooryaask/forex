import pandas as pd
import numpy as np

# Load data
data_path = 'data/historical_data.parquet'
df = pd.read_parquet(data_path)

# Simulate signals (using rule-based for now)
def simulate_signals(row):
    movement = row['RSI'] * 0.1 + row['MACD'] * 10  # simple
    liquidity = 50 + row['Volume_Delta'] * 100 if pd.notna(row['Volume_Delta']) else 50
    signal = 'NEUTRAL'
    if movement > 10 and liquidity > 55:
        signal = 'BUY'
    elif movement < -10 and liquidity > 55:
        signal = 'SELL'
    return signal, movement, liquidity

df['signal'], df['movement'], df['liquidity'] = zip(*df.apply(simulate_signals, axis=1))

# Backtest
capital = 10000
position = 0
trades = []

for idx, row in df.iterrows():
    if row['signal'] == 'BUY' and position == 0:
        position = capital / row['Close']
        entry_price = row['Close']
        capital = 0
    elif row['signal'] == 'SELL' and position > 0:
        capital = position * row['Close']
        pnl = capital - 10000
        trades.append(pnl)
        position = 0

# Results
if trades:
    win_rate = sum(1 for t in trades if t > 0) / len(trades)
    profit_factor = sum(t for t in trades if t > 0) / abs(sum(t for t in trades if t < 0)) if any(t < 0 for t in trades) else float('inf')
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Profit Factor: {profit_factor:.2f}")
else:
    print("No trades executed.")