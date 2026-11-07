from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlmodel import SQLModel

import fincalc.db.models  # noqa: F401
from fincalc.db.session import DATABASE_URL_ENV, make_engine

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Config, str]:
    url = f"sqlite:///{tmp_path / 'sub' / 'test.db'}"
    monkeypatch.setenv(DATABASE_URL_ENV, url)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    return cfg, url


def test_upgrade_matches_models_and_downgrade(alembic_cfg: tuple[Config, str]) -> None:
    cfg, url = alembic_cfg
    command.upgrade(cfg, "head")
    engine = make_engine(url)
    with engine.connect() as conn:
        assert {"imports", "transactions"} <= set(inspect(conn).get_table_names())
        diff = compare_metadata(
            MigrationContext.configure(conn, opts={"compare_type": True}), SQLModel.metadata
        )
        assert diff == []

    command.downgrade(cfg, "base")
    with engine.connect() as conn:
        assert "transactions" not in inspect(conn).get_table_names()
    engine.dispose()
