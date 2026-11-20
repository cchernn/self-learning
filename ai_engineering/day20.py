"""Day 20: evaluator-optimizer loop. Uses your subscription.
Keep ANTHROPIC_API_KEY unset or it overrides your login!"""
import asyncio, json, subprocess, sys, tempfile, textwrap
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

TASK = """Write a Python function `max_drawdown(equity: list[float]) -> float`.
Return the largest peak-to-trough drop as a positive fraction (0.25 = -25%).
Empty or single-point list -> 0.0. Any value <= 0 -> raise ValueError.
Standard library only. No prints."""
MAX_ROUNDS = 3

# ---- 1. Deterministic evaluator: hidden tests ----
TESTS = textwrap.dedent("""
    import math
    def close(a, b): return math.isclose(a, b, abs_tol=1e-9)
    cases = [([], 0.0), ([100], 0.0), ([100, 110, 120], 0.0),
             ([100, 80, 120, 90], 0.25), ([100, 50, 200, 100], 0.5)]
    fails = []
    for eq, want in cases:
        try:
            got = max_drawdown(eq)
            if not close(got, want):
                fails.append(f"max_drawdown({eq}) = {got}, expected {want}")
        except Exception as e:
            fails.append(f"max_drawdown({eq}) raised {e!r}")
    try:
        max_drawdown([100, 0, 50]); fails.append("no ValueError for a 0 value")
    except ValueError: pass
    print("\\n".join(fails) if fails else "ALL PASS")
""")

def run_tests(code: str) -> tuple[bool, str]:
    """Run model code + tests in a separate process with a timeout."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code + "\n" + TESTS)
    try:
        out = subprocess.run([sys.executable, "-I", f.name],
                             capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return False, "Timed out after 10s (infinite loop?)"
    report = (out.stdout + out.stderr).strip()[-1500:]  # keep it small
    return report == "ALL PASS", report

# ---- 2. Helper: ask a model for JSON matching a schema ----
async def ask_json(prompt, system, schema, model) -> dict:
    opts = ClaudeAgentOptions(
        system_prompt=system, model=model, tools=[], max_turns=3,
        output_format={"type": "json_schema", "schema": schema},
    )
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, ResultMessage):
            if msg.is_error or msg.structured_output is None:
                raise RuntimeError(f"No structured output: {msg.subtype}")
            print(f"   [{model}] cost ${msg.total_cost_usd or 0:.4f}")
            return msg.structured_output
    raise RuntimeError("No ResultMessage")

GEN_SCHEMA = {"type": "object", "required": ["code"],
    "properties": {"code": {"type": "string",
                            "description": "Full Python source"}}}
CRITIC_SCHEMA = {"type": "object", "required": ["verdict", "issues"],
    "properties": {
      "verdict": {"type": "string", "enum": ["accept", "revise"]},
      "issues": {"type": "array", "items": {"type": "string"},
                 "maxItems": 5}}}

GEN_SYSTEM = "You write correct, minimal Python. Return only the code field."
CRITIC_SYSTEM = """You are a strict code reviewer. Tests already passed,
so do NOT re-check the listed cases. Look only for: unhandled edge cases
(NaN, non-list input, huge lists), O(n^2) loops, unclear names.
Say 'accept' unless an issue would matter in production. Be brief."""

# ---- 3. The loop ----
async def main():
    feedback, code = "", ""
    for rnd in range(1, MAX_ROUNDS + 1):
        print(f"\n=== Round {rnd} ===")
        prompt = TASK if not feedback else (
            f"{TASK}\n\nYour previous attempt:\n```python\n{code}\n```\n"
            f"Fix these problems:\n{feedback}")
        code = (await ask_json(prompt, GEN_SYSTEM, GEN_SCHEMA, "haiku"))["code"]

        ok, report = run_tests(code)            # cheap check FIRST
        print("   tests:", "PASS" if ok else "FAIL")
        if not ok:
            feedback = "Test failures:\n" + report
            continue                            # skip the paid critic

        review = await ask_json(f"Review this code:\n```python\n{code}\n```",
                                CRITIC_SYSTEM, CRITIC_SCHEMA, "sonnet")
        print("   critic:", review["verdict"],
              json.dumps(review["issues"], indent=1))
        if review["verdict"] == "accept":
            print("\nACCEPTED:\n" + code); return
        feedback = "Reviewer notes:\n- " + "\n- ".join(review["issues"])

    print(f"\nStopped after {MAX_ROUNDS} rounds. Last version:\n{code}")

if __name__ == "__main__":
    asyncio.run(main())