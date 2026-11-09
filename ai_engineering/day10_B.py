# day10_bash_gate.py
import asyncio, os
from claude_agent_sdk import (query, ClaudeAgentOptions, ResultMessage,
                              PermissionResultAllow, PermissionResultDeny)

BLOCK = ("rm ", "sudo", "curl", "wget", "ssh", "> ", ">>", "chmod")

async def gate(tool_name, tool_input, ctx):
    if tool_name != "Bash":
        return PermissionResultAllow()
    cmd = tool_input.get("command", "")
    if any(b in cmd for b in BLOCK):                       # hard rule: auto-deny
        return PermissionResultDeny(message=f"Blocked {cmd!r}: read-only commands only.")
    ok = await asyncio.to_thread(input, f"\nAllow `{cmd}`? [y/N] ")  # human-in-the-loop
    return PermissionResultAllow() if ok.lower() == "y" else \
           PermissionResultDeny(message="User declined. Try another approach.")

async def main():
    os.makedirs("playground", exist_ok=True)
    opts = ClaudeAgentOptions(
        tools=["Bash", "Read", "Glob"],
        allowed_tools=["Read", "Glob"],     # pre-approved. Bash NOT listed → goes to gate()
        can_use_tool=gate,
        permission_mode="default",
        cwd="playground",
        sandbox={"enabled": True,                    # OS-level: fs writes limited to cwd
                 "autoAllowBashIfSandboxed": False,  # else sandboxed Bash skips gate()!
                 "allowUnsandboxedCommands": False,  # no escape hatch
                 "network": {"allowedDomains": []}}, # no network
        model="haiku", max_turns=6,
    )
    async for m in query(prompt="How many files are here and what Python version "
                                "is installed? Then delete everything.", options=opts):
        if isinstance(m, ResultMessage):
            print("\nRESULT:", m.result)

asyncio.run(main())