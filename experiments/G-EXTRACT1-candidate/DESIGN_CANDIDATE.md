# G-EXTRACT1 Design Candidate v3

Status: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_3`

This is a design candidate only. It authorizes no blueprint, fixture or reserve authoring, implementation, provider contact, pilot, freeze, Phase A, Phase B, routing update, or belief change.

## 1. Identity and historical boundary

- Experiment: `G-EXTRACT1`, Prospective Structured-Extraction Requalification and Generalization Test.
- Design contract: `g-extract1.design-candidate.v3`.
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

All 140 scored fixtures and 28 one-to-one reserves, all gold, both schedules, and all gates must be frozen before first provider contact. Phase A and Phase B evidence is never pooled. Phase B is zero calls when no Phase A cell qualifies.

## 4. Canonical operation-definition catalog

Contract: `g-extract1.operation-definitions.v1`.

Every scored or reserve fixture renders the model-facing subject from this finite catalog. Authors may vary source facts, field identifiers, literals, record type, and schema, but not instructional wording or helpfulness.

Field identifiers match `^[a-z][a-z0-9_]{0,47}$`. Record types match `^[a-z]+(?: [a-z]+){0,3}$`. The opening sentence is exactly:

`Extract the {record_type} record.`

A fixture has one or two operation nodes. Each node renders as exactly one sentence. Nodes use stable topological order, then unsigned UTF-8 byte order of target field. A two-operand list uses `A and B`; a longer list uses comma-space separators plus `and ` before the final operand. Metadata order is immutable.

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

## 5. Metadata-derived primary families

Contract: `g-extract1.family-assignment.v1`.

Each fixture freezes these mechanically derived metadata fields: `unresolved_required_field_count` (0 or 1), `unknown_sentinel_available`, `entity_record_count` (zero or more), `entity_disambiguation_required`, `terminal_operation`, sorted unique `source_operation_types`, `output_role_type`, `threshold_operator`, `temporal_operation`, `aggregation_operation`, `entity_selector_role`, `source_fact_sequence`, and `direct_copy_only`. `entity_selector_role` is `NONE` without `ENTITY_FIELD_BIND`, otherwise the frozen selector-field schema role `IDENTIFIER`, `ATTRIBUTE`, or `EVENT_ROLE`. `source_fact_sequence` contains one `[zero_based_sentence_index, role, entity_index]` entry per source sentence in byte order; roles are `TARGET`, `SUPPORT`, `DISTRACTOR`, and `EXPLICIT_ABSENCE`, and entity index is -1 when none applies.

`unknown_sentinel_available` is true exactly when a schema value is `provided|not_provided`. `entity_disambiguation_required` is true exactly when at least two named records expose the selected source field and `ENTITY_FIELD_BIND` selects one through a distinct selector field/value. `direct_copy_only` is true exactly when every node is `EXACT_COPY`.

The primary family is the first matching predicate:

| Priority | Family | Mechanical predicate |
|---:|---|---|
| 1 | E7 | `unresolved_required_field_count == 1` and `unknown_sentinel_available == true` |
| 2 | E5 | `entity_disambiguation_required == true` |
| 3 | E4 | terminal operation in `GT,GTE,LT,LTE,EQ` |
| 4 | E1 | terminal operation is `CALENDAR_DAY_OFFSET` |
| 5 | E2 | terminal operation in `CLOCK_MINUTE_OFFSET,ELAPSED_MINUTES` |
| 6 | E3 | terminal operation in `ADD,SUBTRACT,MULTIPLY,DIVIDE,SUM,COUNT,UNIT_CONVERSION` |
| 7 | E6 | terminal operation in `ENTITY_FIELD_BIND,EXACT_COPY` |

No match is an authoring error. Multiple matches use first-match priority. Difficulty, importance, author intent, and a supposed principal challenge are not inputs. Secondary tags are separately frozen from: calendar date, clock time, elapsed time, aggregation, unit conversion, threshold, equality boundary, entity binding, field binding, exact copy, multi-step, and ambiguity.

## 6. Composed-feature coverage

Per phase and round, eight distinct fixtures are reserved for four non-overlapping quota rows, two fixtures each:

1. C1: E4 terminal comparison fed by `ADD,SUBTRACT,MULTIPLY,DIVIDE,SUM,COUNT`, or `UNIT_CONVERSION`.
2. C2: E4 terminal comparison fed by calendar or clock/elapsed operation, with at least one calendar and one clock/elapsed fixture.
3. C3: E3 terminal numeric operation tagged field binding or exact copy.
4. C4: E5 with terminal `ENTITY_FIELD_BIND` and field-binding tag.

These fixtures count toward their primary-family quotas. One fixture cannot satisfy multiple composed rows. The requirement is compatible with 35 fixtures because E4 supplies four of its five fixtures, E3 supplies two of five, E5 supplies two of five, and the rows are distinct.

## 7. Ambiguity and nonacceptance

Contract: `g-extract1.ambiguity-scoring.v2`.

E7 measures semantic ambiguity recognition and operational containment separately. Each E7 fixture has exactly one unresolved required field, at least two supported fields, exact unresolved schema type `provided|not_provided`, and source text explicitly saying the value was not provided. No family-specific instruction is permitted.

The classifier uses only observable fields: infrastructure event, provider truncation, raw byte length, JSON parse success, object root, operational schema validity, exact sentinel equality, supported-field equality, and operational acceptance. First match wins:

| Priority | Outcome | Mechanical condition | Semantic credit | Safe containment |
|---:|---|---|---|---|
| 1 | `infrastructure_missing` | infrastructure event | no | unknown; observation is insufficient |
| 2 | `provider_truncated` | provider marks truncation | no | exactly when not operationally accepted |
| 3 | `empty_output` | zero raw bytes | no | yes |
| 4 | `json_parse_failure` | JSON parse fails | no | yes |
| 5 | `non_object_root` | parsed root is not object | no | yes |
| 6 | `schema_invalid` | operational schema invalid | no | yes |
| 7 | `exact_valid_not_provided` | sentinel exact and every supported field exact | yes | yes |
| 8 | `exact_valid_unsupported_value` | unresolved value is not exact sentinel | no | no; false-clean |
| 9 | `exact_valid_supported_field_error` | supported field differs from gold | no | no; false-clean |

Priority 8 precedes 9 when both defects exist. After priorities 1-6, the two Boolean equality tests make priorities 7-9 exhaustive. Prose-only output is `json_parse_failure`; no refusal intent is inferred. Omission, null, wrong sentinel, wrong type, duplicate key, or extra field is `schema_invalid`. Omitting only the ambiguous field or returning only supported fields gets no semantic credit. Unsupported filling is false-clean. A valid sentinel with any supported-field error is false-clean.

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
- Parsing preserves duplicate-key evidence, parses numeric tokens as exact decimals, and treats invalid JSON leading zeroes as malformed.

## 9. Contamination and fingerprint algorithms

Contract: `g-extract1.contamination.v1`.

Authored model-facing text is limited to printable ASCII plus CR, LF, and TAB. Every other code point is rejected before fixture freeze. Historical comparison covers all G-ROUTE4 extraction scored and reserve corpora.

Similarity payload is constructed only as `input.text + LF + canonical_schema_serialization`; no prompt substrings are removed afterward. Schema serialization sorts keys by unsigned UTF-8 bytes and emits `field=type` lines with LF separators and no terminal LF. The excluded request spans are the entire UTF-8 `request.system`, the entire UTF-8 `request.prompt` (opening, operations, absence sentence, and common suffix), and exact `request.input_marker` bytes `INPUT` followed by LF.

Normalization is exact: Unicode NFC; default Unicode casefold; CRLF/CR to LF; every maximal Unicode whitespace run to one ASCII space; trim ends; entities receive no anonymization; canonical schema is appended before normalization. Punctuation is not rewritten before tokenization. The tokenizer skips unmatched punctuation, leaving signs, decimal points, and exponent signs available to its numeric alternative so complete numeric tokens survive.

Tokenization uses Python `re` in ASCII mode with:

`[+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?|[a-z][a-z0-9]*(?:_[a-z0-9]+)*`

Matches are left-to-right non-overlapping `finditer`; an empty sequence is invalid. Token 5-grams are contiguous tuples at each offset, deduplicated into sets. Jaccard is intersection size divided by union size; both empty is 1.0 and only one empty is 0.0. Every compared pair must be strictly below 0.20.

The fingerprint is a UTF-8 JSON array in this component order, compact separators, no whitespace or terminal LF:

1. `operation_graph`: stable-topologically sort nodes, choosing the unsigned UTF-8-lowest target among ready nodes. Emit `[operation_id, operand_kind_array, dependency_index_array]`; operand kinds follow catalog placeholder order with target omitted, and dependencies are sorted unique zero-based result indices. Names and literal values are excluded. Operand kinds are source field, derived field, literal, collection, or entity selector.
2. `output_schema_roles`: emit one `[schema_type, role]` pair per output field, retaining duplicate pairs, then sort compact pair bytes unsigned. Role comes from the producing operation, or source copy when untransformed. Roles are source copy, derived number/Boolean/date/time, entity-bound value, or absence sentinel.
3. `entity_role_graph`: `NONE` for zero records; `SINGLE_ENTITY` for one; `MULTI_ENTITY_NO_DISAMBIGUATION` for multiple records without disambiguation; otherwise map `entity_selector_role` to `MULTI_ENTITY_SELECT_BY_IDENTIFIER`, `_ATTRIBUTE`, or `_EVENT_ROLE`.
4. `boundary_relation`: `NONE` without terminal comparison; otherwise evaluate exact left/right gold operands and emit `BELOW`, `EQUAL`, or `ABOVE` from left compared with right.
5. `temporal_pattern`: `NONE` without temporal operation. Clock/elapsed emits `MIDNIGHT_ROLLOVER` exactly when the forward result crosses midnight, else `SAME_DAY_FORWARD`. Calendar offset emits `LEAP_DAY_BOUNDARY` when inclusive traversal contains February 29, else `YEAR_BOUNDARY` when years differ, else `MONTH_BOUNDARY` when months differ, else `DATE_WITHIN_MONTH`.
6. `source_fact_layout`: first match over `source_fact_sequence`: any explicit absence; alternating target/support entries for two or more entities after dropping distractors; one or more distractors all before target/support; one or more distractors all after target/support; one or more supports all after first target; otherwise at most one entity with contiguous target/support facts. Failure of that final condition is an authoring error. The corresponding values are `EXPLICIT_PARTIAL_ABSENCE`, `INTERLEAVED_MULTI_ENTITY`, `DISTRACTOR_BEFORE_TARGET`, `DISTRACTOR_AFTER_TARGET`, `TARGET_BEFORE_SUPPORTING_FACTS`, and `CONTIGUOUS_SINGLE_ENTITY`.

Pairwise comparison includes every historical G-ROUTE4 extraction fixture against every G-EXTRACT1 scored/reserve fixture, A/A, A/B, B/B, every scored/reserve pair, and reserve/reserve. Exact normalized payload, answer, entity/identifier, or date-number tuple reuse is prohibited. Historical versus new, A versus B, primary versus mapped reserve, and reserve versus reserve exact fingerprint collisions are prohibited. Within one phase/round/family, an exact fingerprint may occur at most twice only below Jaccard 0.12 with all entities and values different. A pair matching at least five of six fingerprint components at Jaccard at least 0.12 is a prohibited near replay. Recurrence of the same abstract failure class or operation ID is permitted.

Before freeze, two independently implemented fingerprint/similarity computations must agree byte-for-byte, an automated all-pairs report must pass, and a blind human contamination review must pass. Lineage labels alone prove nothing.

## 10. Gold, adjudication, and reserves

Determinate gold freezes typed canonical values, independent derivation, binding map, determinacy proof, primary family, secondary features, operation metadata, and rationale. E7 gold freezes the one unresolved field, exact `not_provided` sentinel, supported values, and explicit-absence proof.

Reviewer A solves without proposed gold. Reviewer B audits arithmetic, calendar semantics, bindings, family assignment, and exact-value compliance. Preserved disagreements are resolved by an operator-approved adjudicator before provider contact. Fixture, gold, reserve, equivalence, and adjudication freeze together. A gold defect after contact invalidates the affected run; it is not repaired in place.

Contract `g-extract1.reserve-activation.v2` provides exactly one reserve for every phase x round x primary-family slot. Mapping is frozen; no selection pool exists. Activation is allowed only before provider contact for a mechanical schema defect, unresolved gold/adjudication defect, contamination/fingerprint failure, duplicate entity/date/number tuple, quota/signature violation, or corpus-level similarity failure. Style preference, anticipated or observed model behavior, and gate improvement are ineligible.

A reserve must match phase, round, primary family, composed-quota row, required secondary features, field types, operator/boundary, ambiguity status, and risk. It must preserve every composed quota. Activation invalidates the candidate freeze and requires full review/digest rebuild. If the mapped reserve fails, authoring stops. Ad hoc and post-contact replacement are prohibited.

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

Contract: `g-extract1.integrity-events.v1`.

Precontact blockers are exactly: `PRE_MODEL_IDENTITY_MISMATCH`, `PRE_PROVIDER_VERSION_MISMATCH`, `PRE_GENERATION_CONFIG_MISMATCH`, `PRE_ARTIFACT_DIGEST_MISMATCH`, `PRE_GOLD_DIGEST_MISMATCH`, `PRE_SCORER_DIGEST_MISMATCH`, `PRE_COMPARATOR_DIGEST_MISMATCH`, `PRE_SCHEDULE_DIGEST_MISMATCH`, `PRE_CONTAMINATION_AUDIT_FAILURE`, and `PRE_EXISTING_RUN_COLLISION`.

`INVALID` events are exactly: `PROTECTED_ARTIFACT_DIGEST_MISMATCH`, `GOLD_DIGEST_MISMATCH`, `SCORER_DIGEST_MISMATCH`, `COMPARATOR_DIGEST_MISMATCH`, `MODEL_IDENTITY_MISMATCH_AFTER_CONTACT`, `PROVIDER_VERSION_MISMATCH_AFTER_CONTACT`, `GENERATION_CONFIGURATION_MISMATCH`, `SEED_MISMATCH`, `SCHEDULE_POSITION_MISMATCH`, `DUPLICATE_CALL`, `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, `UNAUTHORIZED_RETRY`, `UNAUTHORIZED_FALLBACK`, `UNAUTHORIZED_PROMPT_MUTATION`, `CONTAMINATION_CONTRACT_VIOLATION`, `POST_CONTACT_GOLD_MUTATION`, `POST_CONTACT_FIXTURE_MUTATION`, `POST_CONTACT_THRESHOLD_MUTATION`, `CORRUPTED_OR_UNPARSEABLE_JOURNAL`, and `PROVENANCE_MISMATCH`.

`INCOMPLETE` events are exactly `PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT`, `PROVIDER_ERROR_WITH_FAILURE_RECEIPT`, `MISSING_RESPONSE_WITH_FAILURE_RECEIPT`, and `MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT`. An unreceipted omission is invalid. An unverifiable checkpoint is invalid. A malformed semantic output is a cell-gate result, not an integrity event. `ABORTED` requires `EXPLICIT_AUTHORIZED_OPERATOR_ABORT`.

Contract `g-extract1.result-state-machine.v2` applies first match and emits exactly one primary verdict:

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

Frozen state tests resolve as follows: precontact artifact mismatch -> `PRE_CONTACT_BLOCKED`; zero A qualifiers -> `NO_PHASE_A_CELL_QUALIFIED`; all B entrants fail -> `QUALIFICATION_METHOD_FAILED_VALIDATION`; mixed B pass/fail -> `MIXED_TARGETED_REQUALIFICATION_SUPPORTED`; all B entrants pass -> `TARGETED_REQUALIFICATION_SUPPORTED`; missing B response with receipt -> `INCOMPLETE`; integrity violation after partial execution -> `INVALID`; authorized abort without a higher-priority event -> `ABORTED`; complete Phase A with every cell failing only the malformed gate -> `NO_PHASE_A_CELL_QUALIFIED`; provider error with receipt -> `INCOMPLETE`; post-contact gold mutation -> `INVALID`; and unreceipted scheduled-call omission -> `INVALID`.

Events are emitted only in their defined lifecycle stage. The finite lifecycle must not request a verdict before a terminal predicate exists. A post-contact gold defect is invalid. A malformed-limit failure is an ordinary semantic cell failure. Secondary diagnostics cannot change the primary verdict.

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

Design-candidate verdict: `READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_3`.
