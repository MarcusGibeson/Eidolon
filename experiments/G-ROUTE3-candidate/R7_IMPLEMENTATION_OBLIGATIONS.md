# R7 implementation obligations

Source: design review round 8, which was safety-gated (see `R7_DESIGN_REVIEW_ROUND8.md`).

These findings did not block the design under the operator's gate. The implementation of R7 must satisfy every
one of them. The implementation review checks each item, and the certification crash campaign runs each listed
case.

Items marked **(in rev 9)** are already reflected in the design text. The design governs if it conflicts with
this list. A conflict is itself a finding.

## From Reviewer A (journal, replay, recoverability)

| # | Obligation | Certification case |
|---|---|---|
| A-O1 | **(in rev 9)** `execution_started` stores `executable_json`, and the worker runs exactly those bytes. R3 checks only that sha256. The scorer checks that the stored executable equals the re-derived one, after the drift check, at a pinned recursion budget. | Nesting inside the depth-sensitive window. Guarded-code drift during a live attempt: it must refuse as drift, never become an integrity failure. |
| A-O2 | Only a confirmed not-found means `absent` or "missing". Every directory-listing or stat error is an R−1 refusal. | Access denied when listing `journal/`, `runs/`, `ledger/` and `tables/`. |
| A-O3 | Re-read and compare before renaming a file to `.torn`. A `.torn` whose bytes seal counts as protective (§9.4). A journal-level `closed` is refused for a protected attempt. | A read-corruption injector, separate from file damage. |
| A-O4 | Table and audit-copy file names are fixed, not derived from a digest. Before the commit, any table-shaped or audit-shaped file that is not the rebuilt bytes makes the command refuse. The rerun may reuse the audit copy already in `D/tables/`. §13.4 gets a row for extra files in `D/tables/` after the commit. | A different audit document on the rerun; a lost original audit document. |
| A-O5 | **(in rev 9)** §10.8 excludes commit ids and the restore log. | Phase B precondition 8 on a real table. |
| A-O6 | `--export-evidence` is read-only: it takes the lease and the controlled git environment, and skips verification, recovery and commits. | Export while a file is unreadable. |
| A-O7 | Verification quarantines an uncommitted `n.torn` whose number has a committed `n.json`. | The twin case: damage between J8 step 2 and step 4. |
| A-O8 | Pass `-c safe.directory=<D/evidence.git>` to git, or check ownership at preflight. Verify first that git 2.40.1 accepts this setting from the command line. | `D` owned by Administrators. |
| A-O9 | "Consumption committed" requires both `update-ref` and a successful flush of the ref directory. | The ref-directory flush fails after `update-ref`. |
| A-O10 | Commit the collection boundary as soon as the state reaches `collected`, before the scorer starts. | A kill during scoring. |
| A-O11 | Bind the closure-snapshot digest in `attempt_closed_at_ledger`. Name orphan snapshots in `scoring_started`. | Tampering with a snapshot after its commit. |
| A-O12 | The scorer rebuilds R6's record shape exactly. `transport_failure` and `infrastructure_failure` map onto R6's `infrastructure_failure` for partial cells. | **A differential test.** Take identical synthetic outputs, including surrogate, fenced, trailing-newline and failure cases. R6 `_collect` plus its report path must give byte-identical cells and score to the R7 scorer. |
| A-O13 | Pin the worker to the holder's `sys.executable`, and give it the holder's environment after proxy stripping, not git's allowlist. | Host-failure attribution matches R6. |
| A-O14 | R3 forbids a non-empty `acknowledges` on any kind other than `closed` and the derived entries. | A mutation test. |
| A-O15 | The Phase B terminal disclosure names the evidence head **before** its own commit. | — |

## From Reviewer B (science, authorization, attempts)

| # | Obligation | Certification case |
|---|---|---|
| B-O1 | **High priority.** The scorer calls R6's `qualify`, `g_route3_validation.score` and `g_route3_validation.decide` verbatim, on records with R6's exact shape. That shape includes `returned_model`/`model`, `infrastructure_failure`, `coding_execution_evidence`, `normalization`, `raw_output` and the operational validations. | The A-O12 differential test. |
| B-O2 | **High priority.** Before publishing `scored`, the scorer verifies every input's digest (corpus, gold, thresholds, table and guarded code) against `run_created`. This carries R6's `post_run_dependency_drift`. | Drift during scoring. |
| B-O3 | An attempt in progress whose journal files cannot be recovered byte for byte is closed by a supported command, never resumed. Directory-listing errors count as unreadable (see A-O2). The freeze writer follows J8 and refuses on unreadable files. | A lossy copy that drops a trailing `call_started`: the attempt must close, not resume. |
| B-O4 | **(in rev 9)** Replay stays pure. The fixture-dependent check runs in the scorer, after the drift check. | Corpus drift during an attempt: it must refuse as drift. |
| B-O5 | Disclose the content of `.orphan-tmp` files (output identity, partial cells), labelled as coming from a temporary file. | A kill after the temporary file for position N is flushed. |
| B-O6 | State how a coding position whose provider call failed (no sandbox run) appears in partial cells. | A provider error at a coding position. |
| B-O7 | Define "torn" for the audit copy: it differs from the audit digest recorded in an intact on-disk table. | A truncated audit copy before the commit. |
| B-O8 | Add the new R7 modules (journal, worker, scorer, launcher) to the guarded paths and to the freeze. | Drift in the scorer module. |
| B-O9 | Pin the resolved path of `D` literally in the qualification contract. | An overridden `%LOCALAPPDATA%` at the first freeze. |
| B-O10 | Text fixes: §20's "no candidate can reach" wording (see §1.2); a producer for the `journal_missing` reason; R6's `operator_confirmation` in the §12 disclosure; the schema version for the Phase B score's `phase_b_attempts` and for the table; binding snapshots in `scoring_started` (see A-O11). | — |

## From the revision-9 confirmation review

| # | Obligation | Certification case |
|---|---|---|
| C-O1 | **(in rev 9)** One shared `run_pinned` wrapper (fresh thread, 64 MiB stack, recursion limit 1000, fixed entry, exception class preserved) for every function that handles model output, in the holder, the worker and the scorer. | Near-limit bands from several caller depths and in two processes. Every exception class R6's attribution distinguishes. |
| C-O2 | **(in rev 9)** The freeze records the thresholds measured at the pinned budget, for JSON nesting and for syntax-tree chain length. | Threshold measurement run at certification. |
| C-O3 | **(in rev 9)** The worker reports the digests of the guarded modules it loaded, and a mismatch refuses as drift. | A worker that loads a drifted module. |

## Also required, from earlier rounds

Every seed listed in §19 of the design, and every row in §18.
