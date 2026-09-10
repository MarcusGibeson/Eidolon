# Eidolon v1267.0-v1267.9 Iterative Self-Repair Review

## Scope

v1267 completes only the Iterative Self-Repair arc. It consumes the sealed v1265 disposable self-candidate and the exact v1266 trusted-test selection. It does not apply a self-candidate to active Eidolon, install, promote, certify, release, or grant permanent/independent authority. Application remains separately governed by v1255.9; governed self-update remains v1269 work.

## v1267.0-v1267.2 foundations

- Added a deterministic repair-campaign record bound to v1265 operation lineage, v1266 selection digest, active-source manifest, candidate manifest, selected-test digest, affected surfaces, and risk band.
- Added one exact digest-bound bounded-campaign authorization phrase.
- Capped provider repair attempts at two.
- Preserved authority denial before and after the bounded campaign; no standing provider/test/repair/application authority is created.
- Added restart-safe idempotent preparation and content-minimized public projection.

## v1267.3-v1267.5 integration

- Executes only v1266-selected trusted tests from the disposable candidate copy.
- Verifies selected trusted test files still match the active-source baseline before execution.
- Records only test path digests, exit classes, pass/fail state, and output digests; raw test output is not persisted.
- Forms bounded competing implementation/environment/integration hypotheses from failed selected verification.
- Contacts the repair provider only after exact campaign authorization and only when evidence supports repair.
- Rejects repair changes to trusted tests.
- Applies repairs transactionally only to the disposable workspace.
- Recomputes candidate changed paths, affected surfaces, and selected verification after each repair.
- Stops when verification passes, the failure repeats, the environment blocks, the attempt budget is exhausted, or authority/freshness checks fail.
- Successful replay is idempotent and makes no new provider call.

## v1267.6-v1267.8 reliability hardening

- A repeated normalized failure fingerprint blocks before another provider call.
- A genuinely changed failure state may consume the second and final bounded repair attempt.
- The second attempt receives the post-first-repair candidate manifest and prior failed strategy history.
- Repeated/missing provider strategy codes are rejected.
- Candidate test weakening is rejected.
- Provider failure is persisted and never automatically retried.
- Interrupted provider-pending state recovers to operator-review-required blocked state, never an automatic retry.
- Stale active source blocks before test/provider work.
- Cancellation is durable and idempotent.
- Deep runtime paths are covered deterministically.
- Active-source manifest checks surround selected-test/provider activity; the repair engine never intentionally writes the active tree.

## Practical full-tree Eidolon probe

A disposable self-candidate was built from the real v1267 source. The candidate changed only `MAX_REPAIR_ATTEMPTS` in `iterative_self_repair_foundations.py` from 2 to 3. v1266 selected four real v1267 verification files: three focused tests and the v1267.9 checkpoint as regression coverage. Initial verification detected the defect. One repair provider call restored the bound to 2 and the rerun passed. The v1267 repair portion completed in about 26 seconds in the successful bounded probe. The active Eidolon source manifest was identical before and after. The disposable workspace was removed afterward.

The probe used one v1265 fixture provider call to create the intentionally defective candidate and one v1267 repair provider call to repair it. No provider call occurred on replay.

## Authority boundary

v1267 grants no active-source mutation, selected-project mutation, application, installation, promotion, certification, release, self-update, permanent approval, or independent authority. A consumed exact repair authorization is bounded to one candidate lineage and at most two repair attempts. It is not reusable authority.

## Remaining limitations

- Selected tests execute as trusted baseline-owned subprocesses in the disposable workspace. This is bounded and source-isolated, but is not claimed to be an OS-enforced sandbox.
- Native Windows cross-process repair locking, NTFS junction/reparse behavior, and restart during provider return require Desktop Codex validation.
- v1267 produces repair/verification evidence but does not yet provide the polished operator-facing review packet owned by v1268.
- v1267 does not apply the candidate to active Eidolon; that remains later governed work.
