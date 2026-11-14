from decimal import Decimal

import pytest
from pydantic import ValidationError

from fincalc.core.models import TbszInput
from fincalc.core.tax import TaxConfig, load_tax_config
from fincalc.core.tbsz import tbsz

D = Decimal
CENT = D("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT)


@pytest.fixture
def cfg() -> TaxConfig:
    return load_tax_config()


def test_lump_sum_held_full_lock_period(cfg: TaxConfig) -> None:
    # 1M at the start of the collection year, 7%, + 5 lock years = 72 months
    res = tbsz(
        TbszInput(initial_amount=D(1_000_000), annual_return_pct=D(7), lock_years_held=5), cfg
    )
    assert _q(res.gross_final) == D("1520105.50")
    assert _q(res.gain) == D("520105.50")
    assert res.tbsz.total_tax == 0
    assert res.tbsz.net_final == res.gross_final
    assert _q(res.regular.total_tax) == D("145629.54")  # 28% of the gain
    assert _q(res.savings) == D("145629.54")
    assert len(res.series) == 73


def test_monthly_contributions_broken_after_3_years(cfg: TaxConfig) -> None:
    # 100k/month in the collection year, then 3 lock years at 7%
    res = tbsz(
        TbszInput(monthly_contribution=D(100_000), annual_return_pct=D(7), lock_years_held=3), cfg
    )
    assert res.total_contributed == D(1_200_000)
    assert _q(res.gross_final) == D("1527913.55")
    assert _q(res.tbsz.total_tax) == D("32791.35")  # 10% SZJA, 0% szocho (open question)
    assert _q(res.regular.total_tax) == D("91815.79")
    assert res.tbsz.pit_pct == D(10)
    # Contributions stop after month 12.
    assert res.series[12].contributed == D(1_200_000)
    assert res.series[-1].contributed == D(1_200_000)


def test_hand_checked_zero_return_no_tax(cfg: TaxConfig) -> None:
    res = tbsz(
        TbszInput(
            initial_amount=D(100),
            monthly_contribution=D(10),
            annual_return_pct=D(0),
            lock_years_held=1,
        ),
        cfg,
    )
    assert res.gross_final == D(220)
    assert res.gain == 0
    assert res.savings == 0


def test_broken_early_same_tax_as_regular(cfg: TaxConfig) -> None:
    res = tbsz(TbszInput(initial_amount=D(1000), annual_return_pct=D(10), lock_years_held=2), cfg)
    assert res.tbsz == res.regular
    assert res.savings == 0


def test_loss_is_not_taxed(cfg: TaxConfig) -> None:
    res = tbsz(TbszInput(initial_amount=D(1000), annual_return_pct=D(-20), lock_years_held=0), cfg)
    assert res.gain < 0
    assert res.regular.total_tax == 0
    assert res.regular.net_final == res.gross_final


def test_tax_split_pit_and_social(cfg: TaxConfig) -> None:
    res = tbsz(TbszInput(initial_amount=D(1000), annual_return_pct=D(12), lock_years_held=0), cfg)
    assert res.regular.pit_tax == res.gain * D("0.15")
    assert res.regular.social_tax == res.gain * D("0.13")


@pytest.mark.parametrize(
    "overrides",
    [
        {"initial_amount": D(-1)},
        {"monthly_contribution": D(-1)},
        {"annual_return_pct": D(-100)},
        {"lock_years_held": -1},
        {"lock_years_held": 60},
    ],
)
def test_validation_errors(overrides: dict[str, object]) -> None:
    base: dict[str, object] = {
        "initial_amount": D(1000),
        "annual_return_pct": D(7),
        "lock_years_held": 5,
    }
    with pytest.raises(ValidationError):
        TbszInput.model_validate(base | overrides)
