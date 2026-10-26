# Final demonstration

The workflow the project plan asks to show, on the Data Core alone, with a fresh database and real official sources.
Run from the repository root with the virtual environment active.

```sh
export DATABASE_URL=sqlite:///data/demo-run.db SNAPSHOT_DIR=data/demo-run-snapshots
alembic upgrade head
python -m tools.pilot --online --as-of "$(date +%F)" --output data/demo-run
export WRITE_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(24))')"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| Step | Where to show it |
|---|---|
| 1. Select a real source | Sources & evidence screen, or `GET /api/records/sources` and `GET /api/records/source_access?source_id=…`: publisher, type and the audited access decision with its exact hosts |
| 2. Retrieve a document | The pilot's captures, or **Retrieve URL** on the Sources & evidence screen (`POST /api/acquire`); `GET /api/records/retrieval_attempts` shows each attempt |
| 3. Preserve the evidence | `GET /api/documents/{id}/content` returns the exact bytes; the file in `SNAPSHOT_DIR` is named by its SHA-256 |
| 4. Register metadata and hash | `GET /api/records/documents/{id}`: URL, media type, publication and retrieval dates, version, `content_hash` |
| 5. Extract one attribute | `POST /api/documents/{id}/extract`, e.g. the Portland PDF page 1 nameplate capacity (`pdf-v1`, literal words before and after the number) |
| 6. Resolve the facility | The candidate resolves to "Portland Aluminium"; an unclear name goes to the review queue for a human decision |
| 7. Normalize value and unit | The fact keeps the reported value and unit and an exact value in t/year |
| 8. Run quality validation | `GET /api/quality`: PASS/WARN/FAIL with coded findings; a corrupted copy blocks export |
| 9. Export the package | `python -m app.evidence_cli export data/demo-run/package.json` (CommodityEvidencePackage 1.0.0) |
| 10. Trace back to the evidence | The record's `document_id`, `content_hash` and `evidence_reference` lead to the saved bytes and page; `scripts/consume_evidence.py` does it without the database |
| 11. Re-run the frozen acquisition | `python -m app.evidence_cli freeze data/demo-run/bundle.zip`, then `replay` offline |
| 12. Equivalent logical output | Replay reports `equivalent: true` and the same `build_hash` |

The pilot itself writes `pilot-evidence-package.json`, `pilot-frozen-evidence.zip` and `pilot-validation.json` with the
replay result. For market data, the same steps run with a vendor file: register it with `python -m tools.market_import`,
check `GET /api/market/quality`, export with `market-export`, then `market-freeze` and `market-replay`
([MARKET_DATA.md](MARKET_DATA.md)).

Saved pages and licensed files are private: the demo directories are under `data/`, which git ignores.
