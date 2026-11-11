# AI Engineering

Daily AI Engineering lessons.  

## Day 1: Introduction to Agents  

### Concept
```
user goal
   ↓
model ──► wants a tool? ──no──► final answer
   ▲            │ yes
   │            ▼
   └── tool result ◄── YOUR code runs the tool
```  

Three things to understand:

1. The model never runs anything. It returns a tool_use block, which is a request. Your code executes it and sends back a tool_result.
2. stop_reason drives the loop. If it’s "tool_use", run the tools and call the model again. Anything else means the model is finished.
3. Workflow vs. agent. In a workflow, your code fixes the steps (e.g. step 1 summarize, step 2 translate). In an agent, the model picks the steps. Use a workflow when you can predict the path; it’s cheaper and more reliable. Use an agent when you can’t.

What to look for: two loop turns. The first ends with stop_reason: tool_use and the call `get_weather({'city': 'Kuala Lumpur'})`. The second ends with end_turn and an answer that uses the tool’s result.

Tweak to try: ask “Compare the weather in KL and Penang”. Watch whether the model asks for both tools in one turn (parallel calls) or one after the other. Then add a `max_turns` counter so the loop can’t run forever.


### Quiz  

1. What would break if you sent back only the tool_result and never appended the assistant’s `tool_use` message?
2. You need “fetch yesterday’s Bursa announcements → summarize → email me”, the same steps every day. Agent or workflow?
3. Why does the tool description matter as much as the code that implements it?

### Answers

1. The API rejects it, because every tool_result must match a tool_use_id from the previous assistant turn. The model also loses the record of what it asked for.
2. A workflow. The steps are fixed and known in advance, so hard-coding them is cheaper, faster and more predictable. You could still use a model inside the summarize step.
3. The description is the only information the model has about when and how to use the tool. A vague description leads to missed calls or wrong arguments, however good your implementation is. That’s Day 2.

## Day 2: Tool Design 1 - names, descriptions, schemas  

### Concept  

Names: use verb_noun, be specific  
Descriptions: write them like docs. Cover:  
- what it returns
- when to use it
- its limits  
Schemas: put as much meaning into types  
- `enum` whenever valid values are fixed set  
- `pattern`, `minimum`/`maximum` for format and range  
- leave optional fields out of `required`, give `default`, what happens if omitted  
- `"additionalProperties": False` so model can't invent extra arguments  
- `description` should include example  

### What to look for

in the [CALL] lines:
- “nvidia” should become NVDA (uppercase, no exchange prefix), because the description told it to.
- You should see three separate calls (NVDA 1d, AAPL 1d, AAPL 1h), because the description says one symbol per call.
- `lookback_bars=10` should appear for “last 10 days”, and on the hourly call it’ll probably leave the field out, so the default of 20 kicks in.
- The cost line is the SDK’s estimate. On a subscription it’s informational; you aren’t billed per call.

### Quiz
1. Your tool takes side for an order. The model sometimes sends "long" or "Buy" when you expect "buy"/"sell". What’s the most effective fix, and where does it go?
2. You have get_quote(symbol) and get_last_price(symbol), and they return nearly the same thing. What problem does this cause, and what would you do?
3. Should a description like “Use this only for US equities; for crypto use get_crypto_bars” go in the tool description or the system prompt? Why?

### Answers
1. Make it "enum": ["buy", "sell"] in the input schema. That shows the model the exact valid values. Still normalise or validate in the handler as a backstop, since the schema isn’t a guarantee.
2. The model can’t reliably tell them apart. It picks one more or less at random, and if you add a second similar pair you get confused trajectories and wasted calls. Merge them into one tool, or make the difference explicit in both the names and the descriptions (e.g. get_quote returns bid/ask/size, get_last_trade_price returns only the last trade).
3. The tool description. It’s guidance about using that specific tool, and the model reads it exactly when it’s choosing between tools. It also travels with the tool if you reuse it in another agent. The system prompt is for task-level goals and policy (Day 6).

## Day 3: Tool Design 2 - results, errors, idempotency, small outputs  

### Concept  
1. Return what the model needs, not what the API gives you
   - Summarise: 250 OHLC rows → last, min, max, change_pct, last_5
   - Use compact JSON with clear keys; drop internal IDs and noise
   - Cap or paginate big lists (limit, next_cursor)
   - Rule of thumb: a tool result should be a few hundred tokens, not thousands

2. Errors are instructions for the next turn
```
bad : "Error 400"
good: "Unknown symbol 'TSLA'. Supported: [AAPL, MSFT, NVDA]."
```
- Set `"is_error": True` so the model (and your logs) know it failed
- Say what went wrong, what’s valid, and whether anything changed (“No order placed”)
- Return errors; don’t raise. An uncaught exception gives the model an opaque failure

3. Idempotency = safe to retry
```
model → place_order(cid="NVDA-buy-2026-11-02")  → created
(timeout, retry, or model repeats itself)
model → place_order(cid="NVDA-buy-2026-11-02")  → duplicate_ignored
```
Agents repeat calls more often than you’d expect: retries, loops, or forgetting earlier turns. Any tool with side effects should take an idempotency key. Alpaca supports this natively via client_order_id.

### What to look for  
- ERR : on TSLA. The agent should read the message and move on (or tell you TSLA isn’t supported) instead of making up a price.
- NVDA is up about 1.8% over 20 days, so expect one created order.
- The repeat order returns duplicate_ignored, and the final line prints Orders on 'broker': 1.
- cost is a notional figure. On a subscription you aren’t billed per call, but it’s still a useful size signal.  

### Quiz
1. Your get_positions tool returns the raw broker JSON: 40 fields × 30 positions. What’s wrong with that, and what would you return instead?
2. Should a tool raise an exception or return is_error: True when the user asks for an invalid date range? Why?
3. Your agent called place_order, the HTTP request timed out, and the agent retried. Without idempotency, what can go wrong? Which tools in a trading agent need an idempotency key, and which don’t?

Reply here with your output, code or questions, and I’ll review them.

### Answers
1. It floods the context (thousands of tokens per call, re-sent on every later turn), slows the model down, and buries the signal. Return only the fields it needs to decide (symbol, qty, avg_price, market_value, unrealized_pl_pct), maybe sorted, with a limit parameter. Let it call a detail tool if it needs more.
2. Return is_error: True with an actionable message, e.g. “start must be before end; data available from 2021-01-04”. The model can read it and self-correct on the next turn. A raised exception gives an opaque failure and can’t teach the model how to fix the call. Save exceptions for real bugs in your own code.
3. The first order may have gone through even though the response was lost, so the retry places a second real order. Anything with side effects needs a key: place/cancel/modify order, sending alerts, writing files or records. Read-only tools (quotes, positions, history) are naturally idempotent and don’t need one.  

## Day 4: Inside the Agent Loop  
```
prompt ─► MODEL ──stop_reason="tool_use"──► run tool(s) ─► results
            ▲                                                │
            └───────────────── next turn ◄───────────────────┘
          stop_reason="end_turn" ─► ResultMessage (done)
```

- **Turn**: one model response, plus running whatever tools it asked for. One `AssistantMessage` in the stream is roughly one turn.  
- **max_turns**: a hard cap on turns. When the agent hits it, the run ends with `ResultMessage.subtype == "error_max_turns"` and no final answer. Always set it. It's your cheapest guard against runaway loops.  
- **Parallel tool calls**: in a single turn, the model can return several `ToolUseBlock`s. If a tool is marked `readOnlyHint=True` (it has no side effects), the runtime may run those calls at the same time. That means 3 quotes take about 1s instead of 3s. Never mark a tool that places orders as read-only.  
- **Stop reasons**: `tool_use` (the model wants tools, so the loop continues), `end_turn` (the model is done), `max_tokens` (the output was cut off).
- Two kinds of retry:
   1. Transport retries. The runtime retries API errors like 429 and 5xx automatically.
   2. Model retries. Your tool returns `is_error: True` with a helpful message, and the model decides whether to try again (Day 3). You stay in control by keeping the error text honest (“safe to retry” vs “don’t retry”).
- **Hooks**: `PreToolUse` and `PostToolUse` run in your Python around every tool call. They’re your window into the loop, and later (Day 13) your guardrails.

### What to look for:

1. **Turn 1**: the model asks for about 4 calls at once (3 prices + FX). The PRE timestamps should be close together, and the POSTs should land about 1s later, not 4s later. Overlapping timestamps mean the calls ran in parallel. Depending on how the SDK sends them, you may see each call in its own `AssistantMessage` with the same timing, so read the timestamps, not just the turn count.
2. **The retry**: one result shows ERROR for MSFT, and in the next turn the model asks for MSFT again.
3. **The end**: `subtype=success` and a small turn count (about 3).

### Quiz

1. Your agent ends with `subtype="error_max_turns"`. Name two likely causes, and say what you’d check in the message stream.
2. You have get_quote and place_order tools. Which should get readOnlyHint=True, and what could go wrong if you mark the wrong one?
3. A broker API returns HTTP 500. Should your tool retry internally, or return is_error and let the model decide? When would you choose each?

### Answers

1. Causes: the model keeps retrying a tool that never succeeds (look for repeated ERROR results with the same input), or the task needs more steps than the cap allows (look for steady progress with each turn). Also check whether the error messages give the model an unclear signal. Fix the tool’s error message, raise the cap, or split the task.
2. Only `get_quote`. Marking `place_order` read-only invites it to run in parallel and to be treated as safe to repeat, which could mean duplicate or conflicting orders. Side-effecting tools should run one at a time and be idempotent (Day 3).
3. Retry quick, transient errors inside the tool (1–2 tries with backoff) on read-only calls. That’s cheaper than spending a model turn. Return `is_error` when the failure persists, or when the call has side effects, so the model (or a human) decides. Never blindly retry `place_order`.

## Day 5: Context Engineering  

Context window is the agent's whole world. Everything the model knows on a turn has to fit inside it. Bloated context costs in 3 ways  
1. Pay for it
2. Slows every call  
3. Model reasons worse when signal is buried in noise  

```
┌─────────────────────────────────┐
│ system prompt                   │  stable   ← cached
│ tool definitions (names+schemas)│  stable   ← cached
├─────────────────────────────────┤
│ user msg 1                      │
│ assistant: tool_use             │  grows every turn
│ tool_result  (← the usual hog)  │
│ assistant: text                 │
│ user msg 2 ...                  │
└─────────────────────────────────┘
```

### Four levers of control  
1. Shrink at the source.
   - make tools return summaries  
2. Truncate and paginate
   - cap output size and return something like "truncated: 180 more rows, call again with offset=20"
3. Compaction
   - when long session nears limit, older turns get summarized into short recap
   - loses detail, so anything that must survive belongs in file or DB
4. Prompt caching
   - if start of window is identical to last turn, read from cache at fraction of cost and latency

### What to look for

- Compact mode: the hook reports about 150 chars per tool call. Turns 2–3 should show a large cache_read and a small uncached in, because the prefix was reused.
- Verbose mode: about 15,000 chars per call, and the totals jump on every later turn because both price dumps get re-sent each time. Turn 3 needs no tool call, but it still pays for every bar from turns 1–2.
- Answer quality: in verbose mode the model has to do drawdown maths in its head from raw numbers. Compare its answer with the exact max_dd_pct it gets in compact mode.
- Compaction: you probably won’t see COMPACTION with only 3 turns. That’s expected, because it only fires near the window limit.

### Quiz
1. Your agent calls a get_positions tool on every turn of a 30-turn session, and each call returns 8k tokens. Name two fixes, one at the tool level and one at the agent/design level.
2. You add f"Current time: {datetime.now()}" to the start of your system prompt. Why might latency and usage get noticeably worse?
3. After auto-compaction, your trading agent “forgets” the order ID it placed 20 turns ago. What’s the right fix, and why isn’t “turn off compaction” the answer?

### Answers
1. Tool level: return only what changed, or a summary (symbol, qty, P&L), with an optional filter or detail argument. Design level: don’t re-fetch on every turn. Fetch once, or only after an order is placed, and let the system prompt or plan say when a refresh is needed. Both fixes stop 30 × 8k of mostly duplicate tokens piling up in history.
2. Caching matches on an exact prefix. A value that changes every turn at the very start of the window invalidates the cache for everything after it: the tool definitions and the whole history. Put dynamic facts at the end (in the user message), or expose them through a get_time tool.
3. Write critical state to durable storage the moment it’s created, such as a file, DB or “notes” tool, and read it back when needed (more on this Day 12). Turning compaction off just means the session hits the hard context limit and fails, and long contexts degrade the model’s reasoning anyway. Treat the context as working memory and storage as the source of truth.

## Day 6: System prompt for agents  

System prompt says *how the agent should work*, its role, rules, the order of steps and what "done" looks like.  

### Concept  
```
Tool description  → what this tool does, its inputs,
                    when to use it (local, per tool)
System prompt     → who you are, global rules, the plan,
                    when to stop, output format
User prompt       → this specific task
```

A good agent system prompt has 4 parts
1. **Role**: who it serves and what it's for  
2. **Rules / limits**: hard constraints eg. *read-only*  
3. **Plan**: numbered steps plus an explicit stop condition  
4. **Output contract**: exact shape of final answer  

in Claude Code, adding to existing system prompt:
```
system_prompt={"type": "preset", "preset": "claude_code", "append": "Extra rules ..."}
```

### What to look for  

- The correct total is $11,768.00 (20×231.4 + 50×142.8). Check that both runs get it.
- A usually calls `get_price("MSFT")`, gives a chatty answer and maybe some investment opinion. Its format changes from run to run.
- B should make exactly 1 + 2 tool calls, ideally with the two prices in the same turn, then print a clean table.
- Compare `turns` and `cost` across the two runs. Run each 2–3 times to see how much the output varies.

### Quiz
1. You want the agent to always pass tickers in uppercase to get_price. Does that go in the system prompt or the tool definition, and why?
2. Your agent keeps calling get_price again “to confirm” after it already has the data. Which part of the system prompt is missing?
3. You’re building a narrow trading bot with custom tools only. Should you pass a plain string or the claude_code preset with append? What changes?

### Answers
1. The tool definition. It’s a per-tool input rule, so put it in the parameter description (or a pattern/enum), or better, just .upper() it in the handler as we did. The system prompt is for rules that span tools.
2. The stop condition. Add an explicit “after step N, stop, no further tool calls” plus a clear output contract so the model knows what “done” looks like.
3. A plain string. It replaces Claude Code’s large default prompt (coding instructions, file-tool guidance), which uses fewer tokens and avoids behaviour you don’t want. Use the preset with append only when you want Claude Code’s coding-agent behaviour plus your additions.

## Day 7: Mini-project - Research Agent (Web search + notes tool)  

### Concept  
Agent writes what it learns to external notepad instead of keeping in context window
```
question
  │
  ▼
WebSearch (≤3) ──► WebFetch (≤3 pages)
                       │  big page text (lives in context briefly)
                       ▼
                 save_note(key, fact, source)  ← small, cited, on disk
                       │
                       ▼
                 list_notes ──► final answer citing [key]
```
Design choices:
- Built-ins limited with `tools=[...]`. Agent only has WebSearch and WebFetch, no Bash and file edits.
- Idempotent notes. Saving to same `key` overwrites old note, avoiding duplicates.  
- Errors model can act on. Source that isn't a URL comes back as `is_error` with clear reason.  
- Small outputs  
- budget in prompt plus `max_turns`.
- Answer only from notes.  

### What to look for  

- Each step prints as 🔧 (tool call) and then ✅ or ❌ (result). You should see searches, then fetches, then several save_note calls, then one list_notes, and finally the 💬 answer with [key] citations.
- Check the size of each result. WebFetch results are large and save_note results are tiny. That gap is the context-engineering point of this lesson.
- Open research_notes.json afterwards. It’s your audit trail.
- The final line shows turns= and the cost. On your subscription the cost is a notional figure, not a bill.

### Quiz (today)
1. Why have the agent answer from list_notes instead of from the pages it just read?
2. The agent saves key="mcp_launch", then later finds a better source and saves the same key again. Is that a bug?
3. You set max_turns=15, but the prompt says “at most 3 searches, 3 fetches”. Why have both?

### Week 1 review quiz
4. Give one sign that a task should be a fixed workflow rather than an agent.
5. Two tools are called get_data and fetch_info. What’s wrong, and how would you fix it?
6. When should a tool return is_error: True instead of raising an exception?
7. Can the model run several tool calls in one turn? What should you mark a tool as so they can safely run in parallel?
8. Which belongs in the system prompt and which in a tool description: (a) “the source must be a URL”; (b) “do the research in 4 steps”?

### Answers
1. The pages are large and get crowded out or compacted as the context fills. The notes are small, cited and checkable, and every claim in the answer traces back to a URL.
2. No, it’s by design. The tool is idempotent, so the same key means a correction and you get no duplicates.
3. The prompt budget is a soft limit the model usually follows. max_turns is the hard stop if the model ignores the prompt or gets stuck in a loop.
4. The steps are known in advance and always the same (for example: fetch prices, then compute signals, then email). Use an agent only when the next step depends on what it found.
5. The names are vague and overlap, so the model can’t tell which to use. Use specific, verb-first names with clear descriptions, such as get_ohlc_bars(symbol, timeframe) and get_company_profile(symbol).
6. For expected, recoverable problems the model can fix (bad arguments, not found, rate limited). Write a message that says what to do differently. Raise an exception only for real bugs.
7. Yes. Mark read-only, side-effect-free tools with readOnlyHint=True (tool annotations) so the SDK can run them at the same time.
8. (a) goes in the tool description, because it’s a rule about that tool’s input. (b) goes in the system prompt, because it’s the agent’s overall plan.

## Day 8: Model Context Protocol (MCP)  

### Concept  
#### Three roles
```
 HOST (the app: your SDK script, Claude Code)
  ├─ CLIENT ──stdio──► SERVER A (fetch, a local process)
  ├─ CLIENT ──http───► SERVER B (remote, e.g. a SaaS)
  └─ CLIENT ──in-proc► SERVER C (your @tool funcs)
```
- **Host**: app that runs the model and decides what reaches the context window  
- **Client**: one connection per server: created by host. Speaks JSON-RPC  
- **Server**: program that exposes capabilities. It never sees the model, only requests coming in  

#### Transports  
- **stdio**: server starts as subprocess. This is usual choice for local tools  
- **Streamable HTTP**: for remote servers, usually need OAuth  
- **SDK**: no subprocess. Fastest option  

#### Lifecycle  
`initialize` (handshake + capabilities) -> `tools/list` (discovery) -> `tools/call` (repeated) -> shutdown  

Three primitives:  

Primitive | Controlled by | Example
--- | --- | ---
Tools	| the model decides to call them	| get_quote(symbol)
Resources | the app/user attaches them as context | file://watchlist.csv
Prompts | the user picks a template | “/daily-brief”

### What to look for  

- Two [server] lines, both connected. Fetch lists ['fetch'] and notes lists ['save_note']. That’s discovery working.
- [call] mcp__fetch__fetch, followed by two mcp__notes__save_note calls. The model treats both servers the same way; it can’t tell which one is in-process.
- If fetch shows failed, read the error. It’s almost always a missing uvx on PATH, which is the most common MCP setup problem.  

### Quiz
1. Your SDK script connects to 3 MCP servers. How many hosts, clients and servers are there?
2. You want to expose (a) “place a paper-trade order”, (b) your static list of tickers to watch, and (c) a “weekly portfolio review” template you start manually. Which MCP primitive fits each one?
3. A teammate wants your market-data tools usable from both Claude Code on their laptop and a shared server agent. Should you build them with create_sdk_mcp_server or as a standalone MCP server? Why?

### Answers
1. 1 host (your script / the Claude Code process it drives), 3 clients (one per connection), 3 servers.
2. (a) Tool, because it has side effects and the model decides when to call it. (b) Resource, because it’s read-only data the app attaches. (c) Prompt, because it’s a template a user triggers.
3. A standalone server (stdio for local use, HTTP for shared use). create_sdk_mcp_server only runs inside your own Python process, so other hosts can’t connect to it. In-process is great for tools that belong to a single script; standalone is for tools you want to reuse across apps.  

## Day 9: Build standalone MCP Server  

### Concept  
```
 Host (Agent SDK / Claude Code)
   └─ MCP client ──stdio (JSON-RPC)──▶ risk_server.py
                                        ├─ tool:     position_size
                                        ├─ resource: risk://rules
                                        └─ prompt:   trade_review
```
- **stdio transport**: host starts script as subprocess and sends JSON over stdin and stdout. Never `print()` to stdout inside a stdio server because it corrupts the protocol, log to stderr instead
- **in-process vs standalone**
- official `mcp` package is now **v2** and `FastMCP` was renamed `MCPServer`  
- type hints plus `pydantic.Field` generation the JSON Schema

### What to look for

- The init line should show risk with status connected. If it shows failed, run python risk_server.py directly and look for errors on stderr.
- AAPL comes back as 40 shares (risk $200 ÷ $5 per share).
- TSLA comes back with error=True, because the stop is above entry for a long. Watch how Claude reacts: does it explain the problem, or retry as a short? That’s your error message doing its job.

### Quiz

1. Your stdio server works on its own, but the agent reports it as failed or it hangs on the first call. You added print("server starting") at the top. What’s wrong?
2. When would you keep a tool in-process (create_sdk_mcp_server) instead of making it a standalone MCP server?
3. The house risk rules: should they be a tool, a resource, or text in the system prompt? Argue it briefly.

### Answers

1. print writes to stdout, which is the JSON-RPC channel, so the host gets non-protocol bytes. Log to stderr instead (print(..., file=sys.stderr) or logging).
2. In-process makes sense when only this one script uses the tool and you want zero subprocess overhead or simpler deployment. It’s also the easy way to give the tool direct access to your script’s live objects, like a pandas DataFrame already in memory or a broker client. Go standalone when several hosts need the tool, or when you want to test and version it on its own.
3. There’s no single right answer. A resource suits read-only context the host or user chooses to attach, and it keeps the rules in one place. If the agent must always follow the rules, put the short version in the system prompt, or better, enforce them in code: a tool that refuses oversized trades. A model reading a rule is advice; code checking it is a guarantee. Use a tool only when the model needs to fetch or check rules on demand.

## Day 10: Code Execution as a tool  

Never ask whether to let it run code. Decide where the code runs, what it can touch, and who approves it.  

### Concept  
Two ways to give agent code execution  
1. **Your own tool**. Control the whole process  
2. **The SDK's built in `Bash` tool**. 

#### Layers of defence  
```
model writes code
   │
   ▼
[1] Tool surface   tools=[...]  (does Bash even exist?)
[2] Permission     hooks → deny rules → permission_mode
                   → allow rules → can_use_tool (you/human)
[3] Process limits timeout, CPU, memory, file size, no fork bombs
[4] Isolation      throwaway cwd, empty env, OS sandbox
                   (no network, writes only in cwd), or a container
[5] Output         truncate + is_error so the model can fix itself
```

#### Permission modes  
- default: anything that isn’t pre-approved goes to your can_use_tool callback
- acceptEdits: file edits are auto-approved, other tools still get checked
- plan: the agent plans only and executes nothing
- dontAsk: never prompts; anything not in allowed_tools is denied (good for unattended scripts)
- auto: a model classifier approves or denies each call
- bypassPermissions: everything runs. Only use it inside a disposable container.  

### Exercise A - a hardened `run_python` tool  
What to look for: the agent writes a drawdown script, runs it, and answers. The correct answer is max drawdown ≈ −15.5%, bottoming at index 7 (110 → 93). If it tries import pandas, it gets an is_error result and should rewrite the script in pure Python. That’s the Day 3 self-correction loop in action.

### Exercise B - built in Bash, gates by you and OS sandbox  

### Quiz
1. You put "Bash" in allowed_tools and also wrote a can_use_tool callback that blocks rm. The agent runs rm notes.txt anyway. Why?
2. Your nightly agent runs unattended from a scheduler. Which permission mode fits best, and why not default?
3. Your run_python tool has a 5s timeout and a 512 MB memory cap. Name two things malicious or buggy code could still do, and the layer that stops each.

### Answers
1. Anything in allowed_tools is pre-approved, and allow rules are checked before can_use_tool, so your callback never ran. Fix it by removing Bash from allowed_tools, or use a deny rule or PreToolUse hook, since those are checked first.
2. Use dontAsk with a tight allowed_tools list. In default, anything not pre-approved goes to a permission prompt, and with nobody watching the run would just hang or fail. dontAsk denies anything not pre-approved, so the run is safe and predictable. Avoid bypassPermissions unless you’re in a throwaway container.
3. Examples: read files outside the temp dir (e.g. ~/.ssh, your .env) or make network calls to exfiltrate data. Rlimits and an empty env don’t stop either one. You need OS/container isolation: the SDK sandbox with an empty allowedDomains and restricted filesystem, or Docker with --network none and a read-only mount.  

## Day 11: Retrieval as a tool - agentic search vs classic RAG  

Two Ways to Do it:  
```
CLASSIC RAG (one shot, you pick)
question → embed → top-k chunks → stuffed into prompt → answer

AGENTIC SEARCH (a loop, the model picks)
question → Glob("**/*.md") → Grep("stop|exit") → Read(file) → maybe Grep again → answer
```  

**Agentic search** (the SDK's built-in Grep/Glob/Read tools):
- no index to build or keep up to date  
- read whole files, keeping context around a match  
- exact matches work well  
- only finds words it thinks to search for  
- takes more turns, costs more time and tokens  

**Classic RAG** (chunk the docs, embed, and return nearest k chunks):
- one fast call, matches on meaning when using real embeddings  
- scales to corpora too big to grep  
- chunking cuts context apart  
- index goes stale, does badly on exact identifiers  

### What to look for
- Agentic: the -> lines show the strategy: a Glob, then Grep with patterns the model invents (e.g. stop|exit|loss), then Reads. Count the turns.
- RAG: usually 1–2 calls and fewer turns. Look at what comes back. I tested the handler: with the raw question it returns broker_api.md and the breakout entry chunk, and misses the 3×ATR stop and “cut losers fast”, because word overlap isn’t meaning. The model only does better if it rewrites the query (e.g. “stop loss exit”).
- Compare the citations: whole files (agentic) vs #chunk fragments (RAG).

### Quiz
1. Your agent has to answer questions over a 40-file strategy repo that changes every day. Agentic search or a vector index? Why?  
2. A RAG tool returns "Risk: initial stop at the breakout bar low" and the agent attributes it to the wrong strategy. What went wrong, and give two fixes.  
3. Users ask “what did I lose on earnings plays?” but your journal says “gap down post-results”. Which approach struggles, and what would you add?  

### Answers  
1. Agentic search. The repo is small, there’s no index to rebuild every day, files are always current, and it handles exact names like tickers and functions well.
2. Chunking cut the chunk off from its context (the # Breakout strategy header is in a different chunk). Fixes: add the doc title or section heading to every chunk (contextual chunking); return the source file and let the agent Read the full file; use bigger or overlapping chunks.
3. Lexical approaches struggle: grep and bag-of-words both miss the synonyms “loss/earnings” vs “gap down/results”. Add real embeddings (semantic search) as a tool, or tell the agent in the tool description or system prompt to try synonyms. Hybrid (keyword + embeddings) is the robust default.  

## Day 12: Memory - short-term vs long-term  

### Concept  
1. **Short-term memory = context window**  
Each `query()` call creates a *session*, which is a transcript the SDK saves to disk. The `ResultMessage` gives you the `session_id`. 
- `resume=session_id` -> carry on with full history loaded  
- `fork_session=True` -> branch off a copy and leave the original as is  
- `continue_conversation=True` -> resume most recent session in folder  

2. **Long-term memory = something outside the model (file or DB)**  
```
          ┌── session (short-term) ──┐
user ───▶ │ history in context window │ ──resume──▶ same chat later
          └─────────┬────────────────┘
          remember()│   ▲ recall()
                    ▼   │
          ┌── store (long-term) ─────┐
          │ JSON / SQLite / files    │  ◀── any future session
          └──────────────────────────┘
```
What to store:  
- store durable facts: preferences, rules, account settings, decisions that were made  
- don't store: chit-chat, today's prices, anything that goes stale fast  
- use stable keys so saving again overwrites old values. 
- read memory at moment of the task, using `recall`, rather than putting whole store into the system prompt every time. This is just-in-time context.  

### What to look for

- A: the agent should call remember (probably risk_per_trade, category rule, and maybe market_focus).  
- B: session= shows the same id as A. The agent can answer from the conversation history, so it may not call recall at all.  
- C: you get a new session id with no history. The agent can only answer by calling recall, which reads the file. That’s long-term memory doing its job.  
- At the end, open agent_memory.json and check what the agent decided was worth keeping.  

### Quiz  
1. Your agent resumes one session every day for a month, and its answers get slower and vaguer. Why, and what should you change?
2. Would you store “AAPL closed at $231 today” with remember? Why or why not?
3. Why give remember a stable key that overwrites, rather than appending every fact to a list?

### Answers
1. The session history keeps growing. You resend more tokens each time, and compaction summaries lose detail, so older facts get blurry. Use short sessions for each task, and keep durable facts in long-term memory that the agent fetches with recall when it needs them.
2. No. A price goes stale within hours, and a saved one invites the agent to use an old number. Fetch live data with a tool. Store only durable facts, like “prefers limit orders”.
3. Keys make writes idempotent. If you change your rule to 0.5%, the old 1% is replaced instead of both sitting in memory and contradicting each other, and the store stays small.