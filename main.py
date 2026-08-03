from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from utils.data_fetcher import fetch_data, get_all_pairs_list
from utils.analysis import add_indicators, generate_signal

app = FastAPI(title="Real Market Signal AI")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    pairs = get_all_pairs_list()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "pairs": pairs,
            "result": None,
            "selected_pair": "EURUSD",
            "selected_tf": "5m"
        }
    )

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, pair: str = Form(...), timeframe: str = Form(...)):
    pairs = get_all_pairs_list()
    try:
        df = fetch_data(pair, timeframe)
        if df is None or df.empty:
            result = {
                "signal": "WAIT",
                "confidence": 0,
                "trend": "No Data",
                "entry": "None",
                "reasons": ["Unable to fetch live market data."],
                "price": 0,
                "time": "--:--:--"
            }
        else:
            df = add_indicators(df)
            result = generate_signal(df, pair=pair, timeframe=timeframe)
    except Exception as e:
        result = {
            "signal": "WAIT",
            "confidence": 0,
            "trend": "Error",
            "entry": "None",
            "reasons": [f"Processing error: {str(e)[:60]}"],
            "price": 0,
            "time": "--:--:--"
        }
        
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "pairs": pairs,
            "result": result,
            "selected_pair": pair,
            "selected_tf": timeframe
        }
    )
