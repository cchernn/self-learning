import os
from datetime import datetime
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols=["SPY", "QQQ", "AAPL", "XLE"],
                       timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)   # split/dividend adjusted
px = client.get_stock_bars(req).df["close"].unstack(level=0)
rets = np.log(px).diff().dropna()

def test_mean(r, alpha=0.05):
    n, m, s = len(r), r.mean(), r.std(ddof=1)
    se = s / np.sqrt(n)                       # standard error of the mean
    t = m / se                                # t-stat vs H0: mean = 0
    p = 2 * stats.t.sf(abs(t), df=n - 1)      # two-sided p-value
    tc = stats.t.ppf(1 - alpha / 2, df=n - 1)
    lo, hi = m - tc * se, m + tc * se         # confidence interval
    # Newey-West t-stat: regress returns on a constant with HAC errors
    hac = sm.OLS(r.values, np.ones(n)).fit(cov_type="HAC",
                                           cov_kwds={"maxlags": 5})
    sr = m / s * np.sqrt(252)                 # annual Sharpe (rf = 0)
    return dict(n=n, t=t, p=p, t_hac=hac.tvalues[0],
                ann_mean=m * 252, ann_lo=lo * 252, ann_hi=hi * 252,
                sharpe=sr, yrs_for_t2=(2 / sr) ** 2 if sr > 0 else np.inf)

res = pd.DataFrame({sym: test_mean(rets[sym]) for sym in rets}).T
print(res.astype(float).round(3))

# Sanity check against scipy's built-in test
print("\nscipy SPY:", stats.ttest_1samp(rets["SPY"], 0))

# How informative is ONE year of data? t-stat per calendar year
spy = rets["SPY"]
yearly_t = spy.groupby(spy.index.year).apply(
    lambda r: r.mean() / (r.std() / np.sqrt(len(r))))
print("\nSPY t-stat by year:\n", yearly_t.round(2))