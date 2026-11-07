from decimal import Decimal

import pytest
from pydantic import ValidationError

from fincalc.core.compound import compound, future_value, monthly_rate
from fincalc.core.models import CompoundInput

D = Decimal
CENT = D("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT)


# Reference values: checked with an independent float computation and the
# closed form FV = P(1+r)^n + PMT((1+r)^n - 1)/r, r = R/12 (also matches Excel FV()).


def test_lump_sum_1m_7pct_10y() -> None:
    res = compound(CompoundInput(initial_amount=D(1_000_000), annual_return_pct=D(7), years=10))
    assert _q(res.final_balance) == D("2009661.38")
    assert res.total_contributed == D(1_000_000)
    assert _q(res.total_return) == D("1009661.38")


def test_monthly_50k_7pct_20y() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(0), monthly_contribution=D(50_000), annual_return_pct=D(7), years=20
        )
    )
    assert _q(res.final_balance) == D("26046332.99")
    assert res.total_contributed == D(12_000_000)
    assert _q(res.total_return) == D("14046332.99")


def test_initial_and_monthly_combined() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(1_000_000),
            monthly_contribution=D(50_000),
            annual_return_pct=D(7),
            years=20,
        )
    )
    assert _q(res.final_balance) == D("30085071.84")


def test_series_shape_and_consistency() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(1000), monthly_contribution=D(100), annual_return_pct=D(5), years=3
        )
    )
    assert len(res.series) == 37
    assert res.series[0].month == 0
    assert res.series[0].balance == D(1000)
    assert res.series[0].contributed == D(1000)
    assert res.series[-1].month == 36
    assert res.series[-1].contributed == res.total_contributed
    # Iterated series agrees with closed form.
    assert abs(res.series[-1].balance - res.final_balance) < D("1e-15")


def test_first_month_contribution_at_month_end() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(1200), monthly_contribution=D(100), annual_return_pct=D(12), years=1
        )
    )
    # 1% monthly: 1200 * 1.01 + 100 (payment does not earn interest in its own month)
    assert res.series[1].balance == D("1312.00")


def test_zero_return() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(500), monthly_contribution=D(100), annual_return_pct=D(0), years=2
        )
    )
    assert res.final_balance == D(2900)
    assert res.total_return == D(0)


def test_zero_contribution_zero_initial() -> None:
    res = compound(CompoundInput(initial_amount=D(0), annual_return_pct=D(7), years=5))
    assert res.final_balance == D(0)
    assert all(p.balance == 0 for p in res.series)


def test_negative_return() -> None:
    # -12% p.a. -> -1% monthly, 12 months: 100000 * 0.99^12
    res = compound(CompoundInput(initial_amount=D(100_000), annual_return_pct=D(-12), years=1))
    assert _q(res.final_balance) == D("88638.49")
    assert res.total_return < 0


def test_contribution_increase_zero_return_hand_checked() -> None:
    # Year 1: 12 * 1000, year 2: 12 * 1100 -> 25200
    res = compound(
        CompoundInput(
            initial_amount=D(0),
            monthly_contribution=D(1000),
            annual_return_pct=D(0),
            years=2,
            annual_contribution_increase_pct=D(10),
        )
    )
    assert res.final_balance == D(25200)
    assert res.series[12].contributed == D(12000)
    assert res.series[13].contributed - res.series[12].contributed == D(1100)


def test_contribution_increase_with_return_uses_iteration() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(0),
            monthly_contribution=D(1000),
            annual_return_pct=D(12),
            years=2,
            annual_contribution_increase_pct=D(10),
        )
    )
    # Year 1 annuity at 1%/month, then grown 12 months, plus year 2 annuity of 1100.
    year1 = future_value(D(0), D(1000), D("0.01"), 12)
    expected = future_value(year1, D(1100), D("0.01"), 12)
    assert abs(res.final_balance - expected) < D("1e-15")
    assert res.final_balance == res.series[-1].balance


def test_monthly_rate() -> None:
    assert monthly_rate(D(12)) == D("0.01")


def test_future_value_zero_rate() -> None:
    assert future_value(D(10), D(5), D(0), 4) == D(30)


def test_decimal_types_preserved() -> None:
    res = compound(CompoundInput(initial_amount=D(1), annual_return_pct=D(1), years=1))
    assert isinstance(res.final_balance, Decimal)
    assert all(isinstance(p.balance, Decimal) for p in res.series)


def test_pure_function_same_output() -> None:
    inp = CompoundInput(
        initial_amount=D(1000), monthly_contribution=D(50), annual_return_pct=D(6), years=4
    )
    assert compound(inp) == compound(inp)


@pytest.mark.parametrize(
    "overrides",
    [
        {"initial_amount": D(-1)},
        {"monthly_contribution": D(-1)},
        {"annual_return_pct": D(-100)},
        {"annual_return_pct": D(-150)},
        {"years": 0},
        {"years": 61},
        {"annual_contribution_increase_pct": D(-1)},
    ],
)
def test_validation_errors(overrides: dict[str, object]) -> None:
    base: dict[str, object] = {
        "initial_amount": D(1000),
        "monthly_contribution": D(100),
        "annual_return_pct": D(7),
        "years": 10,
    }
    with pytest.raises(ValidationError):
        CompoundInput.model_validate(base | overrides)


def test_boundary_years_accepted() -> None:
    assert compound(CompoundInput(initial_amount=D(1), annual_return_pct=D(7), years=1))
    assert compound(CompoundInput(initial_amount=D(1), annual_return_pct=D(7), years=60))
