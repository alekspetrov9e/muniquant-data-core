# ADR 0003: The Data Core as its own project

Status: accepted; DC1 signed off by the spec owner on 2026-10-26.

**Context.** One codebase, database and migration history held both the plant-evidence platform and the research
features (leads, practice trading, investigations, map), so every change was risky.

**Decision.** The Data Core has its own repository, database, straight migration line and tests. Other programs (the
Workspace) use only its API, keep Core IDs instead of copies, and send candidate facts that the Core checks like any
curator's. The Core has no code that refers to them (tests/test_boundary.py).

**Alternatives considered.** Separate packages in one repository with one database (the coupling stays); a shared
database with schemas per part (still one migration history and hidden joins).

**Reasoning.** A one-way dependency keeps the evidence rules in one place and lets the research side experiment freely.

**Consequences.** Existing databases are split by tools, not upgraded in place; the pilot comparison (A6/B4) proved
identical results. Programs that keep Core IDs must be backed up together with the Core.
