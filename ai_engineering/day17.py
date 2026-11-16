# day17.py — subagent context isolation, observed
# Run: python day17.py   (ANTHROPIC_API_KEY must be UNSET so your subscription is used)
import asyncio, random, csv
from pathlib import Path
from claude_agent_sdk import (
    query, ClaudeAgentOptions, AgentDefinition,
    AssistantMessage, UserMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

WORK = Path("day17_work"); WORK.mkdir(exist_ok=True)

def make_fake_log(n=3000):
    """A big noisy trade log: the kind of thing you DON'T want in your lead's context."""
    random.seed(17)
    with open(WORK / "trades.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "symbol", "side", "qty", "price", "status"])
        for i in range(n):
            sym = random.choice(["AAPL", "MSFT", "NVDA", "TSLA", "SPY"])
            status = "REJECTED" if random.random() < 0.03 else "FILLED"
            w.writerow([f"2026-11-{1+i%15:02d}T{9+i%7:02d}:{i%60:02d}", sym,
                        random.choice(["BUY", "SELL"]), random.randint(1, 200),
                        round(random.uniform(100, 900), 2), status])

# The worker: its own fresh context, cheap model, read-only tools, strict output contract.
digester = AgentDefinition(
    description="Use for ANY question that requires reading files in the working "
                "directory. Reads/greps large logs and returns a short digest.",
    prompt=(
        "You analyse trade log files. Use Grep/Read to find what the task asks for.\n"
        "Return AT MOST 5 lines: the answer, key numbers, and the evidence "
        "(e.g. counts). Never paste raw rows back."
    ),
    tools=["Read", "Grep", "Glob"],
    model="haiku",
)

options = ClaudeAgentOptions(
    cwd=str(WORK),
    system_prompt=(
        "You are a trading-ops lead. You may NOT read files yourself. "
        "Delegate file work to the log-digester subagent with a precise, "
        "self-contained task (it cannot see this conversation). Then answer briefly."
    ),
    agents={"log-digester": digester},
    # 'Agent' is the subagent tool (older CLI versions call it 'Task').
    tools=["Agent", "Task", "Read", "Grep", "Glob"],
    allowed_tools=["Agent", "Task", "Read", "Grep", "Glob"],
    model="sonnet",
    max_turns=8,
)

async def main():
    make_fake_log()
    log_bytes = (WORK / "trades.csv").stat().st_size
    inside_chars = 0      # text that stayed inside the subagent's context
    returned_chars = 0    # text that came back to the lead
    agent_call_ids = set()

    async for msg in query(prompt="Which symbol had the most REJECTED orders, and how many?",
                           options=options):
        sub = getattr(msg, "parent_tool_use_id", None)   # set => message is from INSIDE a subagent
        tag = "   [sub]" if sub else "[lead]"
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    if b.name in ("Agent", "Task"):
                        agent_call_ids.add(b.id)
                        print(f"{tag} DELEGATES -> {b.input.get('subagent_type')}: "
                              f"{b.input.get('prompt', '')[:120]!r}")
                    else:
                        print(f"{tag} tool {b.name} {str(b.input)[:80]}")
                elif isinstance(b, TextBlock) and not sub:
                    print(f"{tag} {b.text}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    size = len(str(b.content))
                    if b.tool_use_id in agent_call_ids:
                        returned_chars += size
                        print(f"[lead] <- subagent digest ({size} chars):\n{str(b.content)[:400]}")
                    elif sub:
                        inside_chars += size
        elif isinstance(msg, ResultMessage):
            print(f"\nturns={msg.num_turns}  cost_est=${msg.total_cost_usd or 0:.4f}")

    print(f"log file: {log_bytes:,} bytes | tool output inside subagent: {inside_chars:,} chars "
          f"| returned to lead: {returned_chars:,} chars")

asyncio.run(main())