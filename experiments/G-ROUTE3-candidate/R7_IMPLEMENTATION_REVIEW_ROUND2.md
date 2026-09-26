# R7 implementation review, round 2

Date: 2026-09-26
Reviewed: the round-1 fixes (certified at commit `1790b01`, report committed in `5d90dfe`), against the accepted
design, rulings 1–11 and `R7_IMPLEMENTATION_OBLIGATIONS.md`.

The gate is the same safety-gated rule as round 1. **BLOCKING** means one of the following:
1. a repeated call;
2. best-of-N;
3. contact without the correct sentence;
4. a silent scientific or grading change;
5. a contradiction with an operator ruling.

**MUST-FIX** means a defect to fix before the freeze.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Journal, replay, recovery and evidence code, and whether the harness proves them | FINDINGS: 1 BLOCKING, 4 MUST-FIX, notes |
| B | Scientific integrity, authorization and attempts | FINDINGS: 0 BLOCKING, 5 MUST-FIX, notes |

Both reviews were read-only and made no provider contact.

## Operator ruling 12 (2026-09-26)

Reviewer A asked what Ctrl+C should do in a resumed attempt before its first new call. The operator chose
**"Exit, don't close"**:
- in a resumed attempt, an interrupt before the first new provider call exits without writing, and the attempt
  stays open;
- this includes the safe point before a pending sandbox run;
- closing a stalled attempt needs a declaration (ruling 11) or an abandon on a failing preflight;
- after the first new call, and throughout a fresh launch, interrupts still close as `operator_interrupt`.

This is recorded in the design (§7 and §21), in the candidate JSON, and in the code (`Lifecycle._interrupt`,
`collect(resumed=...)`).

## Reviewer A

| # | Class | Finding | Fix |
|---|---|---|---|
| A-N1 | BLOCKING (4) | `--resume` never compared the holder's in-memory inputs (schedules, fixtures, request bodies) or the launcher's compiled modules with the attempt's `run_created`. A resume after the inputs changed could send a different request under the old attempt. | `command_resume` compares `input_digests` and `loaded_source_digests()` with `run_created.guarded_files` before any call, and refuses on any difference. The scorer checks each record's rebuilt request body against the `request_sha256` sealed in its `call_started`; a mismatch makes the position undeterminable. Tests `test_resume_refuses_inputs_differing_from_run_created` and `test_scorer_marks_request_body_mismatch_and_unexecuted_coding`. |
| A-N2 | MUST-FIX | The pending-boundary step committed any uncommitted ledger or journal bytes found on disk, including bytes replay had rejected, and read them once. | Only entries replay accepted, and `.torn` files an accepted entry acknowledges, are committed. Each file is read again just before the commit; a disagreement refuses with `…retry_after_verification`. |
| A-N3 | MUST-FIX | (a) Snapshot files were read once. (b) A closure snapshot whose digest differed from `snapshot_digest` blocked every later command. (c) Files under `closures/` and `orphans/` whose names look like entries were treated as sealed in verification. | (a) Snapshot reads are checked by a second read. (b) The snapshot is committed as found and the disclosure row carries `snapshot_matches_recorded_digest`. (c) Files under `closures/` and `orphans/` are unsealed copies: quarantined and restored. Design §13.3 and §13.4 updated. |
| A-N4 | MUST-FIX | The harness could not prove recovery under kills: the status probe ran an unkilled prelude, kill points were a fixed range, power loss skipped recursive kills, one seed targeted a non-existent entry, and the stub provider could not see a send without a durable `call_started`. | `peek_attempt` is a pure disk read. Recovery runs only inside commands the harness may kill, either alone (`prelude`, what a refused command does) or with the action. Recursive kills use a per-operation kill probability and lose unflushed operations when `power` is set. The seed targets `000014.json`, the real terminal entry. The stub provider records a violation when no durable `call_started` precedes a send (from `FaultFs.pending`), and the oracle reports it. |
| F7 residue | MUST-FIX | Scoring did not check the interrupt flag before each derived publication. | `score()` checks it first and exits without writing (§7). |
| F14 residue | MUST-FIX | `OSError` and `subprocess.TimeoutExpired` still printed tracebacks. | The launcher reports them as plain refusals (exit 2). |

## Reviewer B

| # | Class | Finding | Fix |
|---|---|---|---|
| B-N1 | MUST-FIX | The Close sentence survived in the freeze manifest text, `QUALIFICATION_CONTRACT.md`, the status record, the design's §7 table, and as dead code (`command_close`). | All removed; the §7 table's declare column now states ruling 11. The duplicate `frozen_table_run` and the unused `table_run` parameter were removed. |
| B-N2 | MUST-FIX | In partial results, a coding call with no `execution_recorded` was graded as a model failure. | It carries `infrastructure_failure: execution_not_run`. In a complete run every successful coding call has an execution, so complete results are unchanged (differential byte-identical). |
| B-N3 | MUST-FIX | As A-N1, from the authorization side. | As A-N1. |
| B-N4 | MUST-FIX | Phase B partial results gave per-observation correctness but no routing decisions. | `partial_routing_decisions`: R6's gold-blind `decide`, pinned, against the frozen table, for the cases whose every tier has a determinable record. |
| B-N5 | MUST-FIX | An entry present as both `n.json` and `n.torn` was counted twice in individually sealed lower bounds. | One entry per number, preferring `n.json`, in both the holder's disclosure and the scorer (`_individually_sealed`). Test `test_individually_sealed_prefers_json_over_torn_twin`. |
| Notes | — | Undeterminable reasons were per row, not per position; cross-attempt identity compared positions across different schedules; the input comparison missed thresholds, prompt profiles and model bindings; ledger-closed rows dropped temporary-file records; the freeze writer's history check was vacuous on git failure; a freeze-table rerun with a different auditor or verdict after the commit returned `already_frozen`. | `undeterminable_reasons` per position; identity is `undeterminable` where the attempts' schedules differ; every guarded data file is compared; ledger-closed rows keep their temporary-file records; git failures refuse (`freeze_history_unreadable`); a different auditor or verdict is refused. |

## Verification

- `tools/g_route3_r7_tests.py`: 37 tests pass (4 new).
- `tools/g_route3_tests.py`: 80 tests pass, 19 superseded R6 tests skipped.
- `tools/g_route3_r7_differential.py`: PASS. Both Phase A differentials are byte-identical in cells, and Phase B is identical in the table cells, the routing lookup and the score.
- **Quick campaign (stride 7)** on the new harness. It found two defects, both now fixed:
  - **Interrupts at the three new scoring safe points.** These exited without writing, as specified, but did not report `interrupted_after_collection`. `score()` now tells `_run_to_end`, which reports it.
  - **A loop guard in the harness.** It mistook an orphan-folder refusal repeated across a kill for a stuck loop. It now resets after a kill or a successful command.

  After the fixes, the clean kill sweep is 150 of 150 completed, and all 18 gap seeds pass, including all 13 interrupt safe points. Every other quick-campaign case passed: kill sweeps, torn entries and ledgers, flush failures, environment cases and all 9 review seeds. There were 0 repeated calls and 0 sends without a durable `call_started`.
- The full certification campaign is rerun on the fixed code, and the results replace `R7_CERTIFICATION_REPORT.json`.

## Next

1. Commit these fixes.
2. Run the full certification campaign on the fixed code.
3. Then a fresh confirmation review of the round-2 fixes.

## Confirmation review (2026-09-26)

Two fresh read-only reviewers checked the round-2 fixes at `a05d568`. Neither contacted a provider; both ran their
experiments only in temporary folders, with stub or synthetic providers.

| Reviewer | Verdict |
|---|---|
| A (journal, recovery, evidence, harness) | 0 BLOCKING, 1 MUST-FIX, 4 notes. Confirmed A-N1, A-N2, A-N3a/c, every A-N4 change, F14 and ruling 12, which was reproduced end to end, including the pending-sandbox safe point. Showed that the durable-intent oracle fires. |
| B (science, authorization, attempts) | 0 BLOCKING, 1 MUST-FIX, 4 notes. Complete-run grading is unchanged; B's own differential passed. Only launch sentences reach the provider, rulings 11 and 12 hold, and every Close remnant is gone. |

| # | Class | Finding | Fix |
|---|---|---|---|
| A MF-1 | MUST-FIX | `snapshot_matches_recorded_digest` was wrong in three ways. The committed disclosure said `None`, because it was computed before the snapshot commit. Torn-acknowledgement closures, which record no digest, said `False`. Any later file in the run folder flipped the flag, which after `--freeze-table` would make Phase B refuse permanently. | The flag is decided by the disclosure committed with the closure's own boundary; before that commit it is computed from the files as found, which are exactly what that commit adds. Every later disclosure reuses the committed value. A closure without a recorded digest says `no_digest_recorded`. Design §13.3 updated. Test `test_snapshot_flag_is_fixed_by_the_closure_commit`. |
| B MF-1 | MUST-FIX | Phase B partial observations reported an infrastructure failure (`execution_not_run`, transport, sandbox) as `correct: false`, and partial routing decisions routed such cases. | Each observation carries `infrastructure_failure`, and `correct` is null when it is set. Cases with any infrastructure-failed tier are excluded from `partial_routing_decisions`, and each decision names its record sources. |
| A N1 | NOTE | An interrupt during the scorer child still let `scored` be published. | The flag is checked again just before the derived publication. |
| A N2, B note 3 | NOTE | Coverage: no case for a resumed attempt's pending-sandbox safe point, or for closing after the first new call; no proof the durable-intent oracle fires; orphan clearing never ran under kills; design §19 and §20 did not mention ruling 12. | New unit tests for each. A new campaign section, `resumed_interrupts`, interrupts resumed attempts at every check from a plain and from a coding position: 16 cases pass. Orphan clearing runs under the harness's killable filesystem. §19 and §20 updated. |
| A N3 | NOTE | Orphan temporary files and quarantine files were committed after a single read. | They are read a second time too. §13.3 says so. |
| A N4 | NOTE | An individually sealed entry was not checked against its file number. | It must carry its own number. |
| B note 1 | NOTE | Partial routing decisions had no source label. | Added (as B MF-1). |
| B note 2 | NOTE | Cross-attempt identity was keyed only on the schedule digest. | Keyed on each position's sealed `request_sha256`, which covers the model, the prompt and the corpus. |
| B note 4 | NOTE | The freeze writer skipped an unparseable historic freeze version, and its git calls had no timeout. | It refuses (`freeze_history_version_unparseable`). The git calls time out after 120 s. The real history passes. |

Verification after these fixes:
- R7 suite: 41 tests pass.
- R6 suite: 80 tests pass, 19 skipped as superseded.
- Differential: PASS.
- A targeted quick campaign is clean: clean kills (150), torn ledger, 21 gap seeds, 9 review seeds and 16 resumed-interrupt seeds.
  - One resumed-interrupt oracle was wrong at first. It required an unchanged journal, but a sandbox run that finishes before the interrupt legitimately adds its execution entries. It was corrected, and all 16 cases pass.

The full certification campaign reruns on this code next.
