# R7 implementation status

This record sets out how the R7 implementation meets the accepted design (`R7_LIFECYCLE_DESIGN.md`, accepted under
the safety-gated rule; see `R7_DESIGN_REVIEW_ROUND8.md`) and `R7_IMPLEMENTATION_OBLIGATIONS.md`. It is the checklist
for the fresh implementation review.

No provider generation calls have been made, and there is no execution freeze. The certification campaign has run
only in part; see `R7_CERTIFICATION_REPORT.json`, which is provisional.

## Modules

| Module | Role (design section) |
|---|---|
| `tools/g_route3_platform.py` | No-replace write-through rename, directory flush, OS lease lock at 2^40, kill-on-close job, child creation flags, `run_pinned` (§8, §14, §15) |
| `tools/g_route3_fs.py` | The single choke point for every filesystem operation and every child process; the §14 publication protocol; the §4.4 reading rule |
| `tools/g_route3_journal.py` | Canonical entries and seals, and pure replay of runs and ledgers: R−1 to R17, tear prediction, R3 grammar and closed-reason function, per-file protection (§4, §5, §9.1) |
| `tools/g_route3_evidence.py` | The private evidence repository: allowlisted git environment, add-only commits, batched exact blob I/O (§13) |
| `tools/g_route3_lifecycle.py` | J8 command shape, verification and restore (§13.4), recovery (§6), pending boundaries (§13.3), collection (§8), scoring, and the commands (§7) |
| `tools/g_route3_worker.py` | The sandbox worker, running R6's coding classification verbatim, and the shared executable derivation |
| `tools/g_route3_scorer.py` | The scorer child, the only process that reads gold: R6's `collect_evaluation`, `attach_semantics`, `qualify`, `score` and `build_table` on R6-shaped records |
| `tools/g_route3_launch.py` | Launcher v4 with the §7.1 sentences |
| `tools/g_route3_campaign.py` | The certification campaign harness (§19) |
| `tools/g_route3_r7_tests.py` | The quick deterministic suite |

**R6 code.** R6's `g_route3_runner.py` still provides the verbatim functions R7 reuses. Its authorized execution path now
refuses (`r6_authorized_path_superseded_by_r7_lifecycle`). Its synthetic path remains, so the R6-versus-R7
comparisons can run.

## Evidence so far

- **Quick R7 suite:** 31 tests pass.
- **R6 suite:** the science tests all still run. The R6 lifecycle tests that exercised the superseded authorized path
  or launcher v3 are skipped, and each skip names the R7 counterpart. One new test asserts that R6's authorized path
  refuses.
- **R6-versus-R7 comparisons (A-O12 and B-O1)**, each on identical synthetic outputs:
  - **Phase A, 288 mixed outputs** (correct, wrong, fenced, malformed and non-hashable): the 72 cells are
    byte-identical.
  - **A second Phase A plan,** yielding 32 qualified and 40 not qualified cells: identical.
  - **Phase B end to end:**
    - R7 froze the table with `--freeze-table`, then passed the §10 gate and completed Phase B;
    - the Phase A cells and routing lookup are identical;
    - the Phase B score is identical in every field except `table_sha256`, which differs by design because R7's
      table carries the `r7_binding` block.
- **Crash campaign (provisional),** on a four-call schedule with stub provider, worker and scorer:
  - kill campaigns: clean, power loss, transport failure, and a full every-operation sandbox-failure campaign of 456
    cases;
  - torn journal and ledger entries, failed flushes, stale git locks, transient read errors, and inherited `GIT_*` and
    proxy variables.

  There were no J12 violations, no unmatched temporary-file deletions, and final verification passed in every case.
- **Measured recursion bands** at the pinned budget (C-O2): JSON nesting up to 991, syntax-tree binary chains up to
  2,977 terms. The freeze records them.

## Obligations

| # | Status | Where |
|---|---|---|
| A-O1 | Done | `execution_started.executable_json` and `executable_sha256` (lifecycle `_execute`); R3 checks the sha only (journal); the scorer re-derives with the same `run_pinned` split (`scorer.rebuild_records`) |
| A-O2 | Done | `fs.list_names` and `fs.read_bytes` return None only on not-found; every walk raises `Unreadable` (`_walk_error`) |
| A-O3 | Done | `_rename_torn` re-reads before renaming; `sealed_protective` counts sealing `.torn` files; `_publish_closed` refuses for protected attempts |
| A-O4 | Done | Fixed names `QUALIFICATION_TABLE.json` and `QUALIFICATION_AUDIT_DOCUMENT`. Before the commit, a torn copy is quarantined and republished, an intact different one is refused, and other files are quarantined. After the commit, verification quarantines extras. |
| A-O5 | Done | §10.8 compares disclosure rows, which carry no commit ids or restore log |
| A-O6 | Done | `command_export` takes only the lease and uses controlled git |
| A-O7 | Done | `verify_evidence` quarantines an uncommitted `n.torn` whose `n.json` is committed |
| A-O8 | Partly | `-c safe.directory=<evidence.git>` on every git call. The case of a data root owned by Administrators is not yet run (campaign gap). |
| A-O9 | Done | `EvidenceRepo.commit` flushes `refs/heads` after `update-ref`; a failure raises `NotDurable` |
| A-O10 | Done | `collect` runs `sync()` as soon as the state reaches `collected`, before the scorer |
| A-O11 | Done | `attempt_closed_at_ledger.snapshot_digest`; `scoring_started.disclosure_inputs.orphans_cleared` |
| A-O12 | Done | See the comparisons above |
| A-O13 | Done | `spawn_worker` and `spawn_scorer` use `sys.executable` and `child_env()` (the holder's environment after proxy stripping) |
| A-O14 | Done | Journal grammar; test `test_acknowledges_only_on_closed_and_derived` |
| A-O15 | Done | Disclosure records carry `evidence_head_before` |
| B-O1 | Done | `scorer.score_run` calls R6's functions verbatim on R6-shaped records |
| B-O2 | Done | The scorer recomputes the guarded digest (corpus, gold, thresholds, table and code) against `run_created` before reporting |
| B-O3 | Done, with a sentence **added to §7.1** for the review to confirm | `command_close` and the sentence `Close G-ROUTE3 phase <P> attempt <n> without further calls`. Directory errors count as unreadable. The freeze writer follows J8 (`data_root_refusals`). |
| B-O4 | Done | Replay is pure; the fixture-dependent check runs in the scorer after the drift check |
| B-O5 | Done | Disclosure rows carry `temporary_file_records`, labelled `source: temporary_file` |
| B-O6 | Done | A coding position whose provider call failed gets R6's `_failed_coding_evidence` in partial cells, as R6 would for an empty output |
| B-O7 | Done | A torn audit copy is one that differs from the digest recorded in an intact on-disk table |
| B-O8 | Done | `R7_MODULES` are guarded (`standard_guarded_files`) and listed as freeze artifacts |
| B-O9 | Done | The literal data root is in `QUALIFICATION_CONTRACT.md` and `g_route3_freeze.DATA_ROOT` |
| B-O10 | Partly | The table keeps R6's `TABLE_SCHEMA`, which `verify_table` requires, and adds an `r7_binding` block instead of a new schema version. `phase_b_attempts` uses the §12 rows. `operator_confirmation` is carried. |
| C-O1 | Done | `platform.run_pinned` (64 MiB stack, limit 1000, fresh thread, exception class preserved) |
| C-O2 | Done | `freeze.measure_recursion_thresholds` |
| C-O3 | Done | The worker reports `module_digests`, and the holder compares them with `run_created.guarded_files` |
| C-O4 | Done | A mismatch is recorded as `sandbox_worker_failure:guarded_module_drift` |
| C-O5 | Done | One `derive_executable` is shared by the holder and the scorer |
| C-O6 | Done | Positions whose re-derivation mismatches are disclosed as `undeterminable_positions` |

## Also run since the first campaign pass

These gap seeds were added and pass (`g_route3_campaign.py`, `gap_seeds`):
- an unreadable committed entry, an unreadable tail entry and an unlistable journal: each refuses, then recovers
  once the file can be read again;
- a damaged `root.json`: restored;
- two concurrent first setups: one intact data root;
- an interrupt at each of 11 safe points: `operator_interrupt` before `collected`, completion after it.

The quick suite adds two platform tests:
- a killed holder leaves no live child;
- the near-limit recursion bands give identical derivations and classifications from different caller depths and in
  two processes.

The launcher reports refusals plainly: exit code 2, or 3 for a declared exception.

## Known gaps

- **Every-operation sweeps:** the stride-1 kill campaigns for the clean, power-loss (all and subset) and
  transport-failure scenarios are running for certification. Earlier they were sampled at stride 7.
- **A-O8:** a data root owned by Administrators has not been run. It needs an elevated account, and the reviewers
  may confirm it by inspection.
- **Real console Ctrl+C and Ctrl+Break during the sandbox:** covered only by the design-review probe (the worker
  and scorer start with `CREATE_NO_WINDOW`). There is no harness case.
- **Clock step while the lease is held:** not applicable. The OS lock does not depend on time.
- **No POSIX run.** The governed run executes on Windows.
