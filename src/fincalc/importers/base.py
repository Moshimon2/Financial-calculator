"""Common interface for broker statement importers.

Importers only depend on ``fincalc.core``: they turn a broker export into
``Transaction`` objects and never touch the database.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from fincalc.core.transactions import Transaction


class RowErrorCode(StrEnum):
    MISSING_VALUE = "missing_value"
    INVALID_DATE = "invalid_date"
    INVALID_NUMBER = "invalid_number"
    INVALID_VALUE = "invalid_value"


@dataclass(frozen=True)
class RowError:
    """A row that could not be imported. ``line`` is the 1-based line in the file."""

    line: int
    code: RowErrorCode
    column: str
    value: str
    message: str


@dataclass(frozen=True)
class SkippedRow:
    """A valid row of a type we do not import (e.g. currency conversion)."""

    line: int
    broker_type: str


@dataclass(frozen=True)
class ParsedRow:
    line: int
    transaction: Transaction


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)

    @property
    def transactions(self) -> list[Transaction]:
        return [r.transaction for r in self.rows]

    @property
    def rows_total(self) -> int:
        return len(self.rows) + len(self.errors) + len(self.skipped)


class ImportFormatError(ValueError):
    """The whole file is unusable (wrong format, missing columns, bad encoding)."""


class BrokerImporter(ABC):
    broker: ClassVar[str]

    @abstractmethod
    def parse(self, data: bytes) -> ParseResult:
        """Parse a broker export.

        A bad row never stops the import: it is reported in ``errors`` with its
        line number. Raises ``ImportFormatError`` only if the file as a whole
        cannot be read.
        """
