import logging
from dotenv import load_dotenv
import os
import math
from datetime import datetime, timedelta
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

SYMBOL = ["SPY", "AAPL", "GOOG", "TSLA"]
START = datetime(2019, 1, 1)
END = datetime.now() - timedelta(days=1)

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
    logger.info("Starting day1 script")

    # Get Alpaca client and fetch historical data
    client = get_alpaca_client(StockHistoricalDataClient)
    df = get_historical_data(client, SYMBOL, START, END)

    # Process the data to compute simple returns and log returns
    close = df['close'].unstack(level=0).dropna()
    simple = close.pct_change().dropna()
    logr = np.log(close / close.shift(1)).dropna()

    # Total Return Calculations
    # from_prices: Total return from the first to the last price
    # compound_simple: Total return using compounded simple returns
    # SUM_simple(bad): Total return using the sum of simple returns (not accurate for compounding)
    # exp_sum_log: Total return using the exponential of the sum of log returns
    out = pd.DataFrame({
        "from_prices": close.iloc[-1] / close.iloc[0] - 1,
        "compound_simple": (1 + simple).prod() - 1,
        "SUM_simple(bad)": simple.sum(),
        "exp_sum_log": np.exp(logr.sum()) - 1
    })
    logger.info("Total return:\n%s\n", out.round(4))

    # Mean daily simple vs log; the gap is the difference between the two means, and var/2 is half the variance of simple returns
    gap = pd.DataFrame({
        "mean_simple": simple.mean(),
        "mean_log": logr.mean(),
        "gap": simple.mean() - logr.mean(),
        "var/2": simple.var() / 2,
    })
    logger.info("Daily means (x1e4 = basis points):\n%s\n", (gap * 1e4).round(3))

    # Find the day with the biggest gap between simple and log returns for each symbol
    d = (simple - logr)
    for t in close.columns:
        day = d[t].idxmax()
        logger.info(f"{t}: biggest gap on {day.date()}  "
                    f"simple={simple.loc[day, t]:+.4f}  log={logr.loc[day, t]:+.4f}  gap={d.loc[day, t]:+.4f}")

    # Monthly log returns match monthly returns from prices
    m_from_daily = logr.resample("ME").sum()
    m_px = close.resample("ME").last()
    m_from_prices = np.log(m_px / m_px.shift(1))
    logger.info("Monthly log returns match: %s", np.allclose(m_from_daily.iloc[1:], m_from_prices.iloc[1:]))

    quiz1_simple_return = 75/50 - 1
    quiz1_log_return = np.log(75/50)
    logger.info(f"Quiz 1: simple return={quiz1_simple_return:.4f}, log return={quiz1_log_return:.4f}")

    quiz2_log_returns = [0.02, -0.01, 0.03]
    quiz2_simple_return = math.exp(sum(quiz2_log_returns)) - 1
    logger.info(f"Quiz 2: simple return from log returns={quiz2_simple_return:.4f}")

    logger.info("Quiz 3: Log returns add across time, simple returns do not. For weighted average returns, use log returns for time aggregation and simple returns for weighting by capital allocation.")

    logger.info("End day1 script")