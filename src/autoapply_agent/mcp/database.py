"""Read-only database access for the MCP server.

The server reuses the application's engine and session helpers
(:mod:`autoapply_agent.db.session`) and adds two guards so an assistant session can
never change the job database:

* every SQLite connection runs ``PRAGMA query_only = ON``, so SQLite itself rejects
  ``INSERT``/``UPDATE``/``DELETE``/DDL even if a future code path tried to write;
* a missing SQLite file is reported instead of being created empty, which is what
  SQLite would otherwise do on connect.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from autoapply_agent.db.session import create_engine, create_session_factory


def _enable_sqlite_query_only(dbapi_connection: Any, _connection_record: Any) -> None:
    """Make one new SQLite connection reject every write (``connect`` event hook)."""

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA query_only = ON")
    finally:
        cursor.close()


def open_read_only_database(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an engine and session factory for read-only access.

    Args:
        database_url: SQLAlchemy async database URL (the API's ``DATABASE_URL``).

    Returns:
        The engine (dispose it when done) and a session factory bound to it.
    """

    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _enable_sqlite_query_only)
    return engine, create_session_factory(engine)


def sqlite_file_path(database_url: str) -> Path | None:
    """Return the database file of a file-based SQLite URL.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        Absolute path of the database file (relative paths resolve against the current
        working directory, as SQLite does), or None for other databases, in-memory
        databases and ``file:`` URIs.
    """

    url = make_url(database_url)
    database = url.database
    if url.get_backend_name() != "sqlite" or not database or database == ":memory:":
        return None
    if database.startswith("file:") or url.query.get("uri"):
        return None
    return Path(database).absolute()


def describe_database_url(database_url: str) -> str:
    """Render a database URL for logs and error messages with any password masked."""

    return make_url(database_url).render_as_string(hide_password=True)
