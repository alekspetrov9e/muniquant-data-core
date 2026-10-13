# Today's Core tables

`today-sqlite.json` and `today-postgresql.json` describe the 26 Core tables and 3 views exactly as the
platform's migrations create them on 2026-10-13: platform commit `1f02c0b`, revision `d8317b920a11`,
SQLite and PostgreSQL 16 (PostgreSQL 17 gives the identical description). They were produced with
`describe()` in `tests/test_schema.py` after `alembic upgrade head` in the platform repository.

`test_baseline_matches_todays_core_tables` compares the Data Core baseline with them. The only allowed
differences are listed in that test and in the baseline migration's docstring.
