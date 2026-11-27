# day28_portable.py
import asyncio, json
from claude_agent_sdk import (query, ClaudeAgentOptions, tool,
    create_sdk_mcp_server, AssistantMessage, ToolUseBlock, ResultMessage)

# 1. CORE: plain Python, no framework imports
PRICES = {"AAPL": 231.4, "MSFT": 418.9, "NVDA": 141.2}  # fake data

def get_price(symbol: str) -> dict:
    sym = symbol.upper()
    if sym not in PRICES:
        raise ValueError(f"Unknown symbol {sym}. Known: {sorted(PRICES)}")
    return {"symbol": sym, "price": PRICES[sym]}

def position_value(symbol: str, qty: float) -> dict:
    p = get_price(symbol)
    return {**p, "qty": qty, "value": round(p["price"] * qty, 2)}

SPECS = [  # (function, description, JSON Schema)
  (get_price, "Latest price for one stock symbol.",
   {"type": "object", "properties": {"symbol": {"type": "string"}},
    "required": ["symbol"]}),
  (position_value, "Market value of holding qty shares of symbol.",
   {"type": "object", "properties": {"symbol": {"type": "string"},
    "qty": {"type": "number"}}, "required": ["symbol", "qty"]}),
]

# 2. ADAPTER: the ONLY Claude-specific code
def to_sdk_tool(fn, desc, schema):
    @tool(fn.__name__, desc, schema)
    async def _wrapped(args):
        try:
            out = fn(**args)
            return {"content": [{"type": "text", "text": json.dumps(out)}]}
        except Exception as e:  # errors go back to the model
            return {"content": [{"type": "text", "text": str(e)}],
                    "is_error": True}
    return _wrapped

sdk_tools = [to_sdk_tool(*s) for s in SPECS]
server = create_sdk_mcp_server(name="port", tools=sdk_tools)

# 3. RUN: the framework owns the loop
async def main():
    opts = ClaudeAgentOptions(
        mcp_servers={"port": server},
        allowed_tools=[f"mcp__port__{fn.__name__}" for fn, *_ in SPECS],
        tools=[], model="haiku", max_turns=6,
        system_prompt="Portfolio helper. Use tools; never guess prices.")
    q = "I hold 10 NVDA and 3 TSLA. What are they worth?"
    async for msg in query(prompt=q, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print("TOOL →", b.name, b.input)
        elif isinstance(msg, ResultMessage):
            print("\nANSWER:", msg.result)
            print(f"turns={msg.num_turns} cost≈${msg.total_cost_usd}")

if __name__ == "__main__":
    print("core test:", position_value("aapl", 2))  # no model needed
    asyncio.run(main())