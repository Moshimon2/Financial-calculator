"""Shared fixtures. Tests never touch ./data: in-memory SQLite, no auto-migration."""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

os.environ["FINCALC_AUTO_MIGRATE"] = "0"
os.environ["FINCALC_DATABASE_URL"] = "sqlite://"
os.environ["FINCALC_TIMEZONE"] = "Europe/Budapest"

import fincalc.db.models  # noqa: F401
from fincalc.api.main import create_app
from fincalc.db.session import get_session, make_engine


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = make_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    with TestClient(app) as c:
        yield c
