# G-EXTRACT1 Human/Machine Equivalence Checklist v4

This checklist indexes normative Markdown sections to machine paths. It supports direct review; it is not a substitute for comparison or scientific/adversarial review.

| Normative subject | Markdown | JSON path | Equivalence obligation |
|---|---:|---|---|
| Identity/status/authority | 1, 17 | `schema_version`, `experiment`, `final_verdict` | v4 identity, design-only state, all execution flags false. |
| Historical boundary | 1 | `historical_binding` | Same closure/diagnostic/commit and immutable failed status. |
| Scope/counts | 2, 3 | `research_question`, `scope`, `corpus`, `phases`, `efficiency` | Extraction-only R2/R3; 35 per round; A 420, B <=210. |
| Placeholder serialization | 4 | `operation_definition_contract.placeholder_type_system`, `.operand_object`, `.operation_node_object` | Same kinds, regexes, canonical literal/string bytes, and exact object shapes. |
| Operation rendering | 4 | `operation_definition_contract.catalog`, `.sum_operands`, `.rendering_test_vectors` | Same templates, kinds, graph/order rules, SUM bounds, and nine expected SUBJECT strings. |
| Historical absence | 4, 7 | operation/ambiguity historical fields | Exact schema, sentinel, sentence, and conditional inclusion. |
| Fixture/fact representation | 5 | `family_assignment_contract.fixture_representation`, `.fact_record_contract` | Same typed records, source rendering, segmentation, and entity indexing. |
| Family metadata/predicates | 5 | `family_assignment_contract.metadata_schema`, `.priority_first_match` | Same derivations and E7->E5->E4->E1->E2->E3->E6 precedence. |
| Secondary features/C3 | 5, 6 | `.secondary_feature_derivations`, `composed_feature_requirements` | Same mechanical tags and wrapped numeric-to-copy C3 graph. |
| Ambiguity parser/classifier | 7 | `ambiguity_contract` | Same operational/semantic split, duplicate rule, ten outcomes, vectors, and A/B gates. |
| Exact values | 8 | `exact_value_contract` | Same type, JSON, date/time, duplicate, and false-clean bridge rules. |
| Similarity/tokenizer | 9 | `contamination_contract.text_normalization`, `.tokenizer`, `.ngram` | Same normalization, precedence, regex, vectors, 5-grams, and Jaccard. |
| Fingerprint/layout | 9 | `.fingerprint`, `.source_fact_layout_algorithm` | Same six components, exact derivations/serialization, six layouts, and rejection vectors. |
| Contamination independence | 9 | `.independent_implementation_contract`, pairwise/collision fields | Same all-pairs scope, no shared normative code, byte differential, and replay limits. |
| Gold/adjudication | 10 | `gold_adjudication_contract` | Same independent review, precontact resolution/freeze, and post-contact invalidation. |
| Reserve activation | 10 | `reserve_activation_contract` | Same 28 slots, IDs, ordered primaries, profiles, single-claim algorithm, and rechecks. |
| Gates/confidence | 11 | `cell_gates`, `confidence_contract` | Same denominators, thresholds, guardrails, and benchmark-only interpretation. |
| Cell transitions | 12 | `cell_state_machine` | Same machine-selected B entrants, no pooling/reentry. |
| Integrity events | 13 | `integrity_event_contract` | Same finite blocker/invalid/incomplete/abort catalogs and event vectors. |
| Primary verdict | 13 | `result_state_machine` | Same first-match predicates and evaluated structured fact vectors. |
| Baseline artifacts | 14 | `baseline_binding` | Same exact text/template, paths, SHA-256, blobs, and v2 operation renderer. |
| Models/seeds | 15 | `model_provider`, `sampling` | Same provider/models/hashes/configuration and seed formula. |
| Governance | 16, 17 | `failure_handling`, `governance`, prerequisites | Same preservation and separate-authority boundaries. |
| Validation claim | 17 | `validation_claim_scope` | Structural/cross-representation consistency only; no scientific-validity claim. |

## Mechanical boundary

`validate_design.py` executes the frozen vectors and verifies exact structured constants and historical bindings. It does not establish corpus representativeness, future implementation correctness, provider behavior, or scientific validity. Those remain separately governed review, authoring, implementation, pilot, and freeze obligations.
