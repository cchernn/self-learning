"""Day 12: short-term memory (session resume) vs long-term memory (a JSON file tool).
Run:  python day12_memory.py   (ANTHROPIC_API_KEY must be UNSET -> uses your subscription)
"""
import asyncio, json, pathlib, datetime
from claude_agent_sdk import (query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
                              AssistantMessage, TextBlock, ToolUseBlock, ResultMessage)

MEM_FILE = pathlib.Path("agent_memory.json")

def load() -> dict:
    return json.loads(MEM_FILE.read_text()) if MEM_FILE.exists() else {}

# ---------- Long-term memory tools ----------
@tool("remember",
      "Save ONE durable fact about the user (a preference, rule, or account setting) "
      "so future sessions can use it. Do NOT save one-off chit-chat or today's prices. "
      "Saving the same key again overwrites it.",
      {"type": "object",
       "properties": {
           "key": {"type": "string", "description": "short snake_case id, e.g. 'risk_per_trade'"},
           "value": {"type": "string", "description": "the fact, one sentence"},
           "category": {"type": "string", "enum": ["preference", "rule", "account"]}},
       "required": ["key", "value", "category"]})
async def remember(args):
    mem = load()
    mem[args["key"]] = {"value": args["value"], "category": args["category"],
                        "saved": datetime.date.today().isoformat()}
    MEM_FILE.write_text(json.dumps(mem, indent=2))       # idempotent: same key = overwrite
    return {"content": [{"type": "text", "text": f"saved {args['key']}"}]}

@tool("recall",
      "Look up saved facts about the user. Call this BEFORE answering anything that "
      "depends on their preferences or rules. Optional category filter.",
      {"type": "object",
       "properties": {"category": {"type": "string", "enum": ["preference", "rule", "account"]}},
       "required": []})
async def recall(args):
    mem = load()
    cat = args.get("category")
    hits = {k: v["value"] for k, v in mem.items() if not cat or v["category"] == cat}
    return {"content": [{"type": "text", "text": json.dumps(hits) if hits else "no memories"}]}

server = create_sdk_mcp_server("memory", tools=[remember, recall])

def opts(**kw) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model="haiku", tools=[], max_turns=4,
        mcp_servers={"memory": server},
        allowed_tools=["mcp__memory__remember", "mcp__memory__recall"],
        system_prompt="You are a trading assistant. Use recall before giving advice "
                      "that depends on the user's rules. Use remember for durable facts only.",
        **kw)

async def run(label: str, prompt: str, **kw) -> str | None:
    print(f"\n=== {label} ===\nUSER: {prompt}")
    sid = None
    async for m in query(prompt=prompt, options=opts(**kw)):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock): print("AGENT:", b.text)
                if isinstance(b, ToolUseBlock): print("  -> tool:", b.name, b.input)
        elif isinstance(m, ResultMessage):
            sid = m.session_id
            print(f"  [session={sid[:8]} turns={m.num_turns}]")
    return sid

async def main():
    MEM_FILE.unlink(missing_ok=True)   # start clean each run

    # 1) Short-term: conversation lives in a session transcript
    sid = await run("A: new session", "Hi! I trade US tech stocks and never risk more than 1% per trade.")
    await run("B: RESUMED session", "What's my max risk per trade?", resume=sid)
    await run("C: FRESH session (no resume)", "What's my max risk per trade?")

    # 2) Long-term: what the agent chose to write to disk survives any session
    print("\nMemory file now contains:\n", MEM_FILE.read_text() if MEM_FILE.exists() else "(empty)")

if __name__ == "__main__":
    asyncio.run(main())