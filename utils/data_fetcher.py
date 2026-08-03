import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import pytz
import os
from cachetools import TTLCache

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# 1 মিনিট মেমোরি ক্যাশিং (API Limit বাঁচানোর জন্য)
data_cache = TTLCache(maxsize=100, ttl=60)

PAIRS_MAPPING = {
    "EURUSD": {"td": "EUR/USD", "yf": "EURUSD=X"},
    "GBPUSD": {"td": "GBP/USD", "yf": "GBPUSD=X"},
    "USDJPY": {"td": "USD/JPY", "yf": "JPY=X"},
    "AUDUSD": {"td": "AUD/USD", "yf": "AUDUSD=X"},
    "USDCAD": {"td": "USD/CAD", "yf": "CAD=X"},
    "USDCHF": {"td": "USD/CHF", "yf": "CHF=X"},
    "EURJPY": {"td": "EUR/JPY", "yf": "EURJPY=X"},
    "GBPJPY": {"td": "GBP/JPY", "yf": "GBPJPY=X"},
    "BTCUSDT": {"td": "BTC/USD", "yf": "BTC-USD"},
    "ETHUSDT": {"td": "ETH/USD", "yf": "ETH-USD"},
    "GOLD": {"td": "XAU/USD", "yf": "GC=F"},
    "XAUUSD": {"td": "XAU/USD", "yf": "GC=F"}
}

def get_all_pairs_list():
    return sorted(list(PAIRS_MAPPING.keys()))

def get_dhaka_time():
    dhaka = pytz.timezone("Asia/Dhaka")
    return datetime.now(dhaka).strftime("%H:%M:%S")

def fetch_from_twelvedata(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    if not TWELVE_DATA_API_KEY:
        return pd.DataFrame()
    
    td_symbol = PAIRS_MAPPING.get(symbol, {}).get("td", symbol)
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol,
        "interval": interval,
        "outputsize": limit,
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON"
    }
    
    try:
        response = requests.get(url, params=params, timeout=8)
        data = response.json()
        if "values" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "timestamp", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df = df[["Open", "High", "Low", "Close"]].astype(float)
        return df.sort_index().dropna()
    except Exception:
        return pd.DataFrame()

def fetch_from_yfinance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    yf_symbol = PAIRS_MAPPING.get(symbol, {}).get("yf", f"{symbol}=X")
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m"}
    interval = tf_map.get(timeframe, "5m")
    
    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="5d", interval=interval)
        if df.empty:
            return pd.DataFrame()
        
        df = df[["Open", "High", "Low", "Close"]].astype(float)
        df.index = df.index.tz_localize(None)
        return df.tail(limit)
    except Exception:
        return pd.DataFrame()

def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    symbol = symbol.upper().replace("/", "").replace("-", "")
    cache_key = f"{symbol}_{timeframe}_{limit}"
    
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    tf_map_td = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h"}
    interval_td = tf_map_td.get(timeframe, "5min")
    
    # 1. Primary: Twelve Data
    df = fetch_from_twelvedata(symbol, interval_td, limit)
    
    # 2. Fallback: Yahoo Finance
    if df.empty:
        df = fetch_from_yfinance(symbol, timeframe, limit)
        
    if not df.empty:
        data_cache[cache_key] = df
        
    return df
