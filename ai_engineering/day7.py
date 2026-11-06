"""Day 7 mini-project: a research agent with web search/fetch + a notes tool.
Run:  python day7_research_agent.py "What is MCP and who supports it?"
Make sure ANTHROPIC_API_KEY is NOT set (it would override your subscription).
"""
import asyncio, json, sys
from pathlib import Path
from claude_agent_sdk import (
    query, tool, create_sdk_mcp_server, ClaudeAgentOptions,
    AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

NOTES = Path("research_notes.json")   # long-lived store; survives runs

def _load() -> dict:
    return json.loads(NOTES.read_text()) if NOTES.exists() else {}

# --- Tool 1: save a note (idempotent: same key overwrites, never duplicates) ---
@tool(
    "save_note",
    "Save ONE short finding with its source URL. Call once per distinct fact. "
    "Re-using a key overwrites that note (use this to correct a finding).",
    {
        "type": "object",
        "properties": {
            "key":    {"type": "string", "description": "short snake_case id, e.g. 'mcp_launch_date'"},
            "fact":   {"type": "string", "description": "one or two sentences, max ~300 chars"},
            "source": {"type": "string", "description": "URL the fact came from"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["key", "fact", "source"],
    },
)
async def save_note(args):
    if not args["source"].startswith("http"):
        return {"content": [{"type": "text", "text": "Error: source must be a URL you actually fetched or saw in search results."}],
                "is_error": True}
    notes = _load()
    existed = args["key"] in notes
    notes[args["key"]] = {"fact": args["fact"][:400], "source": args["source"],
                          "confidence": args.get("confidence", "medium")}
    NOTES.write_text(json.dumps(notes, indent=2))
    verb = "Updated" if existed else "Saved"
    return {"content": [{"type": "text", "text": f"{verb} '{args['key']}'. Total notes: {len(notes)}"}]}

# --- Tool 2: read notes back (small output: keys + facts only) ---
@tool("list_notes", "List all saved notes. Use before writing the final answer.",
      {"type": "object", "properties": {}})
async def list_notes(args):
    notes = _load()
    if not notes:
        return {"content": [{"type": "text", "text": "No notes yet."}]}
    lines = [f"- {k} [{v['confidence']}]: {v['fact']} ({v['source']})" for k, v in notes.items()]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}

notes_server = create_sdk_mcp_server(name="notes", version="1.0.0", tools=[save_note, list_notes])

SYSTEM = """You are a careful research assistant.
Plan:
1. Run at most 3 WebSearch queries for the question.
2. WebFetch at most 3 of the most relevant pages.
3. After each useful page, call save_note for each distinct fact (cite the URL).
4. Call list_notes, then write a short answer (<= 200 words) using ONLY your notes,
   citing sources as [key]. If notes conflict or are thin, say so.
Never invent URLs. Stop as soon as you can answer."""

async def main(question: str):
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM,
        tools=["WebSearch", "WebFetch"],          # only these built-ins exist for the agent
        mcp_servers={"notes": notes_server},
        allowed_tools=["WebSearch", "WebFetch",   # pre-approve so it runs unattended
                       "mcp__notes__save_note", "mcp__notes__list_notes"],
        model="sonnet",
        max_turns=15,                              # search+fetch+notes needs more than Day 1's 5
    )
    async for msg in query(prompt=question, options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f"🔧 {b.name}  {json.dumps(b.input)[:120]}")
                elif isinstance(b, TextBlock):
                    print(f"\n💬 {b.text}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    tag = "❌" if b.is_error else "✅"
                    print(f"   {tag} result ({len(str(b.content))} chars)")
        elif isinstance(msg, ResultMessage):
            print(f"\n--- {msg.subtype} | turns={msg.num_turns} | stop={msg.stop_reason} "
                  f"| ~${msg.total_cost_usd or 0:.4f} (notional on subscription)")

if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "What is the Model Context Protocol and which companies support it?"))
