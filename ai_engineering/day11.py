# day11.py — agentic search vs a tiny RAG tool, on the same notes folder
import asyncio, math, re, sys
from collections import Counter
from pathlib import Path
from claude_agent_sdk import (query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
                              AssistantMessage, ResultMessage, ToolUseBlock)

NOTES = Path("trading_notes")

# --- 1. Build a small corpus (your own notes would go here) ---
DOCS = {
    "mean_reversion.md": "# Mean reversion on KLCI stocks\nEntry: RSI(2) below 10 and price above 200-day SMA.\n\nExit: close above 5-day SMA.\n\nRisk: hard stop at 3x ATR(14) below entry. Never average down.",
    "breakout.md": "# Breakout strategy\nEntry: 20-day high on volume > 1.5x average.\n\nRisk: initial stop at the breakout bar low; trail with 10-day low.",
    "journal/2026-10.md": "# October journal\nLost 2.1% on MYEG when I ignored my exit rule and held through earnings.\n\nLesson: cut losers fast, size smaller before earnings.",
    "broker_api.md": "# Broker API notes\nRate limit: 200 requests/min. Use bracket orders so the protective order is placed with the entry.",
}
for name, text in DOCS.items():
    p = NOTES / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

# --- 2. "Classic RAG" as a tool: chunk -> vectorise -> top-k ---
# Bag-of-words cosine stands in for real embeddings
# (swap in fastembed / sentence-transformers for true semantic matching).
def tokens(s): return re.findall(r"[a-z0-9]+", s.lower())

CHUNKS = []  # (source, chunk_text, vector)
for f in NOTES.rglob("*.md"):
    for i, para in enumerate(f.read_text().split("\n\n")):
        CHUNKS.append((f"{f.relative_to(NOTES)}#chunk{i}", para, Counter(tokens(para))))

def cosine(a, b):
    dot = sum(a[t] * b[t] for t in a)
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

@tool("search_notes",
      "Semantic search over the user's trading notes. Returns the top matching "
      "passages with their source. Use for conceptual questions.",
      {"type": "object",
       "properties": {"query": {"type": "string", "description": "What to look for, in plain words"},
                      "k": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}},
       "required": ["query"]})
async def search_notes(args):
    q = Counter(tokens(args["query"]))
    hits = sorted(CHUNKS, key=lambda c: cosine(q, c[2]), reverse=True)[: args.get("k", 3)]
    text = "\n---\n".join(f"[{src}] {chunk}" for src, chunk, _ in hits)  # small output (Day 3)
    return {"content": [{"type": "text", "text": text or "No matches."}]}

rag_server = create_sdk_mcp_server("notes", "1.0.0", tools=[search_notes])

# --- 3. Two agents, same question ---
def options(mode):
    common = dict(cwd=str(NOTES), max_turns=8, model="haiku",
                  system_prompt="Answer from the user's notes only. Cite the file for every fact.")
    if mode == "agentic":   # the model explores the files itself
        return ClaudeAgentOptions(tools=["Grep", "Glob", "Read"],
                                  allowed_tools=["Grep", "Glob", "Read"], **common)
    return ClaudeAgentOptions(tools=[], mcp_servers={"notes": rag_server},  # retrieval only
                              allowed_tools=["mcp__notes__search_notes"], **common)

QUESTION = "What should I do when a trade moves against me? Give every rule I've written down."

async def run(mode):
    print(f"\n===== {mode.upper()} =====")
    async for m in query(prompt=QUESTION, options=options(mode)):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, ToolUseBlock):
                    print(f"  -> {b.name}({b.input})")   # watch the search strategy
        elif isinstance(m, ResultMessage):
            u = m.usage or {}
            print(m.result)
            print(f"[turns={m.num_turns} cost=${m.total_cost_usd or 0:.4f} "
                  f"in={u.get('input_tokens')} out={u.get('output_tokens')}]")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "agentic"   # "agentic" or "rag"
    asyncio.run(run(mode))