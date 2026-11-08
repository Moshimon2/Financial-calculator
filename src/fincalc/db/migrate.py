"""Run Alembic migrations from code (used at application start-up)."""

from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


def upgrade_to_head(url: str | None = None) -> None:
    """Upgrade the database to the latest revision (no-op if already current)."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["configure_logger"] = False
    if url is not None:
        cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
