# Eidolon v1335.9 Git Operations Checkpoint Validation

This checkpoint completes the first five arcs of Phase 4 and passes the required five-arc broad verifier gate.

## Completed behavior

- Exposes only four typed Git operations: `status`, `history`, `stage_owned`, and `commit_owned`. Generic Git commands and destructive/expansive recovery/publication operations are absent.
- Status and history operate only inside a v1333 Git candidate workspace under an exact active standing grant and sealed satisfied v1332 Git preconditions.
- History evidence persists commit/parent/time/subject digests rather than raw commit subjects; raw subjects can be returned only to an explicitly requesting internal caller and are not persisted.
- `stage_owned` accepts only sealed v1334 file-operation receipts for the same candidate workspace. Current changed paths are matched by path digest, current candidate contents are checked against the receipt postconditions, and any unrelated pre-staged path blocks staging.
- Unowned unstaged changes are left untouched. Owned file-operation drift blocks rather than silently adopting later edits.
- Git hooks, commit signing, fsmonitor, terminal prompting, pagers, and global/system Git config are disabled for the typed path. Local external clean/process/smudge filters block staging/commit rather than being executed implicitly.
- `commit_owned` requires a v1333 owned-branch worktree, bounded-autonomous `git_commit` authority, the exact sealed `stage_owned` receipt, an unchanged index/HEAD, and a bounded single-subject commit message. Detached-worktree commits are rejected.
- Duplicate stage/commit requests converge only when the current index/HEAD matches the prior sealed postcondition.
- Git worktree/branch metadata mutation is reported explicitly; selected source content is unchanged and no network operation exists in the contract.
- Ordinary chat can inspect Git receipts but never stages or commits.

## Focused deterministic evidence

- v1335.0-v1335.2 foundations: 5/5
- v1335.3-v1335.5 integration: 5/5
- v1335.6-v1335.8 reliability/adversarial: 5/5
- v1335.9 checkpoint: 5/5
- retained v1250.3 release metadata: 94/94
- retained v1250.4 checkpoint registry: 118/118

The current host exercised real temporary Git repositories, including owned-branch/worktree creation, receipt-owned staging, coherent commits, duplicate convergence, unrelated staged/un-staged work handling, external-filter blocking, and detached-commit rejection.

## Five-arc broad verifier gate

The canonical v1250.1 segmented release verifier was run against the frozen v1335 source snapshot with its receipt persisted outside the source tree.

- requested stages: 10
- completed stages: 10
- failed stages: 0
- retained-checkpoint suites: 16/16
- verifier exit: 0
- runtime cleanup: clean
- source remained frozen during the gate
- total elapsed time: approximately 497.8 seconds

Passed stages: source-privacy; authority-approval; conversation-command; development-lifecycle; apply-rollback; queue-execution-recovery; cognition-lessons; provider-project-governance; dashboard-interface; retained-checkpoints.

## Authority and platform boundary

The exact standing grant authorizes only the requested typed candidate Git operation. No generic shell authority, network/push authority, selected-source application, release, installation, protected action, or independent authority is created. The retained Windows-oriented v1253.9.2 suite passed as portable/source-level evidence; native Windows execution remains external and is not claimed by this Linux/container host.
