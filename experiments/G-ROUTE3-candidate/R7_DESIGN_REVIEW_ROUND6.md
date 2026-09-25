# R7 lifecycle design review, round 6

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 6 (commit `5e4db59`, document digest `f0e71d6a…fdca133`)
Outcome: **not clean.**

| Reviewer | Focus | Blocking | Non-blocking |
|---|---|---|---|
| A | Journal and replay correctness, and recoverability | 4 | 5 |
| B | Scientific integrity, and authorization and attempt semantics | 0 | 7 |

Both reviews were read-only and contacted no provider.

Reviewer A's experiments used a throwaway bare repository with git 2.40.1 and Python 3.11.9. Among other
things, A tested that an inherited `GIT_OBJECT_DIRECTORY` redirects objects out of the evidence repository.

Reviewer B verified three things:
- R6's provider-failure rule and coding classification, as described in §8, match the R6 code.
- No supported-command path discards or replaces an attempt, and none contacts the provider without the correct
  sentence.
- No scientific artifact has changed since the R6 freeze commit `0a5a5e1`.

Revision 7 answers every finding, including the non-blocking ones.

## Reviewer A

| # | Severity | Finding (short) | Revision 7 |
|---|---|---|---|
| N1 | Blocking | The restore boundary had to read the unreadable quarantined file | The quarantined file is never read again. The restore boundary commits a quarantine record in its place (original path, the blob id it replaced, size, reason) (§13.4). |
| N2 | Blocking | An unreadable temporary file blocked every publication in its folder | It is renamed, which needs no read, and named with `sha256: "unreadable"`. Commits and snapshots carry a placeholder instead of its bytes (§6). |
| N3 | Blocking | R3's reason binding contradicted the §6 publications | Rewritten. A failure field's reason wins, with or without `acknowledges`. Otherwise a non-empty `acknowledges` means `durability_uncertain`. Otherwise `call_started` means `call_outcome_unknown`. A property test checks every §6 publication against R3 (§5, §19). |
| N4 | Blocking | A kill after the table was published, before its commit, was a dead end; a torn table could not be rebuilt; disclosure records conflicted with the no-replace rule | The table-freeze boundary is pending while `D/tables/` holds uncommitted files, and a rerun of `--freeze-table` completes it. Before the commit, a differing or torn file is quarantined and republished (§7, §13.3). Disclosure records are committed from memory, and their disk copy is written through the restore path (§13.1). |
| N5 | Non-blocking | The restore boundary could commit a torn ledger tail | A restore boundary adds only quarantine files and records (§13.1). |
| N6 | Non-blocking | Inherited `GIT_*` variables | The git environment is built from an allowlist, and every other `GIT_*` variable is stripped (§13.1, §19). |
| N7 | Non-blocking | A transient read error on a consumption-only `000001.json` became permanent | That file is never quarantined for a read error. The command refuses, and the next command re-evaluates (§13.4). |
| N8 | Non-blocking | Replay had no outcome for an unreadable entry | Rule R−1, `unreadable(n)`, refuses. Verification runs first (§5). |
| N9 | Non-blocking | Git children were not shielded from Ctrl+Break; setup ran outside the job; the worker's grandchildren outlived a timeout; §9.2 order | Git children use `CREATE_NO_WINDOW`. Every command process joins its job at startup, before setup. Each worker has a nested job. §9.2 step 1 now runs: job, then setup lock and setup, then lease (§8, §9.2, §15). |
| — | Pointer | §21 note 6 cited §6 | Now cites §7. |

## Reviewer B

| # | Severity | Finding (short) | Revision 7 |
|---|---|---|---|
| N1 | Non-blocking | The sandbox input chain was unspecified | R6's chain is carried verbatim: `sanitize_strings` → `safe_normalize` → `canonical_coding_payload`. It runs in the holder, and `execution_started` binds the executable's sha256. Seeds cover a fenced answer and an `old` with trailing newlines (§8, §19, §20). |
| N2 | Non-blocking | `_local_only_network` was dropped | Carried, with a stub test that sets a proxy variable (§17, §20). |
| N3 | Non-blocking | "Committed terminal copy" made every closed attempt protected | Protection now means a committed `completed` entry (§9.4). |
| N4 | Non-blocking | Abandon on a freeze that no longer verifies was a repairable stop | Treated like drift: the command refuses and names the files. Abandon covers only receipts (§9.3, §20). |
| N5 | Non-blocking | Boundary disclosure used gold before the drift check; gold-blind flags were dropped | Boundary records contain no gold. Partial results appear only in the table and score, computed by the scorer child after the drift check. `gold_loaded_during_collection: false` is carried (§12, §20). |
| N6 | Non-blocking | Attribution claims were overstated | R6's two attribution residuals are declared as carried (§1.2). G2 and the §19 oracle now say "classified exactly as R6 classifies". §8 is corrected. |
| N7 | Non-blocking | A collection finished only in a temporary file; unscored collected attempts had no commit | Temporary files are excluded from the protection check. A **collection boundary** commits the whole journal when replay first reaches `collected` (§9.4, §13.1, §13.3). |
