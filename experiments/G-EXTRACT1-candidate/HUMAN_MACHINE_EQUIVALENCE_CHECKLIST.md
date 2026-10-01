# G-EXTRACT1 Human/Machine Equivalence Checklist

Human source: `DESIGN_CANDIDATE.md`

Machine source: `DESIGN_CANDIDATE.json`, schema `g-extract1.design-candidate.v2`

The deterministic checker must pass every row before the candidate may be presented for design rereview.

| Binding subject | Human section | Machine JSON path | Required equivalence |
|---|---|---|---|
| Identity and authority flags | 1, 23 | `experiment`, `governance` | Design-only; all authoring, implementation, provider, and execution authorities false. |
| Historical G-ROUTE4 binding | 1 | `historical_binding` | FAILED status, commit, closure digest, diagnostic digest, immutable history. |
| Scope and six cells | 4, 5 | `scope`, `phases` | Extraction only; R2/R3 x small/mid/large. |
| Corpus and call counts | 5, 6 | `corpus`, `phases`, `efficiency` | 70 A, 70 B, 28 reserves, 420 fixed calls, 210 maximum B, 630 maximum. |
| Primary family assignment | 7 | `family_assignment_contract` | One frozen first-match primary family and secondary tags. |
| Composed feature quotas | 7 | `composed_feature_requirements` | Four quota rows, two distinct fixtures each, eight total per phase/round. |
| Ambiguity outcomes | 8 | `ambiguity_contract.primary_outcome_precedence` | Same ordered eight outcomes and semantic/containment treatment. |
| Ambiguity gates | 8 | `ambiguity_contract.phase_a_gate`, `.phase_b_gate` | A: 5 fixtures/10 observations; B: 5/5; zero evasive/malformed credit. |
| Contamination/replay | 9 | `contamination_contract` | Exact, lexical, fingerprint, near-replay, A/B, and human-review rules. |
| Exact values and normalization | 10 | `exact_value_contract` | Integer/number/unit/string/JSON/date/time semantics and operational disagreement rule. |
| Gold/adjudication | 11 | `corpus`, `governance`, `implementation_authorization_prerequisites` | Pre-contact gold freeze and independent review/adjudication. |
| Reserve activation | 12 | `reserve_activation_contract` | One mapped reserve, enumerated reasons, refreeze, no post-contact replacement. |
| Confidence interpretation | 13, 18 | `confidence_contract` | Same values; benchmark decision statistic only; no IID population claim. |
| Gate classifications | 13 | `cell_gates` | Independent gates versus enforced redundant pass guardrails. |
| Cell carry-forward | 14 | `cell_state_machine` | Same transitions, machine-derived selector, no pooling/re-entry. |
| Primary result verdict | 15 | `result_state_machine` | Exactly one verdict with identical first-match precedence and predicates. |
| Baseline artifact binding | 16 | `baseline_binding` | Same system text, paths, SHA-256, Git blobs, variable slots, and forbidden content. |
| Models/configuration | 17 | `model_provider` | Same three model identities and exact generation configuration. |
| Sampling | 17 | `sampling` | A=2 repeats, B=1, seed bases, balanced order, frozen schedules. |
| Failure/repair boundary | 19 | `failure_handling`, `baseline_repair_boundary` | No retries, in-place repair, tuning, pooling, or post-contact mutation. |
| Integration boundary | 20 | `integration` | Evidence only, extraction-only candidate overlay, separate authorization. |
| Governance | 21, 23 | `governance`, `implementation_authorization_prerequisites` | All freezes/audits before contact and separate later authorizations. |
| Remaining limitations | 22 | `remaining_nonblocking_limitations` | Same five non-blocking limitations. |

Manual rereview remains required. Passing this checklist proves document consistency, not scientific validity.
