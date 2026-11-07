from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from fincalc.core.transactions import Transaction, TransactionType
from fincalc.db.models import ImportRecord, TransactionRecord
from fincalc.db.repository import Repository, TransactionFilter

D = Decimal


def tx(day: int, **kw: object) -> Transaction:
    base: dict[str, object] = {
        "broker": "lightyear",
        "external_id": f"LY-{day}",
        "type": TransactionType.BUY,
        "executed_at": datetime(2026, 1, day, 9, 0, tzinfo=UTC),
        "ticker": "VWCE",
        "quantity": D("0.123456789"),
        "price": D("123.45"),
        "amount": D("-15.24"),
        "fee": D("0.10"),
        "currency": "EUR",
    }
    return Transaction.model_validate(base | kw)


def save(repo: Repository, txs: list[Transaction], failed: int = 0) -> ImportRecord:
    return repo.save_import(
        broker="lightyear",
        filename="statement.csv",
        transactions=txs,
        rows_total=len(txs) + failed,
        rows_failed=failed,
    )


def test_save_import_counts_and_roundtrip(session: Session) -> None:
    repo = Repository(session)
    rec = save(repo, [tx(1), tx(2)], failed=1)
    assert (rec.rows_total, rec.rows_new, rec.rows_duplicate, rec.rows_failed) == (3, 2, 0, 1)
    assert rec.imported_at.tzinfo == UTC

    stored = session.exec(select(TransactionRecord).order_by(col(TransactionRecord.id))).all()
    assert len(stored) == 2
    first = stored[0]
    assert first.quantity == D("0.123456789")  # exact Decimal round-trip
    assert first.fee == D("0.10")
    assert first.executed_at == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert first.type is TransactionType.BUY
    assert first.import_id == rec.id


def test_same_file_twice_creates_no_duplicates(session: Session) -> None:
    repo = Repository(session)
    save(repo, [tx(1), tx(2)])
    second = save(repo, [tx(1), tx(2), tx(3)])
    assert (second.rows_new, second.rows_duplicate) == (1, 2)
    assert repo.count_transactions() == 3


def test_duplicates_within_one_batch(session: Session) -> None:
    rec = save(Repository(session), [tx(1), tx(1)])
    assert (rec.rows_new, rec.rows_duplicate) == (1, 1)


def test_unique_constraint_on_hash(session: Session) -> None:
    rec = save(Repository(session), [tx(1)])
    assert rec.id is not None
    session.add(TransactionRecord.from_domain(tx(1), rec.id))
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_key_enforced(session: Session) -> None:
    session.add(TransactionRecord.from_domain(tx(1), import_id=999))
    with pytest.raises(IntegrityError):
        session.commit()


def test_existing_hashes(session: Session) -> None:
    repo = Repository(session)
    assert repo.existing_hashes([]) == set()
    save(repo, [tx(1)])
    assert repo.existing_hashes([tx(1).dedup_hash, tx(2).dedup_hash]) == {tx(1).dedup_hash}


def test_list_imports_newest_first(session: Session) -> None:
    repo = Repository(session)
    a = save(repo, [tx(1)])
    b = save(repo, [tx(2)])
    assert [i.id for i in repo.list_imports()] == [b.id, a.id]


def test_list_transactions_filters_and_paging(session: Session) -> None:
    repo = Repository(session)
    save(
        repo,
        [
            tx(1),
            tx(2, ticker="CSPX"),
            tx(3, type=TransactionType.DIVIDEND, quantity=None, price=None, amount=D("1.2")),
            tx(
                4,
                type=TransactionType.DEPOSIT,
                ticker=None,
                quantity=None,
                price=None,
                amount=D("500"),
            ),
            tx(5),
        ],
    )
    page = repo.list_transactions()
    assert page.total == 5
    assert [t.external_id for t in page.items] == ["LY-5", "LY-4", "LY-3", "LY-2", "LY-1"]

    assert repo.list_transactions(TransactionFilter(ticker="vwce")).total == 3
    assert repo.list_transactions(TransactionFilter(type=TransactionType.DEPOSIT)).total == 1
    flt = TransactionFilter(
        date_from=datetime(2026, 1, 2, tzinfo=UTC), date_to=datetime(2026, 1, 4, tzinfo=UTC)
    )
    assert [t.external_id for t in repo.list_transactions(flt).items] == ["LY-3", "LY-2"]

    paged = repo.list_transactions(limit=2, offset=2)
    assert paged.total == 5
    assert [t.external_id for t in paged.items] == ["LY-3", "LY-2"]


def test_latest_purchase(session: Session) -> None:
    repo = Repository(session)
    assert repo.latest_purchase() is None
    save(
        repo,
        [
            tx(1),
            tx(7, ticker="CSPX"),
            tx(9, type=TransactionType.SELL, amount=D("20")),
        ],
    )
    latest = repo.latest_purchase()
    assert latest is not None
    assert (latest.external_id, latest.ticker) == ("LY-7", "CSPX")


def test_naive_datetime_rejected_by_column(session: Session) -> None:
    rec = save(Repository(session), [])
    assert rec.id is not None
    record = TransactionRecord.from_domain(tx(1), rec.id)
    record.executed_at = datetime(2026, 1, 1)
    session.add(record)
    with pytest.raises(Exception, match="timezone-aware"):
        session.commit()


def test_save_import_rolls_back_on_error(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Repository(session)

    def boom() -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(session, "commit", boom)
    with pytest.raises(RuntimeError):
        save(repo, [tx(1)])
    monkeypatch.undo()
    assert repo.count_transactions() == 0
    assert repo.list_imports() == []
