from decimal import Decimal

import pytest
from pydantic import ValidationError

from fincalc.core.compound import compound
from fincalc.core.etf_costs import etf_costs, net_annual_return_pct
from fincalc.core.models import CompoundInput, EtfCostInput

D = Decimal
CENT = D("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT)


def test_net_return_hand_checked() -> None:
    # (1.10)(0.90) - 1 = -1%
    assert net_annual_return_pct(D(10), D(10)) == D(-1)
    # (1.07)(1 - 0.005) - 1 = 6.465%
    assert net_annual_return_pct(D(7), D("0.5")) == D("6.465")
    assert net_annual_return_pct(D(7), D(0)) == D(7)


def test_reference_three_ters() -> None:
    # 1M initial + 50k/month, 7% gross, 20 years (independent float computation)
    res = etf_costs(
        EtfCostInput(
            initial_amount=D(1_000_000),
            monthly_contribution=D(50_000),
            gross_annual_return_pct=D(7),
            years=20,
            ter_pcts=[D("0.22"), D("0.07"), D("0.5")],
        )
    )
    assert res.cheapest_ter_pct == D("0.07")
    assert res.total_contributed == D(13_000_000)
    by_ter = {s.ter_pct: s for s in res.scenarios}
    assert _q(by_ter[D("0.07")].final_balance) == D("29789779.09")
    assert _q(by_ter[D("0.22")].final_balance) == D("29168492.25")
    assert _q(by_ter[D("0.5")].final_balance) == D("28049430.34")
    assert by_ter[D("0.07")].cost_vs_cheapest == 0
    assert _q(by_ter[D("0.5")].cost_vs_cheapest) == D("1740348.75")
    # Order of the input is kept.
    assert [s.ter_pct for s in res.scenarios] == [D("0.22"), D("0.07"), D("0.5")]


def test_zero_ter_equals_plain_compound() -> None:
    res = etf_costs(
        EtfCostInput(initial_amount=D(1000), gross_annual_return_pct=D(5), years=3, ter_pcts=[D(0)])
    )
    plain = compound(CompoundInput(initial_amount=D(1000), annual_return_pct=D(5), years=3))
    assert res.scenarios[0].final_balance == plain.final_balance
    assert len(res.scenarios[0].series) == 37


def test_higher_ter_never_ends_higher_even_with_negative_return() -> None:
    res = etf_costs(
        EtfCostInput(
            initial_amount=D(10_000),
            gross_annual_return_pct=D(-5),
            years=5,
            ter_pcts=[D(1), D("0.1")],
        )
    )
    assert res.cheapest_ter_pct == D("0.1")
    assert res.scenarios[0].cost_vs_cheapest > 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"ter_pcts": []},
        {"ter_pcts": [D(-0.1)]},
        {"ter_pcts": [D(100)]},
        {"ter_pcts": [D(0.1)] * 11},
        {"gross_annual_return_pct": D(-100)},
        {"years": 0},
        {"initial_amount": D(-1)},
    ],
)
def test_validation_errors(overrides: dict[str, object]) -> None:
    base: dict[str, object] = {
        "initial_amount": D(1000),
        "gross_annual_return_pct": D(7),
        "years": 10,
        "ter_pcts": [D("0.2")],
    }
    with pytest.raises(ValidationError):
        EtfCostInput.model_validate(base | overrides)
