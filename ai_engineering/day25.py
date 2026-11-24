# day25_failure_modes.py — catch loops, bad args and runaway usage
# Needs: pip install claude-agent-sdk, one-time `claude` login.
# Keep ANTHROPIC_API_KEY unset, or it overrides your subscription.
import asyncio, json
from collections import Counter
from claude_agent_sdk import (
    query, tool, create_sdk_mcp_server, ClaudeAgentOptions, HookMatcher,
    AssistantMessage, UserMessage, ResultMessage, ToolUseBlock, ToolResultBlock,
)

KNOWN = {"MAYBANK": 9.85, "CIMB": 7.40, "TENAGA": 13.20}

@tool("get_quote", "Get the last price for a Bursa ticker. Valid tickers: "
      "MAYBANK, CIMB, TENAGA.",
      {"type": "object",
       "properties": {"ticker": {"type": "string"}},
       "required": ["ticker"]})
async def get_quote(args):
    t = str(args.get("ticker", "")).upper().strip()
    # Failure mode 1: hallucinated args -> reject, and list the valid options
    if t not in KNOWN:
        return {"is_error": True, "content": [{"type": "text",
                "text": f"Unknown ticker '{t}'. Valid: {sorted(KNOWN)}."}]}
    # Failure mode 2 bait: TENAGA always "times out" -> tempts a retry loop
    if t == "TENAGA":
        return {"is_error": True, "content": [{"type": "text",
                "text": "Upstream timeout. Try again."}]}
    return {"content": [{"type": "text", "text": json.dumps({t: KNOWN[t]})}]}

# --- Detectors (hooks run in YOUR process, so they're cheap and reliable) ---
seen = Counter()          # (tool, args) -> how many times called
MAX_REPEAT = 2            # identical call allowed twice, then blocked
MAX_TOOL_CALLS = 6        # hard cap on tool calls per run

async def loop_guard(input_data, tool_use_id, context):
    key = (input_data["tool_name"],
           json.dumps(input_data["tool_input"], sort_keys=True))
    seen[key] += 1
    total = sum(seen.values())
    reason = None
    if seen[key] > MAX_REPEAT:
        reason = (f"Loop detected: identical call made {seen[key]} times. "
                  "Do not retry; report the failure to the user.")
    elif total > MAX_TOOL_CALLS:
        reason = f"Tool budget exhausted ({MAX_TOOL_CALLS} calls). Stop and answer."
    if reason:
        print(f"  [GUARD] blocked {key[0]} {key[1]}: {reason}")
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}
    return {}

server = create_sdk_mcp_server("market", "1.0.0", [get_quote])

async def main():
    opts = ClaudeAgentOptions(
        model="haiku",
        tools=[],                                  # no built-ins
        mcp_servers={"market": server},
        allowed_tools=["mcp__market__get_quote"],
        hooks={"PreToolUse": [HookMatcher(matcher="mcp__market__get_quote",
                                          hooks=[loop_guard])]},
        max_turns=8,                               # backstop #1
        max_budget_usd=0.05,                       # backstop #2 (cost estimate)
        system_prompt="You are a market assistant. If a tool keeps failing, "
                      "retry at most once, then tell the user plainly.",
    )
    prompt = "Get prices for Maybank, CIMB, Tenaga and Public Bank. Keep retrying until you get them all."
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f"CALL  {b.input}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    flag = "ERR " if b.is_error else "OK  "
                    print(f"{flag}  {str(b.content)[:90]}")
        elif isinstance(msg, ResultMessage):
            # Failure mode 3: runaway usage -> always check how the run ended
            print(f"\nEND subtype={msg.subtype} turns={msg.num_turns} "
                  f"cost≈${msg.total_cost_usd or 0:.4f}")
            if msg.subtype != "success":
                print("!! Run hit a limit — alert/log this, don't trust the answer.")
            else:
                print(msg.result)
    print("Call counts:", dict(seen))

asyncio.run(main())