import pandas as pd
import numpy as np
import ta
from utils.data_fetcher import get_dhaka_time, fetch_data

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 35:
        return df
    
    df = df.copy()
    
    # EMAs
    df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
    df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
    
    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    
    # MACD
    macd = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    
    # Candle Structure
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
    
    body = curr["Body_Size"] if curr["Body_Size"] > 0 else 0.00001
    l_wick = curr["Lower_Wick"]
    u_wick = curr["Upper_Wick"]
    
    # Bullish Rejection / Hammer
    if l_wick >= (body * 2.0) and u_wick <= (body * 0.5):
        return "Bullish Rejection", 15
    
    # Bearish Rejection / Shooting Star (SELL Signal)
    if u_wick >= (body * 2.0) and l_wick <= (body * 0.5):
        return "Bearish Rejection", -15
        
    # Bullish Engulfing
    if prev["Body"] < 0 and curr["Body"] > 0 and curr["Close"] > prev["Open"]:
        return "Bullish Engulfing", 12
        
    # Bearish Engulfing (SELL Signal)
    if prev["Body"] > 0 and curr["Body"] < 0 and curr["Close"] < prev["Open"]:
        return "Bearish Engulfing", -12
        
    return None, 0

def check_support_resistance(df: pd.DataFrame) -> tuple:
    if len(df) < 30:
        return "Mid Zone", 0
    
    curr_close = df.iloc[-1]["Close"]
    recent_low = df["Low"].tail(30).min()
    recent_high = df["High"].tail(30).max()
    
    # Support (BUY) & Resistance (SELL)
    if abs(curr_close - recent_low) / curr_close < 0.0008:
        return "At Key Support Zone", 12
    elif abs(curr_close - recent_high) / curr_close < 0.0008:
        return "At Key Resistance Zone", -12
        
    return "Neutral Zone", 0

def generate_signal(df: pd.DataFrame, pair: str = "", timeframe: str = "5m") -> dict:
    if df.empty or len(df) < 35:
        return {
            "signal": "WAIT", "confidence": 0, "trend": "Unknown",
            "entry": "None", "reasons": ["Not enough live data"],
            "price": 0, "time": get_dhaka_time()
        }
    
    # HTF Trend (1 Hour)
    htf_frame = "1h"
    htf_df = fetch_data(pair, timeframe=htf_frame, limit=50)
    htf_trend = "Neutral"
    
    if not htf_df.empty and len(htf_df) > 20:
        htf_ema_short = ta.trend.ema_indicator(htf_df["Close"], window=9)
        htf_ema_long = ta.trend.ema_indicator(htf_df["Close"], window=21)
        
        if htf_ema_short.iloc[-1] > htf_ema_long.iloc[-1]:
            htf_trend = "Bullish"
        elif htf_ema_short.iloc[-1] < htf_ema_long.iloc[-1]:
            htf_trend = "Bearish"
    
    latest = df.iloc[-1]
    score = 50
    reasons = []
    
    # 1. 1-Hour Trend Check
    if htf_trend == "Bullish":
        score += 6
        reasons.append("1-Hour Trend is Bullish")
    elif htf_trend == "Bearish":
        score -= 6
        reasons.append("1-Hour Trend is Bearish")

    # 2. Candlestick Patterns
    pattern, p_score = detect_candlestick_pattern(df)
    if pattern:
        score += p_score
        reasons.append(f"Pattern: {pattern}")
        
    # 3. Support / Resistance
    sr_zone, sr_score = check_support_resistance(df)
    if sr_score != 0:
        score += sr_score
        reasons.append(sr_zone)

    # 4. Indicators (Balanced Add/Subtract)
    rsi = latest.get("RSI", 50)
    macd = latest.get("MACD", 0)
    macd_signal = latest.get("MACD_Signal", 0)
    
    # RSI Thresholds
    if rsi < 35:
        score += 15
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi > 65:
        score -= 15
        reasons.append(f"RSI Overbought ({rsi:.1f})")
        
    # MACD Crossover
    if macd > macd_signal:
        score += 10
        reasons.append("MACD Bullish Crossover")
    elif macd < macd_signal:
        score -= 10
        reasons.append("MACD Bearish Crossover")

    # EMA Alignment
    if latest["EMA_9"] > latest["EMA_21"]:
        score += 8
    elif latest["EMA_9"] < latest["EMA_21"]:
        score -= 8

    # Limit Score
    score = max(0, min(100, int(score)))

    # 5. Balanced Threshold (58 & 42)
    if score >= 58:
        signal = "CALL"
        entry = "UP (5m Candle Expiry)"
    elif score <= 42:
        signal = "PUT"
        entry = "DOWN (5m Candle Expiry)"
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
