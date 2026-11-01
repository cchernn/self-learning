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