import os
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "QQQ", "AAPL"]
req = StockBarsRequest(
    symbol_or_symbols=tickers,
    timeframe=TimeFrame.Day,
    start=datetime(2016, 1, 1),
    end=datetime(2026, 10, 30),
    adjustment=Adjustment.ALL,          # split/dividend adjusted
)
closes = client.get_stock_bars(req).df["close"].unstack(level=0)
rets = np.log(closes).diff().dropna()   # daily log returns

rows = []
for t in tickers:
    r = rets[t]
    n = len(r)
    z = (r - r.mean()) / r.std()        # standardize with full-sample sigma
    p3 = 2 * stats.norm.sf(3)           # P(|Z|>3) under normal = 0.27%
    p4 = 2 * stats.norm.sf(4)
    jb = stats.jarque_bera(r)
    rows.append({
        "ticker": t, "n": n,
        "skew": stats.skew(r),
        "excess_kurt": stats.kurtosis(r),          # normal = 0
        ">3sd actual": int((z.abs() > 3).sum()),
        ">3sd expected": round(n * p3, 1),
        ">4sd actual": int((z.abs() > 4).sum()),
        ">4sd expected": round(n * p4, 2),
        "JB stat": round(jb.statistic, 1),
        "JB p": jb.pvalue,
        "worst day z": round(z.min(), 1),
    })
print(pd.DataFrame(rows).set_index("ticker").T)

# Fit a Student-t: low degrees of freedom (df) = fat tails (normal is df=inf)
df_t, loc, scale = stats.t.fit(rets["SPY"])
print(f"\nSPY Student-t fit: df = {df_t:.1f}")

# QQ plots: normal vs fitted t
fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))
stats.probplot(rets["SPY"], dist="norm", plot=ax[0])
ax[0].set_title("SPY vs Normal")
stats.probplot(rets["SPY"], dist=stats.t, sparams=(df_t,), plot=ax[1])
ax[1].set_title(f"SPY vs Student-t (df={df_t:.1f})")
plt.tight_layout()
plt.savefig("day7_qq.png", dpi=120)
print("Saved day7_qq.png")