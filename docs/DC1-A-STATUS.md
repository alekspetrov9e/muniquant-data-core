# DC1-A status: separate the Data Core

Status on 2026-10-21, in the team's report form: Done, Evidence, Blockers, Decisions, Next. Work is on branch `feature/dc1-a-separate-core`, pull request [#1](https://github.com/alekspetrov9e/muniquant-data-core/pull/1). `main` holds only the unchanged import of today's Core files from the platform (commit `1f02c0b`), so the pull request shows exactly what the separation changed.

## Done

| Step | State | Done when (specification) |
|---|---|---|
| A1 New home | **Done** | Own repository `muniquant-data-core` with its own tests and CI. CI's container job shows the image holds the runtime only, with no tools and no Workspace code, and runs migrations, health, seed, freeze, replay, export and recovery. |
| A2 Fresh database | **Done** | One migration creates exactly the 26 tables and 3 views: no market table, no joined branches. Setup and the drift check pass in CI on SQLite, PostgreSQL 16 and 17; `tests/test_schema.py` confirms the exact list of tables. |
| A3 One way only | **Done** | `tests/test_boundary.py` fails if any Core file uses a Workspace module or class, names a Workspace table, route or script, if runtime code names a Workspace feature, or if the runtime loads tools. |
| A4 Same export | **Done** | `app/evidence-v1.schema.json` is byte for byte the released file (SHA-256 `7808149a…4151f`); all ten forbidden-field checks stay (`tests/test_contract_schema.py`, `test_prohibited_contract_fields`). |
| A5 Core tests | **Done** | Evidence, hardening and platform tests moved; Core CI is green on all three databases. |
| A6 Same results | **Done** | Exported and replayed inside the Core, the real-source pilot baseline of 2026-10-21 gives byte-identical results: all 15 checks pass ([A6-PILOT-COMPARISON.md](A6-PILOT-COMPARISON.md)). The lost 10 October result is not compared. |
| A7 Clean repository | **Done** | The gitleaks secret scan passes in CI over all history and files. |
| A8 Dates note | Written, **awaiting review and agreement** | [DATES.md](DATES.md) |

## Evidence

- **CI** on the pull request: tests and migrations on SQLite, PostgreSQL 16 and PostgreSQL 17, container smoke and coordinated recovery, and the secret scan, all passing ([first green run](https://github.com/alekspetrov9e/muniquant-data-core/actions/runs/38443172666); the pull request shows the latest).
- **Schema**: the baseline migration matches today's Core tables (platform revision `d8317b920a11`) in columns, column order, keys, indexes, checks and views. The only differences: no `source_access.usage_scope`, and on PostgreSQL no unnamed duplicate copies of two observation checks.
- **Same results on available data**: the platform's bundled demo, copied with `tools/core_import.py`, exports a byte-identical package from the Core and from today's platform (build hash `c6f6b3d6…2b8a95`).
- **A6 on real data**: one fresh real-source pilot (15 plants, 5 companies, 3 publishers, 7 official pages, 2 capacity facts, 4 ownership and operator links), captured on 2026-10-21 by the platform at commit `26a0bcd`, is the approved baseline. Inside the Core it gives a byte-identical export (SHA-256 `abfc10ff…bd32`), the same build hash `87894401…695e`, the same frozen recipe and page copies, the same matching decisions and the same quality (WARN, 11 warnings). Its manifest is pinned in git ([a6/pilot-baseline-2026-10-21-manifest.json](a6/pilot-baseline-2026-10-21-manifest.json)); the Core-made frozen export is fingerprinted in [A6-PILOT-COMPARISON.md](A6-PILOT-COMPARISON.md).
- **The A6 tool also works on output of the 10 October pilot code**: `tests/fixtures/pilot-shaped` was produced by the 10 October pilot code (commit `c6d0411`, revision `fcf5b3d9e812`) from fictional sources: captures, curated identities, HTML/PDF/CSV extraction, an accepted and a rejected review, a manual fact, relationships, export, freeze and replay. `tools/compare_pilot.py` passes all 15 checks on it (byte-identical export and build hash, every record field by field, the same matching decisions, identical frozen recipe and snapshots, the same quality counts and summary numbers). It reports DIFFERENT when the Core's result changes or the pilot database cannot be loaded, and BLOCKED when an input is missing or fails its fingerprint. This proves the tool, not the pilot.
- **Secret scan**: default gitleaks rules with one narrow exception for access-decision UUIDs in run manifests. A planted token is still caught. `tests/test_repository_hygiene.py` adds: no secrets, databases, PDFs or local data, and every stored page is a declared, manifest-verified synthetic fixture.

## Blockers

- **A8** is done only when the dates note is reviewed and agreed.
- **The pilot baseline files exist on one machine only.** They hold copies of third-party pages, so they stay out of git (`data/pilot-baseline-2026-10-21/`). A private copy should go to the team before B4 needs them; the manifest in git proves any copy is the same.

## Decisions

Each follows the specification as closely as possible.

1. **Own repository**, as A1 asks, with the suggested name. It is private on GitHub until the team decides otherwise; the v1.0.0 tag comes with the DC1 handover.
2. **The platform is untouched in DC1-A.** Every feature keeps working there, including its own copy of the Core code, until DC1-B reconnects the Workspace.
3. **No lead code in the Core.** The specification says the Core has no code that refers to leads and that Permutable data stays in the Workspace. So the platform's `source_access.usage_scope` column and its lead-only checks are not in the Core; `quality.py` and `pipeline.py` are in their 10 October form. Licensed-credential support stays as generic source access, with no credential registered by default.
4. **One export.** CommodityEvidencePackage 1.0.0 is "the one and only export". `GET /api/export/draft` and the 0.1.0 draft package left the runtime; the draft tool is `tools/legacy_bundle.py`, marked as a demo and migration utility, as the specification describes `bundle.py`.
5. **The baseline migration copies today's databases** ("never redesign parts that already work"): same columns in the same order and the deployed constraint wording, so ready-made lists match. It leaves out only what DC1 removes: the other tables, the joined branches and, on PostgreSQL, the redundant duplicate checks.
6. **Existing databases enter through `tools/core_import.py`**, needed to export the pilot inside the Core (A6). It follows the split-tool rules: read-only source, new empty targets only, dry run, and a report comparing counts, IDs and fingerprints. It never drops data: a column the Core does not define is accepted only when every value is empty or equals the column's own default; anything else is refused and left to the DC1-B split tool.
7. **Moved tests changed only where they used parts the Core no longer has.** Two hardening tests used the platform's old migration chain; they now prove the same guarantees through the import tool. Two platform tests used the draft export; they now use the draft tool.
8. **A fresh real pilot replaces the lost 10 October files as the A6 and B4 baseline** (approved 2026-10-21). The 10 October files were not found in git, on GitHub, on Aleks's machine or in Youcef's home folder. The new run uses the platform's unchanged pilot code; it proves the Core gives the same results as today on real data, not against the 10 October build hash `415879f2…59e2`.
9. **Names that predate DC1 stay.** The Core's `/api/workspace` endpoint and the "Workspace access" labels in its screens return and protect Core data only. The schema's `$id` still points to the platform repository, because A4 requires the file byte for byte. Renaming either is left to an agreed later change.

## Next

- Hand a private copy of the pilot baseline and the Core's frozen pilot export to the team.
- Review and agree the dates note (A8), then sign off and merge pull request #1.
- DC1-B, after DC1-A has passed:
  - **B1**: the Workspace's database links to Core tables become reference fields: `lead.source_id`, `lead.primary_document_id`, `lead.observation_id`, `lead_revision.document_id`, `lead_headline.document_id`, `investigation_entry.document_id`, `asset_location.entity_id`/`document_id`, `asset_dependency.from_entity_id`/`to_entity_id`/`document_id`, and the old `market_observations.document_id`.
  - Replace a connection the specification does not list: on PostgreSQL the platform migration `d8317b920a11` puts a trigger (`search_entity_changed`) on the Core table `entities` that refreshes the Workspace's lead search when a plant is renamed.
  - **B2**: API client; proposals of candidate facts may need a Core endpoint, to be agreed.
  - **B3**: split tool building on `tools/core_import.py`, with Permutable material going to the Workspace side.
  - **B4** to **B6**.
