# day5_context.py
# Run: python day5_context.py           (compact tool output)
#      VERBOSE=1 python day5_context.py (raw bars into context)
# Reminder: keep ANTHROPIC_API_KEY unset so your subscription is used.
import asyncio, json, os, random
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions, HookMatcher,
    tool, create_sdk_mcp_server, ResultMessage,
)

VERBOSE = os.getenv("VERBOSE") == "1"

def fake_bars(symbol: str, days: int):
    random.seed(symbol)                  # deterministic per symbol
    px, bars = 100.0, []
    for d in range(days):
        o = px; px *= 1 + random.gauss(0, 0.015)
        bars.append({"day": d, "o": round(o, 2),
                     "h": round(max(o, px) * 1.004, 2),
                     "l": round(min(o, px) * 0.996, 2),
                     "c": round(px, 2),
                     "v": random.randint(1_000_000, 5_000_000)})
    return bars

@tool("get_price_history",
      "Daily OHLCV for a ticker. Returns a compact summary "
      "(first/last close, % change, high, low, max drawdown).",
      {"type": "object",
       "properties": {"symbol": {"type": "string"},
                      "days": {"type": "integer", "minimum": 5, "maximum": 250}},
       "required": ["symbol", "days"]})
async def get_price_history(args):
    bars = fake_bars(args["symbol"].upper(), args["days"])
    if VERBOSE:   # lazy tool: every bar goes into context
        text = json.dumps(bars)
    else:         # engineered tool: summarise at the source
        closes = [b["c"] for b in bars]
        peak, mdd = closes[0], 0.0
        for c in closes:
            peak = max(peak, c); mdd = min(mdd, c / peak - 1)
        text = json.dumps({
            "symbol": args["symbol"].upper(), "days": len(bars),
            "first": closes[0], "last": closes[-1],
            "chg_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
            "high": max(b["h"] for b in bars),
            "low": min(b["l"] for b in bars),
            "max_dd_pct": round(mdd * 100, 2)})
    return {"content": [{"type": "text", "text": text}]}

# Hooks let you SEE context events the SDK handles for you
async def on_post_tool(input_data, tool_use_id, context):
    size = len(str(input_data.get("tool_response")))
    print(f"   [hook] tool put ~{size:,} chars into context")
    return {}

async def on_compact(input_data, tool_use_id, context):
    print(f"   [hook] COMPACTION ({input_data['trigger']})")
    return {}

server = create_sdk_mcp_server("market", "1.0.0", [get_price_history])

options = ClaudeAgentOptions(
    model="haiku",            # cheap: today is about tokens
    system_prompt="You are a concise market analyst. "
                  "Answer in 2 sentences.",   # stable → cacheable
    tools=[],                 # no built-ins → smaller prefix
    mcp_servers={"market": server},
    allowed_tools=["mcp__market__get_price_history"],
    max_turns=4,
    hooks={"PostToolUse": [HookMatcher(hooks=[on_post_tool])],
           "PreCompact":  [HookMatcher(hooks=[on_compact])]},
)

QUESTIONS = [   # one session → context accumulates
    "How did AAPL do over the last 200 days?",
    "Now compare MSFT over the same window.",
    "Which had the worse drawdown? One line.",
]

async def main():
    print("Mode:", "VERBOSE" if VERBOSE else "COMPACT", "\n")
    async with ClaudeSDKClient(options=options) as client:
        for q in QUESTIONS:
            print(f"> {q}")
            await client.query(q)
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    u = msg.usage or {}
                    print(f"   answer: {msg.result}")
                    print(f"   in={u.get('input_tokens')} "
                          f"cache_write={u.get('cache_creation_input_tokens')} "
                          f"cache_read={u.get('cache_read_input_tokens')} "
                          f"out={u.get('output_tokens')}\n")

asyncio.run(main())