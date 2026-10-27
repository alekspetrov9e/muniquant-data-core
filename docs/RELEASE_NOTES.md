# Release notes

## Unreleased: market data area (2026-10-26)

- Three new tables, `market_instrument`, `market_build` and `market_observation` (migration `5b1e0c7d9a42`), and
  `source_access.export_allowed`. Instruments keep exchange, market, commodity, grade, region, tenor or contract,
  currency and unit; observations keep each price type and field separately as exact decimals, with trading date and
  instant, publication and retrieval timestamps, data status, vendor series and row locator ([MARKET_DATA.md](MARKET_DATA.md)).
- Vendor files (CSV, XLSX) are stored unchanged under their SHA-256 and read by versioned adapters
  (`market-adapters-1.0.0`) into replayable builds; `python -m tools.market_import` loads a file in one step.
- Market quality checks (`GET /api/market/quality`): damaged files and revoked access block; weekend dates, repeated
  prices, gaps, jumps and conflicting deliveries warn; nothing is altered.
- MarketDataPackage 1.0.0 (`GET /api/market/export`, closed schema), with frozen bundles and offline replay. Sources
  whose data must stay internal are withheld; a plant fact citing such a source blocks the plant export
  (`EXPORT_NOT_ALLOWED`). CommodityEvidencePackage 1.0.0 is unchanged.
- `tools/core_import.py` gives platform databases empty market tables; the DC1 boundary test allows the word "market"
  in Core identifiers but still refuses the Workspace's names. New dependency: openpyxl 3.1.5.
- DC2, first batch: `tools/curation.py` loads curated official sources (every name, alias, link and status verbatim in
  its captured page; capacities through the extractor; whole-word aliases; reuse of captured pages; `--skip-source`).
  [tools/curated/dc2-2026-10.json](../tools/curated/dc2-2026-10.json) adds 57 plants from USGS, the Indian Bureau of Mines,
  Natural Resources Canada, the Aluminium Association of Canada, SEC filings (Alcoa, Century), EGA and Vedanta. Captured
  on 2026-10-26 together with the pilot: 72 real plants in 11 countries from 10 source families, 98 facts, 102 owner and
  operator links, quality WARN with no blocking finding, frozen replay equivalent. EDGAR needs `CAPTURE_CONTACT`.
  Austria and Japan join the country registry (migration `8c3f2a6e1d07`); `CAPTURE_CONTACT` declares an operator
  contact in the capture client.
- Handover documents in this repository: decision records ([adr/](adr/)), data dictionary, source taxonomy, review
  policy, quality codes, risks and roadmap, final demonstration.

## 1.0.0rc1: DC1, the Data Core as its own project (signed off 2026-10-26)

Separated from the MuniQuant platform (release `26a0bcd`) with its own repository, database, straight migration line,
tests and CI; same export, byte for byte; same results on the real-source pilot (A6) and after the split (B4). Record
API with filters and single records for other programs. See [DC1-A-STATUS.md](DC1-A-STATUS.md).
