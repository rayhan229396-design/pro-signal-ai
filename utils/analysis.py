import pandas as pd
import numpy as np
import ta
from utils.data_fetcher import get_dhaka_time

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 30:
        return df
    
    df = df.copy()
    
    # Trend
    df["EMA_9"] = ta.trend.ema_indicator(df["Close"], window=9)
    df["EMA_21"] = ta.trend.ema_indicator(df["Close"], window=21)
    df["EMA_50"] = ta.trend.ema_indicator(df["Close"], window=50)
    df["SMA_50"] = ta.trend.sma_indicator(df["Close"], window=50)
    
    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    
    # MACD
    macd = ta.trend.MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_Mid"] = bb.bollinger_mavg()
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"])
    df["STOCH_K"] = stoch.stoch()
    df["STOCH_D"] = stoch.stoch_signal()
    
    # ADX (Trend Strength)
    df["ADX"] = ta.trend.adx(df["High"], df["Low"], df["Close"], window=14)
    
    # ATR
    df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14)
    
    # Supertrend
    df = add_supertrend(df)
    
    # Support / Resistance
    df["Resistance"] = df["High"].rolling(20).max()
    df["Support"] = df["Low"].rolling(20).min()
    
    return df


def add_supertrend(df: pd.DataFrame, period=10, multiplier=3.0) -> pd.DataFrame:
    hl2 = (df["High"] + df["Low"]) / 2
    atr = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=period)
    
    upper = hl2 + (multiplier * atr)
    lower = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    supertrend.iloc[0] = upper.iloc[0]
    direction.iloc[0] = 1
    
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > supertrend.iloc[i-1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < supertrend.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
            
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == 1 else lower.iloc[i]
        else:
            supertrend.iloc[i] = min(upper.iloc[i], supertrend.iloc[i-1]) if direction.iloc[i-1] == -1 else upper.iloc[i]
    
    df["Supertrend"] = supertrend
    df["Supertrend_Dir"] = direction
    return df


def generate_signal(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 30:
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
    
    score = 50
    reasons = []
    
    close = float(latest["Close"])
    rsi = latest.get("RSI", 50)
    adx = latest.get("ADX", 0)
    
    # LAYER 1: Trend Direction
    ema9 = latest.get("EMA_9")
    ema21 = latest.get("EMA_21")
    ema50 = latest.get("EMA_50")
    
    if ema9 and ema21 and ema9 > ema21:
        score += 6
        reasons.append("EMA9 > EMA21 (short-term up)")
    elif ema9 and ema21:
        score -= 6
        reasons.append("EMA9 < EMA21 (short-term down)")
    
    if ema21 and ema50 and ema21 > ema50:
        score += 5
        reasons.append("EMA21 > EMA50 (medium uptrend)")
    elif ema21 and ema50:
        score -= 5
        reasons.append("EMA21 < EMA50 (medium downtrend)")
    
    if latest.get("Supertrend_Dir") == 1:
        score += 7
        reasons.append("Supertrend Bullish")
    else:
        score -= 7
        reasons.append("Supertrend Bearish")
    
    # LAYER 2: Momentum
    if rsi < 30:
        score += 12
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi < 40:
        score += 6
        reasons.append(f"RSI low ({rsi:.1f})")
    elif rsi > 70:
        score -= 12
        reasons.append(f"RSI Overbought ({rsi:.1f})")
    elif rsi > 60:
        score -= 6
        reasons.append(f"RSI high ({rsi:.1f})")
    
    if latest.get("MACD") and latest.get("MACD_Signal"):
        if latest["MACD"] > latest["MACD_Signal"] and prev.get("MACD", 0) <= prev.get("MACD_Signal", 0):
            score += 9
            reasons.append("MACD Bullish Cross")
        elif latest["MACD"] < latest["MACD_Signal"] and prev.get("MACD", 0) >= prev.get("MACD_Signal", 0):
            score -= 9
            reasons.append("MACD Bearish Cross")
        elif latest.get("MACD_Hist", 0) > 0:
            score += 3
        else:
            score -= 3
    
    stoch_k = latest.get("STOCH_K", 50)
    if stoch_k < 20:
        score += 7
        reasons.append(f"Stochastic Oversold ({stoch_k:.1f})")
    elif stoch_k > 80:
        score -= 7
        reasons.append(f"Stochastic Overbought ({stoch_k:.1f})")
    
    # LAYER 3: Volatility & Strength
    if adx > 25:
        score += 4
        reasons.append(f"Strong Trend (ADX {adx:.1f})")
    elif adx < 15:
        score -= 3
        reasons.append(f"Weak Trend (ADX {adx:.1f})")
    
    if latest.get("BB_Lower") and close <= latest["BB_Lower"] * 1.003:
        score += 8
        reasons.append("Price at Lower Bollinger")
    elif latest.get("BB_Upper") and close >= latest["BB_Upper"] * 0.997:
        score -= 8
        reasons.append("Price at Upper Bollinger")
    
    # LAYER 4: Structure
    dist_to_sup = (close - latest.get("Support", close)) / close * 100 if latest.get("Support") else 99
    dist_to_res = (latest.get("Resistance", close) - close) / close * 100 if latest.get("Resistance") else 99
    
    if dist_to_sup < 0.35:
        score += 8
        reasons.append("Near Support")
    if dist_to_res < 0.35:
        score -= 8
        reasons.append("Near Resistance")
    
    score = max(0, min(100, int(score)))
    
    if score >= 72:
        signal = "BUY"
        entry = "LONG"
        trend = "Bullish"
    elif score <= 28:
        signal = "SELL"
        entry = "SHORT"
        trend = "Bearish"
    else:
        signal = "WAIT"
        entry = "None"
        trend = "Sideways / Unclear"
    
    if signal == "WAIT":
        confidence = max(30, 100 - abs(score - 50) * 1.5)
    else:
        confidence = score if signal == "BUY" else (100 - score)
    
    confidence = int(min(95, max(40, confidence)))
    
    return {
        "signal": signal,
        "confidence": confidence,
        "trend": trend,
        "entry": entry,
        "reasons": reasons[:7],
        "price": round(close, 5),
        "time": get_dhaka_time(),
        "rsi": round(rsi, 1) if rsi else None,
        "adx": round(adx, 1) if adx else None,
        "score": score
    }
