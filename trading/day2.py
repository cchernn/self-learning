import logging
from dotenv import load_dotenv
import os
from datetime import datetime
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

SYMBOL = ["SPY", "AAPL", "QQQ", "TSLA"]
START = datetime(2018, 1, 1)
END = datetime(2025, 12, 31)

def get_alpaca_client(client):
    """
        Get an instance of the Alpaca client with API credentials from environment variables.
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        logger.error("ALPACA_API_KEY and ALPACA_SECRET_KEY not set in .env")
        raise ValueError("Missing Alpaca API credentials")
    return client(api_key=api_key, secret_key=secret_key)

def get_historical_data(client, symbol, start_date, end_date, timeframe=TimeFrame.Day, adjustment=Adjustment.ALL):
    """
        Fetch historical stock data for the given symbol(s) and date range.
    """
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        start=start_date,
        end=end_date,
        timeframe=timeframe,
        adjustment=adjustment
    )
    bars = client.get_stock_bars(request_params)
    return bars.df

if __name__ == "__main__":
    logger.info("Starting day2 script")

    # Get Alpaca client and fetch historical data
    client = get_alpaca_client(StockHistoricalDataClient)
    df = get_historical_data(client, SYMBOL, START, END)

    close = df['close'].unstack(level=0).dropna()
    close.index = pd.to_datetime(close.index).date

    r = close.pct_change().dropna() #daily simple returns
    years = len(r) / 252

    rows = {}
    for t in SYMBOL:
        rt = r[t]
        arith_ann = rt.mean() * 252                                      # naive annualized mean
        cagr = (close[t].iloc[-1] / close[t].iloc[0]) ** (1/years) - 1   # CAGR
        geo_daily = np.exp(np.log1p(rt).mean()) - 1                      # geometric daily mean
        geo_ann = (1 + geo_daily) ** 252 - 1                             # should ≈ CAGR
        vol_ann = rt.std() * np.sqrt(252)                                # annualized volatility
        approx = arith_ann - vol_ann**2 / 2                              # drag approximation
        rows[t] = dict(
            arith=arith_ann,
            geo=geo_ann,
            CAGR=cagr,
            vol=vol_ann,
            drag=arith_ann - cagr,
            approx_geo=approx
        )
    out = pd.DataFrame(rows).T
    logger.info(f"Years: {years:.2f}")
    logger.info((out * 100).round(2).to_string())

    logger.info("End day2 script")