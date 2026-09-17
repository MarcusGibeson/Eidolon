# Reviewer capacity qualification (Q-CAP)

**Status: NOT QUALIFIED at 34 parts. Conditional pass with 1.1% margin; the limit is architectural, not a bug.**

This record is separate from, and does not amend, the original v2731.8 reviewer validation. Nothing here qualifies
the reviewer above its previously demonstrated 27-part ceiling. See §6 for the verdict.

## 1. Question

Can the existing frozen reviewer (`experiment_review.py`, contract `v2731.8`) be qualified from its demonstrated
ceiling of 27 parts to at least 34 parts, on reviewer-infrastructure and evidence-handling merits alone?

## 2. Scope and separation

- `experiment_review.py` was **not modified**. Contract `v2731.8`; module digest
  `ded434186b23307b8c54d444ee4a384d4691c680034d5649305ab773baa4db64` (working copy, CRLF; the git blob digest of the
  same content is `d158e253dd88febca8f22ed050beccde2724fd9b604138fa579c5201228b21c8`).
- No reviewer limit was raised. `CHUNK_CHARS` 6500, `FINAL_INPUT_BUDGET_CHARS` 12000, document statement slots 37,
  all unchanged and asserted unchanged by the test suite.
- **G-EVID1 was not read, rerun, rescored, or used as qualification material.** The qualification corpus is
  synthetic (`Q-CAP`), generated deterministically, and carries no experimental meaning.

## 3. Method

`tools/reviewer_capacity_qualification.py` builds synthetic packages at an exact part count and drives the real
`review_experiment` through a deterministic stub model.

- **Packages**: six documents in the roles the reviewer handles in normal operation (design, prompts, corpus,
  raw_outputs, scorer, evidence). The 34-part shape `(3, 1, 3, 8, 16, 3)` mirrors the document structure of a real
  six-document package at that scale. Every record line carries a unique `ref=` token, so observation loss,
  duplication, citation relocatability and document-boundary correctness are checkable by construction.
- **Scale**: 34 parts = 212,493 characters, above the 199,270-character package that raised the question.
- **Stub calibration**: fixed to the reviewer's own measured behaviour on the completed **G-INVAR** review (19 parts,
  100 grounded observations, 45 part statements, 30 document statements, 22 carried to final, 52 final inputs,
  7,800 final input characters). The calibration sets statements per unit, citations per statement and statement
  length; it is **not** re-tuned per scale. Rendered final-input line length reproduces the real review closely:
  155.7 chars/input against a measured 150.0.
- **Sensitivity band**: the same structure is run with a more compressive (`optimistic`) and a more verbose
  (`pessimistic`) model, so no capacity verdict can rest on one stub setting.

## 4. Results

Final input block against the 12,000-character budget:

| band | 19 parts | 28 parts | 30 parts | 32 parts | 34 parts |
|---|---:|---:|---:|---:|---:|
| optimistic | 2,997 (25.0%) | 4,189 (34.9%) | 4,370 (36.4%) | 4,640 (38.7%) | 5,048 (42.1%) |
| **nominal (calibrated)** | 6,227 (51.9%) | 9,296 (77.5%) | 10,398 (86.7%) | 10,987 (91.6%) | **11,869 (98.9%)** |
| pessimistic | 16,057 (133.8%) | 23,418 (195.2%) | 25,081 (209.0%) | 26,817 (223.5%) | 28,552 (237.9%) |

At the calibrated nominal rate, every scale from 28 to 34 completes with:

- required part coverage 1.00 at every scale (28/28, 30/30, 32/32, 34/34);
- 170 grounded observations at 34 parts, **zero silently dropped**, observation coverage 1.0;
- uncaptured accounting balancing exactly (136 cited + 34 carried = 170);
- **170/170 quotes relocating byte-exactly**, all inside their own part;
- all identifiers valid, no unknown references;
- every part unit, document unit and both final halves accepted;
- mutation guard passed with the source tree guarded;
- document units 9–10 against 37 slots — that ceiling is nowhere near binding;
- no truncation, no schema rejection, no retries.

Failure, where it occurs, is **clean**: status `incomplete`, `final_input_exceeds_budget` named in `missing`, coverage
still reported honestly upstream. Nothing degrades quietly.

## 5. The binding constraint

The limit is **level 3, the final synthesis input budget** (`FINAL_INPUT_BUDGET_CHARS`, checked at
`conscious_agent/experiment_review.py:1022`). It is not chunking, not part synthesis, not document synthesis, and not
the document-statement slot ceiling.

That budget cannot simply be raised, because it is pinned by the model's 8,192-token context window:

| stage | template + fixed extra | output reserve | max input block |
|---|---:|---:|---:|
| `final:first_half` | 1,893 chars | 3,072 tokens | 13,827 chars |
| `final:second_half` | 5,386 chars | 2,048 tokens | **13,488 chars** |

The configured 12,000 sits at 89% of the hard ceiling. The absolute maximum, with the entire safety margin spent, is
13,488 characters.

Fitting the nominal curve (≈376 characters per additional part):

- budget ceiling (12,000) is reached at **≈34.3 parts**;
- hard context ceiling (13,488) is reached at **≈38.3 parts**.

## 6. Verdict

**The reviewer passes structurally at 34 parts but cannot be qualified there.** The nominal margin is 131 characters
out of 12,000 — 1.1%. A qualification is a claim about reliability, and 131 characters of headroom on a budget driven
by model verbosity does not support that claim. The calibration rests on a single completed real review, and a model
marginally more verbose than that one sample exceeds the budget.

This is an **architectural ceiling, not a defect**. No infrastructure bug was found. Every evidence-handling property
held perfectly at 34 parts. The reviewer is context-bound at roughly 34–38 parts by construction.

Per requirement 9, the failure layer is classified above and the qualification runs are preserved in
`experiments/Q-CAP/capacity_sweep.json`.

## 7. Smallest repair, if capacity is wanted

Ordered by size. None is applied here; each needs its own review.

1. **Raise `FINAL_INPUT_BUDGET_CHARS` 12,000 → 13,000.** One constant. Buys ≈3 parts (to ≈37). Spends most of the
   context safety margin, and raises the risk of `context_limit_reached` at the final stages. Cheap but thin.
2. **Add one intermediate synthesis level** between document and final, compressing document statements plus carried
   inputs before the final block. Removes the coupling between part count and final input size entirely. This is a
   genuine architecture change to a frozen, qualified reviewer and is the honest fix if large packages are a
   recurring need.
3. **Raise the reviewer's context window** above 8,192 for the final stages only. Changes the model configuration
   rather than the reviewer, and re-opens the question of whether the reviewer's qualification transfers across
   context sizes.

Option 2 is the right repair if the requirement is real; option 1 is a patch that moves the wall by three parts.

## 8. What this qualification does not cover

- **No real-model run was performed at any scale.** The deterministic stub proves the *infrastructure* handles 34
  parts; it cannot prove the production model stays within the final budget, nor test real truncation, schema failure,
  citation collapse or synthesis degradation under larger input. A real 34-part run is ≈79 model calls, ≈3.3 hours on
  this host by the G-INVAR rate.
- **Detached-job reliability at 34 parts was not exercised.** The qualification drove `review_experiment` in-process.

## 9. Reproducing

```
python tools/reviewer_capacity_qualification.py --out experiments/Q-CAP/capacity_sweep.json
python tools/v2731_13_0_reviewer_capacity_tests.py
```

The sweep is deterministic; the suite is 33 adversarial checks covering deterministic rebuilds, oversized parts,
lossless chunking, record uniqueness, silent observation loss, fabricated quotes, cross-document quote borrowing,
budget overflow failing closed, and the reviewer's own limits being unchanged.
