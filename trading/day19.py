import os
import numpy as np, pandas as pd
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

TICKERS = ["SPY", "QQQ", "TLT", "GLD", "AAPL"]
RF_ANNUAL = 0.03                       # simplification: constant risk-free rate
rf_d = (1 + RF_ANNUAL) ** (1/252) - 1  # convert to daily...
rf_m = (1 + RF_ANNUAL) ** (1/12) - 1   # ...and monthly

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols=TICKERS, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)   # split+dividend adjusted
px = client.get_stock_bars(req).df["close"].unstack(level=0)
px.index = pd.to_datetime(px.index.date)            # drop tz/time
px = px.dropna()

def metrics(p):
    r = p.pct_change().dropna()
    ex = r - rf_d
    n = len(ex)
    sharpe = ex.mean() / ex.std() * np.sqrt(252)
    # correct Sortino: downside deviation averaged over ALL days
    dd_dev = np.sqrt((np.minimum(ex, 0) ** 2).mean())
    sortino = ex.mean() / dd_dev * np.sqrt(252)
    # common WRONG version: std of negative days only
    sortino_wrong = ex.mean() / ex[ex < 0].std() * np.sqrt(252)
    cagr = (p.iloc[-1] / p.iloc[0]) ** (252 / n) - 1
    mdd = (p / p.cummax() - 1).min()
    # Sharpe from monthly returns (sanity check on sqrt-time scaling)
    m = p.resample("ME").last().pct_change().dropna() - rf_m  # "ME" needs pandas>=2.2
    sharpe_m = m.mean() / m.std() * np.sqrt(12)
    # Lo (2002) standard error of the annualized Sharpe
    sr_d = sharpe / np.sqrt(252)
    se = np.sqrt((1 + 0.5 * sr_d**2) / n) * np.sqrt(252)
    return pd.Series(dict(CAGR=cagr, MaxDD=mdd, Sharpe=sharpe, SR_SE=se,
                          SR_lo95=sharpe - 1.96*se, SR_monthly=sharpe_m,
                          Sortino=sortino, Sortino_WRONG=sortino_wrong,
                          Calmar=cagr / abs(mdd)))

pd.set_option("display.width", 200)
print(px.apply(metrics).T.round(2))

# --- Pitfall demo: smoothing returns fakes a higher Sharpe ---
r = px["SPY"].pct_change().dropna()
smooth = (0.5 * r + 0.5 * r.shift(1)).dropna()   # like a stale/smoothed NAV
for name, rr in [("SPY raw", r), ("SPY smoothed", smooth)]:
    s = metrics((1 + rr).cumprod())
    print(f"{name:13s} daily-SR {s.Sharpe:.2f} | monthly-SR {s.SR_monthly:.2f}")