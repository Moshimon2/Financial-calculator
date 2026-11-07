"""Engine and session handling.

The database URL comes from $FINCALC_DATABASE_URL (default: SQLite file in ./data).
"""

import os
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine

DATABASE_URL_ENV = "FINCALC_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///./data/fincalc.db"


def database_url() -> str:
    return os.environ.get(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(url: str, **kwargs: Any) -> Engine:
    """Create an engine; for SQLite, ensure the folder exists and enforce foreign keys."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        if parsed.database and parsed.database != ":memory:":
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    engine = create_engine(url, **kwargs)
    if parsed.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return make_engine(database_url())


def get_session() -> Generator[Session]:
    """FastAPI dependency: one session per request."""
    with Session(get_engine()) as session:
        yield session
