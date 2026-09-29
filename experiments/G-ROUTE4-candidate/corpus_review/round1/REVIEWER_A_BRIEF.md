# G-ROUTE4 external corpus review, round 1: Reviewer A brief

You are **Reviewer A**, one of two fresh, independent reviewers for design step 3.7 of G-ROUTE4 (the external corpus
review). Your focus is **the corpus content**: whether every gold answer in the final corpus is correct and derivable
from what the tested model sees. Reviewer B covers protocol and provenance. You work alone; do not look for, read or
wait for the other reviewer's work.

## Rules (read-only review)

- Repository (git worktree): `C:\Users\marcu\Eidolon-g4adj`, branch `g-route4/adjudication`. Review the commit that is
  `HEAD` when you start, record its id, and confirm that the digests in
  `experiments/G-ROUTE4-candidate/corpus_review/round1/REVIEW_MANIFEST.json` match the files.
- **Do not modify anything in the repository**, and do not run any script that writes into it. Allowed git commands
  are read-only ones only (`log`, `show`, `rev-parse`, `cat-file`, `ls-tree`, `diff`, `merge-base`, `status`,
  `archive -o <file in your scratch folder>`). No commit, checkout, switch, reset, stash, branch, tag, fetch, pull or
  push. Do not touch `C:\Users\marcu\Eidolon` (another checkout) at all.
- Your scratch folder is `C:\Users\marcu\AppData\Local\Temp\claude\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3\scratchpad\corpus_review_r1\reviewer_A\`.
  Write only there. To run repository code, export it there first (`git -c core.autocrlf=false archive`) and run the
  copy. Do not open `...\scratchpad\corpus_review_r1\reviewer_B\`.
- **No network, no model and no provider contact of any kind.** Run Python only as `python -B`, with
  `PYTHONPATH=C:\Users\marcu\AppData\Local\Temp\claude\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3\scratchpad\guard`
  (it blocks sockets). Never read anything under `C:\Users\marcu\.config\`.
- Do not start or propose starting any later G-ROUTE4 stage. You recommend; the operator decides.

## Gate (the operator's safety-gated rule, as in every G-ROUTE4 review)

**BLOCKING** means one of the following: 1. a repeated call; 2. best-of-N or optional stopping; 3. contact without
the correct sentence; 4. a silent scientific or grading change; 5. a contradiction with an operator decision or a
standing constraint. **MUST-FIX** means a defect to fix before the freeze. **NOTE** is anything else worth recording.
The external corpus review is accepted at 0 BLOCKING with every MUST-FIX resolved. Classify each finding yourself,
naming the class for any BLOCKING finding.

## Frozen texts you judge against

- `experiments/G-ROUTE4-candidate/DESIGN_CANDIDATE.md` (accepted revision 6), especially "Gold adjudication" steps
  1–13, the independence standard, and the output-shape disclosure (D8).
- `experiments/G-ROUTE4-candidate/G-ROUTE4_OBLIGATIONS.md` (it overrides conflicting design wording).
- `experiments/G-ROUTE4-candidate/blueprint/` (`BLUEPRINT.json`, `BLUEPRINT_CANDIDATE.md`, frozen at `1156d06`).
- The **derivability rule** (G-ROUTE3 `DESIGN.md`, carried into G-ROUTE4 and extended by D8 to every enforced output
  shape): every closed-vocabulary label in gold is given to the model as an allowed set, every ordering the validator
  enforces is stated in the prompt, and every constraint is disclosed; the gold answer must follow uniquely from the
  model-facing input.
- The frozen validators the corpus is graded by: `tools/g_route3_operational.py` (`validate_operational`) and
  `tools/g_route3_semantics.py` (`validate_fixture_output`), as called by
  `experiments/G-ROUTE4-candidate/adjudication/g4_adjudicate.py` (`score`).

## What the tested model sees

For each fixture: the system prompt profile `experiments/G-ROUTE1-candidate/prompt_profiles.json` →
`profiles[<validator_profile>]`, then the fixture's `prompt`, then its `input`. Nothing else. (The adjudicator saw the
same three parts through the O2 prompt template in `adjudication/adjudicator_config_amended.json`.)

## The final corpus under review

`experiments/G-ROUTE4-candidate/corpus_review/round1/FINAL_MAIN_MODEL_FACING.json` holds the 385 main fixtures (80 A′,
305 B′) exactly as bound: the sealed corpus with 20 recorded round-1 fixes overlaid, no replacement. Their gold is in
`FINAL_MAIN_GOLD.json` in the same folder. The fixes are recorded in `adjudication/fixes/round1_bmain/` and
`adjudication/fixes/round1_amain/` (`FIX_RECORD.json`: defect, every changed path, sealed and fixed digests).

## Your work, in this order

1. **Independent derivation (all 385).** Using only the model-facing view above, derive each fixture's answer
   yourself. Until this step is finished and your derivations are saved in your scratch folder, do **not** open the
   gold file, the sealed gold, the adjudication `runs/`, the closure records, the operator decisions or the latent-
   defect reports. Scripts that parse the input are fine; the judgement must be yours.
2. **Comparison with gold.** For every fixture where your answer differs from gold, decide which holds: gold wrong;
   input ambiguous (gold not uniquely derivable); or your own derivation wrong. Show the reasoning. Also check with the
   frozen validators that each gold `reference_output` passes, and probe whether plausible correct alternative answers
   (formatting, equivalent values, ordering the prompt does not fix) would be rejected: a grader trap is a finding.
3. **Output-shape disclosure (D8).** Is every validator-enforced shape, label set, ordering and constraint disclosed
   to the model, per profile? Name any gap.
4. **Difficulty parity (N5).** Per pattern and per cell, are A′ and B′ fixtures of comparable difficulty? The blueprint
   names research P4 with `sls` false specifically. Are the declared construct choices honoured?
5. **The 20 fixes.** For each, from `FIX_RECORD.json` and the fixture: is the change minimal, does it remove its
   declared defect, does it keep the slot's blueprint features, and does gold follow correctly?
6. **Known disclosures.** Now read `adjudication/fixes/LATENT_DEFECTS.md`,
   `adjudication/fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md`, `CONTAMINATION_ANALYSIS.md` (its warnings section) and
   `adjudication/A_MAIN_CLOSURE.json` / `B_MAIN_CLOSURE.json` (`latent_defects`, `residual_limitations`). Judge every
   fixture they name on its own merits under the derivability rule, including the kept main-corpus fixtures and the
   unused reserves (reserves are in `sealed/reserve_corpus_*.json` and `sealed/reserve_gold_*.json`). Say whether each
   disclosure is accurate and complete, and whether any undisclosed fixture shares a disclosed defect.
7. **O2 (brief verdict).** From `adjudication/O2_AMENDMENT_2026-09-29.md`, `sealed/adjudicator_config.json` and
   `adjudication/adjudicator_config_amended.json`: did the amended configuration (`7691126e…`) change anything that
   bears on what the adjudicator saw or on how gold was judged? Reviewer B verifies O2's records in depth.

Where a finding needs a fixture change, name the frozen remedy it would take (design step 10: a fix, counted as the
fixture's one fix, or a replacement from the matching reserve, with re-adjudication; the 20 fixed fixtures have used
their one fix). Do not apply anything.

## Your output

Write your complete report to `...\scratchpad\corpus_review_r1\reviewer_A\REPORT.md`. It is preserved verbatim as your
review, so make it self-contained:

1. The `HEAD` commit you reviewed, and whether the manifest digests matched.
2. **Coverage first:** how many fixtures you derived independently, how many you compared, what you ran, and anything
   you could not check. Partial coverage must be stated as partial.
3. A findings table: id (A1, A2, …), class (BLOCKING with its number / MUST-FIX / NOTE), fixture or artifact, evidence,
   and the frozen remedy that would apply.
4. A verdict per work item 1–7.
5. One final line: `VERDICT: <CLEAN|FINDINGS> — BLOCKING <n>, MUST-FIX <n>, NOTE <n>`.

Then reply with only that final line and the sha256 of `REPORT.md` (bytes as written).
