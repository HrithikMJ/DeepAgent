import llm as l
import constants as c
from langchain_postgres.v2.async_vectorstore import AsyncPGVectorStore
from langgraph.store.postgres.aio import AsyncPostgresStore
from langchain_postgres.v2.engine import PGEngine
import asyncpg
from loguru import logger
from urllib.parse import urlparse

async def create_vector_store():
    # pg_engine = PGEngine.from_connection_string(url=c.CONNECTION_STRING)
    
    # # Check if table exists before initializing
    # # Convert SQLAlchemy connection string to asyncpg format
    # conn_str = c.CONNECTION_STRING.replace("postgresql+asyncpg://", "postgresql://")
    # parsed = urlparse(conn_str)
    
    # # Check if table exists
    # conn = await asyncpg.connect(
    #     host=parsed.hostname,
    #     port=parsed.port or 5432,
    #     user=parsed.username,
    #     password=parsed.password,
    #     database=parsed.path.lstrip("/")
    # )
    
    # table_exists = await conn.fetchval(
    #     """
    #     SELECT EXISTS (
    #         SELECT FROM information_schema.tables 
    #         WHERE table_schema = 'public' 
    #         AND table_name = 'agent_memory'
    #     );
    #     """
    # )
    # await conn.close()
    
    # # Only initialize if table doesn't exist
    # if not table_exists:
    #     await pg_engine.ainit_vectorstore_table(
    #         table_name="agent_memory",
    #         vector_size=1536,
    #     )
    # else:
    #     logger.info("Table already exists, skipping initialization")
    store_ctx = AsyncPostgresStore.from_conn_string(c.CONNECTION_STRING)
    return store_ctx