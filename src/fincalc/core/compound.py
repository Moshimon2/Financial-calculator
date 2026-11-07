"""Compound interest with monthly contributions.

See docs/formulas.md for the formulas and assumptions.
"""

from decimal import Decimal

from fincalc.core.models import CompoundInput, CompoundPoint, CompoundResult

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HUNDRED = Decimal(100)
MONTHS_PER_YEAR = 12


def monthly_rate(annual_pct: Decimal) -> Decimal:
    """Nominal annual percent -> monthly rate as a fraction (r = R / 12)."""
    return annual_pct / _HUNDRED / MONTHS_PER_YEAR


def future_value(principal: Decimal, payment: Decimal, rate: Decimal, months: int) -> Decimal:
    """Closed-form future value with end-of-month payments.

    FV = P(1+r)^n + PMT * ((1+r)^n - 1) / r, and FV = P + PMT * n when r = 0.
    """
    if rate == _ZERO:
        return principal + payment * months
    growth = (_ONE + rate) ** months
    return principal * growth + payment * (growth - _ONE) / rate


def compound(inp: CompoundInput) -> CompoundResult:
    """Run the compound interest calculation and return a monthly series.

    The series is always produced by month-by-month iteration. When there is no
    yearly contribution increase, the final balance comes from the closed-form
    formula (the two agree up to Decimal precision).
    """
    rate = monthly_rate(inp.annual_return_pct)
    increase = inp.annual_contribution_increase_pct / _HUNDRED
    months = inp.years * MONTHS_PER_YEAR

    balance = inp.initial_amount
    contributed = inp.initial_amount
    series = [CompoundPoint(month=0, balance=balance, contributed=contributed)]

    for month in range(1, months + 1):
        year_index = (month - 1) // MONTHS_PER_YEAR
        payment = inp.monthly_contribution * (_ONE + increase) ** year_index
        balance = balance * (_ONE + rate) + payment
        contributed += payment
        series.append(CompoundPoint(month=month, balance=balance, contributed=contributed))

    if increase == _ZERO:
        balance = future_value(inp.initial_amount, inp.monthly_contribution, rate, months)

    return CompoundResult(
        final_balance=balance,
        total_contributed=contributed,
        total_return=balance - contributed,
        series=series,
    )
