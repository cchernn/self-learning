import os
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.stats import norm
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "QQQ", "AAPL", "TLT"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
close = client.get_stock_bars(req).df["close"].unstack(level=0)
rets = close.pct_change().dropna()          # simple returns (P&L-style)

def var_es(r, alpha):
    q = r.quantile(alpha)
    h_var = -q                               # historical VaR
    h_es = -r[r <= q].mean()                 # historical ES
    mu, sd = r.mean(), r.std()
    z = norm.ppf(alpha)                      # negative number
    p_var = -(mu + z * sd)                   # parametric VaR
    p_es = -mu + sd * norm.pdf(z) / alpha    # parametric ES
    return h_var, h_es, p_var, p_es

rows = []
for t in tickers:
    for a in (0.05, 0.01):
        rows.append([t, f"{int((1-a)*100)}%", *var_es(rets[t], a)])
tbl = pd.DataFrame(rows, columns=["ticker", "conf", "hist_VaR",
                                  "hist_ES", "norm_VaR", "norm_ES"])
print((tbl.set_index(["ticker", "conf"]) * 100).round(2), "\n")

# Dollar terms on a $100k SPY position
h_var, h_es, _, _ = var_es(rets["SPY"], 0.01)
print(f"SPY $100k: 99% 1-day VaR ${h_var*1e5:,.0f}, ES ${h_es*1e5:,.0f}\n")

# --- Backtest: rolling 1-year 99% VaR, used for the NEXT day ---
spy = rets["SPY"]
w = 252
roll_hist = -spy.rolling(w).quantile(0.01).shift(1)
roll_norm = -(spy.rolling(w).mean()
              + norm.ppf(0.01) * spy.rolling(w).std()).shift(1)
ok = roll_hist.notna()
for name, v in [("historical", roll_hist), ("normal", roll_norm)]:
    breach = spy[ok] < -v[ok]
    print(f"{name:>10}: {breach.sum()} breaches in {ok.sum()} days "
          f"= {breach.mean():.2%} (expected 1.00%)")
    print("   by year:", breach.groupby(breach.index.year).sum().to_dict())