# Which dates the Data Core stores, and where they stop

DC1 step A8. This note describes what the Core stores **today** (baseline `34e9de7241cf`), field by field, and the limits of those dates. It does not claim that the Core can rebuild what was known on any past day; it cannot. Dates the Core does not have yet are listed at the end and stay open for a later step.

Two kinds of value are stored:

- **Calendar dates** (`YYYY-MM-DD`, no time zone): what a source says or what a curator configured.
- **Recording timestamps** (ISO 8601 in UTC, e.g. `2026-10-10T07:42:43.123456+00:00`): written by the application server's clock (`app.models.now`), not by the database clock. Each is written once, when its row or decision is recorded, and never moved later.

## Per kind of record

| Record | Stored dates | Meaning | Limits |
|---|---|---|---|
| Fact: capacity, power, ownership share, status (`observations`, `observation_detail`) | `valid_from`, optional `valid_to` (also as native dates in `observation_detail`) | The period the fact is asserted for, inclusive; an open end means "no end stated". From the source row (CSV), or set by the curator in the extraction recipe or manual form. | For undated sources it is the **capture date**, not the date the plant changed (the pilot's Portland capacity uses 2026-10-10). Nothing in the record says which case applies. Overlapping facts with different values are kept and flagged `CONFLICTING_OBSERVATIONS`; no winner is chosen. |
| | `recorded_at` | When the fact row was written: the extraction run for matched names, the review decision for names that needed review, the API call for manual facts. | The Core offers no way to edit a fact. A correction is a new fact; nothing links it to the fact it corrects and the older one stays valid. |
| Owner / operator link (`relationships`, `company_facility_relationship`) | `valid_from`, optional `valid_to` | Period the ownership or operation is asserted for. | **No recording timestamp on the row.** The audit entry written with it (`relate`, or `curated_relationship` in the pilot) carries `created_at`. |
| Saved page (`documents`) | `published_at` (optional) | Publication date as entered by the curator at capture. Never read from the page itself. Missing gives the `MISSING_PUBLICATION_DATE` warning; a date after retrieval blocks export. | Often unknown (8 of 10 pilot documents). It is the publisher's stated date, not when the content first became public. |
| | `retrieved_at` | When the Core stored these exact bytes. | Re-capturing identical bytes changes nothing on the document; only the run log shows later confirmations. The HTTP `Date`/`Last-Modified` headers are not kept. |
| | `version` | Order of distinct byte versions for one source and URL. | A sequence number, not a time. |
| Exact copy (`source_snapshot`, `document_version`) | none | Linked to the document above. | |
| Download log (`runs`, `retrieval_attempt`) | `started_at`; `recorded_at` per attempt | When a capture or extraction run started; when each HTTP attempt was logged. | No end time for a run. |
| Plant or company (`entities`, `company`, `facility`, `region`) | none | | **Mutable without history**: name, country, type, region and the alias list can change with no record of the earlier value. API creations leave an audit entry; the pilot's curated identities do not. |
| Other name, merged identity (`entity_alias`, `entity_supersession`) | `created_at` | When the alias or the "replaced by" link was recorded. | Aliases are only ever added. |
| Identity proof (`entity_evidence`) | `created_at` | When the curator linked the identity to a document and locator. | |
| Source and permission (`sources`, `source_access`) | `source_access.decided_at` | When each access decision was taken; decisions are only added, so the decision in force at any time can be found. | `sources.access_status` is overwritten by each decision. |
| Matching (`evidence_build`, `candidate`, `reviews`) | `evidence_build.created_at`; `reviews.decided_at` | When a recipe ran over a saved page; when a person decided an uncertain name. | Candidates carry no time. A pending review has no "opened at" time. |
| Change history (`audit`) | `created_at` | Who did what, and when: every API write, plus extraction and review steps. | Tools write only some entries: the pilot records its relationships but not its identities; the seed records none. |

The export (`CommodityEvidencePackage 1.0.0`) carries `valid_from`, `valid_to`, `published_at` and `retrieved_at` for every fact. It carries no recording or decision times.

## What this supports today

- Which facts were asserted for a given date, from any source, with their exact evidence.
- Which byte versions of a page were captured, and when.
- Which access decision applied at a given time.
- Roughly which facts existed at a past moment, by filtering on `recorded_at`, **but not** the plant names, aliases, types or regions as they were then, and not ownership links by recording time.

## Clocks we do not have yet (open for a later step)

- **First public**: when information first became public, as opposed to the publisher's stated date.
- **Ready for processing**: when captured content became available to the pipeline, separate from the capture itself.
- **Reviewed**: when a fact, not just an uncertain name, was checked by a person.
- **Corrected**: when a fact was replaced or withdrawn, with a link from the old fact to the new one.
- A recording time on ownership and operator links, and a history of changes to plant and company records.
