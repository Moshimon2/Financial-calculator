"""Lightyear account statement CSV importer.

Format (web app: profile -> Settings -> Account statement -> CSV), verified
against a real export in November 2026; anonymised sample in
tests/importers/fixtures/lightyear_account_statement.csv:

    "Date","Reference","Ticker","ISIN","Type","Quantity","CCY","Price/share",
    "Gross Amount","FX Rate","Fee","Net Amt.","Tax Amt."

- Date: DD/MM/YYYY HH:MM:SS in UTC (matches the "Executed on (UTC)" time of
  the PDF trade confirmation).
- Reference: OR-... (order, one row per order), DT-... (deposit),
  CN-... (currency conversion, one row per currency leg).
- Numbers: dot as decimal separator, no thousands separator.
- Buy: Gross Amount = Net Amt. (shares x price) + Fee = cash leaving the account.

If Lightyear changes the export, only COLUMNS / TYPES / DATE_FORMAT below
should need updating.
"""

import csv
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from fincalc.core.transactions import Transaction, TransactionType
from fincalc.importers.base import (
    BrokerImporter,
    ImportFormatError,
    ParsedRow,
    ParseResult,
    RowError,
    RowErrorCode,
    SkippedRow,
)

log = logging.getLogger(__name__)

# Our field name -> Lightyear column header. The single place to fix when the
# export format changes.
COLUMNS: dict[str, str] = {
    "date": "Date",
    "reference": "Reference",
    "ticker": "Ticker",
    "isin": "ISIN",
    "type": "Type",
    "quantity": "Quantity",
    "currency": "CCY",
    "price": "Price/share",
    "gross": "Gross Amount",
    "fee": "Fee",
    "net": "Net Amt.",
}

# Lightyear "Type" (case-insensitive) -> our type. Everything else (e.g.
# "Conversion") is skipped and logged.
# TODO(open-question): only "Buy", "Deposit" and "Conversion" have been seen in
# a real export so far. The labels for sell, dividend, withdrawal and fee are
# assumptions; verify them (and the sign/amount rules in _amount) once such
# rows show up in a statement.
TYPES: dict[str, TransactionType] = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "fee": TransactionType.FEE,
}

DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

# Money leaving the account: amount is negative.
_OUTGOING = {TransactionType.BUY, TransactionType.WITHDRAWAL, TransactionType.FEE}


class RowParseError(Exception):
    def __init__(self, code: RowErrorCode, column: str, value: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.column = column
        self.value = value


def _text(row: dict[str, str], field: str) -> str | None:
    value = (row.get(COLUMNS[field]) or "").strip()
    return value or None


def _required(row: dict[str, str], field: str) -> str:
    value = _text(row, field)
    if value is None:
        raise RowParseError(RowErrorCode.MISSING_VALUE, COLUMNS[field], "", "value is missing")
    return value


def _decimal(row: dict[str, str], field: str) -> Decimal | None:
    value = _text(row, field)
    if value is None:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        number = Decimal("NaN")
    if not number.is_finite():
        raise RowParseError(
            RowErrorCode.INVALID_NUMBER, COLUMNS[field], value, f"not a number: {value!r}"
        )
    return number


def _date(row: dict[str, str]) -> datetime:
    value = _required(row, "date")
    try:
        return datetime.strptime(value, DATE_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        raise RowParseError(
            RowErrorCode.INVALID_DATE, COLUMNS["date"], value, f"expected {DATE_FORMAT}"
        ) from None


def _amount(tx_type: TransactionType, gross: Decimal | None, net: Decimal | None) -> Decimal:
    """Cash effect on the account, with sign.

    Outgoing (buy, withdrawal, fee): the gross amount, which includes the fee.
    Incoming (sell, dividend, deposit): the net amount.
    """
    if tx_type in _OUTGOING:
        value = gross if gross is not None else net
        column = COLUMNS["gross"]
    else:
        value = net if net is not None else gross
        column = COLUMNS["net"]
    if value is None:
        raise RowParseError(RowErrorCode.MISSING_VALUE, column, "", "amount is missing")
    return -abs(value) if tx_type in _OUTGOING else abs(value)


class LightyearImporter(BrokerImporter):
    broker = "lightyear"

    def parse(self, data: bytes) -> ParseResult:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportFormatError("the file is not UTF-8 text") from exc

        reader = csv.DictReader(io.StringIO(text, newline=""))
        header = [h.strip() for h in (reader.fieldnames or [])]
        missing = [c for c in COLUMNS.values() if c not in header]
        if missing:
            raise ImportFormatError(
                "not a Lightyear account statement: missing columns " + ", ".join(missing)
            )
        reader.fieldnames = header

        result = ParseResult()
        for row in reader:
            line = reader.line_num
            if not any((v or "").strip() for v in row.values()):
                continue  # blank line
            try:
                self._parse_row(row, line, result)
            except RowParseError as exc:
                result.errors.append(RowError(line, exc.code, exc.column, exc.value, str(exc)))
        return result

    def _parse_row(self, row: dict[str, str], line: int, result: ParseResult) -> None:
        broker_type = _required(row, "type")
        tx_type = TYPES.get(broker_type.lower())
        if tx_type is None:
            log.info("Lightyear line %d: skipping type %r", line, broker_type)
            result.skipped.append(SkippedRow(line, broker_type))
            return

        executed_at = _date(row)
        quantity = _decimal(row, "quantity")
        price = _decimal(row, "price")
        fee = _decimal(row, "fee") or Decimal(0)
        amount = _amount(tx_type, _decimal(row, "gross"), _decimal(row, "net"))
        try:
            tx = Transaction(
                broker=self.broker,
                external_id=_text(row, "reference"),
                type=tx_type,
                executed_at=executed_at,
                ticker=_text(row, "ticker"),
                isin=_text(row, "isin"),
                quantity=quantity,
                price=price,
                amount=amount,
                fee=abs(fee),
                currency=_required(row, "currency").upper(),
            )
        except ValidationError as exc:
            err = exc.errors()[0]
            field = str(err["loc"][0]) if err["loc"] else ""
            column = COLUMNS.get({"external_id": "reference"}.get(field, field), field)
            raise RowParseError(
                RowErrorCode.INVALID_VALUE, column, str(err.get("input", "")), err["msg"]
            ) from None
        result.rows.append(ParsedRow(line, tx))


IMPORTERS: dict[str, BrokerImporter] = {LightyearImporter.broker: LightyearImporter()}
