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
tickers = ["SPY", "QQQ", "AAPL", "TLT", "GLD"]
req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2018, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
df = client.get_stock_bars(req).df
px = df["close"].unstack(level=0)[tickers].dropna()
rets = np.log(px).diff().dropna()

# 1) Full-sample annualized covariance and correlation
print("Annualized covariance:\n", (rets.cov() * 252).round(4))
print("\nCorrelation:\n", rets.corr().round(2))

# 2) Check the formula by hand for SPY vs QQQ
a, b = rets["SPY"], rets["QQQ"]
cov_ab = ((a - a.mean()) * (b - b.mean())).sum() / (len(a) - 1)
print("\nManual rho:", round(cov_ab / (a.std() * b.std()), 4),
      "| pandas:", round(a.corr(b), 4))

# 3) Rolling 63-day (~1 quarter) correlation with SPY, averaged by year
roll = pd.DataFrame({t: rets[t].rolling(63).corr(rets["SPY"])
                     for t in tickers if t != "SPY"})
print("\nAvg rolling corr with SPY by year:\n",
      roll.groupby(roll.index.year).mean().round(2))
print("\nRange of rolling SPY-TLT corr:",
      round(roll["TLT"].min(), 2), "to", round(roll["TLT"].max(), 2))

# 4) Calm vs stressed regimes (stressed = SPY 21d vol in its top 20%)
vol21 = rets["SPY"].rolling(21).std()
stressed = vol21 > vol21.quantile(0.80)
calm = vol21 < vol21.quantile(0.50)
print("\nCorr in CALM regime:\n", rets[calm].corr()["SPY"].round(2))
print("\nCorr in STRESSED regime:\n", rets[stressed].corr()["SPY"].round(2))

# 5) What diversification bought you: 50/50 SPY/TLT
s1, s2 = rets["SPY"].std(), rets["TLT"].std()
rho = rets["SPY"].corr(rets["TLT"])
vol = lambda r: np.sqrt(0.25*s1**2 + 0.25*s2**2 + 0.5*r*s1*s2) * np.sqrt(252)
print(f"\n50/50 SPY/TLT vol: actual rho={rho:.2f} -> {vol(rho):.1%}, "
      f"if rho=1 -> {vol(1):.1%}")