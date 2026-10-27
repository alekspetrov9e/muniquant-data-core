# Risks, known limitations and roadmap

State on 2026-10-26, after the DC1 sign-off and the market data area.

## Risks

| Risk | State | Mitigation / owner |
|---|---|---|
| Downstream scope exposure | Closed schemas refuse the ten prohibited fields and derived market fields; no trading or scoring code | Keep analytical logic outside the Core; PM |
| Source licensing | Public publisher pages kept for local research only; licensed market data (LSEG via a member's university licence) stored with `export_allowed: false` | Confirm onward use in writing before allowing export; never put licensed files or saved pages in git; PM |
| Plant identity ambiguity | 50 deliberately hard names keep ambiguity; no fuzzy auto-acceptance | Audited human decisions; SE1/PM |
| Conflicting or wrong facts | Exact value, date and unit checks; overlapping disagreeing facts and owner shares above 100 % warn | Keep each source vintage; curator decides; SE1 |
| Vendor data artefacts | Vendors can pad holidays or copy the last value forward | Market quality flags weekend dates, repeated prices, gaps and jumps; the file is never altered; curator records the decision |
| Saved bytes and database drift apart | Hashes checked on every export; missing or damaged bytes block | Back up database and snapshots together; restore drill; SE2 |
| Live pages change | Changed bytes create new versions; frozen replay uses saved bytes | Versioned literal recipes and failure logs; SE2 |
| Coverage | 72 real plants in 11 countries from 10 source families on 2026-10-26 (pilot plus the first DC2 batch) | More families for Gulf, Chinese and Russian plants; PM/SE1 |
| Shared deployment | Read protection and individual credentials exist but are optional; loopback by default | DC3: login, TLS/private ingress, credential lifecycle, rehearsed backups; SE2 |

## Known limitations

- Text PDFs only, no OCR; at most 200 pages and 10 MB per document.
- Unknown publication dates stay null and warn; dates are never inferred from capture time unless the curator says so.
- Market data: daily vendor files so far; no intraday LME data and no physical premium assessments from the first
  vendor; no currency conversion or derived values (downstream work).
- No scheduled acquisition; captures are explicit curator actions.

## Roadmap

1. **DC2 More data**: 50–100 plants with the hard cases (several owners, operator ≠ owner, ownership changes, capacity
   changes over vintages, closures and restarts, conflicting sources, aliases) from 5–10 official source families.
2. **Market data**: load the first LSEG files (LME cash and 3-month, SHFE contracts, CME premium futures), then further
   forward points and premiums as sources allow.
3. **Release v1.0.0** with the handover documents, final demonstration ([DEMO.md](DEMO.md)) and the Workspace CI pinned
   to the tag.
4. **DC3 Shared use**: login, encryption and tested backups for both parts.
