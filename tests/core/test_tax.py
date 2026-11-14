from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincalc.core.tax import (
    DEFAULT_TAX_CONFIG_PATH,
    TAX_CONFIG_ENV,
    load_tax_config,
    parse_tax_config,
)

D = Decimal

MINIMAL = """
regular_account: {pit_pct: 15, social_pct: 13}
tbsz:
  lock_years: 5
  tiers:
    - {min_lock_years: 0, pit_pct: 15, social_pct: 13}
    - {min_lock_years: 5, pit_pct: 0, social_pct: 0}
"""


def test_bundled_config_loads() -> None:
    assert DEFAULT_TAX_CONFIG_PATH.is_file()
    cfg = load_tax_config()
    assert cfg.regular_account.pit_pct == D(15)
    assert cfg.regular_account.social_pct == D(13)
    assert cfg.regular_account.total_pct == D(28)
    assert cfg.tbsz.lock_years == 5


@pytest.mark.parametrize(
    ("held", "pit", "social"),
    [(0, 15, 13), (2, 15, 13), (3, 10, 0), (4, 10, 0), (5, 0, 0), (30, 0, 0)],
)
def test_bundled_tbsz_tiers(held: int, pit: int, social: int) -> None:
    tier = load_tax_config().tbsz.rates_for(held)
    assert (tier.pit_pct, tier.social_pct) == (D(pit), D(social))


def test_rates_for_negative_years() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        parse_tax_config(MINIMAL).tbsz.rates_for(-1)


def test_explicit_path(tmp_path: Path) -> None:
    f = tmp_path / "tax.yaml"
    f.write_text(MINIMAL, encoding="utf-8")
    cfg = load_tax_config(f)
    assert cfg.tbsz.rates_for(4).pit_pct == D(15)
    assert cfg.last_verified is None


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "tax.yaml"
    f.write_text(MINIMAL.replace("pit_pct: 15, social_pct: 13}", "pit_pct: 20, social_pct: 13}", 1))
    monkeypatch.setenv(TAX_CONFIG_ENV, str(f))
    assert load_tax_config().regular_account.pit_pct == D(20)


@pytest.mark.parametrize(
    "bad",
    [
        MINIMAL.replace("min_lock_years: 0", "min_lock_years: 1"),
        MINIMAL.replace("min_lock_years: 5", "min_lock_years: 0"),
        MINIMAL.replace("pit_pct: 15, social_pct: 13}", "pit_pct: 150, social_pct: 13}", 1),
        MINIMAL + "unknown_key: 1\n",
    ],
)
def test_invalid_config(bad: str) -> None:
    with pytest.raises(ValidationError):
        parse_tax_config(bad)
