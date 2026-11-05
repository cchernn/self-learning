import os
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])

tickers = ["SPY", "QQQ", "AAPL", "TLT"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)   # split/dividend adjusted
bars = client.get_stock_bars(req).df
close = bars["close"].unstack(level=0)              # rows=dates, cols=tickers

daily = np.log(close).diff().dropna()
# Month-end closes ("ME" needs pandas>=2.2; use "M" on older pandas)
monthly = np.log(close.resample("ME").last()).diff().dropna()

def shape(r):
    z_worst = (r.min() - r.mean()) / r.std()
    return pd.Series({
        "mean%":   r.mean() * 100,
        "median%": r.median() * 100,
        "std%":    r.std() * 100,
        "skew":    stats.skew(r),
        "ex_kurt": stats.kurtosis(r),          # excess kurtosis (normal = 0)
        "worst_z": z_worst,                    # worst day in sigmas
        "P_normal(worst)": stats.norm.cdf(z_worst),
    })

pd.set_option("display.float_format", lambda x: f"{x:.4g}")
print("DAILY log returns\n", daily.apply(shape).T, "\n")
print("MONTHLY log returns\n", monthly.apply(shape).T, "\n")

# What does a truly normal sample of the same length look like?
n = len(daily)
sim = np.random.default_rng(0).normal(size=(n, 2000))
sk, ku = stats.skew(sim, axis=0), stats.kurtosis(sim, axis=0)
print(f"Normal samples of n={n}: 95% of skew in "
      f"[{np.percentile(sk, 2.5):.2f}, {np.percentile(sk, 97.5):.2f}], "
      f"ex_kurt in [{np.percentile(ku, 2.5):.2f}, {np.percentile(ku, 97.5):.2f}]")