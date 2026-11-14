"""Data access for imports and transactions. No business logic beyond storage rules."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlmodel import Session, col, select

from fincalc.core.transactions import Transaction, TransactionType
from fincalc.db.models import ImportRecord, TransactionRecord


@dataclass(frozen=True)
class TransactionFilter:
    date_from: datetime | None = None  # inclusive
    date_to: datetime | None = None  # exclusive
    ticker: str | None = None
    type: TransactionType | None = None


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    limit: int
    offset: int


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- duplicates ------------------------------------------------------------

    def existing_hashes(self, hashes: Sequence[str]) -> set[str]:
        """Which of the given dedup hashes are already stored."""
        if not hashes:
            return set()
        stmt = select(TransactionRecord.dedup_hash).where(
            col(TransactionRecord.dedup_hash).in_(list(hashes))
        )
        return set(self.session.exec(stmt).all())

    # --- imports -------------------------------------------------------------------

    def save_import(
        self,
        *,
        broker: str,
        filename: str,
        transactions: Sequence[Transaction],
        rows_total: int,
        rows_failed: int,
    ) -> ImportRecord:
        """Store an import and its new transactions atomically.

        Transactions already in the database, or repeated within the batch,
        are skipped and counted as duplicates.
        """
        known = self.existing_hashes([t.dedup_hash for t in transactions])
        new: list[Transaction] = []
        for tx in transactions:
            if tx.dedup_hash not in known:
                known.add(tx.dedup_hash)
                new.append(tx)

        record = ImportRecord(
            broker=broker,
            filename=filename,
            rows_total=rows_total,
            rows_new=len(new),
            rows_duplicate=len(transactions) - len(new),
            rows_failed=rows_failed,
        )
        try:
            self.session.add(record)
            self.session.flush()
            assert record.id is not None
            self.session.add_all(TransactionRecord.from_domain(tx, record.id) for tx in new)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(record)
        return record

    def list_imports(self, limit: int = 50) -> list[ImportRecord]:
        stmt = (
            select(ImportRecord)
            .order_by(col(ImportRecord.imported_at).desc(), col(ImportRecord.id).desc())
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    # --- transactions -------------------------------------------------------------

    def list_transactions(
        self, flt: TransactionFilter | None = None, *, limit: int = 50, offset: int = 0
    ) -> Page[TransactionRecord]:
        flt = flt or TransactionFilter()
        conditions = []
        if flt.date_from is not None:
            conditions.append(col(TransactionRecord.executed_at) >= flt.date_from)
        if flt.date_to is not None:
            conditions.append(col(TransactionRecord.executed_at) < flt.date_to)
        if flt.ticker:
            conditions.append(func.upper(TransactionRecord.ticker) == flt.ticker.upper())
        if flt.type is not None:
            conditions.append(col(TransactionRecord.type) == flt.type)

        total = self.session.exec(
            select(func.count()).select_from(TransactionRecord).where(*conditions)
        ).one()
        stmt = (
            select(TransactionRecord)
            .where(*conditions)
            .order_by(col(TransactionRecord.executed_at).desc(), col(TransactionRecord.id).desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self.session.exec(stmt).all())
        return Page(items=items, total=total, limit=limit, offset=offset)

    def latest_purchase(self) -> TransactionRecord | None:
        stmt = (
            select(TransactionRecord)
            .where(col(TransactionRecord.type) == TransactionType.BUY)
            .order_by(col(TransactionRecord.executed_at).desc(), col(TransactionRecord.id).desc())
            .limit(1)
        )
        return self.session.exec(stmt).first()

    def count_transactions(self) -> int:
        return self.session.exec(select(func.count()).select_from(TransactionRecord)).one()

    def deposit_totals(self) -> dict[str, Decimal]:
        """Sum of deposits per currency (different currencies are never added up)."""
        stmt = select(col(TransactionRecord.currency), col(TransactionRecord.amount)).where(
            col(TransactionRecord.type) == TransactionType.DEPOSIT
        )
        totals: dict[str, Decimal] = {}
        for currency, amount in self.session.exec(stmt).all():
            totals[currency] = totals.get(currency, Decimal(0)) + amount
        return dict(sorted(totals.items()))
