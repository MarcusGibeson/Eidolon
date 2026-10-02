# G-EXTRACT1 Design Candidate v9

Status: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_9`

This document and `DESIGN_CANDIDATE.json` are co-normative. The machine contract is `g-extract1.design-candidate.v9`. This checkpoint authorizes design rereview only. It authorizes no blueprint, fixture, implementation, pilot, freeze, or execution work.

## 1. Historical boundary and question

G-ROUTE4 remains CLOSED FAILED. Its closure and unsafe-stop diagnostic are immutable and are used only to define failure families. G-EXTRACT1 asks whether a larger, prospectively stratified structured-extraction qualification test can identify R2/R3 model-tier cells that remain safe and useful on separately authored validation fixtures under the byte-bound historical prompt behavior.

The design does not identify prompt wording, model weights, provider internals, or sampling as a unique cause. It first measures the existing baseline. Prompt repair requires a different experiment identity and fresh corpora.

Scope is structured extraction only, R2 and R3, for `qwen2.5:7b`, `qwen3:14b`, and `qwen3.8:27b`. Grounded research, conversation, planning, synthesis, coding, timezone conversion, production routing, and prompt repair are excluded.

## 2. Corpus and phases

Each phase and risk round contains seven primary families with five fixtures each: 35 fixtures, comprising 30 determinate fixtures and five E7 explicit-partial-absence fixtures. Phase A has 70 fixtures, two repeats, and three models: 420 calls. Phase B has a separately authored 70 fixtures and one observation per eligible cell: zero to 210 calls. The maximum is 630 calls, a 54.8387% reduction from 1,395 G-ROUTE4 calls.

All 140 scored fixtures, 28 reserves, all gold, gates, schedules, and Phase B material must freeze before the first provider call. A and B never pool. Only an A-qualified cell may enter B.

## 3. Canonical operation and prompt contract

The operation rendering contract is `g-extract1.operation-definitions.v4`. SUBJECT contains no terminal period. Its opening fragment is exactly `Extract the {record_type} record`; operation and absence fragments are joined by exactly `. `. The unchanged historical template begins its invariant suffix with `. Copy names`, so replacing its sole `{SUBJECT}` token terminates SUBJECT exactly once. No trimming, normalization, punctuation insertion, or whitespace insertion occurs during substitution.

Zero operation nodes are legal only for E7. Otherwise there is one node or one connected two-node chain. In a two-node chain, node two consumes node one's target and is the unique sink. Stable topological order applies, then unsigned UTF-8 target order. SUM has two through four operands in immutable array order. Two operands render `A and B`; three or four use comma-space and `, and ` before the last operand.

### 3.1 Placeholder serialization

- `field_identifier`: generated `fNNN_MM`; `derived_field_identifier`: generated `dNNN_01` or `dNNN_02`. NNN is the frozen fixture ordinal, MM the source-field first-appearance ordinal. Collections are not authorable. All identifier regexes and bounds are frozen in the co-normative v9 annex.
- `integer_literal`: `^(?:0|-[1-9][0-9]*|[1-9][0-9]*)$`; no plus sign, leading zero, or negative zero.
- `decimal_literal`: metadata must already be canonical. Parse exact decimal, render fixed point, remove trailing fractional zeros while retaining one fractional digit, and render every signed zero as `0.0`. Thus `5.0`, `0.5`, and `-0.5` are valid metadata; `5.00`, `0.50`, `-0.50`, `-0.0`, and exponent notation are authoring errors. This metadata rule is distinct from semantic equivalence of provider JSON numbers.
- `date_literal`: a valid proleptic-Gregorian `YYYY-MM-DD`.
- `time_literal`: valid 24-hour `HH:MM`.
- `boolean_literal`: exactly lowercase `true` or `false`.
- `string_literal` and `entity_selector_literal`: printable ASCII, rendered with Python `json.dumps(value, ensure_ascii=True, separators=(',', ':'))` after `g-extract1.lexical-neutrality.v1` generation and membership checks pass. Generated entity/string values contain no embedded quote or backslash; arbitrary quoted prose is unavailable.
- `enum_literal`: exactly one opaque option from `option_a` through `option_h`, or the historical E7 `provided`/`not_provided`; no arbitrary semantic labels.

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

Five full-prompt vectors bind SUBJECT bytes, final prompt bytes, and SHA-256 for a one-node prompt, a two-node prompt, E7, a quoted selector, and SUM. `validate_design.py` reconstructs all five and rejects `.. Copy names`.

## 4. Historical schema type system

The normative contract is `g-extract1.schema-types.v1`. Only these historical primitive tokens are legal: `string`, `number`, `integer`, `boolean`, `YYYY-MM-DD`, and `HH:MM`. Aliases including `date`, `time`, `bool`, `int`, and `float` are authoring errors.

Finite enum schemas contain two through eight `^[a-z][a-z0-9_]{0,47}$` options separated by literal `|`. Whitespace and duplicate options are prohibited. Option byte order is preserved in the schema but conveys no ranking. A provider value must equal one listed option exactly. `provided|not_provided` is the historical E7 enum.

| Schema | Semantic tag | SOURCE_COPY kinds | Permitted result roles | Contamination tag |
|---|---|---|---|---|
| `string` | STRING | string/entity-selector literal | source copy, entity-bound value | STRING |
| `number` | NUMBER | integer or decimal literal | source/derived number, entity-bound | NUMBER |
| `integer` | INTEGER | integer literal | source/derived number, entity-bound | INTEGER |
| `boolean` | BOOLEAN | boolean literal | source/derived Boolean, entity-bound | BOOLEAN |
| `YYYY-MM-DD` | DATE | date literal | source/derived date, entity-bound | DATE |
| `HH:MM` | TIME | time literal | source/derived time, entity-bound | TIME |
| finite enum | ENUM | enum literal | source, entity-bound, special absence | ENUM |

Unknown schema tokens are `AUTHORING_ERROR`. Gold uses the exact semantic form named by this table. Exact-answer contamination rows retain the historical schema token and derive only the uppercase semantic tag from this contract.

## 5. Semantic operation and domain contract

The normative contract is `g-extract1.operation-semantics.v2`. Placeholder syntax alone never establishes legality. Every field reference, operand type, result type, output schema, domain condition, and gold result must satisfy this contract.

### 5.1 Source references and output compatibility

An ordinary `field_identifier` operand resolves to exactly one non-entity VALUE fact. A missing or duplicate non-entity field is `AUTHORING_ERROR`. Entity-scoped facts cannot be consumed implicitly; they require `ENTITY_FIELD_BIND`. A `derived_field_identifier` resolves to one prior operation target in stable topological order. The source fact's historical `schema_type` is authoritative: its literal kind must be one allowed by that schema, and an integral literal under `number` evaluates as exact NUMBER rather than INTEGER.

Every OPERATION_TARGET schema must exactly match the producer result: comparison to `boolean`, calendar offset to `YYYY-MM-DD`, clock offset to `HH:MM`, elapsed minutes to `integer`, and numeric operations to the frozen promoted `integer` or `number`. Entity binding and EXACT_COPY preserve the source semantic type and historical schema without coercion. A mismatched producer/schema pair is `AUTHORING_ERROR`.

### 5.2 Numeric operations

ADD, SUBTRACT, MULTIPLY, and SUM accept only INTEGER/NUMBER operands. All-INTEGER operands produce INTEGER; any NUMBER operand produces NUMBER. No date, time, Boolean, string, or enum overload exists.

DIVIDE accepts numeric operands, requires an exactly nonzero divisor, and always produces NUMBER. The reduced exact rational denominator may contain only prime factors 2 and 5, so the decimal terminates. `10 / 4` is valid gold `2.5`; `1 / 3` and `5 / 0` are `AUTHORING_ERROR`. No rounding exists.

Each UNIT_CONVERSION uses its frozen conversion ID as the complete source-unit assertion, accepts INTEGER/NUMBER, produces NUMBER, and must yield an exact terminating decimal. The catalog is exactly: HOURS_TO_MINUTES `source * 60`, MINUTES_TO_HOURS `source / 60`, KILOGRAMS_TO_GRAMS `source * 1000`, GRAMS_TO_KILOGRAMS `source / 1000`, DOLLARS_TO_CENTS `source * 100`, and CENTS_TO_DOLLARS `source / 100`. Those IDs respectively bind source/result units as hours/minutes, minutes/hours, kilograms/grams, grams/kilograms, dollars/cents, and cents/dollars. No free-form unit metadata or implicit conversion exists.

### 5.3 Temporal operations

ELAPSED_MINUTES accepts TIME/TIME and produces `integer`. It is the forward interval: if end is earlier, end is on the next day; equal times produce 0, not 1440. Result range is 0 through 1439.

CALENDAR_DAY_OFFSET accepts DATE and INTEGER, permits offsets 0 through 366 inclusive, prohibits negatives, and produces `YYYY-MM-DD`. The source date is day zero.

CLOCK_MINUTE_OFFSET accepts TIME and INTEGER, permits offsets 0 through 1439 inclusive, prohibits negatives, and produces `HH:MM`. Gold is modulo 1440; rollover occurs exactly when source minutes plus offset is at least 1440.

### 5.4 Comparisons, binding, and chains

GT/GTE/LT/LTE allow INTEGER/NUMBER pairs with exact numeric promotion, DATE/DATE, or TIME/TIME. STRING, ENUM, BOOLEAN ordering is prohibited. EQ allows same-type INTEGER, NUMBER, DATE, TIME, or BOOLEAN plus INTEGER/NUMBER promotion; string and enum equality operations are not authorable. Every comparison produces `boolean`.

ENTITY_FIELD_BIND requires the complete `g-extract1.entity-population.v2` population: exactly two or three entities, every one with exactly one typed selector fact and one typed source fact. No additional entity-scoped facts or non-entity duplicates of those fields exist. Schemas are byte-identical across the population, metadata labels exactly match selector fact values, and selection is unique. The generated label supplies entity identity; the frozen subtype row supplies its selector-role tag. No coercion exists. EXACT_COPY requires one unique source field or upstream target and preserves its exact semantic type/schema.

In a two-node chain, node two's argument position must accept the exact semantic type produced by node one, with only the numeric comparison promotion above. Numeric-to-date, date-to-SUM, Boolean-to-arithmetic, and entity-string-to-numeric-comparison chains are authoring errors.

Gold is never manually chosen. Typed operands resolve mechanically, the exact frozen operation is evaluated, and its result is serialized through `g-extract1.schema-types.v1`; disagreement with proposed gold is `AUTHORING_ERROR`.

## 6. Canonical fixture and output binding

Every output field has exactly these keys:

`name`, `schema_type`, `required`, `binding_kind`, `source_field`, `producer_target`, `label_removal`, `absence_capable`.

`binding_kind` is exactly one of `SOURCE_COPY`, `OPERATION_TARGET`, or `EXPLICIT_ABSENCE`.

- `SOURCE_COPY`: `source_field` names exactly one non-entity VALUE fact; `producer_target` is null; `absence_capable` is false; source literal and schema must match the schema contract.
- `OPERATION_TARGET`: `source_field` is null; `producer_target` names exactly one operation target; `absence_capable` is false; producer type and schema must match the operation contract.
- `EXPLICIT_ABSENCE`: `source_field` equals the output name and exactly one EXPLICIT_ABSENCE fact; `producer_target` is null; schema is `provided|not_provided`; gold is `not_provided`; `absence_capable` is true.

An output name is exactly its binding identifier: SOURCE_COPY/EXPLICIT_ABSENCE use `source_field`; OPERATION_TARGET uses `producer_target`. Output fields remain sorted by unsigned UTF-8 names. There is no model-facing alias or hidden o-to-d/f mapping.

Output roles are exactly `source_copy`, `derived_number`, `derived_boolean`, `derived_date`, `derived_time`, `entity_bound_value`, and `absence_sentinel`. EXACT_COPY is a producer and secondary feature, not an output-role synonym. An EXACT_COPY from a source field has role `source_copy`; an EXACT_COPY of a derived target inherits its upstream role. Every role must also be allowed by the field's schema.

E7 therefore needs no fake operations: it contains exactly one EXPLICIT_ABSENCE output plus at least two supported SOURCE_COPY outputs.

## 7. Typed source facts and positive anti-coaching grammar

Each source fact has exactly `template_id`, `field_identifier`, `schema_type`, `value`, and `entity_selector_value`. `schema_type` must be accepted by `g-extract1.schema-types.v1`; a VALUE literal kind must be allowed by that schema, while EXPLICIT_ABSENCE must use `provided|not_provided` and a null value. The schema metadata is not rendered model-facing. VALUE renders `{field_identifier} is {value}.` or `For {entity_selector_literal}, {field_identifier} is {value}.`; EXPLICIT_ABSENCE renders `{field_identifier} was not provided.` or its entity-prefixed form. One record is one sentence, sentence index is record index, sentences join with one ASCII space, and no heuristic sentence segmentation is used.

The normative content constraint is `g-extract1.lexical-neutrality.v1`, a positive generated vocabulary. Record types are exactly A: `record`, `entry`, `item`, `case`, `notice`, `account`, `order`; B: `permit`, `invoice`, `schedule`, `reading`, `event`, `profile`, `docket`. E1 through E7 use their phase catalog entries in that order. Each appears exactly five times per phase/round; its single family reserve uses that same record type.

Every primary and reserve receives an immutable authoring-position ordinal from 1 through 168 before content is written. Primaries: `1 + phase_offset + round_offset + slot`, where A/B offsets are 0/84, R2/R3 offsets 0/35, and primary slot 0..34 is family-major then within-family slot order. Reserves: `71 + phase_offset + reserve_round_offset + family_ordinal`, with R2/R3 reserve offsets 0/7 and E1..E7 ordinals 0..6. No answer, comparison direction, difficulty, risk wording or model output affects identifier bytes.

Source identifiers are `f{fixture_ordinal:03d}_{source_field_ordinal:02d}`, derived targets `d{fixture_ordinal:03d}_{topological_node_ordinal:02d}`. The first distinct source field gets 01; repeated entity fields retain it. Graph node positions supply 01/02. Output names equal their bindings, ensuring the unchanged extraction prompt requests the names actually defined in source facts or canonical operations. Generated names are unique across fixtures, avoiding collisions between otherwise unavoidable Boolean gold objects.

Entity labels are exactly `Entity {fixture_ordinal:03d} {A|B|C}` in entity index order. String facts are generated `label_NNN_MM`, `code_NNN_MM`, or `id_NNN_MM`; NNN is the fixture ordinal and MM first distinct string-value ordinal in source-fact order. Prefixes follow the fixed cycle label/code/id by value ordinal, so authors cannot choose their wording. Arbitrary Title Case labels, statuses, sentences, coaching identifiers, and synonyms are authoring errors. The ordinary enum schema is a contiguous prefix of `option_a`..`option_h`, with two through eight options in catalog order; E7 preserves `provided|not_provided`. The generic historical enum reader remains unchanged for historical contamination comparisons.

Entity/string/identifier value pools are disjoint between A/B, rounds, primaries and reserves. Values may recur within the same fixture to express a reference, never across fixtures. Shared opaque enum options and repeated record types are intentional and balanced. All lexical atoms present in input.text or canonical schema serialization remain in similarity; fingerprint components remove names only where specified. The v7 typed fact-role refinement remains; v9 explicitly governs recurrence and comparison views. Historical/new uses the separate three-component projection in section 19. Prompt SUBJECT/record type remains excluded by the existing boilerplate-payload rule, with its allocation separately audited. Generated syntactic identifiers are not identity atoms; `id_` string values are. Historical identifier detection retains its field-name adapter, projected into the single two-string comparison shape. Fixed lexical choices remain structurally associated with family/phase; no statistical independence or causal lexical-effect claim is made.

## 8. Families and composed rows

The family contract is `g-extract1.family-assignment.v4`. All metadata are derived from the canonical fixture; authors do not select tags. First-match precedence is E7, E5, E4, E1, E2, E3, E6:

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

## 9. E7 explicit partial absence

The scoring contract is `g-extract1.explicit-absence-scoring.v4`. E7 tests explicit partial absence / not-provided handling, not broad ambiguity. It separately reports semantic recognition and operational containment.

The first-match outcomes are infrastructure missing, provider truncated, empty, JSON parse failure, non-object, operational-schema invalid, semantic-schema invalid, exact valid not-provided, exact valid unsupported value, and exact valid supported-field error. Prose-only output is JSON parse failure; no refusal or evasion intent is inferred.

The historical operational parser remains ordinary `json.loads`. The evaluator separately uses `object_pairs_hook` plus lexical number callbacks. Duplicate keys make semantic schema invalid. If operationally accepted, any semantic-schema invalidity is false-clean. A duplicate-key object can never receive exact-valid-not-provided credit.

Truncation keeps primary outcome `provider_truncated` and earns no semantic credit. Truncated plus operationally accepted is false-clean and not safely contained. Truncated plus rejected is not false-clean and is safely contained. Malformed containment never qualifies E7.

Phase A requires five distinct E7 fixtures and 10/10 semantically correct, safely contained observations. Phase B requires five fixtures and 5/5. Guessed unsupported values, supported-field errors, malformed output, omissions, nulls, extras, wrong types, and duplicate keys fail recognition.

## 10. Exact-value semantics

The evaluator contract is `g-extract1.exact-value-comparator.v1`; it does not alter the model-facing baseline.

- Integer output requires a lexical JSON integer. `5.0` and `5e0` fail an integer schema; `-0` equals zero semantically.
- Number output uses exact decimals, so `5`, `5.0`, `5.00`, and `5e0` are semantically equal.
- Unit conversion is limited to the finite operation catalog; unit-bearing strings remain exact and omitted units fail.
- Strings/entities are exact in case, whitespace, punctuation, and Unicode scalar sequence except a field explicitly frozen with label removal may remove one leading `the`, `Order`, or `Vendor` plus one space.
- Object key order and insignificant JSON whitespace are ignored. Duplicate, extra, omitted, or null fields fail. Arrays and nested values are out of scope.
- Dates are exact valid zero-padded Gregorian `YYYY-MM-DD`; calendar offset uses source date as day zero.
- Times are exact `HH:MM`, with the temporal rules in `operation-semantics.v2`.
- Threshold operators have literal mathematical meaning, including equality boundaries.

Operational acceptance plus any semantic invalidity is false-clean.

## 11. Contamination and exact reuse

The contamination contract is `g-extract1.contamination.v5`. Similarity payload is input text, LF, then schema lines sorted by unsigned UTF-8 field name. Historical system/prompt boilerplate is excluded by construction. Normalize NFC, default casefold, CRLF/CR to LF, collapse Unicode whitespace, and preserve punctuation for tokenization.

Tokenizer precedence is whole date, whole time, context-valid signed number, identifier. The exact Python ASCII regex is frozen in the machine contract. It intentionally keeps `2026-10-01`, `23:45`, `-5`, and `5e-3` whole; `5-3` becomes `5`, `3`. Five-token contiguous n-grams are deduplicated sets. Ordinary ordinal-neutral Jaccard is strictly below 0.20 except the prospectively declared template groups in section 20. Empty/empty ordinary Jaccard is 1.0 and one-empty is 0.0. Declared content-view empty/empty is NOT_APPLICABLE, never evidence of independence.

Fingerprint is a compact JSON array of operation graph, output schema roles, entity role graph, boundary relation, temporal pattern, and source fact layout. Every component is derived from the canonical fixture in stable topological operation order; end-to-end vectors contain no injected boundary or temporal values.

Exact whole-answer reuse uses sorted `[field_name,historical_schema_type,[semantic_tag,canonical_value]]` rows and prohibits only whole-answer equality. Tags are STRING, NUMBER, INTEGER, BOOLEAN, DATE, TIME, or ENUM and derive only from `schema-types.v1`. Entity atoms are entity selector values. For new fixtures, identifier atoms are generated `id_NNN_MM` string VALUE facts. For historical fixtures only, the original `id`, `_id`, `_code`, `_identifier`, `_reference` field adapter remains. Both compare exact canonical value atoms. Generated field names and ordinary `label_`/`code_` values are excluded only from this identity-atom rule, not similarity. Any entity/identifier atom overlap is prohibited.

The date-number tuple preserves duplicates and ordered typed atoms from source facts, then stable-topological operation arguments in catalog placeholder/SUM array order, then gold fields sorted by name. SOURCE_FACT tags derive from schema_type, field-reference argument tags from resolved source schemas, derived-reference tags from upstream producer result types, and literal argument tags from literal semantic types. Ordinary field references resolve unique non-entity facts; ENTITY_FIELD_BIND source/selector references resolve the selected entity's complete facts under the frozen population contract. Gold tags derive from output schemas. NUMBER serializes an exact decimal with at least one fractional digit: a number fact containing integer token 5 becomes NUMBER `5.0`, whereas integer schema yields INTEGER `5`. Temporal atoms use DATE `YYYY-MM-DD` or TIME `HH:MM`. No Decimal context or binary float may round these objects. It is compared only when at least one temporal and one numeric atom occur. Exact eligible tuple equality is prohibited.

Each exact-reuse rule applies explicitly to historical/new, A/A, A/B, B/B, scored/reserve, and reserve/reserve comparisons. Historical/new prohibits exact three-component projection collisions and near replay of at least two of three components plus Jaccard at least 0.12. New/new uses the six-component fingerprint, exact planned positions, recurrence ledger and explicit comparison decision table in section 20. This prospectively supersedes incompatible universal A/B and reserve collision prohibition. Exact reuse rules remain universal.

Two separately authored contamination modules may share the frozen contract and standard library only. They cannot share normative derivation, tokenization, fingerprint, serialization code, or helpers. Byte disagreement blocks freeze.

## 12. Reserves

The reserve contract is `g-extract1.reserve-activation.v5`. There is one reserve per `RESERVE:{phase}:{round}:{primary_family}` slot: 2 phases x 2 rounds x 7 families = 28. There is no pool and no one-to-one reserve per primary fixture.

All five primary IDs in a slot are frozen in unsigned UTF-8 order. Zero eligible defects means no activation; more than one defective primary stops authoring; exactly one may claim the single reserve only when every replacement-profile dimension matches. A reserve must also preserve phase and round and have byte-identical `g-extract1.reserve-equivalence.v1` profile bytes. The exact ordered profile keys and derivations are co-normative in the annex; they include schema sequences, semantic result types, promotion classes, comparison operand pair, exact conversion ID, temporal/boundary classes, entity population/role, output roles, field/node counts, subtype slot and domain obligations. INTEGER/NUMBER, enum option order, conversion IDs, and any domain-profile difference prohibit replacement. Fixture ordinals and fresh literal/entity/gold values are excluded. Subtype and lexical balances, contamination, gold review and all freeze digests rerun after activation. No replacement is possible after provider contact or from observed outputs.

## 13. Phase A repeat reduction and gates

The reduction contract is `g-extract1.phase-a-fixture-reduction.v1`. Positive fixture properties (semantic correctness, structural validity, useful correct acceptance) require both repeats. Adverse properties (malformed, binding error, false-clean) affect a fixture if either repeat is affected. A correlated false-clean pair requires both repeats, but the zero-false-clean observation gate is stricter.

Thus the Phase A family floor means at least four of five distinct determinate fixtures in every family have both repeats semantically correct. Truth tables for pass/pass, pass/fail, fail/pass, and fail/fail are frozen.

Per cell, A requires 70 observations, 35 fixtures, and 35 repeat pairs; B requires 35 observations and fixtures. Both independently require 29/30 determinate semantic, 29/30 structural, 27/30 useful correct acceptance, zero false-clean, at most one malformed determinate fixture, family floor 4/5, zero accepted E5/E6 binding errors, and the E7 gate. B has no repeat-pair guardrail.

One-sided exact 95% Clopper-Pearson values are benchmark decision statistics only: 0/35 upper 0.082031636; 0/30 upper 0.095033853; 29/30 lower 0.851403931; 27/30 lower 0.761402143. They are not claims about an IID natural population.

## 14. Gold, state, and integrity

Gold includes typed values, mechanically evaluated operation results, binding map, determinacy proof, family/features, operation metadata, and rationale. Two independent reviewers solve/audit before an operator-approved adjudication. Gold, fixtures, reserves, equivalence rules, and adjudication freeze together before contact. A defect discovered after contact invalidates the affected run and is not repaired in place.

The integrity catalog is `g-extract1.integrity-events.v2`; the verdict contract is `g-extract1.result-state-machine.v3`.

Cells transition deterministically from A scheduled to blocked, qualified, failed, or incomplete. Only the exact sorted A-qualified set may schedule B. B ends finally qualified, failed validation, or incomplete. A/B pooling and failed-cell reentry are prohibited.

Invalid events are exhaustive and include:

`PROTECTED_ARTIFACT_DIGEST_MISMATCH`, `GOLD_DIGEST_MISMATCH`, `SCORER_DIGEST_MISMATCH`, `COMPARATOR_DIGEST_MISMATCH`, `MODEL_IDENTITY_MISMATCH_AFTER_CONTACT`, `PROVIDER_VERSION_MISMATCH_AFTER_CONTACT`, `GENERATION_CONFIGURATION_MISMATCH`, `SEED_MISMATCH`, `SCHEDULE_POSITION_MISMATCH`, `DUPLICATE_CALL`, `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, `PROVIDER_FAILURE_WITHOUT_RECEIPT`, `UNAUTHORIZED_RETRY`, `UNAUTHORIZED_FALLBACK`, `UNAUTHORIZED_PROMPT_MUTATION`, `CONTAMINATION_CONTRACT_VIOLATION`, `POST_CONTACT_GOLD_MUTATION`, `POST_CONTACT_GOLD_DEFECT_DISCOVERED`, `POST_CONTACT_FIXTURE_MUTATION`, `POST_CONTACT_THRESHOLD_MUTATION`, `CORRUPTED_CHECKPOINT`, `MISSING_CHECKPOINT_AFTER_INTERRUPTION`, `UNVERIFIABLE_INTERRUPTION_CHECKPOINT`, `UNVERIFIABLE_JOURNAL_PREFIX`, `CORRUPTED_OR_UNPARSEABLE_JOURNAL`, and `PROVENANCE_MISMATCH`.

Receipted provider timeout/error/missing response and a verifiable sealed interruption are INCOMPLETE. Explicit authorized operator abort is ABORTED. Before contact, pinned mismatches are PRE_CONTACT_BLOCKED. Primary verdict precedence is INVALID, PRE_CONTACT_BLOCKED, ABORTED, INCOMPLETE, NO_PHASE_A_CELL_QUALIFIED, QUALIFICATION_METHOD_FAILED_VALIDATION, MIXED_TARGETED_REQUALIFICATION_SUPPORTED, then TARGETED_REQUALIFICATION_SUPPORTED.

## 15. Frozen baseline and provider

The baseline contract is `g-extract1.baseline-binding.v4`. The historical system text, request builder, normalization, operational wrapper, extraction validator, semantic references, model binding, and blueprint template are bound by path, SHA-256, and Git blob in the machine contract. The common extraction suffix is byte-identical to G-ROUTE4. Only record type, catalog operands, source text, and historical schema vary.

Provider is Ollama 0.34.3. Models and blob SHA-256 values are:

- `qwen2.5:7b`: `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
- `qwen3:14b`: `a8cc1361f3145dc01f6d77c6c82c9116b9ffe3c97b34716fe20418455876c40e`
- `qwen3.8:27b`: `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`

Generation remains context 8192, output 350, temperature 0.45, top_p 0.9, top_k 40, repeat penalty 1.1, thinking off, stream off, fresh session, zero retry/repair/fallback. Seeds are `base + zero_based_fixture_index * 10 + one_based_repeat`, with candidate bases 610000 and 620000.

## 16. Governance and readiness boundary

G-ROUTE4 remains failed and immutable. There is no historical rewrite, prompt tuning, threshold loosening, post-contact gold/fixture change, autonomy, or belief effect. Failed attempts are append-only. One local-model research job may run at a time. Reviewer output is non-authoritative.

Separate authorization remains required for blueprint authoring, fixture/gold authoring, implementation, mechanical pilot, execution freeze, Phase A, and conditional Phase B. This candidate contains zero scored fixtures, zero reserves, zero provider calls, and no runtime implementation.

`validate_design.py` performs deterministic structural and cross-representation consistency only; it does not prove scientific validity and does not replace adversarial review.

## 17. Frozen subtype allocation and reserve equivalence

The normative allocation is `g-extract1.subtype-allocation.v2`, structurally matched except frozen E4 truth/boundary, E5 selector, difficulty and E7 presentation matrices. Each row is one exact slot, with five slots per family. The blueprint cannot substitute a different subtype. Each family-slot reserve covers only within-family subtype slot 01, fixed before authoring. A defect in slot 02..05 stops authoring, and multiple defective primaries stop before selection. Reserve replacement must preserve its claimed primary's exact slot/profile; if its single frozen family reserve does not match, authoring stops.

| Family | Exact five slots in order |
|---|---|
| E1 | calendar within-month; month boundary; year boundary; leap-day boundary; edge offset R2=0/R3=366 |
| E2 | clock same-day; clock rollover; elapsed ordinary; elapsed rollover; elapsed equal-zero |
| E3 | ADD INTEGER_ONLY; SUBTRACT MIXED_TO_NUMBER; three-operand SUM NUMBER_ONLY; DIVIDE -> EXACT_COPY; UNIT_CONVERSION -> EXACT_COPY |
| E4 | ADD -> GT; SUBTRACT -> LTE; calendar -> GTE; clock -> LT; direct EQ NUMBER/NUMBER; context boundary/truth rows in annex |
| E5 | 2 entities IDENTIFIER/number; 2 ATTRIBUTE/string; 3 EVENT_ROLE/three-option opaque enum; 2 IDENTIFIER/date; 3 ATTRIBUTE/time |
| E6 | EXACT_COPY source integer; source number; source string; calendar -> EXACT_COPY date; clock -> EXACT_COPY time |
| E7 | supported pairs integer/integer; number/string; date/time; enum/string; then Boolean/number/integer triple; exactly one missing enum field in every slot |

C1 uses E4-01/02, C2 E4-03/04, C3 E3-04/05, C4 E5-01/02: eight different quota fixtures. Other E5 binds still carry the C4 feature but add no extra quota row. E4 occupies four composed slots; E3 and E5 retain five total slots. Derived temporal EXACT_COPY remains E6 because the sink is copy and the upstream operation is not numeric.

Numeric coverage fixes INTEGER_ONLY, NUMBER_ONLY, MIXED_TO_NUMBER, DIVIDE_TO_NUMBER and UNIT_CONVERSION_TO_NUMBER. Every phase/round has five operators, numeric/date/time domains, BELOW/EQUAL/ABOVE boundaries and exact context-specific 3 true/2 false balance. Typed result coverage includes INTEGER, NUMBER, DATE, TIME, BOOLEAN and STRING/ENUM copies. MULTIPLY has no scored slot; its catalog legality remains covered by deterministic checking. Unit slots use HOURS_TO_MINUTES in R2 and GRAMS_TO_KILOGRAMS in R3 for both phases. All scalar values must be fresh under contamination rules.

`g-extract1.reserve-equivalence.v1` serializes an exact compact UTF-8 JSON object in its frozen key order, ensure_ascii=true, comma/colon separators, no newline. Numeric promotion is INTEGER_ONLY for all INTEGER numeric operands, NUMBER_ONLY for all NUMBER, MIXED_TO_NUMBER for mixed operands, DIVIDE_TO_NUMBER/UNIT_CONVERSION_TO_NUMBER for those operations, and NOT_APPLICABLE elsewhere. Every profile derivation, schema/domain dimension and freshness exclusion is specified below. Profile equality alone never bypasses contamination or gold review.

Opaque labels limit the inference to the controlled extraction benchmark. This does not establish safety for natural names, arbitrary production field names, all operation subtypes, or unrelated G-ROUTE4 capabilities. No scientific gate or historical result changes.

## 18. Co-normative integration annex

The following exact structured rules are part of this human design, rather than an external checklist assertion. Human prose above and these tables/algorithms bind the same machine sections. They freeze v9 generation, population, type-profile, allocation, comparison-mode and atom-typing decisions; a future blueprint may only instantiate them. Validator checks parse this block and compare the normative objects directly. The validation report is deterministic structural/cross-representation consistency only and does not prove scientific validity.

The E7 source-order rule is exact: A places absence first, B last, and the family reserve between its two supported facts. Supported schema order is the fixed slot-row order. These fixtures necessarily shared the old empty-graph/coarse-layout fingerprint, so v7 prospectively refines only its sixth component to `[layout_enum, [[role,schema_type,entity_index],...]]`. The first-match layout classifier and other five components remain unchanged. This is an explicit consistency correction, not a threshold relaxation or historical rescore. Two independent contamination implementations must implement this same refinement before a future freeze.

Source/output schema profile sequences use canonical schema/role sorting with duplicates retained, rather than presentation order. This allows the independently frozen source-order variation while preserving exact type multiplicities. Node operand semantic-type arrays additionally preserve the types in every argument position. Source order remains in fingerprints and contamination checks; it cannot be chosen from outputs.

## 19. Candidate v8 integration rules

Historical/new uses historical-fingerprint-adapter.v1. All 106 historical extraction inputs must adapt; unsupported inputs block authoring/freeze. Schema tag/cardinality, lexical source-token kinds and instruction surface phrases are observable, not recovered graphs/entities/fact roles. Exact 3/3 collision prohibited; >=2/3 plus Jaccard >=0.12 near replay prohibited. New/new keeps six typed components with the explicit v9 ledger and comparison decision table. Historical/new retains strict ordinary Jaccard below 0.20 with the NEW side ordinal-neutralized. The surface projection is not proof of semantic independence.

Every E4 phase/round has 3 true and 2 false, rotating exact context boundaries/truths. Constant true scores 3/5, constant false 2/5, both below 4/5. Each operator has both truths across contexts; operation/type/C1/C2 allocation stays fixed.

Entity source values are pairwise semantically distinct; any wrong selection fails gold. BOOLEAN sources are prohibited (no scored E5 Boolean slot). E5-03 now uses option_a|option_b|option_c so all three entity values differ. This is a prospective new-fixture correction only. E5-03 gold indices A:R2/A:R3/B:R2/B:R3 are 0/1/2/1; E7-04 support indices 1/0/1/0. E6 has no enum; missing not_provided is not ordinary enum balance.

All 28 reserves are prospective subtype01-only backups, not generic family reserves. Matching single01 activates; mismatches, 02..05 or multiple defects stop. Actual subtype content must be proven before profile generation. E7 integration includes exact support mix/count/order and generated lexical context with A absence-first/B-last/reserve-between-supports.

Identity comparison atoms are two strings [kind,canonical_value]; historical selector fields are removed. Whole-answer equality is exact full-object replay only, not semantic-content deduplication; tuples, identities, Jaccard, structural checks and human review are complementary.

Similarity includes input.text identifiers/entities/string-code-id values and canonical schema field/type-option bytes. It excludes system, SUBJECT (record type and operation instructions), common suffix and INPUT marker. Record allocation is separately audited. Lexical forms are fixed/unavailable to authors but associated with family/phase; no statistical independence or causal lexical-effect estimate is claimed.

Historical artifacts, provider/model bindings, prompt hashes, gates/reductions and separate authorizations stay unchanged. The v7 new/new layout refinement changed prospective structural discrimination; it is not applied to invented historical metadata.

## 20. Candidate v9 joint allocation and comparison rules

The four new co-normative contracts below freeze design rules only, not a blueprint or scored content.

### Structural recurrence ledger

`g-extract1.template-recurrence.v1` derives 168 symbolic positions, 51 exact six-component fingerprint classes, and 35 subtype template groups. All 45 recurring exact classes have complete member lists and exact maximum counts in the annex. The four E7-01 reserves share one four-member exact class. Values and fixture IDs still do not enter fingerprints. Actual fixtures must pass typed semantics, subtype, lexical, value-shape and frozen wiring checks before their exact ledger class can be used.

Cross-round, cross-phase, scored/reserve, reserve/reserve, mapped reserve/primary and unmapped same-subtype reserve/primary recurrence is PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE. Unrelated family/subtype exact collisions are PROHIBITED. Replacement eligibility is separate: only a reserve's own phase/round/family subtype01 can consume it. No implicit exemption exists.

Each ordinary operand resolves a distinct source fact, in catalog operand order; SUM preserves list order. Calendar offset is literal except E1-05, whose offset is a second source INTEGER. E2-05 has one source start TIME and equal literal end. These two wiring corrections separate otherwise identical unrelated subtype classes without fingerprint IDs or values. Composed comparisons use upstream left and same-type literal right; E4-05 uses two source NUMBER facts. Entity selector facts precede bound-source facts, each in letter order. Every slot has exactly zero distractors.

### Ordinal-neutral comparison and prospective correction

`g-extract1.ordinal-neutral-similarity.v1` masks NEW generated ordinal tokens in both input.text and serialized schema: fNNN_MM -> f_MM, dNNN_MM -> d_MM, Entity NNN A/B/C -> Entity A/B/C, label/code/id_NNN_MM -> label/code/id_MM. It preserves within-fixture positions. Historical text is not guessed or rewritten, and model-facing bytes never change.

Ordinal masking alone leaves the demonstrated fresh-value 5/6 replay at Jaccard 0.0. An additional shape view maps complete numeric/date/time/option/Boolean tokens to the literal token `value`. Undeclared structure is an AUTHORING_ERROR and its >=5/6 plus max(ordinary,shape)>=0.12 replay evidence is reported. Two independently slot/domain/ledger-validated different subtypes retain the ordinary >=5/6 plus >=0.12 test: legitimate required boundary variants also share five components. Ordinary <0.20 remains for these pairs and historical/new.

Fixed E7 reserve scaffolds exceed ordinary 0.20 with fresh integers, and generated-only string copies become ordinal-neutral equality. This is a genuine prospective feasibility contradiction. Only exact-position members of one declared subtype group therefore use content-view <0.12 instead: retain ordinary five-grams containing at least one complete numeric/date/time token. Finite enum/Boolean catalog tokens and generated labels are not scalable textual freshness evidence; shape view still includes them, and their exact prospective answer allocation/scoring remains mandatory. This is not pairwise intersection subtraction. Both content sets empty is NOT_APPLICABLE, permitted only for frozen generated-label/finite-enum content with fresh raw typed VALUE sequence and no exact-reuse violation. Mandatory E4 boundary rotations and E7 presentation shifts are explicitly declared variants; no author-selected layout may enter this exception. All other pairs retain existing thresholds. This scoped correction requires rereview; it changes no qualification gate or historical result.

Report ordinary, shape, content, freshness and all exact-reuse results for every applicable pair. Raw payload equality remains prohibited. Raw VALUE freshness is source-order [schema_type,canonical semantic value], preserving generated string bytes, duplicates and numerical equivalence but not field names. Whole typed VALUE sequences must differ. Fixed Boolean/enum literals may individually recur only by their frozen allocation. Whole-answer equality remains narrow exact-object replay, not content deduplication.

### Entity-selection counterbalance

`g-extract1.entity-selection-allocation.v1` freezes zero-based indices A/B/C:

| Context | E5-01 | E5-02 | E5-03 | E5-04 | E5-05 |
|---|---:|---:|---:|---:|---:|
| A:R2 | 0 | 1 | 0 | 1 | 0 |
| A:R3 | 1 | 0 | 2 | 0 | 2 |
| B:R2 | 1 | 0 | 1 | 0 | 1 |
| B:R3 | 0 | 1 | 0 | 1 | 0 |

Always-A scores 3/2/2/3; always-B 2/1/3/2; always-C 0/2/0/0. Exhaustive schema/subtype mappings each contain 243 candidates and selector-role mappings 27. No fixed mapping reaches >=4/5 in both A and B of either round. Schema/subtype mappings can still score 5/5 in a single context; the design does not conceal that limit. All two-entity slots use both indices; three-entity slots use all three. Complete distinct populations and wrong-value substitution failure remain required. Enum gold positions are unchanged, but their permutation uses the new context-selected index.

### Value-shape allocation

`g-extract1.value-allocation.v1` freezes all 35 subtype profiles and exact context expansion. Absolute integer-part bands are SMALL 1..9, MEDIUM 10..99, LARGE 100..999. Context pattern A:R2/A:R3/B:R2/B:R3 = 0/1/1/0 gives NUMBER source precision one/two/two/one meaningful decimal places; integral-valued NUMBER has zero scored allocation. Numeric inputs are positive; only E3-02 arithmetic result is negative. Frozen temporal edge/equal slots permit zero.

E3 ADD uses MEDIUM integers with rotated carry; SUBTRACT uses MEDIUM mixed types, negative result and rotated absolute-difference borrow. SUM has three MEDIUM NUMBER operands and at least one carry. DIVIDE uses LARGE integer numerator/two-digit MEDIUM divisor: pattern0 nonintegral one-place quotient with reduced denominator a power of2; pattern1 two-place quotient with both2/5 factors. Exact rational arithmetic, no rounding. R2 conversion multiplies60 from SMALL fractional NUMBER; R3 divides1000 from LARGE fractional NUMBER. E4-02 positive INTEGER-minus-fractional-NUMBER necessarily borrows at a fractional column and is always borrow=true; a no-borrow allocation here would be impossible.

Unequal E4 gaps are numeric1, DATE1day, TIME5minutes; equal gap0. Calendar representative offsets are7..14, leap1..7, edge0/366. Clock/elapsed durations31..89, equal0. DATE years2028..2043; source TIME minute modulo30 must be nonzero. Entity sorted adjacent-value gaps are numeric2, DATE2days, TIME13minutes. Numeric/date selected rank rotates min/max; three-entity TIME selected rank is middle/min/max/middle. String/enum values follow frozen generation/permutation. Distractors are exactly0 for every position, schema/placement NOT_APPLICABLE.

Carry sums aligned absolute base10 digits with carry-in; borrow subtracts smaller from larger aligned absolute values. Precision strips trailing fractional zeros of exact canonical decimals. Matrix rules have no model-tier dependence. Marginal phase/round precision/carry/borrow are counterbalanced, but intentional edge/conversion/equality/presentation confounds remain; no causal difficulty isolation is claimed. Actual semantics, slot and value-shape validation precede deriving a reserve profile with its appended value_shape_profile.

### Interpretation and boundaries

For E7, Phase B is fresh-fixture validation under a prospectively shifted presentation order: A absence-first, B absence-last, reserves between supports. A/B differences are not solely freshness and are not identically distributed. E7-05 supported Boolean values are true/false/false/true in A:R2/A:R3/B:R2/B:R3; authors cannot choose them.

The ledger proves symbolic structural feasibility, not future content/gold/contamination acceptance. All106 historical fixtures must still adapt. Independent contamination implementations, gold review and separate future authorizations remain mandatory. No blueprint, scored/reserve corpus, provider/model contact, runtime implementation, belief change or historical rewrite is authorized. G-ROUTE4 remains unchanged CLOSED FAILED.

<!-- V9_NORMATIVE_BEGIN -->
```json
{
  "lexical_neutrality_contract": {
    "contract_id": "g-extract1.lexical-neutrality.v1",
    "all_model_facing_atoms_are_generated": true,
    "record_type_catalog_by_phase": {
      "A": [
        "record",
        "entry",
        "item",
        "case",
        "notice",
        "account",
        "order"
      ],
      "B": [
        "permit",
        "invoice",
        "schedule",
        "reading",
        "event",
        "profile",
        "docket"
      ]
    },
    "record_type_assignment": {
      "formula": "phase catalog[zero-based primary-family ordinal E1..E7]",
      "balance_per_phase_round": "each phase-specific record type occurs exactly five times among primaries; its family-slot reserve has the same record type",
      "phase_pools_disjoint": true
    },
    "identifier_generation": {
      "source_field": {
        "format": "f{fixture_ordinal:03d}_{source_field_ordinal:02d}",
        "regex": "^f(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_(?:0[1-9]|[1-9][0-9])$",
        "maximum": 99
      },
      "derived_target": {
        "format": "d{fixture_ordinal:03d}_{topological_node_ordinal:02d}",
        "regex": "^d(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_0[12]$",
        "maximum": 2
      },
      "output_field": {
        "rule": "SOURCE_COPY or EXPLICIT_ABSENCE name equals source_field; OPERATION_TARGET name equals producer_target; output fields sorted by unsigned UTF-8 name bytes",
        "regex": "^[fd](?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_(?:0[1-9]|[1-9][0-9])$"
      },
      "ordinal_sources": {
        "source_field": "first appearance of distinct source fields in source_fact_records",
        "derived_target": "stable topological node order",
        "output_field": "binding identifier; no aliases"
      },
      "meaning_independence": "f/d plus positional ordinals only; no operation, answer, comparison direction, family or risk vocabulary"
    },
    "ordinary_enum_labels": {
      "catalog": [
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "option_e",
        "option_f",
        "option_g",
        "option_h"
      ],
      "legal_schema": "a contiguous prefix of length 2..8 in catalog order",
      "special_historical_schema": "provided|not_provided",
      "other_enum_lexemes_prohibited": true
    },
    "entity_label_generation": {
      "format": "Entity {fixture_ordinal:03d} {entity_letter}",
      "fixture_ordinal": "1..168",
      "entity_letter": [
        "A",
        "B",
        "C"
      ],
      "regex": "^Entity (?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8]) [ABC]$",
      "arbitrary_title_case_labels_allowed": false
    },
    "string_value_generation": {
      "formats": [
        "label_{fixture_ordinal:03d}_{value_ordinal:02d}",
        "code_{fixture_ordinal:03d}_{value_ordinal:02d}",
        "id_{fixture_ordinal:03d}_{value_ordinal:02d}"
      ],
      "regex": "^(?:label|code|id)_(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_(?:0[1-9]|[1-9][0-9])$",
      "value_ordinal_rule": "first distinct string value in source_fact_records order; repeated references retain the same value",
      "arbitrary_prose_or_title_case_allowed": false,
      "identifier_atom_prefix": "id_",
      "prefix_rule": "first distinct string value ordinal chooses prefix from [label,code,id] cyclically: ordinal1 label, ordinal2 code, ordinal3 id, then repeat; no author-selected prefix"
    },
    "lexical_balance_and_reuse": {
      "phase_a_b_value_and_identifier_pools_disjoint": true,
      "primary_reserve_pools_disjoint": true,
      "entity_and_string_values_may_appear_in_only_one_fixture": true,
      "ordinary_enum_catalog_intentionally_shared": true,
      "record_type_pool_disjoint_by_phase": true,
      "record_type_exactly_five_per_family": true,
      "generated_field_identifiers_are_not_identity_atoms": true,
      "field_identifiers_retained_where_existing_fingerprint_rules_retain_roles": true,
      "string_prefixes_deterministic": true,
      "all_input_text_and_canonical_schema_atoms_included": true
    },
    "rejected_examples": [
      "correct_answer",
      "larger_amount",
      "comparison_value",
      "expected_total",
      "final_result",
      "pick_value",
      "higher_value",
      "threshold_result",
      "Take Larger Amount",
      "Select Bigger Sum",
      "Correct Amount",
      "Give Five",
      "Prefer First",
      "Use Second"
    ],
    "validation_vectors": [
      {
        "kind": "record_type",
        "value": "record",
        "phase": "A",
        "expected": "VALID"
      },
      {
        "kind": "record_type",
        "value": "invoice",
        "phase": "B",
        "expected": "VALID"
      },
      {
        "kind": "source_field",
        "value": "f001_01",
        "expected": "VALID"
      },
      {
        "kind": "derived_target",
        "value": "d001_02",
        "expected": "VALID"
      },
      {
        "kind": "output_field",
        "value": "d001_01",
        "expected": "VALID"
      },
      {
        "kind": "enum_schema",
        "value": "option_a|option_b|option_c",
        "expected": "VALID"
      },
      {
        "kind": "entity",
        "value": "Entity 001 A",
        "expected": "VALID"
      },
      {
        "kind": "string",
        "value": "label_168_01",
        "expected": "VALID"
      },
      {
        "kind": "forbidden",
        "value": "correct_answer",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "larger_amount",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "comparison_value",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "expected_total",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "final_result",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "pick_value",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "higher_value",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "threshold_result",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Take Larger Amount",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Select Bigger Sum",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Correct Amount",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Give Five",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Prefer First",
        "expected": "AUTHORING_ERROR"
      },
      {
        "kind": "forbidden",
        "value": "Use Second",
        "expected": "AUTHORING_ERROR"
      }
    ],
    "fixture_ordinal_assignment": {
      "domain": "1..168",
      "primary_formula": "1 + phase_offset + round_offset + zero_based_phase_round_slot; phase_offset A=0 B=84; round_offset R2=0 R3=35; primary slot 0..34 in E1..E7 then slot 01..05 order",
      "reserve_formula": "71 + phase_offset + reserve_round_offset + zero_based_family_ordinal; reserve_round_offset R2=0 R3=7; family ordinal E1=0..E7=6",
      "frozen_before_content": true,
      "meaning_independence": "ordinals depend only on frozen authoring position; expected value, operator direction, gold and observed performance never affect naming"
    },
    "non_scored_legacy_parser_vectors": "isolated raw-output classifier vectors may retain historical illustrative status/name/count strings solely to test parsing; they are not authorable fixture content",
    "causal_limit": "fixed/unavailable to authors but structurally associated with family/phase; not statistical independence or causal lexical isolation"
  },
  "entity_population_contract": {
    "contract_id": "g-extract1.entity-population.v2",
    "applies_when": "operation graph contains ENTITY_FIELD_BIND",
    "entity_count_allowed": [
      2,
      3
    ],
    "entity_object_exact_keys": [
      "selector_value",
      "selector_role"
    ],
    "entity_index_rule": "generated entity letters A,B,C in array order; zero-based array index supplies fingerprint index",
    "selector_value_rule": "Entity {fixture_ordinal:03d} {entity_letter}; exact source selector fact equality",
    "selector_field_facts_per_entity": 1,
    "source_field_facts_per_entity": 1,
    "all_entity_facts_must_be_value": true,
    "selector_schema_identical_across_entities": true,
    "source_schema_identical_across_entities": true,
    "selector_schema_required": "string",
    "selector_values_unique": true,
    "selector_fact_value_equals_entity_metadata": true,
    "selected_selector_identifies_exactly_one_entity": true,
    "all_selector_and_source_facts_entity_scoped": true,
    "non_entity_duplicate_of_selector_or_source_field_prohibited": true,
    "extra_entity_scoped_facts_allowed": false,
    "entity_fact_for_unknown_entity_allowed": false,
    "selected_source_value_copy_rule": "exact schema and value; no coercion",
    "selector_roles": [
      "IDENTIFIER",
      "ATTRIBUTE",
      "EVENT_ROLE"
    ],
    "authoring_error_conditions": [
      "entity count not 2 or 3",
      "missing or duplicate selector fact for any entity",
      "missing or duplicate source fact for any entity",
      "selector schema mismatch",
      "source schema mismatch",
      "duplicate selector value",
      "metadata/fact selector mismatch",
      "unknown entity fact",
      "non-entity duplicate selector/source field",
      "extra entity-scoped fact",
      "selected entity absent",
      "equal source values",
      "boolean source schema"
    ],
    "validation_scenarios": [
      {
        "id": "valid_two_identifier",
        "entity_count": 2,
        "selector_role": "IDENTIFIER",
        "expected": "VALID"
      },
      {
        "id": "valid_three_attribute",
        "entity_count": 3,
        "selector_role": "ATTRIBUTE",
        "expected": "VALID"
      },
      {
        "id": "valid_two_event_role",
        "entity_count": 2,
        "selector_role": "EVENT_ROLE",
        "expected": "VALID"
      },
      {
        "id": "missing_nonselected_source",
        "mutation": "remove source fact for last entity",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "missing_nonselected_selector",
        "mutation": "remove selector fact for last entity",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "mismatched_source_schema",
        "mutation": "change last source schema",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "mismatched_selector_schema",
        "mutation": "change last selector schema",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "duplicate_selector",
        "mutation": "copy first selector value to last",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "metadata_fact_mismatch",
        "mutation": "change metadata selector only",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "duplicate_source_fact",
        "mutation": "duplicate one entity source fact",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "non_entity_source_duplicate",
        "mutation": "add non-entity source field fact",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "selected_entity_absent",
        "mutation": "select unknown entity",
        "expected": "AUTHORING_ERROR"
      },
      {
        "id": "unknown_entity_fact",
        "mutation": "add fact for unknown entity",
        "expected": "AUTHORING_ERROR"
      }
    ],
    "selector_role_rule": "all entities share one role from the frozen subtype row; no author choice",
    "selector_field_must_differ_from_source_field": true,
    "source_values_pairwise_semantically_distinct": true,
    "source_value_comparison": "same-schema equality: exact rational NUMBER, exact INTEGER, string/enum bytes, DATE/TIME; equal pair AUTHORING_ERROR",
    "boolean_source_schema_allowed": false,
    "wrong_selection_invariant": "any nonselected source value substituted for selected gold fails exact comparison"
  },
  "reserve_equivalence_contract": {
    "contract_id": "g-extract1.reserve-equivalence.v1",
    "profile_exact_keys_in_order": [
      "primary_family",
      "composed_quota_row",
      "secondary_features",
      "operation_ids",
      "conversion_ids",
      "source_schema_sequence",
      "output_schema_sequence",
      "operation_result_semantic_types",
      "numeric_promotion_classes",
      "comparison_operator",
      "comparison_operand_type_pair",
      "boundary_relation",
      "temporal_operation",
      "temporal_boundary_pattern",
      "explicit_absence",
      "entity_count",
      "entity_selector_role",
      "output_role_sequence",
      "consequence_risk",
      "field_count",
      "operation_node_count",
      "subtype_slot",
      "domain_classes",
      "operation_operand_semantic_types",
      "value_shape_profile"
    ],
    "serialization": "UTF-8 compact JSON object in profile_exact_keys_in_order; ensure_ascii=true; comma/colon separators; no newline",
    "sequence_order": {
      "secondary_features": "frozen feature enum order",
      "operation_ids": "stable topological node order",
      "conversion_ids": "stable topological UNIT_CONVERSION order; NONE for other nodes",
      "source_schema_sequence": "source schema tokens sorted by unsigned UTF-8 bytes; duplicates retained; presentation order excluded",
      "output_schema_sequence": "sort [schema_type,derived_output_role] pair bytes, retain duplicates, then emit schema sequence",
      "operation_result_semantic_types": "stable topological node order",
      "numeric_promotion_classes": "stable topological node order; NOT_APPLICABLE for nonnumeric nodes",
      "output_role_sequence": "same paired schema/role order as output_schema_sequence"
    },
    "numeric_promotion_classes": [
      "INTEGER_ONLY",
      "MIXED_TO_NUMBER",
      "NUMBER_ONLY",
      "DIVIDE_TO_NUMBER",
      "UNIT_CONVERSION_TO_NUMBER",
      "NOT_APPLICABLE"
    ],
    "excluded_freshness_fields": [
      "fixture_id",
      "literal_values",
      "entity_values",
      "gold_values",
      "lexical_context",
      "generated field identifiers",
      "source-fact presentation order; typed role sequence is separately checked for fingerprint independence"
    ],
    "replacement_rule": "reserve profile bytes must equal primary profile bytes exactly",
    "integer_number_interchange_allowed": false,
    "test_vectors": [
      {
        "id": "identical",
        "left": {
          "numeric_promotion_classes": [
            "INTEGER_ONLY"
          ],
          "conversion_ids": [
            "NONE"
          ]
        },
        "right": {
          "numeric_promotion_classes": [
            "INTEGER_ONLY"
          ],
          "conversion_ids": [
            "NONE"
          ]
        },
        "expected": true
      },
      {
        "id": "integer_number_mismatch",
        "left": {
          "source_schema_sequence": [
            "integer"
          ]
        },
        "right": {
          "source_schema_sequence": [
            "number"
          ]
        },
        "expected": false
      },
      {
        "id": "conversion_mismatch",
        "left": {
          "conversion_ids": [
            "MINUTES_TO_HOURS"
          ]
        },
        "right": {
          "conversion_ids": [
            "HOURS_TO_MINUTES"
          ]
        },
        "expected": false
      },
      {
        "id": "promotion_mismatch",
        "left": {
          "numeric_promotion_classes": [
            "INTEGER_ONLY"
          ]
        },
        "right": {
          "numeric_promotion_classes": [
            "MIXED_TO_NUMBER"
          ]
        },
        "expected": false
      }
    ],
    "derivation": {
      "primary_family": "first-match family derived from canonical fixture",
      "composed_quota_row": "designated row for exact frozen subtype slot, otherwise NONE",
      "secondary_features": "derive_features result in frozen enum order",
      "operation_ids": "stable topological operation IDs",
      "conversion_ids": "one entry per node, exact conversion ID or NONE",
      "source_schema_sequence": "all source_fact_records schema tokens sorted by unsigned UTF-8 bytes, retaining duplicates; record presentation order is fingerprint metadata rather than a reserve type-equivalence dimension",
      "output_schema_sequence": "sort compact [schema_type,derived_output_role] pair bytes and emit schema types in that order, retaining duplicates",
      "operation_result_semantic_types": "operation evaluator result tag for each stable topological node",
      "numeric_promotion_classes": "ADD/SUBTRACT/MULTIPLY/SUM: INTEGER_ONLY if all operands INTEGER, NUMBER_ONLY if all NUMBER, MIXED_TO_NUMBER otherwise; DIVIDE_TO_NUMBER for DIVIDE; UNIT_CONVERSION_TO_NUMBER for UNIT_CONVERSION; NOT_APPLICABLE otherwise",
      "comparison_operator": "unique comparison ID or NONE",
      "comparison_operand_type_pair": "resolved left/right semantic tags or empty array",
      "boundary_relation": "derived BELOW/EQUAL/ABOVE or NONE",
      "temporal_operation": "unique temporal operation ID or NONE",
      "temporal_boundary_pattern": "existing contamination temporal pattern derived from exact source/result",
      "explicit_absence": "true iff valid E7 shape",
      "entity_count": "length of complete entities array",
      "entity_selector_role": "common entities.selector_role or NONE",
      "output_role_sequence": "emit corresponding roles in the same canonical schema/role pair order",
      "consequence_risk": "exact R2 or R3 from frozen slot",
      "field_count": "output field count",
      "operation_node_count": "operation node count",
      "subtype_slot": "frozen E1-01..E7-05 allocation slot",
      "domain_classes": "applicable slot obligations after subtype-content-validation.v1 proves actual content: context comparison row/enum position, temporal predicates, numeric types/signs, selection/unit ID",
      "operation_operand_semantic_types": "one array per stable-topological node in catalog placeholder order with SUM array order; resolved semantic operand tags; ENTITY_FIELD_BIND is [selected source semantic type,STRING,STRING]"
    },
    "validation_sequence": [
      "derive actual semantics",
      "validate actual lexical/subtype context",
      "derive profile from proven actual type/domain/results",
      "compare bytes; never bypass contamination/gold review"
    ],
    "value_shape_profile_binding": "g-extract1.value-allocation.v1"
  },
  "subtype_allocation_contract": {
    "contract_id": "g-extract1.subtype-allocation.v2",
    "applies_identically_to": [
      "A:R2",
      "A:R3",
      "B:R2",
      "B:R3"
    ],
    "fixtures_per_phase_round": 35,
    "fixtures_per_family": 5,
    "slot_rows": {
      "E1": [
        {
          "slot_id": "E1-01",
          "operation_shape": "CALENDAR_DAY_OFFSET",
          "coverage_class": "within_month",
          "domain": "offset_1_to_27"
        },
        {
          "slot_id": "E1-02",
          "operation_shape": "CALENDAR_DAY_OFFSET",
          "coverage_class": "month_boundary",
          "domain": "offset_1_to_31"
        },
        {
          "slot_id": "E1-03",
          "operation_shape": "CALENDAR_DAY_OFFSET",
          "coverage_class": "year_boundary",
          "domain": "offset_1_to_31"
        },
        {
          "slot_id": "E1-04",
          "operation_shape": "CALENDAR_DAY_OFFSET",
          "coverage_class": "leap_day_boundary",
          "domain": "leap_year_required"
        },
        {
          "slot_id": "E1-05",
          "operation_shape": "CALENDAR_DAY_OFFSET",
          "coverage_class": "edge_offset",
          "domain": "R2_offset_0_R3_offset_366"
        }
      ],
      "E2": [
        {
          "slot_id": "E2-01",
          "operation_shape": "CLOCK_MINUTE_OFFSET",
          "coverage_class": "same_day",
          "domain": "no_rollover"
        },
        {
          "slot_id": "E2-02",
          "operation_shape": "CLOCK_MINUTE_OFFSET",
          "coverage_class": "clock_rollover",
          "domain": "midnight_rollover"
        },
        {
          "slot_id": "E2-03",
          "operation_shape": "ELAPSED_MINUTES",
          "coverage_class": "ordinary_elapsed",
          "domain": "end_after_start"
        },
        {
          "slot_id": "E2-04",
          "operation_shape": "ELAPSED_MINUTES",
          "coverage_class": "elapsed_rollover",
          "domain": "end_before_start"
        },
        {
          "slot_id": "E2-05",
          "operation_shape": "ELAPSED_MINUTES",
          "coverage_class": "equal_time_zero",
          "domain": "start_equals_end"
        }
      ],
      "E3": [
        {
          "slot_id": "E3-01",
          "operation_shape": "ADD",
          "coverage_class": "single_node",
          "domain": "INTEGER_ONLY"
        },
        {
          "slot_id": "E3-02",
          "operation_shape": "SUBTRACT",
          "coverage_class": "single_node",
          "domain": "MIXED_TO_NUMBER"
        },
        {
          "slot_id": "E3-03",
          "operation_shape": "SUM",
          "coverage_class": "single_node_three_operands",
          "domain": "NUMBER_ONLY"
        },
        {
          "slot_id": "E3-04",
          "operation_shape": "DIVIDE>EXACT_COPY",
          "coverage_class": "C3",
          "domain": "DIVIDE_TO_NUMBER"
        },
        {
          "slot_id": "E3-05",
          "operation_shape": "UNIT_CONVERSION>EXACT_COPY",
          "coverage_class": "C3",
          "domain": "UNIT_CONVERSION_TO_NUMBER"
        }
      ],
      "E4": [
        {
          "slot_id": "E4-01",
          "operation_shape": "ADD>GT",
          "coverage_class": "C1",
          "domain": "comparison_slot_matrix[phase:risk_round][slot_id]"
        },
        {
          "slot_id": "E4-02",
          "operation_shape": "SUBTRACT>LTE",
          "coverage_class": "C1",
          "domain": "comparison_slot_matrix[phase:risk_round][slot_id]"
        },
        {
          "slot_id": "E4-03",
          "operation_shape": "CALENDAR_DAY_OFFSET>GTE",
          "coverage_class": "C2",
          "domain": "comparison_slot_matrix[phase:risk_round][slot_id]"
        },
        {
          "slot_id": "E4-04",
          "operation_shape": "CLOCK_MINUTE_OFFSET>LT",
          "coverage_class": "C2",
          "domain": "comparison_slot_matrix[phase:risk_round][slot_id]"
        },
        {
          "slot_id": "E4-05",
          "operation_shape": "EQ",
          "coverage_class": "direct_comparison",
          "domain": "comparison_slot_matrix[phase:risk_round][slot_id]"
        }
      ],
      "E5": [
        {
          "slot_id": "E5-01",
          "operation_shape": "ENTITY_FIELD_BIND",
          "coverage_class": "entities_2:IDENTIFIER",
          "domain": "number"
        },
        {
          "slot_id": "E5-02",
          "operation_shape": "ENTITY_FIELD_BIND",
          "coverage_class": "entities_2:ATTRIBUTE",
          "domain": "string"
        },
        {
          "slot_id": "E5-03",
          "operation_shape": "ENTITY_FIELD_BIND",
          "coverage_class": "entities_3:EVENT_ROLE",
          "domain": "option_a|option_b|option_c"
        },
        {
          "slot_id": "E5-04",
          "operation_shape": "ENTITY_FIELD_BIND",
          "coverage_class": "entities_2:IDENTIFIER",
          "domain": "YYYY-MM-DD"
        },
        {
          "slot_id": "E5-05",
          "operation_shape": "ENTITY_FIELD_BIND",
          "coverage_class": "entities_3:ATTRIBUTE",
          "domain": "HH:MM"
        }
      ],
      "E6": [
        {
          "slot_id": "E6-01",
          "operation_shape": "EXACT_COPY(source)",
          "coverage_class": "source_copy",
          "domain": "integer"
        },
        {
          "slot_id": "E6-02",
          "operation_shape": "EXACT_COPY(source)",
          "coverage_class": "source_copy",
          "domain": "number"
        },
        {
          "slot_id": "E6-03",
          "operation_shape": "EXACT_COPY(source)",
          "coverage_class": "source_copy",
          "domain": "string"
        },
        {
          "slot_id": "E6-04",
          "operation_shape": "CALENDAR_DAY_OFFSET>EXACT_COPY",
          "coverage_class": "derived_copy",
          "domain": "YYYY-MM-DD"
        },
        {
          "slot_id": "E6-05",
          "operation_shape": "CLOCK_MINUTE_OFFSET>EXACT_COPY",
          "coverage_class": "derived_copy",
          "domain": "HH:MM"
        }
      ],
      "E7": [
        {
          "slot_id": "E7-01",
          "operation_shape": "zero_node_absence",
          "coverage_class": "support_schemas",
          "domain": [
            "integer",
            "integer"
          ]
        },
        {
          "slot_id": "E7-02",
          "operation_shape": "zero_node_absence",
          "coverage_class": "support_schemas",
          "domain": [
            "number",
            "string"
          ]
        },
        {
          "slot_id": "E7-03",
          "operation_shape": "zero_node_absence",
          "coverage_class": "support_schemas",
          "domain": [
            "YYYY-MM-DD",
            "HH:MM"
          ]
        },
        {
          "slot_id": "E7-04",
          "operation_shape": "zero_node_absence",
          "coverage_class": "support_schemas",
          "domain": [
            "option_a|option_b",
            "string"
          ]
        },
        {
          "slot_id": "E7-05",
          "operation_shape": "zero_node_absence",
          "coverage_class": "support_schemas",
          "domain": [
            "boolean",
            "number",
            "integer"
          ]
        }
      ]
    },
    "composed_rows": {
      "C1": [
        "E4-01",
        "E4-02"
      ],
      "C2": [
        "E4-03",
        "E4-04"
      ],
      "C3": [
        "E3-04",
        "E3-05"
      ],
      "C4": [
        "E5-01",
        "E5-02"
      ]
    },
    "distinct_composed_fixtures_per_phase_round": 8,
    "one_slot_may_satisfy_at_most_one_composed_row": true,
    "numeric_promotion_coverage": {
      "INTEGER_ONLY": [
        "E3-01"
      ],
      "MIXED_TO_NUMBER": [
        "E3-02"
      ],
      "NUMBER_ONLY": [
        "E3-03"
      ],
      "DIVIDE_TO_NUMBER": [
        "E3-04"
      ],
      "UNIT_CONVERSION_TO_NUMBER": [
        "E3-05"
      ]
    },
    "comparison_operator_coverage": {
      "GT": [
        "E4-01"
      ],
      "LTE": [
        "E4-02"
      ],
      "GTE": [
        "E4-03"
      ],
      "LT": [
        "E4-04"
      ],
      "EQ": [
        "E4-05"
      ]
    },
    "comparison_boundary_coverage": {
      "A:R2": {
        "BELOW": [
          "E4-04",
          "E4-05"
        ],
        "EQUAL": [
          "E4-03"
        ],
        "ABOVE": [
          "E4-01",
          "E4-02"
        ]
      },
      "A:R3": {
        "BELOW": [
          "E4-01"
        ],
        "EQUAL": [
          "E4-02",
          "E4-05"
        ],
        "ABOVE": [
          "E4-03",
          "E4-04"
        ]
      },
      "B:R2": {
        "BELOW": [
          "E4-02"
        ],
        "EQUAL": [
          "E4-01",
          "E4-05"
        ],
        "ABOVE": [
          "E4-03",
          "E4-04"
        ]
      },
      "B:R3": {
        "BELOW": [
          "E4-03",
          "E4-04"
        ],
        "EQUAL": [
          "E4-02"
        ],
        "ABOVE": [
          "E4-01",
          "E4-05"
        ]
      }
    },
    "comparison_domain_coverage": {
      "numeric": [
        "E4-01",
        "E4-02",
        "E4-05"
      ],
      "date": [
        "E4-03"
      ],
      "time": [
        "E4-04"
      ]
    },
    "cross_cutting_result_type_minimum": {
      "INTEGER": 1,
      "NUMBER": 1,
      "DATE": 1,
      "TIME": 1,
      "BOOLEAN": 5,
      "STRING_OR_ENUM_SOURCE_COPY": 1
    },
    "phase_a_b_structure": "same operation/type/subtype matrix except explicit context E4 boundary/truth rotation; 3 true/2 false each",
    "phase_a_b_content": "fresh values/identities with declared template recurrence; E7 Phase B includes presentation shift",
    "multiplication_note": "MULTIPLY remains catalog-valid but has zero scored allocation in G-EXTRACT1 v8; the fixed five-slot E3 allocation prioritizes SUM, DIVIDE, and UNIT_CONVERSION diagnosed coverage",
    "blueprint_reallocation_allowed": false,
    "unit_conversion_assignment": {
      "A:R2": "HOURS_TO_MINUTES",
      "A:R3": "GRAMS_TO_KILOGRAMS",
      "B:R2": "HOURS_TO_MINUTES",
      "B:R3": "GRAMS_TO_KILOGRAMS"
    },
    "numeric_comparison_operand_classes": {
      "E4-01": "INTEGER_ONLY",
      "E4-02": "MIXED_TO_NUMBER",
      "E4-05": "NUMBER_ONLY"
    },
    "comparison_pair_types": {
      "E4-01": [
        "INTEGER",
        "INTEGER"
      ],
      "E4-02": [
        "NUMBER",
        "NUMBER"
      ],
      "E4-03": [
        "DATE",
        "DATE"
      ],
      "E4-04": [
        "TIME",
        "TIME"
      ],
      "E4-05": [
        "NUMBER",
        "NUMBER"
      ]
    },
    "exact_slot_boundary_predicates": {
      "within_month": "offset 1..27 and source/result month and year equal, no Feb 29 in inclusive interval",
      "month_boundary": "source/result month differs but year equal, no Feb 29 in inclusive interval",
      "year_boundary": "source/result year differs, no Feb 29 in inclusive interval",
      "leap_day_boundary": "inclusive source/result interval contains Feb 29 and source/result differ",
      "edge_offset": "R2 exactly 0, R3 exactly 366; resulting temporal fingerprint independently derived",
      "same_day": "clock offset 1..1439, start_minutes + offset <1440",
      "clock_rollover": "clock offset 1..1439, start_minutes + offset >=1440",
      "ordinary_elapsed": "end_minutes > start_minutes",
      "elapsed_rollover": "end_minutes < start_minutes",
      "equal_time_zero": "end_minutes == start_minutes"
    },
    "composed_feature_vs_quota": "all E5 entity binds carry C4 feature; only E5-01/E5-02 fill its two required quota slots; no fixture fills two rows",
    "value_pool_independence": "all complete typed literal vectors and derived gold objects must differ between scored/reserve fixtures under exact-reuse rules; reserve profile permits only its frozen type/domain class, never post-output choice",
    "output_field_counts": {
      "E1": 1,
      "E2": 1,
      "E3": 1,
      "E4": 1,
      "E5": 1,
      "E6": 1,
      "E7-01": 3,
      "E7-02": 3,
      "E7-03": 3,
      "E7-04": 3,
      "E7-05": 4
    },
    "secondary_temporal_domains": {
      "E4-03": "month_boundary; positive calendar offset 1..31; no Feb29 in inclusive interval",
      "E4-04": "clock_rollover; positive offset 1..1439",
      "E6-04": "year_boundary; calendar offset 1..31; no Feb29 in inclusive interval",
      "E6-05": "clock_rollover; positive offset 1..1439"
    },
    "edge_temporal_domain": {
      "R2": "offset0; source is not Feb29; DATE_WITHIN_MONTH",
      "R3": "offset366; inclusive interval excludes Feb29; YEAR_BOUNDARY"
    },
    "non_numeric_copy_types": {
      "E6-03": "string",
      "E6-04": "YYYY-MM-DD",
      "E6-05": "HH:MM"
    },
    "numeric_result_sign_coverage": {
      "E3-01": "positive",
      "E3-02": "negative",
      "E3-03": "positive",
      "E3-04": "positive_non_integral",
      "E3-05": "positive",
      "E4-01": "positive",
      "E4-02": "positive"
    },
    "field_typing_for_numeric_slots": {
      "E3-01": [
        "INTEGER",
        "INTEGER"
      ],
      "E3-02": [
        "INTEGER",
        "NUMBER"
      ],
      "E3-03": [
        "NUMBER",
        "NUMBER",
        "NUMBER"
      ],
      "E3-04": [
        "INTEGER",
        "INTEGER"
      ],
      "E3-05": [
        "NUMBER"
      ],
      "E4-01": [
        "INTEGER",
        "INTEGER"
      ],
      "E4-02": [
        "INTEGER",
        "NUMBER"
      ]
    },
    "operand_orientation": "numeric and temporal composed nodes are comparison left operand; right operand is same result semantic type; no blueprint reversal; direct E4-05 uses two NUMBER source facts",
    "e7_support_shape_order": "support schema order follows row domain; absence position follows phase/reserve source-order rule; output names follow generated source bindings; exact supported count, no extra facts",
    "catalog_vs_sampling": "the finite operation catalog defines mechanical legality; only slot_rows may be authored as scored/reserve fixtures; MULTIPLY and unallocated conversion IDs are mechanical-validation coverage only",
    "reserve_subtype_slot": "E1-01..E7-01 for each family reserve, per phase/round; profile byte identity mandatory",
    "e7_source_order": {
      "A": "absence then supported facts in frozen support-schema order",
      "B": "supported facts in frozen support-schema order then absence",
      "reserve": "first supported fact then absence then remaining supported facts in frozen order"
    },
    "comparison_slot_matrix": {
      "A:R2": {
        "E4-01": {
          "operator": "GT",
          "operand_domain": "numeric",
          "boundary_relation": "ABOVE",
          "gold_boolean": true,
          "composed_row": "C1",
          "numeric_promotion_class": "INTEGER_ONLY",
          "operand_type_pair": [
            "INTEGER",
            "INTEGER"
          ]
        },
        "E4-02": {
          "operator": "LTE",
          "operand_domain": "numeric",
          "boundary_relation": "ABOVE",
          "gold_boolean": false,
          "composed_row": "C1",
          "numeric_promotion_class": "MIXED_TO_NUMBER",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        },
        "E4-03": {
          "operator": "GTE",
          "operand_domain": "date",
          "boundary_relation": "EQUAL",
          "gold_boolean": true,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "DATE",
            "DATE"
          ]
        },
        "E4-04": {
          "operator": "LT",
          "operand_domain": "time",
          "boundary_relation": "BELOW",
          "gold_boolean": true,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "TIME",
            "TIME"
          ]
        },
        "E4-05": {
          "operator": "EQ",
          "operand_domain": "numeric",
          "boundary_relation": "BELOW",
          "gold_boolean": false,
          "composed_row": "NONE",
          "numeric_promotion_class": "NUMBER_ONLY",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        }
      },
      "A:R3": {
        "E4-01": {
          "operator": "GT",
          "operand_domain": "numeric",
          "boundary_relation": "BELOW",
          "gold_boolean": false,
          "composed_row": "C1",
          "numeric_promotion_class": "INTEGER_ONLY",
          "operand_type_pair": [
            "INTEGER",
            "INTEGER"
          ]
        },
        "E4-02": {
          "operator": "LTE",
          "operand_domain": "numeric",
          "boundary_relation": "EQUAL",
          "gold_boolean": true,
          "composed_row": "C1",
          "numeric_promotion_class": "MIXED_TO_NUMBER",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        },
        "E4-03": {
          "operator": "GTE",
          "operand_domain": "date",
          "boundary_relation": "ABOVE",
          "gold_boolean": true,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "DATE",
            "DATE"
          ]
        },
        "E4-04": {
          "operator": "LT",
          "operand_domain": "time",
          "boundary_relation": "ABOVE",
          "gold_boolean": false,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "TIME",
            "TIME"
          ]
        },
        "E4-05": {
          "operator": "EQ",
          "operand_domain": "numeric",
          "boundary_relation": "EQUAL",
          "gold_boolean": true,
          "composed_row": "NONE",
          "numeric_promotion_class": "NUMBER_ONLY",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        }
      },
      "B:R2": {
        "E4-01": {
          "operator": "GT",
          "operand_domain": "numeric",
          "boundary_relation": "EQUAL",
          "gold_boolean": false,
          "composed_row": "C1",
          "numeric_promotion_class": "INTEGER_ONLY",
          "operand_type_pair": [
            "INTEGER",
            "INTEGER"
          ]
        },
        "E4-02": {
          "operator": "LTE",
          "operand_domain": "numeric",
          "boundary_relation": "BELOW",
          "gold_boolean": true,
          "composed_row": "C1",
          "numeric_promotion_class": "MIXED_TO_NUMBER",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        },
        "E4-03": {
          "operator": "GTE",
          "operand_domain": "date",
          "boundary_relation": "ABOVE",
          "gold_boolean": true,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "DATE",
            "DATE"
          ]
        },
        "E4-04": {
          "operator": "LT",
          "operand_domain": "time",
          "boundary_relation": "ABOVE",
          "gold_boolean": false,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "TIME",
            "TIME"
          ]
        },
        "E4-05": {
          "operator": "EQ",
          "operand_domain": "numeric",
          "boundary_relation": "EQUAL",
          "gold_boolean": true,
          "composed_row": "NONE",
          "numeric_promotion_class": "NUMBER_ONLY",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        }
      },
      "B:R3": {
        "E4-01": {
          "operator": "GT",
          "operand_domain": "numeric",
          "boundary_relation": "ABOVE",
          "gold_boolean": true,
          "composed_row": "C1",
          "numeric_promotion_class": "INTEGER_ONLY",
          "operand_type_pair": [
            "INTEGER",
            "INTEGER"
          ]
        },
        "E4-02": {
          "operator": "LTE",
          "operand_domain": "numeric",
          "boundary_relation": "EQUAL",
          "gold_boolean": true,
          "composed_row": "C1",
          "numeric_promotion_class": "MIXED_TO_NUMBER",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        },
        "E4-03": {
          "operator": "GTE",
          "operand_domain": "date",
          "boundary_relation": "BELOW",
          "gold_boolean": false,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "DATE",
            "DATE"
          ]
        },
        "E4-04": {
          "operator": "LT",
          "operand_domain": "time",
          "boundary_relation": "BELOW",
          "gold_boolean": true,
          "composed_row": "C2",
          "numeric_promotion_class": "NOT_APPLICABLE",
          "operand_type_pair": [
            "TIME",
            "TIME"
          ]
        },
        "E4-05": {
          "operator": "EQ",
          "operand_domain": "numeric",
          "boundary_relation": "ABOVE",
          "gold_boolean": false,
          "composed_row": "NONE",
          "numeric_promotion_class": "NUMBER_ONLY",
          "operand_type_pair": [
            "NUMBER",
            "NUMBER"
          ]
        }
      }
    },
    "comparison_truth_invariant": {
      "true_count_per_phase_round": 3,
      "false_count_per_phase_round": 2,
      "constant_true_baseline_score": "3/5",
      "constant_false_baseline_score": "2/5",
      "both_constants_fail_family_floor_4_of_5": true,
      "rotation_rule": "each operator has both true and false across exact contexts; not independence from observable position"
    },
    "enum_answer_positions": {
      "A:R2": {
        "E5-03": 0,
        "E7-04": 1
      },
      "A:R3": {
        "E5-03": 1,
        "E7-04": 0
      },
      "B:R2": {
        "E5-03": 2,
        "E7-04": 1
      },
      "B:R3": {
        "E5-03": 1,
        "E7-04": 0
      }
    },
    "enum_position_rule": "zero-based schema index; E5-03 has three options, entity i receives option[(i-selected_index+gold_index) mod 3]; E7-04 support enum uses exact context index; E6 no enum slot; missing not_provided excluded from ordinary balancing",
    "entity_selected_index_binding": "g-extract1.entity-selection-allocation.v1"
  },
  "historical_fingerprint_adapter_contract": {
    "contract_id": "g-extract1.historical-fingerprint-adapter.v1",
    "recoverability": "fixture_id/task_class/input.schema/input.text/prompt available; no typed graph/entity/fact roles; never reconstruct unavailable semantics",
    "artifact_bindings": [
      {
        "path": "experiments/G-ROUTE4-candidate/sealed/corpus_a.json",
        "sha256": "6eb8683581fc66f6d445eaed38120415edb05c4779bf082b6c27ef10f899e82d"
      },
      {
        "path": "experiments/G-ROUTE4-candidate/sealed/corpus_b.json",
        "sha256": "f8d93db6bde59f548c5792ad7717fad6238f70a755550391ec7c855a39afc1bf"
      },
      {
        "path": "experiments/G-ROUTE4-candidate/sealed/reserve_corpus_a.json",
        "sha256": "cd5d5c4325c1fd476989082c18a9164150ef32763d3d46d2b144e5bb3afd30e9"
      },
      {
        "path": "experiments/G-ROUTE4-candidate/sealed/reserve_corpus_b.json",
        "sha256": "1f1eced43fb4e2b34acc21e96d5f6c991f3e328fab17bb8ad6e6e1b110d5c088"
      }
    ],
    "expected_historical_extraction_count": 106,
    "selection": "listed artifact order then fixtures array order; task_class exactly structured_extraction; historical duplicates remain distinct inputs",
    "projection_component_order": [
      "output_schema_signature",
      "source_token_kind_sequence",
      "instruction_surface_sequence"
    ],
    "output_schema_signature": "parse schema-types.v1; [semantic_tag,enum_option_count] per output, primitive count 0; duplicates retained, compact row bytes sorted UTF-8; no field names/enum lexemes",
    "source_token_kind_sequence": "NFC/casefold/CRLF-or-CR-to-LF/Unicode whitespace collapse; frozen ASCII tokenizer; full DATE/TIME/NUMBER regex selects kind, otherwise IDENTIFIER; preserve order/duplicates; lexical shapes, not source semantic tags",
    "instruction_surface_sequence": "require exact terminal historical suffix (template minus {SUBJECT}); strip only that suffix; normalize SUBJECT as above; ASCII re.finditer catalog alternation order; emit surface IDs, never operation/dependency semantics",
    "surface_catalog": [
      {
        "id": "GTE_WORDS",
        "regex": "\\bgreater than or equal to\\b"
      },
      {
        "id": "LTE_WORDS",
        "regex": "\\bless than or equal to\\b"
      },
      {
        "id": "GT_WORDS",
        "regex": "\\bgreater than\\b"
      },
      {
        "id": "LT_WORDS",
        "regex": "\\bless than\\b"
      },
      {
        "id": "EQ_WORDS",
        "regex": "\\bequal to\\b"
      },
      {
        "id": "MORE_THAN",
        "regex": "\\bmore than\\b"
      },
      {
        "id": "AT_LEAST",
        "regex": "\\bat least\\b"
      },
      {
        "id": "AT_MOST",
        "regex": "\\bat most\\b"
      },
      {
        "id": "PLUS",
        "regex": "\\bplus\\b"
      },
      {
        "id": "MINUS",
        "regex": "\\bminus\\b"
      },
      {
        "id": "TIMES",
        "regex": "\\btimes\\b"
      },
      {
        "id": "DIVIDED_BY",
        "regex": "\\bdivided by\\b"
      },
      {
        "id": "SUM_OF",
        "regex": "\\b(?:the )?sum of\\b"
      },
      {
        "id": "BEFORE",
        "regex": "\\bbefore\\b"
      },
      {
        "id": "AFTER",
        "regex": "\\bafter\\b"
      }
    ],
    "source_kind_regex": {
      "DATE": "[0-9]{4}-[0-9]{2}-[0-9]{2}",
      "TIME": "[0-9]{2}:[0-9]{2}",
      "NUMBER": "[+-]?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)(?:e[+-]?[0-9]+)?"
    },
    "serialization": "UTF-8 compact JSON array in component order; ensure_ascii=true; comma/colon separators; no newline",
    "new_projection": "validate canonical fixture/subtype; render source facts/schema/catalog SUBJECT/full prompt; apply identical projection to rendered input/schema/prompt",
    "unavailable_components": "omitted on both sides, no sentinel/fabricated graph/entity/fact roles",
    "historical_new_collision": "3/3 equal => prohibited regardless of Jaccard",
    "historical_new_near_replay": "at least 2/3 equal AND existing payload token-5gram Jaccard>=0.12 => prohibited",
    "new_new": "six typed components with explicit v9 ledger/template controls; historical adapter creates no new/new rule",
    "jaccard_gate": "historical/new ordinary Jaccard strictly <0.20; new/new uses explicit v9 comparison modes",
    "rationale": "separate conservative observable check, at most one differing component for near replay; not recovered semantic independence; exact reuse/human review still mandatory",
    "unsupported_handling": "wrong/missing types, unsupported schema, empty tokens, suffix/digest mismatch or unstable bytes => BLOCK_AUTHORING_AND_FREEZE, path/fixture/reason reported; never skip/invent",
    "independence": "both independent contamination modules compare these bytes and all existing new/new outputs; disagreement blocks freeze"
  },
  "subtype_content_validation_contract": {
    "contract_id": "g-extract1.subtype-content-validation.v1",
    "context": "exact lexical_context keys phase,risk_round,fixture_ordinal,primary_family_slot,within_family_slot; computed ordinal; within_family_slot 01..05 primary or null reserve; reserve only01",
    "sequence": [
      "typed semantics/gold",
      "generated lexical context",
      "actual operation shape/output count/schema",
      "resolved operand types/promotion",
      "sign/SUM count/conversion",
      "comparison matrix/orientation",
      "temporal slot predicates",
      "entity row/enum permutation",
      "E7 support mix/order",
      "then reserve profile"
    ],
    "numeric": "field_typing_for_numeric_slots exact resolved first-node types; three SUM operands; exact sign/nonintegral DIVIDE; exact context conversion",
    "comparison": "exact matrix operator/domain/boundary/truth/pair; upstream left argument in composed slots; direct EQ two NUMBER source fields",
    "temporal": "evaluate actual source/result then exact slot calendar interval/range/Feb29/month/year/edge predicates, positive clock exact rollover, elapsed >/< /== by slot",
    "entity": "complete pairwise-distinct population; exact row count/role/schema/selected index and E5-03 option permutation",
    "E6": "EXACT_COPY(source) requires field_identifier; temporal-copy schema/domain exact",
    "E7": "zero-node shape plus exact output/source counts and support order; no extras/entities; generated bindings; A absence-first/B-last/reserve between support1/2; support enum gold index fixed",
    "any_mismatch": "AUTHORING_ERROR before profile; never copy unproven declaration",
    "non_scored_mechanical_vectors": "existing validator vectors may be reindexed to exact lexical slot context for deterministic checking only; no scored/reserve corpus created",
    "v9_sequence": [
      "derive actual typed semantics/gold",
      "validate slot and context-selected entity",
      "validate value-shape and frozen wiring",
      "derive actual fingerprint and check ledger",
      "derive profile including validated value shape",
      "compare canonical bytes"
    ]
  },
  "source_contamination_atom_contract": {
    "sources_in_order": [
      "source_fact_records array order",
      "operation_nodes stable topological order then catalog argument order and SUM operand order",
      "gold output fields sorted by unsigned UTF-8 field name"
    ],
    "included_kinds": [
      "date_literal",
      "time_literal",
      "integer_literal",
      "decimal_literal",
      "gold date",
      "gold time",
      "gold integer",
      "gold number"
    ],
    "atom": "[origin_tag,type_tag,canonical_value]",
    "duplicates_preserved": true,
    "serialization": "compact UTF-8 JSON array ensure_ascii=true in source order",
    "eligibility": "tuple is compared only when it contains at least one date/time atom and at least one integer/number atom",
    "match_rule": "eligible tuple bytes equal",
    "source_fact_type_tag": "derive from source fact schema_type through schema-types.v1, never literal token shape",
    "operation_argument_type_tag": "ordinary field reference resolves unique non-entity source; ENTITY_FIELD_BIND source/selector references resolve exactly the selected entity's complete facts; derived reference resolves upstream type; literal defines its semantic type",
    "gold_type_tag": "source, resolved operation arguments and gold tags use schema/semantic types; exact NUMBER canonicalization is finite rational -> fixed-point decimal without rounding, preserving NUMBER versus INTEGER",
    "number_integer_distinction": "number schema plus integer literal serializes NUMBER canonical n.0; integer schema plus same literal serializes INTEGER n",
    "canonical_value_serialization": {
      "INTEGER": "canonical integer",
      "NUMBER": "canonical exact decimal with decimal point",
      "DATE": "YYYY-MM-DD",
      "TIME": "HH:MM"
    },
    "value_extraction": "SOURCE_FACT schema-derived tags; each operation argument resolved by semantic type in catalog placeholder order, SUM array order; gold by output schema in UTF-8 name order; preserve duplicates"
  },
  "identity_atom_contract": {
    "entity": "every generated entities.selector_value",
    "identifier": "every source string VALUE matching ^id_(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_(?:0[1-9]|[1-9][0-9])$",
    "syntactic_field_names_excluded": true,
    "historical_identifier_rule": "for historical G-ROUTE4 only, retain its id/_id/_code/_identifier/_reference field rule; compare canonical value atoms across old and new",
    "historical_projection": "structured historical id/_id/_code/_identifier/_reference fields select canonical values, field names removed; unstructured identity semantics reported unavailable, never guessed"
  },
  "enum_schema_identity_contract": {
    "operations": [
      "ENTITY_FIELD_BIND",
      "EXACT_COPY"
    ],
    "rule": "source and output historical schema bytes must be identical, including finite-enum option set and order",
    "widening_narrowing_or_reordering_allowed": false,
    "test_vectors": [
      {
        "source": "option_a|option_b",
        "output": "option_a|option_b",
        "expected": "VALID"
      },
      {
        "source": "option_a|option_b",
        "output": "option_a|option_b|option_c",
        "expected": "AUTHORING_ERROR"
      },
      {
        "source": "option_a|option_b",
        "output": "option_b|option_a",
        "expected": "AUTHORING_ERROR"
      },
      {
        "source": "option_a|option_b|option_c",
        "output": "option_a|option_b",
        "expected": "AUTHORING_ERROR"
      }
    ]
  },
  "e7_integrated_shape_contract": {
    "operations": 0,
    "explicit_absence_outputs": 1,
    "absence_schema": "provided|not_provided",
    "absence_gold": "not_provided",
    "minimum_supported_source_copy_outputs": 2,
    "all_supported_source_copies_require_complete_unique_source_facts": true,
    "invalid_cases": [
      "wrong absence schema",
      "wrong absence gold",
      "two absence outputs",
      "fewer than two supported copies",
      "operation node present",
      "unsupported field binding",
      "incomplete source facts"
    ]
  },
  "fingerprint_layout_contract": {
    "id": "source_fact_layout",
    "type": "array",
    "allowed": [
      "CONTIGUOUS_SINGLE_ENTITY",
      "INTERLEAVED_MULTI_ENTITY",
      "DISTRACTOR_BEFORE_TARGET",
      "DISTRACTOR_AFTER_TARGET",
      "TARGET_BEFORE_SUPPORTING_FACTS",
      "EXPLICIT_PARTIAL_ABSENCE"
    ],
    "derivation": "derive source_fact_sequence mechanically; compute existing first-match layout enum or AUTHORING_ERROR; pair each role/index with that source fact schema_type; retain complete sequence and duplicates; no literals or field names included",
    "structure": "[existing_layout_enum, typed_fact_role_sequence]; each sequence row is [role, historical_schema_type, entity_index] in source-record order"
  },
  "reserve_activation_contract": {
    "contract_id": "g-extract1.reserve-activation.v5",
    "interpretation": "one prospective subtype01-only backup per phase/round/family, not a generic family reserve or one reserve per scored fixture",
    "slot_id_format": "RESERVE:{phase}:{round}:{primary_family}",
    "slot_domains": {
      "phase": [
        "A",
        "B"
      ],
      "round": [
        "R2",
        "R3"
      ],
      "primary_family": [
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7"
      ]
    },
    "total_reserve_slots": 28,
    "reserves_per_phase_round_primary_family_slot": 1,
    "selection_pool_allowed": false,
    "mapping_frozen_before_review": true,
    "slot_record_exact_keys": [
      "slot_id",
      "phase",
      "round",
      "primary_family",
      "reserve_fixture_id",
      "replacement_profile",
      "ordered_primary_fixture_ids"
    ],
    "ordered_primary_fixture_ids": "all five primary fixture IDs in the slot sorted by unsigned UTF-8 bytes and frozen before review",
    "replacement_profile": "canonical bytes from g-extract1.reserve-equivalence.v1",
    "activation_algorithm": [
      "evaluate all five frozen primary IDs and all eligible pre-contact defect reasons",
      "zero defective primaries: NO_ACTIVATION",
      "more than one defective primary: STOP_AUTHORING before any selection",
      "exactly one defective primary: only within-family slot01 can activate; otherwise STOP_AUTHORING",
      "slot01 must match the single reserve canonical profile byte-for-byte and pass every contamination/gold/balance check; otherwise STOP_AUTHORING",
      "consume the one reserve at most once and rebuild the pre-contact freeze candidate"
    ],
    "reserve_consumption_limit": 1,
    "activation_allowed_only_before_provider_contact": true,
    "eligible_reasons": [
      "mechanical_schema_defect",
      "unresolved_gold_or_adjudication_defect",
      "contamination_or_fingerprint_failure",
      "duplicate_entity_date_or_number_tuple",
      "quota_or_signature_violation",
      "corpus_level_similarity_failure"
    ],
    "ineligible_reasons": [
      "style_preference",
      "anticipated_model_behavior",
      "observed_model_output",
      "gate_improvement"
    ],
    "required_match_dimensions": [
      "primary_family",
      "composed_quota_row",
      "secondary_features",
      "operation_ids",
      "conversion_ids",
      "source_schema_sequence",
      "output_schema_sequence",
      "operation_result_semantic_types",
      "numeric_promotion_classes",
      "comparison_operator",
      "comparison_operand_type_pair",
      "boundary_relation",
      "temporal_operation",
      "temporal_boundary_pattern",
      "explicit_absence",
      "entity_count",
      "entity_selector_role",
      "output_role_sequence",
      "consequence_risk",
      "field_count",
      "operation_node_count",
      "subtype_slot",
      "domain_classes",
      "operation_operand_semantic_types"
    ],
    "replacement_must_preserve_every_composed_quota_count": true,
    "post_activation_rechecks": [
      "family counts",
      "composed-feature counts",
      "risk counts",
      "output-schema-role balance",
      "all contamination comparisons",
      "gold and adjudication",
      "all candidate digests",
      "lexical pool uniqueness and exact subtype/schema/domain profile equality"
    ],
    "candidate_freeze_invalidated_on_activation": true,
    "full_review_and_digest_rebuild_required": true,
    "if_mapped_reserve_fails": "stop_authoring_campaign",
    "ad_hoc_replacement_allowed": false,
    "post_contact_replacement_allowed": false,
    "test_vectors": [
      {
        "id": "zero_claims",
        "defective_primary_ids": [],
        "profile_matches": [],
        "expected": "NO_ACTIVATION"
      },
      {
        "id": "one_matching_claim",
        "defective_primary_ids": [
          "A-R2-E3-01"
        ],
        "profile_matches": [
          "A-R2-E3-01"
        ],
        "expected": "ACTIVATE_SINGLE_RESERVE"
      },
      {
        "id": "one_nonmatching_claim",
        "defective_primary_ids": [
          "A-R2-E3-01"
        ],
        "profile_matches": [],
        "expected": "STOP_AUTHORING"
      },
      {
        "id": "uncovered_slot_2",
        "defective_primary_ids": [
          "A-R2-E3-02"
        ],
        "profile_matches": [
          "A-R2-E3-02"
        ],
        "expected": "STOP_AUTHORING"
      },
      {
        "id": "uncovered_slot_3",
        "defective_primary_ids": [
          "A-R2-E3-03"
        ],
        "profile_matches": [
          "A-R2-E3-03"
        ],
        "expected": "STOP_AUTHORING"
      },
      {
        "id": "uncovered_slot_4",
        "defective_primary_ids": [
          "A-R2-E3-04"
        ],
        "profile_matches": [
          "A-R2-E3-04"
        ],
        "expected": "STOP_AUTHORING"
      },
      {
        "id": "uncovered_slot_5",
        "defective_primary_ids": [
          "A-R2-E3-05"
        ],
        "profile_matches": [
          "A-R2-E3-05"
        ],
        "expected": "STOP_AUTHORING"
      },
      {
        "id": "two_claims",
        "defective_primary_ids": [
          "A-R2-E3-01",
          "A-R2-E3-03"
        ],
        "profile_matches": [
          "A-R2-E3-01",
          "A-R2-E3-03"
        ],
        "expected": "STOP_AUTHORING"
      }
    ],
    "replacement_rule": "byte-identical canonical reserve-equivalence profile",
    "covered_primary_slot": "the single family reserve is authored against within-family subtype slot 01; defects in slots 02..05 have no matching reserve and stop authoring; no choice is made after defect discovery",
    "reserve_coverage_limit": "28 prospective subtype01 backups only: 2 phases x 2 rounds x 7 families; not generic family reserves; 02..05 and multiple defects stop"
  },
  "comparison_modes": {
    "historical_new": "three-component historical-fingerprint-adapter.v1",
    "new_new": "six components, exact ledger classes within preregistered subtype template groups only"
  },
  "lexical_similarity_categories": {
    "included_in_similarity_payload": [
      "input.text source identifiers",
      "input.text entity labels",
      "input.text string/code/id values",
      "canonical schema field names",
      "canonical schema type/enum option bytes"
    ],
    "identity_atoms": "generated entity labels plus generated id_ string values; historical identifier field rule retained only for historical comparison",
    "not_identity_atoms": "generated f/d identifiers, record types, shared opaque enums, label_/code_ values",
    "lexical_neutrality_alone_creates_no_exemption": true,
    "record_type_reporting": "separate frozen allocation audit; family/phase association, not statistical independence",
    "excluded_from_similarity_payload": [
      "system text",
      "prompt SUBJECT",
      "record type (only in SUBJECT)",
      "operation instruction text",
      "historical common suffix",
      "INPUT marker"
    ],
    "inclusion_rule": "all input.text/canonical schema atoms included, not all model-facing atoms"
  },
  "whole_answer_reuse_limit": "exact full-object replay only, not semantic-content deduplication; fixture-specific names limit sensitivity; tuples/identities/Jaccard/structure/human review provide complementary content controls",
  "canonical_identity_atom_shape": "[kind,canonical_value] exactly two strings; kind ENTITY/IDENTIFIER; historical selector field removed",
  "template_recurrence_contract": {"contract_id":"g-extract1.template-recurrence.v1","positions":[{"position":"A:R2:E1-01:PRIMARY","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"A:R2:E1-02:PRIMARY","subtype_slot":"E1-02","fingerprint_class":"75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487"},{"position":"A:R2:E1-03:PRIMARY","subtype_slot":"E1-03","fingerprint_class":"1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa"},{"position":"A:R2:E1-04:PRIMARY","subtype_slot":"E1-04","fingerprint_class":"93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855"},{"position":"A:R2:E1-05:PRIMARY","subtype_slot":"E1-05","fingerprint_class":"a35d90134fc6e9e13db34b16e47cc1a055a4c176162bb9932c0e58261b3f99a6"},{"position":"A:R2:E1-01:RESERVE","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"A:R2:E2-01:PRIMARY","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"A:R2:E2-02:PRIMARY","subtype_slot":"E2-02","fingerprint_class":"8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786"},{"position":"A:R2:E2-03:PRIMARY","subtype_slot":"E2-03","fingerprint_class":"6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85"},{"position":"A:R2:E2-04:PRIMARY","subtype_slot":"E2-04","fingerprint_class":"93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b"},{"position":"A:R2:E2-05:PRIMARY","subtype_slot":"E2-05","fingerprint_class":"7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263"},{"position":"A:R2:E2-01:RESERVE","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"A:R2:E3-01:PRIMARY","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"A:R2:E3-02:PRIMARY","subtype_slot":"E3-02","fingerprint_class":"ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32"},{"position":"A:R2:E3-03:PRIMARY","subtype_slot":"E3-03","fingerprint_class":"af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609"},{"position":"A:R2:E3-04:PRIMARY","subtype_slot":"E3-04","fingerprint_class":"cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720"},{"position":"A:R2:E3-05:PRIMARY","subtype_slot":"E3-05","fingerprint_class":"666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120"},{"position":"A:R2:E3-01:RESERVE","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"A:R2:E4-01:PRIMARY","subtype_slot":"E4-01","fingerprint_class":"2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01"},{"position":"A:R2:E4-02:PRIMARY","subtype_slot":"E4-02","fingerprint_class":"064b91bf8e07079846aa5c56aae6d3ff6c30417529a97f23ef0c4b4c84f0e665"},{"position":"A:R2:E4-03:PRIMARY","subtype_slot":"E4-03","fingerprint_class":"e649ff77ea060b4cbcf5e53950bbbd53f4e070701f7de80b0b6e68c16a137407"},{"position":"A:R2:E4-04:PRIMARY","subtype_slot":"E4-04","fingerprint_class":"afce74b4555bcc3cdde3ff43c1ac6bea68b5c4d5eec1db1c2e96cb85083be575"},{"position":"A:R2:E4-05:PRIMARY","subtype_slot":"E4-05","fingerprint_class":"254a8fb612273c76c3c6d8754879867af2be71a71031e2e7e82ec1add8486977"},{"position":"A:R2:E4-01:RESERVE","subtype_slot":"E4-01","fingerprint_class":"2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01"},{"position":"A:R2:E5-01:PRIMARY","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"A:R2:E5-02:PRIMARY","subtype_slot":"E5-02","fingerprint_class":"fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2"},{"position":"A:R2:E5-03:PRIMARY","subtype_slot":"E5-03","fingerprint_class":"82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac"},{"position":"A:R2:E5-04:PRIMARY","subtype_slot":"E5-04","fingerprint_class":"cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4"},{"position":"A:R2:E5-05:PRIMARY","subtype_slot":"E5-05","fingerprint_class":"f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713"},{"position":"A:R2:E5-01:RESERVE","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"A:R2:E6-01:PRIMARY","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"A:R2:E6-02:PRIMARY","subtype_slot":"E6-02","fingerprint_class":"2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4"},{"position":"A:R2:E6-03:PRIMARY","subtype_slot":"E6-03","fingerprint_class":"4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4"},{"position":"A:R2:E6-04:PRIMARY","subtype_slot":"E6-04","fingerprint_class":"fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3"},{"position":"A:R2:E6-05:PRIMARY","subtype_slot":"E6-05","fingerprint_class":"972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc"},{"position":"A:R2:E6-01:RESERVE","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"A:R2:E7-01:PRIMARY","subtype_slot":"E7-01","fingerprint_class":"d1c3da9ae2cce46fc326a9d4be4e7526f19db93116d32340aa007ad2c2a97500"},{"position":"A:R2:E7-02:PRIMARY","subtype_slot":"E7-02","fingerprint_class":"92951b86ec0e62d3672c598698daf5812da4cef89eb4845ec5604c6ba8937d13"},{"position":"A:R2:E7-03:PRIMARY","subtype_slot":"E7-03","fingerprint_class":"a451fa9afeceb4e4e3b489496ef321d47e53a723d90061232ec2acd5e64485a8"},{"position":"A:R2:E7-04:PRIMARY","subtype_slot":"E7-04","fingerprint_class":"c86ca571f35c5236cb2dc4f6b7b243b9a0911117c4a23b2699c4159c3b7c3ecc"},{"position":"A:R2:E7-05:PRIMARY","subtype_slot":"E7-05","fingerprint_class":"021518e38e9f0e7f436e474350b590484b4029301e33d9ad721cb96f75bb5e14"},{"position":"A:R2:E7-01:RESERVE","subtype_slot":"E7-01","fingerprint_class":"4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c"},{"position":"A:R3:E1-01:PRIMARY","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"A:R3:E1-02:PRIMARY","subtype_slot":"E1-02","fingerprint_class":"75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487"},{"position":"A:R3:E1-03:PRIMARY","subtype_slot":"E1-03","fingerprint_class":"1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa"},{"position":"A:R3:E1-04:PRIMARY","subtype_slot":"E1-04","fingerprint_class":"93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855"},{"position":"A:R3:E1-05:PRIMARY","subtype_slot":"E1-05","fingerprint_class":"9c0819c95cf68abc8abf05b1d4dfc4a8fb7cf8c0e33939a07e6ed4968d33fd2f"},{"position":"A:R3:E1-01:RESERVE","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"A:R3:E2-01:PRIMARY","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"A:R3:E2-02:PRIMARY","subtype_slot":"E2-02","fingerprint_class":"8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786"},{"position":"A:R3:E2-03:PRIMARY","subtype_slot":"E2-03","fingerprint_class":"6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85"},{"position":"A:R3:E2-04:PRIMARY","subtype_slot":"E2-04","fingerprint_class":"93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b"},{"position":"A:R3:E2-05:PRIMARY","subtype_slot":"E2-05","fingerprint_class":"7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263"},{"position":"A:R3:E2-01:RESERVE","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"A:R3:E3-01:PRIMARY","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"A:R3:E3-02:PRIMARY","subtype_slot":"E3-02","fingerprint_class":"ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32"},{"position":"A:R3:E3-03:PRIMARY","subtype_slot":"E3-03","fingerprint_class":"af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609"},{"position":"A:R3:E3-04:PRIMARY","subtype_slot":"E3-04","fingerprint_class":"cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720"},{"position":"A:R3:E3-05:PRIMARY","subtype_slot":"E3-05","fingerprint_class":"666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120"},{"position":"A:R3:E3-01:RESERVE","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"A:R3:E4-01:PRIMARY","subtype_slot":"E4-01","fingerprint_class":"e7340f1603d953e3876c2491ef70a864fff432e964be80a8e8a89437d4801d0f"},{"position":"A:R3:E4-02:PRIMARY","subtype_slot":"E4-02","fingerprint_class":"ccd7cd8f9381601a28e8a7619c3c65031ea45e81c33aa4fd8e4950d6b6651d54"},{"position":"A:R3:E4-03:PRIMARY","subtype_slot":"E4-03","fingerprint_class":"b949370a25c7dc598394c653afe1c5584e78e93c6853742171cab3891565347a"},{"position":"A:R3:E4-04:PRIMARY","subtype_slot":"E4-04","fingerprint_class":"f3c43d017b0f954483fe0325b16c656f3d29c66beaa336e8228ff799165f79fa"},{"position":"A:R3:E4-05:PRIMARY","subtype_slot":"E4-05","fingerprint_class":"cafbe4748bed7bd4f077512900f7c7d46dd667fa2a3e1c4da144fd1c8ac51b61"},{"position":"A:R3:E4-01:RESERVE","subtype_slot":"E4-01","fingerprint_class":"e7340f1603d953e3876c2491ef70a864fff432e964be80a8e8a89437d4801d0f"},{"position":"A:R3:E5-01:PRIMARY","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"A:R3:E5-02:PRIMARY","subtype_slot":"E5-02","fingerprint_class":"fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2"},{"position":"A:R3:E5-03:PRIMARY","subtype_slot":"E5-03","fingerprint_class":"82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac"},{"position":"A:R3:E5-04:PRIMARY","subtype_slot":"E5-04","fingerprint_class":"cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4"},{"position":"A:R3:E5-05:PRIMARY","subtype_slot":"E5-05","fingerprint_class":"f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713"},{"position":"A:R3:E5-01:RESERVE","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"A:R3:E6-01:PRIMARY","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"A:R3:E6-02:PRIMARY","subtype_slot":"E6-02","fingerprint_class":"2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4"},{"position":"A:R3:E6-03:PRIMARY","subtype_slot":"E6-03","fingerprint_class":"4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4"},{"position":"A:R3:E6-04:PRIMARY","subtype_slot":"E6-04","fingerprint_class":"fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3"},{"position":"A:R3:E6-05:PRIMARY","subtype_slot":"E6-05","fingerprint_class":"972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc"},{"position":"A:R3:E6-01:RESERVE","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"A:R3:E7-01:PRIMARY","subtype_slot":"E7-01","fingerprint_class":"d1c3da9ae2cce46fc326a9d4be4e7526f19db93116d32340aa007ad2c2a97500"},{"position":"A:R3:E7-02:PRIMARY","subtype_slot":"E7-02","fingerprint_class":"92951b86ec0e62d3672c598698daf5812da4cef89eb4845ec5604c6ba8937d13"},{"position":"A:R3:E7-03:PRIMARY","subtype_slot":"E7-03","fingerprint_class":"a451fa9afeceb4e4e3b489496ef321d47e53a723d90061232ec2acd5e64485a8"},{"position":"A:R3:E7-04:PRIMARY","subtype_slot":"E7-04","fingerprint_class":"c86ca571f35c5236cb2dc4f6b7b243b9a0911117c4a23b2699c4159c3b7c3ecc"},{"position":"A:R3:E7-05:PRIMARY","subtype_slot":"E7-05","fingerprint_class":"021518e38e9f0e7f436e474350b590484b4029301e33d9ad721cb96f75bb5e14"},{"position":"A:R3:E7-01:RESERVE","subtype_slot":"E7-01","fingerprint_class":"4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c"},{"position":"B:R2:E1-01:PRIMARY","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"B:R2:E1-02:PRIMARY","subtype_slot":"E1-02","fingerprint_class":"75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487"},{"position":"B:R2:E1-03:PRIMARY","subtype_slot":"E1-03","fingerprint_class":"1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa"},{"position":"B:R2:E1-04:PRIMARY","subtype_slot":"E1-04","fingerprint_class":"93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855"},{"position":"B:R2:E1-05:PRIMARY","subtype_slot":"E1-05","fingerprint_class":"a35d90134fc6e9e13db34b16e47cc1a055a4c176162bb9932c0e58261b3f99a6"},{"position":"B:R2:E1-01:RESERVE","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"B:R2:E2-01:PRIMARY","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"B:R2:E2-02:PRIMARY","subtype_slot":"E2-02","fingerprint_class":"8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786"},{"position":"B:R2:E2-03:PRIMARY","subtype_slot":"E2-03","fingerprint_class":"6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85"},{"position":"B:R2:E2-04:PRIMARY","subtype_slot":"E2-04","fingerprint_class":"93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b"},{"position":"B:R2:E2-05:PRIMARY","subtype_slot":"E2-05","fingerprint_class":"7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263"},{"position":"B:R2:E2-01:RESERVE","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"B:R2:E3-01:PRIMARY","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"B:R2:E3-02:PRIMARY","subtype_slot":"E3-02","fingerprint_class":"ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32"},{"position":"B:R2:E3-03:PRIMARY","subtype_slot":"E3-03","fingerprint_class":"af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609"},{"position":"B:R2:E3-04:PRIMARY","subtype_slot":"E3-04","fingerprint_class":"cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720"},{"position":"B:R2:E3-05:PRIMARY","subtype_slot":"E3-05","fingerprint_class":"666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120"},{"position":"B:R2:E3-01:RESERVE","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"B:R2:E4-01:PRIMARY","subtype_slot":"E4-01","fingerprint_class":"bb3ed883802c943c394c3d632f19ad302dbfffc390a5369fe7463fb887759092"},{"position":"B:R2:E4-02:PRIMARY","subtype_slot":"E4-02","fingerprint_class":"3f7a230fefd71755eb01d5e2fe2fb1de85e7becfd55d36999e6de04714f8a197"},{"position":"B:R2:E4-03:PRIMARY","subtype_slot":"E4-03","fingerprint_class":"b949370a25c7dc598394c653afe1c5584e78e93c6853742171cab3891565347a"},{"position":"B:R2:E4-04:PRIMARY","subtype_slot":"E4-04","fingerprint_class":"f3c43d017b0f954483fe0325b16c656f3d29c66beaa336e8228ff799165f79fa"},{"position":"B:R2:E4-05:PRIMARY","subtype_slot":"E4-05","fingerprint_class":"cafbe4748bed7bd4f077512900f7c7d46dd667fa2a3e1c4da144fd1c8ac51b61"},{"position":"B:R2:E4-01:RESERVE","subtype_slot":"E4-01","fingerprint_class":"bb3ed883802c943c394c3d632f19ad302dbfffc390a5369fe7463fb887759092"},{"position":"B:R2:E5-01:PRIMARY","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"B:R2:E5-02:PRIMARY","subtype_slot":"E5-02","fingerprint_class":"fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2"},{"position":"B:R2:E5-03:PRIMARY","subtype_slot":"E5-03","fingerprint_class":"82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac"},{"position":"B:R2:E5-04:PRIMARY","subtype_slot":"E5-04","fingerprint_class":"cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4"},{"position":"B:R2:E5-05:PRIMARY","subtype_slot":"E5-05","fingerprint_class":"f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713"},{"position":"B:R2:E5-01:RESERVE","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"B:R2:E6-01:PRIMARY","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"B:R2:E6-02:PRIMARY","subtype_slot":"E6-02","fingerprint_class":"2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4"},{"position":"B:R2:E6-03:PRIMARY","subtype_slot":"E6-03","fingerprint_class":"4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4"},{"position":"B:R2:E6-04:PRIMARY","subtype_slot":"E6-04","fingerprint_class":"fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3"},{"position":"B:R2:E6-05:PRIMARY","subtype_slot":"E6-05","fingerprint_class":"972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc"},{"position":"B:R2:E6-01:RESERVE","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"B:R2:E7-01:PRIMARY","subtype_slot":"E7-01","fingerprint_class":"49cd0870fecec6b46f8b8d81600ad01b33a0724a26798c5be7ac801da753cd2e"},{"position":"B:R2:E7-02:PRIMARY","subtype_slot":"E7-02","fingerprint_class":"f908d84920aee765909fc9f4e0d7d38bffd79cf277bdc089a9e6cd18aa2efddf"},{"position":"B:R2:E7-03:PRIMARY","subtype_slot":"E7-03","fingerprint_class":"99152903617fe43e06098271430c30980599cd84a3d893352f911d68abb7c96d"},{"position":"B:R2:E7-04:PRIMARY","subtype_slot":"E7-04","fingerprint_class":"3b04f8ce70e40aa7200683fc3fd81f17ee7301d42709dc421e453cded7f23ad6"},{"position":"B:R2:E7-05:PRIMARY","subtype_slot":"E7-05","fingerprint_class":"41242a78258cbd9f3b750beb17f6bd646138ce704c3f2d99f4d9c89a92367838"},{"position":"B:R2:E7-01:RESERVE","subtype_slot":"E7-01","fingerprint_class":"4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c"},{"position":"B:R3:E1-01:PRIMARY","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"B:R3:E1-02:PRIMARY","subtype_slot":"E1-02","fingerprint_class":"75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487"},{"position":"B:R3:E1-03:PRIMARY","subtype_slot":"E1-03","fingerprint_class":"1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa"},{"position":"B:R3:E1-04:PRIMARY","subtype_slot":"E1-04","fingerprint_class":"93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855"},{"position":"B:R3:E1-05:PRIMARY","subtype_slot":"E1-05","fingerprint_class":"9c0819c95cf68abc8abf05b1d4dfc4a8fb7cf8c0e33939a07e6ed4968d33fd2f"},{"position":"B:R3:E1-01:RESERVE","subtype_slot":"E1-01","fingerprint_class":"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"},{"position":"B:R3:E2-01:PRIMARY","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"B:R3:E2-02:PRIMARY","subtype_slot":"E2-02","fingerprint_class":"8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786"},{"position":"B:R3:E2-03:PRIMARY","subtype_slot":"E2-03","fingerprint_class":"6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85"},{"position":"B:R3:E2-04:PRIMARY","subtype_slot":"E2-04","fingerprint_class":"93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b"},{"position":"B:R3:E2-05:PRIMARY","subtype_slot":"E2-05","fingerprint_class":"7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263"},{"position":"B:R3:E2-01:RESERVE","subtype_slot":"E2-01","fingerprint_class":"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"},{"position":"B:R3:E3-01:PRIMARY","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"B:R3:E3-02:PRIMARY","subtype_slot":"E3-02","fingerprint_class":"ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32"},{"position":"B:R3:E3-03:PRIMARY","subtype_slot":"E3-03","fingerprint_class":"af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609"},{"position":"B:R3:E3-04:PRIMARY","subtype_slot":"E3-04","fingerprint_class":"cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720"},{"position":"B:R3:E3-05:PRIMARY","subtype_slot":"E3-05","fingerprint_class":"666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120"},{"position":"B:R3:E3-01:RESERVE","subtype_slot":"E3-01","fingerprint_class":"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"},{"position":"B:R3:E4-01:PRIMARY","subtype_slot":"E4-01","fingerprint_class":"2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01"},{"position":"B:R3:E4-02:PRIMARY","subtype_slot":"E4-02","fingerprint_class":"ccd7cd8f9381601a28e8a7619c3c65031ea45e81c33aa4fd8e4950d6b6651d54"},{"position":"B:R3:E4-03:PRIMARY","subtype_slot":"E4-03","fingerprint_class":"af1e5a60dc1f50aa4ee34b5b4ca540a0b3916aecfe6712c4359f9dd4b7199f5f"},{"position":"B:R3:E4-04:PRIMARY","subtype_slot":"E4-04","fingerprint_class":"afce74b4555bcc3cdde3ff43c1ac6bea68b5c4d5eec1db1c2e96cb85083be575"},{"position":"B:R3:E4-05:PRIMARY","subtype_slot":"E4-05","fingerprint_class":"5b31ae478f2cee3e1759d2e33cb83f9dd645216bd705248feedef0137202cb0c"},{"position":"B:R3:E4-01:RESERVE","subtype_slot":"E4-01","fingerprint_class":"2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01"},{"position":"B:R3:E5-01:PRIMARY","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"B:R3:E5-02:PRIMARY","subtype_slot":"E5-02","fingerprint_class":"fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2"},{"position":"B:R3:E5-03:PRIMARY","subtype_slot":"E5-03","fingerprint_class":"82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac"},{"position":"B:R3:E5-04:PRIMARY","subtype_slot":"E5-04","fingerprint_class":"cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4"},{"position":"B:R3:E5-05:PRIMARY","subtype_slot":"E5-05","fingerprint_class":"f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713"},{"position":"B:R3:E5-01:RESERVE","subtype_slot":"E5-01","fingerprint_class":"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"},{"position":"B:R3:E6-01:PRIMARY","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"B:R3:E6-02:PRIMARY","subtype_slot":"E6-02","fingerprint_class":"2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4"},{"position":"B:R3:E6-03:PRIMARY","subtype_slot":"E6-03","fingerprint_class":"4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4"},{"position":"B:R3:E6-04:PRIMARY","subtype_slot":"E6-04","fingerprint_class":"fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3"},{"position":"B:R3:E6-05:PRIMARY","subtype_slot":"E6-05","fingerprint_class":"972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc"},{"position":"B:R3:E6-01:RESERVE","subtype_slot":"E6-01","fingerprint_class":"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"},{"position":"B:R3:E7-01:PRIMARY","subtype_slot":"E7-01","fingerprint_class":"49cd0870fecec6b46f8b8d81600ad01b33a0724a26798c5be7ac801da753cd2e"},{"position":"B:R3:E7-02:PRIMARY","subtype_slot":"E7-02","fingerprint_class":"f908d84920aee765909fc9f4e0d7d38bffd79cf277bdc089a9e6cd18aa2efddf"},{"position":"B:R3:E7-03:PRIMARY","subtype_slot":"E7-03","fingerprint_class":"99152903617fe43e06098271430c30980599cd84a3d893352f911d68abb7c96d"},{"position":"B:R3:E7-04:PRIMARY","subtype_slot":"E7-04","fingerprint_class":"3b04f8ce70e40aa7200683fc3fd81f17ee7301d42709dc421e453cded7f23ad6"},{"position":"B:R3:E7-05:PRIMARY","subtype_slot":"E7-05","fingerprint_class":"41242a78258cbd9f3b750beb17f6bd646138ce704c3f2d99f4d9c89a92367838"},{"position":"B:R3:E7-01:RESERVE","subtype_slot":"E7-01","fingerprint_class":"4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c"}],"fingerprint_classes":{"3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c":{"slot":"E1-01","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","DATE_WITHIN_MONTH",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E1-01:PRIMARY","A:R2:E1-01:RESERVE","A:R3:E1-01:PRIMARY","A:R3:E1-01:RESERVE","B:R2:E1-01:PRIMARY","B:R2:E1-01:RESERVE","B:R3:E1-01:PRIMARY","B:R3:E1-01:RESERVE"],"maximum_recurrence_count":8},"75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487":{"slot":"E1-02","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","MONTH_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E1-02:PRIMARY","A:R3:E1-02:PRIMARY","B:R2:E1-02:PRIMARY","B:R3:E1-02:PRIMARY"],"maximum_recurrence_count":4},"1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa":{"slot":"E1-03","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","YEAR_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E1-03:PRIMARY","A:R3:E1-03:PRIMARY","B:R2:E1-03:PRIMARY","B:R3:E1-03:PRIMARY"],"maximum_recurrence_count":4},"93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855":{"slot":"E1-04","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","LEAP_DAY_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E1-04:PRIMARY","A:R3:E1-04:PRIMARY","B:R2:E1-04:PRIMARY","B:R3:E1-04:PRIMARY"],"maximum_recurrence_count":4},"a35d90134fc6e9e13db34b16e47cc1a055a4c176162bb9932c0e58261b3f99a6":{"slot":"E1-05","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","source_field"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","DATE_WITHIN_MONTH",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1],["SUPPORT","integer",-1]]]],"members":["A:R2:E1-05:PRIMARY","B:R2:E1-05:PRIMARY"],"maximum_recurrence_count":2},"99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2":{"slot":"E2-01","fingerprint":[[["CLOCK_MINUTE_OFFSET",["source_field","literal"],[]]],[["HH:MM","derived_time"]],"NONE","NONE","SAME_DAY_FORWARD",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E2-01:PRIMARY","A:R2:E2-01:RESERVE","A:R3:E2-01:PRIMARY","A:R3:E2-01:RESERVE","B:R2:E2-01:PRIMARY","B:R2:E2-01:RESERVE","B:R3:E2-01:PRIMARY","B:R3:E2-01:RESERVE"],"maximum_recurrence_count":8},"8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786":{"slot":"E2-02","fingerprint":[[["CLOCK_MINUTE_OFFSET",["source_field","literal"],[]]],[["HH:MM","derived_time"]],"NONE","NONE","MIDNIGHT_ROLLOVER",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E2-02:PRIMARY","A:R3:E2-02:PRIMARY","B:R2:E2-02:PRIMARY","B:R3:E2-02:PRIMARY"],"maximum_recurrence_count":4},"6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85":{"slot":"E2-03","fingerprint":[[["ELAPSED_MINUTES",["source_field","source_field"],[]]],[["integer","derived_number"]],"NONE","NONE","SAME_DAY_FORWARD",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1],["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E2-03:PRIMARY","A:R3:E2-03:PRIMARY","B:R2:E2-03:PRIMARY","B:R3:E2-03:PRIMARY"],"maximum_recurrence_count":4},"93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b":{"slot":"E2-04","fingerprint":[[["ELAPSED_MINUTES",["source_field","source_field"],[]]],[["integer","derived_number"]],"NONE","NONE","MIDNIGHT_ROLLOVER",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1],["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E2-04:PRIMARY","A:R3:E2-04:PRIMARY","B:R2:E2-04:PRIMARY","B:R3:E2-04:PRIMARY"],"maximum_recurrence_count":4},"7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263":{"slot":"E2-05","fingerprint":[[["ELAPSED_MINUTES",["source_field","literal"],[]]],[["integer","derived_number"]],"NONE","NONE","SAME_DAY_FORWARD",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E2-05:PRIMARY","A:R3:E2-05:PRIMARY","B:R2:E2-05:PRIMARY","B:R3:E2-05:PRIMARY"],"maximum_recurrence_count":4},"c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd":{"slot":"E3-01","fingerprint":[[["ADD",["source_field","source_field"],[]]],[["integer","derived_number"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","integer",-1]]]],"members":["A:R2:E3-01:PRIMARY","A:R2:E3-01:RESERVE","A:R3:E3-01:PRIMARY","A:R3:E3-01:RESERVE","B:R2:E3-01:PRIMARY","B:R2:E3-01:RESERVE","B:R3:E3-01:PRIMARY","B:R3:E3-01:RESERVE"],"maximum_recurrence_count":8},"ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32":{"slot":"E3-02","fingerprint":[[["SUBTRACT",["source_field","source_field"],[]]],[["number","derived_number"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","number",-1]]]],"members":["A:R2:E3-02:PRIMARY","A:R3:E3-02:PRIMARY","B:R2:E3-02:PRIMARY","B:R3:E3-02:PRIMARY"],"maximum_recurrence_count":4},"af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609":{"slot":"E3-03","fingerprint":[[["SUM",["source_field","source_field","source_field"],[]]],[["number","derived_number"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","number",-1],["SUPPORT","number",-1],["SUPPORT","number",-1]]]],"members":["A:R2:E3-03:PRIMARY","A:R3:E3-03:PRIMARY","B:R2:E3-03:PRIMARY","B:R3:E3-03:PRIMARY"],"maximum_recurrence_count":4},"cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720":{"slot":"E3-04","fingerprint":[[["DIVIDE",["source_field","source_field"],[]],["EXACT_COPY",["derived_field"],[0]]],[["number","derived_number"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","integer",-1]]]],"members":["A:R2:E3-04:PRIMARY","A:R3:E3-04:PRIMARY","B:R2:E3-04:PRIMARY","B:R3:E3-04:PRIMARY"],"maximum_recurrence_count":4},"666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120":{"slot":"E3-05","fingerprint":[[["UNIT_CONVERSION",["source_field"],[]],["EXACT_COPY",["derived_field"],[0]]],[["number","derived_number"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","number",-1]]]],"members":["A:R2:E3-05:PRIMARY","A:R3:E3-05:PRIMARY","B:R2:E3-05:PRIMARY","B:R3:E3-05:PRIMARY"],"maximum_recurrence_count":4},"2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01":{"slot":"E4-01","fingerprint":[[["ADD",["source_field","source_field"],[]],["GT",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","ABOVE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","integer",-1]]]],"members":["A:R2:E4-01:PRIMARY","A:R2:E4-01:RESERVE","B:R3:E4-01:PRIMARY","B:R3:E4-01:RESERVE"],"maximum_recurrence_count":4},"064b91bf8e07079846aa5c56aae6d3ff6c30417529a97f23ef0c4b4c84f0e665":{"slot":"E4-02","fingerprint":[[["SUBTRACT",["source_field","source_field"],[]],["LTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","ABOVE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","number",-1]]]],"members":["A:R2:E4-02:PRIMARY"],"maximum_recurrence_count":1},"e649ff77ea060b4cbcf5e53950bbbd53f4e070701f7de80b0b6e68c16a137407":{"slot":"E4-03","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]],["GTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","EQUAL","MONTH_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E4-03:PRIMARY"],"maximum_recurrence_count":1},"afce74b4555bcc3cdde3ff43c1ac6bea68b5c4d5eec1db1c2e96cb85083be575":{"slot":"E4-04","fingerprint":[[["CLOCK_MINUTE_OFFSET",["source_field","literal"],[]],["LT",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","BELOW","MIDNIGHT_ROLLOVER",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E4-04:PRIMARY","B:R3:E4-04:PRIMARY"],"maximum_recurrence_count":2},"254a8fb612273c76c3c6d8754879867af2be71a71031e2e7e82ec1add8486977":{"slot":"E4-05","fingerprint":[[["EQ",["source_field","source_field"],[]]],[["boolean","derived_boolean"]],"NONE","BELOW","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","number",-1],["SUPPORT","number",-1]]]],"members":["A:R2:E4-05:PRIMARY"],"maximum_recurrence_count":1},"ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383":{"slot":"E5-01","fingerprint":[[["ENTITY_FIELD_BIND",["source_field","source_field","entity_selector"],[]]],[["number","entity_bound_value"]],"MULTI_ENTITY_SELECT_BY_IDENTIFIER","NONE","NONE",["INTERLEAVED_MULTI_ENTITY",[["SUPPORT","string",0],["SUPPORT","string",1],["TARGET","number",0],["TARGET","number",1]]]],"members":["A:R2:E5-01:PRIMARY","A:R2:E5-01:RESERVE","A:R3:E5-01:PRIMARY","A:R3:E5-01:RESERVE","B:R2:E5-01:PRIMARY","B:R2:E5-01:RESERVE","B:R3:E5-01:PRIMARY","B:R3:E5-01:RESERVE"],"maximum_recurrence_count":8},"fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2":{"slot":"E5-02","fingerprint":[[["ENTITY_FIELD_BIND",["source_field","source_field","entity_selector"],[]]],[["string","entity_bound_value"]],"MULTI_ENTITY_SELECT_BY_ATTRIBUTE","NONE","NONE",["INTERLEAVED_MULTI_ENTITY",[["SUPPORT","string",0],["SUPPORT","string",1],["TARGET","string",0],["TARGET","string",1]]]],"members":["A:R2:E5-02:PRIMARY","A:R3:E5-02:PRIMARY","B:R2:E5-02:PRIMARY","B:R3:E5-02:PRIMARY"],"maximum_recurrence_count":4},"82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac":{"slot":"E5-03","fingerprint":[[["ENTITY_FIELD_BIND",["source_field","source_field","entity_selector"],[]]],[["option_a|option_b|option_c","entity_bound_value"]],"MULTI_ENTITY_SELECT_BY_EVENT_ROLE","NONE","NONE",["INTERLEAVED_MULTI_ENTITY",[["SUPPORT","string",0],["SUPPORT","string",1],["SUPPORT","string",2],["TARGET","option_a|option_b|option_c",0],["TARGET","option_a|option_b|option_c",1],["TARGET","option_a|option_b|option_c",2]]]],"members":["A:R2:E5-03:PRIMARY","A:R3:E5-03:PRIMARY","B:R2:E5-03:PRIMARY","B:R3:E5-03:PRIMARY"],"maximum_recurrence_count":4},"cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4":{"slot":"E5-04","fingerprint":[[["ENTITY_FIELD_BIND",["source_field","source_field","entity_selector"],[]]],[["YYYY-MM-DD","entity_bound_value"]],"MULTI_ENTITY_SELECT_BY_IDENTIFIER","NONE","NONE",["INTERLEAVED_MULTI_ENTITY",[["SUPPORT","string",0],["SUPPORT","string",1],["TARGET","YYYY-MM-DD",0],["TARGET","YYYY-MM-DD",1]]]],"members":["A:R2:E5-04:PRIMARY","A:R3:E5-04:PRIMARY","B:R2:E5-04:PRIMARY","B:R3:E5-04:PRIMARY"],"maximum_recurrence_count":4},"f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713":{"slot":"E5-05","fingerprint":[[["ENTITY_FIELD_BIND",["source_field","source_field","entity_selector"],[]]],[["HH:MM","entity_bound_value"]],"MULTI_ENTITY_SELECT_BY_ATTRIBUTE","NONE","NONE",["INTERLEAVED_MULTI_ENTITY",[["SUPPORT","string",0],["SUPPORT","string",1],["SUPPORT","string",2],["TARGET","HH:MM",0],["TARGET","HH:MM",1],["TARGET","HH:MM",2]]]],"members":["A:R2:E5-05:PRIMARY","A:R3:E5-05:PRIMARY","B:R2:E5-05:PRIMARY","B:R3:E5-05:PRIMARY"],"maximum_recurrence_count":4},"0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef":{"slot":"E6-01","fingerprint":[[["EXACT_COPY",["source_field"],[]]],[["integer","source_copy"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["TARGET","integer",-1]]]],"members":["A:R2:E6-01:PRIMARY","A:R2:E6-01:RESERVE","A:R3:E6-01:PRIMARY","A:R3:E6-01:RESERVE","B:R2:E6-01:PRIMARY","B:R2:E6-01:RESERVE","B:R3:E6-01:PRIMARY","B:R3:E6-01:RESERVE"],"maximum_recurrence_count":8},"2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4":{"slot":"E6-02","fingerprint":[[["EXACT_COPY",["source_field"],[]]],[["number","source_copy"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["TARGET","number",-1]]]],"members":["A:R2:E6-02:PRIMARY","A:R3:E6-02:PRIMARY","B:R2:E6-02:PRIMARY","B:R3:E6-02:PRIMARY"],"maximum_recurrence_count":4},"4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4":{"slot":"E6-03","fingerprint":[[["EXACT_COPY",["source_field"],[]]],[["string","source_copy"]],"NONE","NONE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["TARGET","string",-1]]]],"members":["A:R2:E6-03:PRIMARY","A:R3:E6-03:PRIMARY","B:R2:E6-03:PRIMARY","B:R3:E6-03:PRIMARY"],"maximum_recurrence_count":4},"fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3":{"slot":"E6-04","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]],["EXACT_COPY",["derived_field"],[0]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","YEAR_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R2:E6-04:PRIMARY","A:R3:E6-04:PRIMARY","B:R2:E6-04:PRIMARY","B:R3:E6-04:PRIMARY"],"maximum_recurrence_count":4},"972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc":{"slot":"E6-05","fingerprint":[[["CLOCK_MINUTE_OFFSET",["source_field","literal"],[]],["EXACT_COPY",["derived_field"],[0]]],[["HH:MM","derived_time"]],"NONE","NONE","MIDNIGHT_ROLLOVER",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R2:E6-05:PRIMARY","A:R3:E6-05:PRIMARY","B:R2:E6-05:PRIMARY","B:R3:E6-05:PRIMARY"],"maximum_recurrence_count":4},"d1c3da9ae2cce46fc326a9d4be4e7526f19db93116d32340aa007ad2c2a97500":{"slot":"E7-01","fingerprint":[[],[["integer","source_copy"],["integer","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","integer",-1],["TARGET","integer",-1]]]],"members":["A:R2:E7-01:PRIMARY","A:R3:E7-01:PRIMARY"],"maximum_recurrence_count":2},"92951b86ec0e62d3672c598698daf5812da4cef89eb4845ec5604c6ba8937d13":{"slot":"E7-02","fingerprint":[[],[["number","source_copy"],["provided|not_provided","absence_sentinel"],["string","source_copy"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","number",-1],["TARGET","string",-1]]]],"members":["A:R2:E7-02:PRIMARY","A:R3:E7-02:PRIMARY"],"maximum_recurrence_count":2},"a451fa9afeceb4e4e3b489496ef321d47e53a723d90061232ec2acd5e64485a8":{"slot":"E7-03","fingerprint":[[],[["HH:MM","source_copy"],["YYYY-MM-DD","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","YYYY-MM-DD",-1],["TARGET","HH:MM",-1]]]],"members":["A:R2:E7-03:PRIMARY","A:R3:E7-03:PRIMARY"],"maximum_recurrence_count":2},"c86ca571f35c5236cb2dc4f6b7b243b9a0911117c4a23b2699c4159c3b7c3ecc":{"slot":"E7-04","fingerprint":[[],[["option_a|option_b","source_copy"],["provided|not_provided","absence_sentinel"],["string","source_copy"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","option_a|option_b",-1],["TARGET","string",-1]]]],"members":["A:R2:E7-04:PRIMARY","A:R3:E7-04:PRIMARY"],"maximum_recurrence_count":2},"021518e38e9f0e7f436e474350b590484b4029301e33d9ad721cb96f75bb5e14":{"slot":"E7-05","fingerprint":[[],[["boolean","source_copy"],["integer","source_copy"],["number","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","boolean",-1],["TARGET","number",-1],["TARGET","integer",-1]]]],"members":["A:R2:E7-05:PRIMARY","A:R3:E7-05:PRIMARY"],"maximum_recurrence_count":2},"4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c":{"slot":"E7-01","fingerprint":[[],[["integer","source_copy"],["integer","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","integer",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1],["TARGET","integer",-1]]]],"members":["A:R2:E7-01:RESERVE","A:R3:E7-01:RESERVE","B:R2:E7-01:RESERVE","B:R3:E7-01:RESERVE"],"maximum_recurrence_count":4},"9c0819c95cf68abc8abf05b1d4dfc4a8fb7cf8c0e33939a07e6ed4968d33fd2f":{"slot":"E1-05","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","source_field"],[]]],[["YYYY-MM-DD","derived_date"]],"NONE","NONE","YEAR_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1],["SUPPORT","integer",-1]]]],"members":["A:R3:E1-05:PRIMARY","B:R3:E1-05:PRIMARY"],"maximum_recurrence_count":2},"e7340f1603d953e3876c2491ef70a864fff432e964be80a8e8a89437d4801d0f":{"slot":"E4-01","fingerprint":[[["ADD",["source_field","source_field"],[]],["GT",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","BELOW","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","integer",-1]]]],"members":["A:R3:E4-01:PRIMARY","A:R3:E4-01:RESERVE"],"maximum_recurrence_count":2},"ccd7cd8f9381601a28e8a7619c3c65031ea45e81c33aa4fd8e4950d6b6651d54":{"slot":"E4-02","fingerprint":[[["SUBTRACT",["source_field","source_field"],[]],["LTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","EQUAL","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","number",-1]]]],"members":["A:R3:E4-02:PRIMARY","B:R3:E4-02:PRIMARY"],"maximum_recurrence_count":2},"b949370a25c7dc598394c653afe1c5584e78e93c6853742171cab3891565347a":{"slot":"E4-03","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]],["GTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","ABOVE","MONTH_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["A:R3:E4-03:PRIMARY","B:R2:E4-03:PRIMARY"],"maximum_recurrence_count":2},"f3c43d017b0f954483fe0325b16c656f3d29c66beaa336e8228ff799165f79fa":{"slot":"E4-04","fingerprint":[[["CLOCK_MINUTE_OFFSET",["source_field","literal"],[]],["LT",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","ABOVE","MIDNIGHT_ROLLOVER",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","HH:MM",-1]]]],"members":["A:R3:E4-04:PRIMARY","B:R2:E4-04:PRIMARY"],"maximum_recurrence_count":2},"cafbe4748bed7bd4f077512900f7c7d46dd667fa2a3e1c4da144fd1c8ac51b61":{"slot":"E4-05","fingerprint":[[["EQ",["source_field","source_field"],[]]],[["boolean","derived_boolean"]],"NONE","EQUAL","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","number",-1],["SUPPORT","number",-1]]]],"members":["A:R3:E4-05:PRIMARY","B:R2:E4-05:PRIMARY"],"maximum_recurrence_count":2},"bb3ed883802c943c394c3d632f19ad302dbfffc390a5369fe7463fb887759092":{"slot":"E4-01","fingerprint":[[["ADD",["source_field","source_field"],[]],["GT",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","EQUAL","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","integer",-1]]]],"members":["B:R2:E4-01:PRIMARY","B:R2:E4-01:RESERVE"],"maximum_recurrence_count":2},"3f7a230fefd71755eb01d5e2fe2fb1de85e7becfd55d36999e6de04714f8a197":{"slot":"E4-02","fingerprint":[[["SUBTRACT",["source_field","source_field"],[]],["LTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","BELOW","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","integer",-1],["SUPPORT","number",-1]]]],"members":["B:R2:E4-02:PRIMARY"],"maximum_recurrence_count":1},"49cd0870fecec6b46f8b8d81600ad01b33a0724a26798c5be7ac801da753cd2e":{"slot":"E7-01","fingerprint":[[],[["integer","source_copy"],["integer","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","integer",-1],["TARGET","integer",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1]]]],"members":["B:R2:E7-01:PRIMARY","B:R3:E7-01:PRIMARY"],"maximum_recurrence_count":2},"f908d84920aee765909fc9f4e0d7d38bffd79cf277bdc089a9e6cd18aa2efddf":{"slot":"E7-02","fingerprint":[[],[["number","source_copy"],["provided|not_provided","absence_sentinel"],["string","source_copy"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","number",-1],["TARGET","string",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1]]]],"members":["B:R2:E7-02:PRIMARY","B:R3:E7-02:PRIMARY"],"maximum_recurrence_count":2},"99152903617fe43e06098271430c30980599cd84a3d893352f911d68abb7c96d":{"slot":"E7-03","fingerprint":[[],[["HH:MM","source_copy"],["YYYY-MM-DD","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","YYYY-MM-DD",-1],["TARGET","HH:MM",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1]]]],"members":["B:R2:E7-03:PRIMARY","B:R3:E7-03:PRIMARY"],"maximum_recurrence_count":2},"3b04f8ce70e40aa7200683fc3fd81f17ee7301d42709dc421e453cded7f23ad6":{"slot":"E7-04","fingerprint":[[],[["option_a|option_b","source_copy"],["provided|not_provided","absence_sentinel"],["string","source_copy"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","option_a|option_b",-1],["TARGET","string",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1]]]],"members":["B:R2:E7-04:PRIMARY","B:R3:E7-04:PRIMARY"],"maximum_recurrence_count":2},"41242a78258cbd9f3b750beb17f6bd646138ce704c3f2d99f4d9c89a92367838":{"slot":"E7-05","fingerprint":[[],[["boolean","source_copy"],["integer","source_copy"],["number","source_copy"],["provided|not_provided","absence_sentinel"]],"NONE","NONE","NONE",["EXPLICIT_PARTIAL_ABSENCE",[["TARGET","boolean",-1],["TARGET","number",-1],["TARGET","integer",-1],["EXPLICIT_ABSENCE","provided|not_provided",-1]]]],"members":["B:R2:E7-05:PRIMARY","B:R3:E7-05:PRIMARY"],"maximum_recurrence_count":2},"af1e5a60dc1f50aa4ee34b5b4ca540a0b3916aecfe6712c4359f9dd4b7199f5f":{"slot":"E4-03","fingerprint":[[["CALENDAR_DAY_OFFSET",["source_field","literal"],[]],["GTE",["derived_field","literal"],[0]]],[["boolean","derived_boolean"]],"NONE","BELOW","MONTH_BOUNDARY",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","YYYY-MM-DD",-1]]]],"members":["B:R3:E4-03:PRIMARY"],"maximum_recurrence_count":1},"5b31ae478f2cee3e1759d2e33cb83f9dd645216bd705248feedef0137202cb0c":{"slot":"E4-05","fingerprint":[[["EQ",["source_field","source_field"],[]]],[["boolean","derived_boolean"]],"NONE","ABOVE","NONE",["CONTIGUOUS_SINGLE_ENTITY",[["SUPPORT","number",-1],["SUPPORT","number",-1]]]],"members":["B:R3:E4-05:PRIMARY"],"maximum_recurrence_count":1}},"structural_wiring":{"numeric":"distinct source-field references for each first-node operand, exact frozen operand schema sequence","calendar":"source DATE and literal INTEGER offset, except E1-05 offset is second source INTEGER","clock":"source TIME and literal INTEGER offset","elapsed":"start/end source TIME facts except E2-05 end is equal TIME literal","comparison":"composed upstream left, same-type literal right; E4-05 two source NUMBER operands","copy":"E6-01..03 exactly one source fact; downstream EXACT_COPY consumes upstream target","entity":"all selectors in letter order, then all bound-source facts in letter order; no extras","e7":"frozen support-schema order and A/B/reserve absence position","fact_order":"first distinct source reference in catalog operand order then SUM list order; derived nodes introduce no extra source facts except direct E4-05; names first source appearance","distractors":0,"slot_separation":"E1-05 offset-as-source and E2-05 literal-end prevent unrelated subtype collisions without fingerprint IDs or values"},"ledger_algorithm":"derive six typed components from frozen wiring/schema/subtype boundary/presentation, compact JSON ensure_ascii=true separators comma/colon UTF-8 no newline; SHA256 class key","class_rule":"actual fingerprint equals exact planned class; same-subtype group includes only enumerated context/status members; class and group maxima exact","scope_table":{"A:R2_vs_A:R3":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","B:R2_vs_B:R3":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","same_round_different_phase":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","different_round_different_phase":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","scored_vs_reserve":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","reserve_vs_reserve":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","mapped_reserve_vs_primary":"PERMITTED_ONLY_AS_DECLARED_TEMPLATE_RECURRENCE","reserve_vs_unrelated_family_or_subtype":"PROHIBITED","same_context_different_subtype":"PROHIBITED"},"freshness_rule":"every NEW/NEW pair raw typed VALUE sequence must differ; generated strings remain raw; exact answer/identity/eligible date-number reuse forbidden","freshness_sequence":"source-record order [schema_type,canonical schema semantic value] including VALUE only; no field names/fixture IDs; preserve duplicates and numeric equivalence","maximum_objects":168,"replacement_eligibility_independent":true,"structural_feasibility_claim":"all168 value-free planned positions have legal declared classes, not proof future content passes contamination or gold audit","subtype_template_groups":{"E1-01":{"members":["A:R2:E1-01:PRIMARY","A:R2:E1-01:RESERVE","A:R3:E1-01:PRIMARY","A:R3:E1-01:RESERVE","B:R2:E1-01:PRIMARY","B:R2:E1-01:RESERVE","B:R3:E1-01:PRIMARY","B:R3:E1-01:RESERVE"],"fingerprint_classes":["3b62f3ae6732d62d8392137dd234275c5e9094b65c963cf96659cc0f2d75ec7c"],"maximum_members":8},"E1-02":{"members":["A:R2:E1-02:PRIMARY","A:R3:E1-02:PRIMARY","B:R2:E1-02:PRIMARY","B:R3:E1-02:PRIMARY"],"fingerprint_classes":["75174600897e0672a47a33576b9dbaf80d92fa71bf571c5866ad940800fbd487"],"maximum_members":4},"E1-03":{"members":["A:R2:E1-03:PRIMARY","A:R3:E1-03:PRIMARY","B:R2:E1-03:PRIMARY","B:R3:E1-03:PRIMARY"],"fingerprint_classes":["1e810133ae221b1862bb77221d2cba52998a015fa93a30ba40e8516231a6dafa"],"maximum_members":4},"E1-04":{"members":["A:R2:E1-04:PRIMARY","A:R3:E1-04:PRIMARY","B:R2:E1-04:PRIMARY","B:R3:E1-04:PRIMARY"],"fingerprint_classes":["93089d847bb65258a38fbf2898e36ef16b83c7bc2ea78df5f86260f531820855"],"maximum_members":4},"E1-05":{"members":["A:R2:E1-05:PRIMARY","A:R3:E1-05:PRIMARY","B:R2:E1-05:PRIMARY","B:R3:E1-05:PRIMARY"],"fingerprint_classes":["9c0819c95cf68abc8abf05b1d4dfc4a8fb7cf8c0e33939a07e6ed4968d33fd2f","a35d90134fc6e9e13db34b16e47cc1a055a4c176162bb9932c0e58261b3f99a6"],"maximum_members":4},"E2-01":{"members":["A:R2:E2-01:PRIMARY","A:R2:E2-01:RESERVE","A:R3:E2-01:PRIMARY","A:R3:E2-01:RESERVE","B:R2:E2-01:PRIMARY","B:R2:E2-01:RESERVE","B:R3:E2-01:PRIMARY","B:R3:E2-01:RESERVE"],"fingerprint_classes":["99f24494bf092ad9e2212297fa8b9f9ae5ae6a464b38fb27e7d52300d8c4dde2"],"maximum_members":8},"E2-02":{"members":["A:R2:E2-02:PRIMARY","A:R3:E2-02:PRIMARY","B:R2:E2-02:PRIMARY","B:R3:E2-02:PRIMARY"],"fingerprint_classes":["8139ce5939d7a80c698bbe5db29f299607b794c0f6999ee677195db4b5748786"],"maximum_members":4},"E2-03":{"members":["A:R2:E2-03:PRIMARY","A:R3:E2-03:PRIMARY","B:R2:E2-03:PRIMARY","B:R3:E2-03:PRIMARY"],"fingerprint_classes":["6c3a93bda85cbe69485b7c8157062400ca969ba53ebee8c56c027536ca084c85"],"maximum_members":4},"E2-04":{"members":["A:R2:E2-04:PRIMARY","A:R3:E2-04:PRIMARY","B:R2:E2-04:PRIMARY","B:R3:E2-04:PRIMARY"],"fingerprint_classes":["93601a65d09fe3b9e2b33588e053b501643e6530651cd313df45ca0b235a193b"],"maximum_members":4},"E2-05":{"members":["A:R2:E2-05:PRIMARY","A:R3:E2-05:PRIMARY","B:R2:E2-05:PRIMARY","B:R3:E2-05:PRIMARY"],"fingerprint_classes":["7d926544801b2b0a8adda81282c3e42c6aaf301c33e4e47080c28ceec673d263"],"maximum_members":4},"E3-01":{"members":["A:R2:E3-01:PRIMARY","A:R2:E3-01:RESERVE","A:R3:E3-01:PRIMARY","A:R3:E3-01:RESERVE","B:R2:E3-01:PRIMARY","B:R2:E3-01:RESERVE","B:R3:E3-01:PRIMARY","B:R3:E3-01:RESERVE"],"fingerprint_classes":["c678c17bf6a194b2ee1fce4a1c8bec01bd0f51aeac315f61b05a322d5fe31abd"],"maximum_members":8},"E3-02":{"members":["A:R2:E3-02:PRIMARY","A:R3:E3-02:PRIMARY","B:R2:E3-02:PRIMARY","B:R3:E3-02:PRIMARY"],"fingerprint_classes":["ef7c51fd764b8c2f2c7c170255577111c8d147c875bee255bcaaf03460d8ff32"],"maximum_members":4},"E3-03":{"members":["A:R2:E3-03:PRIMARY","A:R3:E3-03:PRIMARY","B:R2:E3-03:PRIMARY","B:R3:E3-03:PRIMARY"],"fingerprint_classes":["af4827fa10999e7210221650d9e547c1488a7adad4aed7de8f47505ddb67d609"],"maximum_members":4},"E3-04":{"members":["A:R2:E3-04:PRIMARY","A:R3:E3-04:PRIMARY","B:R2:E3-04:PRIMARY","B:R3:E3-04:PRIMARY"],"fingerprint_classes":["cff83db3ac68e2c4a3bf1b95e0ec5b19a60216e1d8d5d82606a15a67f4a21720"],"maximum_members":4},"E3-05":{"members":["A:R2:E3-05:PRIMARY","A:R3:E3-05:PRIMARY","B:R2:E3-05:PRIMARY","B:R3:E3-05:PRIMARY"],"fingerprint_classes":["666dcd06eeaeb168af7b77d593bc0db30381cec772a5748b54248d60657a5120"],"maximum_members":4},"E4-01":{"members":["A:R2:E4-01:PRIMARY","A:R2:E4-01:RESERVE","A:R3:E4-01:PRIMARY","A:R3:E4-01:RESERVE","B:R2:E4-01:PRIMARY","B:R2:E4-01:RESERVE","B:R3:E4-01:PRIMARY","B:R3:E4-01:RESERVE"],"fingerprint_classes":["2279d818ef1af2f928c2b6e03dd3e01955c7666db37bd3f7833acb2d76e29e01","bb3ed883802c943c394c3d632f19ad302dbfffc390a5369fe7463fb887759092","e7340f1603d953e3876c2491ef70a864fff432e964be80a8e8a89437d4801d0f"],"maximum_members":8},"E4-02":{"members":["A:R2:E4-02:PRIMARY","A:R3:E4-02:PRIMARY","B:R2:E4-02:PRIMARY","B:R3:E4-02:PRIMARY"],"fingerprint_classes":["064b91bf8e07079846aa5c56aae6d3ff6c30417529a97f23ef0c4b4c84f0e665","3f7a230fefd71755eb01d5e2fe2fb1de85e7becfd55d36999e6de04714f8a197","ccd7cd8f9381601a28e8a7619c3c65031ea45e81c33aa4fd8e4950d6b6651d54"],"maximum_members":4},"E4-03":{"members":["A:R2:E4-03:PRIMARY","A:R3:E4-03:PRIMARY","B:R2:E4-03:PRIMARY","B:R3:E4-03:PRIMARY"],"fingerprint_classes":["af1e5a60dc1f50aa4ee34b5b4ca540a0b3916aecfe6712c4359f9dd4b7199f5f","b949370a25c7dc598394c653afe1c5584e78e93c6853742171cab3891565347a","e649ff77ea060b4cbcf5e53950bbbd53f4e070701f7de80b0b6e68c16a137407"],"maximum_members":4},"E4-04":{"members":["A:R2:E4-04:PRIMARY","A:R3:E4-04:PRIMARY","B:R2:E4-04:PRIMARY","B:R3:E4-04:PRIMARY"],"fingerprint_classes":["afce74b4555bcc3cdde3ff43c1ac6bea68b5c4d5eec1db1c2e96cb85083be575","f3c43d017b0f954483fe0325b16c656f3d29c66beaa336e8228ff799165f79fa"],"maximum_members":4},"E4-05":{"members":["A:R2:E4-05:PRIMARY","A:R3:E4-05:PRIMARY","B:R2:E4-05:PRIMARY","B:R3:E4-05:PRIMARY"],"fingerprint_classes":["254a8fb612273c76c3c6d8754879867af2be71a71031e2e7e82ec1add8486977","5b31ae478f2cee3e1759d2e33cb83f9dd645216bd705248feedef0137202cb0c","cafbe4748bed7bd4f077512900f7c7d46dd667fa2a3e1c4da144fd1c8ac51b61"],"maximum_members":4},"E5-01":{"members":["A:R2:E5-01:PRIMARY","A:R2:E5-01:RESERVE","A:R3:E5-01:PRIMARY","A:R3:E5-01:RESERVE","B:R2:E5-01:PRIMARY","B:R2:E5-01:RESERVE","B:R3:E5-01:PRIMARY","B:R3:E5-01:RESERVE"],"fingerprint_classes":["ce5455c2eb3c4dcd5ecee7928fca41c9a85ade8d875f433fb43bed7b270cb383"],"maximum_members":8},"E5-02":{"members":["A:R2:E5-02:PRIMARY","A:R3:E5-02:PRIMARY","B:R2:E5-02:PRIMARY","B:R3:E5-02:PRIMARY"],"fingerprint_classes":["fd8d25e0cd0fb74f1c01b4604d78eed4b009b4b809f6d62a65075e4afa5fe9c2"],"maximum_members":4},"E5-03":{"members":["A:R2:E5-03:PRIMARY","A:R3:E5-03:PRIMARY","B:R2:E5-03:PRIMARY","B:R3:E5-03:PRIMARY"],"fingerprint_classes":["82bc5da8ff4ebf8587be1fdec410461f83b52929dc6615a0f588df473fa76bac"],"maximum_members":4},"E5-04":{"members":["A:R2:E5-04:PRIMARY","A:R3:E5-04:PRIMARY","B:R2:E5-04:PRIMARY","B:R3:E5-04:PRIMARY"],"fingerprint_classes":["cec902c93f23a39b90e9a1c7a688ae00af848164bc7d4e9c22bf562a2abd02d4"],"maximum_members":4},"E5-05":{"members":["A:R2:E5-05:PRIMARY","A:R3:E5-05:PRIMARY","B:R2:E5-05:PRIMARY","B:R3:E5-05:PRIMARY"],"fingerprint_classes":["f259f7faf78a20d45692dd8512d09098c05827b74ca65a6da73192ea97116713"],"maximum_members":4},"E6-01":{"members":["A:R2:E6-01:PRIMARY","A:R2:E6-01:RESERVE","A:R3:E6-01:PRIMARY","A:R3:E6-01:RESERVE","B:R2:E6-01:PRIMARY","B:R2:E6-01:RESERVE","B:R3:E6-01:PRIMARY","B:R3:E6-01:RESERVE"],"fingerprint_classes":["0466bacac728ccf96fc9210a70a21df7140f740e212a45884d1739308cc8c0ef"],"maximum_members":8},"E6-02":{"members":["A:R2:E6-02:PRIMARY","A:R3:E6-02:PRIMARY","B:R2:E6-02:PRIMARY","B:R3:E6-02:PRIMARY"],"fingerprint_classes":["2c9095d16b5198eef42c7d458354283d07e3f5be4a4843d1b8191b2763dc2da4"],"maximum_members":4},"E6-03":{"members":["A:R2:E6-03:PRIMARY","A:R3:E6-03:PRIMARY","B:R2:E6-03:PRIMARY","B:R3:E6-03:PRIMARY"],"fingerprint_classes":["4ce94db99626aefae35959c043aecb5875e692f92675e90fc91daa7c6695b4f4"],"maximum_members":4},"E6-04":{"members":["A:R2:E6-04:PRIMARY","A:R3:E6-04:PRIMARY","B:R2:E6-04:PRIMARY","B:R3:E6-04:PRIMARY"],"fingerprint_classes":["fa373c2bac7c6ba28d1509529b3125d86da9a8fe55e802ca4d25c533ca62b3d3"],"maximum_members":4},"E6-05":{"members":["A:R2:E6-05:PRIMARY","A:R3:E6-05:PRIMARY","B:R2:E6-05:PRIMARY","B:R3:E6-05:PRIMARY"],"fingerprint_classes":["972eaa3950ee4332670cfb7dea22cb3b8082bd1f323a17d7b95ce19d321aa5cc"],"maximum_members":4},"E7-01":{"members":["A:R2:E7-01:PRIMARY","A:R2:E7-01:RESERVE","A:R3:E7-01:PRIMARY","A:R3:E7-01:RESERVE","B:R2:E7-01:PRIMARY","B:R2:E7-01:RESERVE","B:R3:E7-01:PRIMARY","B:R3:E7-01:RESERVE"],"fingerprint_classes":["49cd0870fecec6b46f8b8d81600ad01b33a0724a26798c5be7ac801da753cd2e","4d85ad28646a6d82a346b82a292075f5760cb1e3f411191ce49376acb8b1a93c","d1c3da9ae2cce46fc326a9d4be4e7526f19db93116d32340aa007ad2c2a97500"],"maximum_members":8},"E7-02":{"members":["A:R2:E7-02:PRIMARY","A:R3:E7-02:PRIMARY","B:R2:E7-02:PRIMARY","B:R3:E7-02:PRIMARY"],"fingerprint_classes":["92951b86ec0e62d3672c598698daf5812da4cef89eb4845ec5604c6ba8937d13","f908d84920aee765909fc9f4e0d7d38bffd79cf277bdc089a9e6cd18aa2efddf"],"maximum_members":4},"E7-03":{"members":["A:R2:E7-03:PRIMARY","A:R3:E7-03:PRIMARY","B:R2:E7-03:PRIMARY","B:R3:E7-03:PRIMARY"],"fingerprint_classes":["99152903617fe43e06098271430c30980599cd84a3d893352f911d68abb7c96d","a451fa9afeceb4e4e3b489496ef321d47e53a723d90061232ec2acd5e64485a8"],"maximum_members":4},"E7-04":{"members":["A:R2:E7-04:PRIMARY","A:R3:E7-04:PRIMARY","B:R2:E7-04:PRIMARY","B:R3:E7-04:PRIMARY"],"fingerprint_classes":["3b04f8ce70e40aa7200683fc3fd81f17ee7301d42709dc421e453cded7f23ad6","c86ca571f35c5236cb2dc4f6b7b243b9a0911117c4a23b2699c4159c3b7c3ecc"],"maximum_members":4},"E7-05":{"members":["A:R2:E7-05:PRIMARY","A:R3:E7-05:PRIMARY","B:R2:E7-05:PRIMARY","B:R3:E7-05:PRIMARY"],"fingerprint_classes":["021518e38e9f0e7f436e474350b590484b4029301e33d9ad721cb96f75bb5e14","41242a78258cbd9f3b750beb17f6bd646138ce704c3f2d99f4d9c89a92367838"],"maximum_members":4}},"comparison_override":"mandatory E4 boundary rotations/E7 presentation shifts permitted only as exact ledger variants in same frozen subtype group; undeclared 5/6 variants remain prohibited","freshness_exclusions":"fixed Boolean/enum literals may individually recur by allocation; whole typed VALUE sequence must differ; raw generated identities fresh"},
  "ordinal_neutral_similarity_contract": {"contract_id":"g-extract1.ordinal-neutral-similarity.v1","applies_to":"NEW input.text plus canonical schema serialization only; historical side is unchanged; never model-facing bytes","stage_order":["canonical payload serialization","NFC/CRLF/casefold/whitespace as contamination contract","NEW generated-token ordinal masking","shared tokenizer","five-gram sets"],"ordinal_pattern":"(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])","replacements":[{"pattern":"\\b([fd]){ORDINAL}_(\\d{2})\\b","replacement":"\\1_\\2"},{"pattern":"\\bentity {ORDINAL} ([abc])\\b","replacement":"entity \\1"},{"pattern":"\\b(label|code|id)_{ORDINAL}_(\\d{2})\\b","replacement":"\\1_\\2"}],"regex_engine":"Python re ASCII; ordered substitutions; ORDINAL expanded from ordinal_pattern","ordinary_limit_exclusive":0.2,"near_replay_inclusive":0.12,"shape_view":{"algorithm":"after tokenization replace each complete date/time/numeric/option_a..h/true/false token with exact token value; then five-gram sets","value_token_regex":"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2}|[+-]?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)(?:e[+-]?[0-9]+)?|option_[a-h]|true|false)","new_near_replay":"Reject an undeclared structural variant with >=5/6 component matches and max(ordinary,shape)>=0.12. Both fully slot/domain/ledger-valid positions of different subtypes instead retain ordinary>=0.12 near-replay; shape is reported. Same subtype declared variants use content view. No output-dependent exception.","reason":"ordinal masking alone still leaves demonstrated fresh-value near-replay at Jaccard 0; shape view is a stronger added replay control, not a threshold relaxation","replacement_token":"value"},"declared_template_content_view":{"eligible":"NEW/NEW same preregistered subtype group, both matching their exact planned fingerprint class; no undeclared layout","algorithm":"retain ordinary five-grams containing at least one complete numeric/date/time token matching content_value_regex; finite enum/Boolean catalog tokens and generated labels are not scalable freshness evidence; shape view still includes them","limit_exclusive":0.12,"one_empty_set":"Jaccard=0; both empty => NOT_APPLICABLE, never described as evidence of dissimilarity","both_empty_handling":"both exact ledger positions, same subtype group, fresh raw generated VALUE sequence, finite generated labels/enum only; not evidence of dissimilarity","still_report":"ordinary ordinal-neutral Jaccard, shape Jaccard, content Jaccard or NOT_APPLICABLE, freshness and all exact reuse checks for every declared pair","no_freshness_or_reuse_exemption":true,"content_value_regex":"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2}|[+-]?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)(?:e[+-]?[0-9]+)?)","finite_catalog_control":"opaque enum/Boolean positions prospectively counterbalanced and scored exactly; they may recur as finite catalog atoms, not treated as textual freshness; both-empty content case requires fresh raw generated VALUE sequence and all exact reuse checks"},"prospective_correction":{"reason":"fixed E7 reserve source/schema scaffolds yield ordinary neutral Jaccard >0.20 despite fresh integers; generated-only string copies yield 1.0 after removing ordinals. Universal ordinary-Jaccard prohibition contradicts fixed subtype recurrence. Mandatory E4 truth/boundary rotations and E7 presentation shifts are planned 5/6 variants, which also require this bounded ledger exception; no author-selected variants.","scope":"same preregistered subtype group, exact ledger variants only. Content <0.12 replaces ordinary <0.20 for these pairs. All others retain thresholds and stronger shape near-replay. Historical unchanged. Different planned subtype boundaries necessarily give some 5/6 matches; after independently proving actual subtype/domain and exact ledger assignment, these pairs keep original ordinary 0.12 rule, not value-masked shape veto. Shape catches undeclared layouts; exact allocation also rejects them.","not_a_gate_change":true,"requires_independent_rereview":true},"decision_table":[{"case":"HISTORICAL_NEW","decision":"reject ordinary>=0.20 or projection 3/3 or (>=2/3 and ordinary>=0.12); NEW masked only"},{"case":"NEW_UNDECLARED_STRUCTURE","decision":"AUTHORING_ERROR; additionally report >=5/6 plus max(ordinary,shape)>=0.12 replay evidence"},{"case":"NEW_DECLARED_SAME_SUBTYPE","decision":"both exact ledger positions; reject raw typed VALUE sequence equality or any exact reuse failure; reject content>=0.12; both content sets empty permitted only generated-label/finite-enum case; no raw payload reuse"},{"case":"NEW_DECLARED_DIFFERENT_SUBTYPE","decision":"reject ordinary>=0.20 or exact six-component collision or (>=5/6 and ordinary>=0.12); no exception for different subtype"}]},
  "entity_selection_allocation_contract": {"contract_id":"g-extract1.entity-selection-allocation.v1","column_order":["E5-01","E5-02","E5-03","E5-04","E5-05"],"selected_index_matrix":{"A:R2":[0,1,0,1,0],"A:R3":[1,0,2,0,2],"B:R2":[1,0,1,0,1],"B:R3":[0,1,0,1,0]},"index_order":"entity A/B/C = 0/1/2; generated entities in letter order","constraint":"two-entity slots both indices, three-entity slots all three across four contexts","enum_permutation":"entity i option[(i-selected_index+frozen_gold_option_index) mod entity_count]; old gold positions unchanged","baseline_gate":"no fixed schema/subtype/selector-role mapping >=4/5 in A and B of same round","exhaustive_domain":"all mappings into indices 0/1/2; invalid index C for two entities counts incorrect","baseline_expected":{"context_order":["A:R2","A:R3","B:R2","B:R3"],"always_index_scores":{"0":[3,2,2,3],"1":[2,1,3,2],"2":[0,2,0,0]},"mapping_families":{"schema":{"exhaustive_mapping_count":243,"maximum_by_context":[5,5,5,5],"maps_passing_all_contexts":0,"maps_passing_both_phases_same_round":0},"subtype":{"exhaustive_mapping_count":243,"maximum_by_context":[5,5,5,5],"maps_passing_all_contexts":0,"maps_passing_both_phases_same_round":0},"selector_role":{"exhaustive_mapping_count":27,"maximum_by_context":[3,3,3,3],"maps_passing_all_contexts":0,"maps_passing_both_phases_same_round":0}}},"interpretation":"prospective counterbalancing, not random sampling or causal independence"},
  "value_allocation_contract": {"contract_id":"g-extract1.value-allocation.v1","applies_to":"every primary and its slot01 reserve; no model-tier-specific content; all direct literals, source facts and evaluated results remain operation-domain valid","magnitude_bands":{"SMALL":[1,9],"MEDIUM":[10,99],"LARGE":[100,999]},"magnitude_algorithm":"floor(abs(exact rational numeric value)); band applies to source numeric operands in source/catalog order, not arbitrary derived results/thresholds; magnitude zero is allowed only frozen E1-05 offset or elapsed zero result","context_pattern":{"A:R2":0,"A:R3":1,"B:R2":1,"B:R3":0},"context_parameters":{"0":{"precision_places":1,"add_carry":true,"subtract_borrow":false,"divide_quotient_places":1,"divide_reduced_denominator":"POWER_OF_2_ONLY","numeric_gap":"1","date_gap_days":1,"time_gap_minutes":5,"numeric_entity_gap":"2","date_entity_gap_days":2,"time_entity_gap_minutes":13,"two_entity_selected_rank":0,"three_entity_selected_rank":1},"1":{"precision_places":2,"add_carry":false,"subtract_borrow":true,"divide_quotient_places":2,"divide_reduced_denominator":"BOTH_2_AND_5","numeric_gap":"1","date_gap_days":1,"time_gap_minutes":5,"numeric_entity_gap":"2","date_entity_gap_days":2,"time_entity_gap_minutes":13,"two_entity_selected_rank":1,"three_entity_selected_rank":0}},"three_entity_rank_override":{"A:R2":1,"A:R3":0,"B:R2":2,"B:R3":1},"slot_profiles":{"E1-01":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[7,14],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E1-02":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[7,14],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E1-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[7,14],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E1-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[1,7],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E1-05":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"R2_0_R3_366","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E2-01":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E2-02":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E2-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E2-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E2-05":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[0,0],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E3-01":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE_OPERANDS_POSITIVE_RESULT","arithmetic_complexity":"CONTEXT_ADD_CARRY","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E3-02":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE_OPERANDS_NEGATIVE_RESULT","arithmetic_complexity":"CONTEXT_SUBTRACT_BORROW","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E3-03":{"magnitude_bands":["MEDIUM","MEDIUM","MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE_OPERANDS_POSITIVE_RESULT","arithmetic_complexity":"THREE_OPERANDS_AT_LEAST_ONE_CARRY","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E3-04":{"magnitude_bands":["LARGE","MEDIUM"],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE_OPERANDS_POSITIVE_RESULT","arithmetic_complexity":"TERMINATING_NONINTEGRAL_QUOTIENT_CONTEXT_DECIMAL_LENGTH","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E3-05":{"magnitude_bands":"R2_SMALL_R3_LARGE","number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE_OPERANDS_POSITIVE_RESULT","arithmetic_complexity":"FROZEN_CONVERSION_ID","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E4-01":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE_OPERANDS","arithmetic_complexity":"CONTEXT_ADD_CARRY","comparison_distance":"CONTEXT_NUMERIC_GAP","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E4-02":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE_OPERANDS","arithmetic_complexity":{"operation":"SUBTRACT","borrow":true},"comparison_distance":"CONTEXT_NUMERIC_GAP","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E4-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"CONTEXT_DATE_GAP","temporal_distance":[7,14],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E4-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"CONTEXT_TIME_GAP","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E4-05":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE_OPERANDS","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"CONTEXT_NUMERIC_GAP","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E5-01":{"magnitude_bands":["MEDIUM","MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"CONTEXT_NUMERIC_ENTITY_GAP","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"CONTEXT_TWO_ENTITY_RANK"},"E5-02":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"DISTINCT_GENERATED_STRINGS","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E5-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"ALL_THREE_ENUM_OPTIONS","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E5-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"CONTEXT_DATE_ENTITY_GAP","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"CONTEXT_TWO_ENTITY_RANK"},"E5-05":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"CONTEXT_TIME_ENTITY_GAP","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"CONTEXT_THREE_ENTITY_RANK"},"E6-01":{"magnitude_bands":["MEDIUM"],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E6-02":{"magnitude_bands":["MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E6-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E6-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[7,14],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E6-05":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"NOT_APPLICABLE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":[31,89],"entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E7-01":{"magnitude_bands":["SMALL","SMALL"],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E7-02":{"magnitude_bands":["MEDIUM"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E7-03":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"IRREGULAR_MINUTE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E7-04":{"magnitude_bands":[],"number_precision":"NOT_APPLICABLE","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"},"E7-05":{"magnitude_bands":["MEDIUM","SMALL"],"number_precision":"CONTEXT_PRECISION","sign_class":"POSITIVE","arithmetic_complexity":"NOT_APPLICABLE","comparison_distance":"NOT_APPLICABLE","temporal_distance":"NOT_APPLICABLE","entity_separation":"NOT_APPLICABLE","distractor_count":0,"distractor_schema":"NOT_APPLICABLE","distractor_placement":"NOT_APPLICABLE","source_time_class":"NOT_APPLICABLE","date_years":[2028,2043],"entity_selected_rank":"NOT_APPLICABLE"}},"derivation":"copy slot profile, expand CONTEXT_* using context_pattern/context_parameters; E4 gap=0 iff frozen boundary EQUAL else frozen domain gap; R2_SMALL_R3_LARGE and temporal R2_0_R3_366 expand by round; entity rank override applies only E5-05","number_precision_algorithm":"logical fractional places of canonical exact decimal after removing trailing fractional zeros; INTEGER has 0; integral-valued NUMBER class=0 is defined but zero authored allocation; NUMBER sources must have exactly 1 or 2 places as allocated, not visually integral","carry_algorithm":"align numeric operands to maximum fractional places; use absolute scaled integers, sum per base-10 column including carry-in; carry=true iff any column sum>=10; exactly three SUM operands","borrow_algorithm":"align to maximum fractional places; subtract smaller absolute value from larger; borrow=true iff any column requires borrow-in from its next column; sign of operation separately frozen","division":"positive INTEGER numerator LARGE and divisor MEDIUM, reduced rational denominator >1; remove factors2/5; remainder must1. Pattern0 denominator has factors2 only, exact decimal one place; pattern1 contains both2 and5, exact decimal two places; no rounding; divisor is exactly two digits","conversion":"R2 HOURS_TO_MINUTES multiply60, source SMALL fractional NUMBER; R3 GRAMS_TO_KILOGRAMS divide1000, source LARGE fractional NUMBER; precision per context; exact rational calculation","temporal":"DATE source and date comparison literals/gold years 2028..2043 inclusive; exact subtype boundary plus profile offset interval; TIME source minute modulo30 not0 (excludes on-hour/half-hour); clock/elapsed duration31..89 except E2-05 zero","comparison":"non-equal numeric absolute operand gap exactly1, DATE exactly1 day, TIME exactly5 minutes; equal gap0; E4 truth/boundary matrix remains unchanged","entity":"pairwise distinct values; numeric/date/time sorted adjacent semantic values have exact gap2/2days/13minutes; selected rank fixed by context; date/time sorted on same-date-free civil representations, no TIME midnight wrap for separation; strings/enums use frozen generated/enum allocation","sign":"all source numeric values and numeric literals positive except E1-05 zero offset; only E3-02 has negative arithmetic result; no blueprint-selected negative input; arithmetic constants derived from profile cannot choose sign","source_representation_binding":"template_recurrence_contract.structural_wiring fixes references/fact order; exactly zero distractors in all168, no hidden unused facts; relevance/fact roles derived from actual typed graph","balancing_claim":"patterns [0,1,1,0] match marginal A/B and R2/R3 precision/carry/borrow difficulty; temporal edge and conversion IDs retain intentional round effects; E4 equality/unequal and E7 presentation remain structured confounds, not causal isolation or IID; every unequal E4 case has same domain distance regardless truth; E5 selected rank is counterbalanced, not always extreme","baseline_novelty_limitation":"broader hand-authored stratification, not proof of natural-population safety; concrete values must pass all historical/new and new/new contamination rules before contact","reserve_match":"value-shape profile is derived only after actual semantics/slot/profile validation and is appended to the canonical reserve equivalence profile; reserve presentation may differ exactly as already frozen","mixed_subtraction_correction":"E4-02 INTEGER minus fractional NUMBER positive result always borrows at fractional column; E3-02 negative-result absolute subtraction retains rotated borrow class.","e7_boolean_source_allocation":{"A:R2":true,"A:R3":false,"B:R2":false,"B:R3":true}}
}
```
<!-- V9_NORMATIVE_END -->
