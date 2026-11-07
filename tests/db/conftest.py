from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import fincalc.db.models  # noqa: F401
from fincalc.db.session import make_engine


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
