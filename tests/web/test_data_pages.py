import re
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from fincalc.core.transactions import TransactionType
from fincalc.web.formatting import NBSP
from tests.helpers import make_tx, seed

FIXTURE = Path(__file__).parents[1] / "importers" / "fixtures" / "lightyear_account_statement.csv"


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace(NBSP, " ")


def test_import_flow_in_web_ui(client: TestClient) -> None:
    page = client.get("/import")
    assert page.status_code == 200
    assert "Még nem volt import" in _text(page.text)

    r = client.post("/import/preview", files={"file": ("statement.csv", FIXTURE.read_bytes())})
    text = _text(r.text)
    assert "Előnézet: statement.csv" in text
    assert "Új 5" in text
    assert "Kihagyva 2" in text
    assert "Nem importált típusok: Conversion" in text
    assert "-6 113 Ft" in text
    preview_id = re.search(r'hx-post="/import/([0-9a-f]+)/confirm"', r.text)
    assert preview_id is not None

    done = client.post(f"/import/{preview_id.group(1)}/confirm")
    done_text = _text(done.text)
    assert "Mentve: 5 új tranzakció" in done_text
    assert 'hx-swap-oob="true"' in done.text
    assert "statement.csv" in done_text

    expired = client.post(f"/import/{preview_id.group(1)}/confirm")
    assert "lejárt" in _text(expired.text)

    again = client.post("/import/preview", files={"file": ("statement.csv", FIXTURE.read_bytes())})
    assert "Nincs új tranzakció" in _text(again.text)

    dash = _text(client.get("/").text)
    assert "MTELEKOM 6 113 Ft" in dash
    assert "300,00 EUR" in dash


def test_import_preview_errors(client: TestClient) -> None:
    assert "Válassz ki" in _text(client.post("/import/preview").text)
    bad = client.post("/import/preview", files={"file": ("x.csv", b'"a"\n"1"\n')})
    assert "A fájl nem olvasható" in _text(bad.text)
    big = client.post("/import/preview", files={"file": ("x.csv", b"x" * (5 * 1024 * 1024 + 1))})
    assert "túl nagy" in _text(big.text)


def test_import_preview_shows_row_errors(client: TestClient) -> None:
    lines = FIXTURE.read_text().splitlines()
    lines[1] = lines[1].replace("13/11/2026 08:05:05", "2026-11-13")
    r = client.post("/import/preview", files={"file": ("s.csv", "\n".join(lines).encode())})
    assert "2. sor, Date: érvénytelen dátum (2026-11-13)" in _text(r.text)


def test_transactions_page_filters_and_paging(client: TestClient, session: Session) -> None:
    assert "Nincs a szűrésnek megfelelő" in _text(client.get("/transactions").text)
    seed(
        session,
        [make_tx(d) for d in range(1, 28)]
        + [make_tx(d, external_id=f"B-{d}", ticker="CSPX") for d in range(1, 28)]
        + [
            make_tx(
                28,
                type=TransactionType.DEPOSIT,
                ticker=None,
                quantity=None,
                price=None,
                amount=Decimal("100"),
            )
        ],
    )
    text = _text(client.get("/transactions").text)
    assert "55 tranzakció" in text
    assert "1. oldal / 2" in text
    assert "Következő" in text
    page2 = _text(client.get("/transactions", params={"page": 2}).text)
    assert "2. oldal / 2" in page2 and "Előző" in page2

    cspx = _text(client.get("/transactions", params={"ticker": "cspx"}).text)
    assert "27 tranzakció" in cspx
    deposits = _text(client.get("/transactions", params={"type": "deposit"}).text)
    assert "1 tranzakció" in deposits and "Befizetés" in deposits
    # Budapest days: 2 Jan 00:00 - 3 Jan 24:00 -> days 2 and 3 for both tickers
    ranged = client.get(
        "/transactions", params={"date_from": "2026-01-02", "date_to": "2026-01-03"}
    )
    assert "4 tranzakció" in _text(ranged.text)


def test_transactions_page_invalid_filters(client: TestClient) -> None:
    r = client.get(
        "/transactions", params={"date_from": "x", "date_to": "2026-13-01", "type": "swap"}
    )
    text = _text(r.text)
    assert "Érvénytelen szűrő: Dátumtól" in text
    assert "Érvénytelen szűrő: Dátumig" in text
    assert "Érvénytelen szűrő: Típus" in text
