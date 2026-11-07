"""Pydantic input/output models for the core calculators.

All money values are ``Decimal`` and are never rounded here; rounding is a
presentation concern. Percentages are expressed in percent (``7`` means 7%).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

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
