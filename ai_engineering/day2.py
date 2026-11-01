import os
import logging
import asyncio
import random
from claude_agent_sdk import (
    query,
    tool,
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    AssistantMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

PROMPT = "Compare how nvidia and apple moved over the last 10 days, and give me AAPL on hourly bars too."
PRICE_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Ticker in UPPERCASE, e.g. 'AAPL' or 'BTCUSD'. No exchange prefix.",
            "pattern": "^[A-Z.]{1,10}$",
        },
        "interval": {
            "type": "string",
            "enum": ["1d", "1h", "15m"],
            "description": "Bar size. Use '1d' unless the user asks for intraday.",
        },
        "lookback_bars": {
            "type": "integer",
            "minimum": 1, "maximum": 200, "default": 20,
            "description": "How many most-recent bars to summarise. Optional; default 20.",
        },
    },
    "required": ["symbol", "interval"],
    "additionalProperties": False,
}

@tool(
    "get_price_summary",
    "Summarise recent OHLC price bars for one ticker: last close, % change "
    "over the window, high and low. Use for questions about recent price moves. "
    "Does not return news or fundamentals. One symbol per call.",
    PRICE_SCHEMA,
)
async def get_price_summary(args):
    symbol = args["symbol"]
    interval = args["interval"]
    n = args.get("lookback_bars", 20)          # optional -> default
    rng = random.Random(f"{symbol}{interval}")  # fake, repeatable data
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(round(closes[-1] * (1 + rng.uniform(-0.02, 0.02)), 2))
    chg = (closes[-1] / closes[0] - 1) * 100
    text = (f"{symbol} {interval} x{n}: last={closes[-1]} "
            f"change={chg:+.2f}% high={max(closes)} low={min(closes)}")
    return {"content": [{"type": "text", "text": text}]}

SERVER = create_sdk_mcp_server(
    name="market",
    version="1.0.0",
    tools=[get_price_summary]
)
OPTIONS = ClaudeAgentOptions(
    mcp_servers={"market": SERVER},
    tools=[],
    allowed_tools=["mcp__market__get_price_summary"],
    max_turns=5,
    model="haiku",
)

async def main():
    async for msg in query(prompt=PROMPT, options=OPTIONS):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    logger.info(f"\n[CALL] {b.name} input={b.input}")
                elif isinstance(b, TextBlock):
                    logger.info(f"\n[CLAUDE] {b.text}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    logger.info(f"[RESULT] {b.content}")
        elif isinstance(msg, ResultMessage):
            logger.info(f"\n[DONE] turns={msg.num_turns} cost=${msg.total_cost_usd}")


if __name__ == "__main__":
    logger.info("Starting day2 script")
    asyncio.run(main())
    logger.info("End day2 script")