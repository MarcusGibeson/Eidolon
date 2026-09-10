# Eidolon v1268.0-v1268.9 Operator Review Handoff Review

## Outcome

v1268 completes the operator-review boundary between verified disposable self-repair and the separately governed v1269 self-update stage. A v1267 candidate must be verified before review preparation. The packet is content-minimized and digest-bound to the exact active-source and candidate manifests.

## v1268.0-v1268.2

- Added exact review lineage over v1265 self-candidate, v1266 selection, and v1267 verification.
- Added readable changed paths/actions/sizes/digests without source contents.
- Added verification summary, repair history, affected surfaces, risk codes, limitations, unresolved uncertainty, and rollback/recovery prerequisites.
- Preparation is deterministic/idempotent and grants no authority.

## v1268.3-v1268.5

- Added packet-digest-bound `approve_for_v1269_consideration`, `defer`, and `reject` dispositions.
- Same decision replays idempotently; conflicting decisions fail closed.
- Approval creates only a digest-only v1269 consideration handoff.
- Fresh v1269 preflight and fresh exact v1269 authorization remain mandatory.

## v1268.6-v1268.8

- Added active-source and candidate-manifest freshness validation.
- Added resealed semantic-tamper rejection.
- Added long-runtime-path coverage, read-only health inspection, and native Windows review handoff.

## Practical full-source evidence

A full Eidolon source-only copy was created in external runtime storage. One candidate-only module (`conscious_agent/v1268_review_probe.py`) was added. v1266 selected two retained regression tests; v1267 passed them in one test round with no repair attempt; v1268 produced a review packet containing one changed file, one low-risk bounded-change signal, four explicit unresolved uncertainty codes, and rollback/recovery prerequisites. The operator disposition `approve_for_v1269_consideration` produced a ready handoff while all self-update/application authority remained denied. The active source manifest was unchanged and the probe file never entered active source.

## Authority boundary

v1268 does not apply, install, promote, certify, release, self-update, contact providers, execute commands/tests, or grant permanent/independent authority. Application remains separately governed by v1255. v1269 owns any active self-update, restart, health verification, and rollback behavior.
