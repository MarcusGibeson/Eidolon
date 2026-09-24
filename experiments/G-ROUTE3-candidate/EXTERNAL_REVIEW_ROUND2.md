# G-ROUTE3 external pre-contact review, round 2

Date: 2026-09-24
Reviewed artifact: `G-ROUTE3-EXECUTION-R2`, binding `aa5db17af6e12aaf1453cdbd1c88940743cb8712882c8a7ccba2a6541bfd52af`
Outcome: **not clean.** R2 was never authorized and is void. It is preserved unchanged as
`EXECUTION_FREEZE_CANDIDATE_R2.json` and superseded by `G-ROUTE3-EXECUTION-R3`. Provider generation calls
during review and repair: **0**.

## Reviewers and verdicts

Two fresh reviewers worked independently. Both were read-only and made no model contact.

| Reviewer | Scope | Verdict |
|---|---|---|
| Fixtures | all 96 fixtures; about 590 constructed outputs run through both validators, the triggers and the coding runner | **FINDINGS** (5 blocking) |
| Boundary | A/B separation; qualification, routing, scoring and runner code; probe scripts against the real freeze | Part 3 **BORDERLINE**, Part 4 **FINDINGS** (3 blocking) |

The author reproduced every blocking finding before repairing it. These included:

- a hand-built Phase A directory, with no calls, that passed `phase_b_preconditions` and
  `phase_b_authorized` against the real freeze;
- reusing an authorization by adding one key or changing the run root;
- conversation false-cleans such as "…unless manager approval is granted" (A-CONV-R2-2);
- a test-passing coding fix rejected by both validators because `old` lacked its final newline.

Both reviewers confirmed the following as sound:

- every gold answer is derivable, with no hidden codes or ordering rules;
- the research, synthesis, extraction and coding graders;
- the gate ordering and metric arithmetic;
- gold blindness;
- write-once tables;
- exact-string Phase A authorization;
- 2 × 2 qualification;
- infrastructure attribution for sandbox host and provider failures;
- a bit-for-bit reproducible independence report.

## Operator decisions

- **Conversation grading: disclosed answer frame.** Each conversation fixture lists `answer_options`. The
  reply's first line is `Answer: <option>`, and the decision is judged exactly on that line. The free text
  is judged only for claims that the assistant carried out an action. This replaces phrase anchors, which
  failed in both directions across two reviews.
- **Coding `old`: ignore trailing newlines.** `old` is compared with the source ignoring trailing newlines
  only. G-ROUTE3 measures code repair, not newline fidelity. The mid model dropped that newline in 10–11 of
  12 coding calls in G-ROUTE1 and G-ROUTE2.

## Findings and repairs

### Blocking

| # | Finding | Repair | Locked by |
|---|---|---|---|
| B1 | Phase A provenance was self-attested. `run.json` was unsealed. The score seal is a digest of its own content, so a score and a table could be edited together and both resealed. Nothing re-derived the cells from the call records. | `phase_b_preconditions` re-derives the cells as `qualify(attach_semantics(call records))`, and they must equal both the sealed score and the table. It also requires all of the following: the call records match all 288 scheduled calls in order; the sealed terminal receipt chains to the call records (new `call_records_sha256`) and to the score; the synthetic flag and freeze digest come from the sealed receipt, never from `run.json`; the receipt's guarded digest equals today's; and a non-synthetic run appears in the authorization ledger. | `test_table_provenance_is_rederived_from_the_sealed_call_records`, `test_a_fabricated_phase_a_run_cannot_open_phase_b` |
| B2 | The one-shot authorization could be reused under a new key or a different run root, and the attempt list scanned only one run root. The opposite also held: after an infrastructure failure there was no legitimate way to authorize a retry. | Authorizations use an exact key set and are numbered: `Authorize G-ROUTE3 phase A execution <binding> attempt <n>`. Phase B's also names the table and the Phase A run. Each authorization is consumed by exclusive creation in a **fixed ledger** (`experiments/G-ROUTE3-candidate/authorization_ledger/`), independent of the run root. Attempt numbers are contiguous, and a run may resume under its own attempt. The table discloses every Phase A attempt from the ledger, so a later attempt breaks disclosure. | `test_real_authorizations_are_numbered_attempts_recorded_in_a_fixed_ledger`, `test_authorization_is_consumed_exactly_once_in_the_fixed_ledger` |
| B3 / F2–F6 | Conversation anchors still failed both ways. Correct replies were rejected: "unless approval is granted", "I'm not authorized", "Don't open the link", "Not all three keys…". Wrong ones were accepted: "Yes, you can leave at 15:00. No approval is needed", "I went ahead and booked you". A correct late-fee explanation was rejected for "applied". | Disclosed answer frame (operator decision). All 16 conversation fixtures were rewritten on it. Each has a closed option set, three alternative correct replies in varied formats, and four incorrect replies. The action-claim check normalizes typographic apostrophes. It catches "went ahead and" / "gone ahead and" and "you're booked"-style claims, and never matches a negation. Answer positions are pseudo-random. | `test_conversation_frame_accepts_negation_and_rejects_action_claims`, `test_conversation_answer_line_parsing_is_lenient_only_in_form`, `test_conversation_answer_positions_carry_no_information`, 48 alternative and 64 incorrect replies |
| F1 | Coding: a correct fix whose `old` lacked the final newline failed both validators, although its tests passed | `g_route3_semantics.canonical_coding_payload` restores the exact source as `old` only when the difference is trailing newlines. The runner builds execution evidence from the same canonical payload, so the candidate digests agree. Any other difference still fails. | `test_coding_old_is_compared_ignoring_trailing_newlines_only` and an assembly check |

### Non-blocking, repaired

| # | Finding | Repair |
|---|---|---|
| B4 / F7 | Typographic apostrophes let claims through and made negations fail | Text is normalized before matching (conversation frame) |
| B5 | `synthetic_fixture=True` skipped authorization for any provider | The synthetic path requires a provider that declares `synthetic_provider = True`, checked before anything else. The synthetic flag is read back from the sealed receipt. |
| B6 | Runtime dependencies were outside the freeze and the guard: the G-ROUTE1 model bindings used for preflight, `g_route1_execution_contract.py`, `g_route1_freeze.py` and `conscious_agent/activity.py` | Model preflight now checks against G-ROUTE3's own frozen bindings. A test computes the runtime import closure, including the activity module, which also pulls in `json_storage.py` and `metadata_mutation_coordination.py`. It requires every module to be both frozen and guarded; all are now. |
| B7 | Some trigger branches are unreachable on an accepted output | Stated in the trigger module. The live conditions were verified by probe; one wrongly claimed live condition was corrected. |
| B8 / F10 | The 350-token output cap was undisclosed | Every JSON-profile prompt now says output beyond about 350 tokens is cut off. The two longest references (A/B-SYNTH-R4-1) were shortened, and assembly bounds every reference at about 250 tokens compact. The generation configuration is unchanged. |
| B9 | A coding timeout was always charged to the model | On a timeout the runner re-runs the unchanged source as a host baseline. If that also times out, the result is an infrastructure failure (`coding_sandbox_host_slow`). |
| B10 | The audit could be any file, not tied to the run; the table's source digests were never checked | The audit document must name the Phase A run id and score digest and must not be a frozen artifact or guarded file. `verify_table` checks the corpus, gold and threshold digests. |
| B11 | Planning `allowed_actions` were listed in gold order, so the order could be copied | Actions are listed in a fixed pseudo-random order that is never the gold order, and assembly checks this |
| B12 | CONV-R1 paired the same two templates in A and B; the research signature was too fine to see a same-shape pair | Conversation was rewritten with distinct operations per cell: A-R1 is filter and division, B-R1 is maximum with unit conversion and counting. A coarse research signature (statuses, recommendation, reason for unresolved, ignoring lineage counts) was added. It found A-RESEARCH-R1-1 / B-RESEARCH-R1-2; the latter now has both claims contradicted by numbers. |
| B13 | Within-cell difficulty mismatches | CONV-R2 and R3: each corpus pairs one computation with one lookup. EXTRACT-R2: A-R2-2 gained a date addition and B-R2-2 was simplified to one multiplication. EXTRACT-R3: B-R3-2 now derives retention days from two dates. An extraction signature that counts derived fields was added. |
| B14 / F9 | Contestable research gold, and the rule (3) wording | B-RESEARCH-R2-1 now claims "both Saturdays and Sundays" and cites a "liability insurance certificate". B-RESEARCH-R2-2's claim names "inks, paper and screens". A/B-RESEARCH-R1-1 sources name the product. Rule (3) says "narrower scope" only. A-EXTRACT-R1-1 no longer has a name-with-label field. |
| F8 | Synthesis anchors required one inflection ("promoted" rejected "promotion") | Inflected anchors are stems ("promot", "review", "configur"…), each still a substring of its observation. Anchor checks remain inherently lenient in the other direction, and this is stated in the scoring contract. |

## What round 2 does not establish

These repairs were made by the same agent that made the defects. The R3 freeze goes to fresh reviewers, and
Phase A may be authorized only if that review is clean.
