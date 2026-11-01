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