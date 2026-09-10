# Eidolon v1271.9 Final Validation

v1271 completes Long-Running Work Sessions as a supervised continuation layer around v1270. It preserves the v1270 monolithic-probe wall-clock overrun as a harness-duration/performance finding and addresses it with explicit phase budgets, bounded progress checkpoints, and split-required decisions rather than blanket timeout increases.

The checkpoint is read-only. It performs no provider calls, tests, source mutation, update, application, rollback, installation, promotion, certification, release, autonomous continuation, or authority grant.

Remaining limitation: the v1271 heartbeat/lease model is deliberately advisory and bounded; cross-process exactly-once ownership and late-result semantics belong to v1273. Native Windows process lifetime, shutdown, lock expiry, long-path, and restart behavior require Desktop Codex validation.
