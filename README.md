# MuniQuant Data Core

The source of truth for aluminium plant data on the MuniQuant platform: companies and plants, the sources and exact saved copies of their pages, dated facts with the precise place in the source, matching and human review, quality checks, and the plant export, **CommodityEvidencePackage 1.0.0**. Since 2026-10-26 it also keeps **market data**: each aluminium market instrument (LME cash and forward points, SHFE contracts, regional premiums…) as separate, source-traceable observations, with their own checks and export, **MarketDataPackage 1.0.0** ([docs/MARKET_DATA.md](docs/MARKET_DATA.md)). Built with Python, a small C++17 kernel and PostgreSQL (SQLite for local use).

The Data Core was separated from the MuniQuant Aluminium Trading Platform in DC1 step A. Everything here existed there before; it now has its own code, database and tests. Research, practice trading, Permutable leads, investigations and the map stay in the **Workspace**, which talks to the Core only through this API. The Core has no Workspace code, and a test ([tests/test_boundary.py](tests/test_boundary.py)) fails if any appears.

Status of the separation: [docs/DC1-A-STATUS.md](docs/DC1-A-STATUS.md); same results on real data: [docs/A6-PILOT-COMPARISON.md](docs/A6-PILOT-COMPARISON.md). Dates we store and their limits: [docs/DATES.md](docs/DATES.md). Export contract and record API: [docs/CONTRACT.md](docs/CONTRACT.md). Operations: [docs/RUNBOOK.md](docs/RUNBOOK.md). Tables: [docs/DATA_DIAGRAM.md](docs/DATA_DIAGRAM.md). Market data: [docs/MARKET_DATA.md](docs/MARKET_DATA.md).

## Used by other programs

The Workspace (leads, research, investigations and the map) runs as its own project with its own database. It reads
plants, names, documents and facts through `GET /api/records/{type}` (with equality filters) and
`GET /api/records/{type}/{id}`, and sends candidate facts as extraction requests that the Core checks like any other.
Give such a program its own entry in `WRITE_IDENTITIES_JSON`, so the history names it. The Core has no code that refers
to it. See [docs/CONTRACT.md](docs/CONTRACT.md#reading-core-records-through-the-api).

## Run locally with Python

Requires Python 3.11+ and a C++17 compiler (Apple Command Line Tools on macOS, g++ on Linux). CI and the container use Python 3.12.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install --no-build-isolation -e .
alembic upgrade head
python -m tools.seed
export WRITE_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(24))')"
printf '%s\n' "$WRITE_TOKEN"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [the data screens](http://127.0.0.1:8000), choose **Workspace access** and paste the printed token to enable editing; the browser keeps it only until reload. The API documentation is at [/docs](http://127.0.0.1:8000/docs). `python -m tools.seed` adds fictional demonstration data; leave it out for an empty database. SQLite is the default (`data/muniquant.db`, snapshots in `data/snapshots`); set `DATABASE_URL` and `SNAPSHOT_DIR` for anything else. Without `WRITE_TOKEN`, reads work and every write is refused.

## Run with PostgreSQL and Docker

```sh
cp .env.example .env
# Replace both placeholder secrets with independent generated hexadecimal strings.
docker compose up --build -d
```

The migration service runs before the app; PostgreSQL and snapshots have separate persistent volumes. `docker compose down` stops without deleting data. The image contains the runtime only: tools such as the seed are not in it.

## Test

```sh
pytest -q
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/test_db pytest -q
alembic check
```

CI runs the tests, setup, drift check and migration round trip on SQLite, PostgreSQL 16 and PostgreSQL 17, plus a container smoke and recovery test and a gitleaks secret scan ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Database

One straight migration line ([migrations/versions](migrations/versions)). Its DC1 baseline creates the 26 Core tables, 3 views and the controlled country, commodity and facility-type rows, with the same columns, keys and checks as the platform's databases on 2026-10-13 ([tests/test_schema.py](tests/test_schema.py) lists the only differences); the next migration adds the three market data tables and the export permission on access decisions. Existing platform databases are not upgraded in place; copy their Core rows into a new database:

```sh
python -m tools.core_import data/platform.db data/core.db --report data/core-import-report.json --dry-run
python -m tools.core_import data/platform.db data/core.db --report data/core-import-report.json
```

The source is opened read-only; the target must be new; the report compares counts, IDs and fingerprints of every table. Nothing is dropped: a database whose Core tables hold data in columns the Core does not define (platform databases with licensed lead feeds, for example) is refused. Those are split by the Workspace's split tool (DC1 step B3), which runs this tool with `--exclude` (rows to leave out) and `--snapshots`/`--target-snapshots` (copy the saved pages of the copied rows).

## Export, freeze and replay

```sh
python -m app.evidence_cli export data/evidence-v1.json
python -m app.evidence_cli freeze data/evidence-v1.zip
python -m app.evidence_cli replay data/evidence-v1.zip
python scripts/consume_evidence.py data/evidence-v1.json
```

The same package is served at `GET /api/export` and its schema at `GET /api/export/schema`. Output paths must not exist. Replay is offline and re-extracts parser-produced facts from the preserved bytes. Market data has its own operations: `market-export`, `market-freeze` and `market-replay` ([docs/MARKET_DATA.md](docs/MARKET_DATA.md#export-marketdatapackage-100)).

## Tools and scripts (not part of the runtime)

| Command | Purpose |
|---|---|
| `python -m tools.seed` | Fictional demonstration data |
| `python scripts/restore_demo.py` | Restore the bundled fictional demo database ([fixtures/demo](fixtures/demo/README.md)) |
| `python -m tools.pilot --online --as-of DATE --output DIR` | The real-source pilot: explicit captures of seven official pages |
| `python -m tools.curation FILE --online --as-of DATE --output DIR [--skip-source KEY] [--recapture]` | Grow the real dataset from a curated file of official sources: every name, link and status must appear verbatim in its captured page; capacities go through the extractor ([docs/RUNBOOK.md](docs/RUNBOOK.md#growing-the-real-dataset-dc2)) |
| `python -m tools.core_import SOURCE TARGET --report FILE` | Copy the Core tables of an existing database into a new Core database |
| `python -m tools.market_import FILE --source-id ID --locator URI --title TITLE --spec SETTINGS.json` | Register a market data file (CSV, XLSX or an LSEG JSON response) and read it into market observations ([docs/MARKET_DATA.md](docs/MARKET_DATA.md)) |
| `python -m tools.market_recipe RECIPE.json --root DELIVERY_DIR [--dry-run]` | Load a vendor delivery from a recipe in `tools/curated/` (files, columns, instruments, licence, what is left out and why) |
| `python -m tools.lseg_import EXPORT_DIR [--dry-run]` | Load an LSEG export folder (untouched API responses) into the market data area, kept internal |
| `python -m tools.compare_pilot --output DIR [--core-database DB]` | DC1 steps A6 and B4: export and replay the real-source pilot baseline of 2026-10-21 inside the Core and compare field by field; `--core-database` compares a Core database made elsewhere, such as the split tool's ([docs/A6-PILOT-COMPARISON.md](docs/A6-PILOT-COMPARISON.md)) |
| `python -m tools.legacy_bundle freeze\|verify\|restore PATH` | Demo and migration utility for the old 0.1.0-draft package. **Not** the evidence contract |
| `python scripts/export_v1_schema.py` | Regenerate the v1 schema (must stay byte for byte the same) |
| `python scripts/benchmark_native.py` | Native name-distance microbenchmark |

## Layout

```text
app/          Runtime: API, models, acquisition, extraction, quality, export contracts, market data, data screens
cpp/          C++17 Unicode edit-distance kernel for name matching
migrations/   The Core migration line
tools/        Seed, pilot, import, market file import, pilot comparison and legacy draft tools
scripts/      Demo restore, schema generation, example consumer, benchmark
fixtures/     Bundled fictional demo database
tests/        Core tests, including one test file per DC1-A step
docs/         Status, decision records, data dictionary, source taxonomy, review policy, quality codes, dates note,
              export contracts and record API, market data, runbook, data diagram, risks, final demo, release notes
```

No licence for redistribution of third-party source data is implied by this repository. Raw publisher snapshots are kept in local evidence storage, never in git.
