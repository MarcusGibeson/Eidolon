# Eidolon v1336.9 Process Operations Checkpoint Validation

This checkpoint reconstructs and completes v1336 from the durable v1335.9 recovery baseline after the prior tool-container reset.

## Completed behavior

- Typed candidate process operations are limited to start, monitor, and stop; commands are argument vectors and no shell-string evaluation surface is added.
- Start requires an existing v1333 disposable candidate workspace, sealed satisfied v1332 `shell` preconditions, workspace-matching active v1302 standing command authority, and a `shell` or `process` command class.
- The retained process-ownership subsystem supplies generation-bound ownership, PID start-identity validation, exact child identity, POSIX process groups, Windows `taskkill /T` tree handling, cooperative cancellation, and crash/orphan reconciliation.
- v1336 distinguishes the normal multiprocessing spawn-binding window from stale ownership so a just-accepted operation is not prematurely finalized as uncertain.
- Process stdout/stderr remain runtime-private. Public records contain only bounded sizes and digests; optional log tails are internal-only and never persisted in v1336 evidence.
- Per-stream log budgets and elapsed-time budgets terminate the exact process tree on overflow/timeout.
- A dead worker with a still-live child is reported as `orphan_running`; no replay occurs. Exact orphan termination preserves uncertainty for potentially mutating work.
- Duplicate starts converge on the same sealed operation only for identical invocation material. An explicit content-free invocation discriminator is available for future orchestrators that legitimately need a fresh generation.
- Ordinary chat can inspect a selected process receipt but cannot start, stop, retry, or recover a process.

## Focused deterministic evidence

- v1336.0-v1336.2 foundations: 5/5
- v1336.3-v1336.5 integration: 4/4
- v1336.6-v1336.8 reliability/adversarial: 6/6
- v1336.9 checkpoint: 5/5

Real disposable fixtures exercise process spawn, log evidence, timeout containment, log overflow containment, exact stop, sealed-record tamper rejection, and stale-worker/orphan recovery. The selected source fixture remains unchanged.

## Verification requirement

Because v1336 extends retained shared process-worker/result infrastructure to add bounded log enforcement, the canonical ten-stage segmented verifier was run against a frozen external source snapshot before packaging.

- requested stages: 10
- completed stages: 10
- failed stages: 0
- retained-checkpoint suites: 16/16
- verifier status: segmented_verification_complete
- source remained frozen during the gate
- total elapsed time: approximately 531.6 seconds

Passed stages: source-privacy; authority-approval; conversation-command; development-lifecycle; apply-rollback; queue-execution-recovery; cognition-lessons; provider-project-governance; dashboard-interface; retained-checkpoints.

## Authority and platform boundary

Process execution is limited to the active standing grant and disposable candidate workspace. Process evidence does not create selected-source application, release, installation, network, provider, protected-action, or independent authority. Windows process-tree behavior remains source-level/portable evidence on this Linux host; native Windows execution is not claimed.
