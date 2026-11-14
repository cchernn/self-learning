import os
from datetime import datetime
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "QQQ", "AAPL"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
df = client.get_stock_bars(req).df          # MultiIndex (symbol, timestamp)
close = df["close"].unstack(level=0).dropna()
rets = np.log(close).diff().dropna()        # daily log returns

LAGS = 10
for t in tickers:
    r = rets[t].values
    T = len(r)
    band = 1.96 / np.sqrt(T)                # 95% band under "no autocorrelation"
    a = acf(r, nlags=LAGS, fft=True)
    p = pacf(r, nlags=LAGS)
    a_abs = acf(np.abs(r), nlags=LAGS, fft=True)   # volatility clustering check
    print(f"\n=== {t}  (T={T}, 95% band = ±{band:.3f}) ===")
    tab = pd.DataFrame({"ACF r": a[1:], "PACF r": p[1:], "ACF |r|": a_abs[1:]},
                       index=range(1, LAGS + 1)).round(3)
    tab["r sig?"] = np.where(np.abs(tab["ACF r"]) > band, "*", "")
    print(tab.to_string())
    lb = acorr_ljungbox(r, lags=[5, 10], return_df=True)
    lb_abs = acorr_ljungbox(np.abs(r), lags=[10], return_df=True)
    print("Ljung-Box p (returns, lag 5/10):", lb["lb_pvalue"].round(4).tolist())
    print("Ljung-Box p (|returns|, lag 10):", f"{lb_abs['lb_pvalue'].iloc[0]:.2e}")

# Benchmark: a true random walk with the same volatility as SPY
rng = np.random.default_rng(0)
fake = rng.normal(0, rets["SPY"].std(), len(rets))
print("\nSimulated RW lag-1..5 ACF:", acf(fake, nlags=5, fft=True)[1:].round(3))
print("Simulated RW |r| lag-1..5 ACF:", acf(np.abs(fake), nlags=5, fft=True)[1:].round(3))

# Does the lag-1 effect come from crash periods? Compare with/without 2020.
spy = rets["SPY"]
ex2020 = spy[spy.index.year != 2020]
print("\nSPY lag-1 ACF, all years:", round(spy.autocorr(1), 3),
      "| excluding 2020:", round(ex2020.autocorr(1), 3))