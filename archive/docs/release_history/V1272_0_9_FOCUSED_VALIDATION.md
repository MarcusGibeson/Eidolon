# v1272.0-v1272.9 Focused Validation

## Scope

v1272 adds restart and crash recovery to the existing v1270 Self-Development Alpha campaign through the v1271 Long-Running Work Sessions layer. It does not create a separate development workflow and does not broaden authority.

## Deterministic evidence

- v1272.0-v1272.2 foundations: 62/62 checks pass.
- v1272.3-v1272.5 integration: 37/37 checks pass.
- v1272.6-v1272.8 reliability: 22/22 checks pass.
- v1272.9 read-only checkpoint: 11/11 checks pass.

The integration evidence includes two crash windows that are especially important for exactly-once preparation:

1. v1265 has durably sealed the disposable self-candidate while the v1270 parent campaign has not yet recorded the candidate-stage transition. Recovery advances only the missing parent bookkeeping and does not replay the provider call.
2. v1267 has durably passed selected trusted verification while the v1270 parent campaign has not yet recorded operator-review readiness. Recovery advances only the missing parent/review bookkeeping and does not rerun tests or replay the repair provider.

A lower v1265/v1267 stage that remains merely `running` is treated as externally ambiguous and blocks for operator reconciliation. No automatic retry is inferred.

## Retained evidence

The retained v1271.9, v1270.9, v1269.9, v1256.9, and v1244.9 checkpoints remain applicable. Release-metadata, checkpoint-registry, and privacy/security consolidation suites are retained as final packaging gates.

## Authority

Recovery state, interruption evidence, provider-return evidence, restart generation, heartbeat/lease state, and explicit resume are not provider, test, repair, update, application, rollback, installation, promotion, certification, release, or autonomous authority. v1272 never manufactures replacement v1265/v1267 authorization and never reuses a consumed or absent v1269 update authorization.

## Native Windows handoff

Native review remains required for forced process termination, process lifetime, lock release, NTFS atomic replacement, power interruption, long runtime paths, dashboard/API shutdown and restart, and read-only handling of an interrupted governed-update state.
