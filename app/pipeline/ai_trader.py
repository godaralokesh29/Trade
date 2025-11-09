import os
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
import tensorflow as tf

# === DYNAMIC PATHS (works anywhere) ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "pipeline", "AAPL_lstm_best.keras")
SCALER_PATH = os.path.join(BASE_DIR, "pipeline", "AAPL_scaler_with_sent.joblib")

SEQ_LEN = 60
FINAL_FEATURES = [
    'Open', 'High', 'Low', 'Close', 'Volume',
    'return', 'MA7', 'MA30', 'RSI', 'MACD',
    'BB_high', 'BB_low', 'vol_z', 'score'
]

# === Load once at startup ===
print(f"Loading AI model from: {MODEL_PATH}")
model = tf.keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
print("AI Trader READY")

router = APIRouter(prefix="/ai", tags=["AI Trader"])

# === add_features function (copy-paste) ===
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['return'] = df['Close'].pct_change().fillna(0)
    df['MA7'] = df['Close'].rolling(7, min_periods=1).mean()
    df['MA30'] = df['Close'].rolling(30, min_periods=1).mean()
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    
    rolling_mean = df['Close'].rolling(20).mean()
    rolling_std = df['Close'].rolling(20).std()
    df['BB_high'] = rolling_mean + 2 * rolling_std
    df['BB_low'] = rolling_mean - 2 * rolling_std
    
    vol_mean = df['Volume'].rolling(30).mean()
    vol_std = df['Volume'].rolling(30).std()
    df['vol_z'] = (df['Volume'] - vol_mean) / vol_std
    df['vol_z'] = df['vol_z'].fillna(0)
    df['score'] = 0.0
    return df.dropna()

# === ROUTE ===
@router.get("/predict/{ticker}")
async def predict_ticker(ticker: str = "AAPL"):
    ticker = ticker.upper()
    try:
        end = datetime.now()
        start = end - timedelta(days=180)
        df = yf.download(ticker, start=start, end=end, progress=False)
        if df.empty:
            raise ValueError("No data")

        df_feat = add_features(df)
        if len(df_feat) < SEQ_LEN:
            raise ValueError("Not enough data")

        scaled = scaler.transform(df_feat[FINAL_FEATURES].tail(SEQ_LEN))
        X = scaled.reshape(1, SEQ_LEN, len(FINAL_FEATURES))

        pred_price = float(model.predict(X, verbose=0)[0][0])
        last_close = float(df_feat['Close'].iloc[-1])
        pct = (pred_price - last_close) / last_close * 100

        signal = "APOCALYPTIC SELL" if pct < -50 else "SELL" if pct < -5 else "BUY" if pct > 2 else "HOLD"

        return {
            "ticker": ticker,
            "last_close": round(last_close, 2),
            "ai_prediction": round(pred_price, 2),
            "move_pct": round(pct, 2),
            "signal": signal,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))