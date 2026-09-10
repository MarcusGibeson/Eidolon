# v1273.0-v1273.9 Focused Validation

v1273 adds a local durable ownership/fencing coordinator above the existing v1272 restart/crash-recovery journal. It does not replace v1272 reconciliation and does not create provider/test/update authority.

## Focused suites

- `tools/v1273_0_2_ownership_concurrency_foundations_tests.py`
- `tools/v1273_3_5_ownership_concurrency_integration_tests.py`
- `tools/v1273_6_8_ownership_concurrency_reliability_tests.py`
- `tools/v1273_9_ownership_concurrency_checkpoint_tests.py`

## Key demonstrated properties

- exactly one live executable claim under a spawned multi-process race;
- duplicate process/tab/queue/retry submissions suppressed;
- same-owner re-entry suppressed;
- bounded lease heartbeat and monotonically increasing owner epochs;
- expired-owner successors cannot execute before v1272 reconciliation;
- durable lower-stage completion is reused without provider/test replay;
- late results from fenced epochs cannot commit;
- malformed ownership projections are quarantined rather than reconstructed with invented ownership history;
- raw owner labels are not persisted;
- fencing tokens and ownership claims are non-authorizing concurrency evidence.

Final aggregate results are recorded in `Eidolon_v1273_9_FINAL_VALIDATION.md` after retained verification and fresh-extraction parity.
