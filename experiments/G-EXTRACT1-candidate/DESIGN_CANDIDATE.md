# G-EXTRACT1: Prospective Structured-Extraction Requalification

Status: **DESIGN CANDIDATE - REVIEW REQUIRED**

Execution status: **not implemented, not frozen, not authorized, not running**

Provider generation calls: **0**

Belief effects: **none**

## 1. Governed origin and experiment identity

**Experiment ID:** `G-EXTRACT1`

**Name:** Prospective Structured-Extraction Requalification and Generalization Test

This is a new experiment. It is not a continuation, rescore, repair, or reopening of G-ROUTE4. G-ROUTE4 remains
historically **FAILED** at evidence commit `c95d2d1a4177c0f6a33bb8ffb772dfc19c272646`.

The design is motivated by, but does not alter, these frozen G-ROUTE4 records:

- `G_ROUTE4_CLOSURE.json`, SHA-256
  `d992a169a2be293909f0fe0f1b39720656f40a09dc4f6b4e9c53449110cef8be`;
- `PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json`, SHA-256
  `461a85368a6cbbd39429bebbae883c0b17be614db52e343150b23051041b4868`.

No G-ROUTE4 artifact is an execution input or scored observation for G-EXTRACT1. Historical results are used only to
define prospective failure families and the scope of the new question.

## 2. Research question

**Primary question:**

> Under the unchanged G-ROUTE4 structured-extraction prompt and operational contract, can a prospective,
> family-stratified qualification test identify model-tier and risk-round cells that retain safe and useful behavior
> on a separately authored fresh validation corpus, while containing false-clean extraction errors?

**Diagnostic questions:**

1. Would broader fixture-family coverage and a larger number of distinct fixtures have detected the date/time,
   numeric/threshold, and entity-binding failures missed by G-ROUTE4 Phase A?
2. Are errors repeat-variable or repeat-stable within a fixture and model cell?
3. Do failures cluster by family, boundary type, tier, or round?
4. Which of the six extraction cells (`R2` and `R3` x 7B, 14B, and 27B), if any, pass both prospective
   qualification and fresh validation?

This design can test whether stronger sampling and coverage would have caught the observed failure classes. It cannot,
by itself, causally separate prompt behavior from model weights or every source of model stochasticity. The prompt is
held unchanged so prompt improvement cannot masquerade as an improved qualification method.

## 3. Prospective hypotheses

- **H1 - sparse-qualification hypothesis.** At least one of the four extraction cells qualified by G-ROUTE4 will
  fail the larger, stratified G-EXTRACT1 Phase A gate. A preregistered legacy-sized 8-observation prefix is reported
  descriptively to show whether an old-sized sample would have missed a later full-corpus failure; it never decides
  qualification.
- **H2 - family-coverage hypothesis.** Date/time and numeric/threshold families will account for more semantic
  failures than entity/binding families, consistent with the 8/5/1 G-ROUTE4 extraction breakdown. This is diagnostic,
  not a gate or permission to weaken another family.
- **H3 - repeat-pattern hypothesis.** Some errors will recur on both Phase A repeats for the same fixture and tier.
  Repeat agreement on the same wrong value is reported as correlated wrong agreement. Repeats are never counted as
  independent fixtures for confidence bounds.
- **H4 - no monotonic-tier assumption.** Qualification is decided independently for every tier/round cell. The design
  permits 7B, 14B, 27B, any subset, or no tier to qualify; parameter count creates no presumption.
- **H5 - fresh-validation hypothesis.** A cell that passes the improved Phase A gate should independently pass the
  same safety and utility principles on the pre-authored Phase B corpus. An A-pass/B-fail cell is not qualified and is
  evidence that the proposed qualification method still failed to generalize.

## 4. Scope

### In scope

- Structured extraction only.
- Risk rounds `R2` and `R3` only.
- Candidate cells: all three frozen tiers in both rounds, six cells total.
- Date arithmetic, clock/time arithmetic, elapsed time, date and midnight boundaries, numeric arithmetic, existing
  in-scope units, threshold relations, equality boundaries, entity binding, field/value binding, multi-entity
  disambiguation, exact values, and complete-versus-partial binding.
- Structurally valid semantic errors, ambiguity containment, malformed outputs, and repeat-stable errors.

### Explicitly out of scope

- Grounded research, ordinary conversation, reflective planning, hierarchical synthesis, and coding.
- R1 promotion and R4 operational routing. Their G-ROUTE4 statuses remain unchanged.
- Timezone conversion. The current extraction contract supports `YYYY-MM-DD` and `HH:MM`, not a frozen timezone
  type or offset-arithmetic contract. Adding one would change the task contract and requires another design.
- Production routing, source modification, prompt repair, model installation, and belief effects.

## 5. Phase structure

### Phase A - prospective requalification

Purpose: test all six candidate cells on a larger family-stratified corpus under the unchanged baseline prompt.

- 35 distinct fixtures per round, 70 total.
- Seven families per round, exactly five distinct fixtures per family.
- Two fresh-session repeats per fixture/tier.
- All three tiers run on all Phase A fixtures.
- Exactly 420 scheduled calls: `70 fixtures x 3 tiers x 2 repeats`.

Phase A produces a cell-level `qualifies_for_validation` result only. It does not update a routing table.

### Phase B - targeted fresh validation

Purpose: independently test only Phase A-qualified cells on a corpus that was authored, adjudicated, reviewed, and
frozen before any Phase A model contact.

- 35 new distinct fixtures per round, 70 total.
- The same seven failure families, but separate template lineages and payloads.
- One call per fixture for each qualifying tier/round cell.
- Zero calls for cells that fail Phase A.
- Maximum 210 calls if all six cells qualify: `35 fixtures x 6 cells`.

Phase A observations, bounds, and failures are not pooled with Phase B. A cell is finally requalifiable only when it
passes both phases independently. If no cell qualifies in Phase A, Phase B makes zero calls and the valid result is
`no_extraction_cell_qualified`.

## 6. Corpus architecture

| Component | R2 | R3 | Total |
|---|---:|---:|---:|
| Phase A scored fixtures | 35 | 35 | 70 |
| Phase B scored fixtures | 35 | 35 | 70 |
| Phase A matched reserves | 7 | 7 | 14 |
| Phase B matched reserves | 7 | 7 | 14 |
| **Fixtures authored before model contact** | **84** | **84** | **168** |

Each phase/round contains five distinct fixtures in each of seven families. One matched reserve is authored for every
phase x round x family slot. Reserves are not scored by default.

No scored fixture, gold answer, or reserve is authored in this design task.

### Replacement policy

- A reserve may replace a fixture only before any provider contact, for a documented mechanical, ambiguity, leakage,
  or gold defect found by independent review.
- The reserve must match the frozen phase, round, family, field-type, operator, and ambiguity slot.
- Any replacement requires renewed corpus/gold digests and renewed preflight review.
- After first provider contact, no fixture replacement is allowed. A defect makes the affected run incomplete or
  invalid under the preregistered abort rules; it is never silently repaired.

## 7. Fixture-family plan

| ID | Family | Required variation across A/B and R2/R3 | Main observed risk addressed |
|---|---|---|---|
| E1 | Calendar-date arithmetic | day/month/year boundaries, leap-year status, positive intervals, direction checks, off-by-one traps | 8 date/time failures |
| E2 | Clock and elapsed-time arithmetic | minute/hour addition, midnight rollover, elapsed duration, date carry when a date field exists | 8 date/time failures |
| E3 | Numeric aggregation and in-scope units | sums, products, decimal amounts, rates, counts, explicit same-unit or explicitly defined conversions | 5 numeric/threshold failures |
| E4 | Threshold and equality semantics | `>`, `>=`, `<`, `<=`, `=`, just-below, exactly-on, just-above, combined conditions | 5 numeric/threshold failures |
| E5 | Entity binding and disambiguation | full multi-token names, multiple entities, repeated surnames/tokens, entity-to-record binding | 1 entity-binding failure |
| E6 | Field/value and exact-value binding | same-typed fields, transposition traps, identifiers, canonical strings, complete field sets, exact formatting | wrong-field and partial-binding risks |
| E7 | Ambiguity and partial evidence | omitted critical values, equally plausible bindings, conflicting same-priority statements, incomplete records | accepted guesses and false-clean ambiguity |

Every determinate family contains five fixtures per phase/round. E7 contains five ambiguity sentinels per
phase/round. Each family must vary surface wording, schema names, entity count, operation graph, values, dates, and
answer position. A direct paraphrase or isomorphic value substitution of a G-ROUTE4 failure is prohibited.

## 8. Diagnostic linkage and realistic detection opportunity

| G-ROUTE4 finding | G-EXTRACT1 prospective response | How it could catch the class without replaying it |
|---|---|---|
| 8 date/time failures | E1 and E2: 10 distinct fixtures per round per phase | New calendars, intervals, rollover structures, and field schemas exercise the same reasoning classes without reusing dates, names, values, or operation signatures. |
| 5 numeric/threshold failures | E3 and E4: 10 distinct fixtures per round per phase | Balanced relation operators and exact-boundary placements prevent an aggregate arithmetic score from hiding comparison errors. |
| 1 entity-binding failure | E5 plus binding portions of E6: 10 distinct fixtures per round per phase | Full-span names, multiple entities, and same-typed fields create prospective opportunities for truncation, swaps, and wrong-record attachment. |
| Structurally valid wrong outputs | Zero-false-clean gate over all 35 distinct fixtures | Schema-valid wrong values cannot be treated as a structural pass or hidden by aggregate correctness. |
| Possible repeated/correlated mistakes | Two Phase A repeats and a repeat-pair ledger | Same-fixture wrong agreement is visible, but repeats are not treated as independent evidence. |
| Old 8/8 qualification generalized poorly | 35 distinct fixtures/cell, seven-family coverage, fixture-level confidence bound | Zero false-clean over 35 distinct fixtures has a one-sided 95% upper bound of 0.082032, unlike 0/4 fixtures or 0/8 observations. |
| Unsafe R2 escalation at 14B | All R2 tiers evaluated independently; no routing simulation needed for qualification | The 14B cell must pass fresh threshold and binding families directly before any later routing use is considered. |

## 9. Independence and contamination controls

All controls are checked before model contact and are bound into the eventual corpus freeze.

1. **Fresh lineages.** Phase A, Phase B, and reserves use separate template-lineage IDs. Phase B is complete and
   sealed before Phase A runs.
2. **No historical reuse.** No G-ROUTE4 prompt payload, answer, entity, identifier, exact date tuple, exact numeric
   tuple, or expected output may appear as a scored G-EXTRACT1 item.
3. **Prompt/gold blindness.** Model requests contain only the unchanged extraction system/prompt template and the
   fixture payload/schema. Gold, determinacy, family, gate, phase outcome, historical failure, and expected labels
   are excluded.
4. **No development examples by default.** The unchanged G-ROUTE4 prompt receives no newly authored examples. If a
   later prompt-repair study needs examples, they must use separate development-only families and cannot enter either
   scored corpus.
5. **Independent authorship/review.** Fixture authoring and gold review are separate roles where practical. Reviewers
   receive the task contract and candidate fixtures but no model outputs. At least two semantic signoffs are required
   before adjudication closes.
6. **Lexical checks after boilerplate removal.** Normalized exact matches must be zero. Maximum token 5-gram Jaccard
   against any G-ROUTE4 A/B payload must be below 0.20. Near-threshold pairs are manually reviewed and disclosed.
7. **Structural checks.** No scored item may share the exact operation-graph + schema-type + entity-count + boundary-
   relation signature of any of the 14 G-ROUTE4 unsafe extraction fixtures. Phase A and B may share a family but not
   an exact structural signature.
8. **Diversification.** Invented entities/IDs are globally unique; exact date/numeric tuples are unique; relation
   operators and equality positions are balanced prospectively.
9. **Family separation.** A/B template lineages, not merely words or values, are disjoint. Reserve lineage is also
   separate from its primary slot.
10. **Reports.** Exact-match, lexical overlap, structural overlap, entity/identifier reuse, date/number reuse, family
    balance, and near-threshold reports are mandatory preflight artifacts.

The numerical similarity thresholds are design judgments and require adversarial review before acceptance. Passing a
similarity check does not replace human contamination review.

## 10. Gold and adjudication plan

### Gold form

Every fixture is classified before model contact as either:

- `determinate`: one complete canonical extraction exists; or
- `ambiguous_nonaccept`: the evidence does not support one complete extraction, so operational acceptance of a
  guessed complete object is unsafe.

Determinate gold contains the exact schema, canonical typed values, derivation steps, binding map, determinacy proof,
and rationale. Ambiguous gold contains the specific unresolved field/binding, the conflicting or missing evidence,
and why no single complete object is supported. It does not invent a guessed expected value.

### Frozen semantic rules

- **Dates:** proleptic Gregorian calendar. `date + N days` treats the stated date as day zero and adds exactly N
  elapsed calendar days. Inclusive ranges are counted only when the fixture explicitly says inclusive.
- **Times:** 24-hour `HH:MM`; elapsed minutes/hours use exact arithmetic. Midnight rollover is explicit. No timezone
  inference or daylight-saving conversion is allowed.
- **Numbers:** source literals are parsed as exact decimal values. Integer fields require mathematical integers.
  Number fields compare by exact decimal value, so `5` and `5.0` are numerically equivalent where the schema says
  `number`. No floating tolerance is used.
- **Rounding and units:** no implicit rounding or conversion. Any rounding or conversion rule must be stated in the
  fixture and frozen in gold before contact. Currency and measured quantities otherwise require exact values.
- **Thresholds:** `>`, `>=`, `<`, `<=`, and equality are applied literally. Equality cases are deliberately balanced.
- **Entities:** exact full-span, case-sensitive binding after removal only of an explicitly permitted leading label or
  article. Partial names, swapped entities, and values attached to the wrong record fail.
- **Fields:** all required fields must be present exactly once and bound to the correct source fact. Extra, omitted,
  or transposed fields fail the semantic and/or structural contract as preregistered.
- **Formatting:** object-key order and insignificant JSON whitespace are ignored. Enum/string contents, identifiers,
  dates, and times must match canonical values exactly. Duplicate JSON keys are invalid.

### Adjudication

1. Author creates fixture, independent derivation, gold, rationale, family/features, and reserve match.
2. Reviewer A independently solves the fixture without seeing the proposed answer, then compares.
3. Reviewer B audits arithmetic/calendar operations, determinacy, binding, and contract compliance.
4. Disagreements are preserved and resolved by an operator-approved adjudicator before provider contact.
5. A genuinely ambiguous determinate candidate is moved to E7 or rejected; it is never forced into crisp gold.
6. Gold, fixtures, reserves, equivalence rules, and adjudication records freeze together before any model contact.
7. Any gold defect discovered after contact invalidates the affected prospective run; historical G-ROUTE4 gold is
   never edited.

## 11. Units of analysis and metrics

Metrics must name their unit and denominator:

- **Observation:** one model call.
- **Distinct fixture:** one independently authored payload/gold item.
- **Repeat pair:** the two Phase A observations for one fixture/cell.
- **Family:** one of E1-E7.
- **Cell:** one model tier x risk round.

Primary confidence bounds use distinct fixtures, not repeated observations. Exact one-sided 95% Clopper-Pearson
bounds are computed in exact arithmetic. Observation-level bounds are descriptive only.

Required metrics, separately by phase/cell/family:

- semantic correctness;
- structural validity;
- operational acceptance;
- correct operational acceptance;
- false-clean (operationally accepted but semantically wrong);
- ambiguity containment/nonacceptance;
- malformed/truncated output;
- entity and field binding correctness;
- wrong exact value and wrong-field counts;
- repeat exact agreement, semantic agreement, wrong agreement, and correlated false-clean agreement;
- provider/infrastructure failures;
- fixture and family denominator coverage.

## 12. Proposed frozen qualification and validation gates

These are prospective candidate gates. They must be independently reviewed and frozen before model contact. No
result may change them.

### Per-cell Phase A gates

| Gate | Numerator / denominator | PASS | FAIL | INSUFFICIENT |
|---|---|---|---|---|
| Denominator integrity | completed scheduled observations / 70; distinct fixtures / 35; repeat pairs / 35 | 70/70, 35/35, 35/35; no duplicate | any semantic missingness caused by model output is scored under its gate | provider/config/provenance failure, missing call, duplicate, or unprovable call state |
| Family coverage | distinct fixtures in each E1-E7 family | exactly 5/5 in every family | wrong family assignment or off-plan substitution | missing family record or unresolved fixture identity |
| False-clean / unsafe candidate use | fixtures with any accepted semantic error / 35 | 0/35; one-sided 95% upper bound 0.082032 <= 0.10; also 0/70 observations | >=1 false-clean fixture or observation | denominator invalid |
| Determinate semantic correctness | determinate fixtures with both repeats correct / 30 | >=29/30; one-sided lower bound 0.851404 >= 0.85 | <=28/30 | denominator invalid or determinacy disputed |
| Determinate structural validity | determinate fixtures with both repeats structurally valid / 30 | >=29/30 | <=28/30 | denominator invalid |
| Useful correct acceptance | determinate fixtures with both repeats accepted and correct / 30 | >=27/30; one-sided lower bound 0.761402 >= 0.75 | <=26/30 | denominator invalid |
| Family semantic floor | correct determinate fixtures / 5 in each E1-E6 family | >=4/5 in every family | any family <=3/5 | family denominator invalid |
| Ambiguity containment | E7 fixtures with no accepted guessed complete extraction / 5 | 5/5 across both repeats | any accepted unsupported complete extraction | ambiguity gold unresolved |
| Binding correctness | accepted E5/E6 outputs with exact entity-field-value binding / all accepted E5/E6 outputs | 100%; no partial/swap error | any accepted binding error | no valid binding denominator due infrastructure failure |
| Malformed determinate output | determinate fixtures with either repeat malformed / 30 | <=1/30 and structural gate passes | >=2/30 | provider truncation/config failure makes status unknown |
| Correlated false-clean | repeat pairs with the same or equivalent wrong accepted output / 35 | 0/35 | >=1/35 | repeat missing |

A cell proceeds to Phase B only if every Phase A gate passes. Family floors prevent aggregate success from hiding one
known failure class. Safe nonacceptance on an ambiguity sentinel is not counted as a malformed determinate failure.

### Per-cell Phase B gates

Phase B uses 35 distinct fresh fixtures and one observation each. It applies the same principles:

- denominator integrity: 35/35 calls and fixtures, no duplicate;
- family coverage: 5/5 fixtures in every E1-E7 family;
- false-clean: 0/35, one-sided upper bound 0.082032 <= 0.10;
- determinate semantic correctness: >=29/30, lower bound >=0.85;
- determinate structural validity: >=29/30;
- useful correct acceptance: >=27/30, lower bound >=0.75;
- family semantic floor: >=4/5 for every E1-E6 family;
- ambiguity containment: 5/5;
- accepted E5/E6 binding correctness: 100%;
- malformed determinate fixtures: <=1/30.

No A/B pooling is allowed. `finally_qualified` requires Phase A PASS and Phase B PASS independently. An A-pass/B-fail
cell is `validation_failed`, not qualified. If a completed cell misses a gate, it fails; insufficient is reserved for
missing or untrustworthy denominators, not inconvenient semantic results.

### Prospective threshold provenance and rationale

| Threshold | Prospective basis |
|---|---|
| 0.10 false-clean upper limit | Carries the standing G-ROUTE4 unsafe-stop safety target as a design principle; it does not alter or rescore the historical gate. |
| 35 distinct fixtures/cell | With zero affected fixtures, the one-sided 95% upper bound is 0.082032. Repeats are excluded from this calculation. |
| Zero false-clean observations/fixtures | G-ROUTE4 failed because accepted semantic errors reached stops. One such event is therefore disqualifying in a requalification experiment. |
| 30 determinate + 5 ambiguity fixtures | Thirty determinate fixtures give a 0/30 false-clean upper bound of 0.095034, while five ambiguity sentinels form a separately visible containment stratum. |
| Semantic lower bound 0.85 | A qualified extractor must be broadly correct, not merely safe through rejection. 29/30 gives a one-sided lower bound of 0.851404. |
| Useful-acceptance lower bound 0.75 | Prevents universal rejection from qualifying. 27/30 gives a one-sided lower bound of 0.761402. |
| 4/5 per-family floor | Prevents the aggregate gate from hiding two or more failures in one known failure family. It is a stratification rule, not a confidence claim. |
| <=1 malformed determinate fixture | Keeps structural reliability aligned with the 29/30 structural-validity floor; ambiguity nonacceptance is reported separately. |
| A and B must pass independently | Directly tests generalization and prevents a strong Phase A score from compensating for fresh-validation failure. |

All numerical thresholds are prospective design judgments or standing safety principles. They require independent
review before freeze and are never tuned to model output.

### Experiment-level outcomes

- `TARGETED_REQUALIFICATION_SUPPORTED`: at least one cell passes A and B; only those cells are candidates for a later
  table update.
- `NO_EXTRACTION_CELL_QUALIFIED`: all completed cells fail Phase A or Phase B without integrity failure.
- `QUALIFICATION_METHOD_FAILED_VALIDATION`: one or more cells pass A but fail B; no failed cell qualifies.
- `INCOMPLETE`: required evidence is missing under the frozen failure rules.
- `INVALID`: provenance, blindness, gold, configuration, scorer, or denominator integrity is compromised.

These are scientific result labels, not production-routing authorization.

## 13. Model/provider configuration proposal

To isolate sampling/coverage from prompt or provider changes, carry forward the exact G-ROUTE4 baseline:

| Tier | Model | Parameters / quantization | Manifest digest | Blob SHA-256 |
|---|---|---|---|---|
| small | `qwen2.5:7b` | 7.6B / Q4_K_M | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` |
| mid | `qwen3:14b` | 14.8B / Q4_K_M | `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8` | `a8cc1361f3145dc01f6d77c6c82c9116b9ffe3c97b34716fe20418455876c40e` |
| large | `qwen3.8:27b` | 27.3B / Q4_K_M | `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643` | `f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` |

- Provider: Ollama `0.34.3`.
- `num_ctx=8192`, `num_predict=350`, `temperature=0.45`, `top_p=0.9`, `top_k=40`,
  `repeat_penalty=1.1`, `think=false`, non-streaming.
- Fresh session per call, zero retries, zero repair calls, zero fallback.
- Exact model/provider/config preflight before any future pilot or run; mismatch fails closed.
- Ollama accepts submitted options but does not attest internal honoring. That limitation remains explicit.

No new model is proposed.

## 14. Sampling, seeds, and call order

- Phase A: two distinct seeds per fixture, fresh sessions, same fixture/repeat seed across tiers for comparability.
- Phase B: one seed per fresh fixture; fixture independence, not repeated sampling, supports the validation bound.
- Candidate seed bases: 610000 (A) and 620000 (B), subject to a global collision audit before freeze.
- Candidate formula: `base + zero_based_fixture_index * 10 + one_based_repeat`.
- Model order is balanced prospectively across fixtures so tier is not confounded with run order, heat, or load.
- The complete A schedule and all conditional B cell schedules freeze before Phase A contact.
- No adaptive resampling, retry, repair, replacement, or extra diagnostic generation call is allowed.

The first four Phase A fixtures and their two repeats form a preregistered, legacy-sized 8-observation descriptive
prefix per cell. The prefix has no gate authority and cannot be selected after results.

## 15. Efficiency estimate

| Stage | Calls per tier | Total calls | Condition |
|---|---:|---:|---|
| Phase A | 140 | 420 | always |
| Phase B | up to 70 | up to 210 | only A-qualified cells |
| **Maximum** | **210** | **630** | all six cells pass A |

Preserved G-ROUTE4 observed mean call latencies were approximately 7.6 seconds (7B), 13.0 seconds (14B), and
51.2 seconds (27B). With sequential execution:

- Phase A active time estimate: about 2.8 hours.
- Maximum Phase B active time: about 1.4 hours.
- Maximum total active time: about 4.2 hours; practical wall estimate 4.6-5.0 hours with verification/checkpoints.
- 27B maximum contribution: about 3.0 hours, the dominant bottleneck.
- Maximum calls are 630 versus G-ROUTE4's 1,395, a 54.8% reduction. Estimated active time is about 55% lower than
  the preserved 9.33-hour G-ROUTE4 A+B active total.

If no cell qualifies, execution stops after 420 calls. If only one 27B cell qualifies, Phase B adds 35 calls (about
30 minutes by the preserved mean).

## 16. Failure and abort behavior

- Malformed, truncated, refused, or semantically wrong model outputs are evidence. They are preserved and never
  repaired or retried.
- Provider/config/model mismatch, corpus/gold digest drift, blindness breach, schedule drift, scorer-integrity
  failure, or unprovable persistence state prevents a valid completed verdict.
- A provider transport failure creates missing evidence and an insufficient/incomplete cell under the frozen rule;
  it is not converted into a semantic failure or silently retried.
- A semantic gate failure is a valid result. It never triggers threshold relaxation, gold editing, prompt tuning,
  added calls, or automatic rerun.
- Failed and incomplete attempts remain append-only and cannot be overwritten by a later attempt.
- One local-model research job at a time; pause/resume must preserve exact next-call identity and provenance.

## 17. Baseline-versus-repair boundary

G-EXTRACT1 primary execution uses the unchanged frozen G-ROUTE4 extraction prompt, schema, and operational validator.
No prompt wording derived from the 14 unsafe cases is added.

A prompt-repair study may be proposed only after the baseline closes and operator review occurs. A prospective trigger
for considering (not authorizing) that separate study is any of:

1. no cell finally qualifies;
2. the same family produces false-clean failures in two or more completed model cells; or
3. repeat-stable wrong agreement appears in two or more fixtures in one family.

Any repair must receive a new experiment identity, use a separate development corpus, and use newly authored,
independently adjudicated scored corpora. G-EXTRACT1 A/B fixtures become historical diagnostics and cannot score the
repaired prompt. Baseline and repaired results are never pooled.

## 18. Integration and requalification plan

Passing G-EXTRACT1 grants evidence, not routing authority. After human review:

1. Build a candidate extraction-only qualification-table overlay containing only cells that passed A and B.
2. Prove deterministically that every non-extraction G-ROUTE4 cell and policy row is byte-identical.
3. Run a small no-provider integration check of lookup, escalation, no-qualified behavior, and table immutability.
4. Require separate operator authorization for any runtime/table installation or production routing.

Outcome handling:

- **Only 27B qualifies:** only the passing 27B round cell(s) enter the candidate overlay; lower tiers remain
  unqualified and routing starts at 27B or returns no-qualified.
- **Only one round qualifies:** update only that round in the candidate overlay; the other round remains no-qualified.
- **No tier qualifies:** structured extraction remains unavailable for governed routing; no table update is created.
- **Baseline fails but a later repair passes:** only the separately preregistered repaired-prompt experiment can
  support a new prompt-specific table. It does not turn G-ROUTE4 or G-EXTRACT1 into a pass.
- **Shared logic changes:** a broader routing revalidation is required only if prompt, validator, comparator, routing,
  or persistence changes affect other task classes. A cell-only table overlay does not by itself require a full
  G-ROUTE4 rerun.

Production adaptive routing remains disabled throughout G-EXTRACT1.

## 19. Risks and unresolved design questions

1. **Ambiguity representation:** the unchanged extraction prompt has no explicit abstain token. The proposed E7 gold
   therefore treats safe operational nonacceptance as success and an accepted guessed complete object as unsafe. This
   must receive specific external review before corpus authoring.
2. **Fixture independence:** Clopper-Pearson bounds assume independent fixtures. Family/template separation reduces
   obvious dependence but cannot prove statistical independence.
3. **Prompt-versus-model causality:** an unchanged-prompt failure identifies baseline behavior, not whether prompt
   wording or model weights caused it.
4. **Similarity thresholds:** lexical/structural thresholds are prospective design judgments and may reject legitimate
   cases or miss conceptual similarity. Human contamination review remains mandatory.
5. **Risk-round semantics:** R2/R3 authoring must preserve the existing consequence-risk definitions without using
   superficial difficulty as a substitute for risk.
6. **Provider attestation:** Ollama does not attest internal seed/option honoring. A later authorized mechanical pilot
   may verify submission and observable behavior only.
7. **Local runtime:** estimates use preserved G-ROUTE4 latency and may vary with load or model residency.
8. **Narrow scope:** passing extraction does not repair the six unsafe stops in other classes and cannot authorize
   those capabilities.

None of these questions is resolved by changing a historical artifact. Items 1, 2, 4, and 5 require explicit design
review before implementation authorization.

## 20. Requirement-by-requirement mapping

| Requirement | Design location / disposition |
|---|---|
| A. Extraction-only task scope | Sections 4 and 7; only R2/R3 structured extraction, no other classes. |
| B. Failure-mode coverage | E1-E7 in section 7; false-clean and repeat-pair gates in section 12. |
| C. Independence/contamination | Section 9; both phases and reserves freeze before contact. |
| D. Stronger qualification design | Sections 6, 11, and 12; 35 distinct fixtures, stratification, fixture-level bounds, no pseudoreplication. |
| E. Three frozen model tiers | Sections 4 and 13; six tier/round cells, no monotonic assumption. |
| F. Compact two-phase structure | Sections 5 and 15; 420 fixed + up to 210 targeted calls. |
| G. Repair-versus-measurement | Section 17; unchanged baseline first, separate future identity/corpora for repair. |
| H. Gold/adjudication | Section 10; explicit determinacy, arithmetic, equivalence, binding, and independent signoff. |
| I. Prospective gates | Section 12; numerator, denominator, PASS/FAIL/INSUFFICIENT for every gate. |
| J. Diagnostic linkage | Section 8; maps 8 date/time, 5 numeric/threshold, and 1 entity failure to fresh families. |
| K. Efficiency | Section 15; 630-call maximum, 4.2 active hours, 27B bottleneck explicit. |
| L. Integration | Section 18; bounded extraction-only overlay and deterministic integration check. |
| M. Governance | Sections 1, 16, 18, and 22; no history rewrite, autonomy, beliefs, or implicit execution. |

## 21. Conditions required before implementation authorization

Implementation is not authorized until all of the following are complete:

1. Two independent adversarial design reviews find no unresolved blocking issue.
2. The ambiguity/nonacceptance construct is explicitly accepted or revised before fixture authoring.
3. The six candidate cells, seven families, fixture counts, gates, units, bounds, and phase-selection rule are frozen.
4. The machine-readable design contract is proven equivalent to this document.
5. A corpus-authoring blueprint fixes every phase/round/family slot, feature crossing, operator balance, and reserve.
6. All 168 primary/reserve fixtures and gold records are authored without model contact.
7. Independent gold review and adjudication close every determinate/ambiguity judgment before model contact.
8. G-ROUTE4 overlap, structural-signature, entity/identifier, date/number, and family-lineage reports pass and are
   independently audited.
9. Exact model/provider/config identities are inspected without generation and remain compatible with the proposal.
10. Runner, validator, scorer, denominator logic, persistence, Activity, and abort behavior receive separate
    implementation authorization, deterministic tests, and an adversarial implementation audit.
11. A mechanical-pilot protocol and authorization boundary are separately reviewed; no pilot is implied here.
12. A candidate execution freeze binds every behaviorally relevant artifact, with Phase A and Phase B execution
    authorization flags false.
13. Separate explicit operator authorization is required for a mechanical pilot, Phase A, and conditional Phase B.

## 22. Governance boundary at this checkpoint

- G-ROUTE4 remains FAILED and byte-unchanged.
- No scored fixture or gold item exists for G-EXTRACT1.
- No implementation, runner, scorer, schedule, runtime root, qualification table, or execution freeze exists.
- No provider or model was contacted.
- No new experiment run began.
- No source/runtime behavior changed.
- Reviewer output remains non-authoritative.
- Belief effects remain `none`.
- No autonomous authority is granted.

## Design verdict

`READY_FOR_EXTRACTION_EXPERIMENT_REVIEW`

This verdict authorizes review of the design only. It does not authorize fixture authoring, implementation, a pilot,
model contact, execution, table mutation, installation, or production routing.
