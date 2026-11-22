# Run:  python day23_trace.py          -> runs agent, writes traces/<run_id>.jsonl
#       python day23_trace.py replay   -> prints latest trace (no model calls)
import asyncio, json, sys, time, uuid
from pathlib import Path
from claude_agent_sdk import (
    query, ClaudeAgentOptions, HookMatcher, tool, create_sdk_mcp_server,
    AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

TRACE_DIR = Path("traces"); TRACE_DIR.mkdir(exist_ok=True)
RUN_ID = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
TRACE = TRACE_DIR / f"{RUN_ID}.jsonl"
T0 = time.monotonic()

def log(event, **fields):
    """One JSON object per line."""
    rec = {"run_id": RUN_ID, "event": event,
           "t_ms": round((time.monotonic() - T0) * 1000), **fields}
    with TRACE.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")

def clip(x, n=300):  # keep logs small
    s = x if isinstance(x, str) else json.dumps(x, default=str)
    return s if len(s) <= n else s[:n] + f"...(+{len(s)-n})"

# --- a tool with fake data (TSLA missing on purpose) ---
PRICES = {"AAPL": 231.4, "NVDA": 142.8, "MAYBANK": 10.12}

@tool("get_price", "Get the latest price for a ticker symbol.",
      {"type": "object",
       "properties": {"symbol": {"type": "string"}},
       "required": ["symbol"]})
async def get_price(args):
    sym = args["symbol"].upper()
    if sym not in PRICES:
        return {"content": [{"type": "text",
                "text": f"Unknown symbol {sym}. Known: {list(PRICES)}"}],
                "is_error": True}
    return {"content": [{"type": "text",
            "text": json.dumps({"symbol": sym, "price": PRICES[sym]})}]}

server = create_sdk_mcp_server("mkt", "1.0.0", tools=[get_price])

# --- hooks: signature is (input, tool_use_id, context) ---
async def pre_tool(inp, tid, ctx):
    log("tool_start", tool=inp["tool_name"], tool_use_id=tid,
        input=clip(inp["tool_input"]), agent=inp.get("agent_type"))
    return {}  # {} = observe only

async def post_tool(inp, tid, ctx):
    log("tool_end", tool=inp["tool_name"], tool_use_id=tid,
        duration_ms=inp.get("duration_ms"),
        output=clip(inp["tool_response"]))
    return {}

async def tool_failed(inp, tid, ctx):
    log("tool_fail", tool=inp["tool_name"], tool_use_id=tid,
        error=clip(inp["error"]))
    return {}

async def run():
    opts = ClaudeAgentOptions(
        model="haiku", tools=[], max_turns=6,
        mcp_servers={"mkt": server},
        allowed_tools=["mcp__mkt__get_price"],
        system_prompt="Answer price questions using get_price. Be brief.",
        hooks={  # matcher=None -> every tool
            "PreToolUse": [HookMatcher(hooks=[pre_tool])],
            "PostToolUse": [HookMatcher(hooks=[post_tool])],
            "PostToolUseFailure": [HookMatcher(hooks=[tool_failed])],
        },
    )
    prompt = "What are AAPL, MAYBANK and TSLA at? Which is cheapest?"
    log("run_start", prompt=prompt, model=opts.model)
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):          # model side
            for b in msg.content:
                if isinstance(b, TextBlock):
                    log("model_text", text=clip(b.text))
                elif isinstance(b, ToolUseBlock):
                    log("model_tool_call", tool=b.name,
                        tool_use_id=b.id, input=clip(b.input))
            if msg.usage:
                log("model_usage", msg_id=msg.message_id, usage=msg.usage)
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    log("tool_result", tool_use_id=b.tool_use_id,
                        is_error=b.is_error)
        elif isinstance(msg, ResultMessage):
            log("run_end", subtype=msg.subtype, turns=msg.num_turns,
                duration_ms=msg.duration_ms, cost_usd=msg.total_cost_usd,
                session_id=msg.session_id, result=clip(msg.result or ""))
    print(f"Trace: {TRACE}")

def replay(path=None):
    """Rebuild the timeline from the log alone."""
    path = Path(path) if path else max(TRACE_DIR.glob("*.jsonl"))
    rows = [json.loads(l) for l in path.open()]
    for r in rows:
        t, e = f'{r["t_ms"]:>6}ms', r["event"]
        if e == "tool_start":
            print(f"{t}  TOOL {r['tool']} {r['input']}")
        elif e in ("tool_end", "tool_fail"):
            print(f"{t}    -> {r.get('output') or r.get('error')}")
        elif e == "model_text":
            print(f"{t}  SAY  {r['text']}")
        elif e == "run_end":
            print(f"{t}  END  {r['subtype']} turns={r['turns']} "
                  f"cost=${r['cost_usd']}")
    n_err = sum(1 for r in rows if r["event"] == "tool_result"
                and r["is_error"])
    n_tool = sum(1 for r in rows if r["event"] == "tool_start")
    print(f"\n{n_tool} tool calls, {n_err} errors")

if __name__ == "__main__":
    if sys.argv[1:2] == ["replay"]:
        replay(*sys.argv[2:])
    else:
        asyncio.run(run())