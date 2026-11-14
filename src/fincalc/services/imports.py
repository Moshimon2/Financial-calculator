"""Two-step import: preview (parse + duplicate check, nothing saved) and confirm.

The uploaded file is never written to disk: only the parsed transactions are
kept in memory until confirmation, and dropped after ``PREVIEW_TTL``.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum

from fincalc.core.transactions import Transaction
from fincalc.db.models import ImportRecord
from fincalc.db.repository import Repository
from fincalc.importers.base import BrokerImporter, ParseResult, RowError, SkippedRow
from fincalc.importers.lightyear import IMPORTERS

PREVIEW_TTL = timedelta(minutes=30)
MAX_PREVIEWS = 20
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class UnknownBrokerError(KeyError):
    pass


class PreviewNotFoundError(KeyError):
    pass


class RowStatus(StrEnum):
    NEW = "new"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class PreviewRow:
    line: int
    status: RowStatus
    transaction: Transaction


@dataclass
class ImportPreview:
    id: str
    broker: str
    filename: str
    rows: list[PreviewRow]
    errors: list[RowError]
    skipped: list[SkippedRow]
    created: float = field(default_factory=time.monotonic)

    @property
    def rows_total(self) -> int:
        return len(self.rows) + len(self.errors) + len(self.skipped)

    @property
    def rows_new(self) -> int:
        return sum(r.status is RowStatus.NEW for r in self.rows)

    @property
    def rows_duplicate(self) -> int:
        return sum(r.status is RowStatus.DUPLICATE for r in self.rows)


class PreviewStore:
    """Thread-safe in-memory store (single process; previews are short-lived)."""

    def __init__(self, ttl: timedelta = PREVIEW_TTL, max_items: int = MAX_PREVIEWS) -> None:
        self._ttl = ttl.total_seconds()
        self._max = max_items
        self._items: dict[str, ImportPreview] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        now = time.monotonic()
        for key in [k for k, p in self._items.items() if now - p.created > self._ttl]:
            del self._items[key]
        while len(self._items) >= self._max:
            del self._items[min(self._items, key=lambda k: self._items[k].created)]

    def add(self, preview: ImportPreview) -> None:
        with self._lock:
            self._expire()
            self._items[preview.id] = preview

    def get(self, preview_id: str) -> ImportPreview:
        with self._lock:
            self._expire()
            try:
                return self._items[preview_id]
            except KeyError:
                raise PreviewNotFoundError(preview_id) from None

    def pop(self, preview_id: str) -> ImportPreview:
        with self._lock:
            self._expire()
            try:
                return self._items.pop(preview_id)
            except KeyError:
                raise PreviewNotFoundError(preview_id) from None


previews = PreviewStore()


def get_importer(broker: str) -> BrokerImporter:
    try:
        return IMPORTERS[broker]
    except KeyError:
        raise UnknownBrokerError(broker) from None


def build_preview(
    repo: Repository, broker: str, filename: str, parsed: ParseResult
) -> ImportPreview:
    """Mark each parsed row as new or duplicate (in the DB or earlier in the file)."""
    known = repo.existing_hashes([t.dedup_hash for t in parsed.transactions])
    rows: list[PreviewRow] = []
    for parsed_row in parsed.rows:
        h = parsed_row.transaction.dedup_hash
        status = RowStatus.DUPLICATE if h in known else RowStatus.NEW
        known.add(h)
        rows.append(PreviewRow(parsed_row.line, status, parsed_row.transaction))
    return ImportPreview(
        id=uuid.uuid4().hex,
        broker=broker,
        filename=filename,
        rows=rows,
        errors=parsed.errors,
        skipped=parsed.skipped,
    )


def create_preview(
    repo: Repository, broker: str, filename: str, data: bytes, store: PreviewStore = previews
) -> ImportPreview:
    """Parse an upload and keep the preview until it is confirmed. Saves nothing."""
    parsed = get_importer(broker).parse(data)
    preview = build_preview(repo, broker, filename, parsed)
    store.add(preview)
    return preview


def confirm_preview(
    repo: Repository, preview_id: str, store: PreviewStore = previews
) -> ImportRecord:
    """Save the new transactions of a preview. Duplicates are re-checked at save time."""
    preview = store.pop(preview_id)
    return repo.save_import(
        broker=preview.broker,
        filename=preview.filename,
        transactions=[r.transaction for r in preview.rows],
        rows_total=preview.rows_total,
        rows_failed=len(preview.errors),
    )
