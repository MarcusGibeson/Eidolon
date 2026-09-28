# G-ROUTE4 design review, round 2

Date: 2026-09-28.
Reviewed: `DESIGN_CANDIDATE.md` revision 2 (commit `c33e5e1`).
Answered by: revision 3.

Gate: the operator's safety-gated rule, as in round 1.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | 0 BLOCKING, 6 MUST-FIX, 11 notes |
| B | Protocol, R7 reuse, implementability | 0 BLOCKING, 11 MUST-FIX, 5 notes |

**What both reviewers confirmed:**
- The round-1 blocking findings are resolved, by all-tier Phase B′ (D1) and coding deferred (D6).
- The three-way gate rule is coherent. Reviewer A brute-forced every (n, k) with n ≤ 300: PASS and FAIL never
  overlap, and every G-ROUTE3-standard failure is FAIL.
- Every composition and per-cell bound figure checks out.

Both reviews were read-only, with no provider contact.

## Operator decisions after this round (2026-09-28)

| # | Decision |
|---|---|
| D8, exact wording | Approved. The full-disclosure research sentence (in revision 3, verbatim) discloses every shape rule the frozen research validator enforces. |
| D8, scope | All five classes are audited. Gaps are closed in the freshly authored fixture prompts; G-ROUTE1's system prompts stay byte-identical. |
| D10, new | The operator starts each gold-adjudication batch in chat. Every Claude session is logged and sealed. |

## Reviewer A

| # | Class | Finding | Disposition in revision 3 |
|---|---|---|---|
| 1 | MUST-FIX | The power table reported its end values, not the range. The stop-rate basis was unstated. The reachable NOT_TESTABLE was undeclared. | The power table shows the minimum and maximum over n = 120–219, with the basis stated. The block structure and the NOT_TESTABLE configurations are declared. |
| 2 | MUST-FIX | The research allocation was infeasible (4 fixtures vs 8 patterns; 18 is not divisible by 8; R4 cell of 1). | An exact per-cell pattern table for A′ and B′, and exact `single_lineage_support` counts. The coverage gap between A′ and B′ is declared. |
| 3 | MUST-FIX | The A′↔B′ independence standard was undefined; the cap was B′-only; the planning change was undeclared. | Independence criteria: what may be shared, what must be fresh, and a 4-gram Jaccard limit of 0.5, including against G-ROUTE3. Families are shared jointly by A′ and B′. The planning construct change is declared. |
| 4 | MUST-FIX | The integrity list omitted G-ROUTE3 gates. | Every G-ROUTE3 integrity gate is listed. |
| 5 | MUST-FIX | The D8 audit extension had no operator record or remedy. | Operator decision after round 2. The remedy goes into fixture prompts. The research sentence already discloses every enforced shape. |
| 6 | MUST-FIX | No B′ cell-success rule; G-ROUTE3's generalization labels break. | Generalization is redefined as the per-cell B′ pass rate with an exact interval beside the A′ verdict. The labels are not used. |
| Notes | — | Floor rationale; exact forms and n = 0; the E1 model; the estimand given the realized table; the direction of oversampling; the equal-weight rate; the cluster bound; adjudication ties; P2 staleness; the 0.776 comparison; traceability of D3, D5 and D7. | All answered in the Gates, Corpora and decision sections. S1 is renamed E1. The P2 counterfactual rate is added. D3's rewording is recorded as a consequence of D9. |

## Reviewer B

| # | Class | Finding | Disposition in revision 3 |
|---|---|---|---|
| N1 | MUST-FIX | The identity constants were incomplete. | A full table covers call-id, fixture namespace, schema and contract strings, salts, candidate id and superseded list, evidence author, index file, root message, lease tag and pinned thread. A grep test enforces it. |
| N2 | MUST-FIX | The seed range overflowed. | The formula is stated. The bases are 470000 and 480000, disjoint ranges are declared, and tiers share a group seed. |
| N3 | MUST-FIX | The import-or-fork plan and guarded set. | A per-module import-or-fork table and a complete guarded list. Forked grading code carries a proof of equality. The carried scientific inputs are named. |
| N4 | MUST-FIX | The coding exclusion in the R7 fork. | The loader refuses coding. Execution kinds are forbidden, so any such entry is an integrity failure. No worker. The coding runner is never loaded (digest-checked). The certification drops, additions and keeps are listed. |
| N5 | MUST-FIX | The B′ preconditions were truncated. | R7 §10 items 1–11 apply unchanged except 60 cells, the 8-observation shape and G-ROUTE4 identity. |
| N6 | MUST-FIX | G-ROUTE3 scoring shapes. | Denominators, the thresholds schema, the per-cell composition check and generalization are redefined. The secondary verdict and the "excluding coding" metric are removed. |
| N7 | MUST-FIX | The differential was undefined. | A lifecycle differential on a shared non-coding synthetic schedule (equal apart from identity), plus an independent oracle for 8/8, the gates and the bounds. |
| N8 | MUST-FIX | Data-root refusal and sentences. | G-ROUTE3's side already holds and is test-asserted. G-ROUTE4's check is read-only and comes before setup, the lease or any write. Verbatim ASCII sentence templates for all 8 commands. |
| N9 | MUST-FIX | Adjudication residuals (a–i). | Gold and reserve sealed first. One sealed answer per session, with no re-runs and every invocation logged. A blind second and third adjudicator, and a decision table. The operator only for three-way disagreement, against the derivability rule, and declared not blind. At most one fix per fixture, with re-adjudication. Blueprint-matched replacements. Halt on exhaustion, never shrink. Disagreement defined by the frozen validator. One fixture per session. Pretesting ban limited to pinned and Ollama models. |
| N10 | MUST-FIX | The allocation was infeasible. | As A-2. |
| N11 | MUST-FIX | D8 provenance, audit remedy and exact bytes. | Operator decision recorded. The remedy is fixture prompts. The exact bytes are in a code block, with the separator and punctuation stated. |
| Notes | — | "Never re-read" wording; the large-tier statement; the runbook and ruling 12; who audits; model bindings and Ollama version; authorization of adjudication. | "Never rescored or reinterpreted". The large-tier statement is corrected. The runbook states ruling 12. Audits are by fresh sessions. The bindings and Ollama 0.34.3 are named and frozen. D10 covers adjudication. |

## Next

Revision 3 goes to two fresh reviewers (round 3) under the same gate.
