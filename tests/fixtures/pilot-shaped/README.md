# Pilot-shaped legacy fixture

Synthetic, fictional data in the exact shape of the 10 October 2026 real-source pilot. It lets the tests prove that `tools/compare_pilot.py` (DC1 step A6) works while the real pilot files are unavailable. **It is not the real pilot and never replaces it**: step A6 stays blocked until the real database, snapshots, manifest and frozen bundle are supplied.

## Provenance

Generated on 2026-10-13 by `generate.py` running the pilot's own code: platform commit `c6d0411` (the 10 October release), database revision `fcf5b3d9e812`. Like `app.pilot`, it records audited permitted sources, captures documents through `acquire_remote` (served offline from fictional bytes), curates identities with identity evidence, extracts with the HTML, PDF and CSV adapters, records sourced ownership and operator relationships, then exports, freezes and replays. It adds what the real pilot lacked: an ambiguous name accepted through review, an unknown name rejected through review and a manually entered fact.

| File | Content |
|---|---|
| `database.sql` | SQLite dump of the pilot-era database (`real-pilot.db`), without Workspace rows |
| `real-pilot-snapshots/` | five fictional source documents, named by SHA-256 |
| `real-pilot-export/` | the pilot code's own `pilot-evidence-package.json`, `pilot-frozen-evidence.zip` and `pilot-validation.json` |
| `manifest.json` | SHA-256 of every file above |

Recorded by the pilot code: build hash `d0df265b56abbb4d3f0f0e49651147b71f3ed7e8f012bb0753184be3bfee8a6f`, quality WARN with 7 warnings and no BLOCK/ERROR, 6 records (one manual), 4 builds, 6 replayed candidates.

## Regenerate

Only needed if the fixture itself must change. From a checkout of the platform repository:

```sh
git worktree add --detach ../pilot-code c6d0411
cd ../pilot-code   # build or copy the native module here first
export PYTHONPATH="$PWD" OUT=/tmp/pilot-shaped
DATABASE_URL=sqlite:///$OUT/real-pilot.db alembic upgrade head
DATABASE_URL=sqlite:///$OUT/real-pilot.db SNAPSHOT_DIR=$OUT/real-pilot-snapshots \
  python /path/to/muniquant-data-core/tests/fixtures/pilot-shaped/generate.py --output $OUT/real-pilot-export
```

Then dump `real-pilot.db` with Python's `sqlite3` `iterdump()`, copy the snapshots and outputs here, and rewrite `manifest.json`. Captured timestamps and random document IDs change on every run, so the build hash changes with them.
