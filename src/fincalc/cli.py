"""Command line interface.

    fincalc import lightyear path/to/statement.csv [--yes]

Shows the same preview as the web UI (new / duplicate / failed / skipped rows)
and saves the new transactions after confirmation.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from sqlmodel import Session

from fincalc.db.migrate import upgrade_to_head
from fincalc.db.repository import Repository
from fincalc.db.session import database_url, ensure_sqlite_writable, get_engine
from fincalc.importers.base import ImportFormatError
from fincalc.importers.lightyear import IMPORTERS
from fincalc.services import imports as svc
from fincalc.settings import auto_migrate


def _print_preview(p: svc.ImportPreview, out: Callable[[str], None]) -> None:
    out(f"File: {p.filename} ({p.broker})")
    out(
        f"Rows: {p.rows_total} total, {p.rows_new} new, {p.rows_duplicate} duplicate, "
        f"{len(p.errors)} failed, {len(p.skipped)} skipped"
    )
    for e in p.errors:
        out(f"  line {e.line}: {e.column}: {e.message}")
    if p.skipped:
        types = sorted({s.broker_type for s in p.skipped})
        out(f"  skipped types: {', '.join(types)}")


def cmd_import(
    args: argparse.Namespace, out: Callable[[str], None], ask: Callable[[str], str]
) -> int:
    path = Path(args.file)
    try:
        data = path.read_bytes()
    except OSError as exc:
        out(f"error: cannot read {path}: {exc.strerror}")
        return 2

    ensure_sqlite_writable(database_url())
    if auto_migrate():
        upgrade_to_head()

    with Session(get_engine()) as session:
        repo = Repository(session)
        store = svc.PreviewStore()
        try:
            preview = svc.create_preview(repo, args.broker, path.name, data, store)
        except ImportFormatError as exc:
            out(f"error: {exc}")
            return 1
        _print_preview(preview, out)
        if preview.rows_new == 0:
            out("Nothing new to import.")
            return 0
        if not args.yes and ask(
            f"Save {preview.rows_new} new transactions? [y/N] "
        ).strip().lower() not in {"y", "yes", "i", "igen"}:
            out("Cancelled, nothing saved.")
            return 0
        record = svc.confirm_preview(repo, preview.id, store)
        out(f"Saved import #{record.id}: {record.rows_new} new transactions.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fincalc", description="fincalc command line tools")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="import a broker statement")
    imp.add_argument("broker", choices=sorted(IMPORTERS))
    imp.add_argument("file", help="path to the exported statement")
    imp.add_argument("-y", "--yes", action="store_true", help="save without asking")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_import(args, print, input)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
