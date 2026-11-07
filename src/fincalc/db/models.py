"""SQLModel tables. Calculators store nothing; only imports and transactions."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from fincalc.core.transactions import Transaction, TransactionType
from fincalc.db.types import DecimalText, UTCDateTime


def utcnow() -> datetime:
    return datetime.now(UTC)


class ImportRecord(SQLModel, table=True):
    __tablename__ = "imports"

    id: int | None = Field(default=None, primary_key=True)
    broker: str = Field(max_length=32)
    filename: str = Field(max_length=255)
    imported_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    rows_total: int = 0
    rows_new: int = 0
    rows_duplicate: int = 0
    rows_failed: int = 0


class TransactionRecord(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    broker: str = Field(max_length=32)
    external_id: str | None = Field(default=None, max_length=128)
    dedup_hash: str = Field(max_length=64, unique=True)
    type: TransactionType = Field(
        sa_type=SAEnum(
            TransactionType,
            name="transaction_type",
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
            validate_strings=True,
        ),
        index=True,
    )
    executed_at: datetime = Field(sa_type=UTCDateTime, index=True)
    ticker: str | None = Field(default=None, max_length=32, index=True)
    isin: str | None = Field(default=None, max_length=12)
    quantity: Decimal | None = Field(default=None, sa_type=DecimalText)
    price: Decimal | None = Field(default=None, sa_type=DecimalText)
    amount: Decimal = Field(sa_type=DecimalText)
    fee: Decimal = Field(default=Decimal(0), sa_type=DecimalText)
    currency: str = Field(max_length=3)
    import_id: int = Field(foreign_key="imports.id", index=True)

    @classmethod
    def from_domain(cls, tx: Transaction, import_id: int) -> "TransactionRecord":
        return cls(
            broker=tx.broker,
            external_id=tx.external_id,
            dedup_hash=tx.dedup_hash,
            type=tx.type,
            executed_at=tx.executed_at,
            ticker=tx.ticker,
            isin=tx.isin,
            quantity=tx.quantity,
            price=tx.price,
            amount=tx.amount,
            fee=tx.fee,
            currency=tx.currency,
            import_id=import_id,
        )
