# day8_mcp.py: in-process + external stdio MCP servers
# pip install claude-agent-sdk ; needs `uvx` on PATH
# Auth: subscription login. Keep ANTHROPIC_API_KEY UNSET.
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions, tool, create_sdk_mcp_server,
    AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

# --- Server 1: in-process SDK server (like Days 1-3) ---
NOTES: list[str] = []

@tool("save_note", "Save a one-line note. Key facts only.",
      {"type": "object",
       "properties": {"text": {"type": "string", "maxLength": 200}},
       "required": ["text"]})
async def save_note(args):
    NOTES.append(args["text"])
    return {"content": [{"type": "text",
                         "text": f"saved (#{len(NOTES)})"}]}

notes_server = create_sdk_mcp_server(
    name="notes", version="1.0.0", tools=[save_note])

options = ClaudeAgentOptions(
    model="haiku",   # cheap; enough here
    tools=[],        # no built-ins: MCP only
    max_turns=6,
    mcp_servers={
        "notes": notes_server,          # in-process
        "fetch": {                      # subprocess, stdio
            "type": "stdio",
            "command": "uvx",
            "args": ["mcp-server-fetch"],
        },
    },
    # always mcp__<server key>__<tool name>
    allowed_tools=["mcp__notes__save_note",
                   "mcp__fetch__fetch"],
)

async def main():
    async with ClaudeSDKClient(options=options) as client:
        # 1) Discovery: what each handshake reported
        status = await client.get_mcp_status()
        for s in status["mcpServers"]:
            names = [t["name"] for t in s.get("tools", [])]
            print(f"[server] {s['name']}: {s['status']}"
                  f" tools={names}", s.get("error", ""))

        # 2) A task that needs both servers
        await client.query(
            "Fetch https://modelcontextprotocol.io/introduction "
            "and save 2 short notes on what MCP is. "
            "Then reply in one sentence.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        print(f"[call] {b.name} {str(b.input)[:80]}")
                    elif isinstance(b, TextBlock):
                        print(f"[text] {b.text}")
            elif isinstance(msg, UserMessage) and \
                    isinstance(msg.content, list):
                for b in msg.content:
                    if isinstance(b, ToolResultBlock):
                        print(f"[result] {str(b.content)[:80]}...")
            elif isinstance(msg, ResultMessage):
                print(f"[done] turns={msg.num_turns} "
                      f"cost=${msg.total_cost_usd}")
    print("NOTES:", NOTES)

asyncio.run(main())