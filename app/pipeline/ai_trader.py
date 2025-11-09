import os
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
import importlib
import tensorflow as tf
from pydantic import BaseModel

# === DYNAMIC PATHS (works anywhere) ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "pipeline", "AAPL_lstm_best.keras")
SCALER_PATH = os.path.join(
    BASE_DIR, "pipeline", "AAPL_scaler_with_sent.joblib")

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

_sentiment_pipeline = None


def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            hf = importlib.import_module("transformers")
            hf_pipeline = getattr(hf, "pipeline")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Missing 'transformers' or incompatible Keras. Install with: pip install transformers tf-keras") from e
        _sentiment_pipeline = hf_pipeline(
            "sentiment-analysis",
            model="yiyanghkust/finbert-tone",
            tokenizer="yiyanghkust/finbert-tone"
        )
    return _sentiment_pipeline


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

    df['MACD'] = df['Close'].ewm(span=12).mean() - \
        df['Close'].ewm(span=26).mean()

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


@router.get("/realtime/{ticker}")
async def get_realtime(ticker: str = "AAPL"):
    """Get real-time market data and prediction"""
    ticker = ticker.upper()
    try:
        end = datetime.now()

        # First get historical daily data (this always works)
        start_hist = end - timedelta(days=180)
        df_hist = yf.download(ticker, start=start_hist,
                              end=end, progress=False)

        if df_hist.empty:
            raise ValueError(f"No data available for {ticker}")

        # Get the last trading day's data
        df_today = df_hist.tail(1)
        latest_time = df_hist.index[-1]
        market_open = False

        # Try to get intraday data if we're during market hours
        if end.weekday() < 5:  # Monday-Friday
            try:
                start = end - timedelta(hours=8)  # Last 8 hours
                df_intraday = yf.download(
                    ticker, start=start, end=end, interval='1m', progress=False)
                if not df_intraday.empty:
                    df_today = df_intraday
                    latest_time = df_intraday.index[-1]
                    market_open = True
            except Exception:
                pass  # Fallback to daily data

        # Get latest price and trading info
        latest_price = float(df_today['Close'].iloc[-1])
        latest_time = df_today.index[-1]

        # Prepare prediction data
        df_feat = add_features(df_hist)
        if len(df_feat) < SEQ_LEN:
            raise ValueError("Not enough historical data")

        # Get prediction
        scaled = scaler.transform(df_feat[FINAL_FEATURES].tail(SEQ_LEN))
        X = scaled.reshape(1, SEQ_LEN, len(FINAL_FEATURES))
        pred_price = float(model.predict(X, verbose=0)[0][0])

        # Calculate metrics
        pct_change = (pred_price - latest_price) / latest_price * 100
        day_change = (
            latest_price - float(df_today['Open'].iloc[0])) / float(df_today['Open'].iloc[0]) * 100

        return {
            "ticker": ticker,
            "timestamp": latest_time.isoformat(),
            "market_open": market_open,
            "current_price": round(latest_price, 2),
            "day_change_pct": round(day_change, 2),
            "day_high": round(float(df_today['High'].max()), 2),
            "day_low": round(float(df_today['Low'].min()), 2),
            "volume": int(df_today['Volume'].sum()),
            "prediction": {
                "price": round(pred_price, 2),
                "change_pct": round(pct_change, 2),
                "signal": "STRONG_BUY" if pct_change > 5 else
                "BUY" if pct_change > 2 else
                "SELL" if pct_change < -2 else
                "STRONG_SELL" if pct_change < -5 else "HOLD"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        signal = "APOCALYPTIC SELL" if pct < - \
            50 else "SELL" if pct < -5 else "BUY" if pct > 2 else "HOLD"

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


class NewsAnalysisRequest(BaseModel):
    prompt: str
    ticker: str = "AAPL"  # Default to AAPL if not provided


@router.post("/analyze")
async def analyze_news(request: NewsAnalysisRequest):
    sentiment_pipeline = get_sentiment_pipeline()
    sentiment_result = sentiment_pipeline(request.prompt)[0]
    label = sentiment_result['label']
    score = sentiment_result['score']
    sentiment_score = score if label == "Positive" else - \
        score if label == "Negative" else 0

    # 3. Fetch data
    end = datetime.now()
    start = end - timedelta(days=180)
    df = yf.download(request.ticker, start=start, end=end, progress=False)
    if df.empty:
        raise HTTPException(242, detail=f"No data for {request.ticker}")

    # 4. Features
    df_feat = add_features(df)
    df_feat.loc[df_feat.index[-7:],
                'score'] = sentiment_score  # inject sentiment

    # 5. Predict
    scaled = scaler.transform(df_feat[FINAL_FEATURES].tail(SEQ_LEN))
    X = scaled.reshape(1, SEQ_LEN, len(FINAL_FEATURES))
    pred_price = float(model.predict(X, verbose=0)[0][0])

    last_close = float(df_feat['Close'].iloc[-1])
    pct = (pred_price - last_close) / last_close * 100

    # 6. Sanity check
    if abs(pct) > 100:
        confidence = "LOW (extreme move)"
    elif abs(pct) > 20:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    # 7. Human explanation
    direction = "UP" if pct > 0 else "DOWN"
    explanation = f"The model predicts a {abs(pct):.1f}% move {direction} due to "
    if abs(sentiment_score) > 0.5:
        explanation += f"{'strong bullish' if sentiment_score > 0 else 'strong bearish'} sentiment in your prompt."
    else:
        explanation += "technical patterns and momentum."

    return {
        "ticker": request.ticker,
        "user_prompt": request.prompt,
        "sentiment": label.lower(),
        "sentiment_score": round(sentiment_score, 3),
        "last_close": round(last_close, 2),
        "predicted_close": round(pred_price, 2),
        "expected_move_pct": round(pct, 2),
        "signal": "APOCALYPTIC SELL" if pct < -50 else "SELL" if pct < -5 else "BUY" if pct > 5 else "HOLD",
        "confidence": confidence,
        "explanation": explanation,
        "timestamp": datetime.now().isoformat()
    }
