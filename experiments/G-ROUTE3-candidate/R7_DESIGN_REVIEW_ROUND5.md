# R7 lifecycle design review, round 5

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 5 (commit `73f4d26`, document digest `c52a8ed5…94857`)
Outcome: **not clean.**

- **Reviewer A** (journal and replay correctness, and recoverability): 3 blocking, 7 non-blocking.
- **Reviewer B** (scientific integrity, and authorization and attempt semantics): 3 blocking, 8 non-blocking.

The first launch of both reviewers stopped at a usage limit before either reported, so both were relaunched from
scratch. Both reviews were read-only and contacted no provider.

Reviewer A ran these experiments in the session scratchpad:
- a nested kill-on-close job;
- `CREATE_NEW_PROCESS_GROUP` and `CREATE_NO_WINDOW` under Ctrl+C and Ctrl+Break;
- the lock at 2^40;
- renaming a folder while a file in it is open;
- `git hash-object` under this machine's `core.autocrlf=true`.

Reviewer B confirmed that no supported-command path discards or replaces a completed or collected attempt. B also
confirmed that no scientific artifact changed.

Two blocking findings (B-F1, B-F2) were **regressions against R6 behaviour** that revision 5 would have
introduced silently. Revision 6 fixes both by carrying the R6 code paths over verbatim.

## Reviewer A

| # | Severity | Finding (short) | Revision 6 |
|---|---|---|---|
| B1 | Blocking | `recover()` both "never runs the scorer" and re-derives a torn `scored` | `recover()` never derives and never runs a child. `torn_pending(derived)` is a §7 row: `--resume` re-derives after the drift check, then continues (§6, §7). |
| B2 | Blocking | A permanently unreadable file refused every command | A committed file is quarantined by rename, which needs no read, and restored. An uncommitted entry that cannot be read blocks the phase under the declared exception, because it could be protective (§4.4, §13.4, §1.3). |
| B3 | Blocking | The host's `core.autocrlf=true` changed evidence bytes | `hash-object -w --no-filters` and `cat-file blob`. The repository config pins `core.autocrlf=false` and `core.safecrlf=false`, and every command checks them. `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL` set to null, a fixed identity, and no signing (§11, §13.1). There is a CRLF seed in §19. |
| NB-1 | Non-blocking | An interrupt could hide a failure reason; counts in `closed` | The failure field takes precedence over the interrupt (§7). R3 binds every `closed` reason to its source. Counts and the in-doubt position are no longer stored, and are recomputed from the chain (J5, §4.2, §5). |
| NB-2 | Non-blocking | Ctrl+Break reached the worker | The worker and the scorer use `CREATE_NO_WINDOW`, which the reviewer tested against both Ctrl+C and Ctrl+Break (§8). |
| NB-3 | Non-blocking | A child assigned to the job after `Popen`; breakaway; POSIX | The holder assigns itself to the kill-on-close job before creating any child, and breakaway is forbidden. On Linux the holder is a child subreaper, with a declared SIGKILL limit. The governed run executes on Windows (§15). |
| NB-4 | Non-blocking | Race between concurrent setups; empty `D` | A setup lock in the parent folder. Leftovers are removed only under that lock, an empty `D` counts as absent, and WinError 5 on the rename is retried (§3.1). |
| NB-5 | Non-blocking | Worker timeout versus R6 grading | The worker runs R6's whole classification verbatim, with a 180 s worker timeout (§8). As B-F2. |
| NB-6 | Non-blocking | On-disk locations of tree prefixes; orphan snapshot before the move | A location table for every prefix. An orphan snapshot is checked in `runs/<run_id>/` first, and a partial POSIX move is completed (§13.1). |
| NB-7 | Non-blocking | New freeze with an attempt in progress; missing seeds; trailing quarantines | The freeze writer refuses while an attempt is in progress (§9.3). The seeds are added (§19). A quarantine is committed at once by a restore boundary (§13.1, §13.4). |

## Reviewer B

| # | Severity | Finding (short) | Revision 6 |
|---|---|---|---|
| F1 | Blocking | Provider errors and fallback models were no longer failures, a regression against R6 | R6's rule is carried verbatim: an exception, a non-empty adapter `error`, or a returned-model mismatch sets `transport_failure` (§8 step 4). It has a §20 row and stub seeds in §17 and §19. |
| F2 | Blocking | Worker host classification could take genuine model failures, such as infinite loops or memory exhaustion | The worker runs R6's coding classification verbatim. `sandbox_worker_failure` is only for the worker process itself: it died, exceeded 180 s, or was killed by a console control or signal. No candidate can reach it (§8, §20). |
| F3 | Blocking | A consumed attempt that is never resumed was never disclosed | A disclosure record, marking the attempt in progress, is committed at the consumption boundary (§12, §13.1). |
| F4 | Non-blocking | Ctrl+Break reached the worker, and compile failures were misgraded | `CREATE_NO_WINDOW` (§8). As A-NB2. |
| F5 | Non-blocking | The protection predicate was too broad | Only a clean non-coding `call_recorded` N, a clean `execution_recorded` N, or a derived entry protects (§9.4). |
| F6 | Non-blocking | `D` was identified by path only | Each freeze records the canonical, fully resolved path, and commands never re-expand environment variables. The freeze writer compares against `D` in every earlier R7 manifest, and synthetic runs never use `D` (§3). |
| F7 | Non-blocking | A weak public anchor | The table file at the tip of `main` must match, with exactly one version in first-parent history. Pushing is a runbook step (§10.9, §7). |
| F8 | Non-blocking | The table freeze skipped §10.1–10.6; synthetic runs | `--freeze-table` requires §10 items 1–6. Synthetic runs use a temporary data root (§7, §3). |
| F9 | Non-blocking | Ruling text did not match the bound JSON; scope of "authorize contact" | §21 quotes ruling 7 as given, with a design note. Ruling 9's extension is a design note. "Generation calls" (§7.1). The candidate JSON's ruling text is updated to match. |
| F10 | Non-blocking | Orphan tie-break; freeze during an attempt; missing §20 rows | Launch is refused while an orphan run folder exists (§7, §9.1). The freeze writer refuses while an attempt is in progress (§9.3). §20 gains rows for pause and cancel, `_require_governed_real_path`, redirects, provider failure, and the worker. |

**Redirects (B-F10).** R6's guarded adapter is not modified. `requests` would follow a redirect, but only a
non-Ollama server at the fixed loopback endpoint could issue one, and a fake server is out of scope. §17 states
this, and a stub test documents it.
