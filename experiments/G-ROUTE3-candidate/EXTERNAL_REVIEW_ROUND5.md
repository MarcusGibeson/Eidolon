# G-ROUTE3 external pre-contact review, round 5

Date: 2026-09-24
Reviewed artifact: `G-ROUTE3-EXECUTION-R5`, binding `2e97b75e0b3ce68bd2cd21fd5cbcc69f6133abaa736727b62452d729061fce94`
Outcome: **not clean.** R5 was never authorized and is now void. It is preserved unchanged as
`EXECUTION_FREEZE_CANDIDATE_R5.json` and superseded by `G-ROUTE3-EXECUTION-R6`. No provider generation
calls were made during review or repair.

The first two reviewers stopped at a usage limit before reporting. Two fresh reviewers then ran from the
start with the same instructions. Both were given the operator's threat model: an honest operator with
tamper-evident records.

## Reviewers and verdicts

| Reviewer | Scope | Verdict |
|---|---|---|
| Fixtures | All 96 fixtures, derived independently before reading gold. About 9,100 outputs: 1,522 correct, 1,365 wrong, 5,936 hostile fuzz cases, and full synthetic Phase A runs. | **FINDINGS**: 1 blocking. Questions 1 and 2 both answered cleanly: every gold answer can be derived, and nothing hidden remains. |
| Boundary | A/B separation, plus the lifecycle and boundary probes on the authorized path | Part 3 **BORDERLINE**. Part 4 **FINDINGS**, with 2 blocking. |

**Confirmed sound:**
- All 96 gold answers match independent derivation, and each has a single defensible answer.
- No correct output was rejected, apart from one typographic-hyphen case, which is now fixed.
- Every wrong output was rejected, except the declared synthesis anchor leniency.
- No trigger fired on a correct output.
- The freeze verifies.
- The normal launcher path works end to end, including a retry after an infrastructure failure.
- Routing is gold-blind.
- Gates and denominators are correct.
- The corpora share no entities or answers.

## A pattern, stated plainly

Both blocking classes had been repaired in round 5 for **the exact case the previous probe used**:
- crash-proofing covered the validators, but not the coding sandbox's pre-subprocess stage;
- interrupted finalization covered one crash window, but not three others.

In round 6 each class is repaired at its root, not per instance.

## Findings and repairs

### Blocking

| # | Finding | Root-cause repair | Locked by |
|---|---|---|---|
| F1 / B1 | **A coding candidate crashed Phase A.** One was a 3,200-dash unary chain, only 88 tokens long; another was JSON nested about 1,000 levels deep. `ast.parse` or JSON parsing raised `RecursionError` or `MemoryError` before the sandbox subprocess started. The runner charged that to infrastructure and stopped. | The runner now runs the frozen coding runner's own pre-subprocess steps in-process: parse, schema and path checks, candidate build, and the AST whitelist. **Any** exception at that stage is the model's failure. Only the subprocess stage can report a host failure. | `test_pathological_coding_candidates_are_model_failures_not_infrastructure`: a full Phase A with hostile coding output completes. |
| B2 | **Finalization crash windows left an attempt unrecoverable:** <br>(a) after the score and before the receipt; <br>(b) after completion and before the anchor; <br>(c) after the 288th record and before its checkpoint. | **Finalization is a single idempotent `_finalize`:** <br>• an existing sealed score must equal the recomputed one; <br>• an existing receipt must chain to the records and the score; <br>• the manifest is finished if it has not been; <br>• the checkpoint seal and the git anchor are no-ops when already done. <br><br>**`--resume` repairs any of these windows:** <br>• a checkpoint exactly one record behind is reconciled from the sealed record; <br>• any run that holds every record, or is already complete, goes straight to `_finalize` without contacting the model. | `test_finalization_recovers_from_a_crash_after_the_score_before_the_receipt`, `…_after_completion_before_the_anchor`, `test_a_checkpoint_one_record_behind_is_reconciled_at_the_end_and_mid_run` |

### Non-blocking, repaired

| # | Finding | Repair |
|---|---|---|
| N1 | An interrupted launch could leave an orphan run folder that blocked every new attempt. | New step `clear_orphan_run` (launcher `--clear-orphan`). It applies only to a folder with no ledger entry and no call record. It moves the folder aside, records a reason, and anchors that record in git. |
| N2 | A failed git anchor was never retried. | Anchors are always re-applied, and they are idempotent. An authorized Phase B requires three things to be committed and unmodified in git: the Phase A ledger entries, the Phase A run anchor, and the frozen table. |
| N3 | Editing the manifest from "incomplete" to "running" let a closed attempt resume. | Every non-complete end now writes a sealed closure record. On the authorized path that record is also anchored in git. A run with a closure record is never resumable, and its disclosed outcome comes from the sealed closure. Abandon uses the same mechanism and is anchored. |
| N4 | A proxy could redirect the loopback endpoint. Out of scope, but cheap to fix. | The launcher removes proxy variables and sets `NO_PROXY=127.0.0.1,localhost`. |
| N5 | A relative audit path, and no supported way to freeze the table. | Audit paths are resolved to absolute paths. New launcher command `--freeze-table` builds the table from the sealed score, binds the audit, writes the table once, anchors it, and reports the Phase B preconditions. |
| N6 | Abandon was not anchored. | Abandon is now anchored, as described under N3. |
| N7 | Ollama auto-updates could invalidate the pinned version. | Documented in the launcher: turn off auto-update until Phase B finishes. A changed version fails the preflight closed. |
| F2 | A typographic hyphen in a verbatim synthesis copy failed a meaning anchor. | Synthesis statement text is normalized for typographic punctuation, as the conversation frame already was. |
| F3 | A direct `collect_evaluation` call on a raw lone surrogate produced a record that could not be sealed. | `collect_evaluation` sanitizes its own input. |
| I1 / I2 | Synthesis R1 and R2 reuse a conclusion-rule family across the corpora. Research R2 and R3 recommendation directions were not declared. | Both are declared, with per-cell tables in `CONTAMINATION_ANALYSIS.md`. |

## What round 5 does not establish

The same agent made both the defects and the repairs. The R6 freeze goes to fresh reviewers under the same
threat model. Phase A may be authorized only if that review is clean.
