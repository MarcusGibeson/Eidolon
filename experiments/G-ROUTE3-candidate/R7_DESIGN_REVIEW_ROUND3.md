# R7 lifecycle design review, round 3

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 3 (commit `df78fa0`, document digest `bda5feeb…25830dd`)
Outcome: **not clean.**

- **Reviewer A** (journal and replay correctness, and recoverability): 6 blocking, 11 non-blocking.
- **Reviewer B** (scientific integrity, and authorization and attempt semantics): 4 blocking, 9 non-blocking.

Both reviews were read-only and contacted no provider. Reviewer A's experiments were a throwaway repository with
a second worktree, and one read-only `NtQuerySystemInformation` query. Reviewer B confirmed that nothing
scientific has changed since `80a10d9~1`. B also confirmed that treating tampering inside an attempt in
progress as a residual is consistent with ruling 10.

## What revision 4 changes structurally

- **One fixed data root `D`, outside every checkout, bound in the freeze.** It holds a private evidence
  repository. This answers A-B5: the per-worktree ledger and lease against a repository-global ref, restores
  and declarations from another worktree, and `pack-refs` elsewhere. It also answers A-NB8 (packed-refs
  durability) and B-13/A-NB5 (the table's location).
- **An OS-held lock** instead of staleness heuristics. This answers A-B6 (the Windows boot time moves with
  clock steps) and A-NB9 (lease release and break).
- **Every command verifies every committed file** before acting. It restores missing or unparseable files from
  their commits, and refuses when a file parses but differs. This answers B-1, B-2 and B-4, A-NB3 and A-NB4.
- **"Published" and "durable" are separated.** No irreversible step follows an entry that is not durable.
  This answers A-B4.

## Reviewer A

| # | Severity | Finding (short) | Revision 4 |
|---|---|---|---|
| B1 | Blocking | Tear prediction was wrong after a failure record | The prediction table (§5) gives `closed` with the original failure's reason after any failure record. "Cleanly" is required for `scoring_started`. Every last-entry case is covered. |
| B2 | Blocking | Two `.torn` entries in a row were rejected; a ledger `.torn` at entry 1 was rejected | The trailing tear is a run of `.torn` entries sharing one prediction. `acknowledges` is a list, and the previous seal skips to the last valid entry (§4.1, §5). The entry-1 clause is for run journals only, and the ledger has a genesis seal (§4.1, §9.1). |
| B3 | Blocking | Deadlock: a pending consumption commit when `run_created` is torn | J8 now completes pending boundaries **after** recovery (step 5). A pending consumption boundary whose run cannot replay to `created` is superseded by the ledger-level closure (§13.3, §6). |
| B4 | Blocking | A failed directory flush still led to a send | "Published" (the rename succeeded) is separated from "durable" (the flush then succeeded). No request, sandbox run or boundary commit follows an entry until it is durable. `ERROR_ALREADY_EXISTS` is always a failure, and success after other errors is defined precisely (§14, §8). |
| B5 | Blocking | Shared repository and per-worktree data | One fixed `D` for all checkouts, bound in the freeze, with `root_id`, plus a private evidence repository inside `D` with no other worktrees and no gc. One lease in `D` (§3, §13, §15). |
| B6 | Blocking | The Windows boot time is not constant, so a live lease could be broken | An OS lock (`LockFileEx` / `fcntl`), released by the OS when the process dies. No heuristics, and the handle is non-inheritable (§15). |
| NB1 | Non-blocking | Durability of recovery writes | A directory flush follows every recovery rename, unlink and deletion (§6). |
| NB2 | Non-blocking | Where orphan-temp names are recorded | The envelope field `orphans` is set on the next entry. For a terminal directory, the terminal commit carries the name (§4.1, §6). |
| NB3 | Non-blocking | Committed attempts were not read-only | Nothing may follow a terminal entry. A terminal-committed journal is restored from its commit when damaged, and refused when a file differs or an extra file appears (§5, §13.4). |
| NB4 | Non-blocking | Closure snapshots collided with committed paths | Snapshots go under `closures/` and `orphans/`. Add-only conflicts are a declared exception (§1.3, §13.1). |
| NB5 | Non-blocking | Table and audit location | `D/tables/`. The audit document is copied there, committed at the table freeze, and restored when damaged (§7, §13). |
| NB6 | Non-blocking | Interrupt handler races | The handler only sets a flag. The main loop closes through the normal path, after recording any request in flight (§7). |
| NB7 | Non-blocking | Antivirus deleting the tail `call_started` | A declared residual, with a runbook exclusion (§1.2). |
| NB8 | Non-blocking | Git version, and `pack-refs` from other worktrees | Git 2.38 or later. The private repository's own config sets `core.fsync`. There are no other worktrees and no gc (§11, §13). |
| NB9 | Non-blocking | Ledger acknowledgement took two writes; restore versus acknowledgement; lease details | `ledger_torn_acknowledged` is one entry that also closes. A committed copy is always restored and never acknowledged (§9.1). The lease is an OS lock (§15). |
| NB10 | Non-blocking | Wording: J8/§6 drift; J13 in R1a; the drift "reason" | J8 step 4 puts the drift check before derivation and before the sandbox. R3 forbids `closed` after `collected`. The drift pseudo-reason is removed. |
| NB11 | Non-blocking | Crash-table rows and campaign seeds | §18 has every listed row. §19 seeds every listed case and adds a damage injector. |

## Reviewer B

| # | Severity | Finding (short) | Revision 4 |
|---|---|---|---|
| 1 | Blocking | A torn `attempt_consumed` closed an attempt that may already have made calls | A committed ledger entry is always restored, never acknowledged (§9.1, §13.4). The protection rules apply to every ledger-level closure, declared or automatic (§9.4). Launch is refused if any earlier attempt replays as `completed` or has a committed `completed` copy (§9.3). |
| 2 | Blocking | Phase B attempts were not verified after their boundaries | Every command verifies every committed item of both phases before acting (J8 step 2, §13.4). |
| 3 | Blocking | The operator-caused flags were incomplete | Every non-complete attempt is flagged "optional stopping cannot be excluded" (§4.2, §12). |
| 4 | Blocking | The table freeze did not verify the named attempt or the ledger | Covered by J8 step 2 for every command, the table freeze included (§7). |
| 5 | Non-blocking | The table-in-git check was dropped | The table and audit copy are committed at the table freeze and verified by §13.4. Phase B also checks the table's seals and run id against the named attempt (§10.7). |
| 6 | Non-blocking | Sentence semantics | §7.1 gives every sentence: `<binding>` must equal the freeze in force, and `--resume` requires a byte-identical sentence. |
| 7 | Non-blocking | §20 omissions | §20 is now a table that includes the three clauses named, plus the move of data to `D`. |
| 8 | Non-blocking | J13 was not in the grammar | R3 forbids `closed` after `collected`. |
| 9 | Non-blocking | Residual wording; completed attempts with a pending commit | §1.2 defines "in progress" and says that launch continues through completion. Protection also covers any sealed on-disk entry that shows `collected` or later (§9.4). |
| 10 | Non-blocking | Counts for `journal_missing` | Counts are unknown, with lower bounds. Identity is undeterminable (§9.1, §12). |
| 11 | Non-blocking | Undefined reasons and states | `operator_cancelled`, the state field and the drift pseudo-reason are removed. The reasons table in §4.2 is complete. |
| 12 | Non-blocking | Torn `run_created` when a committed copy exists | This is deliberately **not** restored. A damaged `000001.json` in a non-terminal attempt means later entries may be lost as well, so continuing could repeat calls. It becomes `integrity_failure`, and is declared subject to the protection rules (§6, §13.4). |
| 13 | Non-blocking | Table location | `D/tables/` (§3). |
