# Market data

The Data Core keeps a market data area next to the plant data (added after DC1, approved 2026-10-26). Its job is to
preserve aluminium market observations correctly and traceably, so that later research can use them: **an aluminium
market-data system, not one aluminium price**. It records and checks; it does not interpret, model or trade.

- Every instrument is its own series: LME cash, LME 3-month and each further forward point; SHFE front month, most
  active contract and next contracts; each regional physical premium; secondary instruments such as CME aluminium and
  alumina. Nothing is collapsed into a single "aluminium price".
- Values stay in the source's own currency and unit (SHFE in CNY/t, the US Midwest premium as quoted). Currency
  conversion, if ever needed, is a separate derived step and is not implemented.
- Nothing is derived or combined here: no cash–3M spread, LME–SHFE difference, premium difference, curve or tightness
  score, expected move or all-in price (benchmark + premium). The export refuses such fields.
- Every value cites the registered document version it was read from (the vendor file, stored unchanged under its
  SHA-256), the row and column, and the vendor's series code.

## What is stored

Three tables ([DATA_DIAGRAM.md](DATA_DIAGRAM.md)): `market_instrument` (what a series is), `market_build` (one reading
of one file, replayable) and `market_observation` (the values). The fields a market observation should carry, and
where they live:

| Field | Where |
|---|---|
| exchange, market, instrument, commodity, grade, region | instrument: `exchange` (LME, SHFE, CME…; none for physical assessments), `market` (`forward`, `futures`, `physical`), `code` and `name`, `commodity`, `grade`, `region` |
| contract code, contract month / prompt date | instrument `contract_code`/`contract_month` for one dated contract, or `tenor` for a rolling point (`cash`, `3M`, `15M`, `front`, `active`, `second`…); each observation also keeps the actual `contract_code`, `contract_month` and `prompt_date` when the file gives them |
| price type | observation `price_type`: `official`, `closing`, `settlement`, `daily` (one trading day's summary), `assessment` (price reporting agency), `intraday` |
| bid, ask, open, high, low, close, settlement | observation, exact decimals; absent is null, never zero |
| currency, unit | instrument `currency` (ISO 4217) and price `unit`: USD/t, USc/lb, USD/lb, CNY/t, EUR/t, JPY/t, kept consistent |
| volume, open interest | observation, with the instrument's `quantity_unit` (lots, contracts or t) |
| effective timestamp | observation `effective_date` (trading or assessment date) and `effective_at` (exact UTC instant, when the source gives a time) |
| publication timestamp | observation `published_at`, when the source states it; otherwise null and reported |
| retrieval timestamp | observation `retrieved_at` (when the vendor delivered the data) and the document's own registration time |
| source | document → source (publisher, access decision), plus the vendor's series code per field in `source_series` |
| data status | observation `data_status`: `reported` (as delivered), `provisional`, `final`, `carried_forward`, `corrected` |

Two deliveries may give different values for the same day; both are kept and the quality report names the conflict.

### Instrument codes

Codes are stable upper-case names. Use the ones below; add others in the same style.

| Code | Instrument |
|---|---|
| `LME_AL_CASH`, `LME_AL_3M`, `LME_AL_15M`, `LME_AL_27M` | LME aluminium forward points (`forward`, `tenor` cash/3M/15M/27M) |
| `SHFE_AL_FRONT`, `SHFE_AL_ACTIVE`, `SHFE_AL_SECOND` | SHFE aluminium continuation series (`futures`, `tenor` front/active/second); each observation names the actual contract |
| `SHFE_AL_2501` | One SHFE aluminium contract (`contract_code` AL2501, `contract_month` 2025-01) |
| `EUROPE_DUTY_PAID_PREMIUM`, `EUROPE_DUTY_UNPAID_PREMIUM`, `US_MIDWEST_PREMIUM`, `JAPAN_PREMIUM` | Physical premium assessments (`physical`, by `region`) |
| `CME_AUP_FRONT`, `CME_EDP_FRONT` | CME futures settled on premium assessments. They are futures, not the physical assessment, and stay separate instruments |
| `CME_ALI_FRONT`, `SHFE_AO_ACTIVE` | Secondary: CME aluminium, SHFE alumina (`commodity` alumina) |

Register each instrument with the unit and currency from the vendor's own series description, and say in
`description` which description that was.

## Bringing in a vendor file

1. **Register the source once**, with its licence in an audited access decision. A licensed source whose data may not
   leave the Core gets `export_allowed: false`; the data is stored and checked but every export leaves it out and
   lists it under `withheld`. A later decision that omits `export_allowed` keeps the previous value.

   ```sh
   curl -X POST $CORE/api/sources -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
     "name": "LSEG Datastream exports", "publisher": "LSEG", "source_type": "commercial",
     "url": "https://www.lseg.com/en/data-analytics", "access_status": "review_required",
     "notes": "University licence held by a club member; exports handed over as files"}'
   curl -X POST $CORE/api/sources/$SOURCE_ID/access -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
     "status": "permitted", "allowed_hosts": [], "export_allowed": false,
     "basis": "University licence; the holder confirmed club use and storage on 2026-10-26",
     "retention": "Private storage only; never in git; no export until onward use is confirmed"}'
   ```

2. **Describe the file** in import settings (JSON, see below) and the instruments it fills (JSON list).
3. **Load it** with the original file, unchanged:

   ```sh
   python -m tools.market_import ~/private/lseg-lme-2026-10-27.csv --source-id $SOURCE_ID \
     --locator "datastream:LAHCASH,LAH3MTH" --title "LSEG Datastream LME aluminium cash and 3M, daily" \
     --published-at 2026-10-27 --spec lme-settings.json --instruments lme-instruments.json
   ```

   The tool stores the file under its SHA-256 (the same bytes again are a duplicate, changed bytes a new version),
   reads it into a build and prints the observation count and the market data quality. CSV is also accepted by
   `POST /api/documents` followed by `POST /api/documents/{id}/market-import`.
4. **Review the quality report** (`GET /api/market/quality`): BLOCK stops export; record how WARN findings were
   considered.

Licensed files are private data: keep them and the snapshot directory out of git and shared folders.

### Import settings

| Setting | Meaning |
|---|---|
| `adapter` | `market-csv-v1` (UTF-8 CSV) or `market-xlsx-v1` (Excel workbook, cached cell values; give `sheet`) |
| `header_row` | 1-based row holding the column names; rows above it (vendor descriptions) are kept in the file, not read |
| `date_column`, `date_format` | The date column and its exact strptime pattern, e.g. `%d/%m/%Y`. Excel dates read as `%Y-%m-%d`. No guessing: a row that does not match stops the import |
| `time_column`, `time_format`, `timezone` | Optional intraday time and the IANA timezone of date and time; stored as UTC |
| `columns` | One entry per value column: `column` (header), `instrument` (code), `price_type`, `field` (bid … settlement, volume, open_interest), `source_series` (vendor code, default the header) |
| `instrument_column`, `instrument_map` | Long tables: a column naming the contract or series, mapped to instrument codes; unmapped values stop the import |
| `contract_code_column`, `contract_month_column`, `prompt_date_column` | Optional per-row contract details |
| `missing_values` | Cells meaning "no value" (default empty, NA, N/A, #N/A, NaN, NULL, -) |
| `retrieved_at` | When the vendor delivered the data, with timezone (the export time) |
| `published_at` | When the vendor says the values were published, if it does |
| `data_status` | Status of the whole file, default `reported` |

Numbers are exact decimals with `.` for decimals and optional `,` thousands grouping; exponents, more than six
decimals and negative volumes are refused. A file with any invalid row is refused whole and the failure is logged as
a run. Example for a two-column daily export whose third row holds the codes:

```json
{"adapter": "market-csv-v1", "header_row": 3, "date_column": "Date", "date_format": "%d/%m/%Y",
 "retrieved_at": "2026-10-27T10:15:00+01:00",
 "columns": [
   {"column": "LAHCASH", "instrument": "LME_AL_CASH", "price_type": "official", "field": "settlement"},
   {"column": "LAH3MTH", "instrument": "LME_AL_3M", "price_type": "official", "field": "settlement"}]}
```

Which LME price a vendor series carries (official, closing or another) must come from the vendor's series description;
record it in `price_type` and the instrument description, not by assumption.

## Quality checks

`GET /api/market/quality` returns PASS/WARN/FAIL with machine-readable findings. Series checks are counted per series
(`CODE/price_type[/contract]`) with up to five example dates; they flag, they never change data.

| Code | Severity | Meaning |
|---|---|---|
| `MISSING_SNAPSHOT`, `CORRUPT_SNAPSHOT`, `INVALID_CONTENT_HASH` | BLOCK | The stored file is missing or no longer matches its SHA-256 |
| `ACCESS_REVOKED` | BLOCK | The source's latest access decision does not permit it |
| `INVALID_UNIT`, `MISSING_QUANTITY_UNIT`, `PROVENANCE_MISMATCH` | BLOCK | Inconsistent instrument unit, volume without a unit, observation and build citing different files |
| `MISSING_ACCESS_AUDIT` | WARN | No audited access decision; the data is not exported |
| `WEEKEND_DATE` | WARN | Values dated on a Saturday or Sunday (padded days) |
| `POSSIBLE_CARRY_FORWARD` | WARN | Prices identical to the previous date in the same file (a vendor may copy the last value forward) |
| `SERIES_GAP` | WARN | More than seven weekdays without a value in one file |
| `SUSPICIOUS_VALUE_CHANGE` | WARN | An exchange price moved more than 20% from the previous date in one file |
| `CONFLICTING_OBSERVATIONS` | WARN | Two files give different values for the same date; both are kept |
| `DUPLICATE_OBSERVATION`, `DECLARED_CARRIED_FORWARD`, `DECLARED_PROVISIONAL`, `PUBLICATION_TIME_UNKNOWN`, `EXPORT_WITHHELD` | INFO | Recorded for the reader; no action unless the source says otherwise |

Database checks refuse what can never be right: high below low, bid above ask, negative volume or open interest, an
observation without any value, unknown price types, statuses and units.

## Export: MarketDataPackage 1.0.0

`GET /api/market/export` (optional `instrument=CODE`, repeatable, and `from`/`to` dates) returns a self-contained JSON
package; its closed schema is `GET /api/market/export/schema` ([app/market-v1.schema.json](../app/market-v1.schema.json)).
Each observation carries its instrument identity, price type, values, currency and unit, dates and timestamps, data
status, source, vendor series, document ID and SHA-256, row locator, build ID and quality codes. The package also lists
the instruments, sources, documents, build manifest and the observations `withheld` per source, and a `build_hash`
over its logical content. BLOCK findings stop the export; every build is replayed first.

The plant export, CommodityEvidencePackage 1.0.0, is unchanged and contains no market data. A plant fact may never cite
a source whose data is kept internal (`EXPORT_NOT_ALLOWED`, BLOCK).

```sh
python -m app.evidence_cli market-export data/market-v1.json
python -m app.evidence_cli market-freeze data/market-v1.zip
python -m app.evidence_cli market-replay data/market-v1.zip
```

A frozen bundle holds the package, the build recipes and the exact files; replay re-reads every file without a
database and proves each exported observation equals its source row. `POST /api/market/builds/{id}/replay` does the
same for one stored build.

## Known limits

- The first vendor, LSEG Datastream through a member's university licence, gives daily values only: no intraday LME
  data and no physical premium assessments (premiums come as CME futures, stored as futures).
- Publication times are rarely in vendor exports and stay null unless stated.
- No currency conversion, no derived values, no curve construction: downstream work.
- Data from LSEG stays internal (`export_allowed: false`) until its onward use is confirmed.
