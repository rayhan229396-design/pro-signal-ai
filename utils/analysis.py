import pandas as pd
import numpy as np
import ta
from utils.data_fetcher import get_dhaka_time

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 30:
        return df
    
    df = df.copy()
    
    # Short-term EMAs (Binary এর জন্য দ্রুত)
    df["EMA_5"] = ta.trend.ema_indicator(df["Close"], window=5)
    df["EMA_8"] = ta.trend.ema_indicator(df["Close"], window=8)
    df["EMA_13"] = ta.trend.ema_indicator(df["Close"], window=13)
    df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
    
    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=7)  # Faster RSI for binary
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=8, smooth_window=3)
    df["STOCH_K"] = stoch.stoch()
    df["STOCH_D"] = stoch.stoch_signal()
    
    # MACD (faster settings)
    macd = ta.trend.MACD(df["Close"], window_slow=21, window_fast=8, window_sign=5)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df["Close"], window=14, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_Mid"] = bb.bollinger_mavg()
    
    # ATR
    df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=10)
    
    # Candle body & direction
    df["Body"] = df["Close"] - df["Open"]
    df["Body_Size"] = abs(df["Body"])
    df["Candle_Dir"] = np.where(df["Close"] > df["Open"], 1, -1)
    
    return df


def generate_signal(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 25:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "trend": "Unknown",
            "entry": "None",
            "reasons": ["Not enough data"],
            "price": 0,
            "time": get_dhaka_time()
        }
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    
    score = 50
    reasons = []
    
    close = float(latest["Close"])
    open_price = float(latest["Open"])
    rsi = latest.get("RSI", 50)
    stoch_k = latest.get("STOCH_K", 50)
    stoch_d = latest.get("STOCH_D", 50)
    
    # ===================== 1. Short EMA Momentum =====================
    ema5 = latest.get("EMA_5")
    ema8 = latest.get("EMA_8")
    ema13 = latest.get("EMA_13")
    
    if ema5 and ema8:
        if ema5 > ema8:
            score += 8
            reasons.append("EMA5 > EMA8 (bullish momentum)")
        else:
            score -= 8
            reasons.append("EMA5 < EMA8 (bearish momentum)")
    
    if ema8 and ema13:
        if ema8 > ema13:
            score += 6
            reasons.append("EMA8 > EMA13")
        else:
            score -= 6
            reasons.append("EMA8 < EMA13")
    
    # ===================== 2. RSI (Fast) =====================
    if rsi < 28:
        score += 12
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi < 40:
        score += 6
        reasons.append(f"RSI low ({rsi:.1f})")
    elif rsi > 72:
        score -= 12
        reasons.append(f"RSI Overbought ({rsi:.1f})")
    elif rsi > 60:
        score -= 6
        reasons.append(f"RSI high ({rsi:.1f})")
    
    # ===================== 3. Stochastic =====================
    if stoch_k < 20 and stoch_k > stoch_d:
        score += 10
        reasons.append(f"Stoch Oversold + Turning Up ({stoch_k:.1f})")
    elif stoch_k < 25:
        score += 6
        reasons.append(f"Stoch Oversold ({stoch_k:.1f})")
    elif stoch_k > 80 and stoch_k < stoch_d:
        score -= 10
        reasons.append(f"Stoch Overbought + Turning Down ({stoch_k:.1f})")
    elif stoch_k > 75:
        score -= 6
        reasons.append(f"Stoch Overbought ({stoch_k:.1f})")
    
    # ===================== 4. MACD Histogram =====================
    macd_hist = latest.get("MACD_Hist", 0)
    prev_hist = prev.get("MACD_Hist", 0)
    
    if macd_hist > 0 and prev_hist <= 0:
        score += 11
        reasons.append("MACD Hist Bullish Cross")
    elif macd_hist < 0 and prev_hist >= 0:
        score -= 11
        reasons.append("MACD Hist Bearish Cross")
    elif macd_hist > 0:
        score += 4
    else:
        score -= 4
    
    # ===================== 5. Current Candle Strength =====================
    body = latest.get("Body", 0)
    body_size = latest.get("Body_Size", 0)
    atr = latest.get("ATR", 0.0001)
    
    # Strong bullish candle
    if body > 0 and body_size > (atr * 0.6):
        score += 7
        reasons.append("Strong Bullish Candle")
    # Strong bearish candle
    elif body < 0 and body_size > (atr * 0.6):
        score -= 7
        reasons.append("Strong Bearish Candle")
    
    # ===================== 6. Bollinger Position =====================
    bb_lower = latest.get("BB_Lower")
    bb_upper = latest.get("BB_Upper")
    
    if bb_lower and close <= bb_lower * 1.001:
        score += 8
        reasons.append("Price at Lower Bollinger")
    elif bb_upper and close >= bb_upper * 0.999:
        score -= 8
        reasons.append("Price at Upper Bollinger")
    
    # ===================== 7. Recent Momentum (last 2 candles) =====================
    if prev["Candle_Dir"] == 1 and latest["Candle_Dir"] == 1:
        score += 5
        reasons.append("2 consecutive bullish candles")
    elif prev["Candle_Dir"] == -1 and latest["Candle_Dir"] == -1:
        score -= 5
        reasons.append("2 consecutive bearish candles")
# Final score
    score = max(0, min(100, int(score)))
    
    # ===================== Binary Decision (More Sensitive) =====================
    if score >= 62:
        signal = "CALL"
        entry = "UP"
        trend = "Bullish"
    elif score <= 38:
        signal = "PUT"
        entry = "DOWN"
        trend = "Bearish"
    else:
        signal = "WAIT"
        entry = "None"
        trend = "Sideways / Unclear"
    
    # Confidence
    if signal == "WAIT":
        confidence = max(30, 100 - abs(score - 50) * 1.6)
    else:
        confidence = score if signal == "CALL" else (100 - score)
    
    confidence = int(min(90, max(50, confidence)))
    
    return {
        "signal": signal,
        "confidence": confidence,
        "trend": trend,
        "entry": entry,
        "reasons": reasons[:7],
        "price": round(close, 5),
        "time": get_dhaka_time(),
        "rsi": round(rsi, 1) if rsi else None,
        "score": score          # ← এইটা যোগ করা হয়েছে
    }
