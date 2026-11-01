import os
import logging
import asyncio
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

PROMPT = "Should I bring an umbrella in KL today?"

@tool(
    "get_weather",
    "Get the current weather for a city. Use when the user asks about weather or what to wear.",
    {
        "city": str
    },
)
async def get_weather(args):
    return {
        "content": [{
            "type": "text",
            "text": f"{args['city']}: 31°C, 80% chance of afternoon thunderstorms"
        }]
    }

SERVER = create_sdk_mcp_server(
    name="weather",
    version="1.0.0",
    tools=[get_weather]
)
OPTIONS = ClaudeAgentOptions(
    mcp_servers={"weather": SERVER},
    tools=[],
    allowed_tools=["mcp__weather__get_weather"],
    max_turns=5,
)

async def main():
    async for msg in query(prompt=PROMPT, options=OPTIONS):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    logger.info(f"MODEL -> tool_use   {b.name}({b.input})")
                elif isinstance(b, TextBlock):
                    logger.info(f"MODEL -> text       {b.text[:80]}")
        elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
            for b in msg.content:
                if isinstance(b, ToolResultBlock):
                    logger.info(f"YOUR CODE -> result {b.content}")
        elif isinstance(msg, ResultMessage):
            logger.info(f"\nDONE ({msg.subtype}) in {msg.num_turns} turns\n{msg.result}")


if __name__ == "__main__":
    logger.info("Starting day1 script")
    asyncio.run(main())
    logger.info("End day1 script")