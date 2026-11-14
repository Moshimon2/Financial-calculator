"""Chart.js data and table rows built from core results (display values only)."""

from decimal import Decimal
from typing import Any

from fincalc.core.models import CompoundInflationResult, CompoundPoint, EtfCostResult
from fincalc.web.formatting import format_pct

MONTHS_PER_YEAR = 12


def _yearly[T](series: list[T]) -> list[T]:
    return series[::MONTHS_PER_YEAR]


def _round(value: Decimal) -> int:
    return int(value.to_integral_value())


def _year_labels(t: dict[str, Any], points: list[CompoundPoint]) -> list[str]:
    return [
        t["common"]["start"] if p.month == 0 else t["common"]["year_n"].format(n=p.month // 12)
        for p in points
    ]


def compound_chart(res: CompoundInflationResult, t: dict[str, Any]) -> dict[str, Any]:
    texts = t["compound"]
    points = _yearly(res.series)
    datasets: list[dict[str, Any]] = [
        {
            "label": texts["series_nominal"],
            "slot": 1,
            "data": [_round(p.balance) for p in points],
        }
    ]
    if res.real_series is not None:
        datasets.append(
            {
                "label": texts["series_real"],
                "slot": 2,
                "data": [_round(p.real) for p in _yearly(res.real_series)],
            }
        )
    datasets.append(
        {
            "label": texts["series_contributed"],
            "slot": 3,
            "dashed": True,
            "data": [_round(p.contributed) for p in points],
        }
    )
    return {"labels": _year_labels(t, points), "datasets": datasets}


def etf_chart(res: EtfCostResult, t: dict[str, Any]) -> dict[str, Any]:
    points = _yearly(res.scenarios[0].series)
    datasets = [
        {
            # Color follows the input position (the fund), never its rank.
            "label": t["etf_costs"]["fund"].format(ter=format_pct(s.ter_pct)),
            "slot": i + 1,
            "data": [_round(p.balance) for p in _yearly(s.series)],
        }
        for i, s in enumerate(res.scenarios)
    ]
    return {"labels": _year_labels(t, points), "datasets": datasets}


def chart_table(chart: dict[str, Any]) -> list[list[Any]]:
    """Rows [label, value per dataset...] mirroring the chart (accessible table view)."""
    return [
        [label, *(d["data"][i] for d in chart["datasets"])]
        for i, label in enumerate(chart["labels"])
    ]
