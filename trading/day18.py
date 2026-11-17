import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])

# (y, x) candidates. GLD/IAU both hold gold = near-certain "control" pair.
PAIRS = [("GLD", "IAU"), ("KO", "PEP"), ("XOM", "CVX"), ("SPY", "QQQ")]
tickers = sorted({t for p in PAIRS for t in p})

req = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
                       start=datetime(2018, 1, 1),
                       end=datetime.now() - timedelta(days=1),
                       adjustment=Adjustment.ALL)
px = client.get_stock_bars(req).df["close"].unstack(level=0).dropna()
logp = np.log(px)

# Fit on the first 70%, validate on the last 30%
split = int(len(logp) * 0.7)
train, test = logp.iloc[:split], logp.iloc[split:]
print(f"Train {train.index[0].date()}→{train.index[-1].date()}, "
      f"Test →{test.index[-1].date()}\n")

def half_life(s):
    """Regress Δs_t on s_{t-1}; HL = -ln2 / ln(1+b)."""
    d, lag = s.diff().dropna(), s.shift(1).dropna()
    b = sm.OLS(d, sm.add_constant(lag)).fit().params.iloc[1]
    return -np.log(2) / np.log(1 + b) if b < 0 else np.inf

for y, x in PAIRS:
    # Step 1: hedge ratio from TRAIN only
    c, beta = sm.OLS(train[y], sm.add_constant(train[x])).fit().params
    # Step 2: Engle-Granger with MacKinnon critical values
    t_eg, p_eg, crit = coint(train[y], train[x])
    s_train = train[y] - beta * train[x] - c

    # Out-of-sample: SAME beta & c, is the spread still stationary?
    # (beta not fitted here, so ordinary ADF p-values are fine)
    s_test = test[y] - beta * test[x] - c
    p_oos = adfuller(s_test, autolag="AIC")[1]

    # Current z-score using TRAIN mean/sd
    z_now = (s_test.iloc[-1] - s_train.mean()) / s_train.std()
    ret_corr = px[y].pct_change().corr(px[x].pct_change())

    print(f"{y}/{x}: beta={beta:.3f}  return corr={ret_corr:.2f}")
    print(f"  EG t={t_eg:.2f} (5% crit {crit[1]:.2f})  p={p_eg:.3f}")
    print(f"  half-life (train) = {half_life(s_train):.1f} days")
    print(f"  OOS ADF p={p_oos:.3f}   z today={z_now:+.2f}\n")