# G-ROUTE3 Phase A independent audit (attempt 2)

Verdict: READY
Run: groute3a-002-a90ef4e01edaf413
Scored seal: 9deda3e55818f9d639aa973f7aa616ef3a00a3b2fb8de8a9e735fc067d4a2fa2
run_created seal: ae80640ae63727d5e5b976b149ec1ee1336dc4800784dcd85c1ec7da359c7acf
Execution freeze binding: 0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465
Auditor: independent Claude auditor (fresh session), 2026-09-27

Completed seal: 1e0cef61bf0e147bd1ab580b14853e21296cc0c37472f07c1b8064d80326762f
Code and protocol: worktree C:\Users\marcu\Eidolon-groute3, HEAD 257126037d8d4988ea0b4ba81e8b2fc54411bd12 (main), clean before and after.
Data root audited: C:\Users\marcu\AppData\Local\Eidolon\research\g_route3 (read only).

## Method and safety

- The whole data root was copied with `shutil.copytree` to a temp folder under %TEMP%. `diff -r` and a per-file sha256 comparison showed the copy was identical to the real root. All replay, git and scoring work ran on the copy only. The copy was compared with the real root again at the end and then deleted.
- No launcher command was run. `Lifecycle.open()` was never called. No provider or model was contacted. The only child process run was the scorer (`tools/g_route3_scorer.py`, mode `phase_a_cells`), which is provider-free, and it ran against the copy.
- Every run used `python -B`. The repository was not modified: `git status` was empty before and after.
- Git inspection of `evidence.git` was done on the copy only, with `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL` set to the null device.

## 1. Evidence integrity — PASS

- **Run journal.** `replay_run` (tools/g_route3_journal.py) was run with the Phase A RunSpec from `g_route3_scorer.run_spec("A")`: 288 calls, 48 coding positions. The journal of `groute3a-002-a90ef4e01edaf413` replays to `completed`.
  - It has 676 entries: run_created 1, call_started 288, call_recorded 288, execution_started 48, execution_recorded 48, scoring_started 1, scored 1, completed 1.
  - There are no `.torn`, temp or foreign files.
- **Hash chain.** It was re-checked independently:
  - every `record_sha256` recomputes;
  - every `previous_entry_sha256` names the preceding seal;
  - entry 1 names the ledger head it claims (`9e12f32d…`, ledger entry 1).
- **Receipt.** The `completed` receipt equals {run_created seal, scored seal, freeze binding, guarded digest, calls 288}. `scoring_started.fact_prefix_sha256` equals the seal of the last fact entry.
- **Seals.** run_created, scored and completed match the three seals stated above.
- **Projections.** `receipt.json` equals the canonical bytes of the `completed` payload, and `score.json` equals the canonical bytes of the `scored` report. Neither file is committed, which is by design.
- **Evidence repository (on the copy).**
  - `git fsck --full --strict` is clean. The config matches §11 (fsync=all, gc.auto=0, logAllRefUpdates=always, autocrlf=false).
  - `refs/heads/evidence` has a linear history of 6 commits: root, consumption A1, terminal A1, consumption A2, collection A2, terminal A2. The reflog matches.
  - All 814 committed blobs are byte-identical to their files on disk (journals, ledger, root.json and disclosure records, with `disclosure/A/*` mapped to `D/disclosure/phase_a/*`).
  - Each terminal journal's committed set equals its on-disk set: 676 of 676 for attempt 2 and 130 of 130 for attempt 1.
  - The only uncommitted files are the two projections.
- **Ledger.** `phase_a/ledger` replays with `replay_ledger` to `ok`: 2 `attempt_consumed` entries, chained from the genesis seal `32379d99…`, and no ledger-level closures. Attempt 1 maps to `groute3a-001-deb591f4a575779c`, attempt 2 to `groute3a-002-a90ef4e01edaf413`. The verbatim sentences are in section 2.

## 2. Authorization — PASS

- **Sentences.** Each consumed sentence equals the expected string exactly:
  - `Authorize G-ROUTE3 phase A execution 0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465 attempt 1`
  - `Authorize G-ROUTE3 phase A execution 0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465 attempt 2`
- **Digests.** For both attempts:
  - `authorization_sha256` recomputes as `digest({sentence, phase, attempt})`;
  - `run_created.sentence_sha256` equals the sha256 of the ledger sentence;
  - `run_created.authorization_sha256` equals the ledger's;
  - the ledger's `run_created_sha256` equals the run's entry-1 seal.
- **Freeze binding.** `run_created.freeze_binding` and both ledger entries carry `0bfbe6b1…`. `_freeze_digest()` computed now from `EXECUTION_FREEZE_CANDIDATE.json` gives the same value.
- **Guarded files.** `run_created.guarded_files` lists 41 files: schedules A and B, corpora, gold, thresholds, G-ROUTE3 and G-ROUTE1 model bindings, prompt profiles, 27 tool modules, 3 conscious_agent modules and the execution freeze.
  - This is exactly the set `standard_guarded_files(D, "A")` produces today, and every digest is equal.
  - Every digest also equals the CRLF-normalized sha256 of the blob at commit 2571260 (`git show 2571260:<path>`).
  - `guarded_digest` recomputes to `309e94da…`.
  - Attempt 1's `run_created` carries the identical guarded files and model receipts.
- **Freeze manifest.** `python -B tools/g_route3_freeze.py` (verify only, no --write) returns `valid: true` with no reasons and status `READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION`. Its verification path does not touch the data root.
  - The manifest's `implementation_commit` is d20c689. The only change from d20c689 to 2571260 is the freeze file itself.

## 3. Protocol compliance — PASS

- **Calls.** There are exactly 288 call_started and 288 call_recorded entries, with positions 1..288 each exactly once and in order.
  - The call ids equal `schedule_a.json` (`verify_checked_schedule("A")`), and every fixture is Corpus A.
  - The whole entry sequence equals the one the schedule dictates: started, recorded, then execution_started and execution_recorded for each coding position.
- **Request bodies.** Every `call_started.request_sha256` equals `digest(request_body(fixture, scheduled))` rebuilt from the frozen inputs: 288 of 288. Every `call_started.guarded_digest` equals run_created's.
- **Provider evidence.** For all 288 calls:
  - the raw body's sha256 matches;
  - the body's `model`, `requested_model` and `returned_model` all equal the scheduled model;
  - the scheduled model equals the model binding for its tier;
  - `extract_output(body)` equals the stored raw output, and the raw-output sha256 matches;
  - `provider_contacted` is true, the adapter `error` is empty and `transport_failure` is empty.
  - `done_reason` is `stop` for 286 calls and `length` for 2 (positions 165 and 196). Both of these are conversation outputs cut at num_predict 350. They are graded as the model's `conversation_output_too_long`, with no infrastructure failure.
- **Model receipts.** The three receipts (qwen2.5:7b, qwen3:14b, qwen3.8:27b) have:
  - resolved equal to requested;
  - the pinned manifest and blob digests;
  - provider_version 0.34.3;
  - `silent_fallback` false;
  - the frozen generation configuration (retry_limit 0, output_repair_calls 0).

  `verify_model_receipts` returns valid. The endpoint is `http://127.0.0.1:11434`, and the transport contract reads "one POST /api/generate per call; max_retries=0; proxies stripped".
- **Coding executions.** All 48 coding positions have execution_started and execution_recorded.
  - Every `executable_sha256` matches its `executable_json`.
  - Every stored executable equals `derive_executable(fixture, raw_output)` re-derived now: 48 of 48.
  - Every `infrastructure_failure` is empty.
  - The worker's reported module digests all equal run_created's.
  - 35 candidates were rejected before the subprocess. I reproduced every one offline with the frozen pre-subprocess steps:
    - 6 were malformed JSON;
    - 3 were `SyntaxError` from a stray `}` inside `new`;
    - 26 were whitelist denials (`len`, `append`, `isinstance`, `range`, `any`, `enumerate`, `rstrip`, `find`, `endswith`, `set`).

    The whitelist is disclosed verbatim in each coding prompt, so under the frozen rules (QUALIFICATION_CONTRACT: "a whitelist denial … count[s] as failed evidence") these are the model's failures.
  - 13 candidates ran: 9 passed their tests and 4 failed them.
- **Failures.** There were no transport or infrastructure failures. `run_created.gold_loaded_during_collection` is false.
  - The collection path (`load_bound_inputs`) skips `gold_*` files, and no gold loader appears in lifecycle, launcher or worker.
  - The score reports `corpus_b_consulted: false`, and no Corpus B call exists.

## 4. Scoring reproducibility — PASS

- **Scorer child.** It was run on the copy (`{"mode":"phase_a_cells","data_root":<copy>,"run_id":…}`) and returned 72 cells with no error.
  - Its cells are equal to the `scored` entry's cells, compared as canonical bytes, and equal to `score.json`'s cells.
  - It loaded 19 modules, all guarded, with no drift from run_created.
- **In-process check.** An independent in-process run on the copy gave identical cells: `rebuild_records` (check_executables=True, no mismatches), then `attach_semantics` via `run_pinned`, then `qualify`.
- **Independent verdicts.** I re-implemented the verdict rule from QUALIFICATION_CONTRACT and thresholds.json myself:
  - the shape is exactly 2 fixtures × 2 repeats with 4 complete observations;
  - `qualified` needs 4 of 4 accepted, 4 of 4 semantic passes, 0 false-clean, 0 infrastructure failures and 0 model mismatches;
  - any other shape is `insufficient_evidence`.

  It reproduces all 72 sealed verdicts.
- **Thresholds.** The ones applied are those of `thresholds.json` (`G-ROUTE3-THRESHOLDS-R6`, digest-bound in run_created). The failure-rate bound for 0 failures in 4 is 0.527129.
- **Result.** 30 cells are qualified, 42 not_qualified and 0 insufficient_evidence.
  - Qualified: conversation 8 of 12, extraction 11 of 12, synthesis 7 of 12, planning 4 of 12 (large tier only).
  - Research and coding have 0 qualified cells.
- **Attempt disclosure.** The scored report's `attempt_disclosure` was recomputed with `partial_results` from the sealed attempt-1 records and equals the sealed value.

## 5. Grading spot-check (frozen rules only) — PASS

I inspected each record against `gold_a.json` and the frozen validators (g_route1_validators, g_route3_conversation and g_route3_semantics), using the normalized payload as the contract specifies.

- **Qualified-cell passes.** All are correct passes.
  - 287: conversation R1 small. The Answer is the gold option and Actions taken is `none`.
  - 66: extraction R2 large. The output equals the gold object.
  - 265: synthesis R2 mid. Roles, verbatim text, anchors and the conclusion `cause_unresolved` all match.
  - 158: planning R1 large. After the fence is removed, the plan equals gold.
  - 205: coding R4 large. The candidate is within the whitelist and its tests pass.
- **Failures.** All are correct failures.
  - 199: research R1 small. Citations are objects, not ids, and the model cites S2, which is about a different venue.
  - 222: planning R2 small. The output is a JSON array plus trailing prose, so it is malformed.
  - 196: conversation R2 large. The Answer is the wrong option (`yes, no approval is needed`), and the reply is over 600 characters.
  - 278: coding R2 small. `len` is not on the disclosed whitelist.
  - 4: coding R1 mid. The candidate returns `al.` instead of `a.l.`, so its tests fail.
- **False-clean cases.** All are genuinely wrong answers that were operationally accepted.
  - 211: conversation R2 mid. The Answer is `pending review and overdue`, but day 8 of 14 is within the window.
  - 157: planning R1 mid. It includes the excluded `delete_duplicate_photos` and a `storage_quota_unknown` uncertainty whose condition does not hold.
  - 45: research R2 mid. It omits `single_lineage_support`, although C2 rests on one lineage.
  - 233: extraction R3 small. The requester keeps the label (`Vendor Lindqvist Ltd`), which the prompt excludes.
  - 47: synthesis R4 mid. The conclusion is `insufficient_evidence`, but the hypothesis is disputed by counterevidence, so it should be `cause_unresolved`.
  - 21: research R3 large. It adds `single_lineage_support`, although C2 has two lineages. This is also the only record where the raw and normalized false-clean flags differ: the raw output is fenced and therefore rejected. Qualification correctly uses the normalized flag.
- **Deviations.** No record was found whose grading deviates from the frozen rules.

## 6. Disclosure and attempts — PASS (with the stated limitation)

- **Attempt 1.** The journal of attempt 1 (`groute3a-001-deb591f4a575779c`) replays to `closed` with the reason `operator_interrupt`. This is permitted, because its last fact entry is the clean call_recorded of position 52. That is a coding position whose sandbox had not yet started, and R3 permits `operator_interrupt` after any clean record.
  - It holds 130 entries: 52 call_started, 52 call_recorded, 12 execution_started and 12 execution_recorded.
  - It contains no scoring_started, scored or completed entry, and it has no projections.
- **Scored report.** The report's `attempt_disclosure` lists attempt 1 as outcome `closed`, reason `operator_interrupt`, with counts calls_started 52, calls_recorded 52, executions_started 12 and no in-doubt position.
  - It carries `optional_stopping_cannot_be_excluded: true` and `undeterminable_positions: []`.
  - Its partial cells are all 72 `insufficient_evidence`, from 52 observations. Attempt 2 is listed as `this_attempt`.
- **Disclosure records.** Records 000001 to 000005 are consistent with this. They are committed at each boundary and contain no gold. Record 000005 lists attempt 2 as completed.
- **Other attempts.** No other attempts exist:
  - the ledger holds 2 entries;
  - `phase_a/runs` holds exactly these 2 folders;
  - `phase_a/orphans` is empty;
  - there are no closure, orphan or quarantine paths in the evidence tree;
  - phase B has no ledger or runs;
  - there are no tables.
- **Order.** Attempt 2 was consumed only after attempt 1's terminal boundary had been committed: the evidence commit order is terminal A1, then consumption A2.
- **Whether attempt 1's stop could have been result-driven.**
  - *What the evidence shows:*
    - Attempt 1 contains no score of any kind. Its disclosure records at the stop contain no gold and no cells, so no recorded score existed when it stopped.
    - The guarded inputs, the freeze and the model receipts are identical across both attempts.
    - The raw outputs at positions 1 to 52 are byte-identical between attempts 1 and 2 (52 of 52), as are the request digests, the 12 stored executables and the 12 sandbox evidence records. The restart therefore changed no observation that attempt 1 had collected.
    - The provider timestamps are consistent with the stated reason. Attempt 1 ran 52 calls from 13:37:00Z to 14:00:36Z, about 27 s per call, which projects to roughly 2 h for 288 calls. Attempt 2 ran from 20:53:43Z to 22:40:49Z.
  - *What it cannot show:* whether anyone inspected attempt 1's raw outputs, or graded them outside the lifecycle, before stopping. The operator's stated reason, run duration, is recorded here only as a stated reason. Byte-identity at the 52 shared positions suggests seeded determinism, but that is not proven for positions 53 to 288. The protocol's flag "optional stopping cannot be excluded" is therefore correct and must remain on the attempt-1 row.

## 7. Other soundness checks — PASS

- **Attempt policy and completion.** The attempt policy of §9.3 was respected. Attempt 2 is the only `completed` Phase A attempt, and its terminal boundary is committed (548a0b6 contains the `completed` entry).
- **Synthetic flag.** `synthetic` is false in run_created.
- **§10 items 1–6.** The conditions that `--freeze-table` requires hold on the evidence I checked: completed and committed, the only completed attempt, ledger agreement, not synthetic, the same freeze and today's guarded digest, valid receipts, the fixed endpoint, consistent provider evidence, and re-derived cells equal to the sealed cells.
- **scoring_started.** `disclosure_inputs` names the ledger head `5a58d504…` (ledger entry 2) and attempt 1's terminal seal `dea64bea…`. Both match.
- **Timing.** The file timestamps in the data root agree with the provider timestamps: setup at 08:44 local, the lease and ledger at attempt-2 launch at 16:53 local, and the last evidence commit at 18:40:59 local, just after the last call.

## Notes (non-blocking)

1. **Stale lease text.** `D/.lease` names pid 45052 (`g-route3-r7`), and that process is not running. The lock is released by the OS, so this text is informational only.
2. **Fixed commit dates.** Evidence commits carry a fixed date (1700000000), as designed, so the repository orders events but does not time them. The timing above comes from provider `created_at` values and file mtimes.
3. **Corpus B reads.** The scorer child reads the bytes of `gold_b.json` and `corpus_b.json` to check guarded digests (`bind_inputs`). The holder also loads the Corpus B fixtures and schedule to build request bodies at startup. Neither affects Phase A cells: only gold A is paired with records, and there are no B calls. This is still a file read, not a "consultation".
4. **Construct residuals.** Coding results are dominated by the disclosed call whitelist: 26 of 48 coding outputs were denied, including builtins such as `len`. Research false-cleans come mostly from the uncertainty-code and citation rules. These are declared properties of the frozen construct, not grading errors, and they should be read with the declared limitations (pilot scale, upper bound 0.527 at 0/4).
5. **Planning tiers.** The 4 qualified planning cells are all on the large tier. The mid tier is false-clean in every planning cell: 16 of 16 accepted outputs failed.
