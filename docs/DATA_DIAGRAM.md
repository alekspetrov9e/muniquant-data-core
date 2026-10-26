# Data diagram

The 26 Core tables (`app/models.py`, created by the baseline migration) and how they relate. Three views sit on top:
`capacity_observation` and `status_observation` over observations, `facility_alias` over entity_alias. `audit` records
who changed what and when; it refers to records by ID only.

```mermaid
erDiagram
  ENTITIES ||--o| COMPANY : specializes
  ENTITIES ||--o| FACILITY : specializes
  ENTITIES ||--o{ ENTITY_ALIAS : names
  ENTITIES ||--o| ENTITY_SUPERSESSION : "replaced by"
  COUNTRY ||--o{ REGION : contains
  COUNTRY ||--o{ FACILITY : locates
  REGION ||--o{ FACILITY : locates
  FACILITY_TYPE ||--o{ FACILITY : classifies
  COMMODITY ||--o{ FACILITY : produces
  SOURCES ||--o{ SOURCE_ACCESS : governs
  SOURCES ||--o{ DOCUMENTS : publishes
  SOURCES ||--o{ SOURCE_DOCUMENT_RELATION : relates
  DOCUMENTS ||--o{ SOURCE_DOCUMENT_RELATION : relates
  DOCUMENTS ||--o| DOCUMENT_VERSION : versions
  SOURCE_SNAPSHOT ||--o{ DOCUMENT_VERSION : "exact bytes"
  RUNS ||--o{ RETRIEVAL_ATTEMPT : logs
  ENTITIES ||--o{ OBSERVATIONS : "dated facts"
  DOCUMENTS ||--o{ OBSERVATIONS : supports
  OBSERVATIONS ||--|| OBSERVATION_DETAIL : "exact value and dates"
  ENTITIES ||--o{ RELATIONSHIPS : "owns / operates"
  DOCUMENTS ||--o{ RELATIONSHIPS : supports
  RELATIONSHIPS ||--|| COMPANY_FACILITY_RELATIONSHIP : "exact share and dates"
  COMPANY ||--o{ COMPANY_FACILITY_RELATIONSHIP : owns_or_operates
  FACILITY ||--o{ COMPANY_FACILITY_RELATIONSHIP : has
  DOCUMENT_VERSION ||--o{ COMPANY_FACILITY_RELATIONSHIP : supports
  ENTITIES ||--o{ ENTITY_EVIDENCE : "traced to"
  DOCUMENT_VERSION ||--o{ ENTITY_EVIDENCE : supports
  DOCUMENTS ||--o{ EVIDENCE_BUILD : parses
  EVIDENCE_BUILD ||--o{ CANDIDATE : extracts
  ENTITIES ||--o{ CANDIDATE : matches
  OBSERVATIONS ||--o| CANDIDATE : "accepted as"
  REVIEWS ||--o{ CANDIDATE : decides
  ENTITIES ||--o{ REVIEWS : selects
```

## Around the Core

```mermaid
flowchart LR
  O[Official sources] -- explicit approved URLs --> C[Data Core]
  C --> E[/CommodityEvidencePackage 1.0.0/]
  X[Other programs, e.g. the Workspace] -- "record API reads;<br>candidate facts" --> C
```

Other programs keep Core IDs and read details through the API ([CONTRACT.md](CONTRACT.md)); the Core has no code that
refers to them. Licensed lead feeds and their saved responses are not Core data.
