# pip install alpaca-py statsmodels pandas numpy
import os
from datetime import datetime
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(
    symbol_or_symbols=["AAPL", "SPY", "GLD"],
    timeframe=TimeFrame.Day,
    start=datetime(2018, 1, 1),
    end=datetime(2025, 12, 31),
    adjustment=Adjustment.ALL,          # split/dividend adjusted
)
bars = client.get_stock_bars(req).df
px = bars["close"].unstack(level=0).dropna()   # columns: AAPL, GLD, SPY
rets = np.log(px).diff().dropna()

def report(name, y, x, robust=False):
    X = sm.add_constant(x)
    m = sm.OLS(y, X).fit(cov_type="HC3" if robust else "nonrobust")
    resid = m.resid
    bp_p = het_breuschpagan(resid, X)[1]
    jb_p = jarque_bera(resid)[1]
    print(f"\n== {name} {'(HC3 robust SE)' if robust else ''}")
    print(f"beta={m.params.iloc[1]:.3f}  t={m.tvalues.iloc[1]:.1f}  "
          f"R2={m.rsquared:.3f}")
    print(f"Durbin-Watson={durbin_watson(resid):.2f}  "
          f"BP p={bp_p:.4f}  JB p={jb_p:.4f}")
    return m

# A) Proper regression: AAPL returns on SPY returns
report("AAPL ret ~ SPY ret", rets["AAPL"], rets["SPY"])
report("AAPL ret ~ SPY ret", rets["AAPL"], rets["SPY"], robust=True)

# B) Spurious: AAPL PRICE on GLD PRICE (economically unrelated)
report("AAPL price ~ GLD price", px["AAPL"], px["GLD"])

# C) Same pair, but returns
report("AAPL ret ~ GLD ret", rets["AAPL"], rets["GLD"])

# D) Simulation: two independent random walks
rng = np.random.default_rng(42)
hits = 0
for _ in range(500):
    a = np.cumsum(rng.standard_normal(1000))
    b = np.cumsum(rng.standard_normal(1000))
    t = sm.OLS(a, sm.add_constant(b)).fit().tvalues[1]
    hits += abs(t) > 1.96
print(f"\nIndependent random walks 'significant': {hits/500:.0%}")