# Data Core runbook

Deployment, source onboarding, export and recovery for the Data Core. It continues the platform's runbook (platform
release `26a0bcd`) for the parts that moved here in DC1; lead feeds and the other Workspace operations are in the
Workspace's runbook.

## Setup

The README has local and Docker instructions. Install the pinned dependencies, build the C++ extension and run
`alembic upgrade head` before starting the API; migrations never run hidden inside the API. PostgreSQL is the
deployment target; SQLite supports local use. Source builds need a C++17 compiler; the runtime image does not.

| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy URL; default local SQLite `data/muniquant.db`, deployed postgresql+psycopg |
| SNAPSHOT_DIR | Persistent content-addressed directory of saved page copies |
| WRITE_TOKEN / WRITE_ACTOR | Single curator credential and recorded actor; absent token disables writes |
| WRITE_IDENTITIES_JSON | JSON map of separate bearer credentials to identities: curators, and programs such as the Workspace (`"<token>": "workspace"`) |
| REQUIRE_READ_AUTH / READ_TOKEN | Protect API reads except health; optional read-only credential |
| POSTGRES_PASSWORD | Compose database secret |
| LICENSED_CREDENTIALS_JSON | Credential variable names and the only hosts allowed to receive them; none by default |

Use an ignored `.env` for secrets; Compose loads it, plain Python does not. The screens keep a credential only in memory
until reload. TLS/private ingress, rotation and identity-provider integration are deployment-owner controls.

## Source onboarding

1. Register publisher, source category, canonical URL and access/licensing notes. Prioritize official companies, then
   government, regulators and public bodies.
2. Record an audited access decision with exact lowercase permitted hostnames, the reviewed basis and retention or
   redistribution limits. Only permitted sources can be captured; a later restriction stops capture.
3. Retrieve an explicit HTTPS URL from Sources & evidence or POST /api/acquire. Public-address pinning and TLS checks,
   redirect revalidation, 20-second timeouts, four redirects, three attempts and a 10 MB limit apply. No crawler.
4. Inspect metadata and download the exact saved copy. Identical bytes at the same URL keep the document ID; changed
   bytes create a new version.
5. Create companies and plants; record identity evidence with document ID and locator; curate aliases and owner or
   operator links with dates and locators. Unknown effective dates are capture dates, never inferred history.
6. Extract with an adapter: HTML and PDF use the literal words before and after a number, the reported unit, the plant
   name and country and the dates; PDF may name a page. CSV uses the headers below. Text PDFs only, at most 200 pages.
7. Review unclear or unresolved names; accepting persists the sourced fact and alias, rejecting stays auditable.
8. Check quality. Fix BLOCK/ERROR; record how WARN findings were considered. Export v1 and trace a record to its
   document, hash and locator.

```csv
facility_name,country,reported_value,reported_unit,valid_from,valid_to,attribute,evidence_reference
Synthetic Example,NO,420,kt/year,2025-01-01,,capacity,table 1
Synthetic Example,NO,closed,status,2024-01-01,2024-12-31,status,section 2
```

The rows are fictional. Capacity units: t/year, kt/year, Mt/year; power: MW; ownership: percentage; status:
operating/closed/suspended/planned/construction with unit `status`. At most 1,000 rows per build; invalid rows leave no
partial facts; unresolved rows enter review. Candidate facts from other programs (POST /api/documents/{id}/extract)
follow exactly these steps.

## Logs, health and record reads

GET /api/health checks the database and the native module. JSON request logs carry method, path, status and duration,
without tokens or content. Runs and retrieval attempts record successful, duplicate and failed captures. GET
/api/quality returns findings and coverage. GET /api/records/{type} pages through every register, fact, review,
manifest, access and history record, with equality filters, and GET /api/records/{type}/{id} returns one record
([CONTRACT.md](CONTRACT.md#reading-core-records-through-the-api)). `alembic check` detects schema drift.

## Freeze and independently verify

```sh
python -m app.evidence_cli export data/evidence-v1.json
python -m app.evidence_cli freeze data/evidence-v1.zip
python -m app.evidence_cli replay data/evidence-v1.zip
python scripts/consume_evidence.py data/evidence-v1.json
```

Output paths must not exist. A frozen bundle holds the package, recipes, identities, review decisions and saved copies;
replay is offline, checks hashes and reruns the versioned parsers, and reports manually entered facts separately.
These are evidence artifacts, not operational backups. Source licensing still applies.

## Bring in an existing platform database

Existing databases are not upgraded in place. A database of the combined platform is split by the Workspace's split
tool (its runbook), which calls `tools/core_import.py` here for the Core side. To copy only the Core tables of a
database that holds nothing else of meaning:

```sh
python -m tools.core_import SOURCE.db NEW_CORE.db --report data/core-import-report.json \
  [--snapshots SOURCE_SNAPSHOTS --target-snapshots NEW_SNAPSHOTS] [--exclude ROWS.json] [--dry-run]
```

The source is only read; the target must be new; the report compares counts, IDs and fingerprints of every table.
`--exclude` leaves out exact rows by primary key, refusing rows that do not exist or that a copied row still needs.

## Pilot comparison (A6, B4)

`python -m tools.compare_pilot --output NEW_DIR` exports and replays the real-source pilot baseline of 2026-10-21 inside
the Core and compares it field by field ([A6-PILOT-COMPARISON.md](A6-PILOT-COMPARISON.md)); add
`--core-database CORE_DB` to compare a Core database made elsewhere, such as the split tool's (B4). The baseline files
hold third-party page copies and stay out of git.

## Coordinated backup and restore

Stop writes before capturing the database and the saved copies together. In Compose, stop `app` and leave `db`
running; dump with `docker compose exec -T db pg_dump -U muniquant -d muniquant -Fc` and archive the evidence volume,
preserving ownership. Store dump and archive with the migration revision, SHA-256 checksums and date, as private data.
Restore into a fresh database and volume, never over the working ones; then `alembic upgrade head`, `alembic check`, a
hash-validating export and a frozen replay before enabling writes. A missing or damaged saved copy must block export.
For SQLite, use Python's sqlite3 backup on the quiescent database and archive its saved copies. Programs that keep Core
IDs, such as the Workspace, should be backed up at the same time. Rehearse before shared use.

## Real-source pilot and limits

`python -m tools.pilot --online --as-of DATE --output DIR`, with a separate database and snapshot directory, captures
seven official Alcoa, Hydro and Rio Tinto pages, verifies 15 identities and extracts the Portland and Husnes
capacities. Page 2 of the Portland PDF carries a mismatched Huntly header; page 1 alone supports the extracted values
and ownership. Publication dates may be unknown and warn. Broader coverage (DC2) is curation work, not a release claim.
