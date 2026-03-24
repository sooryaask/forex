import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

# Load data
data_path = 'data/historical_data.parquet'
df = pd.read_parquet(data_path)

# Define asset classes
ASSET_CLASSES = ['forex', 'stocks', 'metals', 'crypto']

# Features
FEATURES = ['Open', 'High', 'Low', 'Close', 'Volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_diff', 'BB_upper', 'BB_lower', 'BB_middle', 'Volume_Delta']

# Target: predict next close direction and magnitude
def create_target(df, horizon=1):
    df['future_close'] = df['Close'].shift(-horizon)
    df['direction'] = (df['future_close'] > df['Close']).astype(int)  # 1 up, 0 down
    df['magnitude'] = (df['future_close'] - df['Close']) / df['Close']  # percentage change
    return df.dropna()

# Train XGBoost for classification
def train_xgb_classifier(X_train, y_train, asset_class):
    model = xgb.XGBClassifier(objective='binary:logistic', n_estimators=100, max_depth=6)
    model.fit(X_train, y_train)
    joblib.dump(model, f'models/xgb_classifier_{asset_class}.pkl')
    return model

# Train RandomForest for regression (magnitude)
def train_rf_regressor(X_train, y_train, asset_class):
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, f'models/rf_regressor_{asset_class}.pkl')
    return model

def main():
    os.makedirs('models', exist_ok=True)
    
    for asset_class in ASSET_CLASSES:
        print(f"Training models for {asset_class}...")
        asset_df = df[df['asset_class'] == asset_class].copy()
        if asset_df.empty:
            continue
        
        asset_df = create_target(asset_df)
        asset_df = asset_df[FEATURES + ['direction', 'magnitude']]
        
        # Split
        X = asset_df[FEATURES]
        y_class = asset_df['direction']
        y_reg = asset_df['magnitude']
        
        X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
            X, y_class, y_reg, test_size=0.2, random_state=42
        )
        
        # Scale
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        joblib.dump(scaler, f'models/scaler_{asset_class}.pkl')
        
        # Train classifier
        xgb_model = train_xgb_classifier(X_train_scaled, y_class_train, asset_class)
        y_pred_class = xgb_model.predict(X_test_scaled)
        acc = accuracy_score(y_class_test, y_pred_class)
        print(f"XGBoost accuracy for {asset_class}: {acc:.2f}")
        
        # Train regressor
        rf_model = train_rf_regressor(X_train_scaled, y_reg_train, asset_class)
        y_pred_reg = rf_model.predict(X_test_scaled)
        mse = mean_squared_error(y_reg_test, y_pred_reg)
        print(f"RF MSE for {asset_class}: {mse:.4f}")

if __name__ == '__main__':
    main()