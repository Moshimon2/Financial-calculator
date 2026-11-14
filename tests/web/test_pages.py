import re
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from fincalc.core.transactions import TransactionType
from fincalc.web.formatting import NBSP
from tests.helpers import make_tx, seed


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace(NBSP, " ")


COMPOUND_FORM = {
    "initial_amount": "0",
    "monthly_contribution": "50 000",
    "annual_return_pct": "7",
    "years": "20",
    "annual_contribution_increase_pct": "0",
    "annual_inflation_pct": "4",
}


@pytest.mark.parametrize(
    "path", ["/", "/calc/compound", "/calc/inflation", "/calc/etf-costs", "/calc/tbsz"]
)
def test_pages_render(client: TestClient, path: str) -> None:
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert '<html lang="hu"' in r.text
    assert "/static/css/app.css" in r.text


def test_static_assets(client: TestClient) -> None:
    for path in (
        "/static/css/app.css",
        "/static/js/app.js",
        "/static/vendor/htmx-2.0.11.min.js",
        "/static/vendor/chart-4.6.1.umd.min.js",
    ):
        assert client.get(path).status_code == 200


def test_compound_page_has_default_result(client: TestClient) -> None:
    text = _text(client.get("/calc/compound").text)
    assert "26 046 333 Ft" in text  # 50 000 Ft/month, 7%, 20 years
    assert "11 887 206 Ft" in text  # in today's money at 4% inflation
    assert "Hogyan számolunk?" in text


def test_compound_partial(client: TestClient) -> None:
    r = client.post("/calc/compound/result", data=COMPOUND_FORM | {"years": "10"})
    assert r.status_code == 200
    assert "<html" not in r.text  # partial only
    assert 'id="chart-compound"' in r.text
    assert "8 654 240 Ft" in _text(r.text)  # 50 000 Ft/month, 7%, 10 years


def test_compound_without_inflation(client: TestClient) -> None:
    r = client.post("/calc/compound/result", data=COMPOUND_FORM | {"annual_inflation_pct": ""})
    assert "Mai értéken" not in _text(r.text)


def test_compound_parse_error(client: TestClient) -> None:
    r = client.post("/calc/compound/result", data=COMPOUND_FORM | {"initial_amount": "abc"})
    text = _text(r.text)
    assert "Kezdőösszeg: érvénytelen szám" in text


def test_compound_missing_and_non_integer(client: TestClient) -> None:
    form = COMPOUND_FORM | {"monthly_contribution": "", "years": "2,5"}
    text = _text(client.post("/calc/compound/result", data=form).text)
    assert "Havi befizetés: kötelező mező" in text
    assert "Futamidő: érvénytelen szám" in text


def test_compound_validation_error(client: TestClient) -> None:
    form = COMPOUND_FORM | {"years": "61", "annual_return_pct": "-100"}
    text = _text(client.post("/calc/compound/result", data=form).text)
    assert "Futamidő: legfeljebb 60 legyen" in text
    assert "Éves hozam: nagyobb legyen, mint -100" in text


def test_inflation_partial(client: TestClient) -> None:
    form = {"amount": "1 000 000", "annual_inflation_pct": "4", "years": "10"}
    text = _text(client.post("/calc/inflation/result", data=form).text)
    assert "675 564 Ft" in text


def test_etf_partial(client: TestClient) -> None:
    form = {
        "initial_amount": "1 000 000",
        "monthly_contribution": "50 000",
        "gross_annual_return_pct": "7",
        "years": "20",
        "ter_1": "0,07",
        "ter_2": "0,22",
        "ter_3": "0,5",
    }
    r = client.post("/calc/etf-costs/result", data=form)
    text = _text(r.text)
    assert "1 740 349 Ft" in text  # 0.5% vs 0.07%
    assert "Legolcsóbb" in text
    assert 'id="chart-etf"' in r.text


def test_etf_without_any_ter(client: TestClient) -> None:
    form = {
        "initial_amount": "0",
        "monthly_contribution": "1000",
        "gross_annual_return_pct": "7",
        "years": "5",
        "ter_1": "",
        "ter_2": "",
        "ter_3": "",
    }
    text = _text(client.post("/calc/etf-costs/result", data=form).text)
    assert "1. alap TER: kötelező mező" in text


def test_tbsz_partial(client: TestClient) -> None:
    form = {
        "initial_amount": "1 000 000",
        "monthly_contribution": "0",
        "annual_return_pct": "7",
        "lock_years_held": "5",
    }
    text = _text(client.post("/calc/tbsz/result", data=form).text)
    assert "Ennyit spórolsz a TBSZ-szel 145 630 Ft" in text


def test_tbsz_no_savings_when_broken_early(client: TestClient) -> None:
    form = {
        "initial_amount": "1 000 000",
        "monthly_contribution": "0",
        "annual_return_pct": "7",
        "lock_years_held": "1",
    }
    text = _text(client.post("/calc/tbsz/result", data=form).text)
    assert "nem ad adóelőnyt" in text


def test_web_routes_not_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert all(p.startswith("/api/v1/") for p in paths)


def test_dashboard_empty_state(client: TestClient) -> None:
    text = _text(client.get("/").text)
    assert "Még nincs importált tranzakció" in text
    assert "Még nincs befizetés" in text


def test_dashboard_with_data(client: TestClient, session: Session) -> None:
    dep = {"type": TransactionType.DEPOSIT, "ticker": None, "quantity": None, "price": None}
    seed(
        session,
        [
            make_tx(2, **dep, amount=Decimal("1500")),
            make_tx(3, **dep, amount=Decimal("120000"), currency="HUF"),
            make_tx(4, ticker="CSPX", quantity=Decimal("2.500"), amount=Decimal("-1234.5")),
            make_tx(1),
        ],
    )
    text = _text(client.get("/").text)
    assert "0,123456789 db" not in text  # only the latest purchase is shown
    # 09:00 UTC on 4 Jan is 10:00 in Budapest (CET)
    assert "CSPX 1 234,50 EUR" in text
    assert "2026. 01. 04. 10:00 · 2,5 db" in text
    assert "Azonosító: LY-4" in text
    assert "1 500,00 EUR" in text
    assert "120 000 Ft" in text
    assert "Tranzakciók száma 4" in text
