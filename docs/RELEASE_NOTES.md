# Release notes

## Unreleased: scale and hardening fixes from the review (2026-11-04)

- Extraction: a number in the literal-context pattern is at most 40 digits and commas with up to 12 decimals, so a long
  run of digits no longer makes the scan quadratic (40,000 digits: 0.06 s instead of about 28 s). Every value that can
  be stored is found as before.
- Quality writes at most one `CONFLICTING_OBSERVATIONS` finding per fact instead of one per conflicting pair, and the
  export reads warning codes by record once. 1,000 open-ended facts on one plant: export 0.27 s instead of 136 s,
  1,799 findings instead of 500,300; the package is unchanged.
- The public-address check reads the IPv4 address inside a NAT64 address (`64:ff9b::/96`), which Python counts as
  global.
- Entity names and aliases longer than 256 characters after Unicode normalisation are refused, the limit of the C++
  name distance; resolve no longer fails when such a name is already stored.
- certifi 2026.7.22 → 2026.10.23, opentelemetry-api 1.45.0 → 1.45.2, setuptools 84.0.0 → 84.2.1 (published advisories).
- The A6 pilot comparison passes unchanged (all 15 checks, WARN 11, the same build hash and a byte-identical export).

## Unreleased: input, token and parallel-write fixes (2026-11-03)

- Plant values are plain decimals only, as market values already were: digits with an optional decimal point and
  `,` thousands grouping. A sign, an exponent, `.5` or `1_000` are refused; "-0" and "1e-999999999" stored a value the
  export could not reproduce, or none on PostgreSQL. An ownership share with a sign ("-0") is refused too.
- Tokens must come as `Authorization: Bearer <token>` (the word "Bearer" in any case). An empty key in
  `WRITE_IDENTITIES_JSON` never matches, and a non-ASCII header is a refusal (401), not a server error.
- Parallel writes: adding an alias locks its plant, so no parallel alias drops out of the plant's list, and adding a
  lost alias again lists it; supersessions run one at a time, so two cannot close a loop. New quality code
  `SUPERSESSION_CYCLE` (BLOCK) finds a loop already in a database.
- Bad requests get 422 instead of a server error: `offset` above 1,000,000,000, integer filters over 18 digits, NUL
  characters (bodies and record filters), CSV fields over 128 KiB (plant and market tables), and any value PostgreSQL
  cannot store or compare. A plant CSV row whose country is not a two-letter code is refused as a failed run; SQLite
  used to store it silently.
- pypdf 6.20.0 → 6.21.4, which fixes 16 published advisories. The A6 pilot comparison passes unchanged (all 15 checks,
  the same build hash and a byte-identical export).

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
- LME from Datastream (2026-10-27): tab-separated vendor copies, `#N` column positions, `leave_out` and `status_by_date`
  in the import settings, and `tools/market_recipe.py` with two recipes. Loaded locally: closing prices for cash, 3M,
  15M and 27M, official bid (cash) and bid and ask (3M), 2008-2026, and the December contracts Dec 2026 - Dec 2036
  (settlement, volume, open interest): 44,240 observations, kept internal; all 340 market builds replay.
- First LSEG load (2026-10-27): `market-lseg-json-v1` reads untouched LSEG historical-pricing responses; `tools/lseg_import.py`
  loads an export folder. Loaded locally: 325 series (SHFE and COMEX aluminium contracts, SHFE continuations, CME premium
  futures, SHFE alumina, SMM alumina FOB), 168,924 observations, all kept internal; every build replays. LME cash and
  3-month wait for the Datastream series definition. The copy-forward check now needs every value, volume and open
  interest included, to repeat; a value beyond 24 digits is refused instead of failing the decimal check.
- LME cash settlement price (2026-11-04): Datastream has the cash official seller after all, LAHCASH(OO), which is the
  LME cash settlement price. [tools/curated/lseg-lme-cash-official-seller-2026-11-04.json](../tools/curated/lseg-lme-cash-official-seller-2026-11-04.json)
  loads it as the cash official ask, 1988-2026: 9,929 observations, kept internal. Three trading days on which
  Datastream repeated the previous official prices are declared `carried_forward`. Market quality no longer counts a
  bid from one delivery and the ask from another as a duplicate.
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
