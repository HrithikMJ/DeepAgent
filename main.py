from deep_agents import create_agent
import asyncio
from kb import create_vector_store
from loguru import logger


async def main():
    store = await create_vector_store()
    async with store as store:
        await store.setup()
        agent = create_agent(store)

        # Print the agent's response
        logger.info("Agent started")
        while True:
            user_input = input("Enter your prompt: ")
            print("-" * 50)
            print()
            if user_input == "exit" or user_input == "quit":
                break

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config={"configurable": {"thread_id": "123451", "user_id": "123452"}},
                context={"user_id": "123452"},
            )
            logger.info(f"Agent response: {result}")
            print(result["structured_response"]["response"])
            print("-" * 50)
            print()


if __name__ == "__main__":
    logger.remove()
    logger.add("logs/agent_{time}.log", rotation="10 MB", retention="10 days")

    asyncio.run(main())
