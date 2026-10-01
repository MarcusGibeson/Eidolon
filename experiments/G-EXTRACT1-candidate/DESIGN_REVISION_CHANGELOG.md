# G-EXTRACT1 Design Revision Change Log

Revision base: `4484500de7a7d35e534b1f3884906b6749a213b9`

This record maps the first independent adversarial review to design candidate v2. `Resolved` means the candidate now
contains a prospective deterministic rule; it does not substitute for independent rereview.

| Review finding | Disposition | Revision evidence and justification |
|---|---|---|
| Ambiguity/nonacceptance was undefined and could reward evasion | Resolved in candidate | Added `g-extract1.ambiguity-scoring.v1`, an explicit unknown sentinel, ordered outcome table, separate semantic-recognition and containment measures, 10/10 Phase A and 5/5 Phase B observation gates, and zero semantic credit for malformed/refused/truncated/evasive output. |
| Baseline prompt was not enforceably unchanged | Resolved in candidate | Added `g-extract1.baseline-binding.v1` with paths, SHA-256, Git blobs, exact system text, allowed variable slots, forbidden coaching, and evaluator-only future scorer identities. |
| Final result labels overlapped | Resolved in candidate | Replaced unordered labels with one first-match primary verdict state machine and deterministic predicates for invalid, blocked, aborted, incomplete, no-A-pass, all-B-fail, mixed, and all-entering-pass outcomes. |
| E5/E6/E7 family boundaries overlapped | Resolved in candidate | Added first-match primary-family precedence and immutable secondary-feature tags. |
| Family quotas did not require composed reasoning | Resolved in candidate | Added eight distinct composed fixtures per phase/round: two each for arithmetic->threshold, date/time->threshold, aggregation->exact binding, and entity->field binding. |
| Structural-signature rule could exclude legitimate failure-class follow-up | Resolved in candidate | Replaced operation-signature ban with a six-component full-case fingerprint and near-replay rule; same operation class is allowed with at least two other structural differences and fresh values/entities. |
| Exact-value and representation rules were incomplete | Resolved in candidate | Added `g-extract1.exact-value-comparator.v1` covering integer/number forms, exponent notation, negative zero, units, strings, Unicode, labels, JSON duplicates/order/nulls, dates, and times. Integer `5.0` is now explicitly invalid, matching the baseline operational validator. |
| Reserve use could be opportunistic | Resolved in candidate | Added one-to-one pre-contact reserve mapping, enumerated activation reasons, exact match dimensions, mandatory refreeze/review, and stop behavior when the sole reserve fails. |
| Clopper-Pearson language could imply population generalization | Resolved in candidate | Bounds are now called benchmark decision statistics; IID/natural-population claims are explicitly forbidden. |
| Gate redundancy was unexplained | Resolved in candidate | Family floor, binding zero-error, and correlated false-clean are labeled enforced redundant pass guardrails; independent gates are separately identified. |
| Human/machine contract differed | Resolved in candidate, pending rereview | Machine v2 now encodes ambiguity, families, compositions, reserves, exact values, prompt binding, state machines, contamination, failure handling, and governance. A deterministic equivalence checker and checklist were added. |
| Phase A to Phase B carry-forward lacked a complete state machine | Resolved in candidate | Added exact per-cell states and a machine-derived sorted Phase B selector with no operator additions, omissions, or re-entry. |
| Governance needed explicit pre-contact boundaries | Resolved in candidate | Machine contract now lists all pre-contact freezes/audits and separate implementation, pilot, Phase A, and Phase B authorizations. |
| Family floor is mathematically redundant with 29/30 | Intentionally retained | It is an enforced denominator/family-attribution guardrail, not independent evidence. |
| Binding and correlated false-clean gates are redundant with zero false-clean | Intentionally retained | They remain named, enforced diagnostics so the relevant failure modes cannot disappear in aggregate reporting. |
| Fixture IID independence cannot be established | Unresolved non-blocking limitation | The design makes no population claim; lineage, fingerprint, lexical, and human review controls reduce but do not prove dependence. |
| Provider does not attest all generation options internally | Unresolved non-blocking limitation | A later separately authorized mechanical pilot may verify request submission and observable behavior only. |
| Runtime estimate may drift | Unresolved non-blocking limitation | Estimates remain planning values based on preserved G-ROUTE4 means. |

No historical artifact was edited, no scored or reserve fixture was authored, and no provider/model contact occurred.
