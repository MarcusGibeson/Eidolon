# R7 lifecycle design review, round 1

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 1 (commit `80a10d9`, document digest `e4c9c8f6…c025ab`)
Outcome: **not clean.**

- **Reviewer A** (journal and replay correctness, and recoverability): 12 blocking, 9 non-blocking.
- **Reviewer B** (scientific integrity, and authorization and attempt semantics): 6 blocking, 8 non-blocking.

Both reviews were read-only and contacted no provider. The first launch of both reviewers ended at a usage
limit before either reported, so both were relaunched from scratch. Revision 2 of the design answers every
finding, as mapped below. Four policy points were ratified by the operator on 2026-09-25; see rulings 6–9
in §21 of the design.

## The most important finding

Both reviewers found the same central flaw, independently. The promise that **a call is never repeated**
(J12) held only if the journal could never go backwards, and revision 1 did not guarantee that.

On Windows, a power loss could lose the `call_started` rename after the provider had already been called.
Deleting the last two files, or a missing run folder, could also make positions run again silently.

Revision 2 closes this with three measures:
- **Durable publication.** Entries are published with a write-through rename that never overwrites, followed
  by a directory flush.
- **Git-committed intent.** An intent record is committed to git before every call.
- **High-water mark.** A git high-water mark makes a truncated journal detectable.

## Reviewer A

| # | Finding (short) | Revision 2 |
|---|---|---|
| A1 | The state table was not a partition. `collecting` and `in_doubt` overlapped, so a call could be repeated. | §5: an ordered decision procedure where the first match wins |
| A2 | Notes broke the "last entry" and adjacency rules, so a lease note could hide `in_doubt`. | Notes are removed from the journal. The non-authoritative `recovery.log` is never read by replay (§16). |
| A3 | Multi-write recovery could hide a torn `call_started` in quarantine. | Torn files are renamed in place (`.torn`) and stay visible to replay until a later entry acknowledges them (§5 R3, §6). |
| A4 | Replay was called "pure" but wrote files. | Pure `replay`, plus a separate `recover()` that only the lease holder runs (J4, §6) |
| A5 | No durable directory entry on Windows, so a lost rename could repeat a call. | §14: `MoveFileExW(WRITE_THROUGH)` without replace, plus a directory `FlushFileBuffers`. Power loss is in the threat model. |
| A6 | Mid-journal integrity failure had no path forward. | `--declare-integrity-failure` records it at the ledger level, and the next attempt needs a distinct sentence (§9.4, ruling 9) |
| A7 | Re-deriving `scored`/`completed` was not deterministic. | No clock in any seal. Derived payloads are pure functions of the prefix. A mismatch is an integrity failure (J7, §4.3, ruling 6). |
| A8 | Torn `closed` entries, and torn or lost ledger entries, had no rule. | Torn `closed` rule (§6). The ledger follows the same rules, and the evidence ref wins over a shorter ledger (§9.1). |
| A9 | Lease problems: PID reuse, exit code 259, an empty lease, racing breakers, and where to log breaks | §15: process creation time, `WaitForSingleObject`, no-overwrite publication, rename-to-break with a single winner, breaks logged in the recovery log |
| A10 | A crashing or hanging scorer caused endless resumes. | Write-ahead `scoring_started`. The scorer runs in a subprocess with a timeout, then either `scored` or `closed(failed, scorer_did_not_finish)` follows (§6). |
| A11 | Tail truncation was indistinguishable from a crash, and sharing violations had no policy. | Evidence intent and high-water cross-checks (§5). Raw text is stored as base64. Bounded retries, then abort (§14). |
| A12 | A stale `index.lock` or a hook could block anchoring, and `anchor_failed` notes piled up. | Evidence ref with plumbing and a private index. No hooks, no shared index (§13). Failures go to the recovery log. |
| A13 | The harness did not kill during recovery or simulate power loss. | §19: a recursive kill campaign to a fixpoint, a power-loss layer that drops or reorders unflushed operations, one I/O choke point, and fact-payload oracles |
| A14 | The write table was incomplete. | §18 now includes every recovery write, the orphan move and the table freeze. |
| A15 | Clear-orphan was allowed after a `call_started`. | Only with no `call_started`. The record is committed first (§9.4). |
| A16 | "Calls so far" was ambiguous. | `closed` records `calls_started`, `calls_recorded`, the in-doubt position and the exception (§4.2). |
| A17 | Torn classification depended on when the kill landed. | The kind is predicted from the grammar. `.torn` persists across kills (§5 R2–R3). |
| A18 | `os.replace` overwrites silently. | Non-overwriting publication, and the lease token is re-checked before every publication (§14). |
| A19 | The sandbox ran inside the in-doubt window. | `call_recorded` then `execution_recorded`. After a crash in between, only the sandbox is re-run (§4.2, §8). |
| A20 | Transport retries were not in the contract. | J14 and §17, with a test |
| A21 | Miscellaneous: manifest seal, foreign files, quarantine name collisions, canonical JSON, table cells | `run_created` seal; foreign files ignored; no quarantine directory; canonical JSON specified (§4.4); table completed (§7) |

## Reviewer B

| # | Finding (short) | Revision 2 |
|---|---|---|
| B1 | The journal could go backwards (power loss, truncation, a deleted folder), so calls could be re-run. | As A5 and A11. A deleted folder is `absent` with the attempt consumed, and can only be recorded at the ledger level, never recollected (§7). |
| B2 | `closed` after `scored`, and drift closing a finished collection, allowed best-of-N. | J13: nothing but `completed` may follow `scored`. Drift in `collected`/`scored` makes commands refuse. Only a scorer failure may close from `collected`. |
| B3 | Free-text abandon and kills allowed optional stopping. | Abandon only when the command's own preflight fails (ruling 7). Partial cells and cross-attempt output identity are disclosed (§12). |
| B4 | Provider contact could happen with an uncommitted ledger entry, and an orphan could hide an attempt. | J11: the ledger and a per-call intent are committed before contact (ruling 8). Orphans only with no `call_started`, and they are disclosed. |
| B5 | Phase B preconditions were under-specified. | §10: the full list, stated against journal entries, including closed anchors and evidence completeness |
| B6 | Grading changes were bundled while the design claimed no scientific change. | Removed (§22). They will be handled as a separate scientific change record. The R6 findings are now recorded in `EXTERNAL_REVIEW_ROUND6.md`. |
| B7 | The re-derivation refinement needed ratification. | Ratified (ruling 6), made deterministic (J7), with torn bytes named by sha256 |
| B8 | A torn note closed a finished attempt. | There are no notes in the journal anymore (A2). |
| B9 | Disclosure undercounted contacts, and per-call guard evidence was dropped. | Disclosure of calls started and recorded plus per-position counts (§12). A guarded digest is kept in every `call_started`. |
| B10 | Sandbox crashes were misclassified as durability events. | As A19 |
| B11 | Integrity-failure disposition was unstated. | Ruling 9 (§9.4) |
| B12 | Superseded contract clauses were not listed. | §20 |
| B13 | The table freeze was missing from the state machine and crash table, and the table's source was unspecified. | §7 and §18. The table is built from the replayed `scored` entry. |
| B14 | Recovered `run_created`, the resume run id, and "n/a" cells were unspecified. | `run_created` now precedes the ledger entry, so no "recovered" entry exists. The run id comes from the ledger. The cells are filled (§7). |
