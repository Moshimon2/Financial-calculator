from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from fincalc.core.transactions import Transaction, TransactionType

D = Decimal
BASE: dict[str, object] = {
    "broker": "lightyear",
    "type": TransactionType.BUY,
    "executed_at": datetime(2026, 3, 1, 10, 30, tzinfo=UTC),
    "ticker": "VWCE",
    "quantity": D("1.5"),
    "price": D("100"),
    "amount": D("-150"),
    "currency": "EUR",
}


def tx(**overrides: object) -> Transaction:
    return Transaction.model_validate(BASE | overrides)


def test_converts_to_utc() -> None:
    budapest = timezone(timedelta(hours=1))
    t = tx(executed_at=datetime(2026, 3, 1, 11, 30, tzinfo=budapest))
    assert t.executed_at == datetime(2026, 3, 1, 10, 30, tzinfo=UTC)
    assert t.executed_at.tzinfo == UTC


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        tx(executed_at=datetime(2026, 3, 1))


@pytest.mark.parametrize(
    "overrides",
    [{"currency": "eur"}, {"currency": "EURO"}, {"isin": "XX"}, {"broker": ""}, {"type": "swap"}],
)
def test_validation(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        tx(**overrides)


def test_valid_isin() -> None:
    assert tx(isin="IE00BK5BQT80").isin == "IE00BK5BQT80"


def test_hash_uses_external_id_when_present() -> None:
    a = tx(external_id="LY-1")
    b = tx(external_id="LY-1", amount=D("-999"), ticker="OTHER")
    assert a.dedup_hash == b.dedup_hash
    assert a.dedup_hash != tx(external_id="LY-2").dedup_hash


def test_hash_without_id_uses_date_ticker_quantity_amount() -> None:
    assert tx().dedup_hash == tx(price=D("101"), fee=D("1")).dedup_hash
    assert tx().dedup_hash == tx(quantity=D("1.50"), amount=D("-150.00")).dedup_hash
    assert tx().dedup_hash != tx(quantity=D("2")).dedup_hash
    assert tx().dedup_hash != tx(ticker="CSPX").dedup_hash
    assert tx().dedup_hash != tx(executed_at=datetime(2026, 3, 2, tzinfo=UTC)).dedup_hash
    assert tx().dedup_hash != tx(amount=D("-151")).dedup_hash


def test_hash_same_instant_in_other_timezone() -> None:
    budapest = timezone(timedelta(hours=1))
    other = tx(executed_at=datetime(2026, 3, 1, 11, 30, tzinfo=budapest))
    assert tx().dedup_hash == other.dedup_hash


def test_hash_zero_and_missing_values() -> None:
    deposit = tx(type=TransactionType.DEPOSIT, ticker=None, quantity=None, amount=D("0.00"))
    assert (
        deposit.dedup_hash
        == tx(type=TransactionType.DEPOSIT, ticker=None, quantity=None, amount=D(0)).dedup_hash
    )
    assert len(deposit.dedup_hash) == 64
