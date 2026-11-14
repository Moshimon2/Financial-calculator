"""Inflation adjustment: convert nominal future amounts to today's money."""

from collections.abc import Sequence
from decimal import Decimal

from fincalc.core.compound import compound
from fincalc.core.models import (
    CompoundInflationInput,
    CompoundInflationResult,
    CompoundInput,
    CompoundPoint,
    InflationInput,
    InflationResult,
    RealPoint,
)

_ONE = Decimal(1)
_HUNDRED = Decimal(100)
_MONTHS_PER_YEAR = Decimal(12)


def deflator(annual_inflation_pct: Decimal, months: int) -> Decimal:
    """Cumulative price level after ``months``: (1 + i)^(months / 12).

    Whole years use an integer power (exact); partial years use a fractional
    power, i.e. inflation is assumed to accrue evenly over the year.
    """
    base = _ONE + annual_inflation_pct / _HUNDRED
    if months % 12 == 0:
        return base ** (months // 12)
    return base ** (Decimal(months) / _MONTHS_PER_YEAR)


def real_value(amount: Decimal, annual_inflation_pct: Decimal, months: int) -> Decimal:
    """FV_real = FV / (1 + i)^t with t = months / 12."""
    return amount / deflator(annual_inflation_pct, months)


def inflation(inp: InflationInput) -> InflationResult:
    real = real_value(inp.amount, inp.annual_inflation_pct, inp.years * 12)
    return InflationResult(nominal=inp.amount, real=real, purchasing_power_loss=inp.amount - real)


def real_series(series: Sequence[CompoundPoint], annual_inflation_pct: Decimal) -> list[RealPoint]:
    """Attach today's-money values to a compound interest series (for charts)."""
    return [
        RealPoint(
            month=p.month,
            nominal=p.balance,
            real=real_value(p.balance, annual_inflation_pct, p.month),
        )
        for p in series
    ]


def compound_with_inflation(inp: CompoundInflationInput) -> CompoundInflationResult:
    """Compound interest result, plus real values when an inflation rate is given."""
    base = compound(CompoundInput.model_validate(inp.model_dump(exclude={"annual_inflation_pct"})))
    if inp.annual_inflation_pct is None:
        return CompoundInflationResult(**base.model_dump())
    series = real_series(base.series, inp.annual_inflation_pct)
    return CompoundInflationResult(
        **base.model_dump(),
        final_real_balance=series[-1].real,
        real_series=series,
    )
