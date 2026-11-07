"""Server-rendered HTML pages (Jinja2 + HTMX).

Every calculator page has a GET route (full page, computed with the default
values) and a POST ``.../result`` route returning only the result partial,
which HTMX swaps in while the user types.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from fincalc.api.dependencies import get_tax_config
from fincalc.core.etf_costs import etf_costs
from fincalc.core.inflation import compound_with_inflation, inflation
from fincalc.core.models import CompoundInflationInput, EtfCostInput, InflationInput, TbszInput
from fincalc.core.tax import TaxConfig
from fincalc.core.tbsz import tbsz
from fincalc.web import charts
from fincalc.web.formatting import format_huf, format_input, format_number, format_pct
from fincalc.web.forms import FormField, defaults, parse_form, validation_messages
from fincalc.web.i18n.hu import TEXTS

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"

templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.filters.update(huf=format_huf, num=format_number, pct=format_pct)
templates.env.globals["t"] = TEXTS

router = APIRouter(include_in_schema=False)

Values = dict[str, Any]
Builder = Callable[[Values, TaxConfig], dict[str, Any]]


# --- calculator definitions --------------------------------------------------


def _compound(values: Values, _: TaxConfig) -> dict[str, Any]:
    res = compound_with_inflation(CompoundInflationInput.model_validate(values))
    chart = charts.compound_chart(res, TEXTS)
    return {"result": res, "chart": chart, "table": charts.chart_table(chart)}


def _inflation(values: Values, _: TaxConfig) -> dict[str, Any]:
    return {"result": inflation(InflationInput.model_validate(values))}


def _etf_costs(values: Values, _: TaxConfig) -> dict[str, Any]:
    ter_keys = ("ter_1", "ter_2", "ter_3")
    ters = [values[k] for k in ter_keys if values.get(k) is not None]
    rest = {k: v for k, v in values.items() if k not in ter_keys}
    res = etf_costs(EtfCostInput.model_validate(rest | {"ter_pcts": ters}))
    chart = charts.etf_chart(res, TEXTS)
    most_expensive = max(res.scenarios, key=lambda s: s.cost_vs_cheapest)
    return {
        "result": res,
        "chart": chart,
        "table": charts.chart_table(chart),
        "max_cost": most_expensive.cost_vs_cheapest,
    }


def _tbsz(values: Values, config: TaxConfig) -> dict[str, Any]:
    return {"result": tbsz(TbszInput.model_validate(values), config)}


@dataclass(frozen=True)
class CalcPage:
    key: str  # template / i18n key
    path: str  # URL segment under /calc/
    fields: tuple[FormField, ...]
    build: Builder


PAGES = (
    CalcPage(
        "compound",
        "compound",
        (
            FormField("initial_amount", "0"),
            FormField("monthly_contribution", format_input(50_000)),
            FormField("annual_return_pct", "7"),
            FormField("years", "20", kind="int"),
            FormField("annual_contribution_increase_pct", "0"),
            FormField("annual_inflation_pct", "4", optional=True),
        ),
        _compound,
    ),
    CalcPage(
        "inflation",
        "inflation",
        (
            FormField("amount", format_input(10_000_000)),
            FormField("annual_inflation_pct", "4"),
            FormField("years", "20", kind="int"),
        ),
        _inflation,
    ),
    CalcPage(
        "etf_costs",
        "etf-costs",
        (
            FormField("initial_amount", "0"),
            FormField("monthly_contribution", format_input(50_000)),
            FormField("gross_annual_return_pct", "7"),
            FormField("years", "20", kind="int"),
            FormField("ter_1", "0,07"),
            FormField("ter_2", "0,22"),
            FormField("ter_3", "0,5", optional=True),
        ),
        _etf_costs,
    ),
    CalcPage(
        "tbsz",
        "tbsz",
        (
            FormField("initial_amount", "0"),
            FormField("monthly_contribution", format_input(50_000)),
            FormField("annual_return_pct", "7"),
            FormField("lock_years_held", "5", kind="int"),
        ),
        _tbsz,
    ),
)


def _evaluate(page: CalcPage, form: dict[str, Any], config: TaxConfig) -> dict[str, Any]:
    """Parse + validate + compute. Returns the template context for the result."""
    texts = TEXTS["errors"]
    raw, values, errors = parse_form(form, page.fields, texts)
    context: dict[str, Any] = {"form": raw, "result": None}
    if not errors:
        try:
            context |= page.build(values, config)
        except ValidationError as exc:
            errors = validation_messages(exc, texts)
    labels = TEXTS[page.key]["fields"]
    context["errors"] = [
        (labels.get(name, {}).get("label", name), message) for name, message in errors.items()
    ]
    context["error_fields"] = set(errors)
    return context


def _register(page: CalcPage) -> None:
    full_template = f"calc/{page.key}.html"
    partial_template = f"calc/_{page.key}_result.html"

    async def show(
        request: Request, config: Annotated[TaxConfig, Depends(get_tax_config)]
    ) -> HTMLResponse:
        context = _evaluate(page, defaults(page.fields), config)
        context |= {"page": page.key, "result_url": f"/calc/{page.path}/result"}
        return templates.TemplateResponse(request, full_template, context)

    async def result(
        request: Request, config: Annotated[TaxConfig, Depends(get_tax_config)]
    ) -> HTMLResponse:
        form = dict(await request.form())
        context = _evaluate(page, form, config)
        return templates.TemplateResponse(request, partial_template, context)

    router.add_api_route(f"/calc/{page.path}", show, methods=["GET"], name=page.key)
    router.add_api_route(
        f"/calc/{page.path}/result", result, methods=["POST"], name=f"{page.key}_result"
    )


for _page in PAGES:
    _register(_page)

templates.env.globals["nav"] = [("dashboard", "/")] + [(p.key, f"/calc/{p.path}") for p in PAGES]


@router.get("/", name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "dashboard.html", {"page": "dashboard"})
