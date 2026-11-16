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

## Day 5: Value at Risk & Expected Shortfall

VaR and Expected Shortfall answers "how much could I lose tomorrow, and how bad is it when things really go wrong"  
Usually used to set position limits and kill switches  

### Concept  
Var at confidence level (1-α) is the loss only exceed with probability α.
95% 1-day VaR = 2% means "on 19 out of 20 days, I lose less than 2%"

Expected Shortfall (also called CVaR) = average loss on days when going past VaR.
```
VaR = -quantile(r,α)
ES = -mean(r for the returns <= that quantile)
```

Parametric (normal) method: assume r ~ N(μ, σ²), and let z = Φ⁻¹(α) (−1.645 at 95%, −2.326 at 99%).
```
VaR = −(μ + z·σ)
ES = −μ + σ·φ(z)/α (φ = normal pdf)
```
Worked example (parametric): μ = 0.05%, σ = 1.2% daily, 95%:
```
VaR = 1.645×1.2 − 0.05 = 1.92%, so about $1,924 on a $100k book
ES = 1.2 × 0.1031/0.05 − 0.05 = 2.43%
```
Worked example (historical): over 100 days, the 5 worst were −4.1, −3.2, −2.8, −2.5, −2.2%.
```
95% VaR ≈ 2.2% (the 5th worst; quantile conventions vary slightly)
ES = mean of the 5 = 14.8/5 = 2.96%
```

### What to look for:

- ES is always larger than VaR. Note how much larger at 99%.
- At 99%, historical VaR is usually bigger than the normal VaR, especially for SPY/QQQ. That’s fat tails (Day 6–7 preview). At 95% the two methods often roughly agree.
- Breach rate: the expected rate is 1%. You’ll likely see more than that, and they bunch up in 2020 (and 2018/2022). That’s volatility clustering: a 1-year window reacts too slowly.
- TLT: the “safe” asset still has non-trivial VaR. Compare it to SPY.

### Quiz
1. Strategies A and B both have 95% 1-day VaR of 2%. Can their risk still differ a lot? Which number would show it?
2. A $50,000 position has daily σ = 1.5% and μ ≈ 0. What is its 99% 1-day parametric VaR in dollars? And its rough 10-day VaR?
3. Your rolling 99% VaR model had 25 breaches in 1,000 days. What does that tell you?

### Answers
1. Yes. VaR only marks the threshold. A might lose 2.5% on its bad days while B (say, short options) loses 15%. Expected Shortfall shows the difference.
2. 2.326 × 1.5% = 3.49%, so ≈ $1,745. 10-day ≈ $1,745 × √10 ≈ $5,517.
3. You’d expect about 10. Getting 25 or more by luck has a probability of about 0.004% (binomial), so the model underestimates risk. The usual causes are fat tails and volatility clustering. Fixes include a shorter or EWMA volatility window, a fatter-tailed distribution, or adding a safety buffer.

## Day 6: Distributions - normal assumption, skewness, kurtosis  

### Concept  
Standardized returns `z = (r − μ)/σ`  

Skewness = average of z³
- 0 → symmetric
- negative → long left tail (rare big losses, many small gains). Typical for stock indices.
- positive → long right tail (rare big wins). Typical for lottery-like assets and trend-following.

Kurtosis = average of z⁴. A normal has kurtosis 3, so we usually report excess kurtosis = kurtosis − 3.
- 0 → normal-like tails
- > 0 → fat tails and a tall, skinny middle: lots of quiet days with the occasional huge move. Daily equity returns often have excess kurtosis of 5–15.

### What to look for

- Daily SPY/QQQ: negative skew, excess kurtosis far above the normal 95% range (which will be roughly ±0.2). The March 2020 crash dominates.
- `worst_z` for SPY: probably around −8 to −10 sigma. Look at `P_normal(worst)`, which is a number so tiny that, under a normal model, it should never happen in the life of the universe. Yet it happened in your 10-year sample.
- Monthly: kurtosis should be much lower than daily (aggregation at work), though usually still not zero.
- Compare TLT (bonds) and AAPL to the indices. Is the skew sign the same?

### Quiz

1. A strategy has a high Sharpe ratio, skew of −2.5 and excess kurtosis of 12. In plain words, what does its return pattern probably look like, and what’s the risk?
2. SPY’s daily σ is about 1.1%. Under a normal model, roughly how often should a −4.4% day (a 4-sigma down move) happen? (Use P(Z < −4) ≈ 3.2×10⁻⁵ and 252 trading days/year.)
3. True or false: if daily returns have excess kurtosis of 10, monthly returns of the same asset will also have excess kurtosis near 10.

### Answers  

1. Steady small gains most of the time, then rare, very large losses: the “selling insurance / pennies in front of a steamroller” profile. Sharpe only uses mean and std, so it misses this tail risk. You’d want drawdown, Expected Shortfall and a long history including crashes before trusting it.
2. 1 / 3.2×10⁻⁵ ≈ 31,000 trading days ≈ once every ~125 years. In reality SPY has had many such days in the last two decades. That gap is tomorrow’s topic (fat tails).
3. False. Summing about 21 daily returns pulls the distribution toward normal (CLT), so monthly kurtosis is usually much lower. It often stays above 0, though, because volatility clusters, which means daily returns aren’t fully independent.

## Day 7: Fat Tails - QQ plots, 3-sigma days, Jarque-Bera  

### Concept  
1. Count extremes. Standardize returns: z = (r - mean) / std. Under a normal, P(|z| > 3) = 0.27%  
2. QQ plot. This plots sample's quantiles against the normal quantiles. If data were normal, points would sit on a straight line. With fat tails you get an S-shape  
3. Jarque-Bera test. Combining skew (S) and kurtosis (K, where normal=3) 
```
JB = n/6 · [ S² + (K − 3)² / 4 ]
```
Under normality, JB follows a χ² distribution with 2 degrees of freedom. The 5% critical value is 5.99.

### What to look for:

- >3sd actual vs expected: the actual count should be several times the expected ~7.
- >4sd: the normal says roughly 0; you’ll likely see a handful (March 2020 alone supplies several).
- Excess kurtosis well above 0, and JB p-values effectively 0.
- Worst day z: probably around −8 to −11 for SPY. Under a normal, that should essentially never happen in the lifetime of the universe.
- QQ plot: an S-shape against the normal. The Student-t panel should hug the line much better. A fitted df of roughly 2–4 means very fat tails.

### Day 7 Quiz
1. Over 2,520 trading days, how many days beyond ±4σ does a normal distribution predict? Roughly how many years is that per event?
2. On a QQ plot (theoretical quantiles on x, sample quantiles on y), where do the points sit in each tail for fat-tailed data?
3. A strategy’s 250 daily returns give JB = 8. Do you reject normality at 5%? And if a different sample had JB = 3, would that prove the returns are normal?

### Week 1 Review Quiz
4. A stock goes +10% then −10%. What’s the total simple return? What’s the sum of the log returns?
5. Monthly arithmetic mean is 1%, monthly vol is 5%. What’s the approximate geometric mean per month?
6. Daily vol is 1.2%. What’s the annualized vol?
7. You’re down 40%. What gain do you need to get back to even?
8. 1-day 99% parametric VaR on $100k, with μ = 0 and σ = 1.5%?

### Answers
1. P = 6.33×10⁻⁵, so 2,520 × P ≈ 0.16 days, i.e. one every ~63 years. Real markets deliver several per decade.
2. Left tail below the line, right tail above it. The sample’s extremes go further out than the normal’s: an S-shape.
3. p = e^(−8/2) ≈ 0.018 < 0.05 → reject. No: failing to reject never proves normality. It may just mean there wasn’t enough data, since 250 days rarely contain enough tail events.
4. 1.1 × 0.9 − 1 = −1%. Log returns: ln 1.1 + ln 0.9 = 0.0953 − 0.1054 = −0.0101. ln(0.99) gives the same number, which is why log returns add over time.
5. ≈ 1% − σ²/2 = 1% − 0.125% = 0.875% (volatility drag).
6. 1.2% × √252 ≈ 19.0%
7. 1/0.6 − 1 = +66.7%
8. 2.326 × 1.5% = 3.49% → ≈ $3,490. And given today’s lesson, that normal-based number understates tail risk.

## Day 8: Covariance & Correlation  

Diversification only works when positions don't all move together.
Correlation tells how much they move together, covariance is what goes into portfolio risk.  

### Concept  

For returns *a* and *b* over *n* periods:  
- Covariance: Cov(a,b) = Σ(aᵢ−ā)(bᵢ−b̄) / (n−1)  
- Correlation: ρ = Cov(a,b) / (σₐ·σ_b), which always falls between −1 and +1  

Why correlation drives portfolio risk (two assets):
```
σₚ² = w₁²σ₁² + w₂²σ₂² + 2·w₁w₂·ρ·σ₁σ₂
```

Take a 50/50 mix of two assets, each with 20% volatility:
- ρ = 1 → portfolio vol 20.0% (no benefit at all)  
- ρ = 0.5 → 17.3%  
- ρ = 0 → 14.1%  
- ρ = −0.5 → 10.0%  

### Three warnings:

1. Correlation only measures linear co-movement.
2. It is an estimate from a sample, so it has noise. A 63-day correlation is very noisy.
3. In a sell-off, everyone de-risks at the same time, so correlations between risky assets rise. Even the stock/bond hedge can fail: in 2022 stocks and bonds fell together.  

### Quiz  

1. Cov(A,B) = 0.0002, σₐ = 2%, σ_b = 1.5% (daily). What is ρ?  
2. A 50/50 portfolio of two assets, each with 30% annual vol and ρ = 0.2. What is the portfolio vol?  
3. True or false: "ρ = 0 means the two assets are independent." Explain.  

### Answers  
1. ρ = 0.0002 / (0.02 × 0.015) = 0.0002 / 0.0003 = 0.667  
2. σₚ² = 0.25(0.09) + 0.25(0.09) + 2(0.25)(0.2)(0.09) = 0.045 + 0.009 = 0.054, so σₚ = 23.2%  
3. False. Zero correlation only rules out a linear relationship. Example: x is symmetric around 0 and y = x². Then ρ ≈ 0, yet y is completely determined by x. In markets, two assets can look uncorrelated on average and still crash together, a tail dependence that a single ρ hides.  

## Day 9: Linear Regression for Finance: Beta, Alpha, R²

Regression splits return into **market part (beta)** and **leftover part (alpha + noise)**  

### Concept
CAPM-style regression  
```
r_stock = α + β · r_SPY + ε
```
- `β (beta) = Cov(r_stock, r_SPY) / Var(r_SPY)`. It also equals `corr × (σ_stock / σ_SPY)`. `β = 1.5` means the stock moves about 1.5% for every 1% SPY move, on average.
- `α (alpha)` = the average return left over once the market part is taken out: `α = mean(r_stock) − β · mean(r_SPY)`. It’s usually tiny per day, so annualize it with α × 252.
- **R²** = the share of the stock’s return variance explained by the market (= corr² for one regressor). The rest, 1 − R², is idiosyncratic risk, which diversification can remove.
- Hedge ratio: to make $10k of a β = 1.4 stock market-neutral, short about $14k of SPY.

### What to look for

- Beta should match across all three methods (the OLS fit, cov/var, and corr × sd ratio).
- QQQ: β above 1 and R² near 0.9, since it’s mostly the market. XLU (utilities): β well below 1. TSLA: high β but low R², meaning lots of stock-specific risk.
- Alpha’s t-stat is usually below 2 even when the annualized alpha looks impressive. That’s a preview of Day 11: alpha is noisy.
- Rolling beta changes noticeably over time. Treat a single beta number as an estimate, not a constant.

### Quiz
1. A stock has β = 1.2 and α = 0. SPY rises 2% today. What’s the expected stock return?
2. Corr(stock, SPY) = 0.6, σ_stock = 30%, σ_SPY = 15%. What is β, and what is R²?
3. A fund shows +15%/yr returns with β = 1.5 while SPY returned +10%/yr (ignore the risk-free rate). Roughly what is its alpha, and was the fund manager skilled?

### Answers
1. 1.2 × 2% = +2.4%
2. β = 0.6 × 30/15 = 1.2. R² = 0.6² = 0.36, so 64% of its variance is idiosyncratic.
3. α ≈ 15% − 1.5 × 10% = 0%. The returns are just leveraged market exposure, not skill.

## Day 10: Regression Pitfalls  

Classic way algo traders fool themselves is to regress *one price* series on another, see R² = 0.9, and trade a relationship that doesn’t exist  

### Concept  
1. Check residuals first  
`OLS: y = α + βx + ε`. The t-stats and p-values assume the residuals ε are:
- independent, meaning not autocorrelated
- constant variance (homoskedastic)
- roughly normal (this matters less with large samples)  

    Durbin–Watson (autocorrelation):
    `DW ≈ 2(1 − ρ)`, where ρ is the lag-1 autocorrelation of the residuals.

- DW ≈ 2 means no autocorrelation (good)
- DW near 0 means strong positive autocorrelation (bad)
- Example: ρ = 0.95 gives DW ≈ 2(0.05) = 0.10. That’s a red flag.

2. Heteroskedasticity  
Return variance isn't constant, it clusters, calm periods and crash periods. In regression, the residual variance changes over time or with x.  
- **Effect**: β is still unbiased, but the ordinary SEs are wrong, usually too small, so the t-stats come out too big.
- **Test**: Breusch–Pagan. A small p-value means heteroskedasticity is present.
- **Fix**: use robust SEs (HC3, or HAC/Newey–West if there’s also autocorrelation). β stays the same and only the SEs change.  

3. Spurious regression on prices  
Prices behave like random walks. If you regress one random walk on another *completely independent* one, you very often get a "significant" result.  
**Rule**: regress **returns on returns**, never prices on prices. The one exception is cointegration. Telltale sign of a spurious regression is high R² with DW near 0.  

### What to look for:

- A: DW should be close to 2. BP p will probably be tiny (heteroskedastic), and JB p tiny too (fat tails, Day 7). β is the same in both runs, but compare the t-stats: the robust t should be smaller.
- B: you’ll likely see a large |t|, a sizeable R², and DW near 0. That’s the spurious pattern.
- C: R² should collapse toward ~0, and the “relationship” mostly disappears.
- D: about 90%+ of the random walks come out “significant.”

### Quiz
1. You regress stock X’s price on stock Y’s price over 5 years and get R² = 0.85, t = 40, DW = 0.06. What’s going on, and what should you do?
2. A returns regression gives DW = 1.2. What’s the approximate lag-1 residual autocorrelation?
3. True or false: heteroskedasticity biases the β estimate, so you should use robust SEs to get the correct β.

### Answers
1. It’s almost certainly spurious. DW = 0.06 means the residuals have ρ ≈ 0.97 and are basically a random walk themselves. Rerun the regression on returns, or if you think the two really are linked, test for cointegration (Day 18).
2. ρ ≈ 1 − DW/2 = 1 − 0.6 = 0.4.
3. False. β stays unbiased. What heteroskedasticity breaks is the SEs, and therefore the t-stats and p-values. Robust SEs leave β unchanged and correct the SEs.

## Day 11: Hypothesis Testing  

### Concept  
- **Null hypothesis (H₀)**: true mean daily return μ = 0 (no edge).  
- **Standard error of the mean**: how much the sample mean wobbles from sample to sample  
`SE = s / √n` (s = std of daily returns, n = number of days)  
- **t-statistic**: how many SEs your mean is from zero  
`t = mean / SE`  
- **p-value**: if H₀ were true, the probability of a |t| at least this large. Small p → luck is an unlikely explanation.  
- **95% confidence interval**: `mean ± t_crit × SE` (t_crit ≈ 1.96 for big n). If the interval contains 0, you can’t reject “no edge.”  

- **Key shortcut**: t ≈ annual Sharpe × √years. With a Sharpe of 0.5, reaching t = 2 takes (2/0.5)² = 16 years of data. Daily returns are very noisy, so you need a lot of data to prove an edge.  
- **Caveats**: the plain t-test assumes independent returns. Real returns have volatility clustering and some autocorrelation, so it’s common to also report a Newey–West (HAC) t-stat, which corrects for that.  

### What to look for:
- Even SPY over 10 years probably has a t-stat only around 2, with p near 0.05. Its annualized CI will be very wide, likely spanning 20+ percentage points.  
- Compare t with t_hac. Are they close? If they are, autocorrelation isn’t distorting the test much here.  
yrs_for_t2: how many years each asset needs before its edge becomes “significant.”  
- Yearly t-stats will swing hard, from strongly negative to strongly positive. One good year proves almost nothing.  

### Quiz  
1. A strategy has an annual Sharpe of 1.0. Roughly how many years of data give t ≈ 2?  
2. You double the number of observations and the mean and std stay the same. By what factor does the SE change? What happens to t?  
3. True or false: “p = 0.03 means there’s a 3% chance my strategy has no edge.”  

### Answers  
1. 4 years, from (2 / 1.0)² = 4.
2. SE shrinks by 1/√2 ≈ 0.71×, so t grows by √2 ≈ 1.41×.
3. False. p is P(data this extreme | no edge), not P(no edge | data). It also assumes this was the only strategy you tested. Trying many inflates false positives, which is Day 13’s topic.  

## Day 12: Bootstrapping & Permutation Tests  

### Concepts  
1. **Bootstrap: How certain is my estimate**  
Treat your sample N returns as stand-in for the population  
- Draw N returns with replacement  
- Compute statistic you care about (mean, Sharpe ratio, max DD, ...)  
- Repeat B times  
- Spread of B values is sampling distribution. For a 95% percentage CI, take the 2.5th and 97.5th percentiles  

2. **Permutation test: Is this better than luck?**  
Pick a null hypothesis, eg. "my signla has no timing skill"  
- Keep returns fixed and shuffle the position series (this keeps the same % of time in the market)  
- Recompute the strategy return each time to get the **null distribution**  
- p-value = (1+#null >= observed) / (1+B)

### What to look for
- How wide the Sharpe CI is. Ten years of data still leaves you very unsure; a range like 0.0 to 1.2 is normal. Does it include 0?
- Whether the block CI is wider than the iid one (clustering adds real uncertainty).
- Whether the excess-vs-B&H CI straddles 0. In a mostly-bull decade, sitting in cash often costs return even when it improves drawdowns.
- The permutation p-values. Don’t be surprised if they’re unimpressive (> 0.05). That’s the honest answer, and Day 13 explains why it gets even harsher once you’ve tried many variants.

### Quiz  
1. Why does a plain iid bootstrap tend to understate the uncertainty of a daily strategy’s Sharpe, and what’s the fix?
2. You run 1,000 permutations and 23 of them produce a statistic ≥ your observed value. What’s the p-value?
3. Your block-bootstrap 95% CI for annualized Sharpe is [−0.10, 1.20]. Can you claim the Sharpe is positive at the 5% level? Which sorted values out of 2,000 boots form that CI?

### Answers
1. It shuffles days independently, which wipes out volatility clustering and autocorrelation. Calm and stormy days get mixed evenly, so each resample looks more “average” than real history can be. The fix is a block bootstrap (resample runs of consecutive days, e.g. 10–20 days long).
2. p = (1 + 23)/(1 + 1000) ≈ 0.024. The “+1” counts the observed result as one of the possibilities and prevents an impossible p = 0.
3. No. The interval includes 0, so a true Sharpe of 0 is consistent with the data. The CI is roughly the 50th and 1,950th sorted values (2.5% and 97.5% of 2,000).  

## Day 13: Multiple Testing & Data Snooping  

### Concept  
1. **Lots of tests produce false positives.**  
Test N independent useless strategies and
```
P(at least one false positive) = 1 − (1 − α)^N
N = 20 → 1 − 0.95²⁰ = 64%
N = 100 → 99.4%
```  
2. **Bonferroni correction (simple,strict).** Multiple each p-value by N, or equivalently use α/N as the bar.  
3. **The best Sharpe from luck alone.** If N skill-less strategies each have Sharpe ≈ 0 with standard error σ_SR, the best of them is roughly:
```
E[max SR] ≈ σ_SR × [(1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))], with γ ≈ 0.5772
```  
4. **Deflated Sharpe Ratio (Bailey & López de Prado).** First, the Probabilistic Sharpe Ratio (PSR): the probability that the true Sharpe exceeds a benchmark SR₀, adjusted for track length T, skew and kurtosis:
```
PSR = Φ( (SR − SR₀)·√(T−1) / √(1 − skew·SR + (kurt−1)/4·SR²) )
```
(SR here is per-period, e.g. daily, and kurt is raw, not excess.)
The DSR is just the PSR with SR₀ set to the expected max Sharpe from step 3. In plain words, it asks: “Does my winner beat the best result luck would give me from this many tries?” A DSR above about 0.95 is a good sign.  

### What to look for:
- The naive p-value of your winner is probably tiny. The Bonferroni one is much bigger.  
- How close is your best Sharpe to the noise median / 95th percentile? If it sits inside the noise range, your “edge” could easily be luck.  
- PSR vs DSR: the gap between them is what the 35 tries cost you. Note whether DSR clears 0.95.  
- Compare the winner to buy & hold of the same ticker. Long/flat rules on stocks that went up earn some of that drift for free, so zero isn’t the fair bar. (Tomorrow’s mini project tackles that.)  
- The average correlation is high, so the true number of independent tests is less than 35. Bonferroni overcorrects here; the noise test (which assumes independent strategies) is a little too harsh as well.  

### Quiz  
1. You backtest 50 independent strategies, none with real edge, at α = 0.05. What’s the chance at least one looks significant? What per-test p-value threshold would Bonferroni require?  
2. You tried 100 parameter combinations on 4 years of daily data. Roughly what annualized Sharpe would you expect the best one to show from luck alone?  
3. Your teammate reports: “PSR = 0.99, so the strategy is real.” What key question should you ask, and why might the DSR be far lower?  

### Answers  
1. 1 − 0.95⁵⁰ ≈ 92%. Bonferroni threshold = 0.05/50 = 0.001.  
2. σ_SR ≈ 1/√4 = 0.5. For N = 100 the bracket ≈ 2.53 → Sharpe ≈ 1.27 from pure noise.  
3. Ask “how many variants did you try?” PSR tests against SR₀ = 0, as if only one strategy was ever tested. If they picked the best of many, the right hurdle is the expected max Sharpe from that many trials. That raises SR₀ and can bring the DSR well below 0.95. Also check the track length and fat tails (negative skew and high kurtosis lower both PSR and DSR).  

## Day 14: Does MA crossover on SPY beat luck?  
Every backtest look like something, job is to find out if it is skill or noise before real money finds out for you.  

- **Correlation (D8)**: co-movement scaled to [-1, 1]. Not stable; it rises in crashes, exactly when you need diversification.
- **Regression (D9–10)**: beta = sensitivity to the market, alpha = what’s left over. Regress returns, never prices (spurious regression). Check residuals.
- **t-test (D11)**: t = mean / (sd/√N). Handy shortcut: t ≈ annual Sharpe × √years.
- **Bootstrap / permutation (D12)**: resample or scramble the data to see what “no edge” looks like, without assuming normality.
- **Data snooping (D13)**: test 20 ideas and the best one looks great by luck alone. Your p-value has to pay for every idea you tried.  

### What to look for

- Section 1: Did the crossover beat buy-and-hold on total return? On Sharpe? Being flat ~25–40% of the time usually lowers return but can lower volatility too. Note the trade count: it’s tiny, so you have very few independent “bets”.
- Sections 2–3: Is the “beats B&H” t-stat anywhere near 2? How wide is the Sharpe CI? If it straddles B&H’s Sharpe, you can’t tell them apart.
- Section 4: Where does the real Sharpe sit in the random-timing distribution? A p-value above 0.05 means random timing with the same exposure often did as well.
- Section 5: The key lesson. The best combo’s naive p will look much better than its max-of-grid p. The honest number is the one to believe.

### Quiz  
1. A strategy has a mean daily return of 0.03%, sd 1.0%, over 2,000 days. What’s the t-stat? Is it significant at 5%?
2. You tested 40 parameter combos. The best has p = 0.004. What’s its Bonferroni-adjusted p-value, and what’s your verdict?
3. Why test against circularly shifted positions instead of randomly shuffled daily positions?

### Answers
1. t = 0.0003 / (0.01/√2000) = 0.0003 / 0.000224 ≈ 1.34 (p ≈ 0.18). Not significant. About 8 years at an annual Sharpe of ~0.48 isn’t enough evidence.
2. 0.004 × 40 = 0.16, so it’s not significant. The result is consistent with being the luckiest of 40 tries.
3. Shuffling destroys the trade structure: the fake strategy would flip almost daily, with very different turnover and holding periods. Circular shifting keeps the same exposure, trade count and run lengths, so the only thing tested is timing, which is the skill the strategy claims to have.  

## Day 15: Autocorrelation, ACF/PACF & Random Walk  

Every momentum or mean-reversion strategy quietly assumes **past returns tell you something about future returns**. Autocorrelation measures that directly, if zero, a linear "yesterday predicts today" signal has nothing to work with, and any backtest that says otherwise is likely overfit.  

### Concept  
**Autocorrelation at lag k** is the correlation of a series with itself shifted k steps:  
`ρₖ = Σ (rₜ − r̄)(rₜ₋ₖ − r̄) / Σ (rₜ − r̄)²`
- ρ₁ > 0 → momentum (up days tend to follow up days)  
- ρ₁ < 0 → mean reversion (up days tend to follow down days)  

**ACF** is ρₖ plotted for k = 1, 2, 3…, and it includes indirect effects. PACF at lag k is the correlation with lag k after removing lags 1…k−1, so it shows only the direct link.  
**AR(1) model**: rₜ = φ·rₜ₋₁ + εₜ  
→ ACF decays like φᵏ, and PACF has a spike at lag 1 then is ~0. That shape is how you recognise it.  
**Random walk**: Pₜ = Pₜ₋₁ + εₜ (in log prices). Returns are just the noise εₜ, so the true ACF of returns is 0 at every lag. “Markets are close to a random walk” means exactly this.  
**Is it significant?** If the true ρ is 0, the sample ρₖ ≈ Normal(0, 1/T). The 95% band is ±1.96/√T. With T = 2,500 days (~10 yrs), that’s ±0.039.  
**Ljung-Box test** checks many lags jointly: Q = T(T+2) Σ ρₖ²/(T−k), compared against χ² with m degrees of freedom. A small p-value means some autocorrelation exists.  

### What to look for:

- ACF r: expect small values, often slightly negative at lag 1 for SPY/QQQ. A few may cross the band (marked *), mostly because of 2020. Look at how much the lag-1 number shrinks when 2020 is dropped.
- ACF |r|: should be far larger (often 0.2–0.4) and decay slowly. Compare it with the simulated random walk, where both columns are ≈ 0.
- Ljung-Box: the p-value on |returns| should be essentially 0. The p-value on returns is often borderline. Before calling anything “significant”, remember Day 13 (multiple testing): 10 lags × 3 tickers = 30 tests.
- Even a “significant” ρ₁ = −0.05 explains only ρ² = 0.25% of tomorrow’s variance, which is tiny once you pay trading costs (Day 21).

### Quiz
1. You have 2,500 daily returns and measure ρ₁ = −0.05. Is it statistically significant at 95%? Is it likely tradable?
2. An AR(1) process has φ = 0.3. What are the ACF and the PACF at lag 3?
3. A stock’s return ACF is ≈ 0 at all lags, but its |return| ACF is 0.3 at lag 1. Is it a random walk with i.i.d. steps? What can you forecast?

### Answers
1. The band is ±1.96/√2500 = ±0.039, and |−0.05| > 0.039, so it’s (just) significant. It’s probably not tradable: R² ≈ 0.0025, the result is fragile to a few crash days, and spreads and slippage eat a signal that small.
2. ACF at lag 3 = 0.3³ = 0.027. PACF at lag 3 = 0, because an AR(1) has only a direct lag-1 link.
3. No. The returns are uncorrelated but not independent, so the steps aren’t i.i.d. Volatility clusters, which means you can forecast the size of moves (risk) even if you can’t forecast their direction. That’s the basis for volatility targeting (Day 20) and GARCH models.  

## Day 16: Stationarity and the ADF test  

### Concept  
**Stationary** (weakly) means the mean, variance and the autocovariance at each lag stay the same over time. A stationary series keeps getting pulled back toward its mean. A non-stationary one can wander off and never come back.  

Simplest model that shows the difference is AR(1):
`x_t = φ·x_{t-1} + ε_t`, with ε having st. dev. σ  
- |φ| < 1 means the series is stationary. Its long-run variance is σ² / (1 − φ²), a finite number.  
- φ = 1 is a random walk, also called a “unit root”. After t steps the variance is t·σ², so it keeps growing without limit.  

The **ADF (Augmented Dickey-Fuller) test**. Subtract x_{t-1} from both sides of the AR(1) and add lagged differences to soak up autocorrelation:  
```
Δx_t = α + β·t + γ·x_{t-1} + Σ δ_i·Δx_{t-i} + e_t, where γ = φ − 1
```
- `H0: γ = 0`, meaning there’s a unit root (non-stationary).  
- `H1: γ < 0`, meaning the series is stationary.  
- The test statistic is the t-stat on γ. Under H0 it does not follow a normal or t distribution. It follows a Dickey-Fuller distribution, which sits further to the left. With a constant, the 5% critical value is about −2.86, not −1.65.  
- `regression="c"` adds a constant, used for returns. "ct" adds a constant plus a trend, used for prices that drift upward.  

**KPSS** tests it the other way around. **H0 is stationary.**. Running both is a good cross-check:

| ADF | KPSS | Verdict |  
| --- | --- | --- |  
| reject | don't reject | stationary |  
| don't reject | reject | unit root |  
| both reject or both don't |   | unclear, or not enough data |  

### What to look for:

- Log prices: the ADF p-value should be well above 0.05 and the KPSS p-value about 0.01. That’s the unit-root verdict.
- Log returns: the ADF stat should be hugely negative (around −15 to −50, p ≈ 0) and the KPSS p-value about 0.10. That’s the stationary verdict.
- Any ticker whose log price comes out “stationary”: GLD and TLT go through long regimes and are the likeliest. Ask yourself whether that’s real mean reversion or one lucky sample window.
- Power table: with φ = 1 the rejection rate should be about 5%, which is the test’s size working correctly. On a synthetic dry run with about 2,700 days, I got roughly 50% at φ = 0.995 and close to 100% at φ = 0.99. Try n = 500 and watch the power collapse. φ = 0.995 means a half-life of about 140 days, so slow mean reversion is very hard to detect.  

### Quiz
1. ADF on SPY log prices gives p = 0.40. Your friend says: “Proven, SPY is a random walk.” What’s wrong with that conclusion?  
2. A stationary AR(1) has φ = 0.8 and σ = 2. What is its long-run standard deviation? And what is the st. dev. of a random walk with σ = 2 after 25 days?  
3. Your ADF regression (with a constant) gives a t-stat on γ of −2.5. A colleague says this beats the one-sided 5% normal critical value of −1.65, so the series is stationary. Do you reject H0 at 5%?  

### Answers
1. Failing to reject H0 is not evidence that H0 is true. ADF has low power against near-unit-root processes, so a slowly mean-reverting series (φ = 0.995) often gives a large p-value too. The correct statement is: “We can’t distinguish SPY’s log price from a random walk with this data.” For trading purposes, that’s still a good reason not to build mean-reversion signals on raw prices.  
2. Variance = σ²/(1 − φ²) = 4/(1 − 0.64) = 4/0.36 = 11.11, so the st. dev. is ≈ 3.33. For the random walk: variance = 25 × 4 = 100, so the st. dev. is 10, and it keeps growing with √t.  
3. No. Under H0 the ADF stat follows the Dickey-Fuller distribution, not a normal or t. With a constant, the 5% critical value is about −2.86. Since −2.5 > −2.86, you fail to reject the unit root. Using normal critical values is a classic mistake that makes series look stationary when they aren’t.  

## Day 17: Mean Reversion and Half-Life  
Yesterday's ADF test tells whether a series mean-reverts. For trading you also need *how fast*. The half-life sets holding period, your z-score lookback, and your stop-out time.  

### Concept  
**Ornstein-Uhlenbeck (OU) Intuition**  
```
dx = θ(μ − x)dt + σ dW
```  
- θ = speed of reversion (bigger means faster)  
- σ = noise kicking it around  

**Discrete version (what you estimate)**. Regress the daily change on yesterday’s level:
```
Δx_t = c + λ·x_{t−1} + ε_t, with λ ≈ −θ
```  
- λ < 0 means it mean-reverts.
- λ ≈ 0 means it’s a random walk.

**Half-life**. This is the expected time for a deviation to shrink by half:
```
HL = −ln(2) / λ
```  
Two rules of thumb:  
1. Deviations decay geometrically. After 1 HL half the gap is left, after 2 HLs a quarter, after 3 HLs an eighth.  
2. The usual practice is to set your z-score lookback to roughly the half-life (or a small multiple of it).  

Caveats:  
- The t-stat on λ does not use normal critical values. That’s the Dickey-Fuller problem from Day 16: you need about −2.86 at 5%, not −1.96.  
- In finite samples λ is biased toward looking more negative, so half-lives tend to be underestimated.  
- Half-lives drift over time. Always check sub-periods.  

### What to look for

- Simulated OU: HL should come out near 13–14 days. This confirms the estimator works when the truth is known.  
- SPY log price: λ near 0 and t well above −2.86. The HL is huge or infinite, which is what a random walk looks like.  
- KO/PEP and XOM/CVX: these probably show finite half-lives. Check whether t actually clears −2.86 or only −1.96.  
- By-year table: how much does the HL jump around? That instability is the real risk in mean-reversion trading. 

### Quiz  
1. You estimate λ = −0.02 on a spread. What’s the half-life?  
2. A spread is 2σ above its mean and has a half-life of 10 days. With no new shocks, roughly where do you expect it after 20 days?  
3. On a stock’s log price you get λ = −0.004 with t = −2.1. Your friend says “significant at 5%, it mean-reverts, let’s trade it.” Give two reasons to push back.  

### Answers  
1. HL = 0.693 / 0.02 ≈ 34.7 days.
2. Two half-lives means a quarter of the gap is left: 2σ × 0.25 = 0.5σ.
3. (a) It’s a unit-root test, so the critical value is about −2.86, not −1.96. A t of −2.1 does not reject the random walk. (b) Even taken at face value, HL = 0.693 / 0.004 ≈ 173 days. That’s far too slow to trade, and the small-sample bias means the true HL is probably even longer. Bonus point: testing many stocks until one looks significant is data snooping (Day 13).