import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (StockQuotesRequest,
    StockTradesRequest, StockBarsRequest)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

client = StockHistoricalDataClient(
    os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])

NY = ZoneInfo("America/New_York")
DAY = "2026-11-18"   # any recent trading day
start = datetime.fromisoformat(f"{DAY}T10:00").replace(tzinfo=NY)
end   = start + timedelta(minutes=15)
# SIP = all exchanges. Free plans can read SIP history older
# than 15 min. If you get a permission error, use DataFeed.IEX
# (IEX-only book, so spreads will look wider).
FEED = DataFeed.SIP
SYMBOLS = ["SPY", "QQQ", "AAPL", "TSLA", "PLUG"]  # PLUG = less liquid
ORDER_USD = 1_000_000

def one(sym):
    q = client.get_stock_quotes(StockQuotesRequest(
        symbol_or_symbols=sym, start=start, end=end, feed=FEED)).df
    q = q.xs(sym, level="symbol").sort_index()
    q = q[(q.bid_price > 0) & (q.ask_price > q.bid_price)]  # drop bad/crossed
    q["mid"] = (q.bid_price + q.ask_price) / 2
    q["spr_bps"] = (q.ask_price - q.bid_price) / q.mid * 1e4
    q = q[q.spr_bps < 500]                                   # drop junk quotes

    # Time-weighted: each quote counts for as long as it was live
    dur = q.index.to_series().diff().shift(-1).dt.total_seconds().fillna(0)
    tw_spread = np.average(q.spr_bps, weights=dur + 1e-9)

    # Effective spread: match each trade to the quote just before it
    t = client.get_stock_trades(StockTradesRequest(
        symbol_or_symbols=sym, start=start, end=end, feed=FEED)).df
    t = t.xs(sym, level="symbol").sort_index()
    m = pd.merge_asof(t[["price", "size"]], q[["mid"]],
                      left_index=True, right_index=True,
                      direction="backward").dropna()
    m["eff_bps"] = 2 * (m.price - m.mid).abs() / m.mid * 1e4
    eff = np.average(m.eff_bps, weights=m["size"])

    # Impact: square-root law using 1y of daily bars
    b = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=sym, timeframe=TimeFrame.Day,
        start=start - timedelta(days=365), end=start)).df.xs(sym)
    sigma = np.log(b.close).diff().std()
    adv_usd = (b.close * b.volume).tail(20).mean()
    impact = sigma * np.sqrt(ORDER_USD / adv_usd) * 1e4

    return dict(sym=sym, quotes=len(q), trades=len(m),
                median_spr=q.spr_bps.median(), tw_spr=tw_spread,
                eff_spr=eff, impact_1M=impact,
                pct_ADV=100 * ORDER_USD / adv_usd)

res = pd.DataFrame([one(s) for s in SYMBOLS]).set_index("sym")
pd.set_option("display.width", 120)
print(res.round(2))

# Annual cost drag = round trips/year x cost per round trip
print("\nAnnual cost drag (%), cost/round trip = eff spread + 1 bp slippage")
for f, n in [("daily", 252), ("weekly", 52), ("monthly", 12)]:
    print(f, (n * (res.eff_spr + 1) / 100).round(2).to_dict())