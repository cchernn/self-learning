import os
import numpy as np, pandas as pd
from datetime import datetime
from scipy import stats
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
TICKERS = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]
req = StockBarsRequest(symbol_or_symbols=TICKERS, timeframe=TimeFrame.Day,
                       start=datetime(2016, 1, 1), end=datetime(2025, 12, 31),
                       adjustment=Adjustment.ALL)
close = req_df = client.get_stock_bars(req).df["close"].unstack(level=0).dropna()
r = close.pct_change()

# --- 1. Run the "research": 35 momentum rules -------------------------
LOOKBACKS = [5, 10, 20, 40, 60, 120, 200]
res = {}
for t in TICKERS:
    for L in LOOKBACKS:
        mom = close[t].pct_change(L)
        # long if past-L return > 0, flat otherwise; trade NEXT day
        pos = (mom > 0).astype(float).where(mom.notna()).shift(1)
        res[f"{t}_{L}"] = pos * r[t]
strat = pd.DataFrame(res).dropna()
N, T = strat.shape[1], len(strat)

sr_d = strat.mean() / strat.std()          # daily Sharpe per rule
sr_a = sr_d * np.sqrt(252)                 # annualized
best = sr_a.idxmax()
print(f"Tested N={N} rules over T={T} days ({T/252:.1f} yrs)")
print(sr_a.sort_values(ascending=False).head(5).round(2))
bh = r[best.split('_')[0]].loc[strat.index]
print(f"Buy & hold {best.split('_')[0]} Sharpe: {bh.mean()/bh.std()*np.sqrt(252):.2f}")

# --- 2. Naive vs Bonferroni p-value for the winner --------------------
t_stat = sr_d[best] * np.sqrt(T)
p_naive = 1 - stats.norm.cdf(t_stat)
print(f"\nBest rule: {best}  Sharpe={sr_a[best]:.2f}  t={t_stat:.2f}")
print(f"Naive one-sided p-value : {p_naive:.4f}")
print(f"Bonferroni p (x{N})      : {min(1, p_naive*N):.4f}")

# --- 3. What does the best of N PURE-NOISE strategies look like? ------
rng = np.random.default_rng(42)
n_sims = 1000
max_noise = np.empty(n_sims)
for i in range(n_sims):
    noise = rng.standard_normal((T, N))     # zero true Sharpe
    s = noise.mean(0) / noise.std(0, ddof=1) * np.sqrt(252)
    max_noise[i] = s.max()
print(f"\nPure noise: median best Sharpe of {N} = {np.median(max_noise):.2f}, "
      f"95th pct = {np.percentile(max_noise, 95):.2f}")
print(f"Share of noise runs beating your best: {(max_noise >= sr_a[best]).mean():.1%}")

# --- 4. Probabilistic & Deflated Sharpe ------------------------------
def expected_max_sr(var_sr, n):
    g = 0.5772156649                        # Euler-Mascheroni
    return np.sqrt(var_sr) * ((1 - g) * stats.norm.ppf(1 - 1/n)
                              + g * stats.norm.ppf(1 - 1/(n * np.e)))

def prob_sr_above(x, sr0):
    sr = x.mean() / x.std()
    sk = stats.skew(x)
    ku = stats.kurtosis(x, fisher=False)    # raw kurtosis (normal = 3)
    z = (sr - sr0) * np.sqrt(len(x) - 1) / np.sqrt(1 - sk*sr + (ku - 1)/4 * sr**2)
    return stats.norm.cdf(z)

var_sr = max(sr_d.var(), 1 / T)             # spread of Sharpes across trials
sr0 = expected_max_sr(var_sr, N)            # luck hurdle (daily units)
x = strat[best]
print(f"\nLuck hurdle SR0 (annualized): {sr0*np.sqrt(252):.2f}")
print(f"PSR  (vs 0, ignores the {N} trials): {prob_sr_above(x, 0):.3f}")
print(f"DSR  (vs luck hurdle)            : {prob_sr_above(x, sr0):.3f}")

c = strat.corr().values
print(f"Avg pairwise correlation of rules: {c[np.triu_indices(N, 1)].mean():.2f}")