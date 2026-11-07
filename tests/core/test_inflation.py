from decimal import Decimal

import pytest
from pydantic import ValidationError

from fincalc.core.compound import compound
from fincalc.core.inflation import (
    compound_with_inflation,
    deflator,
    inflation,
    real_series,
    real_value,
)
from fincalc.core.models import CompoundInflationInput, CompoundInput, InflationInput

D = Decimal
CENT = D("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT)


def test_1m_4pct_10y() -> None:
    # 1 000 000 / 1.04^10 = 675 564.17
    res = inflation(InflationInput(amount=D(1_000_000), annual_inflation_pct=D(4), years=10))
    assert res.nominal == D(1_000_000)
    assert _q(res.real) == D("675564.17")
    assert _q(res.purchasing_power_loss) == D("324435.83")


def test_hand_checked_one_year() -> None:
    res = inflation(InflationInput(amount=D(110), annual_inflation_pct=D(10), years=1))
    assert res.real == D(100)


def test_zero_inflation() -> None:
    res = inflation(InflationInput(amount=D(12345), annual_inflation_pct=D(0), years=30))
    assert res.real == D(12345)
    assert res.purchasing_power_loss == 0


def test_deflation_increases_real_value() -> None:
    res = inflation(InflationInput(amount=D(100), annual_inflation_pct=D(-2), years=5))
    assert res.real > D(100)


def test_partial_year_uses_fractional_power() -> None:
    # Half a year at 21%: sqrt(1.21) = 1.1
    assert deflator(D(21), 6) == D("1.1")
    assert real_value(D(110), D(21), 6) == D(100)


def test_month_zero_is_unchanged() -> None:
    assert real_value(D(500), D(5), 0) == D(500)


def test_real_series_on_compound_output() -> None:
    res = compound(
        CompoundInput(
            initial_amount=D(0), monthly_contribution=D(50_000), annual_return_pct=D(7), years=20
        )
    )
    series = real_series(res.series, D(4))
    assert len(series) == len(res.series)
    assert series[0].real == series[0].nominal
    last = series[-1]
    assert last.month == 240
    assert last.nominal == res.series[-1].balance
    # 26 046 332.99 / 1.04^20
    assert _q(last.real) == D("11887206.37")
    assert all(p.real <= p.nominal for p in series)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": D(-1)},
        {"annual_inflation_pct": D(-100)},
        {"years": 0},
        {"years": 61},
    ],
)
def test_validation_errors(overrides: dict[str, object]) -> None:
    base: dict[str, object] = {"amount": D(1000), "annual_inflation_pct": D(4), "years": 10}
    with pytest.raises(ValidationError):
        InflationInput.model_validate(base | overrides)


def test_compound_with_inflation_adds_real_values() -> None:
    res = compound_with_inflation(
        CompoundInflationInput(
            initial_amount=D(0),
            monthly_contribution=D(50_000),
            annual_return_pct=D(7),
            years=20,
            annual_inflation_pct=D(4),
        )
    )
    assert _q(res.final_balance) == D("26046332.99")
    assert res.final_real_balance is not None
    assert _q(res.final_real_balance) == D("11887206.37")
    assert res.real_series is not None
    assert len(res.real_series) == len(res.series) == 241


def test_compound_with_inflation_without_rate() -> None:
    res = compound_with_inflation(
        CompoundInflationInput(initial_amount=D(1000), annual_return_pct=D(5), years=1)
    )
    assert res.final_real_balance is None
    assert res.real_series is None
    assert (
        res.final_balance
        == compound(
            CompoundInput(initial_amount=D(1000), annual_return_pct=D(5), years=1)
        ).final_balance
    )
