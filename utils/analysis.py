import pandas as pd
import numpy as np
import ta
from utils.data_fetcher import get_dhaka_time

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 30:
        return df
    
    df = df.copy()
    
    # EMA Momentum
    df["EMA_8"] = ta.trend.ema_indicator(df["Close"], window=8)
    df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
    
    # RSI & Stochastic
    df["RSI"] = ta.momentum.rsi(df["Close"], window=7)
    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"], window=8, smooth_window=3)
    df["STOCH_K"] = stoch.stoch()
    
    # Candle Body Structure
    df["Body"] = df["Close"] - df["Open"]
    df["Body_Size"] = abs(df["Body"])
    df["Upper_Wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["Lower_Wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    
    return df

def detect_candlestick_pattern(df: pd.DataFrame) -> tuple:
    if len(df) < 3:
        return None, 0
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    body = curr["Body_Size"]
    l_wick = curr["Lower_Wick"]
    u_wick = curr["Upper_Wick"]
    
    # Hammer / Bullish Pinbar
    if l_wick >= (body * 2) and u_wick <= (body * 0.5):
        return "Bullish Pinbar / Hammer", 15
    
    # Shooting Star / Bearish Pinbar
    if u_wick >= (body * 2) and l_wick <= (body * 0.5):
        return "Bearish Shooting Star", -15
        
    # Bullish Engulfing
    if prev["Body"] < 0 and curr["Body"] > 0 and curr["Close"] > prev["Open"] and curr["Open"] < prev["Close"]:
        return "Bullish Engulfing", 18
        
    # Bearish Engulfing
    if prev["Body"] > 0 and curr["Body"] < 0 and curr["Close"] < prev["Open"] and curr["Open"] > prev["Close"]:
        return "Bearish Engulfing", -18
        
    return None, 0

def check_support_resistance(df: pd.DataFrame) -> tuple:
    if len(df) < 20:
        return "Mid Zone", 0
    
    curr_close = df.iloc[-1]["Close"]
    recent_low = df["Low"].tail(20).min()
    recent_high = df["High"].tail(20).max()
    
    if abs(curr_close - recent_low) / curr_close < 0.0015:
        return "At Key Support Level", 12
    elif abs(curr_close - recent_high) / curr_close < 0.0015:
        return "At Key Resistance Level", -12
        
    return "Neutral Zone", 0

def generate_signal(df: pd.DataFrame, pair: str = "", timeframe: str = "5m") -> dict:
    if df.empty or len(df) < 30:
        return {
            "signal": "WAIT", "confidence": 0, "trend": "Unknown",
            "entry": "None", "reasons": ["Not enough live data"],
            "price": 0, "time": get_dhaka_time()
        }
    
    latest = df.iloc[-1]
    score = 50
    reasons = []

    # 1. Price Action Patterns & S/R
    pattern, p_score = detect_candlestick_pattern(df)
    if pattern:
        score += p_score
        reasons.append(f"Pattern: {pattern}")
        
    sr_zone, sr_score = check_support_resistance(df)
    if sr_score != 0:
        score += sr_score
        reasons.append(sr_zone)

    # 2. Technical Indicators
    rsi = latest.get("RSI", 50)
    stoch_k = latest.get("STOCH_K", 50)
    
    if rsi < 35:
        score += 10
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi > 65:
        score -= 10
        reasons.append(f"RSI Overbought ({rsi:.1f})")
        
    if stoch_k < 25:
        score += 8
        reasons.append("Stochastic Oversold")
    elif stoch_k > 75:
        score -= 8
        reasons.append("Stochastic Overbought")

    if latest["EMA_8"] > latest["EMA_21"]:
        score += 6
        reasons.append("EMA Short-term Uptrend")
    else:
        score -= 6
        reasons.append("EMA Short-term Downtrend")

    score = max(0, min(100, int(score)))

    # 3. Final Binary Signal Decision
    if score >= 60:
        signal = "CALL"
        entry = "UP (1-Candle Expiry)"
    elif score <= 40:
        signal = "PUT"
        entry = "DOWN (1-Candle Expiry)"
    else:
        signal = "WAIT"
        entry = "None"

    confidence = score if signal == "CALL" else (100 - score if signal == "PUT" else 50)
    
    return {
        "signal": signal,
        "confidence": int(confidence),
        "trend": "Disabled",
        "entry": entry,
        "reasons": reasons[:6],
        "price": round(float(latest["Close"]), 5),
        "time": get_dhaka_time()
    }
