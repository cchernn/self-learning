# day6_system_prompts.py — same tools, two system prompts, compare.
# Run: python day6_system_prompts.py  (ANTHROPIC_API_KEY must be UNSET)
import asyncio
from claude_agent_sdk import (
    query, tool, create_sdk_mcp_server, ClaudeAgentOptions,
    AssistantMessage, ResultMessage, TextBlock, ToolUseBlock,
)

# Fake data so runs are cheap and repeatable
PRICES = {"AAPL": 231.4, "NVDA": 142.8, "MSFT": 418.2}
POSITIONS = {"AAPL": 20, "NVDA": 50}  # no MSFT held

@tool("get_positions",
      "List the user's current holdings as SYMBOL: shares.", {})
async def get_positions(args):
    text = "\n".join(f"{s}: {q}" for s, q in POSITIONS.items())
    return {"content": [{"type": "text", "text": text}]}

@tool("get_price", "Latest price for one US stock ticker.",
      {"type": "object",
       "properties": {"symbol": {"type": "string",
                                 "description": "e.g. AAPL"}},
       "required": ["symbol"]})
async def get_price(args):
    sym = args["symbol"].upper()
    if sym not in PRICES:
        return {"content": [{"type": "text",
                             "text": f"Unknown symbol {sym}"}],
                "is_error": True}
    return {"content": [{"type": "text",
                         "text": f"{sym} {PRICES[sym]}"}]}

server = create_sdk_mcp_server(
    "broker", tools=[get_positions, get_price])

# Prompt A: a one-liner
BARE = "You are a helpful trading assistant."

# Prompt B: role + rules + plan + output contract
PLANNED = """You are a portfolio assistant for one retail trader.

## Rules
- Never guess prices or holdings. Every number must come from a tool.
- Only price symbols the user actually holds unless asked otherwise.
- Read-only: you cannot place orders. If asked to trade, say so.

## Plan (follow in order)
1. Call get_positions once.
2. Call get_price for each held symbol (in parallel is fine).
3. Compute value = shares * price per holding, and the total.
4. Stop. Do not call tools again after step 2.

## Output
A markdown table: Symbol | Shares | Price | Value, then one line
'Total: $X'. No other commentary."""

async def run(label, system_prompt):
    print(f"\n===== {label} =====")
    opts = ClaudeAgentOptions(
        system_prompt=system_prompt,  # string REPLACES default prompt
        mcp_servers={"broker": server},
        allowed_tools=["mcp__broker__get_positions",
                       "mcp__broker__get_price"],
        tools=[],          # no built-in Bash/Read/etc.
        max_turns=6,
        model="haiku",     # cheap for experiments
    )
    task = "What's my portfolio worth? Also, should I buy MSFT?"
    async for msg in query(prompt=task, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    name = b.name.split("__")[-1]
                    print(f"  -> tool {name}({b.input})")
                elif isinstance(b, TextBlock):
                    print(b.text)
        elif isinstance(msg, ResultMessage):
            cost = msg.total_cost_usd or 0
            print(f"  [turns={msg.num_turns} cost=${cost:.4f}]")

async def main():
    await run("A: bare prompt", BARE)
    await run("B: planned prompt", PLANNED)

asyncio.run(main())