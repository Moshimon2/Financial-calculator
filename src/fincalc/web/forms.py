"""Parsing HTML form input into calculator inputs, with Hungarian error messages."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import ValidationError

from fincalc.web.formatting import format_number, parse_number


@dataclass(frozen=True)
class FormField:
    name: str
    default: str
    kind: Literal["decimal", "int"] = "decimal"
    optional: bool = False


def defaults(fields: tuple[FormField, ...]) -> dict[str, str]:
    return {f.name: f.default for f in fields}


def parse_form(
    form: Mapping[str, Any], fields: tuple[FormField, ...], errors_text: dict[str, str]
) -> tuple[dict[str, str], dict[str, Decimal | int | None], dict[str, str]]:
    """Return (raw values for re-rendering, parsed values, field errors)."""
    raw: dict[str, str] = {}
    values: dict[str, Decimal | int | None] = {}
    errors: dict[str, str] = {}
    for f in fields:
        text = str(form.get(f.name, "")).strip()
        raw[f.name] = text
        if not text:
            if f.optional:
                values[f.name] = None
            else:
                errors[f.name] = errors_text["missing"]
            continue
        try:
            number = parse_number(text)
            if f.kind == "int":
                if number != number.to_integral_value():
                    raise ValueError("not an integer")
                values[f.name] = int(number)
            else:
                values[f.name] = number
        except ValueError:
            errors[f.name] = errors_text["invalid_number"]
    return raw, values, errors


def validation_messages(exc: ValidationError, errors_text: dict[str, str]) -> dict[str, str]:
    """Map Pydantic errors to {field: Hungarian message}."""
    messages: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][0]) if err["loc"] else ""
        template = errors_text.get(err["type"], errors_text["default"])
        ctx = {
            k: format_number(v, 2).rstrip("0").rstrip(",")
            if isinstance(v, int | float | Decimal)
            else v
            for k, v in (err.get("ctx") or {}).items()
        }
        try:
            message = template.format(**ctx)
        except (KeyError, IndexError):
            message = errors_text["default"]
        messages.setdefault(field, message)
    return messages
