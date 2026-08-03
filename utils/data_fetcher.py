import pandas as pd
import yfinance as yf
import ccxt
from datetime import datetime
import pytz

# ---------------------- Pair Lists ----------------------
FOREX_PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "AUDJPY": "AUDJPY=X",
    "EURAUD": "EURAUD=X",
    "EURCHF": "EURCHF=X",
    "GBPAUD": "GBPAUD=X",
    "CADJPY": "CADJPY=X",
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
    "XAUUSD": "GC=F",
    "GOLD": "GC=F",
}

ALL_PAIRS = {**FOREX_PAIRS, **CRYPTO_PAIRS, **GOLD_PAIRS}

def get_all_pairs_list():
    pairs = list(FOREX_PAIRS.keys()) + list(CRYPTO_PAIRS.keys()) + ["XAUUSD"]
    return sorted(set(pairs))


def fetch_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    symbol = symbol.upper().replace("/", "").replace("-", "")
    
    tf_map = {
        "1m": "1m", "1min": "1m", "1 minute": "1m",
        "5m": "5m", "5min": "5m", "5 minute": "5m",
        "15m": "15m", "15min": "15m", "15 minute": "15m",
    }
    interval = tf_map.get(timeframe.lower(), "5m")
    
    yahoo_symbol = ALL_PAIRS.get(symbol)
    
    if not yahoo_symbol:
        if symbol.endswith("USDT"):
            yahoo_symbol = symbol.replace("USDT", "-USD")
        else:
            yahoo_symbol = symbol + "=X"
    
    try:
        period = "7d" if interval == "1m" else "60d"
        
        df = yf.download(yahoo_symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        
        if df.empty:
            return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df = df.dropna().tail(limit)
        
        return df
        
    except Exception as e:
        print(f"Data fetch error for {symbol}: {e}")
        return pd.DataFrame()


def get_dhaka_time():
    dhaka = pytz.timezone("Asia/Dhaka")
    now = datetime.now(dhaka)
    return now.strftime("%H:%M:%S")
