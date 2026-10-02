# G-EXTRACT1 Design Candidate v4

Status: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_4`

This is a design candidate only. It authorizes no blueprint, fixture or reserve authoring, implementation, provider contact, pilot, freeze, Phase A, Phase B, routing update, or belief change.

## 1. Identity and historical boundary

- Experiment: `G-EXTRACT1`, Prospective Structured-Extraction Requalification and Generalization Test.
- Design contract: `g-extract1.design-candidate.v4`.
- G-ROUTE4 remains closed `FAILED`; this design neither reopens nor rescales it.
- Closure SHA-256: `d992a169a2be293909f0fe0f1b39720656f40a09dc4f6b4e9c53449110cef8be`.
- Unsafe-stop diagnostic SHA-256: `461a85368a6cbbd39429bebbae883c0b17be614db52e343150b23051041b4868`.
- Historical evidence commit: `c95d2d1a4177c0f6a33bb8ffb772dfc19c272646`.
- Historical findings define prospective failure classes only. Historical prompts, answers, fixtures, and gold are prohibited as scored or reserve items.
- Belief effects are `none`.

## 2. Research question and causal limit

Under the byte-bound G-ROUTE4 extraction system prompt, renderer, normalization, and operational validator, can a larger family-stratified qualification test identify R2/R3 model-tier cells that retain safe and useful behavior on separately authored validation fixtures without false-clean extraction errors?

This tests whether stronger prospective sampling and coverage would have exposed observed failure classes. It does not separately identify prompt wording, model weights, provider internals, or stochastic sampling as the cause.

Hypotheses are descriptive and prospective:

1. At least one previously qualified extraction cell will fail the larger Phase A gate.
2. Date/time and numeric/threshold families will produce more errors than entity/binding families.
3. Some wrong answers will recur across both Phase A repeats.
4. Qualification need not be monotonic with parameter count.
5. A Phase A-qualified cell must independently pass Phase B.

## 3. Scope and phases

Only structured extraction is in scope. Candidate cells are `R2` and `R3` crossed with small, mid, and large tiers: six cells total. Grounded research, ordinary conversation, planning, synthesis, coding, R1 promotion, R4 routing, timezone conversion, production routing, and prompt repair are excluded.

Each phase contains 35 distinct fixtures per round: five in each of seven primary families. Each round has 30 determinate fixtures and five E7 ambiguity fixtures.

| Phase | Purpose | Fixtures | Repeats | Models | Maximum calls |
|---|---|---:|---:|---:|---:|
| A | Prospective requalification | 70 | 2 | 3 | 420 |
| B | Independent fresh-fixture validation | 70 | 1 | only Phase A entrants | 210 |

All 140 scored fixtures and 28 family-slot reserves, all gold, both schedules, and all gates must be frozen before first provider contact. Phase A and Phase B evidence is never pooled. Phase B is zero calls when no Phase A cell qualifies.

## 4. Canonical operation-definition catalog

Contract: `g-extract1.operation-definitions.v2`.

Every scored or reserve fixture renders the model-facing subject from this finite catalog. Authors may vary source facts, field identifiers, literals, record type, and schema, but not instructional wording or helpfulness.

Field, derived-field, and collection identifiers match `^[a-z][a-z0-9_]{0,47}$`, remain lowercase ASCII, and render unquoted without normalization. Enum literals use the same form. Record types match `^[a-z]+(?: [a-z]+){0,3}$`. The opening sentence is exactly:

`Extract the {record_type} record.`

A fixture has one operation node or one connected two-node chain. In a two-node graph, the second node consumes the first target and is the unique sink; independent nodes are prohibited. Each node renders one sentence in stable topological order, then unsigned UTF-8 target-field order.

Every non-target placeholder is an exact `{kind,value}` object. Ordinary nodes have exact keys `id,target,arguments`; `UNIT_CONVERSION` alone also requires `conversion_id`. Canonical kinds and bytes are:

| Kind | Canonical UTF-8 rendering |
|---|---|
| `field_identifier`, `derived_field_identifier`, `collection_identifier` | exact matching identifier, unquoted |
| `integer_literal` | `0`, positive digits without a leading zero, or `-` plus a nonzero digit sequence; plus signs, leading zeroes, and negative zero are prohibited |
| `decimal_literal` | plain non-exponent decimal; no leading integer zero except `0`; trailing fractional zeroes removed while retaining one fractional digit; negative zero becomes `0.0` |
| `date_literal` | exact valid proleptic-Gregorian `YYYY-MM-DD` |
| `time_literal` | exact valid 24-hour `HH:MM` |
| `string_literal`, `entity_selector_literal` | printable ASCII source value rendered exactly by Python `json.dumps(value, ensure_ascii=True, separators=(',', ':'))`; double quotes are mandatory and quote/backslash use JSON escaping |
| `enum_literal` | exact lowercase identifier, unquoted |

`SUM` accepts two through four operands of identifier, derived-identifier, integer, or decimal kind. Two render `A and B`; three or four use comma-space and `, and ` before the final item. Array order is immutable. `UNIT_CONVERSION.source` is exactly a source `field_identifier`. `ENTITY_FIELD_BIND.selector_value` is exactly an `entity_selector_literal`.

Allowed argument kinds are also finite: arithmetic binary operands use field, derived-field, integer, or decimal; elapsed endpoints use field, derived-field, or time; calendar date uses field, derived-field, or date while days uses field, derived-field, or integer; clock time uses field, derived-field, or time while minutes uses field, derived-field, or integer; ordering comparisons use field, derived-field, integer, decimal, date, or time; equality additionally permits enum; count uses collection; entity binding uses source/selector field identifiers plus one quoted selector; exact copy uses source or derived field.

| Operation ID | Exact model-facing sentence |
|---|---|
| `ADD` | `{target} is {left} plus {right}.` |
| `SUBTRACT` | `{target} is {minuend} minus {subtrahend}.` |
| `MULTIPLY` | `{target} is {left} times {right}.` |
| `DIVIDE` | `{target} is {dividend} divided by {divisor}.` |
| `SUM` | `{target} is the sum of {operands}.` |
| `COUNT` | `{target} is the number of entries in {collection}.` |
| `ELAPSED_MINUTES` | `{target} is the elapsed minutes from {start} to {end}.` |
| `CALENDAR_DAY_OFFSET` | `{target} is {date} plus {days} calendar days.` |
| `CLOCK_MINUTE_OFFSET` | `{target} is {time} plus {minutes} minutes.` |
| `GT` | `{target} is true when {left} is greater than {right}.` |
| `GTE` | `{target} is true when {left} is greater than or equal to {right}.` |
| `LT` | `{target} is true when {left} is less than {right}.` |
| `LTE` | `{target} is true when {left} is less than or equal to {right}.` |
| `EQ` | `{target} is true when {left} is equal to {right}.` |
| `ENTITY_FIELD_BIND` | `{target} is {source_field} for the entity whose {selector_field} equals {selector_value}.` |
| `EXACT_COPY` | `{target} is copied exactly from {source_field}.` |

`UNIT_CONVERSION` selects exactly one of these frozen sentences:

| Conversion ID | Formula | Exact model-facing sentence |
|---|---|---|
| `HOURS_TO_MINUTES` | `source * 60` | `{target} is {source} multiplied by 60, expressed in minutes.` |
| `MINUTES_TO_HOURS` | `source / 60` | `{target} is {source} divided by 60, expressed in hours.` |
| `KILOGRAMS_TO_GRAMS` | `source * 1000` | `{target} is {source} multiplied by 1000, expressed in grams.` |
| `GRAMS_TO_KILOGRAMS` | `source / 1000` | `{target} is {source} divided by 1000, expressed in kilograms.` |
| `DOLLARS_TO_CENTS` | `source * 100` | `{target} is {source} multiplied by 100, expressed in cents.` |
| `CENTS_TO_DOLLARS` | `source / 100` | `{target} is {source} divided by 100, expressed in dollars.` |

The historical absence sentence is exactly `Use 'not_provided' when the text says a value has not been provided.` It appears exactly once if and only if a schema field has type `provided|not_provided`. The only absence sentinel is `not_provided`; no new sentinel is introduced.

Assembly order is opening, operation sentences, historical absence sentence when required, then the frozen common suffix. Phase A and B use byte-identical wording for the same operation ID. Free-form operation instructions, synonyms outside this catalog, explanatory sentences, intermediate calculations, edge-case reminders, examples, expected values, family names, historical-failure references, and outcome-derived coaching are prohibited.

The machine contract freezes nine rendering vectors: negative integer, decimal, date, time, two-operand SUM, three-operand SUM, a quoted selector containing a space, a selector containing escaped quotes, and a reversed-input two-node dependency. A metadata object is valid only if the deterministic renderer yields the exact frozen SUBJECT bytes.

## 5. Metadata-derived primary families

Contract: `g-extract1.family-assignment.v2`.

The canonical fixture representation contains typed operation nodes; output fields sorted by unsigned UTF-8 field name; canonical gold values; entities sorted by canonical selector-literal bytes; ordered typed source-fact records; and sorted required-output names. No family or feature tag is author-selected.

Each source-fact record has exactly `template_id`, `field_identifier`, `value`, and `entity_selector_value`. `VALUE` renders either `{field} is {value}.` or `For {quoted entity}, {field} is {value}.`; `EXPLICIT_ABSENCE` renders the corresponding `was not provided.` sentence. One record is one sentence, records join with one ASCII space, and rendered source text contains no CR/LF/TAB. Sentence index is record index; no NLP segmentation occurs. Entities receive zero-based indices after unsigned-UTF-8 sorting of unique selector literals.

Derived metadata is exact:

- unresolved count is the count of required `provided|not_provided` fields whose gold is `not_provided` and which have a matching explicit-absence record; a partial match is an authoring error;
- sentinel availability follows required schema types; entity count is sorted entity-list length; entity disambiguation is true exactly when at least two entities have source facts for the bound source field and `ENTITY_FIELD_BIND` selects one unique selector;
- terminal operation is the unique graph sink; source operations are sorted unique non-sink IDs;
- threshold, temporal, and aggregation values are the unique operation of their respective finite sets or `NONE`; more than one is an authoring error;
- selector role comes from the selected entity's frozen `IDENTIFIER`, `ATTRIBUTE`, or `EVENT_ROLE` field;
- source-fact role is explicit absence first, then direct binding/copy target, then any operation-referenced support, otherwise distractor;
- direct-copy-only means every node is `EXACT_COPY`.

Output role is mechanically mapped: comparison to Boolean; calendar to date; clock to time; arithmetic, unit conversion, count, sum, and elapsed minutes to number; entity bind to entity-bound; source-field exact copy to direct copy; and explicit missing gold to absence sentinel. An `EXACT_COPY` wrapping the sole upstream derived target retains the upstream derived role.

The primary family is the first matching predicate:

| Priority | Family | Mechanical predicate |
|---:|---|---|
| 1 | E7 | `unresolved_required_field_count == 1` and `unknown_sentinel_available == true` |
| 2 | E5 | `entity_disambiguation_required == true` |
| 3 | E4 | terminal operation in `GT,GTE,LT,LTE,EQ` |
| 4 | E1 | terminal operation is `CALENDAR_DAY_OFFSET` |
| 5 | E2 | terminal operation in `CLOCK_MINUTE_OFFSET,ELAPSED_MINUTES` |
| 6 | E3 | terminal numeric operation, or terminal `EXACT_COPY` whose sole source operation is numeric |
| 7 | E6 | terminal operation in `ENTITY_FIELD_BIND,EXACT_COPY` |

No match is an authoring error. Multiple matches use first-match priority. Difficulty, importance, author intent, and a supposed principal challenge are not inputs. Secondary tags are computed only as follows: calendar/clock/elapsed from their operation IDs; aggregation from a numeric operation; unit conversion, threshold, entity binding, and exact copy from presence of their operation IDs; equality boundary from `EQ` or exact gold boundary `EQUAL`; field binding from sink `ENTITY_FIELD_BIND` or `EXACT_COPY`; multi-step from two nodes; and ambiguity from unresolved-count one plus sentinel availability. Five adversarial derivation vectors freeze entity+threshold, temporal+threshold, aggregation+copy, ambiguity+entity, and copy+entity-selector precedence.

## 6. Composed-feature coverage

Per phase and round, eight distinct fixtures are reserved for four non-overlapping quota rows, two fixtures each:

1. C1: E4 terminal comparison fed by `ADD,SUBTRACT,MULTIPLY,DIVIDE,SUM,COUNT`, or `UNIT_CONVERSION`.
2. C2: E4 terminal comparison fed by calendar or clock/elapsed operation, with at least one calendar and one clock/elapsed fixture.
3. C3: exactly two nodes: a numeric operation followed by sink `EXACT_COPY`, whose derived-field source equals the first target; this yields E3 through the wrapped-numeric predicate and mechanically supplies aggregation, field-binding, exact-copy, and multi-step tags.
4. C4: E5 with terminal `ENTITY_FIELD_BIND` and field-binding tag.

These fixtures count toward their primary-family quotas. One fixture cannot satisfy multiple composed rows. The requirement is compatible with 35 fixtures because E4 supplies four of its five fixtures, E3 supplies two of five, E5 supplies two of five, and the rows are distinct.

## 7. Ambiguity and nonacceptance

Contract: `g-extract1.ambiguity-scoring.v3`.

E7 measures semantic ambiguity recognition and operational containment separately. Each E7 fixture has exactly one unresolved required field, at least two supported fields, exact unresolved schema type `provided|not_provided`, and source text explicitly saying the value was not provided. No family-specific instruction is permitted.

Operational parsing remains the historical ordinary `json.loads` path. Evaluation separately uses `json.loads` with an `object_pairs_hook` that retains ordered pairs and records a repeated decoded key at every object scope; lexical integer/float callbacks preserve numeric tokens. The classifier uses only observable infrastructure/truncation/byte, operational parse/schema/acceptance, semantic parse/schema/value, duplicate-key, sentinel, and supported-field fields. First match wins:

| Priority | Outcome | Mechanical condition | Semantic credit | Safe containment |
|---:|---|---|---|---|
| 1 | `infrastructure_missing` | infrastructure event | no | unknown; observation is insufficient |
| 2 | `provider_truncated` | provider marks truncation | no | exactly when not operationally accepted |
| 3 | `empty_output` | zero raw bytes | no | yes |
| 4 | `json_parse_failure` | JSON parse fails | no | yes |
| 5 | `non_object_root` | parsed root is not object | no | yes |
| 6 | `operational_schema_invalid` | operational schema invalid | no | yes |
| 7 | `semantic_schema_invalid` | operational schema passed but duplicate-aware semantic schema failed | no | yes only if not operationally accepted; operational acceptance is false-clean |
| 8 | `exact_valid_not_provided` | semantic schema/value valid, sentinel exact, and every supported field exact | yes | yes |
| 9 | `exact_valid_unsupported_value` | unresolved value is not exact sentinel | no | no; false-clean |
| 10 | `exact_valid_supported_field_error` | semantic value invalid or supported field differs from gold | no | no; false-clean |

Priority 9 precedes 10 when both value defects exist. After priorities 1-7, Boolean semantic-value, sentinel, and supported-field tests make priorities 8-10 exhaustive. Prose-only output is `json_parse_failure`; no refusal intent is inferred. Omission, null, wrong operational type, wrong sentinel, or extra field is operationally invalid. Any duplicate key is semantically invalid even when the unchanged operational parser accepts its last value; such operational acceptance is false-clean and can never receive `exact_valid_not_provided`. Omitting only the ambiguous field or returning only supported fields gets no semantic credit. Five frozen vectors cover duplicate unresolved/supported keys and the exact nonduplicate object.

Phase A requires five distinct E7 fixtures and all 10 repeat observations to be `exact_valid_not_provided` and safely contained. Phase B requires five distinct E7 fixtures and all 5 observations. Malformed, truncated, empty, prose, or schema-invalid output never earns recognition credit.

## 8. Exact-value and representation semantics

Contract: `g-extract1.exact-value-comparator.v1`. The operational validator stays unchanged; operational acceptance plus semantic failure is false-clean.

- Integer fields require a lexical JSON integer: `5` passes; `5.0` and `5e0` fail; `-0` equals `0`.
- Number fields compare exact decimal value: `5`, `5.0`, `5.00`, and `5e0` are equivalent. No binary-float tolerance is used.
- Only cataloged unit conversions are allowed. Unit-bearing strings are exact; omission fails.
- Strings/entities compare exact Unicode scalars including case, spacing, and punctuation. There is no trimming, aliasing, abbreviation, or case fold.
- Only exact leading labels `the`, `Order`, or `Vendor`, followed by one space, may be removed when the frozen schema calls for label removal.
- JSON object key order and insignificant JSON whitespace are ignored recursively. Duplicate, extra, omitted, or null fields are invalid.
- Arrays and nested values are prohibited in scored baseline schemas.
- Dates are exact zero-padded `YYYY-MM-DD`, valid in the proleptic Gregorian calendar; start date is day zero for plus-N-days.
- Times are exact zero-padded 24-hour `HH:MM`, with forward elapsed-time interpretation and explicit midnight rollover.
- Timezones are out of scope. Thresholds mean literal `>`, `>=`, `<`, `<=`, and equality.
- Semantic parsing uses duplicate-preserving `object_pairs_hook`, exact lexical numeric callbacks, and treats invalid JSON leading zeroes as malformed. A duplicate makes semantic schema validity false without changing historical operational parsing.

## 9. Contamination and fingerprint algorithms

Contract: `g-extract1.contamination.v2`.

Authored model-facing text is limited to printable ASCII plus CR, LF, and TAB. Every other code point is rejected before fixture freeze. Historical comparison covers all G-ROUTE4 extraction scored and reserve corpora.

Similarity payload is constructed only as `input.text + LF + canonical_schema_serialization`; no prompt substrings are removed afterward. Schema serialization sorts keys by unsigned UTF-8 bytes and emits `field=type` lines with LF separators and no terminal LF. The excluded request spans are the entire UTF-8 `request.system`, the entire UTF-8 `request.prompt` (opening, operations, absence sentence, and common suffix), and exact `request.input_marker` bytes `INPUT` followed by LF.

Normalization is exact: Unicode NFC; default Unicode casefold; CRLF/CR to LF; every maximal Unicode whitespace run to one ASCII space; trim ends; entities receive no anonymization; canonical schema is appended before normalization. Punctuation is not rewritten. Token alternatives consume date, time, context-valid number, then identifier. A leading sign belongs to a number only when not immediately preceded by ASCII letter, digit, or underscore; therefore subtraction-like `5-3` becomes `5`,`3`, while `-5` remains one token.

Tokenization uses Python `re` in ASCII mode with:

`[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2}|(?<![a-z0-9_])[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:e[+-]?[0-9]+)?|[a-z][a-z0-9]*(?:_[a-z0-9]+)*`

Matches are left-to-right non-overlapping `finditer`; an empty sequence is invalid. Frozen vectors cover `2026-10-01`, `23:45`, `-5`, `5-3`, `5e-3`, `$12.50`, `entity_name`, and `field-name`. Token 5-grams are contiguous tuples at each offset, deduplicated into sets. Jaccard is intersection size divided by union size; both empty is 1.0 and only one empty is 0.0. Every compared pair must be strictly below 0.20.

The fingerprint is a UTF-8 JSON array in this component order, compact separators, no whitespace or terminal LF:

1. `operation_graph`: stable-topologically sort nodes. Emit `[operation_id, operand_kind_array, dependency_index_array]`; typed placeholder kinds map mechanically to source field, derived field, literal, collection, or entity selector, following catalog/SUM order. Names and literal values are excluded.
2. `output_schema_roles`: derive each role through section 5's finite operation/schema map, emit one `[schema_type, role]` pair per output field retaining duplicates, and sort compact pair bytes unsigned.
3. `entity_role_graph`: `NONE` for zero records; `SINGLE_ENTITY` for one; `MULTI_ENTITY_NO_DISAMBIGUATION` for multiple records without disambiguation; otherwise map `entity_selector_role` to `MULTI_ENTITY_SELECT_BY_IDENTIFIER`, `_ATTRIBUTE`, or `_EVENT_ROLE`.
4. `boundary_relation`: `NONE` without terminal comparison; otherwise evaluate exact left/right gold operands and emit `BELOW`, `EQUAL`, or `ABOVE` from left compared with right.
5. `temporal_pattern`: `NONE` without temporal operation. Clock/elapsed emits `MIDNIGHT_ROLLOVER` exactly when the forward result crosses midnight, else `SAME_DAY_FORWARD`. Calendar offset emits `LEAP_DAY_BOUNDARY` when inclusive traversal contains February 29, else `YEAR_BOUNDARY` when years differ, else `MONTH_BOUNDARY` when months differ, else `DATE_WITHIN_MONTH`.
6. `source_fact_layout`: first-match over mechanically generated records. Explicit absence wins. Interleaving requires at least four target/support records, at least two entities, adjacent entity indices different, and each entity twice. Before/after distractor requires every distractor strictly before/after every target/support. Target-before-support requires first target before every support. Contiguous-single requires at least one target/support, at most one entity, and an unbroken target/support index interval. Anything else is `AUTHORING_ERROR`. Frozen vectors cover all six layouts and two rejection forms.

Three full fingerprint vectors freeze exact bytes for a single-entity sum, multi-entity binding, and calendar-to-threshold graph. They jointly exercise operand kinds/dependencies, output roles, entity roles, boundary/temporal values, and source layout.

Pairwise comparison includes every historical G-ROUTE4 extraction fixture against every G-EXTRACT1 scored/reserve fixture, A/A, A/B, B/B, every scored/reserve pair, and reserve/reserve. Exact normalized payload, answer, entity/identifier, or date-number tuple reuse is prohibited. Historical versus new, A versus B, primary versus mapped reserve, and reserve versus reserve exact fingerprint collisions are prohibited. Within one phase/round/family, an exact fingerprint may occur at most twice only below Jaccard 0.12 with all entities and values different. A pair matching at least five of six fingerprint components at Jaccard at least 0.12 is a prohibited near replay. Recurrence of the same abstract failure class or operation ID is permitted.

Before freeze, two separately authored source modules must independently implement normalization, tokenization, derivation, serialization, and fingerprinting. They may share the frozen contract/data and generic standard-library primitives, but no normative implementation or helper code. Their normalized payload, token sequence, and fingerprint bytes must agree for every fixture; disagreement blocks freeze. An automated all-pairs report and blind human contamination review must also pass. Lineage labels alone prove nothing.

## 10. Gold, adjudication, and reserves

Determinate gold freezes typed canonical values, independent derivation, binding map, determinacy proof, primary family, secondary features, operation metadata, and rationale. E7 gold freezes the one unresolved field, exact `not_provided` sentinel, supported values, and explicit-absence proof.

Reviewer A solves without proposed gold. Reviewer B audits arithmetic, calendar semantics, bindings, family assignment, and exact-value compliance. Preserved disagreements are resolved by an operator-approved adjudicator before provider contact. Fixture, gold, reserve, equivalence, and adjudication freeze together. A gold defect after contact invalidates the affected run; it is not repaired in place.

Contract `g-extract1.reserve-activation.v3` provides one family-slot reserve, not one reserve per primary fixture. Slot ID is exactly `RESERVE:{phase}:{round}:{primary_family}`; 2 phases x 2 rounds x 7 families gives 28 slots. Each slot freezes its reserve ID, all five primary IDs in unsigned-UTF-8 order, and one replacement profile. No selection pool exists. Activation is allowed only before provider contact for a mechanical schema defect, unresolved gold/adjudication defect, contamination/fingerprint failure, duplicate entity/date/number tuple, quota/signature violation, or corpus-level similarity failure. Style preference, anticipated or observed model behavior, and gate improvement are ineligible.

All five primaries are evaluated before selection. Zero defects means no activation; more than one defect in a slot stops authoring. Exactly one defective primary may consume the reserve only when phase, round, family, composed row, secondary features, field types, operator/boundary, ambiguity, risk, and output-schema roles exactly match its frozen profile. No match stops. Activation is write-once, invalidates the candidate freeze, and reruns family/composed/risk/schema-role balance, every contamination comparison, gold/adjudication, and all digests. Ad hoc and post-contact replacement are prohibited.

## 11. Gates and benchmark statistics

These are decision statistics for this frozen authored benchmark, not estimates of performance in an IID natural population.

Per Phase A cell: 35 fixtures, 70 observations, 35 repeat pairs, five fixtures per family, and all composed quotas. Per Phase B entrant: 35 fixtures, 35 observations, five per family, and all composed quotas.

Independent pass/fail gates in each phase:

- denominator and family/composed coverage exact;
- false-clean: zero affected fixtures and observations; one-sided 95% upper bound at 0/35 is `0.082031636`, below 0.10;
- determinate semantic correctness: at least 29/30; lower bound `0.851403931`, at least 0.85;
- determinate structural validity: at least 29/30;
- useful correct acceptance: at least 27/30; lower bound `0.761402143`, at least 0.75;
- E7 recognition and containment: Phase A 10/10 observations across 5/5 fixtures; Phase B 5/5;
- malformed determinate fixtures: at most one, while structural 29/30 must also pass.

Enforced redundant guardrails are 4/5 semantic correctness in each determinate family and zero accepted E5/E6 binding errors. Phase A also requires zero correlated false-clean repeat pairs out of 35. The correlated-repeat guardrail is not applicable in single-observation Phase B and is not claimed there.

## 12. Cell transitions

Only the sorted exact set of `A_QUALIFIED_FOR_B` cell IDs may enter Phase B; operator selection is prohibited.

- `A_SCHEDULED` -> `A_BLOCKED` for a precontact blocker.
- `A_SCHEDULED` -> `A_QUALIFIED_FOR_B` only with complete denominator and every A gate passing.
- `A_SCHEDULED` -> `A_FAILED` with complete denominator and any A gate failure.
- `A_SCHEDULED` -> `A_INCOMPLETE` for a frozen incomplete event.
- `A_QUALIFIED_FOR_B` -> `B_SCHEDULED` only through the machine-built conditional schedule.
- `A_FAILED` -> `B_NOT_ELIGIBLE` unconditionally.
- `B_SCHEDULED` -> `FINALLY_QUALIFIED` only with complete denominator and every B gate passing.
- `B_SCHEDULED` -> `B_FAILED_VALIDATION` with complete denominator and any B gate failure.
- `B_SCHEDULED` -> `B_INCOMPLETE` for a frozen incomplete event.

No pooling and no failed-cell reentry are allowed.

## 13. Integrity events and primary verdict

Contract: `g-extract1.integrity-events.v2`.

Precontact blockers are exactly: `PRE_MODEL_IDENTITY_MISMATCH`, `PRE_PROVIDER_VERSION_MISMATCH`, `PRE_GENERATION_CONFIG_MISMATCH`, `PRE_ARTIFACT_DIGEST_MISMATCH`, `PRE_GOLD_DIGEST_MISMATCH`, `PRE_SCORER_DIGEST_MISMATCH`, `PRE_COMPARATOR_DIGEST_MISMATCH`, `PRE_SCHEDULE_DIGEST_MISMATCH`, `PRE_CONTAMINATION_AUDIT_FAILURE`, and `PRE_EXISTING_RUN_COLLISION`.

`INVALID` events are exactly: `PROTECTED_ARTIFACT_DIGEST_MISMATCH`, `GOLD_DIGEST_MISMATCH`, `SCORER_DIGEST_MISMATCH`, `COMPARATOR_DIGEST_MISMATCH`, `MODEL_IDENTITY_MISMATCH_AFTER_CONTACT`, `PROVIDER_VERSION_MISMATCH_AFTER_CONTACT`, `GENERATION_CONFIGURATION_MISMATCH`, `SEED_MISMATCH`, `SCHEDULE_POSITION_MISMATCH`, `DUPLICATE_CALL`, `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, `PROVIDER_FAILURE_WITHOUT_RECEIPT`, `UNAUTHORIZED_RETRY`, `UNAUTHORIZED_FALLBACK`, `UNAUTHORIZED_PROMPT_MUTATION`, `CONTAMINATION_CONTRACT_VIOLATION`, `POST_CONTACT_GOLD_MUTATION`, `POST_CONTACT_GOLD_DEFECT_DISCOVERED`, `POST_CONTACT_FIXTURE_MUTATION`, `POST_CONTACT_THRESHOLD_MUTATION`, `CORRUPTED_CHECKPOINT`, `MISSING_CHECKPOINT_AFTER_INTERRUPTION`, `UNVERIFIABLE_INTERRUPTION_CHECKPOINT`, `UNVERIFIABLE_JOURNAL_PREFIX`, `CORRUPTED_OR_UNPARSEABLE_JOURNAL`, and `PROVENANCE_MISMATCH`.

`INCOMPLETE` events are exactly `PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT`, `PROVIDER_ERROR_WITH_FAILURE_RECEIPT`, `MISSING_RESPONSE_WITH_FAILURE_RECEIPT`, and `MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT`. A sealed interruption requires a present digest-valid checkpoint, reconstructable journal prefix, and exact next schedule position. Missing, corrupt, or unverifiable checkpoints and journal prefixes are their named invalid events. Provider failure without a bound append-only receipt is invalid. Gold mutation and discovery of a pre-existing post-contact gold defect are distinct invalid events. A malformed semantic output is a cell-gate result, not an integrity event. `ABORTED` requires `EXPLICIT_AUTHORIZED_OPERATOR_ABORT`.

Contract `g-extract1.result-state-machine.v3` applies first match and emits exactly one primary verdict:

| Priority | Verdict | Exact predicate |
|---:|---|---|
| 1 | `INVALID` | any enumerated invalid event |
| 2 | `PRE_CONTACT_BLOCKED` | zero provider calls and any enumerated precontact blocker |
| 3 | `ABORTED` | exact authorized abort event |
| 4 | `INCOMPLETE` | any enumerated incomplete event or A/B incomplete cell |
| 5 | `NO_PHASE_A_CELL_QUALIFIED` | Phase A terminal and zero B entrants |
| 6 | `QUALIFICATION_METHOD_FAILED_VALIDATION` | at least one B entrant, zero final qualifiers, B terminal |
| 7 | `MIXED_TARGETED_REQUALIFICATION_SUPPORTED` | at least one final qualifier, at least one B validation failure, B terminal |
| 8 | `TARGETED_REQUALIFICATION_SUPPORTED` | at least one final qualifier, all B entrants qualify, B terminal |

Frozen structured state tests cover precontact mismatch, zero A qualifiers, all/mixed/all-passing B entrants, receipted missing/provider failures, invalid-plus-abort precedence, plain abort, malformed-only cell failure, post-contact gold defect discovery, gold mutation, unreceipted provider failure, unverifiable checkpoint, and incomplete-plus-semantic-failure. The validator evaluates predicates against the fact objects rather than trusting stored expected labels.

Events are emitted only in their defined lifecycle stage. The finite lifecycle must not request a verdict before a terminal predicate exists. A malformed-limit failure is an ordinary semantic cell failure. Secondary diagnostics cannot change the primary verdict.

## 14. Frozen baseline binding

Contract: `g-extract1.baseline-binding.v2`.

The historical behavior source is the frozen G-ROUTE4 execution commit `0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28`.

Exact system text:

`Return one JSON object matching the schema supplied in the fixture. Add no fields. Use only explicit facts; represent an explicitly unstated value with the schema's unknown value.`

The frozen common template is:

`{SUBJECT}. Copy names and identifiers exactly as written in the text, keeping their capitalization and leaving out leading articles and labels such as 'the', 'Order' or 'Vendor'. Use JSON numbers for number fields, whole numbers written without a decimal point for integer fields (5, not 5.0), true or false for boolean fields, strings written as YYYY-MM-DD or HH:MM for fields of those types, and exactly one of the listed values for fields whose type lists values separated by |. Keep the reply compact: output beyond about 350 tokens is cut off.`

Template SHA-256: `ef41104bde4915eba10a5ff1705383cf0b3d72e613fd7af87f72f5b06d2d5579`. The only template placeholder is `{SUBJECT}` and the invariant suffix begins `. Copy names`.

`SUBJECT` is rendered only by the canonical operation catalog. Other variable model-facing data is limited to catalog placeholder identifiers/literals and input object keys exactly `schema` and `text`. Free-form instructions and every prohibited feature in section 4 are forbidden.

Behavioral artifacts are bound by path, SHA-256, and Git blob:

| Role | Path | SHA-256 | Git blob |
|---|---|---|---|
| system profiles | `experiments/G-ROUTE1-candidate/prompt_profiles.json` | `d4a683f1e2f0175006d41c34154e3d4a0e79b22fb70e52b68d93ac2587ae3354` | `365a4a499fd61203ae1bef3cf7d0c65490db529a` |
| request builder | `tools/g_route4_contract.py` | `a1d1de6c77abb9d8240c521b1afda891dbf9b32641df7d84b4f44a442767b45e` | `b86d836d45517d012ad07d417e488e7dc7c3f94d` |
| transport normalization | `tools/g_route2_normalization.py` | `2cca70e0843e90967a33baaf2b7b9a3313de21a6e18c3644c7eb083143398f7d` | `3c73a3856cc1b1ddab9e175486c866a22a380da3` |
| operational wrapper | `tools/g_route3_operational.py` | `4ab2c035b38b5bca5f243ec8aa0c5389e73cfc71cbbedcace3dd2b64f7193df3` | `dbf45f536ef2149d643837593a5fa8251256b5d2` |
| extraction validator | `tools/g_route1_operational.py` | `68abc639c2399a7cd19168c6176d03aa7c3fa81a02b0e85fac2d4fdcf4c7ed70` | `bb5dbcdc9d2817bd7a7a6525aec6b0f5999237c2` |
| semantic reference | `tools/g_route3_semantics.py` | `6e80f13b326d25743778e37635192809e8f5a53de2a98fd973c033075ea90a3e` | `3786140bf04481eb85fe5793013bd4ad923895c9` |
| evaluator reference | `tools/g_route1_validators.py` | `3661ffa5a43c2ea89d7f0d3dd6a7d3d3620f2d4a3a2c0ef943e70de53d4ddf2f` | `a42d5046485530ab59b5c0b478e132b638fb7ab6` |
| model binding | `experiments/G-ROUTE4-candidate/model_bindings.json` | `e87e26c40f014a8d58e242082384db382b0b4942902e6d9bd387f24d68859e36` | `43996490276df5c7e89da0a62a1a0c14fbb8c3da` |
| blueprint source | `experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json` | `f005056f967a43af9a821849c63544dd1165fca083ecd1f394a3e19656fee815` | `c0db2bf9eb09dc8a0be518efe67766486df63bbb` |

The G-EXTRACT1 semantic scorer and exact-value comparator remain evaluator-only unimplemented identities. They must be separately implemented, audited, and digest-bound before contact.

## 15. Model, provider, sampling, and efficiency

Provider is Ollama `0.34.3`.

| Tier | Model | Manifest digest | Blob SHA-256 |
|---|---|---|---|
| small | `qwen2.5:7b` | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` |
| mid | `qwen3:14b` | `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8` | `a8cc1361f3145dc01f6d77c6c82c9116b9ffe3c97b34716fe20418455876c40e` |
| large | `qwen3.8:27b` | `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643` | `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` |

Generation: context 8192, output cap 350, temperature 0.45, top-p 0.9, top-k 40, repeat penalty 1.1, thinking off, streaming off, fresh session each call, zero retry, zero repair, zero fallback. Ollama does not attest internal option honoring.

Phase A seed base is 610000; Phase B is 620000. Seed is `base + zero_based_fixture_index * 10 + one_based_repeat`. Global collision audit and balanced model order are required. The legacy-sized first eight observations per cell are reported only and never gate.

Maximum calls are 420 + 210 = 630, a 54.8387% reduction from 1,395. Estimated active time is 2.79 hours A, 1.40 hours B, 4.19 maximum; large-tier maximum 210 calls and about 2.99 hours. These estimates use preserved means of 7.6, 13.0, and 51.2 seconds and are not guarantees.

## 16. Repair boundary, integration, and governance

G-EXTRACT1 measures the unchanged baseline first. Prompt tuning is prohibited. Any prompt repair requires a new experiment identity and fresh development/scored corpora; repaired and baseline results cannot be pooled.

No result automatically edits a table or enables production routing. A later operator-authorized candidate overlay may contain only finally qualified structured-extraction R2/R3 cells; non-extraction rows remain byte-identical. No qualifier means no update. A shared-logic change requires broader revalidation.

Before any provider contact, fixture, reserve, gold, gate, prompt, scorer/comparator, schedule, contamination report, and adjudication artifacts must be frozen. Failed attempts are append-only. There is no post-contact gold edit, fixture replacement, threshold relaxation, retry, repair, fallback, historical rewrite, autonomy, or belief effect. One local-model research job may run at a time.

Separate explicit authorization is required for blueprint work, fixture/gold authoring, implementation, mechanical pilot, execution freeze, Phase A, and conditional Phase B.

## 17. Validation claim and next boundary

`validate_design.py` may establish only deterministic document structure, bound constants, artifact identities, and human/machine cross-representation checks. It does not prove scientific validity and does not replace adversarial review.

Before implementation authorization: an independent rereview must find no blocker; human/machine normative equivalence must be reviewed; a separately authorized blueprint must pass; separately authorized authoring must complete all 168 fixtures and gold without provider contact; independent gold/adjudication and two-implementation contamination audits must pass; and implementation, pilot, freeze, Phase A, and Phase B each retain separate authorization boundaries.

Design-candidate verdict: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_4`.
