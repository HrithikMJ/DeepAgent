import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent
import constants as c
from langchain_openai import AzureChatOpenAI
from agents import create_agent
import json
import asyncio
import pprint

async def main():
    agent = create_agent()
    # Print the agent's response
    while True:
        user_input = input("Enter your prompt: ")
        print("-"* 50)
        print()
        if user_input == "exit":
            break
        result = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]})
        print(result["messages"][-1].content)
        print("-"* 50)
        print()

if __name__ == "__main__":
    asyncio.run(main())