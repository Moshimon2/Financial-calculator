"""Broker-independent transaction model shared by importers and storage."""

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"


def _canonical(value: Decimal | None) -> str:
    """'1.50' and '1.5' must hash the same."""
    if value is None:
        return ""
    normalized = value.normalize()
    return format(normalized, "f") if normalized != 0 else "0"


class Transaction(BaseModel):
    """A normalised broker transaction (output of every BrokerImporter)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker: str = Field(min_length=1, max_length=32)
    external_id: str | None = Field(default=None, max_length=128)
    type: TransactionType
    executed_at: datetime = Field(description="Timezone-aware; stored in UTC")
    ticker: str | None = Field(default=None, max_length=32)
    isin: str | None = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    quantity: Decimal | None = None
    price: Decimal | None = None
    amount: Decimal = Field(description="Total amount with sign (negative = money out)")
    fee: Decimal = Decimal(0)
    currency: str = Field(pattern=r"^[A-Z]{3}$", description="ISO 4217 code")

    @field_validator("executed_at")
    @classmethod
    def _to_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("executed_at must be timezone-aware")
        return v.astimezone(UTC)

    @property
    def dedup_hash(self) -> str:
        """Stable identity for duplicate detection.

        Uses the broker's transaction ID when present, otherwise
        date + ticker + quantity + amount (as the spec requires).
        """
        if self.external_id:
            key = f"{self.broker}|id|{self.external_id}"
        else:
            key = "|".join(
                (
                    self.broker,
                    "row",
                    self.executed_at.isoformat(),
                    self.ticker or "",
                    _canonical(self.quantity),
                    _canonical(self.amount),
                )
            )
        return hashlib.sha256(key.encode()).hexdigest()
