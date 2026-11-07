# fincalc – pénzügyi kalkulátor

Self-hostolt pénzügyi kalkulátor magyar befektetőknek: kamatos kamat, infláció,
ETF költségek (TER), TBSZ adóelőny, valamint Lightyear tranzakciók importja CSV-ből.

> Állapot: **fejlesztés alatt (2. lépés – kamatos kamat és infláció a core-ban)**. A funkciók lépésenként érkeznek,
> lásd a [Fejlesztési sorrend](#fejlesztési-sorrend) részt.

## Alapelvek

- A számítási logika (`src/fincalc/core`) tiszta Python, web- és adatbázisfüggőség nélkül.
- Pénzösszegekhez `Decimal`, kerekítés csak megjelenítéskor.
- Adókulcsok és szabályok konfigból (`config/tax_hu.yaml`), nem beégetve.
- Minden számításhoz teszt, kézzel ellenőrzött referenciaértékekkel.
- Kód és kommentek angolul, a felület magyarul; a UI-szövegek egy helyen (`web/i18n/`).

## Projektstruktúra

```
src/fincalc/
├── core/        # tiszta számítási logika (nem importál semmit a többi rétegből)
├── importers/   # bróker CSV parserek (csak a core-ra épül)
├── db/          # SQLModel táblák, session, repository
├── api/         # FastAPI app, /api/v1 végpontok
└── web/         # Jinja2 + HTMX oldalak, statikus fájlok, i18n
config/          # tax_hu.yaml
docs/            # formulas.md – képletek és feltételezések
migrations/      # Alembic
tests/           # core/, importers/, api/
```

Függési irány: `api`, `web` → `db`, `importers`, `core`; `importers` → `core`; `core` → semmi.

## Fejlesztés

Előfeltétel: [uv](https://docs.astral.sh/uv/) (a Python 3.12-t is letölti, ha nincs meg).

```bash
uv sync
```

```bash
uv run pytest
```

```bash
uv run ruff check
```

```bash
uv run ruff format --check
```

```bash
uv run mypy src
```

Mindhárom ellenőrzésnek (pytest, ruff, mypy) zöldnek kell lennie minden commit előtt.

## Fejlesztési sorrend

1. ✅ Váz: uv, mappastruktúra, ruff, mypy, pytest
2. ✅ core – kamatos kamat és infláció
3. core – ETF költségek és TBSZ, `config/tax_hu.yaml`, `docs/formulas.md`
4. FastAPI + kalkulátor végpontok
5. Frontend a kalkulátorokhoz (Jinja2 + HTMX + Chart.js)
6. Adatbázis: SQLModel, Alembic, repository
7. Lightyear importer
8. Dashboard véglegesítése
9. Docker + OMV telepítési leírás

## Futtatás Dockerben (OMV)

A 9. lépésben kerül kidolgozásra.
