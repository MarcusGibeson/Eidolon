# G-EXTRACT1: Prospective Structured-Extraction Requalification

Status: **REVISED DESIGN CANDIDATE - INDEPENDENT REREVIEW REQUIRED**

Execution status: **not implemented, not frozen, not authorized, not running**

Provider generation calls: **0**

Belief effects: **none**

Normative contract IDs:

- design: `g-extract1.design-candidate.v2`
- ambiguity scoring: `g-extract1.ambiguity-scoring.v1`
- exact-value comparison: `g-extract1.exact-value-comparator.v1`
- result state machine: `g-extract1.result-state-machine.v1`
- reserve activation: `g-extract1.reserve-activation.v1`
- baseline binding: `g-extract1.baseline-binding.v1`

## 1. Governed origin and identity

**Experiment ID:** `G-EXTRACT1`

**Name:** Prospective Structured-Extraction Requalification and Generalization Test

This is a new experiment. It is not a rescore, repair, continuation, or reopening of G-ROUTE4. G-ROUTE4 remains
historically **FAILED** at evidence commit `c95d2d1a4177c0f6a33bb8ffb772dfc19c272646`.

Historical context is bound read-only:

- `G_ROUTE4_CLOSURE.json`, SHA-256
  `d992a169a2be293909f0fe0f1b39720656f40a09dc4f6b4e9c53449110cef8be`;
- `PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json`, SHA-256
  `461a85368a6cbbd39429bebbae883c0b17be614db52e343150b23051041b4868`.

Historical prompts, answers, and gold are not scored inputs. The diagnostic contributes only the prospective failure
classes: eight date/time errors, five numeric/threshold errors, and one entity-binding error.

## 2. Research question and causal limit

> Under the byte-bound G-ROUTE4 extraction system prompt, prompt renderer, transport normalization, and operational
> validator, can a larger family-stratified qualification test identify R2/R3 model-tier cells that retain safe and
> useful behavior on a separately authored validation corpus, without false-clean extraction errors?

The experiment tests whether broader prospective sampling and coverage would have exposed the observed classes of
failure. It does not separately identify prompt wording, model weights, provider internals, or stochastic sampling as
the cause. Confidence bounds are benchmark decision statistics under the frozen authored-fixture design, not estimates
of performance in an undefined natural population.

## 3. Prospective hypotheses

- **H1:** At least one G-ROUTE4-qualified extraction cell will fail the larger Phase A gate.
- **H2:** Date/time and numeric/threshold families will produce more errors than entity/binding families. This is
  descriptive and never changes a gate.
- **H3:** Some wrong answers will recur across both Phase A repeats. Repeats measure within-fixture stability and are
  never counted as independent fixtures.
- **H4:** Qualification is cell-specific and need not be monotonic with parameter count.
- **H5:** A Phase A-qualified cell must independently pass a fresh Phase B corpus. Phase A and B are never pooled.

## 4. Scope

In scope:

- structured extraction only;
- risk rounds `R2` and `R3`;
- tiers `small`, `mid`, and `large`, for six cells;
- calendar dates, clock time, elapsed time, arithmetic, in-scope units, threshold/equality relations, entity and field
  binding, exact values, ambiguity, malformed outputs, and repeat-stable errors.

Out of scope:

- all other task classes, R1 promotion, R4 routing, timezone conversion, production routing, prompt repair, model
  installation, source modification, and belief effects.

R2 and R3 retain the frozen G-ROUTE4 consequence meanings: R2 is costly but reversible money/order/booking/workplace
administration; R3 is security/privacy/compliance/access with possible data exposure or access consequences. Surface
difficulty cannot substitute for consequence risk.

## 5. Cells and phases

The six candidate cells are `R2` and `R3` crossed with the three frozen model tiers.

### Phase A - prospective requalification

- 35 distinct fixtures per round, 70 total;
- five fixtures from each E1-E7 family per round;
- two repeats per fixture and model;
- all six cells run;
- 420 calls: `70 fixtures x 2 repeats x 3 models`.

Phase A can only produce eligibility for Phase B. It cannot produce final qualification or routing authority.

### Phase B - independent fresh validation

- separately authored and adjudicated 35 fixtures per round, 70 total;
- one observation per fixture and eligible cell;
- only machine-derived Phase A PASS cells enter;
- zero calls when no Phase A cell passes;
- maximum 210 calls: `70 fixtures x 3 models`.

All Phase B fixtures and reserves are complete and frozen before the first Phase A provider call. Phase A outcomes may
select cells, but may not change Phase B fixtures, gold, schedule positions, gates, prompts, or scoring.

## 6. Corpus counts

| Artifact | R2 | R3 | Total |
|---|---:|---:|---:|
| Phase A scored fixtures | 35 | 35 | 70 |
| Phase B scored fixtures | 35 | 35 | 70 |
| Phase A reserves | 7 | 7 | 14 |
| Phase B reserves | 7 | 7 | 14 |
| Total authored before contact | 84 | 84 | 168 |

No fixture or gold item is authored in this design revision.

## 7. Primary families and deterministic assignment

Every fixture has exactly one immutable `primary_family` and zero or more `secondary_features`. Assignment follows the
first matching rule below; it is frozen before contact and cannot change after model output exists.

| Priority | Family | Exact primary-assignment rule |
|---:|---|---|
| 1 | E7 ambiguity and partial evidence | At least one required field lacks one supported value or binding and the schema exposes the frozen `unknown` sentinel for that field. |
| 2 | E5 entity binding and disambiguation | The main challenge is selecting or preserving the correct record among at least two named entities with comparable fields. |
| 3 | E4 threshold and equality semantics | The principal scored derivation is a literal `>`, `>=`, `<`, `<=`, or equality decision, including a decision fed by arithmetic or date/time calculation. |
| 4 | E1 calendar-date arithmetic | The principal scored derivation produces a calendar date through exact day arithmetic. |
| 5 | E2 clock and elapsed-time arithmetic | The principal scored derivation produces a clock time or elapsed duration, including midnight rollover. |
| 6 | E3 numeric aggregation and in-scope units | The principal scored derivation is arithmetic, aggregation, rate, count, or an explicitly defined same-dimension conversion. |
| 7 | E6 field/value and exact-value binding | The principal challenge is exact source-to-field binding or copying and none of E7-E3 has priority. |

Primary quotas remain five fixtures per family per phase/round. Secondary tags include `calendar_date`, `clock_time`,
`elapsed_time`, `aggregation`, `unit_conversion`, `threshold`, `equality_boundary`, `entity_binding`, `field_binding`,
`exact_copy`, `multi_step`, and `ambiguity`.

### Required composed features

Each phase/round must contain eight distinct composed fixtures, two in each row. A fixture may satisfy only one of
these quota rows, although all its secondary features remain recorded.

| Required crossing | Primary family | Required secondary feature | Minimum distinct fixtures |
|---|---|---|---:|
| arithmetic -> threshold/equality | E4 | E3 `aggregation` | 2 |
| date/time -> threshold/equality | E4 | E1 or E2 | 2, including at least one date and one time case |
| aggregation -> exact-value binding | E3 | E6 `field_binding` or `exact_copy` | 2 |
| entity -> field/value binding | E5 | E6 `field_binding` | 2 |

These are fresh constructions, not replays of G-ROUTE4 cases. They count normally toward their primary-family quota.

## 8. Ambiguity and nonacceptance contract

E7 measures two separate concepts:

1. **semantic ambiguity recognition** - a structurally valid object uses the exact schema-provided `unknown` sentinel
   only for the unresolved field and correctly extracts every supported field;
2. **operational containment** - no unsupported guessed value is operationally accepted.

Every E7 fixture has exactly one preregistered unresolved required field, at least two supported fields, and an enum
schema for the unresolved field that includes the literal `unknown`. The unchanged system prompt already instructs the
model to use the schema's unknown value. No family-specific or outcome-derived coaching is added.

### Deterministic ambiguity scoring precedence

The first applicable row supplies the primary outcome; flags such as `operationally_accepted` and `false_clean` are
also recorded.

| Priority | Condition | Primary outcome | Semantic credit | Safely contained |
|---:|---|---|---|---|
| 1 | provider/config/provenance failure or missing call | `infrastructure_missing` | no; denominator insufficient | unknown |
| 2 | provider reports output truncation | `truncated` | no | yes only if not operationally accepted |
| 3 | empty output or explicit natural-language refusal | `refusal` | no | yes |
| 4 | JSON parse failure or non-object root | `malformed` | no | yes |
| 5 | object violates schema, omits any field, adds a field, uses null, or has a type error | `structural_nonacceptance` | no | yes |
| 6 | exact schema; unresolved field is `unknown`; all supported fields exactly correct | `correct_ambiguity_recognition` | yes | yes |
| 7 | exact schema; unresolved field is filled with an unsupported value | `guessed_complete_extraction` | no | no; false-clean |
| 8 | exact schema but a supported field is wrong, evasive, or replaced with `unknown` | `accepted_semantic_error` | no | no; false-clean |

Omitting only the ambiguous field or returning only supported fields is `structural_nonacceptance`, not semantic
recognition. Malformed, refused, truncated, structurally invalid, or evasive answers never receive semantic ambiguity
credit. A valid unknown-sentinel object is a correct partial extraction, not a refusal.

Phase A E7 requires all of:

- 5/5 distinct ambiguity fixtures present;
- 10/10 scheduled observations present;
- 10/10 observations `correct_ambiguity_recognition`;
- 10/10 observations safely contained;
- 0 refusals, malformed outputs, truncations, or structural nonacceptances;
- 0 false-clean accepted guesses.

Phase B requires the corresponding 5/5 fixture/observation results. Thus evasion cannot qualify a cell.

## 9. Contamination and independence controls

Phase A, Phase B, and reserves use separately assigned lineage IDs. Phase B is sealed before Phase A contact. Gold,
family, determinacy, gate, historical outcomes, and expected labels are never model-facing.

Prohibited replay is defined deterministically:

- normalized exact payload, answer, entity, identifier, date tuple, and numeric tuple reuse: zero;
- token 5-gram Jaccard after frozen boilerplate removal must be `< 0.20` against every G-ROUTE4 extraction fixture;
- exact `full_case_fingerprint` collision is prohibited. The fingerprint contains operation graph, output-schema roles,
  entity-role graph, boundary relation, temporal pattern, and source-fact layout;
- a near replay is prohibited when at least five of those six components match one historical fixture and payload
  5-gram Jaccard is `>= 0.12`;
- Phase A and B may share a failure class or operation graph, but may not share an exact full-case fingerprint;
- reuse of a reasoning class is explicitly permitted when at least two non-operation fingerprint components differ,
  lexical limits pass, and all values/entities are fresh.

These rules permit fresh date-addition and threshold cases while prohibiting renamed copies. Automated reports and a
blind human contamination review are both required. Separate lineage labels alone are not evidence of independence.

## 10. Exact-value and normalization contract

The model-facing operational validator remains byte-bound to G-ROUTE4. The evaluator-only comparator uses contract
`g-extract1.exact-value-comparator.v1` and never changes operational acceptance.

| Type | Frozen comparison rule |
|---|---|
| integer | JSON lexical integer only; `5` passes, `5.0` and `5e0` fail. `-0` is equivalent to `0`. This matches baseline structural acceptance. |
| number | Exact decimal value; `5`, `5.0`, `5.00`, and `5e0` are equivalent. No binary-float tolerance. |
| units | No implicit conversion or spelling normalization. A conversion is allowed only when its exact formula and target unit are stated in the fixture. Unit-bearing strings match exactly; omission fails. |
| strings/entities | Exact Unicode scalar sequence, case, whitespace, and punctuation. No Unicode normalization, trimming, aliasing, abbreviation, or case folding. |
| entity labels | Only exact leading `the`, `Order`, or `Vendor`, followed by one space, may be removed when the fixture uses the common frozen copy rule. Full remaining names are required. |
| JSON objects | Key order and insignificant JSON whitespace are ignored recursively. Duplicate keys, extra keys, omitted keys, and null values are invalid. |
| arrays/nested values | Arrays and nested values are outside the baseline extraction schema and prohibited in scored fixtures. |
| dates | Exact zero-padded `YYYY-MM-DD`; month names and other formats fail. Proleptic Gregorian calendar; start date is day zero for `+N days`. |
| times | Exact zero-padded 24-hour `HH:MM`; 12-hour forms and AM/PM fail. Midnight rollover must be explicit. |
| thresholds | `>`, `>=`, `<`, `<=`, and equality are literal; equality-boundary fixtures are prospectively balanced. |

The semantic parser must preserve duplicate-key evidence and parse JSON numbers as exact decimal tokens. Leading-zero
numbers invalid under JSON are malformed. The operational parser remains unchanged even where it is less strict; an
operationally accepted but semantically invalid value is false-clean.

## 11. Gold and adjudication

Gold is classified before contact as `determinate` or `ambiguous_nonaccept`. Determinate gold contains canonical typed
values, derivation, binding map, determinacy proof, family/features, and rationale. E7 gold identifies the unresolved
field, exact `unknown` sentinel, supported-field values, and why no factual value is supported.

Authoring review:

1. Author produces fixture, independent derivation, gold, rationale, fingerprint, and reserve mapping.
2. Reviewer A solves blind to proposed gold.
3. Reviewer B audits arithmetic, calendar semantics, bindings, family assignment, and exact-value compliance.
4. Disagreements are preserved and resolved by an operator-approved adjudicator before contact.
5. All fixtures, gold, reserves, equivalence rules, and adjudication records freeze together.
6. A gold defect found after contact invalidates the affected run; gold is never repaired in place.

## 12. Reserve activation policy

Contract `g-extract1.reserve-activation.v1` permits exactly one reserve for every phase x round x primary-family slot.
The mapping is frozen before review. There is no pool from which an author may choose.

A reserve may activate only before provider contact when the mapped primary fixture has a documented mechanical schema
defect, unresolved gold/adjudication defect, contamination/fingerprint failure, duplicate entity/date/number tuple, or
quota/signature violation. Corpus-level similarity failure is eligible. Style preference or anticipated model behavior
is not eligible.

Activation invalidates any candidate corpus/gold freeze. The sole mapped reserve must match phase, round, primary
family, secondary-feature obligations, field types, operator/boundary type, ambiguity status, and consequence risk.
It receives full independent gold and contamination review, then all affected digests are rebuilt. If it fails, the
authoring campaign stops; no ad hoc replacement is created. Replacement after any provider contact is forbidden.

## 13. Analysis units and gate interpretation

Units are observation, distinct fixture, repeat pair, family, and model-tier x risk-round cell. Primary bounds use
distinct fixtures only. Repeats are paired stability evidence.

Clopper-Pearson values are retained as **benchmark decision statistics under the frozen authored-fixture design**.
They are not population-generalization estimates because fixtures are stratified and not random IID draws.

### Phase A independent pass gates

- denominator integrity: 70/70 observations, 35/35 fixtures, 35/35 repeat pairs, no duplicates;
- family coverage: exactly 5/5 in each E1-E7 family and all composed-feature quotas;
- false-clean: 0/35 affected fixtures and 0/70 observations; decision statistic upper bound `0.082032 <= 0.10`;
- determinate semantic correctness: at least 29/30 fixtures with both repeats correct; lower statistic `0.851404`;
- determinate structural validity: at least 29/30 fixtures with both repeats valid;
- useful correct acceptance: at least 27/30 fixtures with both repeats accepted and correct; lower statistic `0.761402`;
- E7 ambiguity recognition and containment: all requirements in section 8;
- malformed determinate fixtures: at most 1/30 and structural gate must pass.

The following remain enforced named **redundant pass guardrails** rather than independent statistical evidence:

- E1-E6 family semantic floor `>=4/5`; 29/30 already implies it, but it detects family attribution/denominator defects;
- accepted E5/E6 binding errors `0`; zero false-clean already implies it, but it provides explicit binding reporting;
- correlated false-clean repeat pairs `0/35`; zero false-clean already implies it, but it exposes repeated wrong agreement.

### Phase B gates

Phase B applies the same fixture-level gates to 35 fresh observations: 35/35 denominator, five/family plus composed
quotas, 0/35 false-clean, >=29/30 determinate semantic and structural validity, >=27/30 useful correct acceptance,
the redundant guardrails, <=1 malformed determinate fixture, and 5/5 correct E7 recognition and containment.

A completed semantic gate failure is FAIL, not insufficient. Insufficient is limited to missing or untrustworthy
denominators caused by provider, configuration, provenance, or call-state failure.

## 14. Cell state machine and Phase A -> B carry-forward

| Current state | Deterministic condition | Next state |
|---|---|---|
| `A_SCHEDULED` | protected preflight fails before contact | `A_BLOCKED` |
| `A_SCHEDULED` | complete denominator and every A gate passes | `A_QUALIFIED_FOR_B` |
| `A_SCHEDULED` | complete denominator and any A gate fails | `A_FAILED` |
| `A_SCHEDULED` | missing/untrustworthy denominator | `A_INCOMPLETE` |
| `A_QUALIFIED_FOR_B` | exact cell appears in machine-built conditional schedule | `B_SCHEDULED` |
| `A_FAILED` | always | `B_NOT_ELIGIBLE` |
| `B_SCHEDULED` | complete denominator and every B gate passes | `FINALLY_QUALIFIED` |
| `B_SCHEDULED` | complete denominator and any B gate fails | `B_FAILED_VALIDATION` |
| `B_SCHEDULED` | missing/untrustworthy denominator | `B_INCOMPLETE` |

The Phase B selector is the sorted exact set of `A_QUALIFIED_FOR_B` cell IDs. Operator selection, omission, addition,
or substitution is invalid. A failed cell never re-enters. No A/B pooling is permitted.

## 15. Deterministic experiment result state

Exactly one primary verdict is selected by first-match precedence:

| Precedence | Primary verdict | Exact predicate |
|---:|---|---|
| 1 | `INVALID` | protected artifact, gold, blindness, scorer, configuration, contamination, schedule, or denominator-integrity contract is violated after execution begins, or a result cannot be trusted |
| 2 | `BLOCKED_CONFIGURATION_MISMATCH` | pre-contact model/provider/configuration/artifact mismatch prevents all provider contact |
| 3 | `ABORTED` | operator-authorized abort ends an otherwise valid run before the frozen schedule completes |
| 4 | `INCOMPLETE` | no higher state applies and required calls/evidence are missing or unprovable |
| 5 | `NO_PHASE_A_CELL_QUALIFIED` | Phase A completes validly and zero cells enter Phase B |
| 6 | `QUALIFICATION_METHOD_FAILED_VALIDATION` | at least one cell enters B and zero cells finally qualify |
| 7 | `MIXED_TARGETED_REQUALIFICATION_SUPPORTED` | at least one cell finally qualifies and at least one other B entrant fails validation |
| 8 | `TARGETED_REQUALIFICATION_SUPPORTED` | at least one cell finally qualifies and every B entrant passes |

Malformed-limit failure is a semantic cell FAIL, not `INVALID`. Secondary diagnostics report counts of A failures,
B failures, malformed outputs, false-clean events, and final cells; they cannot alter the primary verdict.

## 16. Baseline prompt and evaluator binding

Contract `g-extract1.baseline-binding.v1` binds the source commit
`4484500de7a7d35e534b1f3884906b6749a213b9` as the design provenance and these existing behavior artifacts:

| Role | Path | SHA-256 | Git blob |
|---|---|---|---|
| system profiles | `experiments/G-ROUTE1-candidate/prompt_profiles.json` | `d4a683f1e2f0175006d41c34154e3d4a0e79b22fb70e52b68d93ac2587ae3354` | `365a4a499fd61203ae1bef3cf7d0c65490db529a` |
| prompt renderer/request builder | `tools/g_route4_contract.py` | `a1d1de6c77abb9d8240c521b1afda891dbf9b32641df7d84b4f44a442767b45e` | `b86d836d45517d012ad07d417e488e7dc7c3f94d` |
| transport normalization | `tools/g_route2_normalization.py` | `2cca70e0843e90967a33baaf2b7b9a3313de21a6e18c3644c7eb083143398f7d` | `3c73a3856cc1b1ddab9e175486c866a22a380da3` |
| operational wrapper | `tools/g_route3_operational.py` | `4ab2c035b38b5bca5f243ec8aa0c5389e73cfc71cbbedcace3dd2b64f7193df3` | `dbf45f536ef2149d643837593a5fa8251256b5d2` |
| delegated extraction validator | `tools/g_route1_operational.py` | `68abc639c2399a7cd19168c6176d03aa7c3fa81a02b0e85fac2d4fdcf4c7ed70` | `bb5dbcdc9d2817bd7a7a6525aec6b0f5999237c2` |
| historical semantic wrapper | `tools/g_route3_semantics.py` | `6e80f13b326d25743778e37635192809e8f5a53de2a98fd973c033075ea90a3e` | `3786140bf04481eb85fe5793013bd4ad923895c9` |
| historical extraction evaluator | `tools/g_route1_validators.py` | `3661ffa5a43c2ea89d7f0d3dd6a7d3d3620f2d4a3a2c0ef943e70de53d4ddf2f` | `a42d5046485530ab59b5c0b478e132b638fb7ab6` |
| model/config binding | `experiments/G-ROUTE4-candidate/model_bindings.json` | `e87e26c40f014a8d58e242082384db382b0b4942902e6d9bd387f24d68859e36` | `43996490276df5c7e89da0a62a1a0c14fbb8c3da` |
| frozen prompt-template source | `experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json` | `f005056f967a43af9a821849c63544dd1165fca083ecd1f394a3e19656fee815` | `c0db2bf9eb09dc8a0be518efe67766486df63bbb` |

The exact system text is: `Return one JSON object matching the schema supplied in the fixture. Add no fields. Use only
explicit facts; represent an explicitly unstated value with the schema's unknown value.`

The exact structured-extraction assembled template is:

`{SUBJECT}. Copy names and identifiers exactly as written in the text, keeping their capitalization and leaving out leading articles and labels such as 'the', 'Order' or 'Vendor'. Use JSON numbers for number fields, whole numbers written without a decimal point for integer fields (5, not 5.0), true or false for boolean fields, strings written as YYYY-MM-DD or HH:MM for fields of those types, and exactly one of the listed values for fields whose type lists values separated by |. Keep the reply compact: output beyond about 350 tokens is cut off.`

Its SHA-256 is `ef41104bde4915eba10a5ff1705383cf0b3d72e613fd7af87f72f5b06d2d5579`. Only
`{SUBJECT}` is variable; the suffix beginning `. Copy names` is byte-invariant.

The user prompt may vary only in these frozen slots:

1. neutral record-type opening (`Extract the ... record.`);
2. neutral derived-field definitions stating the mathematical or logical operation without worked answers;
3. the exact common G-ROUTE4 copy/type/output-cap boilerplate;
4. fixture `input.text` and `input.schema`.

Forbidden variation includes family names, ambiguity labels, historical failures, expected values, worked examples,
chain-of-thought requests, extra arithmetic hints, model-tier text, risk labels, gold, gates, or outcome-derived
coaching. The blueprint must freeze every variable prompt slot and the exact boilerplate bytes before fixture authoring.

The G-EXTRACT1 semantic scorer and exact-value comparator are evaluator-only future implementations. Their contract
IDs are frozen here; executable paths and SHA-256 values are currently `null` and must be bound and independently
audited before any model contact. They may not alter request construction or operational validation.

## 17. Models, provider, and sampling

Provider: Ollama `0.34.3`.

Models remain exactly:

- small: `qwen2.5:7b`, manifest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`;
- mid: `qwen3:14b`, manifest `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`;
- large: `qwen3.8:27b`, manifest `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.

Generation remains `num_ctx=8192`, `num_predict=350`, `temperature=0.45`, `top_p=0.9`, `top_k=40`,
`repeat_penalty=1.1`, `think=false`, `stream=false`, fresh session, zero retries, zero repairs, and zero fallback.

Candidate seed bases are 610000 for A and 620000 for B, subject to a global collision audit. Phase A uses two
distinct seeds per fixture; Phase B uses one. Model order is balanced and schedules freeze before contact.

## 18. Mathematical and efficiency record

- `0/35` one-sided 95% upper statistic: `0.082031636`;
- `0/30` upper statistic: `0.095033853`;
- `29/30` lower statistic: `0.851403931`;
- `27/30` lower statistic: `0.761402143`;
- Phase A calls: 420;
- maximum Phase B calls: 210;
- maximum total: 630;
- reduction from G-ROUTE4's 1,395 calls: `54.8387%`.

Using preserved mean call latencies (7.6s, 13.0s, 51.2s), Phase A is about 2.79 active hours, maximum Phase B about
1.40 hours, and maximum total about 4.19 active hours. The 27B tier contributes at most about 2.99 hours. These are
planning estimates, not provider guarantees.

## 19. Failure handling and repair boundary

Malformed, truncated, refused, or semantically wrong outputs are preserved without retry. Provider/configuration or
provenance failure yields blocked, insufficient, incomplete, or invalid status according to section 15; semantic gate
failure is a valid result. Failed attempts are append-only.

G-EXTRACT1 never repairs its prompt. A later repair requires a new experiment identity, a separate development corpus,
new independently authored scored corpora, new gold, and new authorization. Baseline and repaired results never pool.

## 20. Integration boundary

Passing G-EXTRACT1 grants evidence only. A later human-reviewed extraction-only table overlay may include only cells
that pass A and B. Non-extraction rows remain byte-identical. A no-provider integration check and separate installation
authorization are required. If no cell qualifies, no table update is created. Shared prompt, validator, comparator,
routing, or persistence changes require broader revalidation.

## 21. Governance and prerequisites

Before implementation authorization:

1. independent adversarial rereview finds no unresolved blocker;
2. the machine and human contracts are proven equivalent;
3. an authoring blueprint freezes every slot, feature crossing, prompt slot, fingerprint, reserve mapping, and risk;
4. all 168 fixtures/reserves and gold are authored and frozen without provider contact;
5. independent gold/adjudication and contamination audits pass;
6. baseline artifact hashes and model metadata are reverified without generation;
7. evaluator implementations receive separate authorization and adversarial audit;
8. a mechanical pilot receives separate design and authorization;
9. an execution freeze binds all behaviorally relevant artifacts with execution flags false;
10. Phase A and conditional Phase B each require separate explicit authorization.

Standing rules: no post-contact fixture or gold change, no threshold loosening, no historical rewrite, one local-model
research job at a time, reviewer outputs non-authoritative, no autonomy, and belief effects `none`.

## 22. Remaining non-blocking limitations

- Authored fixtures do not establish IID sampling or natural-population performance.
- Statistical independence cannot be proved by lineage labels or lexical checks.
- Ollama does not attest internal seed/option honoring.
- Local runtime estimates vary with load and model residency.
- The scope cannot repair or authorize any non-extraction G-ROUTE4 capability.

## 23. Boundary at this checkpoint

- G-ROUTE4 remains FAILED and unchanged.
- No scored or reserve fixture exists for G-EXTRACT1.
- No implementation, runner, scorer, runtime root, schedule, qualification table, or execution freeze exists.
- No provider/model contact or experiment launch occurred.
- No source/runtime behavior changed.
- Belief effects remain `none`.

## Design revision verdict

`READY_FOR_G_EXTRACT1_DESIGN_REREVIEW`

This verdict authorizes independent design rereview only. It does not authorize blueprint authoring, fixtures,
implementation, a pilot, provider contact, execution, installation, or routing.
