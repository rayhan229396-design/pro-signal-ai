import pandas as pd
import yfinance as yf
import ccxt
import requests
from datetime import datetime
import pytz
import os

# ====================== API KEY ======================
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "YOUR_TWELVE_DATA_API_KEY_HERE")

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
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
    "BNBUSDT": "BNB/USDT",
    "XRPUSDT": "XRP/USDT",
    "ADAUSDT": "ADA/USDT",
    "DOGEUSDT": "DOGE/USDT",
    "AVAXUSDT": "AVAX/USDT",
    "DOTUSDT": "DOT/USDT",
    "LINKUSDT": "LINK/USDT",
    "MATICUSDT": "MATIC/USDT",
    "LTCUSDT": "LTC/USDT",
}

GOLD_PAIRS = {
    "XAUUSD": "XAU/USD",
    "GOLD": "XAU/USD",
}

ALL_PAIRS = {**FOREX_PAIRS, **CRYPTO_PAIRS, **GOLD_PAIRS}

def get_all_pairs_list():
    pairs = list(FOREX_PAIRS.keys()) + list(CRYPTO_PAIRS.keys()) + ["XAUUSD"]
    return sorted(set(pairs))


def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    symbol = symbol.upper().replace("/", "").replace("-", "")
    
    # Timeframe mapping
    tf_map = {
        "1m": "1min", "1min": "1min", "1 minute": "1min",
        "5m": "5min", "5min": "5min", "5 minute": "5min",
        "15m": "15min", "15min": "15min", "15 minute": "15min",
    }
    interval = tf_map.get(timeframe.lower(), "5min")
    
    # ===================== CRYPTO → Binance =====================
    if symbol in CRYPTO_PAIRS:
        try:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            binance_symbol = CRYPTO_PAIRS[symbol]
            
            # Binance timeframe format
            binance_tf = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m"
            }.get(interval, "5m")
            
            ohlcv = exchange.fetch_ohlcv(binance_symbol, timeframe=binance_tf, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            
            return df.dropna().tail(limit)
            
        except Exception as e:
            print(f"Binance error for {symbol}: {e}")
            return pd.DataFrame()
    
    # ===================== FOREX + GOLD → Twelve Data =====================
    else:
        try:
            # Convert symbol for Twelve Data
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
                print(f"Twelve Data error: {data}")
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
