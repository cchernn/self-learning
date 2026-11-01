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