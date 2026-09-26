# R7 implementation review, round 1

Date: 2026-09-25 to 2026-09-26
Reviewed: the R7 implementation at commit `a0b62f3`, against the accepted design, and `R7_IMPLEMENTATION_OBLIGATIONS.md`.

The gate is the operator's safety-gated rule. **BLOCKING** means one of the following:
1. a repeated call;
2. best-of-N;
3. contact without the correct sentence;
4. a silent scientific or grading change;
5. a contradiction with an operator ruling.

**MUST-FIX** means a defect to fix before the freeze.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Journal, replay, recovery and evidence code, and whether the harness proves them | FINDINGS: 2 BLOCKING, 12 MUST-FIX. Five were reproduced in throwaway experiments. |
| B | Scientific integrity, authorization and attempts | FINDINGS: 1 BLOCKING, 8 MUST-FIX. B's own 288-call R6-versus-R7 differential gave byte-identical records and cells. |

Both reviews were read-only and made no provider contact. Their experiments used temporary data roots and stub
or synthetic providers.

## Operator ruling 11 (2026-09-26)

Reviewer B's blocking finding (class 5) was that the added `Close … without further calls` sentence was
abandon-at-will. That contradicts ruling 7 ("verified-stuck only"). The operator chose **"Declare untrusted"**:
- the Close sentence is removed;
- `--declare-integrity-failure` extends to an in-progress attempt whose journal cannot be trusted;
- such a declaration is recorded at ledger level as `integrity_failure`, and is refused for protected attempts;
- the next attempt needs the distinct sentence;
- runbook: after any repair or copy of the data folder, declare, never resume.

This is recorded in the design (§9.4 and §21), in the candidate JSON, and in the code (`command_declare`).

## Reviewer A

| # | Class | Finding | Fix |
|---|---|---|---|
| F1 | BLOCKING (2) | Read corruption, or damage between J8 steps 2 and 4, led recovery to rename a **committed** entry to `.torn`. A protected attempt was then closed at the ledger and replaced (exp4), a completed attempt was rewritten as closed (exp3), and a completed result reached a dead end (exp5). | Recovery never renames, acknowledges or publishes after a committed name. It refuses with `…retry_after_verification`, and the next command's verification restores the committed bytes. The claimant closure of `ledger_torn_acknowledged` is refused for a protected run. Launch refuses any earlier attempt that is protected and not closed at journal level. The A-O7 twin quarantine is extended to ledgers and never quarantines a committed `.torn`. Seeds `read_corruption_ledger_on_launch2`, `read_corruption_completed_on_resume` and `ledger_twin` pass. |
| F2 | BLOCKING (4) | The worker re-read the corpus from disk after the holder's guard, and hashed modules from disk after the run. A `git stash` / `stash pop` inside one worker's life could run drifted code or fixtures undetected. | The worker receives the holder's in-memory fixture. Every process (launcher, worker and scorer) installs a **load-time hashing hook** that hashes each repository module's bytes as they are compiled, never from a `.pyc`. The holder checks the launcher's own modules at launch, and each child's reported digests against `run_created`. The holder's schedules, fixtures and request bodies are built from guarded data files **read once and served sealed**, and bound to their digests at launch. The scorer seals its data inputs the same way, and re-checks the raw disk after scoring. The guard always reads raw disk. |
| F3 | MUST-FIX | A declaration snapshot committed damaged bytes under `closures/` while `runs/` held the good copy, so every command after it was blocked (exp1). | Snapshots exclude files already committed under the run's own journal path, so each file has one committed copy. Seed `declare_then_more_commands` passes. |
| F4 | MUST-FIX | A pending closure snapshot could be lost, and `snapshot_digest` was never verified (exp2). | A closure is pending whenever its ledger entry or any snapshot file is uncommitted. A re-snapshot must match `snapshot_digest`. Seed `pending_ledger_closure` passes. |
| F5 | MUST-FIX | `attach_semantics`, `qualify` and `score` ran unpinned in the scorer. | All of them run through `run_pinned`, and so do `sanitize_strings`, `load_frozen_table` and `build_table`. |
| F6 | MUST-FIX | Earlier attempts were graded against today's schedule, corpus and gold by position. | They are compared with the attempt's `run_created` digests and with each record's `call_id`. On any mismatch the positions are undeterminable, with the reason disclosed. |
| F7 | MUST-FIX | Interrupts: no safe point before a pending sandbox run; scoring continued after `collected`; a second signal did nothing. | All three are added. The harness oracle now knows which safe points precede collection. |
| F8 | MUST-FIX | Ledger `.orphan-tmp` files were never named or committed. | They are named in the next ledger entry's `orphans` field and committed with the ledger. |
| F9 | MUST-FIX | A rerun of `--freeze-table` could replace an intact, different audit copy before the commit, and returned `already_frozen` after the commit whatever it was given. | Before the commit, an intact, different audit copy is refused. It counts as intact if it names the run and both seals, or is recorded by an intact table. After the commit, a different attempt or audit document is refused. `verify_table` runs before publishing. |
| F10 | MUST-FIX | After a failed `refs/heads` flush, the next command trusted the ref. | `open()` flushes `refs/heads` before reading the tree. Seed `refs_flush_failure` passes. |
| F11 | MUST-FIX | `_ledger_close` committed inside recovery (J8 step 4). | Recovery only publishes. The commit happens in J8 step 5 (`sync`). |
| F12 | MUST-FIX | The harness could not prove §19: no recursive kills, weak oracles, J12 counts keyed by the ledger, and unreachable seeds. | Kills now recur in recovery. `PhaseBlocked` no longer counts as a pass for kill or damage cases. The interrupt oracle is strict. Completed facts must equal the uninterrupted run. There is a disclosure-versus-ledger oracle. J12 is keyed by the run whose journal holds the durable `call_started`. Seeds added (all pass): read corruption, ledger twin, declaration then more commands, pending closure, refs flush failure, worker module drift, abandon, kill during setup. |
| F13 | MUST-FIX | The Close sentence was not in the design. | Removed (ruling 11). |
| F14 | MUST-FIX | Some errors printed tracebacks. | Every lifecycle error is a plain refusal: exit 2, or exit 3 for a declared exception (`PhaseBlocked`, `AddOnlyConflict`, `Unreadable`). |
| Notes | — | Staging was never emptied; derivation ran before the guard; temporary files in orphan folders were touched; the git-lock walk had no error handler; `data_root_refusals` skipped recovery. | All fixed. |

## Reviewer B

| # | Class | Finding | Fix |
|---|---|---|---|
| 1 | BLOCKING (5) | The Close sentence is abandon-at-will. | Ruling 11 (above). |
| 2 | MUST-FIX | Phase B resume did not re-run the §10 preconditions. | Phase B resume runs `phase_b_preconditions` for the Phase A attempt named in `run_created`. |
| 3 | MUST-FIX | Drift was not checked after scoring (B-O2). | The holder runs the guard after the scorer returns, and the scorer re-checks the raw disk at the end. |
| 4 | MUST-FIX | Scorer functions ran unpinned. | As A-F5. |
| 5 | MUST-FIX | Counts for ledger-closed attempts were zero, and the in-doubt position was always null. | Counts and identity come from individually sealed files, labelled as such. The in-doubt position is taken from a trailing `call_started` with no record. |
| 6 | MUST-FIX | Temporary-file records disclosed only output identity. | They feed the partial results, labelled `source: temporary_file`. Unparseable temporary files are listed by name and sha. |
| 7 | MUST-FIX | C-O6 covered only coding positions. | As A-F6. |
| 8 | MUST-FIX | Cleared orphans were missing from the table and the Phase B score. | `orphans_cleared` is in the Phase A report, in the table's `r7_binding`, and in the Phase B report. |
| 9 | MUST-FIX | The freeze writer's "other data root" check was vacuous. | It reads the existing freeze file and every version in `main`'s history. |
| 10 | MUST-FIX | The differential and gate tests were not in the repository. | `tools/g_route3_r7_differential.py` covers two Phase A differentials with edge cases (surrogates, CRLF, trailing newline, empty output), Phase B end to end, and gate and freeze-table refusals. |
| Notes | — | `verify_table` before publishing; the flag at `collected`; `freeze_valid` before any command touches D; the §20 wording. | All fixed. |

## Next

1. Commit these fixes.
2. Run the full certification campaign on the fixed code, including the new seeds and recursive kills, and the
   differential.
3. Then a fresh confirmation review of the fixes. The operator decides the gate for that review.
