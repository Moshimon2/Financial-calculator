"""Hungarian number formatting for the UI (registered as Jinja filters).

12345678 -> "12 345 678 Ft": thousands separated by a no-break space, decimal
comma. This is the only place where money is rounded for display.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

NBSP = "\u00a0"
Number = Decimal | int | float | str


def format_number(value: Number, decimals: int = 0) -> str:
    """12345.678 -> '12 345,68' (decimals=2)."""
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)  # avoid "-0"
    return f"{q:,.{decimals}f}".replace(",", NBSP).replace(".", ",")


def format_huf(value: Number) -> str:
    """Whole forints with suffix: '12 345 678 Ft'."""
    return f"{format_number(value, 0)}{NBSP}Ft"


def format_pct(value: Number, decimals: int = 2) -> str:
    """Percent with trailing zeros trimmed: 7 -> '7%', 0.07 -> '0,07%'."""
    text = format_number(value, decimals)
    if "," in text:
        text = text.rstrip("0").rstrip(",")
    return f"{text}%"


def format_input(value: Number) -> str:
    """Value prefilled in a text input: grouping kept, no suffix ('50 000', '7,5')."""
    d = Decimal(str(value)).normalize()
    decimals = max(0, -d.as_tuple().exponent)  # type: ignore[operator]
    return format_number(d, decimals)


def parse_number(raw: str) -> Decimal:
    """Parse user input such as '50 000', '7,5' or '1.5'. Raises ValueError."""
    cleaned = raw.strip().replace(NBSP, "").replace(" ", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {raw!r}") from exc
    if not value.is_finite():
        raise ValueError(f"not a finite number: {raw!r}")
    return value
