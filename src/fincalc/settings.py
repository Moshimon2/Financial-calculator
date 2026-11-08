"""Runtime settings from environment variables (see .env.example)."""

import os
from zoneinfo import ZoneInfo

TIMEZONE_ENV = "FINCALC_TIMEZONE"
AUTO_MIGRATE_ENV = "FINCALC_AUTO_MIGRATE"
DEFAULT_TIMEZONE = "Europe/Budapest"


def display_timezone() -> ZoneInfo:
    """Timezone used to show dates in the UI (data is stored in UTC)."""
    return ZoneInfo(os.environ.get(TIMEZONE_ENV) or DEFAULT_TIMEZONE)


def auto_migrate() -> bool:
    """Run Alembic migrations on application start (default: yes)."""
    return os.environ.get(AUTO_MIGRATE_ENV, "1").strip().lower() not in {"0", "false", "no"}
