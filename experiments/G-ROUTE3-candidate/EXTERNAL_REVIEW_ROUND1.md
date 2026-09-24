# G-ROUTE3 external pre-contact review, round 1

Date: 2026-09-24
Reviewed artifact: `G-ROUTE3-EXECUTION-R1`, binding `64eed1ba1a6bb40faa0277f363f4027c09056ef909e6a31bdf71e8ad5ffe3c21`
Outcome: **not clean.** R1 was never authorized and is void. It is preserved unchanged as
`EXECUTION_FREEZE_CANDIDATE_R1.json` (literal sha256 `b63f0094…4f1653c`) and superseded by
`G-ROUTE3-EXECUTION-R2`. Provider generation calls during review and repair: **0**.

## What was asked

The operator asked for a second reviewer to check four things before Phase A could be authorized:

1. every gold answer is fully derivable from model-facing input;
2. no hidden codes, hidden ordering rules or undisclosed operation constraints remain;
3. Corpus A and B are separate enough for the out-of-sample claim;
4. the qualification and scoring rules contain no "grader knows something the model never saw" trap.

Two reviewers ran independently, read-only, with no model contact.

- Reviewer 1 checked all 96 fixtures against the real validators, and tested about 80 alternative correct
  answers.
- Reviewer 2 checked A/B separation and the qualification, routing and scoring code, and ran probe scripts
  against the frozen validators and triggers.

| Reviewer | Scope | Verdict |
|---|---|---|
| 1 | fixture derivability (questions 1–2) | **FINDINGS** |
| 2 | A/B separation (question 3) | **BORDERLINE** |
| 2 | grader traps and boundaries (question 4) | **FINDINGS**, six blocking |

The design's own audit (the R1 version of `INDEPENDENT_AUDIT.md`) said READY, but it missed every blocking
finding below. It was written by the author of the corpora. That is why this review round exists.

## Operator decisions taken on the findings

- **A/B standard: same construct, fresh instance.** The out-of-sample claim covers new instances of
  qualified constructs, not new kinds of problem. Accidental template reuse within a cell is removed. Where
  one template *is* the construct (planning), that is declared and measured.
- **Conversation operational check: a new G-ROUTE3 validator.** `g_route3_operational.py` replaces only the
  conversation branch. G-ROUTE1's module is not modified, and neither G-ROUTE1 nor G-ROUTE2 is rescored.

## Findings and repairs

In the finding column, "R1" means Reviewer 1 and "R2" means Reviewer 2, followed by that reviewer's finding
number. Each repair is locked by one of two things:

- a named test in `tools/g_route3_tests.py`;
- a check in `authoring/assemble_g3.py`, which refuses to write the corpora if the check fails.

### Hidden rules in the graders (questions 1, 2 and 4)

| Finding | Severity | Repair | Locked by |
|---|---|---|---|
| The conversation operational check rejected words such as "completed", "approved" and "I have", even when negated and even in answers the fixture's own prompt asked for (R1 #1, R2 #4) | BLOCKING | The new validator rejects only an affirmative first-person claim that an action was done. "I have not approved it", "hasn't been completed" and "I have no ticket on file" pass. "I've approved it", "we have now rotated the key" and "I just sent the list" are rejected. It also catches `we've`, which the old check missed (R1 #11). | `test_conversation_operational_check_accepts_negation_and_rejects_affirmative_claims` |
| Gold `forbidden` patterns matched inside negations, such as "no refund has been issued" (R1 #2–5) | BLOCKING | Passive patterns carry negative look-behinds for "no " and "not ". Active patterns match only affirmative first-person claims. | the 36 `incorrect_outputs` and 48 `alternative_correct_outputs` |
| Conversation anchors demanded content the question never asked for: a time, the number "3", the word "two". They also rejected natural phrasings such as "eight cups", "8:00 p.m." and "No. Policy only allows…" (R1 #4, #6–9, R2 #5) | BLOCKING | All 16 conversation fixtures were rewritten, and B-CONV-R2-2, B-CONV-R3-1 and B-CONV-R4-2 are new. Each prompt asks for exactly what its anchors check. Number words and time formats are accepted. Refusals may start with "No" or state an "only X may" rule. Every fixture carries at least three natural correct phrasings and at least one incorrect answer. | `test_natural_correct_phrasings_are_accepted_by_both_validators` (48 phrasings, both validators); `test_incorrect_answers_are_rejected` (36) |
| The 600-character limit was undisclosed (R1 #10) | non-blocking | Every conversation prompt now says "Reply in plain text of at most 600 characters." | assemble check; the phrasing test |
| The coding checker had undisclosed restrictions: it denied reading any attribute except `.parts`; it denied `raise`, `del`, `global`, `yield` and async; and it denied calls to self-defined helpers. `PurePosixPath(...).suffix` was a natural answer that passed the tests but failed the checker (R1 #22–23, R2 #6) | BLOCKING | The coding rules now list the full whitelist: the allowed methods, that only `.parts` may be read, that helper functions may not be called, and every denied statement form. The checker is unchanged. | `test_coding_prompts_disclose_the_operation_whitelist`; assemble check |
| Research status rules overlapped: when one source affirms and one denies, both "contradicted" and "unresolved" applied (R1 #14, R2 #12) | BLOCKING (borderline) | The status rules are now numbered and applied in order, with a definition of when a source is about a claim | `test_every_reference_answer_passes_and_every_gold_code_is_model_visible` |
| B-RESEARCH-R1-2 gold said "supported" although the source's scope was narrower (R1 #15) | borderline | Fixture replaced | same |
| The synthesis conclusion rule had no precedence (A-SYNTH-R4-1) (R1 #16) | BLOCKING (R4) | Conclusion rules apply in a stated order. A-SYNTH-R4-1 now contains the request that the authority boundary reserves. | same |
| B-SYNTH-R2-1's cause was only implied by timing (R1 #17) | borderline | The observation now states the cause explicitly | same |
| Synthesis meaning anchors required exact wording and numerals, but the prompt said only "keeping its numbers" (R1 #18, R2 #13) | borderline | The prompt now says "Restate each observation using its own words and numbers". Every anchor is a substring of its observation. | assemble check |
| A-PLAN-R3-2's step order was not fully stated. B-PLAN-R3-2 and B-PLAN-R4-2 relied on implied precedences (R1 #19–20, R2 #11) | BLOCKING | All 32 planning fixtures were rebuilt on one declared template. Every consecutive pair of steps is linked by an evidence line stating "X before Y". | a mechanical check over all 32 fixtures, recorded in `INDEPENDENT_AUDIT.md` |
| `depends_on` was described in the singular but graded as a list (R1 #21) | BLOCKING (borderline) | The prompt now reads "depends_on is a list: [] for P1, and a list containing only the previous step's id" | reference answers |
| Prompts said "must contain" these fields, but the grader required exactly these keys (R1 #24) | non-blocking | Research, synthesis and planning prompts now say "exactly the keys" | reference answers |
| Extraction span boundaries were unstated: "the fern", "Order 5521", "Vendor Lindqvist Ltd" (R1 #25, R2 #13) | non-blocking | A rule was added: copy names exactly as written, keeping capitalization, without leading articles or labels. Every string gold value is a verbatim span of the text. A-EXTRACT-R1-1's "Branch East" still read as a leading label under the new rule, so it was renamed "Eastgate Library". This was caught in round-2 repair by listing every extraction string in context. | assemble check |

### Trigger traps

| Finding | Severity | Repair | Locked by |
|---|---|---|---|
| `source_independence_insufficient` fired on the gold answer of B-RESEARCH-R3-2, and of A-RESEARCH-R4-2. Its "another lineage was available" check ran across the whole fixture, not per claim. A wrong answer citing only one source stopped unsafely (R1 #12–13, R2 #1) | BLOCKING | Retired. Its condition cannot be decided without knowing which sources are about which claim, and that is a semantic judgment. The reason is recorded in `thresholds.json`. | `test_every_retained_trigger_fires_and_retired_triggers_are_absent`; `test_no_trigger_fires_on_any_reference_or_alternative_answer` |
| Synthesis `grounding_weak` split tokens only on `,` and `.`, and fired on faithful restatements such as "11 C for 40 min." (R2 #7) | non-blocking | Tokens now split on every non-alphanumeric character and at every digit–letter boundary, so "11C for 40min" matches "11 C for 40 min". A new test found the digit–letter case during round-2 repair, and it was fixed before the freeze. | `test_synthesis_paraphrase_with_attached_units_is_grounded` |
| The coding branch of `grounding_weak` could never fire on an accepted output (R2 #16) | non-blocking | Removed. The triggers now live in `g_route3_triggers.py`; G-ROUTE2's policy module is untouched. | same |

### Scoring and boundary defects

| Finding | Severity | Repair | Locked by |
|---|---|---|---|
| An evaluable failing rate gate was reported `NOT_TESTABLE` whenever the other gate lacked its denominator (R2 #2) | BLOCKING | Statuses now apply in this order: `FAILED_INTEGRITY`; then `FAIL` if any evaluable gate fails; then `NOT_TESTABLE`; then `PASS` | `test_an_evaluable_failing_gate_is_a_failure_even_when_the_other_gate_is_not_evaluable` |
| Phase B could never be authorized, because the freeze check refused once a table existed (R2 #3) | BLOCKING | The "no table at freeze time" check now runs only when the freeze is written, not when it is verified | `test_freeze_verification_does_not_depend_on_table_absence`; `test_a_freeze_cannot_be_written_once_a_table_exists`; `test_real_authorizations_open_both_phases_once_each` |
| Table provenance was weak (R2 #8): cells could be edited and the digest recomputed; the audit could be any dict saying READY; a synthetic Phase A was accepted; and Phase A's freeze was never compared | BLOCKING | `phase_b_preconditions` now requires that the table's cells equal the sealed Phase A score, that the score digest matches, that Phase A is complete, non-synthetic and ran under this freeze, and that the table is bound to this freeze. The audit must be bound to a document by sha256. | `test_table_provenance_is_checked_against_the_sealed_phase_a_run`; `test_audit_must_be_bound_to_a_document_digest` |
| The authorization was never consumed, so a best run could be picked from several incomplete Phase A reruns (R2 #9) | non-blocking | The authorization is consumed by exclusive file creation, and a second use is refused. Every Phase A run directory is disclosed in the table source, and a table that omits one is rejected. | `test_authorization_file_is_consumed_exactly_once`; provenance test |
| Coding-sandbox host failures were charged to the model (R2 #14) | non-blocking | Only model-caused errors count as failed evidence: bad JSON, syntax, whitelist denial, timeout. Any other exception is an infrastructure failure and stops the run `incomplete`. | `test_coding_sandbox_host_failure_is_infrastructure_not_model_failure` |
| Qualification counted "at least 4" observations, so a 3+1 split qualified (R2 #15) | non-blocking | Exactly 2 distinct fixtures × 2 repeats is required; any other shape is `insufficient_evidence` | `test_only_the_exact_two_by_two_design_can_qualify` |
| B success needs 2 of 2 against A's 4 of 4, which inflates false negatives (R2 #10) | non-blocking | Kept as designed and stated. Every label now reports the A and B per-observation pass rates beside it, with a note on the asymmetry. | `SCORING_CONTRACT.md` |

### A/B separation (question 3)

Reviewer 2 made four points about the independence audit and the corpora:

- The audit rested on pattern labels the author had assigned.
- Its exclusions removed exactly the text where template reuse would appear.
- Seven of the 18 routed cells paired an A and a B fixture that were the same template with renamed
  entities, and some B fixtures recombined A's answer shapes from other cells.
- Difficulty did not match within some cells.

| Finding | Repair |
|---|---|
| Same-template pairs in CONV-R2, CONV-R3, CONV-R4, EXTRACT-R2, EXTRACT-R4, RESEARCH-R4 and CODE-R1 | Every listed B fixture, or its A partner, was rewritten or replaced with a different reasoning problem |
| Research and synthesis shapes were recombined across cells | Research is reassigned by sub-skill: there are eight sub-skills, each used once per corpus, and no cell uses the same sub-skill in A and B. Synthesis fixtures were rewritten. |
| All planning cells share one algorithm | **Declared, not removed.** Under the operator's "same construct, fresh instance" standard, planning *is* that construct: four steps in a stated total order, one excluded action, five evidence items and one holding uncertainty code. It is declared in `SINGLE_TEMPLATE_TASK_CLASSES`, and the independence report lists all 16 same-cell A/B pairs. |
| The audit could not see structural reuse | `g_route3_independence.py` now compares the *shape* of the gold answer within every cell, for research, synthesis, extraction and planning. Any match outside a declared single-template class is a finding. Result: 0 matches. |
| Difficulty mismatches (EXTRACT-R1, PLAN, RESEARCH-R1, CODE-R3) | EXTRACT-R1 fixtures in both corpora now include a computed field. Planning is normalized to one size. B-RESEARCH-R1-1 now applies a two-lineage rule. B-CODE-R3-2 is now `safe_redirect`, which rejects `//`, backslash and `://`. |

Question 3 therefore stands as **same construct, fresh instance**. It no longer claims new problems; see
`CONTAMINATION_ANALYSIS.md`.

## Checked and sound in round 1 (retained)

Both reviewers confirmed the following:

- Every closed-vocabulary gold code is visible to the model.
- The A and B namespaces, seeds and call ids are disjoint.
- The router is gold-blind in code:
  - runtime views pass through a whitelist;
  - it imports no gold loader;
  - routing is decided before B gold loads.
- It never contacts an unqualified tier, and it makes zero routing calls when no tier qualifies.
- R4 is evidence-only.
- Qualification never passes on missing data.
- Normalization is not repair.
- The outcome arithmetic sums to 48 cases and 144 observations.
- The exact binomial bound of 0.527 is correct.

## What round 1 does not establish

Round-2 review has not happened yet. These repairs were made by the same agent that made the defects. The
R2 freeze goes to fresh reviewers, and Phase A may be authorized only if that review is clean.
