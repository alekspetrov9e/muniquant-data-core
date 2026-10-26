# CommodityEvidencePackage 1.0.0

The public boundary is JSON (`GET /api/export`); the machine-readable schema is `GET /api/export/schema` and app/evidence-v1.schema.json. Schema objects are closed: unknown properties are rejected. Breaking changes require a new package version and migration/replay compatibility notes. The application release number is distinct from this contract number.

A package contains `records`, `entities`, `identity_evidence`, `relationships`, `sources`, `documents`, `build_manifest`, package/pipeline versions and `build_hash`. A consumer needs no internal database access. Run `python scripts/consume_evidence.py path/to/package.json` for an independent schema-validating example.

Each record has stable external entity ID/type, canonical name/aliases, facility type, country/region/commodity, industrial attribute, exact reported value/unit, normalized value/unit, valid interval, publication/retrieval dates, source/document IDs, content hash and locator, publisher/URL, resolution and quality status/codes, synthetic marker, parser/pipeline/package versions. These IDs are upstream identities, not authoritative private MEI identities.

Normalized numbers and relationship percentages are decimal strings to preserve exact precision. Capacity normalizes to t/year, power to MW, shares to percentage; status remains a reported categorical value with null numeric normalization. Native intervals use inclusive ISO dates; absent end means open-ended source assertion. Observation date is distinct from publication/retrieval; unknown publication is null with WARN. No date is inferred from an article unless the curator explicitly configures its justified meaning.

Entities include companies even when no capacity fact exists. Identity evidence associates registration with a document and locator. Relationships distinguish OWNS and OPERATES and carry exact share/date/source information. Null share means unspecified, not zero. Sources include publisher and access/retention notes. Documents include original URL, media type, version, hash, storage reference and dates. Snapshot bytes are supplied separately in frozen evidence bundles; the package alone is not a copyright license.

Build manifests identify input document/hash, parser/pipeline versions and logical output hash. Frozen replay re-extracts parser-produced records and verifies values/dates/identity decisions; it explicitly counts manually entered records whose normalization alone is verified. Build/package hash uses canonical ordering and logical content, while recorded provenance timestamps remain included. Online reretrieval is allowed to produce a different document version; use frozen bytes for equivalence.

BLOCK/ERROR prohibit export. WARN facts remain included and visibly marked; no automatic conflict winner is inferred. The closed schema and recursive validator reject impact_score, surprise_score, market_state, analogue_score, supply_pressure, price_prediction, procurement_signal, trading_signal, factor_weight and alpha anywhere. No private analytical outputs, recommendations, securities or trading records are exported.

## Reading Core records through the API

The export is the contract for downstream consumers. Programs that work alongside the Core and keep references to its
records, such as the MuniQuant Workspace, use the record API instead and never the database. Core IDs are stable; a
document ID names one exact document version.

- `GET /api/records/{type}?offset=0&limit=1000` lists records in primary-key order with a `total`. Types: `entities`,
  `supersessions` (replaced entity → replacing entity), `sources`, `source_access`, `documents`, `observations`,
  `relationships`, `reviews`, `candidates`, `builds`, `runs`, `retrieval_attempts`, `audit`.
- Any other query parameter is an equality filter on a text or integer column, for example
  `/api/records/observations?document_id=...` or `/api/records/audit?record_id=...`. Unknown columns, JSON columns and
  malformed numbers are refused with 422, never ignored.
- `GET /api/records/{type}/{id}` returns one record, or 404.
- `GET /api/documents/{id}/content` returns the exact saved bytes after checking their SHA-256.

New facts from such programs are candidate facts, sent like any curator's: `POST /api/documents/{id}/extract` with
the extraction settings. The Core runs its own source check, matching (unclear names go to human review) and quality
checks; the response lists each candidate's status and, once accepted, its observation ID. Reads follow
`REQUIRE_READ_AUTH`; writes need a credential, best a separate entry in `WRITE_IDENTITIES_JSON` so the history names
the program.
