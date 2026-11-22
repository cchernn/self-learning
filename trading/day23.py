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
TICKERS = ["SPY", "TLT", "GLD"]
req = StockBarsRequest(symbol_or_symbols=TICKERS, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)  # include dividends (matters for TLT)
px = client.get_stock_bars(req).df["close"].unstack(level=0)[TICKERS].dropna()
rets = px.pct_change().dropna()

# ---- Risk contributions & ERC solver ----
def risk_contrib(w, cov):
    w = np.asarray(w)
    return w * (cov @ w) / (w @ cov @ w)      # fractions, sum to 1

def erc_weights(cov):
    n = len(cov)
    obj = lambda w: ((risk_contrib(w, cov) - 1 / n) ** 2).sum()
    res = minimize(obj, np.ones(n) / n, method="SLSQP", bounds=[(0, 1)] * n,
                   constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                   options={"ftol": 1e-12})
    return res.x

# ---- Part 1: full-sample comparison ----
cov = rets.cov().values * 252
vols = np.sqrt(np.diag(cov))
ports = {
    "60/40 SPY/TLT": np.array([0.6, 0.4, 0.0]),
    "Equal weight": np.ones(3) / 3,
    "Inverse vol": (1 / vols) / (1 / vols).sum(),
    "Risk parity (ERC)": erc_weights(cov),
}
print("Asset vols:", dict(zip(TICKERS, np.round(vols, 3))))
for name, w in ports.items():
    print(f"{name:18s} w={np.round(w,2)} vol={np.sqrt(w@cov@w):.1%} "
          f"risk%={np.round(risk_contrib(w, cov)*100)}")

# ---- Part 2: backtest with drift, rebalancing and costs ----
def backtest(rets, weight_fn, rebalance=True, cost_bps=5, lookback=252):
    month_ends = set(rets.groupby(rets.index.to_period("M")).tail(1).index)
    w = weight_fn(rets.iloc[:lookback])                 # initial weights
    eq, turnover = [1.0], 0.0
    for i in range(lookback, len(rets)):
        r = rets.iloc[i].values
        port_r = w @ r
        w = w * (1 + r) / (1 + port_r)                  # weights drift
        cost = 0.0
        if rebalance and rets.index[i] in month_ends:
            target = weight_fn(rets.iloc[i - lookback + 1: i + 1])  # trailing data only
            to = np.abs(target - w).sum()
            turnover += to
            cost = to * cost_bps / 1e4
            w = target
        eq.append(eq[-1] * (1 + port_r) * (1 - cost))
    return pd.Series(eq, index=rets.index[lookback - 1:]), turnover

def stats(eq, turnover):
    r = eq.pct_change().dropna(); yrs = len(r) / 252
    return {"CAGR": eq.iloc[-1] ** (1 / yrs) - 1,
            "Vol": r.std() * np.sqrt(252),
            "Sharpe": r.mean() / r.std() * np.sqrt(252),
            "MaxDD": (eq / eq.cummax() - 1).min(),
            "Turnover/yr": turnover / yrs}

equal   = lambda R: np.ones(R.shape[1]) / R.shape[1]
inv_vol = lambda R: (1 / R.std()).values / (1 / R.std()).sum()
erc     = lambda R: erc_weights(R.cov().values * 252)
sixty40 = lambda R: np.array([0.6, 0.4, 0.0])

runs = {
    "60/40, monthly":   backtest(rets, sixty40),
    "Equal, buy&hold":  backtest(rets, equal, rebalance=False),
    "Equal, monthly":   backtest(rets, equal),
    "Inv vol, monthly": backtest(rets, inv_vol),
    "ERC, monthly":     backtest(rets, erc),
}
print(pd.DataFrame({k: stats(*v) for k, v in runs.items()}).T.round(3))