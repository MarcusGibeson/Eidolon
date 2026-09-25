# R7 lifecycle design review, round 2

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 2 (commit `fd5c9f8`, document digest `b98091616a05…6285197`)
Outcome: **not clean.**

- **Reviewer A** (journal and replay correctness, and recoverability): 12 blocking, 8 non-blocking.
- **Reviewer B** (scientific integrity, and authorization and attempt semantics): 6 blocking, 9 non-blocking.

Both reviews were read-only and contacted no provider. Reviewer A's only experiment was a throwaway git
repository in the session scratchpad.

## Main cause and operator ruling 10

The per-call git evidence added in revision 2 was behind most of the findings. That mechanism was an intent
committed before every call, plus a high-water mark and cross-checks in replay. It caused:
- recovery loops (A-N3);
- a stale ref lock blocking every call (A-N9);
- laundering by deleting the ref (B-N4);
- weaker durability than claimed (A-N13);
- compare-and-swap conflicts during collection (A-N15);
- replay depending on git (A-N18).

It also did not protect against cheap tampering with the tail after the last intent (B-N2a).

The operator ruled on 2026-09-25 (ruling 10): **accidents are handled in code, tampering at boundaries.**
- The code guarantees G1–G5 against accidents and misuse of supported commands.
- Each attempt's journal is committed to git at its consumption and terminal boundaries, and at the table
  freeze.
- The table freeze and Phase B verify every journal byte for byte against its committed copy.
- Per-call git, high-water cross-checks and mid-run ref handling are removed.
- Tampering inside an attempt still in progress is a declared residual (§1).

Revision 3 applies the ruling and answers every remaining finding.

## Reviewer A

| # | Severity | Finding (short) | Revision 3 |
|---|---|---|---|
| N1 | Blocking | The last entry was never grammar-checked, so a re-sealed edit could cause a call to repeat. | R1a checks grammar and payload for every entry that parses and seals, including the last. That covers the position and call id against the schedule, and no continuation after a failure field. Only a last entry that fails to parse or seal falls to R2. |
| N2 | Blocking | R0 was not total (empty or temp-only journal, a lone `000001.torn`). | R0 is "no `.json` and no `.torn` entries". A lone `000001.torn` becomes `torn_pending(1, run_created)`, which makes the run an orphan, or leads to a ledger-level `durability_uncertain` closure (§6). |
| N3 | Blocking | Cross-check override loops and undefined precedence | Removed with the cross-checks (ruling 10). Replay reads no git (J4). |
| N4 | Blocking | A torn `scored` could not be predicted, and the torn-`closed` row was dead. | Prediction excludes `closed` and uses the fact prefix (§5). Derived kinds are uniquely predicted and re-derived. The torn-`closed` row is deleted, and torn bytes are never parsed for decisions (§6). |
| N5 | Blocking | `.torn` chaining and gap rules; a mid-journal `.torn`; POSIX link/unlink leaving both files | R1b: every number is occupied by exactly one `.json` or `.torn`. A non-final `.torn` must be acknowledged by entry n+1, through the envelope field `acknowledges` and a previous seal of n−1. A `.torn` at entry 1 with later entries is an integrity failure. An identical `n.json`/`n.torn` pair counts as the `.torn`, and recovery unlinks the `.json` (§5, §6). |
| N6 | Blocking | Temp deletion could lose a provider output, and orphan-temp names collided. | Delete only if byte-identical to the published entry. Otherwise rename to `.orphan-tmp-<n>-<token>` and name its sha256. Orphan temps are committed at the terminal boundary (§6, §13). |
| N7 | Blocking | Recovery re-scored or re-ran the sandbox under drift. | The drift check comes before any recovery step that derives an entry or runs the sandbox. Under drift, the command refuses (§6, J13). |
| N8 | Blocking | No write-ahead marker for the sandbox, so a crashing sandbox looped forever. | `execution_started` k. Finding it on replay means `execution_recorded(infrastructure_failure=execution_interrupted)`, and the attempt closes. The sandbox is never re-run (§4.2, §6, §8). |
| N9 | Blocking | A stale `evidence.lock` blocked every call. | There is no git in the per-call loop anymore. A lock older than 10 minutes is removed under the G-ROUTE3 lease and logged. Pending boundary commits are retried (§13). |
| N10 | Blocking | The ledger had no torn acknowledgement, no restore, and no path for mid-chain failure; `git clean` deleted it. | The ledger moves under git-ignored `data/`. It gets a `ledger_torn_acknowledged` kind, a byte-identical restore of the committed prefix, and a declared operator-ruling exception for mid-chain failure (§3, §9.1). |
| N11 | Blocking | Terminal entries were committed late; the sweep committed unverified disk state. | J11: the terminal boundary is committed before the command returns, otherwise it is pending and retried first. Commits are built only from a replay that reached the boundary state, and are add-only. `--resume` of an attempt with a later attempt is refused (§7, §13). |
| N12 | Blocking | The lease could stay live after a reboot through process id reuse; POSIX break overwrote; the other-host case had no path. | Boot identifier (exact kernel boot time on Windows, `boot_id` on POSIX). `PROCESS_QUERY_LIMITED_INFORMATION`. A break is a no-replace rename keyed on the observed bytes. `--break-lease` with a verbatim sentence for another host (§15). |
| N13 | Non-blocking | Git ref durability, packed-refs, missing-ref recreation, no reflog | G1 no longer depends on git (§11). Every git call uses `core.fsync=all`, and the ref directory is flushed. `--create-reflog`. The ref is never recreated when ledger entries exist; that is a declared G4 exception (§11, §13). |
| N14 | Non-blocking | Directory-flush rights; error 5 after the rename | `GENERIC_WRITE`. Errors before the rename are separated from "published, flush failed". The directory is re-listed after any error. Preflight checks directory flush (§14). |
| N15 | Non-blocking | Compare-and-swap conflicts during collection; `update-ref` landed but reported failure | No commits happen during collection. Up to 5 retries. The ref is re-read to detect a commit that landed (§13). |
| N16 | Non-blocking | "Byte for byte" was ill-defined once the entry number changes; comparisons used projections. | Payloads are compared only against sealed or committed data (J7, ruling 6 note). Projections are written with §14 and carry no authority. |
| N17 | Non-blocking | The campaign could not reach torn, git, sharing or concurrency states; the crash table lacked rows. | §19: seeded fault and torn scenarios, real git with injected locks and lost ref updates, sharing violations, two-process lease races, and a POSIX run. §18 gains mkdir, lease break, temp handling, ledger, table, git plumbing and orphan-rename rows. |
| N18 | Non-blocking | Replay depended on the evidence ref; an unreadable ref was undefined. | Replay reads no git (J4). An unreadable ref makes the command refuse, and is never treated as empty (§13). |
| N19 | Non-blocking | A per-run lease did not serialize the ledger or the ref. | One G-ROUTE3 lease for both phases, the ledgers, the table freeze and the ref (§15). |
| N20 | Non-blocking | Transient scorer failure closed a collected attempt; the orphan directory rename could replace a target. | A scorer failure refuses and never closes (J13, §6). Orphan directory moves are no-replace (§9.4). |

## Reviewer B

| # | Severity | Finding (short) | Revision 3 |
|---|---|---|---|
| N1 | Blocking | Best-of-N by damaging or deleting a completed attempt and then declaring an integrity failure | §9.4: declaration is refused when the committed terminal copy is `completed`, when the on-disk valid prefix reaches `collected`, or when a frozen table names the attempt. The phase then blocks until an operator ruling. The table freeze and Phase B verify every Phase A attempt against its committed copy (§7, §10). |
| N2 | Blocking | Three cheap closures of a collected attempt | (a) Deleting the last record before the terminal boundary is tampering inside an attempt in progress, a declared residual under ruling 10 (§1). (b) A planted file after collection is predicted as `scoring_started` and re-derived, never closed (§5). (c) A scorer failure refuses and never closes (J13, §6). Drift refuses in every state from `collected` onward, including `scoring_interrupted` (§6). |
| N3 | Blocking | A torn `scored` could not be re-derived | Prediction from the fact prefix. Torn `scoring_started`, `scored` and `completed` are re-derived. The campaign covers each (§5, §6, §19). |
| N4 | Blocking | Evidence-ref deletion laundered by the sweep | The sweep is removed. The ref is created before the first ledger entry and never recreated once ledger entries exist. Deleting it is history rewriting, which is out of scope. Reflog and fsync (§13). |
| N5 | Blocking | Phase B dropped R6's table and audit gates | §10 item 8 restores them: table digest, routing lookup, `corpus_b_consulted` false, corpus/gold/threshold digests, freeze binding, a `READY` audit bound to its document's sha256 and naming the seals, and the audit document not being a frozen artifact. Item 11 puts the table in Phase B's per-call guard. §7 `--freeze-table` requires the same audit. |
| N6 | Blocking | Sandbox re-execution was invisible | `execution_started` k is write-ahead. The sandbox is never re-run, and an interrupted execution closes the attempt (§4.2, §6, §8). |
| N7 | Non-blocking | Circular seal reference between `run_created` and the ledger | Entry 1 chains to the ledger head it claims. Only the ledger entry names the `run_created` seal (§4.1, §9.2). |
| N8 | Non-blocking | Restorable drift or an unreachable provider counted as stuck | Drift in `created`/`collecting` refuses until restored and names the paths. Unreachable or transient provider conditions are not preflight failures. Abandon needs a persistent failing check (§7, §9.3). |
| N9 | Non-blocking | Interrupts were not labelled | `operator_interrupt` closure reason. §12 flags operator-provocable reasons. |
| N10 | Non-blocking | Attempt-number and sentence rules unstated | §7: consumed + 1 on launch, latest on resume, and exact full-match regexes including Phase B's table digest. §9.4: the distinct form is required after a declaration or a `journal_missing` closure and refused otherwise. One lease covers ledger-level commands. |
| N11 | Non-blocking | Phase B partial disclosure; counts for ledger-level closures | §12 defines Phase B partial results (per-observation correctness and determinable routing decisions). §9.1: counts come from the committed copy, otherwise from what can be read. |
| N12 | Non-blocking | Phase B `scored` depended on mutable earlier-attempt state; projections were used as references. | `scoring_started` names the seals of the disclosure inputs (§4.2, §4.3). Comparisons use only sealed or committed data (J7). |
| N13 | Non-blocking | Omissions in §20 | §20 lists abandon `--reason`, the orphan reason, manual lease removal, anchored closures, root agreement, the table schema, the sentence form, and guard evidence. |
| N14 | Non-blocking | The evidence ref is not carried by clones | Evidence commit ids are bound into the table and Phase B's `run_created`. Export for reviewers is a documented operator step (§13). |
| N15 | Non-blocking | Dead end after tampering with a table-named attempt | Declaration on the attempt a frozen table names is refused, so the phase blocks for an operator ruling (§9.4). |

## Also changed in revision 3

- §11, the durability summary, is rewritten: G1 no longer depends on git.
- Boundary-commit tree layout, linear history, and the precise meaning of "on-disk equals committed" (§13).
- `--clear-orphan` commits the folder's files before moving it (§9.4).
