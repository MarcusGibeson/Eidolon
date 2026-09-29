# G-ROUTE4 external corpus review, round 1: Reviewer A report

The brief digest was confirmed first: sha256 over LF-normalized bytes is 827cce9f…0c21, which matches.

## 1. Commit reviewed and manifest check

- **Commit:** `97afe8a93def2c1eb572e38f567f68ab5cb53b4b`, on branch `g-route4/adjudication`. It was exported with `git -c core.autocrlf=false archive` to my scratch folder and every check ran on that copy.
- **HEAD moved during the review.** The worktree HEAD is now `ae62dba…`. As the coordinator instructed, I did not inspect the new commits, `corpus_review/round1/outputs/`, or any Reviewer B material.
- **Manifest digests: all match.** Recomputed from the export:
  - The four canonical corpus and gold digests (A′ and B′).
  - The package file digests: `FINAL_MAIN_MODEL_FACING.json` 3613d4fb…, `FINAL_MAIN_GOLD.json` f073d227….
  - The reserve digests, `SEAL_MANIFEST.json` and the six report digests.
  - Both brief digests.
  - The O2 config digests (1658b9a2… and 7691126e…). These are the configs' self-excluding embedded `config_sha256`, not file digests.
  - `check_corpus.py` (b3f6500b…). It matches only at commit dd8193b, because the file is absent at HEAD.
- **The package equals its sources.** I rebuilt sealed corpus + 20 recorded fixes and it is identical to both package files. Every fix is bound to its recorded sealed and fixed digests.
- **Frozen inputs unchanged since the seal:** `git diff 50e6b46 HEAD` is empty for the sealed/, blueprint/, prompt profiles and both frozen validators.

## 2. Coverage

**Full coverage:**
- **Independent derivation: 385 of 385** (80 A′, 305 B′), done before I opened any gold, runs/, closure, operator-decision or latent-defect file.
  - I read every fixture myself in compact per-class views. Scripts only parsed the input, checked my own bookkeeping, and did date and time arithmetic.
  - The derivations are sealed by sha256 in `scratchpad/corpus_review_r1/reviewer_A/derivations/DERIVATIONS_SEALED.sha256`, timestamped 2026-09-29T21:29:15Z, before gold was opened.
- **Comparison: 385 of 385.**
  - My answers were compared with gold using the validators' own normalization.
  - The frozen validators (`validate_operational` and `validate_fixture_output`, called as `score` calls them) were run on all 385 gold `reference_output`s and on all 385 of my answers.
- **Grader-trap probes:** 12 kinds of alternative answer that the prompt leaves free, or that it fixes, over all 385.
- **Construct checks:** every one of the 385 slots against `BLUEPRINT.json` features, plus difficulty statistics per pattern × sls, per phase and per conversation depth.
- **The 20 fixes:** full leaf-level diffs of sealed against fixed fixture and gold, compared with each `FIX_RECORD`.
- **Disclosed fixtures:** all 4 kept main-corpus fixtures and all 15 named reserves judged on their merits.
- **Undisclosed defects:** pattern scans of all 385 main and 199 reserve fixtures for each disclosed defect and for the two new defects I found.
- **Sealed adjudicator answers:** after derivation, a read-only re-read of all 766 bound slots. Each binding text was rebuilt, checked against its digest, and re-graded after the tested-model pipeline's own fence normalization (`g_route2_normalization.normalize`).

**Not checked:**
- Reserves the disclosures do not name were only pattern-scanned, not fully derived.
- Independence, trigram and O6 re-checks were not re-run.
- The conversation `depth` feature cannot be verified mechanically.
- No network, model or provider was used; Python ran as `python -B` with the socket guard.

## 3. Findings

| Id | Class | Fixture / artifact | Evidence | Frozen remedy |
|---|---|---|---|---|
| A1 | MUST-FIX | A4-SYNTH-R1-01, B4-SYNTH-R1-02, B4-SYNTH-R2-15, B4-SYNTH-R3-08 (final main corpus) | These four keep the "SY1 diagnosis role" defect: the cause is stated only by a `diagnosis`-role observation, while the rule says "a finding directly states the cause". The project classified this exact defect as "input ambiguous → fix input" and fixed it in 8 other SY1 fixtures. `LATENT_DEFECTS.md` reports that 16 of 18 B′ answers chose `insufficient_evidence` on it. The rules also use role vocabulary elsewhere ("counterevidence"), so a literal role reading is plausible. Gold is therefore not uniquely derivable, and keeping 4 of 12 SY1 slots with a defect the operator repaired in the other 8 is inconsistent. I derived `cause_established` myself but flagged all four at derivation time. | Step 10: a fix, counted as each fixture's one fix (none has used theirs), using the same role relabel as the 8 recorded SY1 fixes. Then the re-check and re-adjudication: A4-SYNTH-R1-01 gets the full A′ treatment, the others the B′ procedure. Replacement is not suitable for A4-SYNTH-R1-01, because its matching reserve A4-SYNTH-R1-X01 has the same defect. |
| A2 | MUST-FIX | B4-CONV-R1-08 (undisclosed) | "Nonobo dispatches on 2045-11-18 after 2 days of packing…". Read literally (dispatch happens on the stated date), all four options meet both deadlines (deliveries 11-25, 11-26, 11-26, 11-23). Only the reading "dispatch = stated date + packing days" gives the unique gold, Yulofu. Gold follows only from intent inferred through the near-miss design, not from the text. It was kept on the first adjudicator's agreement. | Step 10: a fix (one fix; for example "starts packing on …") with B′ re-adjudication, or a replacement from the matching B′ R1 conversation reserve (gold position × depth). |
| A3 | MUST-FIX | B4-CONV-R2-28 (undisclosed) | "Wapodi can start on 2046-02-03 and needs 11 days" against "in place by 2046-02-13". Counting the start day as day 1 (the usual scheduling convention) finishes on 02-13 and passes. Start + 11 finishes on 02-14 and fails. Under the first reading Wapodi and Vuboyi are both valid, so the gold Vuboyi is not uniquely derivable. By contrast, B4-CONV-R3-19 fails its near-miss under either convention. | Same as A2. |
| A4 | NOTE | Research P4, A′ against B′ (N5) | A′ has P4 only with sls = false (A4-RSRCH-R1-04, A4-RSRCH-R4-02). There C1 always has a second independent lineage, so the same-lineage repost never changes the answer. Every A′ lineage-count decision rule resolves positive. B′ has three fixtures where reposts are the only support and the recommendation is negative (B4-RSRCH-R1-12, R2-12, R3-12). A′ and B′ P4-sls-false fixtures are structurally identical (C1: 3 sources, 2 lineages; codes []). A′ research qualification never tests the repost-counting failure that B′ tests. This follows from the frozen allocation, not an authoring defect. | Disclose in results; no fixture change. |
| A5 | NOTE | Synthesis SY4, SY5, SY6 (35 of 71 fixtures) | By the blueprint's family definitions these conclusions are constant: always `decision_reserved`, `constraint_breached` and `behavior_by_design`. `decision_open`, `constraint_met` and `defect_found` never occur, so in these families the conclusion follows from which rule text is present. The conclusion component is weak there; declared by the blueprint. | Disclose. |
| A6 | NOTE | Adjudication format failures | 168 of 766 bound slots were ```json-fenced and scored `malformed_json`, per the frozen O2 parse rule. My re-grade after the pipeline's fence normalization: 144 agree. All 24 content differences are on the sealed versions of the 20 later-fixed fixtures. The same holds for the 34 scored content disagreements, apart from A4-PLAN-R3-04's 3 refusals (A7). No substantive disagreement was hidden on any unfixed final fixture. The closure counts (52 = 34 + 8 + 3 + 7 for A′; 107 of 131 for B′) are accurate. Tested models get fence normalization and adjudicators did not, which errs toward escalation. | None. |
| A7 | NOTE | A4-PLAN-R3-04 | All three adjudications were provider refusals (category cyber), so the fixture has no substantive adjudication. My independent derivation equals gold. Disclosed. | None. |
| A8 | NOTE | A4-RSRCH-R1-04, B4-RSRCH-R1-04, B4-RSRCH-R2-05, B4-SYNTH-R3-03, B4-EXTR-R1-12, B4-CONV-R2-27 | Borderline wordings where gold still follows:<br>• A4-RSRCH-R1-04: "kiln firing included in the course fee" as support for "fires student work for free".<br>• B4-RSRCH-R1-04: "solo dancers are paired up on arrival" as support for "needs no partner".<br>• B4-RSRCH-R2-05: "all meeting rooms" for "every room".<br>• B4-SYNTH-R3-03: the elapsed time is established only by the [impact] observation.<br>• B4-EXTR-R1-12: the voice-part label "Alto".<br>• B4-CONV-R2-27: the slot starts 2 minutes after landing, but the prompt says to use only the times.<br>All matched gold, and all adjudicator content agreed after normalization. | None. |
| A9 | NOTE | The 20 fixes: minimality and difficulty | Every recorded change list is complete and exact (leaf diffs equal the records), and the digests are bound.<br>• The SY1 fixes also relabel preceding `finding` observations to `symptom`. This is more than one role change, but it is needed to keep `mergeable_pair` and a single causal "finding".<br>• A4-RSRCH-R2-01 and B4-RSRCH-R3-04 now state the support almost verbatim, so these fixtures got easier. They are already flagged under step 12. | None. |
| A10 | NOTE | `B_MAIN_CLOSURE.json` `residual_limitations` | It says "22 fixtures / 14 reserves", which predates the addendum. The current count is 15 reserves, including B4-RSRCH-R2-X04. The A′ closure and the contamination warnings are current. | Wording only. |
| A11 | NOTE (for Reviewer B) | Provenance | The checker commit dd8193b is not an ancestor of HEAD; it is on `g-route4/authoring-staging`. The manifest digest matches at that commit. | None from me. |

## 4. Verdicts per work item

1. **Independent derivation:** done for all 385 and sealed before gold was opened.
2. **Comparison with gold:**
   - 0 of 385 differ from gold, and 385 of 385 gold reference outputs pass the frozen validators.
   - Grader-trap probes: validators accept every correct variant the prompt leaves free and reject every variant it fixes. The only exception is fenced JSON, which raw `score` rejects but the tested-model pipeline normalizes (A6).
   - The ambiguities that affect derivability are A1, A2 and A3. My own derivation matched gold there only by resolving each ambiguity the intended way.
3. **D8 disclosure: no gap in any profile.**
   - Research: the D8 sentence (454 characters, sha256 f3c383d9…) appears exactly once, with the frozen assembly.
   - Conversation: every fixture carries the frame instruction, all options are pairwise distinct under `canonical_value`, and gold `max_characters` is 600 throughout.
   - Extraction: the `not_provided` sentence appears exactly where a `provided|not_provided` type exists, and the type and integer rules are disclosed.
   - Synthesis and planning: every enforced rule appears in the prompt or system text, including ascending `evidence_ids`, alphabetical codes, the `depends_on` chain and verbatim text.
   - The blueprint's "mergeable_pair … must merge" is not enforced by the validator, so it is not a trap.
4. **Difficulty parity (N5):** declared constructs are honoured with 0 violations across all 385 slots:
   - research family sizes, pattern markers and sls;
   - synthesis family conclusions, `obs_band` and `mergeable_pair`;
   - planning included, excluded and holding counts, and precedence form;
   - extraction field count, derived count and field types;
   - conversation gold positions (1/1/1/1 in A′ cells, 7/7/7/7 in B′ cells).

   Per pattern and per cell, A′ and B′ are comparable in claims, sources, reposts and codes, and conversation message lengths are comparable by depth. The exception is P4, where A′ exercises only the redundant form (A4).
5. **The 20 fixes:** every change is minimal or justified, removes its declared defect, keeps the slot's blueprint features, and gold follows (my derivations equal the fixed gold on all 20). Minor observations are in A9.
6. **Known disclosures:** accurate and complete for the four defect types. Every instance in main and reserves is listed:
   - 8 P6 "only" reserves;
   - SY1 diagnosis: 4 main and 5 reserves;
   - 2 weak-paraphrase reserves.

   Each reserve I judged is non-derivable as disclosed and would fail if drawn. No undisclosed fixture shares a disclosed defect. However, the 4 kept SY1 main fixtures should not stay unfixed (A1), and A2 and A3 are new, undisclosed defects.
7. **O2:**
   - **Unchanged:** the amended config (7691126e…) leaves `prompt_template` (template 8dd007c3… and the profile digests), `input_rendering`, `adjudicator`, `judgement` and `sessions` equal to the sealed config.
   - **Changed:** only the sampling and reasoning settings (temperature omitted, adaptive thinking, effort high, 32000 tokens), the request and error-classification blocks, and the binding-text definition (text blocks only).
   - **Conclusion:** nothing that bears on what the adjudicator saw or on how gold was judged changed. The validators, the disagreement definition, the parse-failure rule and the single retry are unchanged. The capability change is disclosed and affects only the strength of the declared residual filter.

VERDICT: FINDINGS — BLOCKING 0, MUST-FIX 3, NOTE 8

(Per the coordinator's instruction this report is returned in the hand-back rather than written to REPORT.md, so no REPORT.md sha256 exists. Working files are in `C:\Users\marcu\AppData\Local\Temp\claude\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3\scratchpad\corpus_review_r1\reviewer_A\`: `derivations/`, `compare_out.txt`, `probe_out.txt`, `constructs_out.txt`, `fixes_out.txt`, `regrade_out.txt`.)
