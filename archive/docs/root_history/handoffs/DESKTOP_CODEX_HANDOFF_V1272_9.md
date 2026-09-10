# Desktop Codex Handoff v1272.9

Validate the source-only v1272.9 candidate on native Windows without installing over an operator-active Eidolon environment.

## Primary native scenarios

1. Kill the owning process after the v1272 write-ahead journal is durable but before the lower v1265/v1267 stage commits. Confirm the state is treated as ambiguous and no provider/test retry occurs automatically.
2. Kill the process after v1265 has durably sealed a candidate but before the v1270/v1272 completion receipt. Confirm restart reconciliation advances bookkeeping without a second provider call.
3. Kill the process after v1267 has durably passed trusted verification but before parent review readiness is recorded. Confirm restart reconciliation does not rerun trusted tests or replay the repair provider.
4. Close/restart dashboard and API processes around active, paused, interrupted, and provider-outage states. Confirm durable campaign state remains coherent and browser closure itself grants no authority.
5. Restart after a v1271 advisory lease expires. Confirm stale lease recovery occurs before session-state reconciliation and does not claim v1273 exactly-once ownership.
6. Exercise NTFS lock release, temp-file fsync plus atomic replacement, forced process death, and machine restart/power-interruption approximations. Inspect for partial/corrupt recovery records and validate quarantine/rebuild behavior.
7. Exercise long external-runtime paths and Windows path normalization. Where available, inspect junction/reparse interactions without weakening existing source-containment rules.
8. Prepare or simulate an interrupted v1269 governed-update state and inspect it through v1272. Confirm inspection remains read-only: no update retry, authorization reuse, rollback, installation, promotion, certification, or release occurs.
9. Re-run the v1270 long-verification/harness-duration scenario through v1271 budgeting. Confirm recovery preserves split/checkpointed verification decisions rather than solving long work by blanket timeout inflation.

## Explicit boundary

Do not certify cross-process exactly-once execution, lease ownership transfer, browser-tab ownership, queue ownership, or late-result adoption as a v1272 capability. Those semantics belong to v1273 Ownership and Concurrency.

Do not grant provider, test, repair, self-update, application, rollback, installation, release, permanent, or autonomous authority during this review. v1273 has not been started.
