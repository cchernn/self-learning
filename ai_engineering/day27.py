# day27_durable.py — a crash-safe, resumable watchlist reviewer
import asyncio, json, os, sys
from claude_agent_sdk import (query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
                              ResultMessage, ToolUseBlock, AssistantMessage)

STATE = "day27_state.json"
TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT"]
FAKE_DATA = {"AAPL": "+1.2% wk, RSI 58", "NVDA": "+6.8% wk, RSI 77",
             "TSLA": "-4.1% wk, RSI 31", "MSFT": "+0.3% wk, RSI 50"}

# ---- durable state: YOUR file is the source of truth ----
def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"session_id": None, "done": {}}

def save_state(s):                       # atomic: write tmp, then rename
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, STATE)               # never leaves a half-written file

state = load_state()

@tool("record_verdict", "Save the final verdict for ONE ticker. Call once per ticker.",
      {"type": "object",
       "properties": {"ticker": {"type": "string", "enum": TICKERS},
                      "verdict": {"type": "string", "enum": ["watch", "ignore", "alert"]},
                      "reason": {"type": "string", "description": "max 15 words"}},
       "required": ["ticker", "verdict", "reason"]})
async def record_verdict(args):
    # idempotent: same ticker twice just overwrites (safe after a crash/retry)
    state["done"][args["ticker"]] = {"verdict": args["verdict"], "reason": args["reason"]}
    save_state(state)                    # checkpoint right after the side effect
    return {"content": [{"type": "text", "text": f"saved {args['ticker']}"}]}

server = create_sdk_mcp_server("desk", tools=[record_verdict])

async def review(ticker):
    opts = ClaudeAgentOptions(
        model="haiku", tools=[], max_turns=3,
        mcp_servers={"desk": server},
        allowed_tools=["mcp__desk__record_verdict"],
        system_prompt="You review one ticker at a time and call record_verdict exactly once.",
        resume=state["session_id"],      # None on first run -> new session
    )
    prompt = (f"Ticker {ticker}: {FAKE_DATA[ticker]}. Record a verdict. "
              "If an earlier ticker in this chat looks similar, mention it in the reason.")
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print("  tool:", b.input)
        if isinstance(msg, ResultMessage):
            state["session_id"] = msg.session_id   # remember the conversation
            save_state(state)
            print(f"  turns={msg.num_turns} stop={msg.subtype}")

async def main():
    crash_after = int(os.getenv("CRASH_AFTER", "0"))   # simulate a crash
    for i, t in enumerate(TICKERS):
        if t in state["done"]:
            print(f"skip {t} (checkpointed)"); continue
        if crash_after and i >= crash_after:
            print("💥 simulated crash"); sys.exit(1)
        print(f"review {t}")
        await review(t)
    print(json.dumps(state["done"], indent=2))

if __name__ == "__main__":
    asyncio.run(main())