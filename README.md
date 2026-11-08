# fincalc – pénzügyi kalkulátor

Self-hostolt pénzügyi kalkulátor magyar befektetőknek: kamatos kamat, infláció,
ETF költségek (TER), TBSZ adóelőny, valamint Lightyear tranzakciók importja CSV-ből.

> Állapot: **fejlesztés alatt (8. lépés – Docker és OMV telepítés; a Lightyear import még hátravan)**. A funkciók lépésenként érkeznek,
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
8. ✅ Docker + OMV telepítési leírás
9. Lightyear importer, import és tranzakciók oldal – **egy valódi, anonimizált
   Lightyear CSV mintára vár** (még nincs Lightyear fiók), ezért került a végére.

## Futtatás Dockerben

Egy konténer (`python:3.12-slim`, több lépcsős build, nem root felhasználó), az SQLite
adatbázis egy kötetre kerül, így újraépítésnél sem vész el. Induláskor lefutnak az Alembic
migrációk. A konténer a 8000-es porton figyel, a host felé alapból a **8090**-es port megy.

A `docker-compose.yml` alapból **közvetlenül a GitHub repóból építi** az image-et
(`main` ág), így a szerveren nem kell a forráskód. Beállítások: `.env.example`.

| Változó | Alapérték | Jelentés |
|---|---|---|
| `FINCALC_DATA_DIR` | `./data` | Host mappa az adatbázisnak (OMV-n a HDD-n!) |
| `FINCALC_PORT` | `8090` | Host port |
| `PUID` / `PGID` | `1000` / `1000` | Ezzel a user/csoporttal fut a konténer; írnia kell a mappát |
| `FINCALC_TIMEZONE` | `Europe/Budapest` | Megjelenítési időzóna (tárolás UTC-ben) |
| `FINCALC_LOG_LEVEL` | `info` | `critical`, `error`, `warning`, `info`, `debug` |
| `FINCALC_BUILD_CONTEXT` | GitHub repó | `.` = helyi forrásból épít |

### Helyben (fejlesztői gépen)

```bash
cp .env.example .env
```

A `.env`-ben állítsd be: `FINCALC_BUILD_CONTEXT=.`, majd:

```bash
docker compose up -d --build
```

Felület: <http://localhost:8090>

### Telepítés OMV-re a Compose plugin felületén (terminál nélkül)

Előfeltétel: OMV 7, telepített **openmediavault-compose** plugin
(*Rendszer → Bővítmények*), és a *Szolgáltatások → Compose → Beállítások* alatt
megadott mappa a compose fájloknak.

1. **Adatmappa a HDD-n.** *Tárhely → Megosztott mappák → Létrehozás*: név `fincalc`,
   fájlrendszer: a **HDD** (ne a rendszer SSD), jogosultság az alapértelmezett
   („Administrator: read/write, Users: read/write, Others: read-only”).
   Mentés után a listában látszik az abszolút útvonal, pl.
   `/srv/dev-disk-by-uuid-1234abcd-…/fincalc/` – ezt jegyezd fel.
2. **Compose fájl.** *Szolgáltatások → Compose → Fájlok → Létrehozás (+)*:
   - **Név:** `fincalc`
   - **Fájl:** másold be a repó `docker-compose.yml` tartalmát változtatás nélkül.
   - **Környezet (Environment):** másold be ezt, az útvonalat az 1. lépésből cserélve:

     ```
     FINCALC_DATA_DIR=/srv/dev-disk-by-uuid-1234abcd-…/fincalc
     FINCALC_PORT=8090
     PUID=1000
     PGID=100
     FINCALC_TIMEZONE=Europe/Budapest
     FINCALC_LOG_LEVEL=info
     ```

     A `PGID=100` az OMV `users` csoportja: az alapértelmezett jogosultságú megosztott
     mappát ez a csoport írhatja, így nincs szükség `chown`-ra.
   - Mentés.
3. **Indítás.** Jelöld ki a `fincalc` sort, és nyomd meg az **Up** gombot. Az első
   indításkor az OMV letölti a forrást a GitHubról és megépíti az image-et
   (pár perc). Utána a konténer állapota *healthy* lesz
   (*Szolgáltatások → Compose → Konténerek*).
4. **Megnyitás:** `http://<omv-ip-cime>:8090`

**Frissítés új verzióra:** a `fincalc` sornál **Down**, majd **Build** (újraépíti a
`main` ág aktuális állapotából), végül **Up**. Az adatbázis a megosztott mappában marad.

**Ha a konténer újraindul és nem lesz healthy:** a naplóban
(*Konténerek → fincalc → Napló*) a `Database folder … is not writable` üzenet azt
jelenti, hogy a `PUID`/`PGID` nem írhatja az adatmappát – ellenőrizd az 1. lépés
jogosultságait vagy a `PGID` értékét.

**Mentés:** a `fincalc` megosztott mappát vedd fel a meglévő backup rutinba
(pl. *Szolgáltatások → Rsync* vagy a backup plugin). Az SQLite fájlt akkor a
legbiztonságosabb másolni, amikor épp nem írsz bele (pl. éjszakai mentés), vagy
mentés előtt **Down**.

**Biztonság:** az MVP-ben nincs bejelentkezés. Csak a helyi hálózaton használd,
ne nyiss rá portot a routeren, és ne tedd ki reverse proxyval az internetre, amíg
nincs hitelesítés (lásd roadmap).
