# Alpaca Trading Lessons  

Daily Trading lessons using Alpaca with tasks and scripts to be updated in this folder.  

## Day 1: Simple vs Log Returns  

Simple Return (Arithmetic Return)
```
R_t = P_t / P_{t-1} - 1
```

Log Return (Continuously compounded)
```
r_t = ln(P_t / P_{t-1}) = ln(1 + R_t)
```

Compounding over time. Simple returns *multiply*
```
1 + R_total = (1+R_1)(1+R_2)...(1+R_n)
```

Log returns *add*
```
r_total = r_1 + r_2 + ... + r_n
```
converting back with
```
R_total = e^{r_total} - 1
```

### Rules of thumb

- For small moves, `r ≈ R (a 0.5% day gives r ≈ 0.4988%)`. The two drift apart on big moves, and log returns are always ≤ simple returns.
- Across time for one asset, log returns add up.
- Across assets in a portfolio on one day, simple returns aggregate: `R_p = Σ wᵢRᵢ`. Log returns don’t.
- The usual workflow is to do the statistics on log returns and report P&L in simple returns.  

### Quiz  
1. A stock goes from $50 to $75. What are the simple and log returns?  
2. Three daily log returns are +0.02, −0.01 and +0.03. What is the total simple return?  
3. You hold 60% SPY and 40% TLT. To get today’s portfolio return as a weighted average, which return type should you use, and why?  

### Answers
1. 1.2 × 0.8 = 0.96, so −4%. It isn’t 0%: compounding punishes symmetric swings.
2. The log returns sum to 0.06, and e^0.06 − 1 ≈ +6.18%.
3. No, not exactly. Convert to simple returns first: AAPL = e^0.04 − 1 = 4.081%, SPY = 0%. The portfolio’s simple return is 2.041%, so its log return is ln(1.02041) ≈ 0.0202, not 0.0200. Log returns add up over time, but across assets it’s simple returns that combine linearly.

## Day 2: Annualizing Returns, CAGR, Arithmetic vs Geometric Mean, Volatility Drag  

Annualizing  
- from daily mean simple return
```
μ_d: annual ≈ (1 + μ_d)^252 − 1
```
- from daily mean *log* return  
```
annual log return = 252 * μ_log  
```  

CAGR
```
(V_end / V_start)^(1/years) - 1
```

Arithmetic vs Geometric Mean
```
Arithmetic
(r_1 + ... + r_n) / n

Geometric
[(1+r_1)...(1+r_n)]^(1/n) - 1
```

Volatility Drag
```
geometric ≈ arithmetic − σ²/2
```

### What to look for:

- geo should be nearly the same as CAGR (both measure real compounded growth).
- arith is always above CAGR. The gap (drag) should be largest for TSLA and smallest for SPY.
- approx_geo (arith − σ²/2) should land close to CAGR. Check whether it works better for SPY or TSLA, and think about why.

### Quiz
1. A strategy returns +20%, −10%, +20%, −10% over 4 years. What are the arithmetic mean and the CAGR?
1. Strategies A and B both have an arithmetic annual mean of 12%. A has σ = 15% and B has σ = 40%. Use the drag approximation to estimate each one’s geometric return.
1. True or false: if you multiply a daily mean simple return by 252, you get the CAGR.

### Answers
1. Arithmetic = (20 − 10 + 20 − 10)/4 = 5%. Growth = 1.2 × 0.9 × 1.2 × 0.9 = 1.1664, so CAGR = 1.1664^(1/4) − 1 ≈ 3.92%.
2. A: 12% − 0.15²/2 = 12% − 1.125% ≈ 10.9%. B: 12% − 0.40²/2 = 12% − 8% ≈ 4%. The averages are the same, but the compounded results are very different.
3. False. That gives an annualized arithmetic mean, which ignores compounding and volatility drag, so it overstates CAGR. Use (V_end/V_start)^(1/years) − 1 or the geometric mean instead.  

## Day 3: Volatility  

### Concept  

1. Volatility = standard deviation of returns  
```
σ = sqrt( Σ (rₜ − r̄)² / (N − 1) )

Tiny example. Five daily returns: +1%, −2%, +0.5%, +1.5%, −1%

Mean = 0%
Squared deviations: 1, 4, 0.25, 2.25, 1 → sum = 8.5 (in %²)
8.5 / 4 = 2.125 → σ_daily = √2.125 ≈ 1.46%
```

2. Square-root-of-time scaling  
```
Var(n days) = n · Var(1 day) → σₙ = σ₁ · √n

Annual: σ_annual = σ_daily × √252
The example above: 1.46% × 15.87 ≈ 23.1% a year
Weekly: × √5. Monthly: × √21
```

3. Rolling volatility  
Vol isn’t constant. It clusters: calm periods stay calm, and wild periods stay wild. A rolling window shows this:

21-day window (about 1 month): reacts fast but is noisy
63 or 252-day window: smooth but slow to react
EWMA (exponentially weighted): gives more weight to recent days, a good middle ground. RiskMetrics uses λ = 0.94.


### What to look for  
- Annualized vol: SPY is probably around 17–20%, QQQ higher, AAPL around 28–32%, TLT lower than SPY.
- Sqrt-rule ratios: mostly between 0.8 and 1.1. A value clearly below 1 suggests short-term mean reversion. The n=63 numbers are noisy because there are few data points.
- The SPY 21-day max should land in March 2020, probably above 80% annualized. The min should be a calm stretch, roughly 5–8%.
- Vol clustering correlation: should be clearly positive (often 0.5 or more). Vol is fairly predictable, much more than returns are.

### Quiz
1. A stock’s daily vol is 1.2%. What is its annualized vol?
2. A strategy’s annualized vol is 20%. What is a typical daily move? What about a typical weekly move?
3. You measure 5-day vol from non-overlapping weekly returns and get 15% less than daily vol × √5. What does that tell you about the returns, and why does it matter if you annualize a weekly-rebalanced strategy’s vol from its daily P&L?  

### Answers  

1. 1.2% × √252 ≈ 1.2% × 15.87 ≈ 19.0%
2. Daily: 20% / √252 ≈ 1.26%. Weekly: 1.26% × √5 ≈ 2.8% (or 20% / √52 ≈ 2.8%)
3. The returns are negatively autocorrelated (some mean reversion): up days tend to be partly undone. If you annualize daily vol with √252, you overstate the risk the strategy really carries over longer horizons. The general lesson: the √n rule assumes independent returns, so check that before you trust a scaled number. Positive autocorrelation would bias it the other way, which is more dangerous.

## Day 4: Drawdowns  

Volatility tells how much returns jump around.  
Drawdown tells how much money actually lost from the best point and how long it took to get it back.  

### Concept  
Drawdown at time `t` is how far equity sits below its highest level
```
Peak_t = max(W_0 ... W_t)
DD_t = W_t / Peak_t - 1           (always <= 0)
```
- max drawdown (MDD) = the most negative DD_t. its the worst loss from a peak to later trough  
- drawdown duration = how long you stay underwater (DD < 0), counted froma  peak until equity makes a new high  
after a loss of `d`, need a gain of:
```
g - 1/(1-d) - 1
```

### What to look for:

- SPY and QQQ: the worst trough should land in the 2020 COVID crash or the 2022 bear market. Which one was deeper for QQQ?
- TLT (long-term bonds): this is the eye-opener. Check its max drawdown and whether it says “not yet” recovered. People call these “safe” assets, but they can lose badly too.
- `pct_time_uw`: even good assets spend most days below their previous high. That’s normal, and it’s useful to know before you watch a live equity curve.
- Compare duration to depth. A shallow drawdown can still drag on for a long time.

### Quiz
1. Your strategy is down 40% from its peak. What return do you need to get back to even?
2. Equity goes 50 → 60 → 45 → 55 → 66. What’s the max drawdown, and at which step do you recover?
3. You run the same strategy over a 3-year backtest and a 15-year backtest. Which one will usually show the bigger max drawdown, and why?

### Answers
1. 1/0.6 − 1 = +66.7%.
2. The peak is 60 and the trough is 45, so MDD = 45/60 − 1 = −25%. You recover at 66 (step 5), the first value at or above 60. You were underwater for 2 steps (45 and 55).
3. The 15-year one, in general. Max drawdown is the worst event in the sample. A longer sample gives more chances for a bad streak, so the expected MDD grows with time. A short backtest’s MDD is too optimistic, so plan for something worse when you go live.