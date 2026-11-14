import os
from datetime import datetime
import numpy as np, pandas as pd
from scipy import stats
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2026, 11, 12),
                       adjustment=Adjustment.ALL)   # split+dividend adjusted
px = client.get_stock_bars(req).df.xs("SPY")["close"]
r = np.log(px).diff().dropna()          # daily log returns

def sharpe(x, axis=None):
    # annualized Sharpe (rf ~ 0); works on Series, 1-D or 2-D arrays
    return np.mean(x, axis=axis) / np.std(x, axis=axis, ddof=1) * np.sqrt(252)

def position(fast, slow):
    # 1 = long, 0 = flat. shift(1): trade the signal NEXT day (no lookahead)
    f, s = px.rolling(fast).mean(), px.rolling(slow).mean()
    return (f > s).astype(float).shift(1)

MAX_SLOW = 250
idx = r.index[MAX_SLOW + 1:]   # same dates for every variant (all MAs warmed up)
R = r.loc[idx]

# ---------- 1) Headline strategy: 50/200 golden cross ----------
pos = position(50, 200).loc[idx]
strat = pos * R                 # flat days earn 0
excess = strat - R              # vs buy-and-hold
print(f"Days: {len(R)} | in market: {pos.mean():.0%} | trades: {int(pos.diff().abs().sum())}")
print(f"Sharpe  strategy: {sharpe(strat):.2f}   buy&hold: {sharpe(R):.2f}")
print(f"Total log ret  strategy: {strat.sum():.2f}   buy&hold: {R.sum():.2f}")

# ---------- 2) t-tests (Day 11) ----------
t1, p1 = stats.ttest_1samp(strat, 0)
t2, p2 = stats.ttest_1samp(excess, 0)
print(f"\nt-test mean>0:     t={t1:.2f}  p={p1:.3f}")
print(f"t-test beats B&H:  t={t2:.2f}  p={p2:.3f}")

# ---------- 3) Bootstrap CI for Sharpe (Day 12) ----------
rng = np.random.default_rng(42)
x = strat.values
boot = np.array([sharpe(rng.choice(x, len(x))) for _ in range(5000)])
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\nBootstrap 95% CI for Sharpe: [{lo:.2f}, {hi:.2f}]")

# ---------- 4) Random-luck test: circular shifts ----------
n, B = len(R), 2000
shifts = rng.integers(60, n - 60, B)
Rv, Pv = R.values, pos.values
luck = np.array([sharpe(np.roll(Pv, k) * Rv) for k in shifts])
p_luck = (np.sum(luck >= sharpe(strat)) + 1) / (B + 1)
print(f"Random-timing Sharpe: median {np.median(luck):.2f}, "
      f"95th pct {np.percentile(luck, 95):.2f}")
print(f"Random-luck p-value (50/200): {p_luck:.3f}")

# ---------- 5) Data snooping (Day 13): try a grid, pick the best ----------
grid = [(f, s) for f in (10, 20, 50, 100)
        for s in (50, 100, 150, 200, 250) if f < s]
P = np.vstack([position(f, s).loc[idx].values for f, s in grid])  # combos x days
sr = sharpe(P * Rv, axis=1)
best = int(np.argmax(sr))
print(f"\nTried {len(grid)} combos. Best: {grid[best]} Sharpe {sr[best]:.2f}")

# naive p (pretend it was the only one tried) vs honest max-of-grid p
naive_luck = np.array([sharpe(np.roll(P[best], k) * Rv) for k in shifts])
naive = (np.sum(naive_luck >= sr[best]) + 1) / (B + 1)
max_luck = np.array([sharpe(np.roll(P, k, axis=1) * Rv, axis=1).max()
                     for k in shifts])
honest = (np.sum(max_luck >= sr[best]) + 1) / (B + 1)
print(f"Best combo p  naive: {naive:.3f} | Bonferroni: "
      f"{min(1, naive*len(grid)):.3f} | max-of-grid: {honest:.3f}")