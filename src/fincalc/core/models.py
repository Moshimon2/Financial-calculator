"""Pydantic input/output models for the core calculators.

All money values are ``Decimal`` and are never rounded here; rounding is a
presentation concern. Percentages are expressed in percent (``7`` means 7%).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MIN_YEARS = 1
MAX_YEARS = 60


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- Compound interest -------------------------------------------------------


class CompoundInput(_Model):
    """Input of the compound interest calculator (contributions at month end)."""

    initial_amount: Decimal = Field(ge=0, description="Starting balance (P)")
    monthly_contribution: Decimal = Field(
        default=Decimal(0), ge=0, description="Monthly contribution (PMT)"
    )
    annual_return_pct: Decimal = Field(gt=-100, description="Nominal annual return in %")
    years: int = Field(ge=MIN_YEARS, le=MAX_YEARS, description="Duration in years")
    annual_contribution_increase_pct: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Yearly increase of the monthly contribution in %, applied from month 13",
    )


class CompoundPoint(_Model):
    """Balance at the end of a given month (month 0 is the starting state)."""

    month: int
    balance: Decimal
    contributed: Decimal = Field(description="Cumulative contributions incl. initial amount")


class CompoundResult(_Model):
    final_balance: Decimal
    total_contributed: Decimal
    total_return: Decimal
    series: list[CompoundPoint]


# --- Inflation ---------------------------------------------------------------


class InflationInput(_Model):
    """Deflate a nominal future amount to today's money."""

    amount: Decimal = Field(ge=0, description="Nominal amount at the end of the period")
    annual_inflation_pct: Decimal = Field(gt=-100, description="Annual inflation in %")
    years: int = Field(ge=MIN_YEARS, le=MAX_YEARS)


class InflationResult(_Model):
    nominal: Decimal
    real: Decimal
    purchasing_power_loss: Decimal = Field(description="nominal - real")


class RealPoint(_Model):
    """A time-series point with both nominal and inflation-adjusted value."""

    month: int
    nominal: Decimal
    real: Decimal


class CompoundInflationInput(CompoundInput):
    """Compound interest input with an optional inflation rate for real values."""

    annual_inflation_pct: Decimal | None = Field(
        default=None, gt=-100, description="If set, real (today's money) values are added"
    )


class CompoundInflationResult(CompoundResult):
    final_real_balance: Decimal | None = None
    real_series: list[RealPoint] | None = None


# --- ETF costs (TER) -----------------------------------------------------------


class EtfCostInput(_Model):
    initial_amount: Decimal = Field(ge=0)
    monthly_contribution: Decimal = Field(default=Decimal(0), ge=0)
    gross_annual_return_pct: Decimal = Field(gt=-100, description="Return before fund costs")
    years: int = Field(ge=MIN_YEARS, le=MAX_YEARS)
    ter_pcts: list[Decimal] = Field(
        min_length=1, max_length=10, description="Total expense ratios in %, e.g. [0.07, 0.22]"
    )

    @field_validator("ter_pcts")
    @classmethod
    def _check_ters(cls, v: list[Decimal]) -> list[Decimal]:
        if any(t < 0 or t >= 100 for t in v):
            raise ValueError("each TER must be >= 0 and < 100")
        return v


class EtfCostScenario(_Model):
    ter_pct: Decimal
    net_annual_return_pct: Decimal
    final_balance: Decimal
    total_return: Decimal
    cost_vs_cheapest: Decimal = Field(
        description="How much less this fund ends with than the cheapest TER"
    )
    series: list[CompoundPoint]


class EtfCostResult(_Model):
    total_contributed: Decimal
    cheapest_ter_pct: Decimal
    scenarios: list[EtfCostScenario] = Field(description="Same order as the input TERs")


# --- TBSZ vs. regular account ------------------------------------------------


class TbszInput(_Model):
    """TBSZ vs. regular account.

    Contributions happen only in the collection year (year 0): an optional lump
    sum at its start plus monthly contributions at the end of each of its 12 months.
    The money then grows for ``lock_years_held`` more years before withdrawal.
    """

    # TODO(open-question): the spec says "befizetés(ek) a gyűjtőévben" - unclear
    # whether that means a lump sum or monthly payments. Both are supported here;
    # the UI default (monthly) is to be confirmed with Simon.
    initial_amount: Decimal = Field(
        default=Decimal(0), ge=0, description="Lump sum at the start of the collection year"
    )
    monthly_contribution: Decimal = Field(
        default=Decimal(0), ge=0, description="Monthly contribution during the collection year"
    )
    annual_return_pct: Decimal = Field(gt=-100)
    lock_years_held: int = Field(
        ge=0, le=MAX_YEARS - 1, description="Full lock years after the collection year"
    )


class AccountOutcome(_Model):
    pit_pct: Decimal
    social_pct: Decimal
    pit_tax: Decimal
    social_tax: Decimal
    total_tax: Decimal
    net_final: Decimal


class TbszResult(_Model):
    gross_final: Decimal
    total_contributed: Decimal
    gain: Decimal
    tbsz: AccountOutcome
    regular: AccountOutcome
    savings: Decimal = Field(description="tbsz.net_final - regular.net_final")
    series: list[CompoundPoint] = Field(description="Gross balance by month (same for both)")
