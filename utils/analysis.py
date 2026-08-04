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
    df["EMA_50"] = ta.trend.ema_indicator(df["Close"], window=50)  # নতুন যোগ
    
    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    
    # MACD
    macd = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()  # হিস্টোগ্রাম যোগ করলাম
    
    # Bollinger Bands (নতুন)
    bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
    df["BB_High"] = bb.bollinger_hband()
    df["BB_Low"] = bb.bollinger_lband()
    df["BB_Mid"] = bb.bollinger_mavg()
    
    # ATR (ভোলাটিলিটি পরিমাপ)
    df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14)
    
    # Volume (যদি থাকে)
    if "Volume" in df.columns:
        df["Volume_SMA"] = df["Volume"].rolling(20).mean()
        df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA"]
    
    # Candle Structure
    df["Body"] = df["Close"] - df["Open"]
    df["Body_Size"] = abs(df["Body"])
    df["Upper_Wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["Lower_Wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    df["Candle_Range"] = df["High"] - df["Low"]
    
    return df

def detect_candlestick_pattern(df: pd.DataFrame) -> tuple:
    if len(df) < 3:
        return None, 0
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3] if len(df) >= 3 else None
    
    body = curr["Body_Size"] if curr["Body_Size"] > 0 else 0.00001
    l_wick = curr["Lower_Wick"]
    u_wick = curr["Upper_Wick"]
    range_ = curr["Candle_Range"] if curr["Candle_Range"] > 0 else 0.00001
    
    # ====== বর্ধিত প্যাটার্ন লিস্ট ======
    
    # 1. Bullish Rejection / Hammer (স্কোর বাড়ানো)
    if l_wick >= (body * 2.0) and u_wick <= (body * 0.5):
        return "Bullish Rejection (Hammer)", 22
    
    # 2. Bearish Rejection / Shooting Star
    if u_wick >= (body * 2.0) and l_wick <= (body * 0.5):
        return "Bearish Rejection (Shooting Star)", -22
        
    # 3. Bullish Engulfing (স্কোর বাড়ানো)
    if prev["Body"] < 0 and curr["Body"] > 0 and curr["Close"] > prev["Open"]:
        # ভলিউম কনফার্মেশন থাকলে বাড়তি স্কোর
        bonus = 5 if "Volume_Ratio" in df.columns and df["Volume_Ratio"].iloc[-1] > 1.5 else 0
        return "Bullish Engulfing", 20 + bonus
        
    # 4. Bearish Engulfing
    if prev["Body"] > 0 and curr["Body"] < 0 and curr["Close"] < prev["Open"]:
        bonus = 5 if "Volume_Ratio" in df.columns and df["Volume_Ratio"].iloc[-1] > 1.5 else 0
        return "Bearish Engulfing", -20 - bonus
    
    # 5. Doji (নতুন)
    if body <= (range_ * 0.1):
        return "Doji (Indecision)", 0  # নিজে স্কোর না, কিন্তু কনফার্মেশন দরকার
    
    # 6. Bullish Harami (নতুন)
    if prev["Body"] < 0 and curr["Body"] > 0 and curr["Body_Size"] < prev["Body_Size"] and curr["Close"] < prev["Open"]:
        return "Bullish Harami", 15
    
    # 7. Bearish Harami (নতুন)
    if prev["Body"] > 0 and curr["Body"] < 0 and curr["Body_Size"] < prev["Body_Size"] and curr["Close"] > prev["Open"]:
        return "Bearish Harami", -15
        
    return None, 0

def check_support_resistance(df: pd.DataFrame) -> tuple:
    if len(df) < 30:
        return "Mid Zone", 0
    
    curr_close = df.iloc[-1]["Close"]
    recent_low = df["Low"].tail(30).min()
    recent_high = df["High"].tail(30).max()
    
    # জোন প্রশস্ত করা (0.08% → 0.15%)
    if abs(curr_close - recent_low) / curr_close < 0.0015:
        return "At Key Support Zone", 15  # স্কোর বাড়ানো
    elif abs(curr_close - recent_high) / curr_close < 0.0015:
        return "At Key Resistance Zone", -15
        
    # ডাইনামিক সাপোর্ট/রেজিস্ট্যান্স (EMA)
    if "EMA_50" in df.columns:
        ema50 = df["EMA_50"].iloc[-1]
        if abs(curr_close - ema50) / curr_close < 0.001:
            return "At 50-EMA", 8 if curr_close > ema50 else -8
        
    return "Neutral Zone", 0

def check_multi_timeframe(pair: str) -> dict:
    """মাল্টি-টাইমফ্রেম ট্রেন্ড চেক"""
    timeframes = ["15m", "1h", "4h"]
    trends = {}
    scores = 0
    
    for tf in timeframes:
        df = fetch_data(pair, timeframe=tf, limit=30)
        if not df.empty and len(df) > 15:
            ema9 = ta.trend.ema_indicator(df["Close"], window=9)
            ema21 = ta.trend.ema_indicator(df["Close"], window=21)
            
            if ema9.iloc[-1] > ema21.iloc[-1]:
                trends[tf] = "Bullish"
                scores += 3  # ১৫মিনিটে ৩, ১ঘণ্টায় ৪, ৪ঘণ্টায় ৫
            elif ema9.iloc[-1] < ema21.iloc[-1]:
                trends[tf] = "Bearish"
                scores -= 3
    
    # টাইমফ্রেম অনুযায়ী ওয়েটেজ
    if "15m" in trends and trends["15m"] == "Bullish":
        scores += 2
    if "1h" in trends and trends["1h"] == "Bullish":
        scores += 4
    if "4h" in trends and trends["4h"] == "Bullish":
        scores += 5
        
    return trends, scores

def generate_signal(df: pd.DataFrame, pair: str = "", timeframe: str = "5m") -> dict:
    if df.empty or len(df) < 50:  # মিনিমাম ডাটা বাড়ানো
        return {
            "signal": "WAIT", "confidence": 0, "trend": "Unknown",
            "entry": "None", "reasons": ["Not enough live data"],
            "price": 0, "time": get_dhaka_time()
        }
    
    latest = df.iloc[-1]
    score = 50
    reasons = []
    
    # ========== 1. মাল্টি-টাইমফ্রেম ট্রেন্ড ==========
    mtf_trends, mtf_score = check_multi_timeframe(pair)
    score += mtf_score
    
    if mtf_trends:
        trend_str = " | ".join([f"{tf}:{t}" for tf, t in mtf_trends.items()])
        reasons.append(f"MTF Trend: {trend_str}")
    
    # ========== 2. ক্যান্ডেলস্টিক প্যাটার্ন ==========
    pattern, p_score = detect_candlestick_pattern(df)
    if pattern and p_score != 0:
        score += p_score
        reasons.append(f"Pattern: {pattern}")
    
    # ========== 3. সাপোর্ট/রেজিস্ট্যান্স ==========
    sr_zone, sr_score = check_support_resistance(df)
    if sr_score != 0:
        score += sr_score
        reasons.append(sr_zone)
    
    # ========== 4. Bollinger Bands (নতুন) ==========
    if "BB_Low" in df.columns and "BB_High" in df.columns:
        if latest["Close"] <= latest["BB_Low"] * 1.001:
            score += 12
            reasons.append("Price at BB Lower Band (Oversold)")
        elif latest["Close"] >= latest["BB_High"] * 0.999:
            score -= 12
            reasons.append("Price at BB Upper Band (Overbought)")
    
    # ========== 5. RSI (স্কোর কমানো) ==========
    rsi = latest.get("RSI", 50)
    if rsi < 30:  # থ্রেশহোল্ড কঠোর করা
        score += 10
        reasons.append(f"RSI Strong Oversold ({rsi:.1f})")
    elif rsi < 40:
        score += 5
        reasons.append(f"RSI Oversold ({rsi:.1f})")
    elif rsi > 70:
        score -= 10
        reasons.append(f"RSI Strong Overbought ({rsi:.1f})")
    elif rsi > 60:
        score -= 5
        reasons.append(f"RSI Overbought ({rsi:.1f})")
    
    # ========== 6. MACD (স্কোর কমানো) ==========
    macd = latest.get("MACD", 0)
    macd_signal = latest.get("MACD_Signal", 0)
    macd_hist = latest.get("MACD_Hist", 0)
    
    if macd > macd_signal and macd_hist > 0:
        score += 8
        reasons.append("MACD Bullish (Histogram +ve)")
    elif macd < macd_signal and macd_hist < 0:
        score -= 8
        reasons.append("MACD Bearish (Histogram -ve)")
    
    # ========== 7. EMA Alignment ==========
    if latest["EMA_9"] > latest["EMA_21"]:
        score += 6
        if "EMA_50" in df.columns and latest["EMA_9"] > latest["EMA_50"]:
            score += 3
            reasons.append("EMA Golden Cross (9>21>50)")
    elif latest["EMA_9"] < latest["EMA_21"]:
        score -= 6
        if "EMA_50" in df.columns and latest["EMA_9"] < latest["EMA_50"]:
            score -= 3
            reasons.append("EMA Death Cross (9<21<50)")
    
    # ========== 8. Volume Confirmation (নতুন) ==========
    if "Volume_Ratio" in df.columns:
        vol_ratio = df["Volume_Ratio"].iloc[-1]
        if vol_ratio > 1.5 and score > 55:
            score += 5
            reasons.append(f"High Volume ({vol_ratio:.1f}x)")
        elif vol_ratio > 1.5 and score < 45:
            score -= 5
            reasons.append(f"High Volume ({vol_ratio:.1f}x)")
    
    # ========== 9. ATR (ভোলাটিলিটি ফিল্টার) ==========
    if "ATR" in df.columns:
        atr = df["ATR"].iloc[-1]
        avg_atr = df["ATR"].rolling(20).mean().iloc[-1] if len(df) >= 20 else atr
        if atr > avg_atr * 1.5:
            reasons.append("High Volatility - Caution")
            score = score  # কোন পরিবর্তন না, শুধু সতর্কতা
    
    # স্কোর লিমিট
    score = max(0, min(100, int(score)))
    
    # ========== 10. সিগন্যাল থ্রেশহোল্ড অ্যাডজাস্ট ==========
    if score >= 60:  # ৫৮ → ৬০ করা
        signal = "CALL"
        entry = "UP (5m Candle Expiry)"
        confidence = int(score)
    elif score <= 40:  # ৪২ → ৪০ করা
        signal = "PUT"
        entry = "DOWN (5m Candle Expiry)"
        confidence = int(100 - score)
    else:
        signal = "WAIT"
        entry = "None"
        confidence = 50
    
    return {
        "signal": signal,
        "confidence": confidence,
        "trend": " | ".join(mtf_trends.values()) if mtf_trends else "Neutral",
        "entry": entry,
        "reasons": reasons[:6],
        "price": round(float(latest["Close"]), 5),
        "time": get_dhaka_time(),
        "score": score  # ডিবাগিংয়ের জন্য
    }
