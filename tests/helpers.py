"""Test data builders."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import Session

from fincalc.core.transactions import Transaction, TransactionType
from fincalc.db.models import ImportRecord
from fincalc.db.repository import Repository


def make_tx(day: int, **kw: object) -> Transaction:
    base: dict[str, object] = {
        "broker": "lightyear",
        "external_id": f"LY-{day}",
        "type": TransactionType.BUY,
        "executed_at": datetime(2026, 1, day, 9, 0, tzinfo=UTC),
        "ticker": "VWCE",
        "quantity": Decimal("0.123456789"),
        "price": Decimal("123.45"),
        "amount": Decimal("-15.24"),
        "fee": Decimal("0.10"),
        "currency": "EUR",
    }
    return Transaction.model_validate(base | kw)


def seed(session: Session, txs: list[Transaction], failed: int = 0) -> ImportRecord:
    return Repository(session).save_import(
        broker="lightyear",
        filename="statement.csv",
        transactions=txs,
        rows_total=len(txs) + failed,
        rows_failed=failed,
    )
