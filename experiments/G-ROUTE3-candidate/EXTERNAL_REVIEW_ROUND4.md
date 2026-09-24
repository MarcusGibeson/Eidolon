# G-ROUTE3 external pre-contact review, round 4

Date: 2026-09-24
Reviewed artifact: `G-ROUTE3-EXECUTION-R4`, binding `3660f60f459ef7a0b3dc1e86bd50aec397d1233e7a235665989ad91195b727b3`
Outcome: **not clean.** R4 was never authorized and is void. It is preserved unchanged as
`EXECUTION_FREEZE_CANDIDATE_R4.json` and superseded by `G-ROUTE3-EXECUTION-R5`. Provider generation calls
during review and repair: **0**.

## Reviewers and verdicts

| Reviewer | Scope | Verdict |
|---|---|---|
| Fixtures | All 96 fixtures, each derived independently before reading gold; 2,805 constructed outputs | **FINDINGS**: 2 blocking, both in how the conversation "Actions taken" line was graded |
| Boundary | Boundary, scoring and independence. A full synthetic A → table → B run was traced through the real activity module. Probes covered the authorized path, fuzzing and tampering. | Part 3 **BORDERLINE**; Part 4 **FINDINGS**, 3 blocking |

**Confirmed sound:**
- Gold and derivability:
  - All 96 gold answers match independent derivation, with no second defensible answer.
  - Every correct output outside conversation passes both validators and fires no trigger.
  - Every wrong output outside conversation fails.
- Coding canonicalization.
- Guard and freeze coverage: every one of the 24 modules loaded, including the launcher.
- The attempt policy, absent tampering.
- A legitimate launcher-path run and a retry after an incomplete attempt, reasoned through end to end.
- Gold-blind routing.
- Gates and the 0.527 bound.

## Operator decisions

- **Threat model: an honest operator, with tamper-evident records.**
  - In scope: the code must stop accidents, misuse through any supported path, and cheap tampering.
  - Out of scope, and declared: a deliberate local adversary. That means someone running a fake model
    server, using a second checkout, or consistently rewriting sealed files.
  - How the out-of-scope case is countered: procedurally, by git anchor commits.
- **Git anchor: the launcher commits locally.** When an attempt is consumed, the launcher commits its
  ledger entry. When a run completes, it commits a small anchor file that binds the run to its sealed
  receipt. Each commit contains that one file only, and nothing is pushed.

## Findings and repairs

### Blocking

| # | Finding | Repair | Locked by |
|---|---|---|---|
| F1 / F2 / B7 | **"Actions taken" parsing.** It rejected natural no-action forms ("None. I have no tools.", "No action was taken."). It also accepted an action smuggled in after a separator ("none, but I forwarded your request"). Both came from the round-4 note allowance. | This is now a closed field. The prompt says: write exactly `none` and nothing else. The grader accepts only bare no-action forms, including "no action was taken", "no actions were taken" and "(none)". Nothing may follow. | `test_conversation_frame_grades_the_two_fields_and_never_the_prose`; 48 alternative and 96 incorrect replies |
| B3 | **Malformed model output could crash collection.** Examples: an unhashable research `status`, JSON nested about 1,000 levels deep, a lone `\ud800` surrogate, planning `steps: 1.5`. The seeds are fixed, so the crash would recur and Phase A could never finish. | Model output can no longer crash collection, scoring or sealing: <br>• Normalization, the operational validator, the semantic evaluator and the triggers record any exception as a failure of that output. <br>• A validator result that cannot be serialized drops its parsed copy and fails the gate. <br>• Lone surrogates are replaced before sealing, and the provider-evidence check applies the same replacement. <br>• Coding canonicalization tolerates `RecursionError`. | `test_no_model_output_can_crash_collection_or_sealing` (a full 288-call Phase A with hostile outputs completes) |
| B1 | **Cheap best-of-N.** Deleting one ledger file and replaying the attempt-1 sentence gave a second complete run that opened Phase B. So did editing an unsealed manifest after deleting a receipt. A second checkout also replays. | **Cheap tampering is now detected in code:** <br>• Ledger entries are hash-chained. <br>• A fresh attempt, and Phase B, require exact agreement between the ledger and the run directories under the fixed run root, so a deleted entry leaves an unrecorded run and is refused. <br>• The attempt number and authorization digest are sealed into every call record and into the receipt, and must match the ledger. <br>• A run holding every call record cannot be abandoned. <br>• Each attempt's disclosure includes its count of sealed calls. <br><br>**Deeper tampering is out of scope (declared):** deleting a run directory or receipt, or using a second checkout. The git anchor commits make it visible in history. | `test_the_ledger_is_hash_chained_and_must_agree_with_the_run_root`, `test_a_run_holding_every_record_cannot_be_abandoned` |
| B2 | **The endpoint could be redirected.** It was a free CLI flag. Model receipts were supplied by the caller and never persisted. The runner did not enforce the launcher's fixed roots. | **Now:** <br>• The endpoint is fixed (`http://127.0.0.1:11434`), and the launcher has no endpoint flag. <br>• The endpoint and model receipts are recorded in the manifest and in the sealed receipt, and Phase B re-verifies them. <br>• The authorized path requires the fixed run root and a git anchor. <br><br>**Out of scope (declared):** a fake server on port 11434. | `test_the_authorized_provider_endpoint_is_fixed`, `test_real_authorizations_are_numbered_attempts_recorded_in_a_fixed_ledger` |

### Non-blocking, repaired or declared

| # | Finding | Response |
|---|---|---|
| B4 | The coding host baseline reran the fixture's own source. For A-CODE-R2-1 that raised a whitelist error, which counted as "host OK". | The baseline is now a trivial whitelist-clean candidate. A timeout or any exception on it counts as infrastructure. |
| B5 | A crash after the receipt was sealed but before `finish` deadlocked the attempt. | `--resume` completes an interrupted finalization after checking that the receipt chains to the records (`test_an_interrupted_finalization_is_completed_on_resume_not_deadlocked`). |
| B6 | An operator could stop a run early, score it privately, and abandon it with a free-text reason. | Abandon is refused once every call record exists. Each disclosed attempt shows how many sealed calls it had. |
| F3 | Numbered or bulleted frame lines and the non-breaking hyphen were rejected. | Accepted as decoration. |
| F4 | A-CODE-R2-1's own source uses `dict()`, which the whitelist forbids. | Disclosed: "The current file may itself use calls that are not allowed; the repaired file must not." |
| B8 | Answer positions were imbalanced within cells. A-CONV-R3-2 was trivial. | Every conversation fixture's answer now sits at a position fixed by its cell and slot, so A and B match within every cell; the independence tool checks this. A-CONV-R3-2 now requires checking an agreement's expiry date. Coding R1 difficulty and the direction of research recommendations are declared, not changed: coding stops cannot be unsafe, and research sub-skills already differ by design. |
| B9 | R4 same-template pairs (conversation refusals, coding normalization). | Declared. R4 is evidence-only. |

## What round 4 does not establish

The same agent that made these defects also made these repairs. The R5 freeze goes to fresh reviewers, who
are told the operator's threat model. Phase A may be authorized only if that review is clean.
