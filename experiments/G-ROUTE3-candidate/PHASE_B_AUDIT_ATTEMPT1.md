# G-ROUTE3 Phase B audit, attempt 1

Verdict: READY
Run: groute3b-001-3ade26dbf80c8774
Scored seal: bd179edb548a260af8110787321b45270cfa65e6a02a8cc2986d681410ad3f2a
run_created seal: 7ceb57fc8fc2fb7a6ef1d7e5bba6ec7b76e34a1d63bad73e3899c8ccd328bdb1
Table: adc5411f1300c8e3dd5e3f2349699c2e9755d73f89fa0e0870d1d70d9f6bf0ab
Execution freeze binding: 0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465
Auditor: independent Claude auditor (fresh session), 2026-09-28

Scope: the Phase B result as sealed in D = C:\Users\marcu\AppData\Local\Eidolon\research\g_route3, judged
against the frozen protocol and code in worktree C:\Users\marcu\Eidolon-groute3 at 27189a8 (main; origin/main
is also 27189a8). READY means the result was produced correctly under the frozen protocol and may be reported
as such. It is not an endorsement beyond that.

Method: I hashed every file under D (2417 files), copied D to %TEMP%, and ran everything that needed execution
on the copy only. That covered replay, git fsck, the scorer child and rescoring. I did not run the launcher,
call Lifecycle.open() or contact any provider. All code ran with `python -B`. When I finished, I re-hashed D and
it was byte-identical to the first hash, with no file newer. `git status` in the worktree was clean. I deleted
the temp copies. Where the frozen code checks something, I also checked it with my own code where that was
practical: the chain walk, routing, gate values, Clopper-Pearson bounds and generalization labels.

## 1. Evidence integrity — PASS

- **Phase B journal.** Replay (`replay_run` with the Phase B RunSpec from schedule_b and corpus_b) gives
  `completed`, with no torn entries, temporary files or orphans. The journal has 340 entries: run_created, 144
  call_started, 144 call_recorded, 24 execution_started, 24 execution_recorded, scoring_started, scored and
  completed.
  - My own chain walk agrees. Every file is canonical JSON, every record_sha256 recomputes, and every
    previous_entry_sha256 links to the entry before it. Entry 1 links to the Phase B genesis seal (root_id
    e5ad48f0…), because the ledger was empty at launch.
  - The seals are exactly the three stated: run_created 7ceb57fc…, scored bd179edb…, completed 67658b65….
- **Evidence repository** (copy). `git fsck --full --strict` is clean. The repository config holds the §11
  settings. `refs/heads/evidence` has a linear history of 10 commits:
  - root;
  - A1 consumption and terminal;
  - A2 consumption, collection and terminal (548a0b6e…);
  - table freeze (51c43c2c…);
  - B consumption (46b26188…, which adds only run B `000001.json`, ledger 000001 and disclosure B/000001, so it
    precedes every call);
  - B collection (af85fa61…, entries 2–337);
  - B terminal (6e6428a9…, entries 338–340).
- **Committed copies against disk.** All 1160 committed files equal their disk copies byte for byte. The Phase B
  journal's file set equals the committed set exactly. The only uncommitted files on disk are `.lease` and the
  two score.json and receipt.json projections of each completed run.
  - score.json equals the canonical bytes of the `scored` report.
  - receipt.json equals the canonical bytes of the `completed` payload.
- **Phase B ledger.** It replays `ok` with exactly one `attempt_consumed` (attempt 1) and no closures. My own
  chain walk agrees.
- **Tables.**
  - `D\tables\QUALIFICATION_TABLE.json` equals its committed copy, the worktree file, and `git show
    27189a8:experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json`, byte for byte (99995 bytes).
  - `verify_table` returns valid. The table_sha256 is adc5411f….
  - The audit copy equals its committed copy and `PHASE_A_AUDIT_ATTEMPT2.md`, byte for byte. Its digest
    7d92b199… equals `table.audit.document_sha256`.
- **r7_binding.** It names Phase A attempt 2's run_created ae80640a… and scored 9deda3e5…, with source.run_id
  groute3a-002-a90ef4e01edaf413. Its terminal_evidence_commit 548a0b6e… holds A2's terminal entry and is an
  ancestor of the head.
- **Phase A attempts.** The Phase A ledger replays `ok` with 2 attempts. Attempt 1 is `closed`
  (operator_interrupt). Attempt 2 is `completed`, and it is the only completed Phase A attempt.

## 2. Authorization and preconditions — PASS

- **Authorization.** The consumed sentence is exactly:
  `Authorize G-ROUTE3 phase B execution 0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465 table adc5411f1300c8e3dd5e3f2349699c2e9755d73f89fa0e0870d1d70d9f6bf0ab attempt 1`.
  - `run_created.sentence_sha256` is the sha256 of that sentence.
  - `authorization_sha256` recomputes and equals the ledger entry.
  - The ledger entry names run B and the run_created seal.
- **run_created bindings.** run_created binds:
  - freeze_binding 0bfbe6b1…;
  - table_sha256 adc5411f…;
  - phase_a_run_id groute3a-002-a90ef4e01edaf413 and phase_a_terminal_commit 548a0b6e… (equal to the table's);
  - schedule_sha256, equal to the digest of the checked schedule (e50011b1…);
  - synthetic false and gold_loaded_during_collection false;
  - endpoint `http://127.0.0.1:11434` and the root_id.
- **Guarded files.**
  - All 42 guarded digests match the worktree at 27189a8 and D. This includes `D/tables/QUALIFICATION_TABLE.json`
    and `execution_freeze`.
  - guarded_digest recomputes, and every call_started carries the same guarded_digest.
  - The worker's module digests in all 24 execution_recorded entries match.
  - The re-run scorer child loaded 22 modules, and none drifted.
- **Freeze.** `python -B tools/g_route3_freeze.py` (verify only) returns `valid: true`, no reasons, status
  READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION. The runner's `_freeze_digest()` is 0bfbe6b1…. The only
  changes from the freeze's implementation commit d20c689 to 27189a8 are the freeze file, the table and the
  Phase A audit.
- **§10 preconditions**, as far as the evidence shows:
  - (1) and (2): A2 is completed with its terminal commit, and it is the only completed Phase A attempt.
  - (3): A2's run_created attempt, authorization and sentence digests equal its ledger entry, which names its
    seal.
  - (4): A2 is not synthetic and ran under the same binding. Its 41 guarded files match today's, and its set is
    B's set minus the table. Its call guards are constant, and its endpoint is the fixed one.
  - (5): For all 288 A2 calls, the body digest, model, output extraction and request digest against the
    schedule are consistent.
  - (6): The frozen scorer child in `phase_a_cells` mode, run on the copy, re-derives cells equal to both A2's
    scored cells and the table's cells.
  - (7): verify_table passes, and the table's seals and run equal A2's. The terminal commit is valid. The audit
    document reads READY, names the run and both seals, and is not a frozen artifact.
  - (8): The table's phase_a_attempts equal the committed A disclosure record on all common fields.
  - (9): The table has exactly one version in main's first-parent history, which is 27189a8, the tip.
  - (10) and (11): shown above.

## 3. Protocol compliance — PASS

- **Calls.** There are 144 call_started and 144 call_recorded entries. Positions 1–144 each appear once, in
  strict order: started k, then recorded k, then an execution pair for coding positions, then the derived
  entries. The call ids equal schedule_b.
- **Corpus.** Every call is for a B- fixture: 48 fixtures, 48 calls per tier, repeat 1, seeds 44001–44471.
  Corpus A was not re-run.
- **Request and provider evidence.**
  - Every request_sha256 equals `digest(request_body(fixture, row))`, rebuilt from the frozen code.
  - The model options are the bound generation configuration: stream false, think false, the per-call seed.
  - For every call, requested model = scheduled model = returned_model = the `model` in the provider body.
  - raw_body_sha256 recomputes.
  - `extract_output(body)` equals the stored raw output, and raw_output_sha256 recomputes.
  - provider_contacted is true on every call. transport_failure and error are empty on all 144 calls.
- **Model receipts.** All 3 receipts match model_bindings.json: manifest and blob digests, provider 0.34.3,
  requested = resolved, silent_fallback false, and an identical generation configuration.
- **Coding.** All 24 coding positions are executed. Each stored executable_json equals `derive_executable`
  (the pinned sanitize → safe_normalize → canonical_coding_payload chain) re-run on the recorded output. There is
  no infrastructure_failure. Candidate errors are 16 model-attributed rejections (ValueError 13, SyntaxError 2,
  JSONDecodeError 1); the other 8 ran.
- **Gold isolation.**
  - run_created records gold_loaded_during_collection false.
  - The holder's `load_bound_inputs` skips `gold_*` files.
  - The scorer child is the only gold reader.
  - Routing sees only `runtime_view`. Its whitelist is enforced by `assert_gold_blind`, and its fields are the
    normalized payload, the operational validation, infrastructure status and coding evidence.
- **Diagnostic calls.** 23 routing calls and 121 diagnostic calls is what the frozen protocol specifies.
  - DESIGN.md "Phase B provider contact" says every Corpus B fixture is observed on all three tiers, that only
    the observations the router would consume count as routing calls, and that the rest are declared
    diagnostic calls, used only for false-negative qualification and never as routing results.
  - SCORING_CONTRACT.md requires reporting routing and diagnostic calls separately.
  - `validation.decide` routes gold-blind from the recorded outputs and the frozen table before gold is
    attached.
  - The 23 routing calls are the 22 start-tier observations plus 1 escalation. 144 − 23 = 121.

## 4. Scoring reproducibility — PASS

- **Rescoring.**
  - In process, `rebuild_records` over the fact entries gave 144 records with no mismatch.
    `g_route3_validation.score` on those records with the frozen table reproduced the report. With the same
    wrapper fields the scorer adds, the report equals the `scored` payload exactly: decisions, metrics, gates,
    generalization, statuses and disclosure.
  - Separately, I ran the frozen scorer child (`tools/g_route3_scorer.py`, mode score_run) against a second
    copy truncated to entry 338 (`scoring_interrupted`). There was no error. Its report equals the sealed one,
    and re-sealing the scored envelope with it gives bd179edb…, the stated seal.
- **My own re-derivation.** From the gold-free fields, the table's cells and the frozen triggers, my routing
  loop reproduces all 48 decisions: outcome, final tier, escalation flag and tiers contacted. Per-observation
  correctness is the frozen evaluator's hard_gate_pass. From these I get:
  - 12 evidence_only, 14 no_qualified_model, 22 stopped, 0 escalation_exhausted;
  - 22 qualified-start cases, 20 correct stops and 2 unsafe stops.
  - The unsafe-stop rate is 2/22 = 0.090909 against a maximum of 0.1, evaluable because 22 ≥ 10.
  - The correct-stop rate is 20/22 = 0.909091 against a minimum of 0.6, evaluable because 22 ≥ 10.
  - There are 0 unqualified terminal results. Denominators are 48 cases and 144 observations.
  - Primary is PASS.
  - Escalated stops number 1, below the minimum of 5, so secondary is NOT_TESTABLE.
  - Generalization labels: 21 generalized, 9 false_positive, 6 false_negative, 36 consistent_unqualified. These
    equal the report's.
- **Thresholds.** The applied thresholds equal thresholds.json exactly: max 0.1, min 0.6, both evaluability
  minimums 10, secondary minimum 5 escalated stops with max 0.1 unsafe and at least 1 correct.

## 5. Grading and routing spot-check — PASS (no deviation from the frozen rules)

- **Unsafe stop 1: B-CONV-R1-1** (conversation, R1).
  - The table qualifies small, mid and large; in Phase A, small went 4/4 with 2 fixtures. The router started at
    small, the output was accepted and no trigger fired, so it stopped.
  - The output was `Answer: P3` / `Actions taken: none`. Its prose wrongly claims 1,150 g is heavier than
    1.2 kg = 1,200 g.
  - The gold answer is P1, and P3 is gold's first listed incorrect output. The frozen conversation frame grades
    the Answer line against the gold option, which gives `answer_mismatch`.
  - This is semantically wrong. Mid made the same error; large was correct.
- **Unsafe stop 2: B-CONV-R3-2** (conversation, R3).
  - The table qualifies small and large; in Phase A, small went 4/4. The router started at small, the output
    was accepted, and it stopped.
  - The output was `Answer: passed`, while the prose itself describes the audit checksum failure. The gold is
    "partly: the audit database failed with a checksum mismatch", so the grade is `answer_mismatch`.
  - This is wrong. Mid and large were correct.
- **Non-correct qualified-start cases.** The 2 non-correct cases are exactly these two stops. All 22
  qualified-start cases stopped, and none was exhausted.
- **The single escalation: B-EXTRACT-R2-2** (extraction, R2; small, mid and large qualified).
  - Small omitted `unit_price` and was rejected with `extraction_schema_mismatch`. That rejection is
    operational and gold-free: it checks against the schema the model was given.
  - The router escalated to mid, the next qualified tier. Mid's output was accepted and matches gold exactly.
    The stop is correct.
- **Correct stops sampled:**
  - B-CONV-R1-2, small: `Answer: 3`, gold 3.
  - B-EXTRACT-R3-1, mid: the JSON equals gold, account_compliant false.
  - B-SYNTH-R2-1, mid: 4 statements with verbatim text and correct roles, conclusion cause_established, equal to
    gold.
  - B-PLAN-R3-1, large: the output was fence-normalized. Its steps, order, depends_on, evidence_ids,
    uncertainties, claims_completed false and requested_authority [] all equal gold.
- **No-qualified-model cases:**
  - B-CODE-R1-1: no coding cell qualified, so there were 0 routing calls. All tiers were rejected on B.
  - B-RESEARCH-R2-1: 0 routing calls. Mid and large were accepted but wrong on B, so they would have been
    unsafe stops had research qualified.
  - B-CONV-R2-1: 0 routing calls.
- **Evidence-only case.** B-CONV-R4-1 has all tiers qualified but returned evidence_only with no attempts.

## 6. Disclosure — PASS

- **phase_b_attempts** lists exactly one attempt: attempt 1, run groute3b-001-3ade26dbf80c8774,
  `this_attempt`. There is no earlier attempt, so earlier_attempt_heads is {} and no orphans were cleared.
- **Report fields.**
  - phase_a_run_id is groute3a-002-a90ef4e01edaf413 and table_sha256 is adc5411f….
  - production_routing_invoked false, belief_effects "none", synthetic_fixture false.
  - Every decision carries uses_gold false.
- **Disclosure records.** The committed Phase B records 000001–000003 show one attempt. It moves from
  in_progress at consumption to completed with 144/144/24 counts. The records contain no gold
  (contains_gold false).
- **Phase A.** Attempt 1, closed by operator_interrupt, is disclosed in the table with "optional stopping cannot
  be excluded". Its 52 recorded positions are identical in raw output to attempt 2's.

## 7. Statistical honesty — reported, not blocking

The frozen rule gates observed rates. validation.py tests `unsafe_rate <= max` and `admission_rate >= min`.
SCORING_CONTRACT.md lists the gates as bounds on the observed ratios, and upper_95 is reported but not gated.
The verdict rule is therefore met as stated. The uncertainty is:

- **Unsafe stops / stops: 2/22 = 0.0909, against a bound of 0.10.** The margin is less than one case: a third
  unsafe stop (3/22 = 0.136) would have failed the gate.
  - The exact one-sided 95% upper bound is 0.259; I recomputed this independently. The two-sided 95% interval
    reaches about 0.29.
  - If the true rate were exactly 0.10, observing 2 or fewer of 22 would still happen 62% of the time. At 0.20
    it would happen 15% of the time.
  - So the data do not show that the true unsafe-stop rate is at most 0.10. They show only that the observed
    rate met the pre-registered bound.
  - Both unsafe stops are conversation stops (2 of 4, 0.5), each on the cheapest qualified tier. The other 18
    stops, in synthesis, planning and extraction, had 0 unsafe.
  - There were no coding stops, so the rate excluding coding is identical.
  - thresholds.json justified 0.10 as resolvable "with more than one case of margin". The realized margin is
    below that.
- **Correct stops / qualified-start cases: 20/22 = 0.909, against a minimum of 0.60.** The exact one-sided 95%
  lower bound is 0.74 (two-sided about 0.71), so this gate passes with a clear margin.
- **Scale.** The result rests on 22 routed cases across 4 task classes. It is pilot scale, one sample per tier,
  on one corpus.
  - At cell level, 9 of 30 qualified cells were false positives on B (4 of them R4, which are never routed).
  - 7 false-clean outputs came from qualified tiers; 2 became stops.
  - It says nothing about coding or research, where nothing qualified.
- **Secondary.** Secondary is NOT_TESTABLE (1 escalated stop of the 5 required) and supports no claim about
  escalation.

## 8. Other — nothing blocking

- `.lease` names pid 39688, which is not running: a stale lease, as expected after the command exited. staging/,
  quarantine/ and both orphans/ folders are empty, and there is no recovery.log. The freeze's
  implementation_commit is d20c689, the code commit. The guarded digests prove the Phase B code is identical
  at 27189a8.

## Notes (non-blocking)

- The Phase B `phase_b_attempts` row for the current attempt carries only attempt, run_id and outcome. Counts
  appear in the committed disclosure records, not in the report. This is as designed.
- Report the primary result with the qualifications in §7: the unsafe gate passed by less than one case, and
  its upper 95% bound is 0.26. The unsafe stops are concentrated in conversation (2/4). Secondary is not
  testable.
