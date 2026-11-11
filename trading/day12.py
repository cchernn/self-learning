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
close = client.get_stock_bars(req).df.xs("SPY", level="symbol")["close"]

# --- Strategy: long when close > SMA200, decided yesterday (no look-ahead)
ret = np.log(close).diff()
sma = close.rolling(200).mean()
pos = (close > sma).astype(float).where(sma.notna()).shift(1)
df = pd.DataFrame({"ret": ret, "pos": pos}).dropna()
r, p = df["ret"].to_numpy(), df["pos"].to_numpy()
s = p * r                      # strategy daily log returns (cash = 0)
n = len(s)

def sharpe(x, axis=None):      # annualized, rf ignored for simplicity
    return np.sqrt(252) * x.mean(axis=axis) / x.std(axis=axis, ddof=1)

def block_idx(n, B, L, rng):   # circular block bootstrap indices
    nb = int(np.ceil(n / L))
    starts = rng.integers(0, n, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(L)) % n
    return idx.reshape(B, -1)[:, :n]

rng, B = np.random.default_rng(42), 2000

# (a) Bootstrap CI for the strategy Sharpe
iid = sharpe(s[rng.integers(0, n, size=(B, n))], axis=1)
blk = sharpe(s[block_idx(n, B, 20, rng)], axis=1)
print(f"Days: {n}, time in market: {p.mean():.0%}")
print(f"Strategy Sharpe: {sharpe(s):.2f} | Buy&hold Sharpe: {sharpe(r):.2f}")
print("95% CI iid  :", np.percentile(iid, [2.5, 97.5]).round(2))
print("95% CI block:", np.percentile(blk, [2.5, 97.5]).round(2))

# (b) Does it beat buy-and-hold? Bootstrap the daily difference
d = s - r
dm = 252 * d[block_idx(n, B, 20, rng)].mean(axis=1)
print(f"\nAnn. excess vs B&H: {252*d.mean():.2%}, "
      f"95% CI {np.percentile(dm, [2.5, 97.5]).round(3)}, "
      f"share of boots <= 0: {(dm <= 0).mean():.0%}")

# (c) Permutation tests: is the TIMING better than random?
obs = s.mean()
shuf = np.array([(rng.permutation(p) * r).mean() for _ in range(B)])
shifts = rng.integers(252, n - 252, size=B)
circ = np.array([(np.roll(p, k) * r).mean() for k in shifts])
pval = lambda null: (1 + (null >= obs).sum()) / (B + 1)
print(f"\nPermutation p (shuffle):        {pval(shuf):.3f}")
print(f"Permutation p (circular shift): {pval(circ):.3f}")