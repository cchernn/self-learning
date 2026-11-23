# day24_cost.py — compare model tiers on the same small task and read
# the cost/latency fields on ResultMessage. Uses your subscription login.
import asyncio, time
from claude_agent_sdk import (
    query, ClaudeAgentOptions, ResultMessage, tool, create_sdk_mcp_server,
)

# Tiny fake market-data tool (swap in your Day 14 MCP server if you like)
@tool("get_closes", "Get the last 5 daily closing prices for a stock symbol.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "description": "Ticker, e.g. AAPL"}},
       "required": ["symbol"]})
async def get_closes(args):
    fake = {"AAPL": [228.1, 230.4, 229.9, 233.2, 235.0],
            "MSFT": [415.2, 412.8, 418.0, 421.5, 419.9]}
    closes = fake.get(args["symbol"].upper())
    if closes is None:
        return {"content": [{"type": "text", "text": f"Unknown symbol {args['symbol']}"}],
                "is_error": True}
    return {"content": [{"type": "text", "text": f"{args['symbol'].upper()}: {closes}"}]}

server = create_sdk_mcp_server("mkt", "1.0.0", [get_closes])
PROMPT = "Fetch AAPL and MSFT closes, then say in one sentence which rose more (%)."

async def run(label, model, effort=None, budget=None):
    opts = ClaudeAgentOptions(
        model=model,
        effort=effort,                 # less thinking = fewer tokens, faster
        max_budget_usd=budget,         # hard stop -> subtype 'error_max_budget_usd'
        max_turns=6,                   # early stop for loops
        tools=[],                      # no built-in tools: smaller prompt
        mcp_servers={"mkt": server},
        allowed_tools=["mcp__mkt__get_closes"],
        system_prompt="You are a terse market assistant. Call tools in parallel when possible.",
    )
    t0 = time.perf_counter()
    async for msg in query(prompt=PROMPT, options=opts):
        if isinstance(msg, ResultMessage):
            u = msg.usage or {}
            print(f"\n=== {label} ({msg.subtype}) ===")
            print("answer   :", (msg.result or "")[:120])
            print(f"wall {time.perf_counter()-t0:.1f}s | api {msg.duration_api_ms/1000:.1f}s"
                  f" | turns {msg.num_turns}")
            print(f"tokens in {u.get('input_tokens')} out {u.get('output_tokens')}"
                  f" | cache write {u.get('cache_creation_input_tokens')}"
                  f" read {u.get('cache_read_input_tokens')}")
            print(f"est. cost ${msg.total_cost_usd or 0:.4f}")
            for m, mu in (msg.model_usage or {}).items():   # per-model split
                print(f"   {m}: in {mu['inputTokens']} out {mu['outputTokens']}"
                      f" ${mu['costUSD']:.4f}")

async def main():
    await run("sonnet", "sonnet")
    await run("haiku", "haiku")
    await run("haiku again (cache warm?)", "haiku")
    await run("tiny budget", "sonnet", budget=0.001)

if __name__ == "__main__":
    asyncio.run(main())