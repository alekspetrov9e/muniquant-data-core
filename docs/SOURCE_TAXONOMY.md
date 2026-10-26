# Source taxonomy

Plant facts cite primary sources, in this order of preference: **company publications** (operations pages, fact
sheets, annual reports), **government** (geological surveys, statistics offices, ministries), **regulators** (filings,
permits, emissions registers), **established industry bodies**, and **exchanges** (brand listings and notices). Formats:
HTML, text PDFs, structured CSV. No crawling, no bypassing access controls, a small number of well-understood source
families rather than many weak ones.

| `source_type` | Use |
|---|---|
| company | The producer's own publications: identity, capacity, ownership, operator, status |
| government | Official statistics and registers; identity, capacity, location |
| regulator | Filings and permits; ownership, status, capacity as reported to the regulator |
| industry | Industry associations' facility lists and statistics |
| exchange | Brand listings and notices (identity, producer); market data from exchanges |
| commercial | Licensed vendor data. Market data files (for example LSEG Datastream exports) are stored and checked in the market data area; vendor facility lists are hints for curators, never cited as plant facts |
| synthetic | Clearly labelled test and demonstration data; never counts toward coverage |

A source becomes usable only through an audited access decision: exact allowed hosts, the reviewed basis (terms,
licence), retention and redistribution limits, and whether its data may leave the Core (`export_allowed`). A public URL
alone is not an access approval; `review_required` and `restricted` sources cannot be captured or exported.

Each document records title, original URL or locator, source, publication date (null with a warning when unknown),
retrieval time, media type, SHA-256, storage reference and version; each retrieval attempt records its status, attempt
number and error without secrets.

Onboarding steps are in the [runbook](RUNBOOK.md#source-onboarding): classify the source, record its access basis,
approve exact hosts, capture, verify bytes and hash, configure and test the adapter and locator, review candidates,
record who maintains the source. Target for the pilot: 50–100 plants from 5–10 source families.
