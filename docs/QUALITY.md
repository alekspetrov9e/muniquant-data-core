# Quality codes

`GET /api/quality` (plant data) and `GET /api/market/quality` (market data, codes in
[MARKET_DATA.md](MARKET_DATA.md#quality-checks)) return machine-readable findings: `code`, `severity`, `record_type`,
`record_id`, `message`, `remediation`. Status is FAIL with any BLOCK or ERROR, WARN with any WARN, else PASS. FAIL stops
the export. Database constraints refuse clear invariants outright (non-negative capacity, end not before start, known
unit per attribute, valid references, shares 0–100 %).

| Code | Severity | Meaning |
|---|---|---|
| `MISSING_SOURCE_METADATA` | BLOCK | Document's source lacks name, publisher or URL |
| `ACCESS_NOT_PERMITTED`, `ACCESS_REVOKED` | BLOCK | Source not permitted, or its latest access decision blocks it |
| `EXPORT_NOT_ALLOWED` | BLOCK | A fact, link or identity cites a source whose data must stay inside the Core |
| `PUBLICATION_AFTER_RETRIEVAL`, `INVALID_DOCUMENT_DATE` | BLOCK | Impossible or invalid document dates |
| `INVALID_CONTENT_HASH`, `MISSING_SNAPSHOT`, `CORRUPT_SNAPSHOT`, `MISSING_VERSION_METADATA` | BLOCK | Saved bytes or their registration are missing or damaged |
| `UNRESOLVED_ENTITY`, `MISSING_PROVENANCE`, `MISSING_EXACT_OBSERVATION`, `INVALID_ATTRIBUTE` | BLOCK | Fact without a valid plant, document and locator, exact value or valid dimension |
| `INVALID_RELATIONSHIP` | BLOCK | Link without company, plant, dates or evidence |
| `INCOMPLETE_RESOLVED_CANDIDATE`, `UNRESOLVED_CANDIDATE` | BLOCK | An extracted name still needs a human decision |
| `MISSING_ACCESS_AUDIT`, `MISSING_PUBLICATION_DATE`, `MISSING_ASSET_EVIDENCE` | WARN | Provenance incomplete but not wrong |
| `DUPLICATE_OBSERVATION`, `CONFLICTING_OBSERVATIONS`, `SUSPICIOUS_VALUE_CHANGE` | WARN | Repeated fact; overlapping facts that disagree (both kept); value more than 50 % from an earlier one |
| `IMPRECISE_RELATIONSHIP_LOCATOR`, `OWNERSHIP_TOTAL_EXCEEDS_100` | WARN | Legacy link locator; overlapping owner shares above 100 % |
| `DUPLICATE_CONTENT` | INFO | Identical bytes under different provenance |

Deliberately broken fixtures in `tests/` prove each blocking rule (plan week 8 gate).
