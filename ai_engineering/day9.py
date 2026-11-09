import asyncio, sys
from pathlib import Path
from claude_agent_sdk import (query, ClaudeAgentOptions, SystemMessage,
    AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock)

SERVER = str(Path(__file__).with_name("risk_server.py"))

options = ClaudeAgentOptions(
    # SDK spawns the server as a subprocess and talks MCP to it
    mcp_servers={"risk": {"type": "stdio",
                          "command": sys.executable, "args": [SERVER]}},
    allowed_tools=["mcp__risk__position_size"],  # mcp__<server>__<tool>
    tools=[],        # no built-ins, only our MCP tool
    model="haiku",   # cheap on your subscription
    max_turns=4,
)

PROMPT = ("I have $20,000. Size two longs at 1% risk: "
          "AAPL entry 230 stop 225, and TSLA entry 250 stop 260.")

async def main():
    async for msg in query(prompt=PROMPT, options=options):
        if isinstance(msg, SystemMessage) and msg.subtype == "init":
            print("MCP servers:", msg.data.get("mcp_servers"))
        elif isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f"→ {b.name} {b.input}")
                elif isinstance(b, TextBlock):
                    print("Claude:", b.text)
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    print(f"← error={b.is_error} {b.content}")
        elif isinstance(msg, ResultMessage):
            print(f"done: turns={msg.num_turns} cost≈${msg.total_cost_usd}")

asyncio.run(main())