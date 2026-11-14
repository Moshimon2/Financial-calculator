"""TBSZ (long-term investment account) vs. regular brokerage account.

Both accounts hold the same investment; the only difference is the tax on the
gain at withdrawal. Rates come from the tax config (see config/tax_hu.yaml).
"""

from decimal import Decimal

from fincalc.core.compound import MONTHS_PER_YEAR, monthly_rate
from fincalc.core.models import AccountOutcome, CompoundPoint, TbszInput, TbszResult
from fincalc.core.tax import TaxConfig, TaxRates

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HUNDRED = Decimal(100)


def _outcome(gross: Decimal, gain: Decimal, rates: TaxRates) -> AccountOutcome:
    taxable = max(gain, _ZERO)  # no tax on a loss; loss compensation is not modelled
    pit = taxable * rates.pit_pct / _HUNDRED
    social = taxable * rates.social_pct / _HUNDRED
    return AccountOutcome(
        pit_pct=rates.pit_pct,
        social_pct=rates.social_pct,
        pit_tax=pit,
        social_tax=social,
        total_tax=pit + social,
        net_final=gross - pit - social,
    )


def tbsz(inp: TbszInput, config: TaxConfig) -> TbszResult:
    rate = monthly_rate(inp.annual_return_pct)
    months = (1 + inp.lock_years_held) * MONTHS_PER_YEAR

    balance = inp.initial_amount
    contributed = inp.initial_amount
    series = [CompoundPoint(month=0, balance=balance, contributed=contributed)]
    for month in range(1, months + 1):
        payment = inp.monthly_contribution if month <= MONTHS_PER_YEAR else _ZERO
        balance = balance * (_ONE + rate) + payment
        contributed += payment
        series.append(CompoundPoint(month=month, balance=balance, contributed=contributed))

    gain = balance - contributed
    tbsz_out = _outcome(balance, gain, config.tbsz.rates_for(inp.lock_years_held))
    regular_out = _outcome(balance, gain, config.regular_account)
    return TbszResult(
        gross_final=balance,
        total_contributed=contributed,
        gain=gain,
        tbsz=tbsz_out,
        regular=regular_out,
        savings=tbsz_out.net_final - regular_out.net_final,
        series=series,
    )
