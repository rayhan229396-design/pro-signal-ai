import pandas as pd
import numpy as np
import ta
from utils.data_fetcher import get_dhaka_time, fetch_data

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
    
    # থ্রেশহোল্ড বাড়িয়ে 0.0015 (0.15%) করা হয়েছে যেন লেভেল সহজে ডিটেক্ট হয়
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
    
    # Higher Timeframe Trend Alignment
    htf_frame = "15m" if timeframe in ["1m", "5m"] else "15m"
    htf_df = fetch_data(pair, timeframe=htf_frame, limit=50)
    htf_trend = "Neutral"
    
    if not htf_df.empty and len(htf_df) > 20:
        htf_ema = ta.trend.ema_indicator(htf_df["Close"], window=20)
        if htf_df["Close"].iloc[-1] > htf_ema.iloc[-1]:
            htf_trend = "Bullish"
        else:
            htf_trend = "Bearish"
    
    latest = df.iloc[-1]
    score = 50
    reasons = []
    
    # 1. HTF Trend
    if htf_trend == "Bullish":
        score += 10
        reasons.append(f"Higher Timeframe ({htf_frame}) is Bullish")
    elif htf_trend == "Bearish":
        score -= 10
        reasons.append(f"Higher Timeframe ({htf_frame}) is Bearish")

    # 2. Price Action Patterns & S/R
    pattern, p_score = detect_candlestick_pattern(df)
    if pattern:
        score += p_score
        reasons.append(f"Pattern: {pattern}")
        
    sr_zone, sr_score = check_support_resistance(df)
    if sr_score != 0:
        score += sr_score
        reasons.append(sr_zone)

    # 3. Technical Indicators (RSI এবং Stochastic সীমা শিথিল করা হয়েছে)
    rsi = latest.get("RSI", 50)
    stoch_k = latest.get("STOCH_K", 50)
    
    if rsi < 35:  # 30 থেকে বাড়িয়ে 35 করা হয়েছে
        score += 10
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi > 65:  # 70 থেকে কমিয়ে 65 করা হয়েছে
        score -= 10
        reasons.append(f"RSI Overbought ({rsi:.1f})")
        
    if stoch_k < 25:  # 20 থেকে বাড়িয়ে 25 করা হয়েছে
        score += 8
        reasons.append("Stochastic Oversold")
    elif stoch_k > 75:  # 80 থেকে কমিয়ে 75 করা হয়েছে
        score -= 8
        reasons.append("Stochastic Overbought")

    if latest["EMA_8"] > latest["EMA_21"]:
        score += 6
    else:
        score -= 6

    score = max(0, min(100, int(score)))

    # 4. Final Binary Signal Decision (থ্রেশহোল্ড ৫০-এর কাছাকাছি ৫৮ এবং ৪২ এ আনা হয়েছে)
    if score >= 58 and htf_trend != "Bearish":
        signal = "CALL"
        entry = "UP (1-Candle Expiry)"
    elif score <= 42 and htf_trend != "Bullish":
        signal = "PUT"
        entry = "DOWN (1-Candle Expiry)"
    else:
        signal = "WAIT"
        entry = "None"

    confidence = score if signal == "CALL" else (100 - score if signal == "PUT" else 50)
    
    return {
        "signal": signal,
        "confidence": int(confidence),
        "trend": htf_trend,
        "entry": entry,
        "reasons": reasons[:6],
        "price": round(float(latest["Close"]), 5),
        "time": get_dhaka_time()
    }
