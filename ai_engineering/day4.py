import asyncio, time
from claude_agent_sdk import (
    query, ClaudeAgentOptions, tool, create_sdk_mcp_server, ToolAnnotations,
    HookMatcher, AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

T0 = time.monotonic()
def ts():  # seconds since start, so you can see overlap
    return f"{time.monotonic() - T0:5.1f}s"

PRICES = {"AAPL": 231.4, "MSFT": 512.8, "NVDA": 189.2}  # fake data
calls = {"MSFT": 0}

# readOnlyHint=True: no side effects, so calls may run concurrently
RO = ToolAnnotations(readOnlyHint=True)

@tool("get_price", "Get the latest USD price for one stock ticker.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "description": "Ticker, e.g. AAPL"}},
       "required": ["symbol"]},
      annotations=RO)
async def get_price(args):
    sym = args["symbol"].upper()
    await asyncio.sleep(1.0)                  # pretend network latency
    if sym == "MSFT":
        calls["MSFT"] += 1
        if calls["MSFT"] == 1:                # fail once -> watch the model retry
            return {"content": [{"type": "text",
                    "text": "Rate limited (429). Safe to retry once."}], "is_error": True}
    if sym not in PRICES:
        return {"content": [{"type": "text", "text": f"Unknown symbol {sym}"}], "is_error": True}
    return {"content": [{"type": "text", "text": f"{sym} {PRICES[sym]} USD"}]}

@tool("get_fx_rate", "Get the FX rate for a currency pair like USDMYR.",
      {"type": "object",
       "properties": {"pair": {"type": "string", "enum": ["USDMYR", "USDSGD"]}},
       "required": ["pair"]},
      annotations=RO)
async def get_fx_rate(args):
    await asyncio.sleep(1.0)
    return {"content": [{"type": "text", "text": f"{args['pair']} 4.21"}]}

server = create_sdk_mcp_server("mkt", "1.0.0", tools=[get_price, get_fx_rate])

# Hooks run around every tool call. Returning {} means "carry on".
async def pre(inp, tool_use_id, ctx):
    print(f"  [{ts()}] PRE  {inp['tool_name']} {inp['tool_input']}")
    return {}

async def post(inp, tool_use_id, ctx):
    print(f"  [{ts()}] POST {inp['tool_name']}")
    return {}

async def main():
    opts = ClaudeAgentOptions(
        mcp_servers={"mkt": server},
        allowed_tools=["mcp__mkt__get_price", "mcp__mkt__get_fx_rate"],
        tools=[],                 # no built-in tools
        model="haiku",            # cheap for experiments
        max_turns=6,              # hard cap on model<->tool round trips
        system_prompt="You are a terse market assistant. Fetch everything you "
                      "need in parallel when the calls are independent.",
        hooks={
            "PreToolUse":  [HookMatcher(matcher="mcp__mkt__.*", hooks=[pre])],
            "PostToolUse": [HookMatcher(matcher="mcp__mkt__.*", hooks=[post])],
        },
    )
    turn = 0
    async for msg in query(prompt="What are AAPL, MSFT and NVDA worth in MYR?",
                           options=opts):
        if isinstance(msg, AssistantMessage):
            turn += 1
            uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]
            print(f"\n[{ts()}] TURN {turn}: model asked for {len(uses)} tool call(s)")
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print("  text:", b.text[:200])
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    flag = "ERROR" if b.is_error else "ok"
                    print(f"  result ({flag}): {str(b.content)[:80]}")
        elif isinstance(msg, ResultMessage):
            print(f"\n=== DONE subtype={msg.subtype} turns={msg.num_turns} "
                  f"stop_reason={msg.stop_reason} time={msg.duration_ms}ms "
                  f"cost=${msg.total_cost_usd}")

if __name__ == "__main__":
    asyncio.run(main())