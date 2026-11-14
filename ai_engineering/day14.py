import re, time
from typing import Literal
import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

mcp = MCPServer("market", instructions="Read-only daily market data.")
RO = ToolAnnotations(readOnlyHint=True, idempotentHint=True)
WATCHLIST = ["AAPL", "MSFT", "NVDA", "SPY", "1155.KL"]  # 1155.KL = Maybank
_cache = {}  # (symbol, period) -> (timestamp, df)

def _bars(symbol, period="6mo"):
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\-^=]{1,15}", symbol):
        raise ToolError(f"'{symbol}' is not a valid ticker. Use Yahoo format, e.g. AAPL or 1155.KL")
    key = (symbol, period)
    if key in _cache and time.time() - _cache[key][0] < 60:
        return _cache[key][1]
    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    if df.empty:  # an error the model can act on, not a stack trace
        raise ToolError(f"No data for {symbol}. Bursa stocks need .KL, e.g. 1155.KL")
    _cache[key] = (time.time(), df)
    return df

@mcp.tool(annotations=RO)
def get_quote(symbol: str) -> str:
    """Latest daily close and 1-day % change for ONE ticker (Yahoo format, e.g. AAPL, 1155.KL)."""
    df = _bars(symbol, "5d")
    last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
    return f"{symbol.upper()} close {last:.2f} on {df.index[-1].date()} ({(last/prev-1)*100:+.2f}% d/d)"

@mcp.tool(annotations=RO)
def get_bars_summary(symbol: str, period: Literal["1mo", "3mo", "6mo", "1y"] = "3mo") -> str:
    """Compact summary of daily bars: range, return, high/low, last 5 closes. Never raw rows."""
    df = _bars(symbol, period); c = df["Close"]
    tail = ", ".join(f"{v:.2f}" for v in c.tail(5))
    return (f"{symbol.upper()} {period}: {len(df)} bars {df.index[0].date()}→{df.index[-1].date()}, "
            f"return {(c.iloc[-1]/c.iloc[0]-1)*100:+.1f}%, high {df['High'].max():.2f}, "
            f"low {df['Low'].min():.2f}, last 5 [{tail}]")

@mcp.tool(annotations=RO)
def get_indicator(symbol: str, indicator: Literal["sma", "rsi"], window: int = 14) -> str:
    """Technical indicator on daily closes. sma = simple moving average; rsi = Wilder RSI (0-100).
    window: lookback in days, 2-200."""
    if not 2 <= window <= 200:
        raise ToolError("window must be between 2 and 200")
    c = _bars(symbol, "1y")["Close"]
    if indicator == "sma":
        return f"{symbol.upper()} SMA{window} = {c.rolling(window).mean().iloc[-1]:.2f} (close {c.iloc[-1]:.2f})"
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/window, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/window, adjust=False).mean()
    return f"{symbol.upper()} RSI{window} = {100 - 100/(1 + up.iloc[-1]/dn.iloc[-1]):.1f}"

@mcp.resource("watchlist://default", mime_type="text/plain")
def watchlist() -> str:
    """Default watchlist: a resource is data to read, not an action."""
    return "\n".join(WATCHLIST)

if __name__ == "__main__":
    mcp.run()  # stdio transport