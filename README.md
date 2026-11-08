# fincalc – pénzügyi kalkulátor

Self-hostolt pénzügyi kalkulátor magyar befektetőknek: kamatos kamat, infláció,
ETF költségek (TER), TBSZ adóelőny, valamint Lightyear tranzakciók importja CSV-ből.

> Állapot: **fejlesztés alatt (7. lépés – dashboard; a Lightyear import még hátravan)**. A funkciók lépésenként érkeznek,
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

### Indítás helyben

```bash
uv run uvicorn fincalc.api.main:app --reload
```

- Webes felület: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/v1/health>
- Kalkulátorok: `POST /api/v1/calc/compound`, `/inflation`, `/etf-costs`, `/tbsz`
- Tranzakciók: `GET /api/v1/transactions` (szűrés: `date_from`, `date_to`, `ticker`, `type`,
  lapozás: `limit`, `offset`), `GET /api/v1/transactions/latest`

Példa:

```bash
curl -X POST localhost:8000/api/v1/calc/compound -H 'content-type: application/json' -d '{"initial_amount": 0, "monthly_contribution": 50000, "annual_return_pct": 7, "years": 20, "annual_inflation_pct": 4}'
```

A pénzösszegek a válaszban kerekítetlen decimális stringek (pl. `"26046332.99127..."`);
a kerekítés a megjelenítő feladata. Bemenetként szám és string is elfogadott.

### Adatbázis

SQLite + SQLModel, a séma Alembic migrációkkal követve. Az adatbázis helye a
`FINCALC_DATABASE_URL` környezeti változóból jön (alapértelmezés: `sqlite:///./data/fincalc.db`).

Induláskor az app automatikusan lefuttatja a migrációkat (`FINCALC_AUTO_MIGRATE=0`
kikapcsolja). Kézzel:

```bash
uv run alembic upgrade head
```

Modellváltozás után új migráció:

```bash
uv run alembic revision --autogenerate -m "rövid leírás"
```

- Táblák: `imports` (importnapló) és `transactions` (`src/fincalc/db/models.py`).
- A pénzösszegek pontosan, szövegként tárolódnak (`DecimalText`), a dátumok UTC-ben (`UTCDateTime`).
- Duplikátumszűrés a `dedup_hash` egyedi mezővel: bróker-azonosító, vagy ha nincs,
  dátum + ticker + darab + összeg hash-e (`fincalc.core.transactions`).

### Frontend

- Szerveroldali Jinja2 sablonok (`src/fincalc/web/templates`), HTMX élő frissítéssel
  (gépelés után 400 ms-mal újraszámol), Chart.js grafikonok.
- A HTMX és a Chart.js a repóban van (`web/static/vendor/`), így internet nélkül is működik.
- Minden UI-szöveg: `src/fincalc/web/i18n/hu.py`; számformázás: `src/fincalc/web/formatting.py`
  (Jinja filterek: `huf`, `num`, `pct`).
- Világos/sötét mód a rendszerbeállítás szerint (CSS változók, `prefers-color-scheme`).

Mindhárom ellenőrzésnek (pytest, ruff, mypy) zöldnek kell lennie minden commit előtt.

## Fejlesztési sorrend

1. ✅ Váz: uv, mappastruktúra, ruff, mypy, pytest
2. ✅ core – kamatos kamat és infláció
3. ✅ core – ETF költségek és TBSZ, `config/tax_hu.yaml`, `docs/formulas.md`
4. ✅ FastAPI + kalkulátor végpontok
5. ✅ Frontend a kalkulátorokhoz (Jinja2 + HTMX + Chart.js)
6. ✅ Adatbázis: SQLModel, Alembic, repository
7. ✅ Dashboard véglegesítése: utolsó vásárlás kártya és összesítők, tranzakció API
8. Docker + OMV telepítési leírás
9. Lightyear importer, import és tranzakciók oldal – **egy valódi, anonimizált
   Lightyear CSV mintára vár** (még nincs Lightyear fiók), ezért került a végére.

## Futtatás Dockerben (OMV)

A 9. lépésben kerül kidolgozásra.
