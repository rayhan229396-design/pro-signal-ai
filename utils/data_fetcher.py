import pandas as pd
import requests
from datetime import datetime
import pytz
import os

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# তোমার চাহিদামতো সকল Assets Mapping
PAIRS_MAPPING = {
    # FOREX PAIRS
    "EURUSD": "EUR/USD",
    "AUDUSD": "AUD/USD",
    "USDJPY": "USD/JPY",
    "GBPUSD": "GBP/USD",
    "USDCAD": "USD/CAD",
    "USDCHF": "USD/CHF",
    "EURJPY": "EUR/JPY",
    "CADJPY": "CAD/JPY",
    "GBPJPY": "GBP/JPY",
    "GBPAUD": "GBP/AUD",
    "AUDJPY": "AUD/JPY",
    "CHFJPY": "CHF/JPY",
    "EURCHF": "EUR/CHF",
    "AUDCAD": "AUD/CAD",
    "EURCAD": "EUR/CAD",
    "EURAUD": "EUR/AUD",
    "EURGBP": "EUR/GBP",
    "GBPCHF": "GBP/CHF",
    "AUDCHF": "AUD/CHF",
    "GBPCAD": "GBP/CAD",
    
    # METALS / COMMODITIES
    "GOLD": "XAU/USD",
    "XAUUSD": "XAU/USD",
    
    # CRYPTO
    "BTCUSDT": "BTC/USD",
    "Ethereum": "ETH/USD",
    "ETHUSDT": "ETH/USD"
}

def get_all_pairs_list():
    # ইউজার ফ্রেন্ডলি সিলেক্ট লিস্ট (ডুপ্লিকেট রিমুভড)
    display_pairs = [
        "EURUSD", "AUDUSD", "USDJPY", "GBPUSD", "USDCAD", 
        "USDCHF", "EURJPY", "CADJPY", "GBPJPY", "GBPAUD", 
        "AUDJPY", "CHFJPY", "EURCHF", "AUDCAD", "EURCAD", 
        "EURAUD", "EURGBP", "GBPCHF", "AUDCHF", "GBPCAD", 
        "GOLD", "BTCUSDT", "Ethereum"
    ]
    return display_pairs

def get_dhaka_time():
    dhaka = pytz.timezone("Asia/Dhaka")
    return datetime.now(dhaka).strftime("%H:%M:%S")

def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    """
    কোনো ক্যাশিং ছাড়া সরাসরি লাইভ API থেকে রিয়েল-টাইম ক্যান্ডেলস্টিক ডাটা আনবে।
    """
    td_symbol = PAIRS_MAPPING.get(symbol, "EUR/USD")
    
    tf_map_td = {
        "1m": "1min", 
        "5m": "5min", 
        "15m": "15min"
    }
    interval = tf_map_td.get(timeframe, "5min")
    
    if not TWELVE_DATA_API_KEY:
        print("Warning: TWELVE_DATA_API_KEY is not set.")
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
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "values" not in data:
            print(f"Twelve Data Error ({symbol}): {data.get('message', 'No data')}")
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
        
        cols = ["Open", "High", "Low", "Close"]
        df = df[cols].astype(float)
        
        return df.sort_index().dropna()
        
    except Exception as e:
        print(f"Fetch Exception ({symbol}): {e}")
        return pd.DataFrame()
