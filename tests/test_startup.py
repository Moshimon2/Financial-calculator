from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from fincalc import settings
from fincalc.api.main import create_app
from fincalc.db import session as db_session


@pytest.mark.parametrize(
    ("value", "expected"), [(None, True), ("1", True), ("0", False), ("false", False)]
)
def test_auto_migrate_flag(
    monkeypatch: pytest.MonkeyPatch, value: str | None, expected: bool
) -> None:
    if value is None:
        monkeypatch.delenv(settings.AUTO_MIGRATE_ENV, raising=False)
    else:
        monkeypatch.setenv(settings.AUTO_MIGRATE_ENV, value)
    assert settings.auto_migrate() is expected


def test_timezone_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(settings.TIMEZONE_ENV, raising=False)
    assert str(settings.display_timezone()) == "Europe/Budapest"


def test_startup_runs_migrations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv(settings.AUTO_MIGRATE_ENV, "1")
    monkeypatch.setenv(db_session.DATABASE_URL_ENV, url)
    db_session.get_engine.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get("/").status_code == 200  # dashboard reads the fresh DB
        with db_session.get_engine().connect() as conn:
            tables = set(inspect(conn).get_table_names())
        assert {"alembic_version", "imports", "transactions"} <= tables
    finally:
        db_session.get_engine().dispose()
        db_session.get_engine.cache_clear()
