# Day 16: Stationarity and the ADF test (prices vs returns)
import os, warnings
from datetime import datetime
import numpy as np, pandas as pd
from scipy.signal import lfilter
from statsmodels.tsa.stattools import adfuller, kpss
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

warnings.filterwarnings("ignore")  # silence KPSS p-value-bound + statsmodels FutureWarnings

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "QQQ", "AAPL", "GLD", "TLT"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2026, 11, 1),
                       adjustment=Adjustment.ALL)
close = client.get_stock_bars(req).df["close"].unstack(level=0).dropna()

def tests(x, trend):
    x = x.dropna()
    adf_stat, adf_p, lags, *_ = adfuller(x, regression=trend, autolag="AIC")
    kpss_stat, kpss_p, *_ = kpss(x, regression=trend, nlags="auto")
    return adf_stat, adf_p, lags, kpss_p

rows = []
for t in tickers:
    logp = np.log(close[t])
    ret = logp.diff()
    # prices drift upward -> include a trend ("ct"); returns -> constant only ("c")
    for name, series, trend in [("log price", logp, "ct"), ("log return", ret, "c")]:
        s, p, lags, kp = tests(series, trend)
        rows.append([t, name, round(s, 2), round(p, 4), lags, round(kp, 3)])

out = pd.DataFrame(rows, columns=["ticker", "series", "ADF stat", "ADF p", "lags", "KPSS p"])
print(out.to_string(index=False))
print("\nADF: H0 = unit root (non-stationary). Small p -> stationary.")
print("KPSS: H0 = stationary. Small p -> NON-stationary. (p is capped at 0.01/0.10)")

# --- Power check: how often does ADF detect a stationary AR(1) that is *close* to a random walk?
rng = np.random.default_rng(42)
n, sims = len(close), 200
print(f"\nSimulated AR(1), n={n}: share of runs where ADF rejects at 5%")
for phi in [1.0, 0.995, 0.99, 0.95]:
    rej = 0
    for _ in range(sims):
        x = lfilter([1.0], [1.0, -phi], rng.standard_normal(n))  # x_t = phi*x_{t-1} + e_t
        rej += adfuller(x, maxlag=1, autolag=None)[1] < 0.05
    print(f"  phi={phi:<6} rejection rate = {rej/sims:.0%}")