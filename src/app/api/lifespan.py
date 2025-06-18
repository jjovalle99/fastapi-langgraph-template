from contextlib import asynccontextmanager
from typing import AsyncIterator, TypedDict

from anthropic import AsyncAnthropic
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langsmith.wrappers import wrap_anthropic
from loguru import logger
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings
from app.db import QueryStore, create_db_connection_pool
from app.graphs import create_chat_graph
from app.tools import get_tool_handler
from app.utils import PromptStore


class AppState(TypedDict):
    """Application state container for FastAPI.

    Holds essential resources needed throughout the application lifecycle.

    Attributes:
        pool: Database connection pool for database operations
        graph: Compiled LangGraph workflow for processing queries
        prompt_store: Jinja2 template handler for rendering prompts
        query_store: QueryStore for managing SQL queries
    """

    pool: AsyncConnectionPool
    graph: CompiledStateGraph
    prompt_store: PromptStore
    query_store: QueryStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    """Manages the application lifecycle and resources.

    Sets up all necessary resources when the application starts and
    properly cleans them up when the application shuts down. This includes:
    - Database connections
    - External service clients

    Args:
        app: The FastAPI application instance

    Yields:
        Application state containing resources
    """
    settings = get_settings()

    # Database setup
    pool = create_db_connection_pool(settings=settings)
    await pool.open()
    logger.info("Database pool ready")

    # Initialize external services
    anthropic_client = wrap_anthropic(
        client=AsyncAnthropic(
            api_key=settings.anthropic.api_key.get_secret_value()
        )
    )
    logger.info("Services initialized")

    # Initialize local services
    tool_handler = get_tool_handler()
    prompt_store = PromptStore(prompts_dir=settings.paths.prompts_dir)
    query_store = QueryStore(base_query_path=settings.paths.queries_dir)

    # Initialize the checkpointer
    checkpointer = AsyncPostgresSaver(conn=pool)  # type: ignore

    # Create and compile the graph
    graph = create_chat_graph(
        anthropic_client=anthropic_client,
        tool_handler=tool_handler,
        prompt_store=prompt_store,
        checkpointer=checkpointer,
    )

    yield {
        "pool": pool,
        "graph": graph,
        "prompt_store": prompt_store,
        "query_store": query_store,
    }

    # Cleanup
    logger.info("Shutting down services")
    await pool.close()
    await anthropic_client.close()
    logger.info("Shutdown complete")
