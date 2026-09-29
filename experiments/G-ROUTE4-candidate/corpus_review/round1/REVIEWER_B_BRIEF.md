# G-ROUTE4 external corpus review, round 1: Reviewer B brief

You are **Reviewer B**, one of two fresh, independent reviewers for design step 3.7 of G-ROUTE4 (the external corpus
review). Your focus is **protocol and provenance**: whether the sealed corpus, the adjudication, the fixes and the
reports meet the frozen design and obligations. Reviewer A covers the corpus content (derivability of gold). You work
alone; do not look for, read or wait for the other reviewer's work.

## Rules (read-only review)

- Repository (git worktree): `C:\Users\marcu\Eidolon-g4adj`, branch `g-route4/adjudication`. Review the commit that is
  `HEAD` when you start, record its id, and confirm that the digests in
  `experiments/G-ROUTE4-candidate/corpus_review/round1/REVIEW_MANIFEST.json` match the files.
- **Do not modify anything in the repository**, and do not run any script that writes into it (several builders and
  checkers write their reports into the repository). Allowed git commands are read-only ones only (`log`, `show`,
  `rev-parse`, `cat-file`, `ls-tree`, `diff`, `merge-base`, `status`, `for-each-ref`, `reflog`,
  `archive -o <file in your scratch folder>`). No commit, checkout, switch, reset, stash, branch, tag, fetch, pull or
  push. Do not touch `C:\Users\marcu\Eidolon` (another checkout) at all.
- Your scratch folder is `C:\Users\marcu\AppData\Local\Temp\claude\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3\scratchpad\corpus_review_r1\reviewer_B\`.
  Write only there. To re-run repository code, export the commit there first (`git -c core.autocrlf=false archive`)
  and run the copy. Do not open `...\scratchpad\corpus_review_r1\reviewer_A\`.
- **No network, no model and no provider contact of any kind.** Run Python only as `python -B`, with
  `PYTHONPATH=C:\Users\marcu\AppData\Local\Temp\claude\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3\scratchpad\guard`
  (it blocks sockets). Never read anything under `C:\Users\marcu\.config\`. Do not run the adjudication harness's
  `run` command or anything that could send a request.
- Do not start or propose starting any later G-ROUTE4 stage. You recommend; the operator decides.

## Gate (the operator's safety-gated rule, as in every G-ROUTE4 review)

**BLOCKING** means one of the following: 1. a repeated call; 2. best-of-N or optional stopping; 3. contact without
the correct sentence; 4. a silent scientific or grading change; 5. a contradiction with an operator decision or a
standing constraint. **MUST-FIX** means a defect to fix before the freeze. **NOTE** is anything else worth recording.
The external corpus review is accepted at 0 BLOCKING with every MUST-FIX resolved. Classify each finding yourself,
naming the class for any BLOCKING finding.

## Frozen texts you judge against

- `experiments/G-ROUTE4-candidate/DESIGN_CANDIDATE.md` (accepted revision 6): "Gold adjudication" steps 1–13, the
  independence standard, the order of work and the standing constraints.
- `experiments/G-ROUTE4-candidate/G-ROUTE4_OBLIGATIONS.md` (overrides conflicting design wording): every item whose
  verification stage includes **CR**: O1, O2, O3, O4, O5, O6, N3, N5 (the parity check itself is Reviewer A's), N8.
- `experiments/G-ROUTE4-candidate/blueprint/` (frozen at `1156d06`) and `sealed/` (seal `50e6b46`, tag `g-route4-seal`,
  `SEAL_MANIFEST.json`, `SEAL_NOTES.md`, `O3_IDENTIFIER_DECISION.md`).

## The records under review (all under `experiments/G-ROUTE4-candidate/`)

- `audit_sample/AUDIT_SAMPLE.json`, `blueprint/audit_sample.py`.
- `adjudication/`: `O2_AMENDMENT_2026-09-29.md`, `adjudicator_config_amended.json`, `o2_amendment.py`,
  `g4_adjudicate.py`, and `runs/<run>/` for the four runs (`journal.jsonl` hash-chained, `raw/`, answers, scores,
  decisions, operator decisions, reports); `fixes/` (both rounds: fix records, fix checks, the latent-defect reports);
  `A_MAIN_CLOSURE.json`, `B_MAIN_CLOSURE.json`; `reports/` (the builders).
- `INDEPENDENCE_REPORT.json`, `CONTAMINATION_ANALYSIS.md`.
- `corpus_review/round1/` (the materialized final corpus and the manifest).

## Your work

1. **O1.** Git parentage shows exactly one seal commit, whose parent is the blueprint commit; the committed sample is
   recomputed from the frozen formula and matches; the first adjudication session is logged after the sample commit.
2. **O2, in depth.** The configuration frozen in the seal; the recorded amendment, its timing relative to the first
   provider contact, and whether O2's change rule was met; one configuration digest throughout every session log;
   invocation ordinals per slot showing no earlier invocation with a final message that went unused; the binding-
   answer rule, parse failures counted as disagreements, the single no-answer retry, and how the one provider
   rejection and the refusals were handled. State plainly whether adjudication under `7691126e…` satisfies O2.
3. **Adjudication procedure (design steps 4–9, 11–13).** A′ full treatment; B′ first adjudicator then two more;
   the audit sample's full treatment for sampled agreed fixtures and the pre-registered full-cell consequence;
   answers committed before comparison (check commit order); operator decisions recorded with reasons and options
   limited to the three permitted; at most one fix per fixture, re-checked and re-adjudicated from scratch; no
   replacement; the counts in both closure records reproduce from the run records.
4. **Independence (O3, O4, O5, O6, N3, N7, N8).** Do the scope strings and `INDEPENDENCE_REPORT.json` show what each
   obligation requires? Reproduce the report in your scratch copy and compare. Is the fix-text exemption as narrow as
   claimed? Is the tool the right one for this stage, as the report states it?
5. **Seal and frozen inputs.** Sealed corpus, gold, ledger, reserves, audit sample, blueprint, validators and
   thresholds unchanged since the seal; G-ROUTE1 and G-ROUTE3 files unchanged; `main` and `g-route4/seal` not moved;
   the final corpus in `corpus_review/round1/` equals the seal plus exactly the 20 recorded fixes.
6. **Reports and disclosures.** Check the numbers and statements in `CONTAMINATION_ANALYSIS.md`,
   `A_MAIN_CLOSURE.json` and `B_MAIN_CLOSURE.json` against the records. Are the recorded disclosures (latent defects
   and their addendum, residual limitations, declared filters and blind spots, operator non-blindness, the O2
   amendment, adjudication exposure) accurate and complete? Is anything that should be disclosed missing?

## Your output

Write your complete report to `...\scratchpad\corpus_review_r1\reviewer_B\REPORT.md`. It is preserved verbatim as your
review, so make it self-contained:

1. The `HEAD` commit you reviewed, and whether the manifest digests matched.
2. **Coverage first:** what you verified, what you reproduced and how, and anything you could not check. Partial
   coverage must be stated as partial.
3. A findings table: id (B1, B2, …), class (BLOCKING with its number / MUST-FIX / NOTE), artifact or fixture,
   evidence, and the frozen remedy that would apply.
4. A verdict per work item 1–6, with an explicit O2 verdict.
5. One final line: `VERDICT: <CLEAN|FINDINGS> — BLOCKING <n>, MUST-FIX <n>, NOTE <n>`.

Then reply with only that final line and the sha256 of `REPORT.md` (bytes as written).
