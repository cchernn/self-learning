import os
import numpy as np, pandas as pd, statsmodels.api as sm
from datetime import datetime
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

def half_life(x):
    """Regress dx_t on x_{t-1}; return (lambda, t-stat, half-life in bars)."""
    x = pd.Series(x).dropna()
    dx = x.diff().dropna()
    lag = x.shift(1).loc[dx.index]
    res = sm.OLS(dx.values, sm.add_constant(lag.values)).fit()
    lam, t = res.params[1], res.tvalues[1]
    hl = -np.log(2) / lam if lam < 0 else np.inf
    return lam, t, hl

# 1) Sanity check: simulate OU with known theta=0.05 (true HL ~13.5-13.9)
rng = np.random.default_rng(0)
theta, sigma, n = 0.05, 0.01, 2000
x = np.zeros(n)
for i in range(1, n):
    x[i] = x[i-1] + theta * (0 - x[i-1]) + sigma * rng.standard_normal()
lam, t, hl = half_life(x)
print(f"Simulated OU: lambda={lam:.4f}  t={t:.1f}  HL={hl:.1f} days\n")

# 2) Real data
client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
req = StockBarsRequest(symbol_or_symbols=["SPY", "KO", "PEP", "XOM", "CVX"],
                       timeframe=TimeFrame.Day,
                       start=datetime(2018, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
px = client.get_stock_bars(req).df["close"].unstack(level=0).dropna()
lp = np.log(px)

series = {
    "log SPY price": lp["SPY"],
    "log KO/PEP":    lp["KO"] - lp["PEP"],
    "log XOM/CVX":   lp["XOM"] - lp["CVX"],
}
print(f"{'series':<15}{'lambda':>9}{'t':>7}{'HL(days)':>10}")
for name, s in series.items():
    lam, t, hl = half_life(s)
    print(f"{name:<15}{lam:>9.4f}{t:>7.2f}{hl:>10.1f}")
print("(DF 5% critical t is about -2.86, not -1.96)\n")

# 3) Stability: half-life of KO/PEP by calendar year
kp = series["log KO/PEP"]
for yr, s in kp.groupby(kp.index.year):
    lam, t, hl = half_life(s)
    print(f"KO/PEP {yr}: HL={hl:6.1f} days  t={t:5.2f}")

# 4) Use the half-life: z-score with lookback ~ HL
hl_full = half_life(kp)[2]
w = int(np.clip(round(hl_full), 5, 120))
z = (kp - kp.rolling(w).mean()) / kp.rolling(w).std()
print(f"\nLookback={w} days, latest KO/PEP z-score: {z.iloc[-1]:.2f}")