# R7 lifecycle design review, round 7

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 7 (commit `3780271`, document digest `2b456675…2814dc`)
Outcome: **not clean.**

| Reviewer | Focus | Blocking | Non-blocking |
|---|---|---|---|
| A | Journal and replay correctness, and recoverability | 4 | 6 |
| B | Scientific integrity, and authorization and attempt semantics | 1 | 3 |

Both reviews were read-only and contacted no provider.
- Reviewer A confirmed that the git environment allowlist works with git 2.40.1 on Windows.
- Reviewer B reproduced a lossy-encoding hazard with R6's own pure functions, run offline with bytecode writing
  disabled.

**Change of approach.** Three of A's four blocking findings came from revision 7's machinery for unreadable
files: quarantine records and placeholders. Revision 8 removes that machinery.
- **Unreadable after retries:** the command refuses. This is a declared operator exception (§1.3). It means a
  failing device or a persistent lock.
- **Readable but damaged, or different from its commit:** the committed file is still restored.

## Reviewer A

| # | Severity | Finding (short) | Revision 8 |
|---|---|---|---|
| F1 | Blocking | The quarantine record had no defined path, so recovery looped | Quarantine records are removed. An unreadable file makes the command refuse (§4.4, §13.4, §1.3). |
| F2 | Blocking | Phase B `scored` depended on commit ids, which the collection commit could change | The table and Phase B score carry no commit ids and no restore log. Those appear only in disclosure records (§12). |
| F3 | Blocking | Persistent unreadable files refused permanently, and this was not declared | One declared exception now covers every file under `D` that stays unreadable after retries (§1.3). |
| F4 | Blocking | A stray temporary file in `D/tables/` kept the table freeze pending forever | The freeze is pending only while the table's or the audit copy's **name** is missing from the ref. The rerun quarantines other files (§7, §13.3). |
| F5 | Non-blocking | Order of the disclosure commit and the disk write | The commit comes first, then the disk write. A differing uncommitted record is quarantined (§13.1). |
| F6 | Non-blocking | The `closed` reason was not fully determined | The reason is a function of the last valid entry and `acknowledges`. `closed` is forbidden right after `execution_started` (§5). |
| F7 | Non-blocking | The ledger rules omitted R−1 | Now R−1 to R6 (§9.1). |
| F8 | Non-blocking | Executable binding and worker job | The executable is derived from the published `call_recorded`, decoded with `surrogatepass`. `executable_sha256` is checked by R3 and the scorer. The worker assigns itself to its own job at startup (§8, §5). |
| F9 | Non-blocking | Rows and seeds | Added (§18, §19). |
| F10 | Non-blocking | `git bundle` ran outside the lease | A supported `--export-evidence` command takes the lease and uses the controlled environment (§13.4). |

## Reviewer B

| # | Severity | Finding (short) | Revision 8 |
|---|---|---|---|
| B1 | Blocking | A lone surrogate in the executable made the transfer and hash undefined: a stuck attempt, or a silent grade change | The transfer is lossless. `call_recorded` stores the raw output encoded with `surrogatepass`. The executable is re-derived from it and sent as `ensure_ascii` JSON, which is what `executable_sha256` hashes. The worker therefore applies R6's classification to the identical object. The scorer applies `sanitize_strings` before evaluation, as R6 did. Seeds cover both cases (§4.2, §8, §19). |
| B2 | Non-blocking | Missing §20 rows | Rows for: drift closing the run, a scorer exception closing the run, `_require_declared_synthetic_provider`, `_freeze_valid`, and "model output cannot crash collection". Every freeze-verification failure refuses (§9.3, §20). |
| B3 | Non-blocking | The gold boundary was not assigned to a process | The §10.6 re-derivation and the table's partial cells run in the scorer child. `run_created` carries `gold_loaded_during_collection: false` (§4.2, §8). |
| B4 | Non-blocking | A rerun with a different audit document could replace an intact table before the commit | Before the commit, an intact but different table or audit copy is refused. Only torn copies are quarantined (§7). |
