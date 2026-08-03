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
    pairs = get_all_pairs_list()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pairs": pairs,
        "result": None
    })

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, pair: str = Form(...), timeframe: str = Form(...)):
    pairs = get_all_pairs_list()
    
    df = fetch_data(pair, timeframe)
    
    if df.empty:
        result = {
            "signal": "WAIT",
            "confidence": 0,
            "trend": "Data Error",
            "entry": "None",
            "reasons": ["Failed to fetch market data. Try another pair or timeframe."],
            "price": 0,
            "time": "--:--:--",
            "error": True
        }
    else:
        df = add_indicators(df)
        result = generate_signal(df)
        result["error"] = False
        result["pair"] = pair
        result["timeframe"] = timeframe
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pairs": pairs,
        "result": result,
        "selected_pair": pair,
        "selected_tf": timeframe
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
