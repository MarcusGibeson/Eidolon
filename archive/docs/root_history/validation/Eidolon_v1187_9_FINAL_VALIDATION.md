# Eidolon v1187.9 Final Validation

## Scope

v1187.9 consolidates the complete bounded persistent campaign work-execution arc introduced by v1187.0-v1187.8. The checkpoint is source-discovered and read-only over production source and caller-supplied runtime roots. Execution, ledger updates, and durable continuation writes occur only inside isolated synthetic temporary fixtures that are removed before return.

## Implemented checkpoint coverage

- Exact lease-backed resumed-session, restart-reconciliation, selection, target, and target-digest binding.
- Separate operator approve, reject, and defer execution review.
- Narrowly allowlisted `python_compile` and `content_digest_match` execution.
- Passed and failed execution receipts without raw output exposure.
- Separate operator accept, reject, and defer result review.
- Exact terminal ledger state and bounded budget-consumption evidence.
- Seven valid success and failure continuation actions.
- Bounded follow-up work selection that cannot reselect terminal work.
- Atomic next campaign-generation persistence under an exclusive local writer lock.
- Stale generation, concurrent writer, target drift, unsafe path, unsupported operation, budget overflow, malformed cost, tamper, privacy, and authority-boundary rejection.
- Registry, CLI, GET-only API, dashboard, release metadata, documentation, and exactly one release-verification registration.

## Deterministic verification

- v1187.9 internal checkpoint: **201/201 PASS**.
- v1187.9 external integration suite: **139/139 PASS**.
- v1187.6-v1187.8: **46/46 PASS**.
- v1187.3-v1187.5: **25/25 PASS**.
- v1187.0-v1187.2: **27/27 PASS**.
- v1186.9: **137/137 PASS**.
- v1185.9: **131/131 PASS**.
- v1184.9: **125/125 PASS**.
- v1183.9: **113/113 PASS**.
- v1182.9: **84/84 PASS**.
- v1181.9: **81/81 PASS**.
- v1180.9: **84/84 PASS**.
- v1179.9: **75/75 PASS**.
- v1174.9: **90/90 PASS**, with the repaired-baseline review suite passing.
- Conversation runtime: **35/35 PASS**.
- Source-only runtime boundary: **9/9 PASS**.
- External compilation: **2,050 Python files PASS**, zero syntax failures.

## Quick release profile

The quick profile is correctly reported as **BLOCKED**, not globally passed.

- Total steps: **117**.
- Passed: **92**.
- Non-pass: **25**.
- Current v1187.0-v1187.9 steps: **all PASS**.
- v1187.9 step: **PASS in 6.738 seconds**.
- Inherited historical non-pass groups: **24**.
- Quick-profile elapsed time: **454.820 seconds**.
- Quick-profile budget: **420 seconds**.
- Performance overrun: **34.820 seconds**.
- Runtime cleanup: **PASS**.
- Source writes: **0**.
- Source deletes: **0**.

No current v1187 functional regression was found. The global profile must not be represented as passed.

## Authority and privacy boundaries

- Production campaign work executions: **0**.
- Automatic retries, resumes, reselections, or repairs: **0**.
- Provider/model contacts: **0**.
- Production-source or sandbox mutations: **0**.
- Installation, promotion, certification, publication, or release authority: **0**.
- Autonomous authority expansion: **0**.
- Public evidence remains content-free and digest-bound.

## Remaining limitations

- The checkpoint uses synthetic isolated fixtures rather than a live operator campaign.
- Execution remains limited to `python_compile` and `content_digest_match` over one target.
- Budget observations are caller-supplied bounded evidence rather than direct operating-system metering.
- Accepted results and continuation receipts do not automatically retry, repair, resume, reselect, or execute work.
- The continuation writer lock is local and single-host rather than distributed or identity-attested.
- Persisted campaign generations are content-free local JSON and are not encrypted.
- Desktop Codex and native-provider review remain scheduled for v1200.

## Final source-only candidate verification

- Candidate archive root count: **1** (`Eidolon/`).
- Candidate source files: **2,127**.
- Fresh-extract v1187.9 suite: **139/139 PASS**.
- Fresh-extract source-only boundary: **9/9 PASS**.
- Fresh-extract compilation: **2,050/2,050 Python files PASS**.
- Fresh-extract manifest after testing: **2,127/2,127 files unchanged**.
- Root and ZIP privacy: **zero forbidden entries and zero private-content findings**.
