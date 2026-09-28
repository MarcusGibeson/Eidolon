# G-ROUTE4 design review, round 4

Date: 2026-09-29.
Reviewed: `DESIGN_CANDIDATE.md` revision 4 (commit `f680782`).
Answered by: revision 5.

Gate: the operator's safety-gated rule, as in the earlier rounds.

Both reviewers were cut off by an API usage limit partway through. Each was resumed with its context intact and
completed its review.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | 0 BLOCKING, 4 MUST-FIX, 4 notes |
| B | Protocol, R7 reuse, implementability | 0 BLOCKING, 4 MUST-FIX, 7 notes |

**What the reviewers confirmed:**
- **Every number** reproduced exactly (Reviewer A). This includes the power table, the maximum size of 0.04998 at
  p = 0.10 over n ≤ 400, the seeds, the allocation counts and the family caps.
- **The amended D8 sentence** (Reviewer B): with the rule body, it discloses every shape rule enforced by both
  research validators. It states nothing false or stricter, and its sha256 matches.
- **The closure** (Reviewer B): the imported-unchanged modules import only each other, the standard library and a
  lazy `requests` import.

Both reviews were read-only, with no provider contact.

## Reviewer A

| # | Class | Finding | Disposition in revision 5 |
|---|---|---|---|
| N1 | MUST-FIX | The tokenizer was misdescribed. Author-defined template removal could make same-family Jaccard pass by construction. The within-cell pattern check was dropped silently for four classes. No path if the feasibility check fails. | G-ROUTE3's exact regex and 25%-frequency boilerplate rule, pooled with G-ROUTE3 fixtures. Template removal is a declared loosening: capped at 30% of tokens, trigram-set removal, reported with and without, and same-family pairs gated on the unremoved Jaccard at most 0.50. Family sharing replaces the pattern check in all classes, declared. An infeasible check goes back to design review. |
| N2 | MUST-FIX | The carried answer-position check cannot be satisfied at 4 vs 28. | Redefined: per-position counts within 1 in every cell of each corpus, preserved by replacements. |
| N3 | MUST-FIX | Adjudication still worked as a difficulty filter; replacements were not re-checked. | A pre-registered 10% random sample of agreed fixtures gets the same scrutiny. The residual filter is declared, touched fixtures are flagged, and P1 and research results are reported on the untouched subset. "Fix input" must name a derivability defect. Checks are re-run after every fix or replacement. |
| N4 | MUST-FIX | No family cap in A′ cells. | Each A′ cell has 4 fixtures from 4 different families. |
| Notes | — | The planning and synthesis signature spaces; pairwise-uniqueness feasibility (enums, action sets, structural ids); reserve size; the floor rationale wording. | Planning and synthesis are exempt from the fine-signature check (declared loosening). Closed-vocabulary values and `[A-Z][0-9]+` ids are excluded as construct vocabulary. The reserve totals are declared. The floor wording is an adaptation. |

## Reviewer B

| # | Class | Finding | Disposition in revision 5 |
|---|---|---|---|
| N1 | MUST-FIX | G-ROUTE1's `model_bindings.json`, read by the provider, was unlisted and unguarded. | Listed as imported-unchanged data and guarded. Bindings equality across G-ROUTE1, G-ROUTE3 and G-ROUTE4. The closure allows `requests`, and its version is recorded. |
| N2 | MUST-FIX | The grading equality proof was not specified; the stub scorer bypasses the forked grading. | A record-level grading differential: edge-case records through both scorers in separate processes. Equal normalization, operational, semantic and routing results; cell verdicts covered by the oracle. |
| N3 | MUST-FIX | The differential normalization did not cover identity-derived digests. | Identical injected inputs on both sides. Every derived digest is recomputed from its substituted preimage, and only `root_id` and run tokens are masked. Zero residual differences. |
| N4 | MUST-FIX | The reserve was not in the pre-seal checks; fixes and replacements were never re-checked. | The reserve is checked pairwise before the seal. Caps are checked per replacement. Checks are re-run after every fix or replacement and on the final corpus. |
| Notes | — | The D8 full assembly; the audit order; grep blind spots and provenance lines; the ambiguous fork list; reserve size; a resumed kill point at N−1; run-id digits. | The whole template assembly and its digest are frozen. The audit runs at the blueprint step, with a contradiction path. A seed-range test, and provenance lines allowed. Test and differential forks are named. Reserve totals declared. A kill point at N−1 added. `[0-9]{3,}`. |

## Next

Revision 5 goes to two fresh reviewers (round 5) under the same gate.
