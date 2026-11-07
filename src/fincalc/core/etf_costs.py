"""Impact of ETF total expense ratio (TER) on the final balance."""

from decimal import Decimal

from fincalc.core.compound import compound
from fincalc.core.models import CompoundInput, EtfCostInput, EtfCostResult, EtfCostScenario

_ONE = Decimal(1)
_HUNDRED = Decimal(100)


def net_annual_return_pct(gross_pct: Decimal, ter_pct: Decimal) -> Decimal:
    """Net return after fund costs: (1 + R)(1 - TER) - 1, in percent."""
    net = (_ONE + gross_pct / _HUNDRED) * (_ONE - ter_pct / _HUNDRED) - _ONE
    return net * _HUNDRED


def etf_costs(inp: EtfCostInput) -> EtfCostResult:
    runs = []
    for ter in inp.ter_pcts:
        net_pct = net_annual_return_pct(inp.gross_annual_return_pct, ter)
        res = compound(
            CompoundInput(
                initial_amount=inp.initial_amount,
                monthly_contribution=inp.monthly_contribution,
                annual_return_pct=net_pct,
                years=inp.years,
            )
        )
        runs.append((ter, net_pct, res))

    cheapest_ter, _, cheapest = min(runs, key=lambda run: run[0])
    scenarios = [
        EtfCostScenario(
            ter_pct=ter,
            net_annual_return_pct=net_pct,
            final_balance=res.final_balance,
            total_return=res.total_return,
            cost_vs_cheapest=cheapest.final_balance - res.final_balance,
            series=res.series,
        )
        for ter, net_pct, res in runs
    ]
    return EtfCostResult(
        total_contributed=cheapest.total_contributed,
        cheapest_ter_pct=cheapest_ter,
        scenarios=scenarios,
    )
