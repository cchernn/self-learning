"""Day 18: parallel fan-out + aggregation.
Runs on your subscription. Keep ANTHROPIC_API_KEY unset!"""
import asyncio, random, time
from claude_agent_sdk import (
    query, ClaudeAgentOptions, ResultMessage, tool, create_sdk_mcp_server,
)

# 1. Fake price tool (no network, same numbers every run)
def make_server():
    # Fresh server per worker: each query() is its own process,
    # so don't share one in-process server object across concurrent runs.
    @tool("get_closes", "Last 10 daily closing prices for a US stock symbol.",
          {"type": "object",
           "properties": {"symbol": {"type": "string", "description": "e.g. AAPL"}},
           "required": ["symbol"]})
    async def get_closes(args):
        sym = args["symbol"].upper()
        if sym not in {"AAPL", "MSFT", "NVDA", "FLAKY"}:
            return {"content": [{"type": "text", "text": f"Unknown symbol {sym}"}],
                    "is_error": True}
        rnd = random.Random(sym)
        px, closes = 100.0, []
        for _ in range(10):
            px *= 1 + rnd.uniform(-0.03, 0.03)
            closes.append(round(px, 2))
        return {"content": [{"type": "text", "text": str(closes)}]}
    return create_sdk_mcp_server("mkt", tools=[get_closes])

# Workers return compact JSON, so aggregation is plain Python
WORKER_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "trend": {"type": "string", "enum": ["up", "down", "flat"]},
        "pct_change": {"type": "number"},
        "note": {"type": "string", "description": "max 15 words"},
    },
    "required": ["symbol", "trend", "pct_change", "note"],
}

# 2. One worker = one query() call
async def run_worker(symbol: str, attempt: int) -> dict:
    if symbol == "FLAKY" and attempt == 1:
        raise RuntimeError("simulated worker crash")  # to exercise retries

    opts = ClaudeAgentOptions(
        model="haiku",                 # cheap, fast workers
        tools=[],                      # no built-in tools
        mcp_servers={"mkt": make_server()},
        allowed_tools=["mcp__mkt__get_closes"],
        max_turns=4,
        system_prompt="You are a terse market analyst. Use get_closes, then answer.",
        output_format={"type": "json_schema", "schema": WORKER_SCHEMA},
    )
    result = None
    async for msg in query(prompt=f"Analyse {symbol}'s 10-day trend.", options=opts):
        if isinstance(msg, ResultMessage):
            result = msg
    # A run can "finish" without succeeding (e.g. error_max_turns)
    if result is None or result.is_error or result.structured_output is None:
        sub = result.subtype if result else "no result"
        raise RuntimeError(f"worker ended badly: {sub}")
    return {**result.structured_output, "cost": result.total_cost_usd or 0}

# 3. Wrap each worker: concurrency limit, timeout, retry
SEM = asyncio.Semaphore(2)   # max 2 CLI processes at once

async def guarded(symbol: str, retries: int = 1, timeout: float = 90) -> dict:
    for attempt in range(1, retries + 2):
        try:
            async with SEM:
                t0 = time.perf_counter()
                out = await asyncio.wait_for(run_worker(symbol, attempt), timeout)
                print(f"  ok   {symbol:6} attempt {attempt} "
                      f"{time.perf_counter() - t0:5.1f}s")
                return out
        except Exception as e:           # TimeoutError lands here too
            print(f"  FAIL {symbol:6} attempt {attempt}: {e!r}")
            if attempt <= retries:
                await asyncio.sleep(2 ** attempt)  # backoff OUTSIDE the semaphore
    raise RuntimeError(f"{symbol}: gave up")

# 4. Fan out, gather, aggregate
async def main():
    symbols = ["AAPL", "MSFT", "NVDA", "FLAKY", "ZZZZ"]
    t0 = time.perf_counter()
    results = await asyncio.gather(*(guarded(s) for s in symbols),
                                   return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]
    failed = [s for s, r in zip(symbols, results) if isinstance(r, Exception)]

    print(f"\n{len(ok)}/{len(symbols)} succeeded in "
          f"{time.perf_counter() - t0:.1f}s wall time")
    for r in sorted(ok, key=lambda r: r["pct_change"], reverse=True):
        print(f"  {r['symbol']:6} {r['trend']:5} {r['pct_change']:+6.2f}%  {r['note']}")
    if failed:
        print("  missing:", ", ".join(failed), "(report as partial result)")
    print(f"  total cost (API-equivalent): ${sum(r['cost'] for r in ok):.4f}")

if __name__ == "__main__":
    asyncio.run(main())