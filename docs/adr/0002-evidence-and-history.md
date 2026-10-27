# ADR 0002: Immutable saved copies and append-only observations

Status: accepted (platform v0.1, 2026-10-10); carried into the Data Core in DC1.

**Context.** Reports change and sources disagree; a mutable capacity column cannot preserve provenance.

**Decision.** Keep SHA-256-addressed source bytes; version documents by source and original URL; store each sourced
value as a separate dated observation with its reported and normalized representation and its exact locator. Shared
bytes do not erase separate publisher identities.

**Alternatives considered.** URLs alone (revised evidence is lost); overwriting the latest value (history is lost); full
bitemporal SQL (deferred until concrete queries need it).

**Reasoning.** Traceability and reproducibility are the platform's purpose; storage is cheap next to lost evidence.

**Consequences.** The database and the snapshot directory are backed up together; exports verify evidence bytes;
conflicting vintages stay side by side for curators. Native dates and exact decimals live in `observation_detail`.
