# Desktop Codex Handoff — v1273.9 Ownership and Concurrency

## Candidate scope

Validate native Windows behavior of the v1273 local ownership/fencing layer that coordinates v1272 candidate and verification stages.

## Required native scenarios

1. Start two independent Windows processes that attempt the same stage claim simultaneously; exactly one may receive the executable owner epoch.
2. Submit the same stage from two browser tabs/API requests and verify only one live claim can enter the stage.
3. Queue/retry the same operation while the first owner lease is live; the retry must be fenced without provider/test replay.
4. Force-terminate the owner after v1273 claim creation but before v1272 stage entry; successor transfer must first reconcile v1272 and may enter only if no in-flight external effect exists.
5. Force-terminate after v1272 write-ahead start and during lower provider/test work; successor must fail closed when durable effect is ambiguous.
6. Force-terminate after lower v1265/v1267 completion but before v1273 ownership completion; successor must reconcile durable lineage and suppress provider/test replay.
7. Deliver a late result from the expired/fenced owner after a successor epoch exists; the old result must not commit ownership state.
8. Exercise NTFS directory-lock creation/removal, atomic JSON replacement, sharing violations, antivirus/indexer contention, and process death while the small critical-section lock is held.
9. Exercise long runtime roots and long target paths under the supported Windows path configuration.
10. Restart dashboard/API processes with expired claims and verify no old exact authorization is renewed, reused, or inferred.

## Expected boundaries

- Fencing token is not an authorization token.
- Lease expiry is not proof of no external effect.
- v1272 reconciliation remains mandatory for successor execution after expiry/blocked ownership.
- v1265 provider mutation and v1267 testing/repair retain separate exact authorization.
- v1269 update, v1255 application, rollback, installation, promotion, certification, and release are not authorized by v1273.
- The v1273 exactly-once claim is local to Eidolon's durable ownership coordinator; distributed consensus across network partitions is not claimed.

## Handoff state

`v1273_ownership_concurrency_checkpoint_ready_for_desktop_codex_review`

Next bounded unit after this checkpoint: **v1274 Environment Awareness**. v1274 is not part of this handoff and has not been started.
