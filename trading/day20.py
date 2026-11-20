import os
from datetime import datetime
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Day,
                       start=datetime(2015, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
px = client.get_stock_bars(req).df.xs("SPY", level="symbol")["close"]
r = px.pct_change().dropna()          # simple daily returns

# --- Part 1: full-sample Kelly (ignores risk-free rate & borrowing cost) ---
f_star = r.mean() / r.var()           # daily mean/var == annual mu/sigma^2
print(f"Full-sample Kelly leverage f* = {f_star:.2f}x\n")

# Realized log-growth for different leverage levels
print(" f     ann. log growth")
for f in np.round(np.linspace(0, 2.5 * f_star, 11), 2):
    x = 1 + f * r
    g = -np.inf if (x <= 0).any() else np.log(x).mean() * 252
    print(f"{f:5.2f}   {g:8.2%}")

# --- Part 2: how stable is f*?  Estimate it year by year ---
yearly = r.groupby(r.index.year).apply(lambda x: x.mean() / x.var())
print("\nKelly f* estimated per calendar year:")
print(yearly.round(2).to_string())

# --- Part 3: compare sizing rules ---
def stats(ret, name):
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = ret.std() * np.sqrt(252)
    sharpe = ret.mean() / ret.std() * np.sqrt(252)
    mdd = (eq / eq.cummax() - 1).min()
    print(f"{name:<16} CAGR {cagr:6.2%}  Vol {vol:6.2%}  "
          f"Sharpe {sharpe:5.2f}  MaxDD {mdd:7.2%}")

vol20 = r.rolling(20).std() * np.sqrt(252)
w_vt = (0.10 / vol20).clip(upper=2.0).shift(1)   # shift: no look-ahead!
strategies = {
    "Buy & hold 1x": r,
    "Half Kelly": (f_star / 2) * r,               # in-sample f*: cheating!
    "Vol target 10%": (w_vt * r),
}
print()
for name, ret in strategies.items():
    stats(ret.dropna(), name)
print(f"\nAvg vol-target weight: {w_vt.mean():.2f}, "
      f"realized vol of VT: {(w_vt*r).std()*np.sqrt(252):.2%}")