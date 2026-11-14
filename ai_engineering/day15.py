# day15.py
import asyncio, time
from claude_agent_sdk import (query, ClaudeAgentOptions, AgentDefinition, tool,
    create_sdk_mcp_server, AssistantMessage, ToolUseBlock, ResultMessage)

# Fake quote tool (no network, no broker keys) so we only measure agent overhead.
QUOTES = {"AAPL": (231.4, 1.2), "MSFT": (418.9, -0.4), "NVDA": (142.7, 3.1)}

@tool("get_quote", "Get last price and % change today for one US stock ticker.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "enum": list(QUOTES)}},
       "required": ["symbol"]})
async def get_quote(args):
    p, chg = QUOTES[args["symbol"]]
    return {"content": [{"type": "text", "text": f"{args['symbol']} {p} ({chg:+}%)"}]}

server = create_sdk_mcp_server("mkt", "1.0.0", [get_quote])
TOOL = "mcp__mkt__get_quote"
TASK = "Get quotes for AAPL, MSFT and NVDA and give a one-line summary of each."

def single_agent():
    return ClaudeAgentOptions(
        mcp_servers={"mkt": server}, tools=[], allowed_tools=[TOOL],
        model="haiku", max_turns=6)

def multi_agent():
    # Lead can ONLY delegate; one worker subagent does the tool calls.
    return ClaudeAgentOptions(
        mcp_servers={"mkt": server},
        tools=["Agent"],                       # built-in subagent launcher
        allowed_tools=["Agent", TOOL],
        system_prompt="You are a lead. Delegate each ticker to the 'quoter' "
                      "subagent (one call per ticker), then combine the answers.",
        agents={"quoter": AgentDefinition(
            description="Fetches and summarizes one stock quote.",
            prompt="Use get_quote for the ticker you are given. Reply in one line.",
            tools=[TOOL], model="haiku")},
        model="haiku", max_turns=10)

async def run(label, opts):
    t0, calls = time.time(), []
    async for m in query(prompt=TASK, options=opts):
        if isinstance(m, AssistantMessage):
            calls += [b.name for b in m.content if isinstance(b, ToolUseBlock)]
        elif isinstance(m, ResultMessage):
            u = m.usage or {}
            print(f"\n=== {label} ===\n{m.result}")
            print(f"wall {time.time()-t0:.1f}s | turns {m.num_turns} | "
                  f"tool calls {calls}")
            print(f"input tok {u.get('input_tokens')} + cache read "
                  f"{u.get('cache_read_input_tokens')} | output {u.get('output_tokens')} | "
                  f"est. cost ${m.total_cost_usd or 0:.4f} (notional on a subscription)")

async def main():
    await run("SINGLE AGENT", single_agent())
    await run("LEAD + SUBAGENTS", multi_agent())

if __name__ == "__main__":
    asyncio.run(main())