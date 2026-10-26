# Data dictionary

Terms and fields of the Data Core and its two exports. Tables: [DATA_DIAGRAM.md](DATA_DIAGRAM.md); every export field:
[CONTRACT.md](CONTRACT.md) and [MARKET_DATA.md](MARKET_DATA.md).

## Plants, companies and facts

| Field / term | Meaning and rules |
|---|---|
| entity, `external_entity_id` | A company or a plant (facility) with a stable Core ID. Not a security or instrument |
| `facility_type` | `smelter` (primary aluminium smelter), `refinery` (alumina refinery), `bauxite_mine` |
| `country`, `region` | ISO 3166-1 alpha-2 code from the controlled registry (28 countries; adding one is a migration), free-text region per country |
| `commodity` | Controlled product: aluminium, alumina, bauxite |
| alias | Another name for an entity, with actor and reason; equal names on different entities stay ambiguous, never merged silently |
| supersession | An entity replaced by another; IDs are kept, chains cannot loop |
| identity evidence | The document and locator that show a plant exists with this name, country and type |
| relationship, `role` | `OWNS` (with optional share, 0–100 %) or `OPERATES`; dated and sourced; owner need not be operator |
| observation, `attribute` | One dated fact: `capacity` (t/year, kt/year, Mt/year), `power` (MW), `ownership_percentage`, `status` (operating, closed, suspended, planned, construction) |
| `reported_value`, `reported_unit` | Exactly as the source writes it |
| `normalized_value`, `unit` | Exact decimal in t/year, MW or percentage; status has none |
| `valid_from`, `valid_to` | Dates the fact applies to; open end means no end stated; end never before start |
| `published_at` | When the source published the document; unknown is null and warns |
| `retrieved_at` | When the Core captured the bytes (UTC) |
| `content_hash` | SHA-256 of the exact captured bytes, checked before every export |
| `evidence_reference` | Page, row, text offset or section that supports the value |
| `resolution_status` | Exported facts are resolved: an exact, normalized or alias match, or an audited human decision |
| `quality_status`, `quality_codes` | PASS or WARN with the codes that apply ([QUALITY.md](QUALITY.md)) |
| build, `parser_version`, `pipeline_version` | One versioned reading of one document; replay re-reads the saved bytes and must give the same output |
| `package_version` | Contract version; breaking changes need a new version |

## Sources and access

| Field | Meaning |
|---|---|
| `source_type` | company, government, regulator, industry, exchange, commercial, synthetic ([SOURCE_TAXONOMY.md](SOURCE_TAXONOMY.md)) |
| access decision | Audited: status (permitted, review_required, restricted), exact allowed hosts, basis, retention, reviewer, time |
| `export_allowed` | Whether the source's data may leave the Core in an export; false keeps licensed data internal |
| `credential_ref` | Name of a server environment variable holding an API credential, never the secret |

## Market data

| Field | Meaning |
|---|---|
| instrument `code` | Stable series name such as `LME_AL_3M`, `SHFE_AL_ACTIVE`, `US_MIDWEST_PREMIUM` |
| `exchange`, `market` | Exchange (LME, SHFE, CME…; none for physical assessments); `forward`, `futures` or `physical` |
| `tenor` / `contract_code`, `contract_month` | A rolling point (cash, 3M, front, active…) or one dated contract |
| `grade`, `region` | As the source defines the instrument |
| `currency`, `unit` | ISO currency and price unit as quoted (USD/t, USc/lb, USD/lb, CNY/t, EUR/t, JPY/t) |
| `quantity_unit` | Unit of volume and open interest: lots, contracts or t |
| `price_type` | official, closing, settlement, daily, assessment, intraday |
| `bid` … `settlement`, `volume`, `open_interest` | Separate exact values; missing is null, never zero |
| `effective_date`, `effective_at` | Trading or assessment date; exact UTC instant when the source gives a time |
| `published_at`, `retrieved_at` | When the source published the value (if stated); when the vendor delivered it |
| `data_status` | reported, provisional, final, carried_forward, corrected |
| `source_series` | The vendor's code for each field |
| `withheld` | Observations left out of an export because their source's data is internal |

Never stored: forecasts, scores, signals, spreads, all-in prices or any of the fields the contracts prohibit.
