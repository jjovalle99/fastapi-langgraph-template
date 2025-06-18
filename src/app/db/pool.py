from psycopg_pool import AsyncConnectionPool

from app.config import Settings


def create_db_connection_pool(
    settings: Settings,
) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=settings.db.connection_string,
        open=False,
        min_size=0,
        max_size=3,
    )
