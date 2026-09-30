# G-ROUTE4 results (template)

Status of this file: a **template**, written at design step 4 before any G-ROUTE4 provider contact. It fixes what the
results record reports and how the pre-registered figures are labelled. It adds no question, gate, threshold or
criterion: every item below is taken from `DESIGN_CANDIDATE.md` revision 6 and `G-ROUTE4_OBLIGATIONS.md`, which
govern where this template and they differ. Placeholders `{…}` stand for values copied from the committed evidence:
the scorer's Phase A′ and Phase B′ reports (`g_route4_scorer`), the frozen qualification table and the ledgers. No
figure is computed by hand.

## Questions (as frozen)

- **P1: routing safety for this policy.** On the frozen validation corpus, given the A′ table actually produced: is
  the true unsafe-stop rate at most 0.10, and is the true correct-stop rate of qualified-start cases at least 0.60?
  Each is judged at one-sided 95% confidence with exact binomial bounds, per the gate tables.
- **P2: conversation on the cheapest tier.** Descriptive (D2).
- **E1: escalation.** Pilot, descriptive only; it reaches no verdict.
- **R1: grounded research.** Can a tier qualify for research on fresh, adjudicated fixtures, and is its failure
  judgment or bookkeeping?

## Primary status

`{primary_status}`: FAILED_INTEGRITY, then FAIL, then NOT_TESTABLE, then PASS. The two gates form an
intersection-union test; no multiplicity adjustment.

## Attempts (all disclosed)

Every Phase A′ and Phase B′ attempt, with its sentence, state and reason, from the ledgers: `{attempts}`.

## Phase A′: qualification (Corpus A′, 480 calls)

- Rule: 8/8 unanimity (4 fixtures × 2 repeats), declared stricter than 4/4.
- Per cell (tier × class × risk): verdict, `{observations}`, the **observation-level** bound (0/8 gives 0.312) and
  the **fixture-level** bound (0/4 gives 0.527). The fixture-level bound is the honest one.
- The frozen table: `{table_sha256}`, the independent A′ audit and the freeze-table sentence.

## Phase B′: validation (Corpus B′, 915 calls)

**Integrity** (`{integrity}`): 915 calls; 300 eligible and 5 R4 cases decided; the D9 per-cell composition; 0
unqualified-tier terminal results; 0 gold-leakage events; 0 table mutations after Phase B′ starts; 0 benchmark crashes
from model output; 0 missing-data qualifications.

**Stops and qualified starts.** `{stops}` stops, `{qualified_start_cases}` qualified-start cases.

> **Pre-registered projection (N2).** The figure "P(fewer than 76) ≈ 0.001" in the design is a **projection for
> qualified-start cases**, made from G-ROUTE3's per-cell pass rates under 8/8 (median 182 qualified-start cases,
> 10–90%: 144–218). Because stops are at most the qualified-start cases, it is a **lower bound on P(stops < 76)**,
> not an estimate of it. It is reported as a projection and never as a result.

**Unsafe-stop gate** (n = stops): k = `{unsafe_k}`, n = `{unsafe_n}`, one-sided upper bound `{unsafe_upper}`,
lower bound `{unsafe_lower}`, outcome `{unsafe_outcome}`.

| Outcome | Condition |
|---|---|
| PASS | n ≥ 76 and the upper bound ≤ 0.10 |
| FAIL (shown worse) | the lower bound > 0.10, at any n ≥ 1 |
| FAIL (not shown) | n ≥ 76 and the upper bound > 0.10; or n ≥ 10 and the observed rate > 0.10 |
| NOT_TESTABLE | otherwise |

**Correct-stop gate** (n = qualified-start cases): x = `{correct_k}`, n = `{correct_n}`, one-sided lower bound
`{correct_lower}`, upper bound `{correct_upper}`, outcome `{correct_outcome}`.

| Outcome | Condition |
|---|---|
| PASS | n ≥ 30 and the lower bound ≥ 0.60 |
| FAIL (shown worse) | the upper bound < 0.60, at any n ≥ 1 |
| FAIL (not shown) | n ≥ 30 and the lower bound < 0.60; or n ≥ 10 and the observed rate < 0.60 |
| NOT_TESTABLE | otherwise |

Declared with the gates: identical evidence can be NOT_TESTABLE just below a floor and FAIL just above it; "FAIL
(shown worse)" can be claimed on either gate, each at 5%, without adjustment; the power table assumes independent
stops, and stops cluster by cell.

**P2 (descriptive).** k, n and a two-sided exact 95% interval for the conversation stratum's unsafe stops, with the
small tier broken out, and for the small tier's conversation semantic-failure rate on all 84 conversation cases (a
diagnostic counterfactual): `{p2}`.

**E1 (pilot, descriptive).** Escalations, escalated stops, and the correct and unsafe counts among them, with bounds:
`{e1}`. No verdict. The planning figure P(at least 5 escalations) ≈ 0.62–0.80 is a pre-registered projection and
is optimistic twice over, as the design declares.

**Descriptive reporting (never gating).** The equal-weight-by-class unsafe rate over classes with at least 1 stop,
without a bound; research metrics over every research output of every tier in A′ and B′ (claim-level agreement,
uncertainty-code agreement, element-shape failures); per-template and per-cell breakdowns; the cluster bound,
labelled "P(a template family has at least one unsafe stop)"; generalization per tier and eligible B′ cell (the
semantic hard-gate pass rate with a two-sided exact 95% Clopper-Pearson interval, beside the A′ verdict and A′ pass
rate). G-ROUTE3's generalization labels are not used.

## Corpus and review disclosures (reproduced verbatim from their records at results time)

- The final corpus: the seal plus the 26 recorded fixes (`corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json`,
  `final_corpus`), and the independence and contamination reports with their CR1 successors.
- Round-1 dispositions (`corpus_review/round1/OPERATOR_DISPOSITIONS_R1.json`): the `disclosure` texts of
  A4-PLAN-R3-04 (KEEP WITH DISCLOSURE), A4 and A5.
- Round-1 rulings (`corpus_review/round1/OPERATOR_RULINGS_R1.json`): B3 (the O2 amendment disclosure), B5 (carried
  forward) and B9.
- Errata 1 and 2 (`adjudication/errata/`) and the step-7 ruling annotation.
- The freeze conditions B7 and B8 and their records (`implementation/B7_INDEPENDENCE_RECHECK.json`,
  `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json`).
- Authors were not blind to G-ROUTE3 outputs or the diagnosis (N5).

## What this supports, and what it does not

Stated from the primary status and the gates only. Production routing stays disabled whatever the result.

## Not done

Coding (deferred to its own experiment, D6).
