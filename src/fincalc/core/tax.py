"""Loading and querying the Hungarian tax configuration (config/tax_hu.yaml).

Loading touches the filesystem; the calculators themselves take a ``TaxConfig``
argument so they stay pure.
"""

import os
from decimal import Decimal
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

TAX_CONFIG_ENV = "FINCALC_TAX_CONFIG"
DEFAULT_TAX_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "tax_hu.yaml"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaxRates(_Model):
    pit_pct: Decimal = Field(ge=0, le=100, description="Personal income tax (SZJA) in %")
    social_pct: Decimal = Field(ge=0, le=100, description="Social contribution tax in %")

    @property
    def total_pct(self) -> Decimal:
        return self.pit_pct + self.social_pct


class TbszTier(TaxRates):
    min_lock_years: int = Field(ge=0)


class TbszRules(_Model):
    lock_years: int = Field(ge=1)
    tiers: list[TbszTier] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_tiers(self) -> Self:
        years = [t.min_lock_years for t in self.tiers]
        if years != sorted(set(years)):
            raise ValueError("tbsz tiers must have strictly increasing min_lock_years")
        if years[0] != 0:
            raise ValueError("the first tbsz tier must start at min_lock_years: 0")
        return self

    def rates_for(self, lock_years_held: int) -> TbszTier:
        """Tax tier applying after ``lock_years_held`` full lock years."""
        if lock_years_held < 0:
            raise ValueError("lock_years_held must be >= 0")
        return [t for t in self.tiers if t.min_lock_years <= lock_years_held][-1]


class TaxConfig(_Model):
    last_verified: str | None = None
    regular_account: TaxRates
    tbsz: TbszRules


def parse_tax_config(text: str) -> TaxConfig:
    """Parse and validate a YAML document."""
    return TaxConfig.model_validate(yaml.safe_load(text))


def load_tax_config(path: Path | None = None) -> TaxConfig:
    """Load the tax config from ``path``, $FINCALC_TAX_CONFIG or the bundled file."""
    if path is None:
        env = os.environ.get(TAX_CONFIG_ENV)
        path = Path(env) if env else DEFAULT_TAX_CONFIG_PATH
    return parse_tax_config(path.read_text(encoding="utf-8"))
