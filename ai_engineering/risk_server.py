from typing import Annotated, Literal
from pydantic import Field
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

mcp = MCPServer("risk", instructions="Position-sizing tools for equity trades.")

@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
def position_size(
    equity: Annotated[float, Field(gt=0, description="Account equity in USD")],
    entry: Annotated[float, Field(gt=0, description="Planned entry price")],
    stop: Annotated[float, Field(gt=0, description="Stop-loss price")],
    risk_pct: Annotated[float, Field(gt=0, le=5, description="% of equity to risk")] = 1.0,
    side: Literal["long", "short"] = "long",
) -> dict:
    """Shares to trade so hitting the stop loses risk_pct of equity.
    Use before proposing any trade size."""
    per_share = entry - stop if side == "long" else stop - entry
    if per_share <= 0:  # model receives is_error=True, not a crash
        raise ToolError(f"For a {side}, stop must be "
                        f"{'below' if side == 'long' else 'above'} entry.")
    risk_usd = equity * risk_pct / 100
    shares = int(risk_usd // per_share)
    return {"shares": shares, "risk_usd": round(risk_usd, 2),
            "notional_usd": round(shares * entry, 2)}

@mcp.resource("risk://rules", mime_type="text/markdown")
def rules() -> str:
    """House risk rules (read-only context)."""
    return "- Max 1% risk per trade\n- Max 5 open positions"

@mcp.prompt()
def trade_review(ticker: str) -> str:
    """Template: review a trade idea."""
    return f"Review a trade for {ticker}. Read risk://rules, then size it."

if __name__ == "__main__":
    mcp.run()  # stdio by default. No print() to stdout!