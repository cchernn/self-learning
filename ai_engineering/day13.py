"""Day 13: guardrails — allow-list, PreToolUse hook, can_use_tool approval."""
import asyncio
from claude_agent_sdk import (
    tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient,
    HookMatcher, PermissionResultAllow, PermissionResultDeny,
    AssistantMessage, ResultMessage, TextBlock, ToolUseBlock,
)

# ---- Fake broker tools (no real orders!) ----
PRICES = {"AAPL": 231.5, "MSFT": 418.2, "TSLA": 247.9}

@tool("get_quote", "Get the last price for a US stock ticker.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "description": "e.g. AAPL"}},
       "required": ["symbol"]})
async def get_quote(args):
    s = args["symbol"].upper()
    if s not in PRICES:
        return {"content": [{"type": "text", "text": f"Unknown symbol {s}"}], "is_error": True}
    return {"content": [{"type": "text", "text": f"{s} last={PRICES[s]}"}]}

@tool("place_order", "Place a PAPER market order. Needs human approval.",
      {"type": "object",
       "properties": {"symbol": {"type": "string"},
                      "side": {"type": "string", "enum": ["buy", "sell"]},
                      "qty": {"type": "integer", "minimum": 1}},
       "required": ["symbol", "side", "qty"]})
async def place_order(args):
    return {"content": [{"type": "text",
            "text": f"FILLED (paper): {args['side']} {args['qty']} {args['symbol']}"}]}

broker = create_sdk_mcp_server("broker", "1.0.0", [get_quote, place_order])

# ---- Layer 1: PreToolUse hook = hard policy, runs FIRST, no human ----
MAX_NOTIONAL = 5_000
WHITELIST = {"AAPL", "MSFT"}

async def risk_hook(input_data, tool_use_id, context):
    if input_data["tool_name"] != "mcp__broker__place_order":
        return {}                                   # {} = no opinion
    a = input_data["tool_input"]
    sym = a["symbol"].upper()
    notional = PRICES.get(sym, 0) * a["qty"]
    reason = None
    if sym not in WHITELIST:
        reason = f"{sym} not on the trading whitelist {sorted(WHITELIST)}"
    elif notional > MAX_NOTIONAL:
        reason = f"notional ${notional:,.0f} exceeds limit ${MAX_NOTIONAL:,}"
    if reason:
        print(f"  [HOOK] BLOCKED: {reason}")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason}}   # the model sees this
    return {}

# ---- Layer 2: can_use_tool = human-in-the-loop ----
async def ask_human(tool_name, tool_input, context):
    print(f"\n  [APPROVAL] {tool_name} {tool_input}")
    ans = await asyncio.to_thread(input, "  approve? [y/N] ")  # don't block loop
    if ans.strip().lower() == "y":
        return PermissionResultAllow()
    return PermissionResultDeny(message="Human rejected this order. Do not retry.")

options = ClaudeAgentOptions(
    tools=[],                                     # no built-ins at all
    mcp_servers={"broker": broker},
    allowed_tools=["mcp__broker__get_quote"],     # read-only: auto-approved
    # place_order is NOT allowed -> falls through to ask_human
    can_use_tool=ask_human,
    hooks={"PreToolUse": [HookMatcher(matcher="mcp__broker__place_order",
                                      hooks=[risk_hook])]},
    system_prompt="You are a careful paper-trading assistant. Quote before ordering.",
    model="haiku",
    max_turns=8,
)

async def main():
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Buy 10 AAPL, then buy 50 MSFT, then buy 5 TSLA. "
                           "Report what happened to each.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ToolUseBlock):
                        print(f"-> {b.name} {b.input}")
                    elif isinstance(b, TextBlock):
                        print(b.text)
            elif isinstance(msg, ResultMessage):
                print(f"\n[done] turns={msg.num_turns} cost=${msg.total_cost_usd or 0:.4f}")

if __name__ == "__main__":
    asyncio.run(main())