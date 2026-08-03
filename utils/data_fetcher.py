import pandas as pd
import yfinance as yf
import ccxt
import requests
from datetime import datetime
import pytz
import os

# ====================== API KEY ======================
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# ---------------------- Pair Lists ----------------------
FOREX_PAIRS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "USDCHF": "USD/CHF",
    "NZDUSD": "NZD/USD",
    "EURGBP": "EUR/GBP",
    "EURJPY": "EUR/JPY",
    "GBPJPY": "GBP/JPY",
    "AUDJPY": "AUD/JPY",
    "EURAUD": "EUR/AUD",
    "EURCHF": "EUR/CHF",
    "GBPAUD": "GBP/AUD",
    "CADJPY": "CAD/JPY",
}

CRYPTO_PAIRS = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "SOLUSDT": "SOL-USD",
    "BNBUSDT": "BNB-USD",
    "XRPUSDT": "XRP-USD",
    "ADAUSDT": "ADA-USD",
    "DOGEUSDT": "DOGE-USD",
    "AVAXUSDT": "AVAX-USD",
    "DOTUSDT": "DOT-USD",
    "LINKUSDT": "LINK-USD",
    "MATICUSDT": "MATIC-USD",
    "LTCUSDT": "LTC-USD",
}

GOLD_PAIRS = {
    "XAUUSD": "XAU/USD",
    "GOLD": "XAU/USD",
}

def get_all_pairs_list():
    pairs = list(FOREX_PAIRS.keys()) + list(CRYPTO_PAIRS.keys()) + ["XAUUSD"]
    return sorted(set(pairs))


def fetch_from_yfinance(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    """Fallback using Yahoo Finance"""
    try:
        yf_symbol = CRYPTO_PAIRS.get(symbol, symbol + "=X")
        period = "7d" if interval in ["1m", "1min"] else "60d"
        
        df = yf.download(yf_symbol, period=period, interval=interval.replace("min", "m"), 
                         progress=False, auto_adjust=True)
        
        if df.empty:
            return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna().tail(limit)
        return df
    except Exception as e:
        print(f"Yahoo Finance error for {symbol}: {e}")
        return pd.DataFrame()


def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    symbol = symbol.upper().replace("/", "").replace("-", "")
    
    tf_map = {
        "1m": "1min", "1min": "1min", "1 minute": "1min",
        "5m": "5min", "5min": "5min", "5 minute": "5min",
        "15m": "15min", "15min": "15min", "15 minute": "15min",
    }
    interval = tf_map.get(timeframe.lower(), "5min")
    
    # ===================== CRYPTO → Yahoo Finance (Binance blocked) =====================
    if symbol in CRYPTO_PAIRS:
        return fetch_from_yfinance(symbol, interval, limit)
    
    # ===================== FOREX + GOLD → Twelve Data =====================
    try:
        if symbol in FOREX_PAIRS:
            td_symbol = FOREX_PAIRS[symbol]
        elif symbol in GOLD_PAIRS:
            td_symbol = GOLD_PAIRS[symbol]
        else:
            td_symbol = symbol
        
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
        
        # Rename columns safely
        rename_map = {
            "datetime": "timestamp",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
        df = df.rename(columns=rename_map)
        
        # Volume may not exist for Forex
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
