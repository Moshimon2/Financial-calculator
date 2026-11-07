from decimal import Decimal

import pytest

from fincalc.web.formatting import (
    NBSP,
    format_huf,
    format_input,
    format_number,
    format_pct,
    parse_number,
)

D = Decimal


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [
        (D("12345678"), 0, "12 345 678"),
        (D("12345678.5"), 0, "12 345 679"),  # half up
        (D("1234.567"), 2, "1 234,57"),
        (D("999"), 0, "999"),
        (D("-1234567"), 0, "-1 234 567"),
        (D("-0.001"), 0, "0"),
        (D("0E-21"), 0, "0"),
        (1000, 0, "1 000"),
    ],
)
def test_format_number(value: Decimal, decimals: int, expected: str) -> None:
    assert format_number(value, decimals) == expected.replace(" ", NBSP)


def test_format_huf() -> None:
    assert format_huf(D("12345678.49")) == f"12{NBSP}345{NBSP}678{NBSP}Ft"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (D(7), "7%"),
        (D("0.07"), "0,07%"),
        (D("6.9251"), "6,93%"),
        (D("0.5"), "0,5%"),
        (D(10), "10%"),
    ],
)
def test_format_pct(value: Decimal, expected: str) -> None:
    assert format_pct(value) == expected


def test_format_input() -> None:
    assert format_input(50_000) == f"50{NBSP}000"
    assert format_input(D("7.50")) == "7,5"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("50 000", D(50000)),
        (f"50{NBSP}000", D(50000)),
        ("7,5", D("7.5")),
        ("1.5", D("1.5")),
        (" -3 ", D(-3)),
    ],
)
def test_parse_number(raw: str, expected: Decimal) -> None:
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "1,2,3", "NaN", "Infinity", ""])
def test_parse_number_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_number(raw)
