# ADR 0004: A market data area inside the Data Core

Status: accepted 2026-10-26 (approved by the spec owner).

**Context.** The project's market data scope asks for an aluminium market-data foundation: LME cash, 3-month and
further forward points, SHFE contracts with volume and open interest, regional physical premiums and secondary
instruments, each kept as a separate, source-traceable observation with its own identity, price type, currency, unit,
timestamps and data status, and no derived signals. The first data arrives as licensed vendor files (LSEG Datastream
through a member's university licence).

**Decision.** Add three Core tables (`market_instrument`, `market_build`, `market_observation`) that reuse the Core's
evidence machinery: each vendor file is an ordinary document version under its SHA-256, a versioned adapter reads it
into a replayable build, and each observation cites the file, row and vendor series. Values are exact decimals in the
source's own currency and unit; one row per instrument, price type and date holds the separate bid/ask/open/high/low/
close/settlement/volume/open-interest fields. A new `source_access.export_allowed` decides whether a source's data may
leave the Core; market data has its own export, MarketDataPackage 1.0.0. CommodityEvidencePackage 1.0.0 is unchanged.

**Alternatives considered.** The Workspace's old `market_observations` table (no provenance, belongs to the research
side); a third project (duplicates sources, snapshots, runs and replay); one long row per value (harder to read and
check high/low or bid/ask); one combined "aluminium price" field (loses the market layers the scope requires).

**Reasoning.** The scope's demands (source traceability, historical identifiability, separate layers) are what the Core
already guarantees for plant facts; one evidence store, one backup and one quality framework.

**Consequences.** The DC1 boundary test now allows the word "market" in Core identifiers while still refusing the
Workspace's market table, class, route and script names. Platform databases imported by `tools/core_import.py` get
empty market tables. Licensed data stays internal (`export_allowed: false`) until its onward use is confirmed; a plant
fact may never cite such a source. Currency conversion and derived values remain downstream work.
