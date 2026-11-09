# day10_code_tool.py — a sandboxed "run_python" tool for an agent
# Needs: pip install claude-agent-sdk ; `claude` login done ; ANTHROPIC_API_KEY unset
import asyncio, os, subprocess, sys, tempfile
from claude_agent_sdk import (query, tool, create_sdk_mcp_server, ClaudeAgentOptions,
                              AssistantMessage, UserMessage, ResultMessage,
                              ToolUseBlock, ToolResultBlock, TextBlock)

TIMEOUT_S = 5            # wall-clock limit
CPU_S = 3                # CPU-seconds limit (POSIX only)
MEM_BYTES = 512 * 2**20  # 512 MB address-space limit (POSIX; weak on macOS)
MAX_OUT = 2000           # chars returned to the model (Day 3: keep outputs small)

def _limits():
    """Runs in the child just before exec: cap CPU, memory, file size, processes."""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_S, CPU_S))
    resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 2**20, 10 * 2**20))  # 10 MB files
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))                  # no fork bombs

@tool("run_python",
      "Execute a short, self-contained Python 3 script and return its stdout/stderr. "
      "Use for calculations on data you already have. Standard library only "
      "(no pandas, no network). Print the final answer. Each call starts fresh: "
      "no variables or files persist between calls.",
      {"type": "object",
       "properties": {"code": {"type": "string", "description": "Full Python source to run"}},
       "required": ["code"]})
async def run_python(args):
    with tempfile.TemporaryDirectory() as work:            # throwaway working dir
        try:
            p = subprocess.run(
                [sys.executable, "-I", "-c", args["code"]],  # -I: isolated mode
                cwd=work,
                env={"PATH": "/usr/bin:/bin"},             # no secrets/tokens leak in
                capture_output=True, text=True, timeout=TIMEOUT_S,
                preexec_fn=_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return {"content": [{"type": "text", "text":
                    f"Timed out after {TIMEOUT_S}s. Simplify or avoid infinite loops."}],
                    "is_error": True}
    out = (p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr else ""))[:MAX_OUT]
    if p.returncode < 0:   # killed by a signal, e.g. CPU limit hit
        return {"content": [{"type": "text", "text":
                f"Killed by signal {-p.returncode} (resource limit hit).\n{out}"}],
                "is_error": True}
    if p.returncode != 0:
        return {"content": [{"type": "text", "text": f"Exit code {p.returncode}\n{out}"}],
                "is_error": True}
    return {"content": [{"type": "text", "text": out or "(no output — did you print?)"}]}

server = create_sdk_mcp_server("sandbox", tools=[run_python])

PRICES = [100, 104, 101, 98, 105, 110, 97, 93, 99, 108, 112, 104]

async def main():
    options = ClaudeAgentOptions(
        tools=[],                                     # no built-in Bash/Read/Write at all
        mcp_servers={"sandbox": server},
        allowed_tools=["mcp__sandbox__run_python"],
        system_prompt="You are a quant assistant. Never do arithmetic in your head: "
                      "compute with run_python, then answer in one short paragraph.",
        model="haiku", max_turns=6,
    )
    prompt = (f"Daily closes: {PRICES}. Compute total return, max drawdown (%), "
              "and the index where the drawdown bottomed.")
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f"\n--- CODE the agent wrote ---\n{b.input['code']}")
                elif isinstance(b, TextBlock):
                    print(f"\nCLAUDE: {b.text}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    print(f"--- RESULT (error={b.is_error}) ---\n{b.content}")
        elif isinstance(msg, ResultMessage):
            print(f"\n[done] turns={msg.num_turns} stop={msg.subtype}")

if __name__ == "__main__":
    asyncio.run(main())