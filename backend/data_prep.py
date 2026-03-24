import yfinance as yf
import pandas as pd
import ta
from fredapi import Fred
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timedelta
import os

# FRED API key - get from https://fred.stlouisfed.org/docs/api/api_key.html (free)
FRED_API_KEY = ' 024d565d11cb44a08964344c2420f593 '  # Replace with actual key  # Replace with actual key

# Define assets
ASSETS = {
    'forex': ['EURUSD=X', 'GBPUSD=X'],
    'stocks': ['AAPL', 'TSLA'],
    'metals': ['GC=F'],  # Gold
    'crypto': ['BTC-USD']
}

# Economic indicators (FRED series IDs)
ECONOMIC_INDICATORS = {
    'US_GDP': 'GDP',
    'US_CPI': 'CPIAUCSL',  # Inflation
    'US_FED_RATE': 'FEDFUNDS',
    'UK_GDP': 'UKNGDP',
    'UK_CPI': 'GBRCPIALLMINMEI',  # UK CPI
    'UK_RATE': 'BOERUKM'  # Bank of England rate
}

def fetch_price_data(symbol, period='2y', interval='1h'):
    """Fetch historical price data from Yahoo Finance."""
    try:
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        if data.index.tz is not None:
            data = data.tz_convert('UTC')
        else:
            data = data.tz_localize('UTC')
        return data
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def fetch_economic_data():
    """Fetch economic indicators from FRED."""
    if not FRED_API_KEY or FRED_API_KEY == 'your_fred_api_key_here':
        print("FRED API key not set. Skipping economic data.")
        return pd.DataFrame()
    fred = Fred(api_key=FRED_API_KEY)
    economic_data = {}
    for name, series_id in ECONOMIC_INDICATORS.items():
        try:
            data = fred.get_series(series_id, start_date='2022-01-01')  # Last 2 years
            economic_data[name] = data
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    return pd.DataFrame(economic_data)

def add_technical_indicators(df):
    """Add technical analysis indicators."""
    close = df['Close']
    
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_diff'] = df['MACD'] - df['MACD_signal']
    
    # Bollinger Bands
    sma = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    df['BB_upper'] = sma + 2 * std
    df['BB_lower'] = sma - 2 * std
    df['BB_middle'] = sma
    
    # Volume delta (if volume exists)
    if 'Volume' in df.columns:
        df['Volume_Delta'] = df['Volume'].pct_change()
    return df

def prepare_asset_data(symbol, asset_class):
    """Prepare data for a single asset."""
    print(f"Processing {symbol} ({asset_class})...")
    
    # Fetch price data
    price_data = fetch_price_data(symbol)
    if price_data is None or price_data.empty:
        return None
    
    # Add technical indicators
    price_data = add_technical_indicators(price_data)
    
    # Add asset class and symbol
    price_data['asset_class'] = asset_class
    price_data['symbol'] = symbol
    
    return price_data

def main():
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Fetch economic data once
    print("Fetching economic data...")
    economic_df = fetch_economic_data()
    economic_df.to_csv('data/economic_data.csv')
    
    # Process each asset
    all_data = []
    for asset_class, symbols in ASSETS.items():
        for symbol in symbols:
            data = prepare_asset_data(symbol, asset_class)
            if data is not None:
                all_data.append(data)
    
    if all_data:
        # Combine all data
        combined_df = pd.concat(all_data)
        
        # Save to Parquet
        table = pa.Table.from_pandas(combined_df)
        pq.write_table(table, 'data/historical_data.parquet')
        
        print("Data preparation complete. Saved to data/historical_data.parquet")
    else:
        print("No data fetched.")

if __name__ == '__main__':
    main()