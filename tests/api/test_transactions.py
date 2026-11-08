from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from fincalc.core.transactions import TransactionType
from tests.helpers import make_tx, seed


def test_latest_404_when_empty(client: TestClient) -> None:
    assert client.get("/api/v1/transactions/latest").status_code == 404


def test_latest_and_list(client: TestClient, session: Session) -> None:
    seed(
        session,
        [
            make_tx(1),
            make_tx(5, ticker="CSPX"),
            make_tx(6, type=TransactionType.SELL, amount=Decimal("10")),
        ],
    )
    latest = client.get("/api/v1/transactions/latest").json()
    assert latest["ticker"] == "CSPX"
    assert latest["external_id"] == "LY-5"
    assert Decimal(latest["quantity"]) == Decimal("0.123456789")
    assert latest["executed_at"].startswith("2026-01-05T09:00:00")

    body = client.get("/api/v1/transactions").json()
    assert body["total"] == 3
    assert [t["external_id"] for t in body["items"]] == ["LY-6", "LY-5", "LY-1"]

    params = {"type": "buy", "ticker": "vwce"}
    assert client.get("/api/v1/transactions", params=params).json()["total"] == 1
    params = {"date_from": "2026-01-02T00:00:00Z", "date_to": "2026-01-06T00:00:00Z"}
    assert client.get("/api/v1/transactions", params=params).json()["total"] == 1
    page = client.get("/api/v1/transactions", params={"limit": 1, "offset": 1}).json()
    assert [t["external_id"] for t in page["items"]] == ["LY-5"]


def test_list_validation_errors(client: TestClient) -> None:
    assert client.get("/api/v1/transactions", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/transactions", params={"type": "swap"}).status_code == 422
    naive = {"date_from": "2026-01-01T00:00:00"}
    assert client.get("/api/v1/transactions", params=naive).status_code == 422
