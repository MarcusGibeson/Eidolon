# G-EXTRACT1 v7 Human/Machine Equivalence Checklist

Both design files are co-normative. The v7 human annex embeds exact structured normative objects; the validator parses them and compares them with the machine contract. This checklist is an index of checks and reviewer obligations, not a proof of complete prose equivalence or scientific validity.

| Normative area | Human location | Machine location | Check |
|---|---|---|---|
| Identity, scope, calls and authority | sections 1-2,16 | experiment/corpus/phases/governance | constants, zero authority/calls/fixtures |
| Historical closure and baseline | sections 1,15 | historical_binding/baseline_binding | literal SHA-256 and Git blobs |
| Canonical full prompt and literals | section 3 | operation_definition_contract | full bytes/SHA, literal rejects, 2-4 SUM |
| Neutral record/field/entity/string/enum atoms | section 7 and annex | lexical_neutrality_contract | catalog, generators, coaching rejects, 168 unique ordinals |
| Schema vocabulary and semantic tags | sections 4-5 | schema_type_contract | primitive/enum parse, exact tags |
| Typed source references and operations | sections 5-7 | operation_semantics_contract/fact_record_contract | valid/invalid types, cardinality, promotion and domains |
| Complete entity population | section 5.4 and annex | entity_population_contract | complete 2/3 populations, missing/mismatch/duplicate/unknown mutations |
| Output shape, binding and roles | section 6 | canonical_output_field_contract | eight exact keys, generated bound names, producer/schema identity |
| Exact enum identity | annex | exact_schema_identity_for_preserving_operations | wider/narrower/reordered schemas rejected |
| Family, secondary and composed derivation | section 8 | family_assignment_contract/composed_feature_requirements | mechanical family/features, distinct quota rows |
| Exact subtype matrix and domain allocations | section 17 and annex | subtype_allocation_contract | 35 slots, 5/family, promotions/operators/boundaries, E7 support distributions |
| E7 shape, parser and truncation | sections 9-10 and annex | ambiguity_contract/exact_value_contract | complete shape, parser paths, duplicates, accepted truncation false-clean |
| Exact reuse and atom typing | section 11 and annex | contamination_contract.exact_reuse_contract | whole-answer/identity/tuple bytes, schema-derived and upstream tags |
| Similarity tokenizer and scopes | section 11 | contamination_contract | frozen regex vectors/constants/six scopes |
| Fingerprint refinement and independence | sections 11,18 and annex | fingerprint/source_fact_layout_algorithm | end-to-end bytes, reversed node order, typed layout sequence |
| Reserve mapping and exact equivalence | sections 12,17 and annex | reserve_activation_contract/reserve_equivalence_contract | 28 slots, one claimant, fixed subtype01, byte profiles and mismatches |
| Repeat reduction and gates | section 13 | phase_a_fixture_reduction_contract/cell_gates | truth tables, thresholds, confidence arithmetic |
| Cell/integrity/verdict states | section 14 | cell_state_machine/integrity_event_contract/result_state_machine | no pooling/reentry, event/verdict vectors |
| Provider/model identities and seeds | section 15 | model_provider/sampling | bound identities/configuration/seed formula |
| Gold review and future authorization | sections 14,16 | gold_adjudication_contract/governance | all pre-contact freeze/review flags |

## Representation decisions

The historical schema reader is generic; the new-fixture lexical overlay is restrictive. Output names equal binding identifiers, so there is no unrendered alias decision. The stable ambiguity_contract container measures only explicit partial absence. Mechanical vectors live in design/checking artifacts and are not corpus or reserve items. The source-layout refinement is an explicit prospective correction recorded in both designs and the changelog.

The validator executes representative mechanics and exact normative-object comparisons. It does not establish author independence, population generalization, scientific validity, complete coverage of every prose claim, or the correctness of future production implementations. Two independently authored contamination implementations and independent corpus/gold reviews remain required before any later freeze.

## Blueprint boundary

The checkpoint permits independent rereview only. A separately authorized blueprint may instantiate frozen IDs, templates, schema/type rules, subtype slots, reserve profiles, schedules and file formats. It may not choose new lexical vocabularies, operation domains, enum compatibility, gold, sampling coverage, contamination semantics, reserve equivalence, thresholds, integrity states or governance authority.
