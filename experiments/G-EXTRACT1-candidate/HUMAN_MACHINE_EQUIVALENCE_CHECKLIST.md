# G-EXTRACT1 Human/Machine Equivalence Checklist v3

This checklist indexes normative Markdown sections to machine paths. It is supporting evidence, not a substitute for direct comparison or adversarial review.

| Normative subject | Markdown | JSON path | Equivalence obligation |
|---|---:|---|---|
| Identity/status/authority | 1, 17 | `schema_version`, `experiment`, `final_verdict` | v3 identity, design-only state, and all execution flags false. |
| Historical boundary | 1 | `historical_binding` | Same closure, diagnostic, commit, failure permanence, and no historical reuse. |
| Question/causal limit | 2 | `research_question`, `causal_limit`, `hypotheses` | Same measurement claim and causal limits. |
| Scope | 3 | `scope` | Extraction-only, R2/R3, three tiers, same exclusions. |
| Corpus/counts | 3 | `corpus`, `phases`, `efficiency` | 35 per round, 30+5, A 420, B <=210, all 168 frozen precontact. |
| Operation grammar | 4 | `operation_definition_contract` | Exact regexes, opening, node count, sentence count/order, operation and unit templates, absence sentence, and prohibitions. |
| Family metadata | 5 | `family_assignment_contract.metadata_schema` | Same finite metadata fields, domains, and derivations. |
| Family predicates | 5 | `family_assignment_contract.priority_first_match` | Same E7->E5->E4->E1->E2->E3->E6 predicates; no subjective inputs. |
| Composed quotas | 6 | `composed_feature_requirements` | Same four rows, two fixtures each, eight distinct, no cross-row reuse. |
| Ambiguity inputs/outcomes | 7 | `ambiguity_contract` | Historical sentinel, observable inputs, nine first-match outcomes, exact precedence, semantic/containment split. |
| Ambiguity gates | 7, 11 | `ambiguity_contract.phase_a_gate`, `.phase_b_gate`, `cell_gates` | A 5 fixtures/10 observations and B 5/5; malformed output gets no recognition. |
| Exact values | 8 | `exact_value_contract` | Same integer/number/unit/string/JSON/date/time/threshold rules and false-clean bridge. |
| Similarity payload | 9 | `contamination_contract.similarity_payload`, `.canonical_schema_serialization`, `.boilerplate_exclusion` | Same bytes enter similarity and the same exact request spans are excluded by construction. |
| Normalization/tokenizer/ngrams | 9 | `contamination_contract.text_normalization`, `.tokenizer`, `.ngram` | Same ASCII authoring restriction, NFC/case/spacing rules, regex, 5-grams, Jaccard. |
| Fingerprint | 9 | `contamination_contract.fingerprint` | Same six finite components, component order, derivation structures, and canonical JSON bytes. |
| Pairwise contamination | 9 | `contamination_contract.pairwise_scope`, collision/near-replay fields | Historical/new, A/A, A/B, B/B, scored/reserve, reserve/reserve all covered. |
| Gold/adjudication | 10 | `gold_adjudication_contract` | Same gold contents, two reviewers, adjudication, freeze timing, and post-contact invalidation. |
| Reserve activation | 10 | `reserve_activation_contract` | One mapped reserve per slot, exact reasons/match dimensions, composed preservation, precontact only. |
| Gates | 11 | `cell_gates` | Same denominators, thresholds, classifications, and Phase B repeat guardrail exclusion. |
| Confidence language | 11 | `confidence_contract` | Benchmark-statistic interpretation only; same numeric values. |
| Cell transitions | 12 | `cell_state_machine` | Same transitions, machine-built B set, no pooling/reentry. |
| Integrity event taxonomy | 13 | `integrity_event_contract` | Same finite precontact, invalid, incomplete, abort events and precedence. |
| Primary verdict | 13 | `result_state_machine` | Same eight first-match verdicts and structured predicates. |
| Baseline text/template | 14 | `baseline_binding.system_text`, assembled-template fields | Exact bytes, only `{SUBJECT}`, same suffix/hash. |
| Baseline artifacts | 14 | `baseline_binding.existing_behavior_artifacts` | Same nine paths, SHA-256 values, Git blobs, and evaluator-only future identities. |
| Model/provider/config | 15 | `model_provider` | Same provider/version, names, manifests, blob hashes, and generation values. |
| Seed/schedule metadata | 15 | `sampling` | Same bases, formula, collision/order controls, legacy-prefix diagnostic. |
| Repair boundary/integration | 16 | `baseline_repair_boundary`, `integration` | No prompt repair/pooling/automatic update and same bounded future overlay. |
| Governance | 16, 17 | `failure_handling`, `governance`, `implementation_authorization_prerequisites` | Same preservation rules and separate authority at each phase. |
| Validator claim | 17 | `validation_claim_scope` | Structural consistency only; no scientific-validity or review-replacement claim. |

## Explicit reconciliation of former machine-only fields

- Model blob SHA-256 values are normative in Markdown section 15 and `model_provider.models`.
- Seed bases/formula are normative in Markdown section 15 and `sampling`.
- The legacy-sized eight-observation prefix is normative, reporting-only, and non-gating in both forms.

## Mechanical validation boundary

`validate_design.py` checks exact structured constants, artifact hashes/blobs, catalog and predicate structure, classifier coverage, integrity-event membership, gate counts, and selected Markdown/JSON equivalence. It does not prove that future fixtures are scientifically representative, that two authoring implementations are independent, or that the eventual experiment is valid. Those remain review and freeze obligations.
