# Run: python day16_orchestrator.py   (ANTHROPIC_API_KEY must be UNSET)
import asyncio
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition, tool, create_sdk_mcp_server,
    AssistantMessage, ResultMessage, TextBlock, ToolUseBlock,
)

# Fake data keeps the run cheap and gives the same answer every time
PRICES = {"AAPL": [228, 231, 229, 235, 238], "MSFT": [415, 410, 418, 421, 419]}
VOL = {"AAPL": 0.24, "MSFT": 0.19}

@tool("get_prices", "Last 5 daily closes for a US ticker. Use for trend/momentum.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "enum": list(PRICES)}},
       "required": ["symbol"]})
async def get_prices(args):
    s = args["symbol"]
    return {"content": [{"type": "text", "text": f"{s} closes: {PRICES[s]}"}]}

@tool("get_volatility", "Annualised volatility (0-1) for a US ticker. Use for risk.",
      {"type": "object",
       "properties": {"symbol": {"type": "string", "enum": list(VOL)}},
       "required": ["symbol"]})
async def get_volatility(args):
    s = args["symbol"]
    return {"content": [{"type": "text", "text": f"{s} vol: {VOL[s]}"}]}

market = create_sdk_mcp_server("market", tools=[get_prices, get_volatility])

# Workers: each has one job, only that job's tool, and the cheap model
AGENTS = {
    "trend-analyst": AgentDefinition(
        description="Analyses price trend/momentum for ONE ticker. Give it the symbol.",
        prompt="You analyse momentum. Call get_prices, then reply in <=2 lines: "
               "'<SYM>: trend=<up|down|flat>, 5d change=<x>%'. No other text.",
        tools=["mcp__market__get_prices"],
        model="haiku",
    ),
    "risk-analyst": AgentDefinition(
        description="Assesses volatility risk for ONE ticker. Give it the symbol.",
        prompt="You assess risk. Call get_volatility, then reply in 1 line: "
               "'<SYM>: vol=<v>, risk=<low|med|high>' (low<0.2, high>0.3).",
        tools=["mcp__market__get_volatility"],
        model="haiku",
    ),
}

LEAD_PROMPT = """You are the lead analyst. You do NOT fetch data yourself.
Plan: 1) split the request into one subtask per (ticker x analyst).
2) Delegate each subtask with the Agent tool, sending a short, self-contained task.
3) When all results are in, write a 3-line comparison and a one-line verdict."""

async def main():
    opts = ClaudeAgentOptions(
        system_prompt=LEAD_PROMPT,
        model="sonnet",            # the lead does the hard thinking
        tools=["Agent"],           # the lead's only built-in tool hands work to workers
        agents=AGENTS,
        mcp_servers={"market": market},
        allowed_tools=["Agent", "mcp__market__get_prices",
                       "mcp__market__get_volatility"],
        max_turns=12,
    )
    async for msg in query(prompt="Compare AAPL vs MSFT for a 1-week swing trade.",
                           options=opts):
        if isinstance(msg, AssistantMessage):
            # parent_tool_use_id is None for the lead, set for a worker's messages
            who = "LEAD " if msg.parent_tool_use_id is None else "  worker"
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    if b.name in ("Agent", "Task"):  # older versions: "Task"
                        print(f"{who} DELEGATE -> {b.input.get('subagent_type')}: "
                              f"{b.input.get('prompt', '')[:70]}")
                    else:
                        print(f"{who} tool {b.name}({b.input})")
                elif isinstance(b, TextBlock) and msg.parent_tool_use_id is None:
                    print(f"{who} says: {b.text}")
        elif isinstance(msg, ResultMessage):
            print(f"\nturns={msg.num_turns} cost=${msg.total_cost_usd or 0:.4f}")
            for model, u in (msg.model_usage or {}).items():
                print(f"  {model}: {u}")

asyncio.run(main())