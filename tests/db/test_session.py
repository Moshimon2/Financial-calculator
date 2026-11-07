from pathlib import Path

import pytest
from sqlmodel import Session, text

from fincalc.db import session as db_session


def test_database_url_default_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(db_session.DATABASE_URL_ENV, raising=False)
    assert db_session.database_url() == db_session.DEFAULT_DATABASE_URL
    monkeypatch.setenv(db_session.DATABASE_URL_ENV, "sqlite:///x.db")
    assert db_session.database_url() == "sqlite:///x.db"


def test_get_session_creates_folder_and_enables_fks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "nested" / "app.db"
    monkeypatch.setenv(db_session.DATABASE_URL_ENV, f"sqlite:///{db_file}")
    db_session.get_engine.cache_clear()
    try:
        gen = db_session.get_session()
        s = next(gen)
        assert isinstance(s, Session)
        assert s.exec(text("PRAGMA foreign_keys")).one()[0] == 1  # type: ignore[call-overload]
        gen.close()
        assert db_file.parent.is_dir()
    finally:
        db_session.get_engine().dispose()
        db_session.get_engine.cache_clear()
