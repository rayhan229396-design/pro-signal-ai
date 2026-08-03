import pandas as pd
import requests
from datetime import datetime
import pytz
import os

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

PAIRS_MAPPING = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "USDCHF": "USD/CHF",
    "EURJPY": "EUR/JPY",
    "GBPJPY": "GBP/JPY",
    "BTCUSDT": "BTC/USD",
    "ETHUSDT": "ETH/USD",
    "GOLD": "XAU/USD",
    "XAUUSD": "XAU/USD"
}

def get_all_pairs_list():
    return sorted(list(PAIRS_MAPPING.keys()))

def get_dhaka_time():
    dhaka = pytz.timezone("Asia/Dhaka")
    return datetime.now(dhaka).strftime("%H:%M:%S")

def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    """
    ক্যাশিং ছাড়া সরাসরি লাইভ রিয়েল-টাইম ডাটা ফেচ করবে।
    """
    symbol = symbol.upper().replace("/", "").replace("-", "")
    td_symbol = PAIRS_MAPPING.get(symbol, f"{symbol[:3]}/{symbol[3:]}")
    
    tf_map_td = {
        "1m": "1min", 
        "5m": "5min", 
        "15m": "15min", 
        "1h": "1h"
    }
    interval = tf_map_td.get(timeframe, "5min")
    
    if not TWELVE_DATA_API_KEY:
        print("Error: TWELVE_DATA_API_KEY is missing.")
        return pd.DataFrame()

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol,
        "interval": interval,
        "outputsize": limit,
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON"
    }
    
    try:
        # নো ক্যাশ - সরাসরি লাইভ রিকোয়েস্ট পাঠানো হচ্ছে
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "values" not in data:
            print(f"Twelve Data Error for {symbol}: {data.get('message', 'No values')}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={
            "datetime": "timestamp", 
            "open": "Open", 
            "high": "High", 
            "low": "Low", 
            "close": "Close", 
            "volume": "Volume"
        })
        
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        
        # প্রয়োজনীয় কলাম ফিল্টার ও টাইপ কাস্টিং
        cols = ["Open", "High", "Low", "Close"]
        df = df[cols].astype(float)
        
        return df.sort_index().dropna()
        
    except Exception as e:
        print(f"Data Fetching Exception: {e}")
        return pd.DataFrame()
