from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

from utils.data_fetcher import fetch_data, get_all_pairs_list
from utils.analysis import add_indicators, generate_signal

app = FastAPI(title="Pro Market Signal AI")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        pairs = get_all_pairs_list()
    except:
        pairs = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD"]
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pairs": pairs,
        "result": None,
        "selected_pair": "EURUSD",
        "selected_tf": "5m"
    })

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, pair: str = Form(...), timeframe: str = Form(...)):
    try:
        pairs = get_all_pairs_list()
    except:
        pairs = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD"]
    
    try:
        df = fetch_data(pair, timeframe)
        
        if df is None or df.empty:
            result = {
                "signal": "WAIT",
                "confidence": 0,
                "trend": "Data Error",
                "entry": "None",
                "reasons": ["Failed to fetch market data. Try another pair."],
                "price": 0,
                "time": "--:--:--",
            }
        else:
            df = add_indicators(df)
            result = generate_signal(df)
    except Exception as e:
        result = {
            "signal": "WAIT",
            "confidence": 0,
            "trend": "Error",
            "entry": "None",
            "reasons": [f"Analysis error: {str(e)[:80]}"],
            "price": 0,
            "time": "--:--:--",
        }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pairs": pairs,
        "result": result,
        "selected_pair": pair,
        "selected_tf": timeframe
    })
