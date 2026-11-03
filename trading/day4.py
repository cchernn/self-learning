import os
from datetime import datetime, timedelta, timezone
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment, DataFeed

client = StockHistoricalDataClient(os.environ["ALPACA_API_KEY"],
                                   os.environ["ALPACA_SECRET_KEY"])
tickers = ["SPY", "QQQ", "AAPL", "TLT"]
req = StockBarsRequest(
    symbol_or_symbols=tickers, timeframe=TimeFrame.Day,
    start=datetime(2016, 1, 1, tzinfo=timezone.utc),
    end=datetime.now(timezone.utc) - timedelta(days=1),  # free plan: no recent SIP
    adjustment=Adjustment.ALL,   # split+dividend adjusted -> total-return-ish
    feed=DataFeed.SIP)           # switch to DataFeed.IEX if SIP errors
px = client.get_stock_bars(req).df["close"].unstack(level=0).dropna()

def drawdown_stats(p):
    wealth = p / p.iloc[0]
    peak = wealth.cummax()
    dd = wealth / peak - 1                       # drawdown series
    trough = dd.idxmin()
    peak_date = wealth.loc[:trough].idxmax()     # peak before worst trough
    after = wealth.loc[trough:]
    rec = after[after >= peak.loc[trough]]       # first new high after trough
    rec_date = rec.index[0].date() if len(rec) else "not yet"
    underwater = dd < 0
    spell = (~underwater).cumsum()               # id for each underwater spell
    longest = int(underwater.groupby(spell).sum().max())
    stats = {
        "max_dd": round(dd.min(), 3),
        "gain_to_recover": round(1 / (1 + dd.min()) - 1, 3),
        "peak": peak_date.date(), "trough": trough.date(),
        "recovered": rec_date,
        "longest_uw_days": longest,              # trading days
        "pct_time_uw": round(underwater.mean(), 2),
        "current_dd": round(dd.iloc[-1], 3)}
    return stats, dd

pd.set_option("display.width", 200)
table = {s: drawdown_stats(px[s])[0] for s in tickers}
print(pd.DataFrame(table).T)

# Top 3 SPY drawdown episodes
_, dd = drawdown_stats(px["SPY"])
uw = dd < 0
sid = (~uw).cumsum()
eps = [{"start": g.index[0].date(), "trough": g.idxmin().date(),
        "end": g.index[-1].date(), "depth": round(g.min(), 3),
        "days": len(g)} for _, g in dd[uw].groupby(sid[uw])]
print("\nSPY worst 3 episodes:")
print(pd.DataFrame(eps).sort_values("depth").head(3).to_string(index=False))