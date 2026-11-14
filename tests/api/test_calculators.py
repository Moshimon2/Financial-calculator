from decimal import Decimal

from fastapi.testclient import TestClient

from fincalc.api.dependencies import get_tax_config
from fincalc.core.tax import parse_tax_config

D = Decimal


def _q(value: str) -> Decimal:
    return D(value).quantize(D("0.01"))


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_and_swagger(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("compound", "inflation", "etf-costs", "tbsz"):
        assert f"/api/v1/calc/{p}" in paths


def test_compound_ok(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/compound",
        json={
            "initial_amount": 0,
            "monthly_contribution": 50000,
            "annual_return_pct": 7,
            "years": 20,
            "annual_inflation_pct": 4,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert _q(body["final_balance"]) == D("26046332.99")
    assert _q(body["final_real_balance"]) == D("11887206.37")
    assert len(body["series"]) == 241
    assert len(body["real_series"]) == 241


def test_compound_accepts_decimal_strings(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/compound",
        json={"initial_amount": "1000000", "annual_return_pct": "7", "years": 10},
    )
    assert r.status_code == 200
    assert _q(r.json()["final_balance"]) == D("2009661.38")
    assert r.json()["real_series"] is None


def test_compound_validation_error(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/compound",
        json={"initial_amount": -1, "annual_return_pct": 7, "years": 61},
    )
    assert r.status_code == 422
    fields = {e["loc"][-1] for e in r.json()["detail"]}
    assert fields == {"initial_amount", "years"}


def test_compound_rejects_unknown_field(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/compound",
        json={"initial_amount": 1, "annual_return_pct": 7, "years": 1, "foo": 1},
    )
    assert r.status_code == 422


def test_inflation_ok(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/inflation",
        json={"amount": 1000000, "annual_inflation_pct": 4, "years": 10},
    )
    assert r.status_code == 200
    assert _q(r.json()["real"]) == D("675564.17")


def test_inflation_validation_error(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/inflation", json={"amount": 100, "annual_inflation_pct": -100, "years": 1}
    )
    assert r.status_code == 422


def test_etf_costs_ok(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/etf-costs",
        json={
            "initial_amount": 1000000,
            "monthly_contribution": 50000,
            "gross_annual_return_pct": 7,
            "years": 20,
            "ter_pcts": [0.07, 0.22, 0.5],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert D(body["cheapest_ter_pct"]) == D("0.07")
    assert _q(body["scenarios"][2]["cost_vs_cheapest"]) == D("1740348.75")


def test_etf_costs_validation_error(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/etf-costs",
        json={"initial_amount": 1, "gross_annual_return_pct": 7, "years": 1, "ter_pcts": []},
    )
    assert r.status_code == 422


def test_tbsz_ok(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/tbsz",
        json={"initial_amount": 1000000, "annual_return_pct": 7, "lock_years_held": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert _q(body["savings"]) == D("145629.54")
    assert D(body["tbsz"]["total_tax"]) == 0


def test_tbsz_uses_injected_tax_config(client: TestClient) -> None:
    cfg = parse_tax_config(
        """
regular_account: {pit_pct: 50, social_pct: 0}
tbsz:
  lock_years: 5
  tiers: [{min_lock_years: 0, pit_pct: 0, social_pct: 0}]
"""
    )
    app = client.app
    app.dependency_overrides[get_tax_config] = lambda: cfg  # type: ignore[attr-defined]
    r = client.post(
        "/api/v1/calc/tbsz",
        json={"initial_amount": 100, "annual_return_pct": 0, "lock_years_held": 0},
    )
    assert r.status_code == 200
    assert D(r.json()["regular"]["pit_pct"]) == 50


def test_tbsz_validation_error(client: TestClient) -> None:
    r = client.post(
        "/api/v1/calc/tbsz",
        json={"initial_amount": 100, "annual_return_pct": 7, "lock_years_held": -1},
    )
    assert r.status_code == 422
