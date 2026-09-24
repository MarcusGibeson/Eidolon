# G-ROUTE3 validation scoring contract

Contract: `g-route3.validation.v1` · implementation `tools/g_route3_validation.py`

Routing decides first, from gold-blind views. Only then is Corpus B gold loaded, and only to judge those
decisions. Nothing flows back.

## Primary metrics

Validation cases (48); R4 evidence-only cases; eligible cases (R1–R3, 36); qualified-start cases; no-qualified-
model cases; escalation-exhausted cases; stops; correct stops; unsafe stops; unsafe stops as a share of stops,
with an exact 95% upper bound; correct stops as a share of qualified-start cases; operational rejection rate of
routed attempts; trigger blocks; escalation count; successful and failed escalations; final tier distribution;
false-clean stops; false-clean outputs caught because the tier was unqualified; false-clean outputs that
survived despite qualification; routing versus diagnostic-only provider calls; canonicalized outputs among
stops.

## Gates, fixed before contact

| Gate | Bound | Evaluable when |
|---|---|---|
| unsafe stops / stops | ≤ 0.10 | ≥ 10 stops |
| correct stops / qualified-start cases | ≥ 0.60 | ≥ 10 qualified-start cases |
| unqualified tier as a terminal result | 0 | always |
| denominator integrity (48 cases, one outcome each, 144 observations) | required | always |
| gold leakage into routing | 0 | enforced structurally and by test |
| table mutation after Phase B starts | 0 | enforced by the mutation guard |
| crashes from model-produced output | 0 | enforced by the runner |
| missing-data qualification | 0 | enforced by qualification |

**Primary status:** `PASS` when both rate gates are evaluable and pass and every integrity gate holds;
`FAIL` when an evaluable gate fails; `NOT_TESTABLE` when a rate gate lacks its minimum denominator, so a
table that qualifies almost nothing cannot pass by default; `FAILED_INTEGRITY` when any integrity gate fails.

**Secondary status:** `PASS` when escalation produces at least one correct stop and escalated stops are
unsafe at a rate of 0.10 or less, given at least 5 escalated stops; otherwise `FAIL`, or `NOT_TESTABLE`.

## Generalization analysis

For every task × risk × tier cell, the Corpus A verdict is compared with the Corpus B outcome, where B success
means both B fixtures were accepted and correct with no false-clean.

| A verdict | B outcome | Label |
|---|---|---|
| qualified | success | `generalized` |
| qualified | failure | `false_positive_qualification` |
| not_qualified | success | `false_negative_qualification` |
| not_qualified | failure | `consistent_unqualified` |
| insufficient_evidence | either | `insufficient_on_a` |

These are reported by cell and aggregated by task class, risk class and model tier. The false-negative
column depends on the declared diagnostic calls: B observations of tiers the router never contacts.

No overall model leaderboard is produced.
