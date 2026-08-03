import pandas as pd
import requests
from datetime import datetime
import pytz
import os

# ====================== API KEY ======================
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# ---------------------- Only Selected Pairs ----------------------
FOREX_PAIRS = {
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
}

CRYPTO_PAIRS = {
    "BTCUSDT": "BTC/USD",
    "ETHUSDT": "ETH/USD",   # Ethereum
}

GOLD_PAIRS = {
    "GOLD": "XAU/USD",
    "XAUUSD": "XAU/USD",
}

def get_all_pairs_list():
    pairs = list(FOREX_PAIRS.keys()) + list(CRYPTO_PAIRS.keys()) + ["GOLD"]
    return sorted(set(pairs))


def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    symbol = symbol.upper().replace("/", "").replace("-", "")
    
    # Timeframe mapping for Twelve Data
    tf_map = {
        "1m": "1min", "1min": "1min", "1 minute": "1min",
        "5m": "5min", "5min": "5min", "5 minute": "5min",
        "15m": "15min", "15min": "15min", "15 minute": "15min",
    }
    interval = tf_map.get(timeframe.lower(), "5min")
    
    # Determine Twelve Data symbol
    if symbol in FOREX_PAIRS:
        td_symbol = FOREX_PAIRS[symbol]
    elif symbol in CRYPTO_PAIRS:
        td_symbol = CRYPTO_PAIRS[symbol]
    elif symbol in GOLD_PAIRS:
        td_symbol = GOLD_PAIRS[symbol]
    else:
        print(f"Unsupported symbol: {symbol}")
        return pd.DataFrame()
    
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": td_symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": TWELVE_DATA_API_KEY,
            "format": "JSON"
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if "values" not in data:
            print(f"Twelve Data error for {symbol}: {data}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data["values"])
        
        # Rename columns
        rename_map = {
            "datetime": "timestamp",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
        df = df.rename(columns=rename_map)
        
        # Volume may not always be present
        if "volume" in df.columns:
            df = df.rename(columns={"volume": "Volume"})
        else:
            df["Volume"] = 0
        
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        
        df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
        df = df.sort_index()
        
        return df.dropna().tail(limit)
        
    except Exception as e:
        print(f"Twelve Data error for {symbol}: {e}")
        return pd.DataFrame()


def get_dhaka_time():
    dhaka = pytz.timezone("Asia/Dhaka")
    now = datetime.now(dhaka)
    return now.strftime("%H:%M:%S")
