import logging
from dotenv import load_dotenv
import os
from datetime import datetime
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment, DataFeed

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

SYMBOL = ["SPY", "AAPL", "QQQ", "TLT"]
START = datetime(2018, 1, 1)
END = datetime(2026, 10, 30)

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
        adjustment=adjustment,
        feed=DataFeed.IEX           # free-tier feed
    )
    bars = client.get_stock_bars(request_params)
    return bars.df

if __name__ == "__main__":
    logger.info("Starting day3 script")

    # Get Alpaca client and fetch historical data
    client = get_alpaca_client(StockHistoricalDataClient)
    df = get_historical_data(client, SYMBOL, START, END)

    close = df['close'].unstack(level=0).dropna()
    close.index = pd.to_datetime(close.index).date

    logp = np.log(close)
    r = logp.diff().dropna() # daily log returns

    # --- 1. Daily and annualized vol ---
    daily = r.std()                        # ddof=1
    annual = daily * np.sqrt(252)
    logger.info("Daily vol (%%):\n%s", (daily * 100).round(2))
    logger.info("\nAnnualized vol (%%):\n%s", (annual * 100).round(1))

    # --- 2. Test the sqrt-of-time rule ---
    # Use NON-overlapping n-day returns and compare their
    # real std with daily_std * sqrt(n). Ratio ~1 => rule holds.
    logger.info("\nRatio actual / sqrt-rule  (n = 5, 21, 63):")
    for n in [5, 21, 63]:
        rn = logp.iloc[::n].diff().dropna()   # every n-th day
        ratio = rn.std() / (daily * np.sqrt(n))
        logger.info(f"n={n:>2}: {ratio.round(2).to_dict()}")

    # --- 3. Rolling and EWMA vol for SPY ---
    spy = r["SPY"]
    roll21 = spy.rolling(21).std() * np.sqrt(252)
    roll252 = spy.rolling(252).std() * np.sqrt(252)
    ewma = np.sqrt((spy**2).ewm(alpha=1 - 0.94).mean() * 252)

    logger.info(f"\nSPY 21d vol: max {roll21.max():.1%} on {roll21.idxmax()}, "
        f"min {roll21.min():.1%} on {roll21.idxmin()}")
    logger.info(f"Latest  21d: {roll21.iloc[-1]:.1%} | 252d: {roll252.iloc[-1]:.1%} "
        f"| EWMA: {ewma.iloc[-1]:.1%}")

    # --- 4. Vol clustering: is high vol followed by high vol? ---
    # Correlate this month's 21d vol with next month's.
    nxt = roll21.shift(-21)
    logger.info(f"Corr(vol today, vol in 21d): {roll21.corr(nxt):.2f}")

    logger.info("End day3 script")