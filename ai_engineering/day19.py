"""Day 19: router + specialists + handoffs (Claude Agent SDK, subscription auth)."""
import asyncio, sys
from claude_agent_sdk import (query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
                              AssistantMessage, TextBlock, ToolUseBlock, ResultMessage)

SPECIALISTS = ["quant", "coder", "general"]

# ---------- 1. ROUTER: cheap model, no tools, forced JSON output ----------
ROUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": SPECIALISTS},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": ["route", "confidence", "reason"],
}

async def route(user_msg: str) -> dict:
    opts = ClaudeAgentOptions(
        model="haiku", tools=[], max_turns=3,
        system_prompt=(
            "You are a request router. Pick ONE specialist:\n"
            "- quant: prices, returns, market data questions\n"
            "- coder: writing/debugging Python trading code\n"
            "- general: anything else\n"
            "Be honest about confidence."),
        output_format={"type": "json_schema", "schema": ROUTE_SCHEMA},
    )
    async for m in query(prompt=user_msg, options=opts):
        if isinstance(m, ResultMessage) and m.structured_output:
            return m.structured_output
    return {"route": "general", "confidence": 0.0, "reason": "router failed"}  # safe fallback

# ---------- 2. Tools: one real tool + the HANDOFF tool ----------
FAKE_PRICES = {"AAPL": 231.4, "NVDA": 141.2, "MSFT": 418.9}

@tool("get_price", "Latest price for a US stock ticker.",
      {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]})
async def get_price(args):
    t = args["ticker"].upper()
    if t not in FAKE_PRICES:
        return {"content": [{"type": "text", "text": f"Unknown ticker {t}"}], "is_error": True}
    return {"content": [{"type": "text", "text": f"{t}: {FAKE_PRICES[t]}"}]}

pending_handoff: dict = {}  # filled by the handoff tool, read by our control loop

@tool("handoff",
      "Transfer the user to another specialist when the request is outside your role. "
      "Write a self-contained summary: the next agent sees ONLY this, not the chat.",
      {"type": "object",
       "properties": {"to": {"type": "string", "enum": SPECIALISTS},
                      "summary": {"type": "string",
                                  "description": "What the user wants + facts gathered so far"}},
       "required": ["to", "summary"]})
async def handoff(args):
    pending_handoff.update(args)
    return {"content": [{"type": "text", "text": "Handoff recorded. Stop now; reply only 'Transferring.'"}]}

server = create_sdk_mcp_server("desk", tools=[get_price, handoff])

# ---------- 3. Specialists: own prompt, own tools, own model ----------
SPEC = {
    "quant":   {"model": "haiku",  "tools": ["mcp__desk__get_price", "mcp__desk__handoff"],
                "prompt": "You answer market-data questions using get_price. You do NOT write code."},
    "coder":   {"model": "sonnet", "tools": ["mcp__desk__handoff"],
                "prompt": "You write short pandas trading code. You have no live data access."},
    "general": {"model": "haiku",  "tools": ["mcp__desk__handoff"],
                "prompt": "You answer general questions briefly."},
}
COMMON = "\nIf the task (or part of it) belongs to another specialist, call handoff instead of guessing."

async def run_specialist(name: str, task: str) -> None:
    s = SPEC[name]
    opts = ClaudeAgentOptions(model=s["model"], system_prompt=s["prompt"] + COMMON,
                              mcp_servers={"desk": server}, tools=[],
                              allowed_tools=s["tools"], max_turns=5)
    async for m in query(prompt=task, options=opts):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    print(f"  [{name}] {b.text}")
                elif isinstance(b, ToolUseBlock):
                    print(f"  [{name}] -> {b.name} {b.input}")

# ---------- 4. Control loop: route once, then follow handoffs (bounded) ----------
async def main(user_msg: str, max_handoffs: int = 2):
    r = await route(user_msg)
    print(f"ROUTER: {r}")
    agent = r["route"] if r["confidence"] >= 0.6 else "general"   # low confidence -> safe default
    task, visited = user_msg, []
    for _ in range(max_handoffs + 1):
        visited.append(agent)
        pending_handoff.clear()
        await run_specialist(agent, task)
        if not pending_handoff:
            break
        nxt = pending_handoff["to"]
        if nxt in visited:                     # stop ping-pong loops
            print(f"!! refusing handoff back to {nxt} (already visited)")
            break
        print(f"HANDOFF {agent} -> {nxt}: {pending_handoff['summary']}")
        agent, task = nxt, pending_handoff["summary"]
    print("PATH:", " -> ".join(visited))

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else \
        "What's NVDA trading at, and write me a pandas function for a 20-day SMA crossover?"
    asyncio.run(main(msg))