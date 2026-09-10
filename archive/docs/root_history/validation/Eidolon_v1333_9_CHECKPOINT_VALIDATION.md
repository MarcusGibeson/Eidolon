# Eidolon v1333.9 Workspace Isolation Checkpoint Validation

This checkpoint adds the first operational Phase 4 isolation layer on top of v1331 tool contracts and v1332 evidence-bound preconditions.

## Completed behavior

- Supports three explicit isolation modes: `filesystem_copy`, `git_worktree`, and `git_branch_worktree`.
- Creates candidate workspaces and runtime-data roots only under the configured external runtime root; selected source content is manifest-checked before and after creation.
- Materialization requires both an active v1302 standing-session grant bound to the exact selected workspace digest and a sealed, satisfied v1332 precondition record for the required tool class.
- Filesystem copies exclude runtime/private/generated/secret-like material, reject links/reparse boundaries, enforce file/disk budgets, and verify every copied digest.
- Git modes use argv-only Git calls, require the declared Git-worktree command class, bind the candidate to the current commit, and explicitly report repository-metadata mutation while preserving selected source content.
- `retain_for_review` prevents cleanup of changed candidate work unless the caller explicitly discards owned candidate changes. Cleanup removes only the owned candidate/runtime root and, for branch-worktree mode, only the deterministic owned branch.
- Partial creation failures attempt rollback of only newly created owned worktree/branch state.
- Ordinary chat can inspect or plan isolation but cannot create or clean a workspace.

## Focused deterministic evidence

- v1333.0-v1333.2 foundations: 5/5
- v1333.3-v1333.5 integration: 5/5
- v1333.6-v1333.8 reliability/adversarial: 5/5
- v1333.9 checkpoint: 5/5
- retained v1250.3 release metadata: 94/94
- retained v1250.4 checkpoint registry: 118/118

The checkpoint tests exercise a real temporary Git repository when Git is available, including creation of a disposable owned branch/worktree and its deterministic cleanup. The selected fixture source contents remain unchanged.

## Authority and platform boundary

Exact standing-session authority is consumed only to permit the bounded workspace-isolation operation. The resulting candidate grants no persistent tool, project-application, source-mutation, release, installation, protected-action, or independent authority. Native Windows junction/reparse and process behavior remains external evidence and is not claimed by this Linux/container host.
