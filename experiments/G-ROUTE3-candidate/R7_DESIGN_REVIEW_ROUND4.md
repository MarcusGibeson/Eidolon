# R7 lifecycle design review, round 4

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 4 (commit `4499175`, document digest `2283b5ba…fa62d`)
Outcome: **not clean.**

- **Reviewer A** (journal and replay correctness, and recoverability): 6 blocking, 10 non-blocking.
- **Reviewer B** (scientific integrity, and authorization and attempt semantics): 2 blocking, 10 non-blocking.

A-F6 and B-N1 are the same finding, so there are 7 distinct blocking findings.

Both reviews were read-only and contacted no provider. Reviewer A's experiments were:
- a Windows directory-flush test, which succeeds for a normal user;
- a `LockFileEx` range-read test;
- listing the proposed data root's parents.

Reviewer B confirmed that nothing scientific has changed, and that the private evidence repository meets
ruling 10 in substance.

## Reviewer A

| # | Severity | Finding (short) | Revision 5 |
|---|---|---|---|
| F1 | Blocking | An interrupt at position N closed a collected attempt | The flag is honoured before each `call_started`, and after each record whose state is not `collected`. From `collected` on, the process exits without writing and `--resume` scores (§7, J13, §18). |
| F2 | Blocking | Ctrl+C reached the sandbox test child and was recorded as a model failure | The sandbox runs in an isolated worker: its own process group (Ctrl+C disabled and inherited) inside a kill-on-close job. Signal and console-control exits, worker death and worker timeouts are recorded as `sandbox_host_failure`. `run_isolated_fixture` is unchanged, so normal-exit grading is as in R6 (§8). |
| F3 | Blocking | No ref existed before the first consumption commit | `D` is set up atomically: a temporary folder holding `root.json` and `evidence.git` with a root commit, renamed into place (§3.1). The ref exists before any ledger entry. |
| F4 | Blocking | `root.json` was regenerated, or its binding was undefined | `root.json` is in the root commit, is restored and never regenerated, and holds no freeze binding (§3, §3.1). Bindings live in `run_created` and `attempt_consumed`. |
| F5 | Blocking | Restores left `.damaged` and `.tmp` files that later counted as extra | Damaged files move to `D/quarantine/`, and restores are staged in `D/staging/`, both outside the verified folders. "Extra" means extra `NNNNNN.*` entries only (§13.4). |
| F6 | Blocking | Protection missed a collected attempt with a damaged middle entry | Protection is evaluated per file, independent of the chain. Any sealed record of position N, or any scoring kind, on disk, in a commit or in a snapshot, protects the attempt (§9.4). |
| N1 | Non-blocking | The next entry number was undefined | The highest occupied number, `.json` or `.torn`, plus 1 (§4.1). |
| N2 | Non-blocking | Read errors were treated as tears | Read errors are retried, then the command refuses. Only bytes actually read can be torn (§4.4). |
| N3 | Non-blocking | "Parses but differs" blocked real damage | Files are compared byte for byte. Unsealed files are restored whenever they differ. Sealed entries are restored when they fail to parse or seal, and a valid different seal is an integrity failure (§13.4). |
| N4 | Non-blocking | `run_created` was not durable before the ledger entry | It must be durable first (§9.2). §6 has a row for `absent` when the consumption is uncommitted. |
| N5 | Non-blocking | The ledger acknowledgement parsed torn bytes; ledger integrity failure; commit coverage | A deterministic rule decides whether an orphan run claims the head before the tear (§9.1). Ledger `integrity_failure` is a declared exception (§1.3). Every boundary commit adds all uncommitted ledger entries (§13.1). |
| N6 | Non-blocking | Lock range and truncation, and POSIX `fcntl` | The file is opened without truncation and one byte at 2^40 is locked, beyond the informational text. POSIX uses `F_OFD_SETLK` or `flock` (§15). |
| N7 | Non-blocking | Orphaned children, stale-lock premise, ref backend | Every child runs in a kill-on-close job (§8, §15). The `files` ref backend and config are checked on every command. Table commits must be ancestors of the evidence head (§10.7). |
| N8 | Non-blocking | The `orphans` existence check made replay read other files | Existence is checked by the publisher. Replay checks only for duplicates (§4.1, §5). |
| N9 | Non-blocking | Reason mapping; recovery running the sandbox or scorer; frozen ledger closures; orphan snapshots | There is a one-to-one reasons table (§4.2). `recover()` never runs the sandbox or scorer (§6). Runs closed at ledger level are frozen. Orphan folders are verified against their snapshots (§9.4). |
| N10 | Non-blocking | Missing crash rows and campaign seeds | Every listed case has a §18 row and a §19 seed. |

## Reviewer B

| # | Severity | Finding (short) | Revision 5 |
|---|---|---|---|
| N1 | Blocking | A damaged entry left a collected attempt unprotected | As A-F6 (§9.4) |
| N2 | Blocking | A new freeze could restart the ledgers | `D` is a constant of the experiment, not of a freeze. Ledgers, attempt numbering and disclosure span every freeze. The freeze writer refuses once `D` holds a table or a protected or completed attempt, and refuses any other `D`. This carries R6's clause (§3, §9.3, §20). |
| NB-1 | Non-blocking | Interrupt at position N | As A-F1 |
| NB-2 | Non-blocking | The §13.3 supersession was too broad | Supersession applies only when the run has no valid entry. Anything else is an integrity failure (§13.3). |
| NB-3 | Non-blocking | Kind and attempt number of a torn ledger tail | A deterministic orphan-run rule. The attempt counts as consumed, so the next launch is n+1 (§9.1). |
| NB-4 | Non-blocking | Restores were not disclosed, and their interaction with §10.8 | Quarantined files are committed and form the restore log. It is disclosed but excluded from the §10.8 comparison (§12, §13.4). |
| NB-5 | Non-blocking | Snapshot-based disclosure | Lower bounds, partial results and identity come from the snapshot's individually sealed records, labelled as such (§9.1, §12). |
| NB-6 | Non-blocking | The R6 table checks were not all listed, and the frozen-artifact test used relative paths | Every check is listed. The frozen-artifact test compares by digest against the freeze's artifacts (§7, §10.7). |
| NB-7 | Non-blocking | A permanently unreachable provider was a dead end | Receipts that cannot be read after 10 minutes are a persistent preflight failure. Abandon is disclosed as optional stopping (§9.3). |
| NB-8 | Non-blocking | Public anchoring | Phase B precondition §10.9: `main` must contain the table's bytes. A bundle at the table freeze and at every Phase B terminal boundary. The evidence head goes in the Phase B terminal disclosure record (§13.4). |
| NB-9 | Non-blocking | With no completed attempt, nothing was disclosed | A disclosure record is committed at every terminal and ledger-closure boundary, and the runbook publishes the latest regardless (§12). |
| NB-10 | Non-blocking | Design statements were inside rulings | The rulings are restated as given. Refinements are marked *design note* (§21). |
| Hardening | — | A recreated repository after `evidence.git` and the ledger were deleted | An existing `D` without an intact repository is refused, never recreated (§3.1, §1.3). |
