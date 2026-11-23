import os
from datetime import datetime
import numpy as np, pandas as pd
from scipy import stats
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

ANN, COST = 252, 0.0005          # 5 bps per one-way trade
SPLIT = "2022-01-01"             # out-of-sample starts here

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), adjustment=Adjustment.ALL)
px = client.get_stock_bars(req).df.loc["SPY", "close"]
px.index = px.index.tz_convert("America/New_York").date
px.index = pd.to_datetime(px.index)
ret = px.pct_change()

def backtest(n, cost=COST):
    # signal uses today's close, trade applies to TOMORROW's return (no lookahead)
    sig = (px > px.rolling(n).mean()).astype(float).shift(1)
    r = sig * ret - sig.diff().abs() * cost
    return r.iloc[n + 1:]

def sharpe(r):
    return r.mean() / r.std() * np.sqrt(ANN)

def metrics(r):
    eq = (1 + r).cumprod()
    mdd = (eq / eq.cummax() - 1).min()
    cagr = eq.iloc[-1] ** (ANN / len(r)) - 1
    down = np.sqrt((np.minimum(r, 0) ** 2).mean() * ANN)
    return pd.Series({"CAGR": cagr, "Vol": r.std() * np.sqrt(ANN),
                      "Sharpe": sharpe(r), "Sortino": r.mean() * ANN / down,
                      "MaxDD": mdd, "Calmar": cagr / abs(mdd)})

strat = backtest(200)
bh = ret.loc[strat.index]

# 1) Headline metrics, in-sample vs out-of-sample
tbl = pd.DataFrame({
    "Strat IS": metrics(strat[:SPLIT]), "B&H IS": metrics(bh[:SPLIT]),
    "Strat OOS": metrics(strat[SPLIT:]), "B&H OOS": metrics(bh[SPLIT:])})
print(tbl.round(3), "\n")

# 2) Is the active return (strat - B&H) different from zero?
active = strat - bh
t, p = stats.ttest_1samp(active, 0)
print(f"Active return: ann mean {active.mean()*ANN:.2%}, t={t:.2f}, p={p:.3f}")

# 3) Paired block bootstrap of the Sharpe difference (keeps autocorrelation)
rng = np.random.default_rng(42)
s, b = strat.values, bh.values
n, block, B = len(s), 20, 2000
starts = rng.integers(0, n, size=(B, -(-n // block)))
idx = ((starts[:, :, None] + np.arange(block)).reshape(B, -1)[:, :n]) % n
sh = lambda x: x.mean(1) / x.std(1) * np.sqrt(ANN)
diff = sh(s[idx]) - sh(b[idx])
lo, hi = np.percentile(diff, [2.5, 97.5])
print(f"Sharpe diff {sharpe(strat)-sharpe(bh):.2f}, 95% CI [{lo:.2f}, {hi:.2f}]")

# 4) Parameter robustness: is 200 a lucky pick or part of a plateau?
grid = {w: sharpe(backtest(w)) for w in [50, 100, 150, 200, 250]}
print("Sharpe by SMA window:", {k: round(float(v), 2) for k, v in grid.items()})

# 5) Luck hurdle: expected best Sharpe from N zero-skill trials
N, years = len(grid), len(strat) / ANN
g = 0.5772
emax = (1 - g) * stats.norm.ppf(1 - 1 / N) + g * stats.norm.ppf(1 - 1 / (N * np.e))
print(f"Luck hurdle for best of {N}: Sharpe ~ {emax/np.sqrt(years):.2f}")

# 6) Cost stress test
print(f"Sharpe @5bps {sharpe(strat):.2f} | @20bps {sharpe(backtest(200, 0.002)):.2f}")
sig = (px > px.rolling(200).mean()).astype(float).shift(1).loc[strat.index]
print(f"Trades per year: {sig.diff().abs().sum() / years:.1f}")