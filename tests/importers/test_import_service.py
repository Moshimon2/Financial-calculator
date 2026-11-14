from datetime import timedelta
from pathlib import Path

import pytest
from sqlmodel import Session

from fincalc.db.repository import Repository
from fincalc.services import imports as svc

FIXTURE = Path(__file__).parent / "fixtures" / "lightyear_account_statement.csv"


def test_preview_saves_nothing_then_confirm(session: Session) -> None:
    repo = Repository(session)
    store = svc.PreviewStore()
    p = svc.create_preview(repo, "lightyear", "s.csv", FIXTURE.read_bytes(), store)
    assert (p.rows_total, p.rows_new, p.rows_duplicate, len(p.errors), len(p.skipped)) == (
        7,
        5,
        0,
        0,
        2,
    )
    assert repo.count_transactions() == 0
    assert store.get(p.id) is p

    record = svc.confirm_preview(repo, p.id, store)
    assert (record.rows_total, record.rows_new, record.rows_duplicate) == (7, 5, 0)
    assert repo.count_transactions() == 5
    with pytest.raises(svc.PreviewNotFoundError):
        svc.confirm_preview(repo, p.id, store)  # cannot be confirmed twice


def test_importing_same_file_twice_adds_nothing(session: Session) -> None:
    repo = Repository(session)
    store = svc.PreviewStore()
    first = svc.create_preview(repo, "lightyear", "s.csv", FIXTURE.read_bytes(), store)
    svc.confirm_preview(repo, first.id, store)

    second = svc.create_preview(repo, "lightyear", "s.csv", FIXTURE.read_bytes(), store)
    assert (second.rows_new, second.rows_duplicate) == (0, 5)
    assert {r.status for r in second.rows} == {svc.RowStatus.DUPLICATE}
    record = svc.confirm_preview(repo, second.id, store)
    assert (record.rows_new, record.rows_duplicate) == (0, 5)
    assert repo.count_transactions() == 5


def test_two_overlapping_previews_confirmed_in_turn(session: Session) -> None:
    repo = Repository(session)
    store = svc.PreviewStore()
    a = svc.create_preview(repo, "lightyear", "a.csv", FIXTURE.read_bytes(), store)
    b = svc.create_preview(repo, "lightyear", "b.csv", FIXTURE.read_bytes(), store)
    svc.confirm_preview(repo, a.id, store)
    record = svc.confirm_preview(repo, b.id, store)  # duplicates re-checked at save time
    assert record.rows_new == 0
    assert repo.count_transactions() == 5


def test_unknown_broker(session: Session) -> None:
    with pytest.raises(svc.UnknownBrokerError):
        svc.create_preview(Repository(session), "xtb", "x.csv", b"", svc.PreviewStore())


def test_store_expiry_and_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr("fincalc.services.imports.time.monotonic", lambda: now[0])
    store = svc.PreviewStore(ttl=timedelta(minutes=30), max_items=2)

    def make(i: int) -> svc.ImportPreview:
        return svc.ImportPreview(str(i), "lightyear", "f.csv", [], [], [])

    store.add(make(1))
    now[0] += 1
    store.add(make(2))
    now[0] += 1
    store.add(make(3))  # capacity 2: the oldest is dropped
    with pytest.raises(svc.PreviewNotFoundError):
        store.get("1")
    assert store.get("3").id == "3"
    now[0] += 31 * 60  # expired
    with pytest.raises(svc.PreviewNotFoundError):
        store.pop("3")
