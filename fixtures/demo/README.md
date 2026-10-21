# Included demonstration database

`database.sql` is a complete SQLite Data Core database at the current migration head. It holds six fictional facilities, one example company, six capacity records, sourced relationships, identity evidence and a deliberately pending name review. `snapshots/` holds the exact fictional source bytes. `manifest.json` verifies both.

It was made from the platform's bundled demo with `tools/core_import.py`, so every ID, value, date and hash is the same, and its v1 export is byte-identical to the platform demo's export (build hash `c6f6b3d6386d3dcb0e50a97b0b4422646937d8c6bf96e4a6a84a515a952b8a95`). No credentials, real operational database or third-party source copies are included. PostgreSQL deployments use migrations and `python -m tools.seed` rather than importing this SQLite-specific dump.

From the repository root, after installing the Data Core:

```sh
python scripts/restore_demo.py
export DATABASE_URL=sqlite:///data/demo.db
export SNAPSHOT_DIR=data/demo-snapshots
alembic check
export WRITE_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(24))')"
printf '%s\n' "$WRITE_TOKEN"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Enter your token in Workspace access. The example company has an explicit missing-identity-evidence warning. The restore command refuses existing paths, so it cannot replace your current database or evidence directory. Choose `--database` and `--snapshots` to install another copy.
