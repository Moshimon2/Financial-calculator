from pathlib import Path

from fastapi.testclient import TestClient

from fincalc.services import imports as svc

FIXTURE = Path(__file__).parents[1] / "importers" / "fixtures" / "lightyear_account_statement.csv"


def upload(client: TestClient, data: bytes, broker: str = "lightyear") -> object:
    return client.post(
        f"/api/v1/imports/{broker}/preview", files={"file": ("statement.csv", data, "text/csv")}
    )


def test_preview_confirm_and_log(client: TestClient) -> None:
    r = upload(client, FIXTURE.read_bytes())
    assert r.status_code == 200  # type: ignore[attr-defined]
    body = r.json()  # type: ignore[attr-defined]
    assert (body["rows_total"], body["rows_new"], body["rows_skipped"]) == (7, 5, 2)
    assert body["rows"][0]["transaction"]["ticker"] == "MTELEKOM"
    assert body["rows"][0]["status"] == "new"
    assert client.get("/api/v1/transactions").json()["total"] == 0  # nothing saved yet

    c = client.post(f"/api/v1/imports/{body['preview_id']}/confirm")
    assert c.status_code == 200
    assert c.json()["rows_new"] == 5
    assert client.get("/api/v1/transactions").json()["total"] == 5
    assert client.get("/api/v1/transactions/latest").json()["ticker"] == "MTELEKOM"

    log = client.get("/api/v1/imports").json()
    assert [(i["filename"], i["rows_new"]) for i in log] == [("statement.csv", 5)]

    again = upload(client, FIXTURE.read_bytes()).json()  # type: ignore[attr-defined]
    assert (again["rows_new"], again["rows_duplicate"]) == (0, 5)


def test_preview_errors(client: TestClient) -> None:
    assert upload(client, b'"a"\n"1"\n').status_code == 422  # type: ignore[attr-defined]
    assert upload(client, b"x", broker="xtb").status_code == 404  # type: ignore[attr-defined]
    big = b"x" * (svc.MAX_UPLOAD_BYTES + 1)
    assert upload(client, big).status_code == 413  # type: ignore[attr-defined]
    assert client.post("/api/v1/imports/lightyear/preview").status_code == 422


def test_confirm_unknown_preview(client: TestClient) -> None:
    assert client.post("/api/v1/imports/nope/confirm").status_code == 404
