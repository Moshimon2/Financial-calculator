from pathlib import Path

import pytest

from fincalc import cli
from fincalc.db import session as db_session

FIXTURE = Path(__file__).parent / "importers" / "fixtures" / "lightyear_account_statement.csv"


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(db_session.DATABASE_URL_ENV, f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("FINCALC_AUTO_MIGRATE", "1")
    db_session.get_engine.cache_clear()
    yield
    db_session.get_engine().dispose()
    db_session.get_engine.cache_clear()


def run(argv: list[str], answer: str = "") -> tuple[int, str]:
    lines: list[str] = []
    args = cli.build_parser().parse_args(argv)
    code = cli.cmd_import(args, lines.append, lambda _: answer)
    return code, "\n".join(lines)


@pytest.mark.usefixtures("db")
def test_cli_import_confirm_and_repeat() -> None:
    code, out = run(["import", "lightyear", str(FIXTURE)], answer="y")
    assert code == 0
    assert "7 total, 5 new, 0 duplicate, 0 failed, 2 skipped" in out
    assert "skipped types: Conversion" in out
    assert "5 new transactions" in out

    code, out = run(["import", "lightyear", str(FIXTURE), "--yes"])
    assert code == 0
    assert "Nothing new to import." in out


@pytest.mark.usefixtures("db")
def test_cli_cancel_and_errors(tmp_path: Path) -> None:
    code, out = run(["import", "lightyear", str(FIXTURE)], answer="n")
    assert (code, "Cancelled" in out) == (0, True)

    bad = tmp_path / "bad.csv"
    bad.write_text('"a"\n"1"\n')
    code, out = run(["import", "lightyear", str(bad)])
    assert code == 1 and "missing columns" in out

    lines = FIXTURE.read_text().splitlines()
    lines[1] = lines[1].replace('"2.000000000"', '"x"')
    broken = tmp_path / "broken.csv"
    broken.write_text("\n".join(lines))
    code, out = run(["import", "lightyear", str(broken), "-y"])
    assert "line 2: Quantity: not a number: 'x'" in out

    code, out = run(["import", "lightyear", str(tmp_path / "missing.csv")])
    assert code == 2 and "cannot read" in out


def test_main_rejects_unknown_broker() -> None:
    with pytest.raises(SystemExit):
        cli.main(["import", "xtb", "file.csv"])
