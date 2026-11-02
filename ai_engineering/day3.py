# day3_results_errors.py — Tool design II: results, errors, idempotency, small outputs
import asyncio, json, random
from claude_agent_sdk import (
    query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
    AssistantMessage, UserMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock,
)

# ---- Fake data so the exercise is free and deterministic ----
random.seed(7)
def walk(start, drift):                # 250 fake daily closes (random walk)
    p, out = start, []
    for _ in range(250):
        p *= 1 + drift + random.gauss(0, 0.01); out.append(round(p, 2))
    return out
PRICES = {"AAPL": walk(190, 0.0), "MSFT": walk(410, 0.0003), "NVDA": walk(120, 0.002)}
ORDERS: dict[str, dict] = {}          # client_order_id -> order (our "broker")

def ok(data: dict) -> dict:
    """Success: small, structured JSON the model can reason over."""
    return {"content": [{"type": "text", "text": json.dumps(data)}]}

def err(msg: str) -> dict:
    """Failure: is_error=True + a message that tells the model how to recover."""
    return {"content": [{"type": "text", "text": msg}], "is_error": True}

@tool("get_price_summary",
      "Summarise recent daily closes for ONE US ticker. Returns stats, not raw rows. "
      "Use this before deciding on any order.",
      {"type": "object",
       "properties": {
           "symbol": {"type": "string", "description": "Ticker, e.g. AAPL"},
           "days": {"type": "integer", "minimum": 5, "maximum": 250, "default": 20},
       },
       "required": ["symbol"]})
async def get_price_summary(args):
    sym = args["symbol"].upper().strip()
    days = int(args.get("days", 20))
    if sym not in PRICES:
        # Actionable error: say what's valid so the model can retry correctly.
        return err(f"Unknown symbol '{sym}'. Supported: {sorted(PRICES)}.")
    closes = PRICES[sym][-days:]
    # Keep output SMALL: 250 rows would burn context; a summary is what the model needs.
    return ok({"symbol": sym, "days": days, "last": closes[-1],
               "min": min(closes), "max": max(closes),
               "change_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
               "last_5": closes[-5:]})

@tool("place_paper_order",
      "Place a PAPER market order. Idempotent: reusing the same client_order_id "
      "returns the existing order instead of creating a duplicate. "
      "Make the id from symbol+side+date, e.g. 'AAPL-buy-2026-11-02'.",
      {"type": "object",
       "properties": {
           "symbol": {"type": "string"},
           "side": {"type": "string", "enum": ["buy", "sell"]},
           "qty": {"type": "integer", "minimum": 1, "maximum": 100},
           "client_order_id": {"type": "string", "description": "Unique key for this intent"},
       },
       "required": ["symbol", "side", "qty", "client_order_id"]})
async def place_paper_order(args):
    cid = args["client_order_id"]
    if cid in ORDERS:                           # idempotency: safe to retry
        return ok({"status": "duplicate_ignored", "order": ORDERS[cid]})
    sym = args["symbol"].upper()
    if sym not in PRICES:
        return err(f"Unknown symbol '{sym}'. No order placed.")
    if args["qty"] > 100:                        # validate in code too, never trust the schema alone
        return err("qty above 100 limit. No order placed; ask the user before sizing up.")
    order = {"id": cid, "symbol": sym, "side": args["side"], "qty": args["qty"],
             "fill_price": PRICES[sym][-1], "status": "filled"}
    ORDERS[cid] = order
    return ok({"status": "created", "order": order})

server = create_sdk_mcp_server("broker", tools=[get_price_summary, place_paper_order])

async def main():
    options = ClaudeAgentOptions(
        model="haiku",                   # cheap model; keeps subscription usage low
        tools=[],                        # no built-in tools (Bash, Read...), only ours
        mcp_servers={"broker": server},
        allowed_tools=["mcp__broker__get_price_summary", "mcp__broker__place_paper_order"],
        max_turns=8,
    )
    prompt = ("Check TSLA and NVDA over 20 days. If NVDA is up, paper-buy 5 shares. "
              "Then, to test safety, submit the exact same NVDA order again.")
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock): print("AI  :", b.text)
                elif isinstance(b, ToolUseBlock): print("CALL:", b.name, b.input)
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    tag = "ERR :" if b.is_error else "OK  :"
                    print(tag, str(b.content)[:200])
        elif isinstance(msg, ResultMessage):
            print(f"\n[done] turns={msg.num_turns} cost=${msg.total_cost_usd}")
    print("Orders on 'broker':", len(ORDERS))   # should be 1, not 2

asyncio.run(main())