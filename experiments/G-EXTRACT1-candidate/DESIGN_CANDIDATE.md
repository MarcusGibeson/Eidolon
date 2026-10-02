# G-EXTRACT1 Design Candidate v5

Status: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_5`

This document and `DESIGN_CANDIDATE.json` are co-normative. The machine contract is `g-extract1.design-candidate.v5`. This checkpoint authorizes design rereview only. It authorizes no blueprint, fixture, implementation, pilot, freeze, or execution work.

## 1. Historical boundary and question

G-ROUTE4 remains CLOSED FAILED. Its closure and unsafe-stop diagnostic are immutable and are used only to define failure families. G-EXTRACT1 asks whether a larger, prospectively stratified structured-extraction qualification test can identify R2/R3 model-tier cells that remain safe and useful on separately authored validation fixtures under the byte-bound historical prompt behavior.

The design does not identify prompt wording, model weights, provider internals, or sampling as a unique cause. It first measures the existing baseline. Prompt repair requires a different experiment identity and fresh corpora.

Scope is structured extraction only, R2 and R3, for `qwen2.5:7b`, `qwen3:14b`, and `qwen3.8:27b`. Grounded research, conversation, planning, synthesis, coding, timezone conversion, production routing, and prompt repair are excluded.

## 2. Corpus and phases

Each phase and risk round contains seven primary families with five fixtures each: 35 fixtures, comprising 30 determinate fixtures and five E7 explicit-partial-absence fixtures. Phase A has 70 fixtures, two repeats, and three models: 420 calls. Phase B has a separately authored 70 fixtures and one observation per eligible cell: zero to 210 calls. The maximum is 630 calls, a 54.8387% reduction from 1,395 G-ROUTE4 calls.

All 140 scored fixtures, 28 reserves, all gold, gates, schedules, and Phase B material must freeze before the first provider call. A and B never pool. Only an A-qualified cell may enter B.

## 3. Canonical operation and prompt contract

The operation contract is `g-extract1.operation-definitions.v3`. SUBJECT contains no terminal period. Its opening fragment is exactly `Extract the {record_type} record`; operation and absence fragments are joined by exactly `. `. The unchanged historical template begins its invariant suffix with `. Copy names`, so replacing its sole `{SUBJECT}` token terminates SUBJECT exactly once. No trimming, normalization, punctuation insertion, or whitespace insertion occurs during substitution.

Zero operation nodes are legal only for E7. Otherwise there is one node or one connected two-node chain. In a two-node chain, node two consumes node one's target and is the unique sink. Stable topological order applies, then unsigned UTF-8 target order. SUM has two through four operands in immutable array order. Two operands render `A and B`; three or four use comma-space and `, and ` before the last operand.

### 3.1 Placeholder serialization

- `field_identifier`, `derived_field_identifier`, and `collection_identifier`: `^[a-z][a-z0-9_]{0,47}$`, exact unquoted ASCII.
- `integer_literal`: `^(?:0|-[1-9][0-9]*|[1-9][0-9]*)$`; no plus sign, leading zero, or negative zero.
- `decimal_literal`: metadata must already be canonical. Parse exact decimal, render fixed point, remove trailing fractional zeros while retaining one fractional digit, and render every signed zero as `0.0`. Thus `5.0`, `0.5`, and `-0.5` are valid metadata; `5.00`, `0.50`, `-0.50`, `-0.0`, and exponent notation are authoring errors. This metadata rule is distinct from semantic equivalence of provider JSON numbers.
- `date_literal`: a valid proleptic-Gregorian `YYYY-MM-DD`.
- `time_literal`: valid 24-hour `HH:MM`.
- `string_literal` and `entity_selector_literal`: printable ASCII, rendered with Python `json.dumps(value, ensure_ascii=True, separators=(',', ':'))`.
- `enum_literal`: `^[a-z][a-z0-9_]{0,47}$`, exact unquoted ASCII.

COUNT is not authorable. No collection source model is needed by the diagnosed scope.

### 3.2 Finite operation catalog

The exact templates are:

- ADD: `{target} is {left} plus {right}`
- SUBTRACT: `{target} is {minuend} minus {subtrahend}`
- MULTIPLY: `{target} is {left} times {right}`
- DIVIDE: `{target} is {dividend} divided by {divisor}`
- SUM: `{target} is the sum of {operands}`
- ELAPSED_MINUTES: `{target} is the elapsed minutes from {start} to {end}`
- CALENDAR_DAY_OFFSET: `{target} is {date} plus {days} calendar days`
- CLOCK_MINUTE_OFFSET: `{target} is {time} plus {minutes} minutes`
- GT: `{target} is true when {left} is greater than {right}`
- GTE: `{target} is true when {left} is greater than or equal to {right}`
- LT: `{target} is true when {left} is less than {right}`
- LTE: `{target} is true when {left} is less than or equal to {right}`
- EQ: `{target} is true when {left} is equal to {right}`
- ENTITY_FIELD_BIND: `{target} is {source_field} for the entity whose {selector_field} equals {selector_value}`
- EXACT_COPY: `{target} is copied exactly from {source_field}`

UNIT_CONVERSION uses only the six cataloged conversions and their exact templates. Its source is a `field_identifier`. Authors cannot add synonyms, hints, intermediate calculations, worked examples, edge reminders, or outcome-derived coaching. The same operation ID has byte-identical wording in A and B.

The historical absence fragment is exactly `Use 'not_provided' when the text says a value has not been provided`, inserted once iff a schema field has type `provided|not_provided`. E7 introduces no new sentinel or instruction.

Five full-prompt vectors in the machine contract bind SUBJECT bytes, final prompt bytes, and SHA-256 for a one-node prompt, a two-node prompt, E7, a quoted selector, and SUM. `validate_design.py` reconstructs all five and rejects `.. Copy names`.

## 4. Canonical fixture and output binding

Every output field has exactly these keys:

`name`, `schema_type`, `required`, `binding_kind`, `source_field`, `producer_target`, `label_removal`, `absence_capable`.

`binding_kind` is exactly one of `SOURCE_COPY`, `OPERATION_TARGET`, or `EXPLICIT_ABSENCE`.

- `SOURCE_COPY`: `source_field` names exactly one non-entity VALUE fact; `producer_target` is null; `absence_capable` is false.
- `OPERATION_TARGET`: `source_field` is null; `producer_target` names exactly one operation target; `absence_capable` is false.
- `EXPLICIT_ABSENCE`: `source_field` equals the output name and exactly one EXPLICIT_ABSENCE fact; `producer_target` is null; schema is `provided|not_provided`; gold is `not_provided`; `absence_capable` is true.

Output roles are exactly `source_copy`, `derived_number`, `derived_boolean`, `derived_date`, `derived_time`, `entity_bound_value`, and `absence_sentinel`. EXACT_COPY is a producer and secondary feature, not an output-role synonym. An EXACT_COPY from a source field has role `source_copy`; an EXACT_COPY of a derived target inherits its upstream role.

E7 therefore needs no fake operations: it contains exactly one EXPLICIT_ABSENCE output plus at least two supported SOURCE_COPY outputs.

## 5. Typed source facts and coaching exclusion

Each source fact has exactly `template_id`, `field_identifier`, `value`, and `entity_selector_value`. VALUE renders `{field_identifier} is {value}.` or `For {entity_selector_literal}, {field_identifier} is {value}.`; EXPLICIT_ABSENCE renders `{field_identifier} was not provided.` or its entity-prefixed form. One record is one sentence, sentence index is record index, sentences join with one ASCII space, and no heuristic sentence segmentation is used.

String and entity values are facts, not a back door for instructions. After ASCII lowercase and maximal non-`[a-z0-9_]` replacement, the frozen forbidden token and phrase lists reject operation language, calculation instructions, output/JSON/schema guidance, threshold language, expected answers, gold, gates, families, and risk labels. Violations are `AUTHORING_ERROR`.

## 6. Families and composed rows

The family contract is `g-extract1.family-assignment.v3`. All metadata are derived from the canonical fixture; authors do not select tags. First-match precedence is E7, E5, E4, E1, E2, E3, E6:

- E7: one unresolved required `not_provided` field and sentinel available; its zero-node graph contract must also pass.
- E5: mechanically required multi-entity disambiguation.
- E4: terminal GT/GTE/LT/LTE/EQ.
- E1: terminal CALENDAR_DAY_OFFSET.
- E2: terminal CLOCK_MINUTE_OFFSET or ELAPSED_MINUTES.
- E3: terminal numeric operation, or numeric operation followed by EXACT_COPY.
- E6: terminal ENTITY_FIELD_BIND or EXACT_COPY.

Derived metadata include terminal/source operations, output roles, comparison/temporal/numeric operation, entity count and selector role, source-fact sequence, and exact-copy-only. Secondary features are derived for calendar date, clock time, elapsed time, aggregation, unit conversion, threshold, equality boundary, entity binding, field binding, exact copy, multistep, and explicit partial absence.

E7 permits zero operation nodes only. It prohibits temporal, comparison, numeric, entity-binding, and downstream operations, so no unresolved operand or invented gold can enter a boundary or temporal fingerprint.

Every phase/round has eight distinct composed fixtures: two C1 numeric-to-comparison, two C2 temporal-to-comparison, two C3 numeric-to-EXACT_COPY, and two C4 entity-to-field binding. One fixture cannot satisfy multiple rows. C3 is exactly a numeric node followed by an EXACT_COPY sink consuming the first target.

## 7. E7 explicit partial absence

The scoring contract is `g-extract1.explicit-absence-scoring.v4`. E7 tests explicit partial absence / not-provided handling, not broad ambiguity. It separately reports semantic recognition and operational containment.

The first-match outcomes are infrastructure missing, provider truncated, empty, JSON parse failure, non-object, operational-schema invalid, semantic-schema invalid, exact valid not-provided, exact valid unsupported value, and exact valid supported-field error. Prose-only output is JSON parse failure; no refusal or evasion intent is inferred.

The historical operational parser remains ordinary `json.loads`. The evaluator separately uses `object_pairs_hook` plus lexical number callbacks. Duplicate keys make semantic schema invalid. If operationally accepted, any semantic-schema invalidity is false-clean. A duplicate-key object can never receive exact-valid-not-provided credit.

Truncation keeps primary outcome `provider_truncated` and earns no semantic credit. Truncated plus operationally accepted is false-clean and not safely contained. Truncated plus rejected is not false-clean and is safely contained. Malformed containment never qualifies E7.

Phase A requires five distinct E7 fixtures and 10/10 semantically correct, safely contained observations. Phase B requires five fixtures and 5/5. Guessed unsupported values, supported-field errors, malformed output, omissions, nulls, extras, wrong types, and duplicate keys fail recognition.

## 8. Exact-value semantics

The evaluator contract is `g-extract1.exact-value-comparator.v1`; it does not alter the model-facing baseline.

- Integer output requires a lexical JSON integer. `5.0` and `5e0` fail an integer schema; `-0` equals zero semantically.
- Number output uses exact decimals, so `5`, `5.0`, `5.00`, and `5e0` are semantically equal.
- Unit conversion is limited to the finite operation catalog; unit-bearing strings remain exact and omitted units fail.
- Strings/entities are exact in case, whitespace, punctuation, and Unicode scalar sequence except a field explicitly frozen with label removal may remove one leading `the`, `Order`, or `Vendor` plus one space.
- Object key order and insignificant JSON whitespace are ignored. Duplicate, extra, omitted, or null fields fail. Arrays and nested values are out of scope.
- Dates are exact valid zero-padded Gregorian `YYYY-MM-DD`; calendar offset uses source date as day zero.
- Times are exact `HH:MM`, with forward elapsed interpretation and explicit midnight rollover.
- Threshold operators have literal mathematical meaning, including equality boundaries.

Operational acceptance plus any semantic invalidity is false-clean.

## 9. Contamination and exact reuse

The contamination contract is `g-extract1.contamination.v3`. Similarity payload is input text, LF, then schema lines sorted by unsigned UTF-8 field name. Historical system/prompt boilerplate is excluded by construction. Normalize NFC, default casefold, CRLF/CR to LF, collapse Unicode whitespace, and preserve punctuation for tokenization.

Tokenizer precedence is whole date, whole time, context-valid signed number, identifier. The exact Python ASCII regex is frozen in the machine contract. It intentionally keeps `2026-10-01`, `23:45`, `-5`, and `5e-3` whole; `5-3` becomes `5`, `3`. Five-token contiguous n-grams are deduplicated sets. Jaccard must be strictly below 0.20; empty/empty is 1.0 and one-empty is 0.0.

Fingerprint is a compact JSON array of operation graph, output schema roles, entity role graph, boundary relation, temporal pattern, and source fact layout. Every component is derived from the canonical fixture; end-to-end vectors include numeric, entity, temporal-comparison, and E7 fixtures.

Exact whole-answer reuse uses sorted `[field_name,schema_type,[value_tag,canonical_value]]` rows and prohibits only whole-answer equality. Entity atoms are entity selector values. Identifier atoms are VALUE facts whose field name is exactly `id` or ends `_id`, `_code`, `_identifier`, or `_reference`; ordinary field names and generic labels are excluded. Any entity/identifier atom overlap is prohibited.

The date-number tuple preserves duplicates and ordered typed atoms from source facts, then operation arguments, then gold fields. It is compared only when at least one temporal and one numeric atom occur. Exact eligible tuple equality is prohibited.

Each exact-reuse rule applies explicitly to historical/new, A/A, A/B, B/B, scored/reserve, and reserve/reserve comparisons. All historical/new and A/B fingerprint collisions are prohibited. Near replay is five of six fingerprint components plus Jaccard at least 0.12. Same operation classes remain allowed. Within one phase/round/family, a fingerprint may occur at most twice only below 0.12 Jaccard with fresh values and entities.

Two separately authored contamination modules may share the frozen contract and standard library only. They cannot share normative derivation, tokenization, fingerprint, serialization code, or helpers. Byte disagreement blocks freeze.

## 10. Reserves

The reserve contract is `g-extract1.reserve-activation.v3`. There is one reserve per `RESERVE:{phase}:{round}:{primary_family}` slot: 2 phases x 2 rounds x 7 families = 28. There is no pool and no one-to-one reserve per primary fixture.

All five primary IDs in a slot are frozen in unsigned UTF-8 order. Zero eligible defects means no activation; more than one defective primary stops authoring; exactly one may claim the single reserve only when every replacement-profile dimension matches. A reserve must preserve phase, round, family, composed row, secondary features, field types, operation/boundary, explicit-absence status, risk, and output schema roles. After activation, all balances, contamination comparisons, gold reviews, and digests rerun. No replacement is possible after provider contact or from observed outputs.

## 11. Phase A repeat reduction and gates

The reduction contract is `g-extract1.phase-a-fixture-reduction.v1`. Positive fixture properties (semantic correctness, structural validity, useful correct acceptance) require both repeats. Adverse properties (malformed, binding error, false-clean) affect a fixture if either repeat is affected. A correlated false-clean pair requires both repeats, but the zero-false-clean observation gate is stricter.

Thus the Phase A family floor means at least four of five distinct determinate fixtures in every family have both repeats semantically correct. Truth tables for pass/pass, pass/fail, fail/pass, and fail/fail are frozen.

Per cell, A requires 70 observations, 35 fixtures, and 35 repeat pairs; B requires 35 observations and fixtures. Both independently require 29/30 determinate semantic, 29/30 structural, 27/30 useful correct acceptance, zero false-clean, at most one malformed determinate fixture, family floor 4/5, zero accepted E5/E6 binding errors, and the E7 gate. B has no repeat-pair guardrail.

One-sided exact 95% Clopper-Pearson values are benchmark decision statistics only: 0/35 upper 0.082031636; 0/30 upper 0.095033853; 29/30 lower 0.851403931; 27/30 lower 0.761402143. They are not claims about an IID natural population.

## 12. Gold, state, and integrity

Gold includes typed values, independent derivation, binding map, determinacy proof, family/features, operation metadata, and rationale. Two independent reviewers solve/audit before an operator-approved adjudication. Gold, fixtures, reserves, equivalence rules, and adjudication freeze together before contact. A defect discovered after contact invalidates the affected run and is not repaired in place.

The integrity catalog is `g-extract1.integrity-events.v2`; the verdict contract is `g-extract1.result-state-machine.v3`.

Cells transition deterministically from A scheduled to blocked, qualified, failed, or incomplete. Only the exact sorted A-qualified set may schedule B. B ends finally qualified, failed validation, or incomplete. A/B pooling and failed-cell reentry are prohibited.

Invalid events are exhaustive and include:

`PROTECTED_ARTIFACT_DIGEST_MISMATCH`, `GOLD_DIGEST_MISMATCH`, `SCORER_DIGEST_MISMATCH`, `COMPARATOR_DIGEST_MISMATCH`, `MODEL_IDENTITY_MISMATCH_AFTER_CONTACT`, `PROVIDER_VERSION_MISMATCH_AFTER_CONTACT`, `GENERATION_CONFIGURATION_MISMATCH`, `SEED_MISMATCH`, `SCHEDULE_POSITION_MISMATCH`, `DUPLICATE_CALL`, `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, `PROVIDER_FAILURE_WITHOUT_RECEIPT`, `UNAUTHORIZED_RETRY`, `UNAUTHORIZED_FALLBACK`, `UNAUTHORIZED_PROMPT_MUTATION`, `CONTAMINATION_CONTRACT_VIOLATION`, `POST_CONTACT_GOLD_MUTATION`, `POST_CONTACT_GOLD_DEFECT_DISCOVERED`, `POST_CONTACT_FIXTURE_MUTATION`, `POST_CONTACT_THRESHOLD_MUTATION`, `CORRUPTED_CHECKPOINT`, `MISSING_CHECKPOINT_AFTER_INTERRUPTION`, `UNVERIFIABLE_INTERRUPTION_CHECKPOINT`, `UNVERIFIABLE_JOURNAL_PREFIX`, `CORRUPTED_OR_UNPARSEABLE_JOURNAL`, and `PROVENANCE_MISMATCH`.

Receipted provider timeout/error/missing response and a verifiable sealed interruption are INCOMPLETE. Explicit authorized operator abort is ABORTED. Before contact, pinned mismatches are PRE_CONTACT_BLOCKED. Primary verdict precedence is INVALID, PRE_CONTACT_BLOCKED, ABORTED, INCOMPLETE, NO_PHASE_A_CELL_QUALIFIED, QUALIFICATION_METHOD_FAILED_VALIDATION, MIXED_TARGETED_REQUALIFICATION_SUPPORTED, then TARGETED_REQUALIFICATION_SUPPORTED.

## 13. Frozen baseline and provider

The baseline contract is `g-extract1.baseline-binding.v3`. The historical system text, request builder, normalization, operational wrapper, extraction validator, semantic references, model binding, and blueprint template are bound by path, SHA-256, and Git blob in the machine contract. The common extraction suffix is byte-identical to G-ROUTE4. Only record type, catalog operands, source text, and schema vary.

Provider is Ollama 0.34.3. Models and blob SHA-256 values are:

- `qwen2.5:7b`: `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
- `qwen3:14b`: `a8cc1361f3145dc01f6d77c6c82c9116b9ffe3c97b34716fe20418455876c40e`
- `qwen3.8:27b`: `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`

Generation remains context 8192, output 350, temperature 0.45, top_p 0.9, top_k 40, repeat penalty 1.1, thinking off, stream off, fresh session, zero retry/repair/fallback. Seeds are `base + zero_based_fixture_index * 10 + one_based_repeat`, with candidate bases 610000 and 620000.

## 14. Governance and readiness boundary

G-ROUTE4 remains failed and immutable. There is no historical rewrite, prompt tuning, threshold loosening, post-contact gold/fixture change, autonomy, or belief effect. Failed attempts are append-only. One local-model research job may run at a time. Reviewer output is non-authoritative.

Separate authorization remains required for blueprint authoring, fixture/gold authoring, implementation, mechanical pilot, execution freeze, Phase A, and conditional Phase B. This candidate contains zero scored fixtures, zero reserves, zero provider calls, and no runtime implementation.

`validate_design.py` performs deterministic structural and cross-representation consistency only; it does not prove scientific validity and does not replace adversarial review.
