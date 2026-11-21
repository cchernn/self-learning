import os
from datetime import datetime
import numpy as np, pandas as pd
from scipy.optimize import minimize
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "EFA", "IWM", "TLT", "GLD"]  # US, intl, small cap, bonds, gold
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
px = client.get_stock_bars(req).df["close"].unstack(level=0)[tickers].dropna()
r = px.pct_change().dropna()          # simple returns for portfolio math

def optimize(mu, cov, kind):
    n = len(mu)
    def neg_sharpe(w): return -(w @ mu) / np.sqrt(w @ cov @ w)
    def var(w): return w @ cov @ w
    res = minimize(var if kind == "minvar" else neg_sharpe, np.ones(n) / n,
                   bounds=[(0, 1)] * n,                       # long-only
                   constraints={"type": "eq", "fun": lambda w: w.sum() - 1})
    return res.x

def ann(rets):                         # annualized mean vector & covariance
    return rets.mean().values * 252, rets.cov().values * 252

# --- 1. Diversification benefit ---
mu, cov = ann(r)
ew = np.ones(len(tickers)) / len(tickers)
print("Individual vols:", dict(zip(tickers, np.sqrt(np.diag(cov)).round(3))))
print(f"Avg individual vol: {np.sqrt(np.diag(cov)).mean():.3f}")
print(f"Equal-weight portfolio vol: {np.sqrt(ew @ cov @ ew):.3f}")
print("Correlation matrix:\n", r.corr().round(2))

# --- 2. Full-sample optimal weights ---
for k in ["minvar", "maxsharpe"]:
    print(k, dict(zip(tickers, optimize(mu, cov, k).round(2))))

# --- 3. Instability: bootstrap the sample, re-optimize max-Sharpe ---
rng = np.random.default_rng(0)
W = []
for _ in range(200):
    sample = r.iloc[rng.integers(0, len(r), len(r))]
    W.append(optimize(*ann(sample), "maxsharpe"))
W = pd.DataFrame(W, columns=tickers)
print("\nBootstrap max-Sharpe weights (mean / std / min / max):")
print(W.describe().loc[["mean", "std", "min", "max"]].round(2))

# --- 4. Out-of-sample: fit on first half, test on second half ---
half = len(r) // 2
train, test = r.iloc[:half], r.iloc[half:]
mu_tr, cov_tr = ann(train)
for name, w in [("equal", ew),
                ("minvar", optimize(mu_tr, cov_tr, "minvar")),
                ("maxsharpe", optimize(mu_tr, cov_tr, "maxsharpe"))]:
    p = test.values @ w
    sr = p.mean() / p.std() * np.sqrt(252)
    print(f"OOS {name:9s} vol={p.std()*np.sqrt(252):.3f} Sharpe={sr:.2f} "
          f"weights={w.round(2)}")