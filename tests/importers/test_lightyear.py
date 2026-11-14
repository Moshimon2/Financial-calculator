from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from fincalc.core.transactions import TransactionType
from fincalc.importers.base import ImportFormatError, RowErrorCode
from fincalc.importers.lightyear import COLUMNS, LightyearImporter

D = Decimal
FIXTURE = Path(__file__).parent / "fixtures" / "lightyear_account_statement.csv"
HEADER = ",".join(f'"{c}"' for c in [*COLUMNS.values(), "FX Rate", "Tax Amt."])


def parse_rows(*rows: str) -> object:
    return LightyearImporter().parse(("\n".join([HEADER, *rows]) + "\n").encode())


def row(**kw: str) -> str:
    values = {
        "Date": "12/11/2026 20:35:05",
        "Reference": "OR-X1",
        "Ticker": "VWCE",
        "ISIN": "IE00BK5BQT80",
        "Type": "Buy",
        "Quantity": "0.5",
        "CCY": "EUR",
        "Price/share": "100",
        "Gross Amount": "50.00",
        "Fee": "0.00",
        "Net Amt.": "50.00",
        "FX Rate": "",
        "Tax Amt.": "",
    } | kw
    return ",".join(f'"{values[c]}"' for c in [*COLUMNS.values(), "FX Rate", "Tax Amt."])


def test_fixture_parses() -> None:
    res = LightyearImporter().parse(FIXTURE.read_bytes())
    assert res.rows_total == 7
    assert res.errors == []
    assert [(s.line, s.broker_type) for s in res.skipped] == [(3, "Conversion"), (4, "Conversion")]
    types = [r.transaction.type for r in res.rows]
    assert types == [TransactionType.BUY] * 4 + [TransactionType.DEPOSIT]
    assert [r.line for r in res.rows] == [2, 5, 6, 7, 8]


def test_buy_row_fields() -> None:
    res = LightyearImporter().parse(FIXTURE.read_bytes())
    tx = res.rows[0].transaction  # MTELEKOM, HUF with a fee
    assert tx.broker == "lightyear"
    assert tx.external_id == "OR-TEST000006"
    assert tx.executed_at == datetime(2026, 11, 13, 8, 5, 5, tzinfo=UTC)
    assert (tx.ticker, tx.isin, tx.currency) == ("MTELEKOM", "HU0000073507", "HUF")
    assert tx.quantity == D("2.000000000")
    assert tx.price == D("2950.000000000")
    assert tx.fee == D("213.00")
    assert tx.amount == D("-6113.00")  # gross = net + fee leaves the account


def test_fractional_quantity_kept_exactly() -> None:
    res = LightyearImporter().parse(FIXTURE.read_bytes())
    vwce = next(r.transaction for r in res.rows if r.transaction.ticker == "VWCE")
    assert vwce.quantity == D("0.293048880")


def test_deposit_row() -> None:
    res = LightyearImporter().parse(FIXTURE.read_bytes())
    dep = res.rows[-1].transaction
    assert dep.type is TransactionType.DEPOSIT
    assert (dep.ticker, dep.isin, dep.quantity, dep.price) == (None, None, None, None)
    assert dep.amount == D("300.00")
    assert dep.fee == D("1.80")


def test_same_file_gives_same_hashes() -> None:
    a = LightyearImporter().parse(FIXTURE.read_bytes())
    b = LightyearImporter().parse(FIXTURE.read_bytes())
    assert [t.dedup_hash for t in a.transactions] == [t.dedup_hash for t in b.transactions]
    assert len({t.dedup_hash for t in a.transactions}) == 5


@pytest.mark.parametrize(
    ("lightyear_type", "expected", "sign"),
    [
        ("Sell", TransactionType.SELL, 1),
        ("dividend", TransactionType.DIVIDEND, 1),
        ("Withdrawal", TransactionType.WITHDRAWAL, -1),
        ("FEE", TransactionType.FEE, -1),
    ],
)
def test_other_types_and_signs(lightyear_type: str, expected: TransactionType, sign: int) -> None:
    res = parse_rows(row(Type=lightyear_type, **{"Gross Amount": "10.00", "Net Amt.": "9.50"}))
    tx = res.rows[0].transaction  # type: ignore[attr-defined]
    assert tx.type is expected
    assert tx.amount == (D("9.50") if sign > 0 else D("-10.00"))


def test_amount_falls_back_when_one_column_empty() -> None:
    res = parse_rows(row(**{"Gross Amount": "", "Net Amt.": "20"}))
    assert res.rows[0].transaction.amount == D(-20)  # type: ignore[attr-defined]


def test_unknown_type_skipped() -> None:
    res = parse_rows(row(Type="Interest"), row(Reference="OR-X2"))
    assert [s.broker_type for s in res.skipped] == ["Interest"]  # type: ignore[attr-defined]
    assert len(res.rows) == 1  # type: ignore[attr-defined]


def test_bad_rows_go_to_error_list_and_do_not_stop_import() -> None:
    res = parse_rows(
        row(Reference="OR-1", Date="2026-11-12 20:35"),
        row(Reference="OR-2", Quantity="abc"),
        row(Reference="OR-3", CCY=""),
        row(Reference="OR-4", ISIN="NOT-AN-ISIN"),
        row(Reference="OR-5", **{"Gross Amount": "", "Net Amt.": ""}),
        row(Reference="OR-6", Type=""),
        row(Reference="OR-7"),
    )
    errors = {e.line: e for e in res.errors}  # type: ignore[attr-defined]
    assert errors[2].code is RowErrorCode.INVALID_DATE
    assert errors[3].code is RowErrorCode.INVALID_NUMBER
    assert (errors[3].column, errors[3].value) == ("Quantity", "abc")
    assert errors[4].code is RowErrorCode.MISSING_VALUE
    assert errors[5].code is RowErrorCode.INVALID_VALUE
    assert errors[5].column == "ISIN"
    assert errors[6].code is RowErrorCode.MISSING_VALUE
    assert errors[7].code is RowErrorCode.MISSING_VALUE
    assert errors[7].column == "Type"
    assert [r.line for r in res.rows] == [8]  # type: ignore[attr-defined]


def test_blank_lines_and_bom_ignored() -> None:
    data = ("﻿" + HEADER + "\n" + row() + "\n\n" + row(Reference="OR-2") + "\n").encode()
    res = LightyearImporter().parse(data)
    assert len(res.rows) == 2
    assert res.errors == []


def test_wrong_file_rejected() -> None:
    with pytest.raises(ImportFormatError, match="missing columns"):
        LightyearImporter().parse(b'"a","b"\n"1","2"\n')
    with pytest.raises(ImportFormatError, match="UTF-8"):
        LightyearImporter().parse(b"\xff\xfe\x00bad")
