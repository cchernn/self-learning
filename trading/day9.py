import os
from datetime import datetime
import numpy as np
import pandas as pd
import statsmodels.api as sm
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "AAPL", "QQQ", "XLU", "TSLA"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2019, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
bars = client.get_stock_bars(req).df            # MultiIndex (symbol, timestamp)
px = bars["close"].unstack(level=0).dropna()    # columns = tickers
rets = px.pct_change().dropna()                 # simple daily returns

# 1) Full regression: AAPL on SPY
X = sm.add_constant(rets["SPY"])
fit = sm.OLS(rets["AAPL"], X).fit()
a, b = fit.params["const"], fit.params["SPY"]
print(f"AAPL beta={b:.3f}  alpha/day={a:.5f}  alpha/yr~{a*252:.2%}")
print(f"t-stats: alpha={fit.tvalues['const']:.2f}  beta={fit.tvalues['SPY']:.1f}")
print(f"R^2={fit.rsquared:.3f}")

# 2) Sanity check: beta = Cov/Var and = corr * sd ratio
cov_b = rets["AAPL"].cov(rets["SPY"]) / rets["SPY"].var()
corr_b = rets["AAPL"].corr(rets["SPY"]) * rets["AAPL"].std() / rets["SPY"].std()
print(f"beta via cov/var={cov_b:.3f}, via corr*sd={corr_b:.3f}")

# 3) Compare several tickers
rows = []
for t in tickers[1:]:
    f = sm.OLS(rets[t], sm.add_constant(rets["SPY"])).fit()
    rows.append({"ticker": t, "beta": f.params["SPY"],
                 "alpha_ann": f.params["const"] * 252,
                 "alpha_t": f.tvalues["const"], "R2": f.rsquared})
print(pd.DataFrame(rows).round(3).to_string(index=False))

# 4) Rolling 1-year beta: is beta stable?
roll_beta = (rets["AAPL"].rolling(252).cov(rets["SPY"])
             / rets["SPY"].rolling(252).var()).dropna()
print("AAPL rolling beta, year-end values:")
print(roll_beta.groupby(roll_beta.index.year).last().round(2))