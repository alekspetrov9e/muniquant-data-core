# DC1-A status: separate the Data Core

Status on 2026-10-13. Branch `feature/dc1-a-separate-core`; `main` holds only the unchanged import of today's Core files from the platform (commit `1f02c0b`), so the branch diff shows exactly what the separation changed. The platform itself is untouched in DC1-A: it keeps running all features, including its own copy of the Core code, until DC1-B reconnects the Workspace.

## Steps

| Step | State | Evidence |
|---|---|---|
| A1 New home | Done; green CI pending the first run on GitHub | Own repository with its own tests and CI. The container job proves the image holds the runtime only, without tools or Workspace code, and runs migrations, health, seed, freeze, replay, export and recovery. |
| A2 Fresh database | Done | One migration (`34e9de7241cf`) creates exactly the 26 tables and 3 views; no market table, no joined branches, no lead-search triggers. `tests/test_schema.py` checks the exact table list, reference rows, drift check, round trip, and equality with today's Core tables on SQLite, PostgreSQL 16 and 17. |
| A3 One way only | Done | `tests/test_boundary.py` fails if any Core file imports or names a Workspace module, class, table, route or script, if runtime identifiers name a Workspace feature, or if the runtime loads tools. The test proves its scanner catches each kind of reference. |
| A4 Same export | Done | `app/evidence-v1.schema.json` is byte for byte the released file (SHA-256 `7808149a…4151f`), its generator reproduces it, the API serves the same bytes, and the ten forbidden fields are unchanged (`tests/test_contract_schema.py`, `test_prohibited_contract_fields`). |
| A5 Core tests | Done locally; CI pending | Evidence, hardening and platform tests moved. 93 tests pass on SQLite, PostgreSQL 16 and PostgreSQL 17. |
| A6 Same results | **Blocked: missing input** | The real pilot files are not available. The comparison with the old result is **not established**. The tool is ready and proven (below). |
| A7 Clean repository | Done locally; CI pending | gitleaks (default rules, one narrow exception for access-decision UUIDs) finds nothing in history or files and still catches a planted token. `tests/test_repository_hygiene.py`: no secrets, databases, PDFs or local data; every stored page is a declared, manifest-verified synthetic fixture. |
| A8 Dates note | Written; needs review and agreement | [DATES.md](DATES.md). |

## Evidence

- **Tests**: 93 passed on SQLite, PostgreSQL 16.15 and PostgreSQL 17.11 (local, 2026-10-13).
- **Schema**: the baseline matches today's Core tables (platform revision `d8317b920a11`) in columns, column order, keys, indexes, checks and views. Deliberate differences: no `source_access.usage_scope` (see decisions) and, on PostgreSQL, no duplicate unnamed copies of two observation checks.
- **Same results on available data**: the platform's bundled demo, copied with `tools/core_import.py`, exports a byte-identical package from the Core and from today's platform (build hash `c6f6b3d6…2b8a95`).
- **A6 tool proven on old-code output**: `tests/fixtures/pilot-shaped` was produced by the 10 October pilot code itself (commit `c6d0411`, revision `fcf5b3d9e812`), with captures, curated identities, HTML/PDF/CSV extraction, an accepted and a rejected review, a manual fact, relationships, export, freeze and replay. `tools/compare_pilot.py` reports PASS on all 15 checks: byte-identical export and build hash, same records field by field, same matching decisions, identical frozen recipe and snapshots, same quality counts and summary numbers. It reports DIFFERENT when the Core's result changes and BLOCKED when an input is missing or fails its fingerprint. This proves the tool, not the pilot.
- **Container and recovery**: rehearsed locally against PostgreSQL 16, including dump, restore and an identical build hash.

## Blockers

- **A6, and the handover's frozen pilot export, need the real pilot files**: `real-pilot.db`, its snapshot directory, the pilot output directory (`pilot-evidence-package.json`, `pilot-frozen-evidence.zip`, `pilot-validation.json`) and a manifest of their SHA-256 fingerprints. They are not on this machine; the platform's VALIDATION.md says the snapshots were kept in local deliverables. When available:

  ```sh
  python -m tools.compare_pilot --database PATH/real-pilot.db --snapshots PATH/real-pilot-snapshots \
    --export-dir PATH/real-pilot-export --manifest PATH/manifest.json --output data/a6-pilot-comparison
  ```

  It expects build hash `415879f2f8a9c5feae9f966947f9be1765b3dd1bb9d490141d7294296edf59e2` and 13 warnings with no BLOCK or ERROR. Run today without the files, it reports `BLOCKED` and lists each missing input.

## Decisions for review

1. **Lead material stays out of the Core.** The specification says the Core has no code referring to leads and Permutable material stays in the Workspace. So `source_access.usage_scope` and the lead-only guard (`LEAD_SOURCE_CITED`, lead checks on observations, relationships and identity evidence) are not in the Core; `quality.py` and `pipeline.py` are back to their 10 October form. Licensed-credential support stays, as generic source access with no credential registered by default. The import tool refuses databases that still mark hint-only sources.
2. **The draft export left the runtime.** `GET /api/export/draft` and the 0.1.0-draft package moved to `tools/legacy_bundle.py`, marked as a demo and migration utility. CommodityEvidencePackage 1.0.0 is the only runtime export.
3. **The baseline copies today's databases, not the model text**: same column order and the deployed wording of one percentage check, so `SELECT *` views match.
4. **Existing databases enter through `tools/core_import.py`.** It is read-only on the source, writes only to new databases, has a dry run and a per-table report. The two hardening tests that used the old migration chain now prove the same guarantees through it; the originals still run in the platform. DC1-B's split tool can build on it.
5. **Package name stays `app`**, so every Core file diffs cleanly against its platform original.
6. **The repository is private on GitHub** until the team decides otherwise; the v1.0.0 tag follows at the end of DC1.

## Found while separating

- A hidden connection the specification did not list: on PostgreSQL the platform's migration `d8317b920a11` puts a trigger (`search_entity_changed`) on the Core table `entities` that refreshes the Workspace's lead search text when a plant is renamed. It is not in the Core. DC1-B must replace it, for example by refreshing lead search from Core names read through the API.
- Workspace tables with database links to Core tables (to change into plain reference fields in B1): `lead.primary_document_id`, `lead.observation_id`, `lead.source_id`, `lead_revision.document_id`, `lead_headline.document_id`, `investigation_entry.document_id`, `asset_location.entity_id`/`document_id`, `asset_dependency.from_entity_id`/`to_entity_id`/`document_id`, and the old `market_observations.document_id`.

## Next

- Obtain the real pilot files, run A6, and keep the report and the Core-made frozen pilot export with its fingerprint.
- Review and agree the dates note and the decisions above.
- DC1-B: Workspace migrations (B1), API client (B2; proposals of candidate facts may need a Core endpoint, to be agreed), split tool building on `tools/core_import.py` with Permutable material going to the Workspace (B3), A6 again on the split result (B4), running together (B5), docs (B6).
