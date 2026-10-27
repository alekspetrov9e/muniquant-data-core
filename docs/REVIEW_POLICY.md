# Manual review policy

Pilot policy (sponsor-authorized 2026-10-10, unchanged by DC1). Target: triage within two business days; source-rights
and identity conflicts go to the project owner within one business day. These are targets for team operation, not
measured performance.

**Categories.** Alias or spelling difference; same name in different countries; same name at several sites; company
versus plant confusion; no matching identity yet; superseded identity; conflicting source or date; access or
provenance failure.

**Deciding.** Inspect the exact saved bytes and locator, country, plant type, company/plant distinction and dated
context. Name distance alone never justifies acceptance. Select a recorded candidate only after corroboration; if the
plant is missing, create it with source-based identity evidence, attach it to the review with a reason, then decide.
An extracted candidate's type and reported country must agree with the selected plant. Reject when the evidence cannot
identify a safe match; rejections stay in frozen recipes.

**What the system records.** Individual reviewer credential, reason, time, selected identity and an audit entry.
Decisions are final and cannot be overwritten. Accepting an extracted candidate creates its fact and an audited alias in
one transaction. Supersession keeps original IDs and cannot loop; history is never rewritten.

**Quality.** BLOCK and ERROR findings stop export: fix the source or settings, resolve or reject candidates, or restore
missing bytes. WARN needs a documented curator consideration; conflicting facts stay separate. INFO is informational.
Restricted or under-review access stops capture and export of the affected evidence. Licensing questions are never
settled by technical success.
