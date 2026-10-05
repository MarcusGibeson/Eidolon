# G-EXTRACT1 Closure and Phase A Diagnostic

**CLOSED / VALID_COMPLETE / NO_PHASE_A_CELL_QUALIFIED**

This is a valid experiment with a negative qualification result, not an infrastructure failure. 480/480 Phase A observations completed; zero provider failures, incomplete observations, integrity events or Phase B calls. No cell qualified. Phase B remains unauthorized and was not executed.

## Frozen Cell Results

Semantic/structural/useful are distinct determinate fixture counts out of 30. Family counts require both repeats; E5 requires all four counterfactual-pair observations. FC means operationally accepted but not exactly correct.

| Cell | Semantic | Structural | Useful | FC obs/fixtures | Malformed fixtures | Binding fixtures | E5 pairs | Correlated FC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small:R2 | 15/30 | 28/30 | 15/30 | 26/13 | 2 | 3 | 3/5 | 13 |
| small:R3 | 16/30 | 29/30 | 16/30 | 24/13 | 1 | 1 | 5/5 | 11 |
| mid:R2 | 18/30 | 21/30 | 18/30 | 9/5 | 9 | 1 | 3/5 | 3 |
| mid:R3 | 16/30 | 22/30 | 16/30 | 14/6 | 8 | 1 | 2/5 | 7 |
| large:R2 | 26/30 | 30/30 | 26/30 | 7/4 | 0 | 0 | 5/5 | 3 |
| large:R3 | 22/30 | 29/30 | 22/30 | 12/7 | 1 | 0 | 4/5 | 5 |

| Cell | E1 | E2 | E3 | E4 | E5 | E6 | E7 observations |
|---|---:|---:|---:|---:|---:|---:|---:|
| small:R2 | 2/5 | 2/5 | 2/5 | 3/5 | 3/5 | 3/5 | 10/10 |
| small:R3 | 3/5 | 1/5 | 1/5 | 2/5 | 5/5 | 4/5 | 10/10 |
| mid:R2 | 4/5 | 3/5 | 3/5 | 2/5 | 3/5 | 3/5 | 10/10 |
| mid:R3 | 3/5 | 4/5 | 2/5 | 2/5 | 2/5 | 3/5 | 10/10 |
| large:R2 | 3/5 | 5/5 | 5/5 | 3/5 | 5/5 | 5/5 | 10/10 |
| large:R3 | 3/5 | 3/5 | 5/5 | 2/5 | 4/5 | 5/5 | 10/10 |

All cells pass denominator integrity, family/composed coverage and E7 recognition/containment. All fail semantic, useful, false-clean, family floor and correlated false-clean gates. Structural/malformed gates pass only small:R3 and both large cells. Binding gates pass only the large cells. E5 pair gate passes only small:R3 and large:R2. The JSON report retains every exact Boolean gate outcome.

## Family and Subtype Concentrations

Each family has 30 cell-fixture instances across six cells. E5 has 120 observations; each other family has 60. These descriptive totals are not pooled qualification denominators.

| Family | Correct observations | Correct fixture instances | FC observations | Malformed observations |
|---|---:|---:|---:|---:|
| E1 calendar | 37/60 | 18/30 | 23 | 0 |
| E2 clock and elapsed | 39/60 | 18/30 | 18 | 3 |
| E3 numeric | 36/60 | 18/30 | 16 | 8 |
| E4 comparison | 32/60 | 14/30 | 20 | 8 |
| E5 entity binding counterfactual pairs | 97/120 | 22/30 | 9 | 14 |
| E6 exact copy | 46/60 | 23/30 | 6 | 8 |
| E7 explicit partial absence / not-provided handling | 60/60 | 30/30 | 0 | 0 |

| Subtype | Definition | Wrong observations | FC observations | Malformed observations |
|---|---|---:|---:|---:|
| E1-01 | CALENDAR_DAY_OFFSET / within_month | 0 | 0 | 0 |
| E1-02 | CALENDAR_DAY_OFFSET / month_boundary | 2 | 2 | 0 |
| E1-03 | CALENDAR_DAY_OFFSET / year_boundary | 2 | 2 | 0 |
| E1-04 | CALENDAR_DAY_OFFSET / leap_day_boundary | 12 | 12 | 0 |
| E1-05 | CALENDAR_DAY_OFFSET / edge_offset | 7 | 7 | 0 |
| E2-01 | CLOCK_MINUTE_OFFSET / same_day | 3 | 1 | 2 |
| E2-02 | CLOCK_MINUTE_OFFSET / clock_rollover | 6 | 6 | 0 |
| E2-03 | ELAPSED_MINUTES / ordinary_elapsed | 0 | 0 | 0 |
| E2-04 | ELAPSED_MINUTES / elapsed_rollover | 9 | 9 | 0 |
| E2-05 | ELAPSED_MINUTES / equal_time_zero | 3 | 2 | 1 |
| E3-01 | ADD / single_node | 0 | 0 | 0 |
| E3-02 | SUBTRACT / single_node | 6 | 6 | 0 |
| E3-03 | SUM / single_node_three_operands | 2 | 2 | 0 |
| E3-04 | DIVIDE>EXACT_COPY / C3 | 8 | 4 | 4 |
| E3-05 | UNIT_CONVERSION>EXACT_COPY / C3 | 8 | 4 | 4 |
| E4-01 | ADD>GT / C1 | 9 | 8 | 1 |
| E4-02 | SUBTRACT>LTE / C1 | 6 | 6 | 0 |
| E4-03 | CALENDAR_DAY_OFFSET>GTE / C2 | 4 | 0 | 4 |
| E4-04 | CLOCK_MINUTE_OFFSET>LT / C2 | 9 | 6 | 3 |
| E4-05 | EQ / direct_comparison | 0 | 0 | 0 |
| E5-01 | ENTITY_FIELD_BIND / entities_2:IDENTIFIER | 11 | 2 | 9 |
| E5-02 | ENTITY_FIELD_BIND / entities_2:ATTRIBUTE | 8 | 7 | 1 |
| E5-03 | ENTITY_FIELD_BIND / entities_3:EVENT_ROLE | 2 | 0 | 2 |
| E5-04 | ENTITY_FIELD_BIND / entities_2:IDENTIFIER | 2 | 0 | 2 |
| E5-05 | ENTITY_FIELD_BIND / entities_3:ATTRIBUTE | 0 | 0 | 0 |
| E6-01 | EXACT_COPY(source) / source_copy | 0 | 0 | 0 |
| E6-02 | EXACT_COPY(source) / source_copy | 2 | 2 | 0 |
| E6-03 | EXACT_COPY(source) / source_copy | 0 | 0 | 0 |
| E6-04 | CALENDAR_DAY_OFFSET>EXACT_COPY / derived_copy | 4 | 0 | 4 |
| E6-05 | CLOCK_MINUTE_OFFSET>EXACT_COPY / derived_copy | 8 | 4 | 4 |
| E7-01 | zero_node_absence / support_schemas | 0 | 0 | 0 |
| E7-02 | zero_node_absence / support_schemas | 0 | 0 | 0 |
| E7-03 | zero_node_absence / support_schemas | 0 | 0 | 0 |
| E7-04 | zero_node_absence / support_schemas | 0 | 0 | 0 |
| E7-05 | zero_node_absence / support_schemas | 0 | 0 | 0 |

## Large:R2 Exact Failure Set

- E1-03: 2041-12-27 + 12 calendar days = 2042-01-08; repeats returned 2052-01-08 and 2041-01-08.
- E1-04: 2032-02-27 + 6 calendar days = 2032-03-04; both repeats returned 2032-03-05.
- E4-01: (57 + 18) > 74 is true; both repeats returned false.
- E4-04: 23:46 + 40 minutes = 00:26; 00:26 < 00:31 is true. Repeat 1 returned false; repeat 2 was correct.

These four fixtures explain 26/30 semantic, E1/E4 floors of 3/5 and all seven false-clean observations. E1-03, E1-04 and E4-01 account for three frozen correlated false-clean pairs. E1-03 is two different wrong results, not an identical-error repeat. Structural 30/30 and E2/E3/E5/E6 5/5 are component successes, not qualification. The cell also fails useful 26/30 against 27/30. It is not a partial or essentially passed cell.

## False-Clean and Repeat Diagnosis

92 accepted-wrong observations affect 48 cell-fixture instances. Every output, expected value, source, schema, frozen evaluation and diagnostic field mismatch is in the JSON observation ledger. Invalid Gregorian date values accepted by the historical operational validator remain false-clean; this diagnostic does not retrospectively tighten the validator.

Both repeats are false-clean in 42 rendered-variant pairs. 35 have identical normalized parsed objects; 34 have the same wrong value under exact typed schema semantics. The latter excludes invalid calendar dates. The frozen gate counts all both-wrong pairs, including differing errors.

## Structural, Format and Binding Findings

Malformed observations: 41. Issues (nonexclusive): extra_output_fields=28, invalid_time_value=2, missing_output_fields=4, wrong_output_type=8.

The malformed outputs are valid JSON objects with schema problems, not an invalid-JSON or provider-truncation campaign. Mid-tier outputs repeatedly include unrequested intermediate/source keys and return entity labels where field values are required. Small-tier failures include empty objects and invalid minute values. Large:R3 has a leading-space field-name error. A format wrapper is not itself malformed when the frozen normalizer accepts it; wrapper outcomes are recorded separately. Prompt causation cannot be inferred because no controlled prompt contrast was run.

E5 small:R2 alters 65.5 to 65 and omits one date output. Mid-tier E5 often returns the selected entity label rather than its requested source value; this is not proof of choosing the wrong entity. No failed response exactly substitutes a nonselected entity source value. E6 small-tier numeric copying loses the fraction, and derived-time copying returns incorrect or untransformed source values. Mid-tier E6 adds intermediate fields even where the expected terminal field is correct. No article/label-removal mechanism is implicated by an observed exact mismatch. E5 qualification remains the original two-selector counterfactual pair interpretation.

## Scaling and Round Differences

Small -> mid -> large semantic fixture counts: R2 15 -> 18 -> 26; R3 16 -> 16 -> 22. Structural counts are nonmonotonic: R2 28 -> 21 -> 30; R3 29 -> 22 -> 29. False-clean observations: R2 26 -> 9 -> 7; R3 24 -> 14 -> 12. Lower mid false-clean counts coexist with much more structural rejection, so they are not standalone proof of safer semantics. Binding errors decline to zero in both large cells, but large:R3 loses one E5 pair through schema naming.

R3 versus R2: small semantic +1 and false-clean -2; mid semantic -2 and false-clean +5; large semantic -4 and false-clean +5. Large:R3 additionally loses E2 clock/elapsed and E4 comparison fixtures. Different independent fixture contents and frozen value strata prevent a causal claim from the risk-round label. Distinct model identities prevent a pure parameter-count scaling claim.

## Supported Components and Historical Motivation

- large:R2 E2/E3/E5/E6 each 5/5 logical fixtures, structural 30/30 and binding errors 0.
- large:R3 E3/E6 each 5/5 logical fixtures; small:R3 E5 counterfactual pairs 5/5.
- All six cells E7 recognition/containment 10/10 observations. This is explicit partial absence, not broad ambiguity reasoning.

Preserved G-ROUTE4 diagnostic records 14/20 unsafe stops in structured extraction; G-EXTRACT1 prospectively tests requalification under the byte-bound baseline.
Structured extraction remains a qualification weakness under the current configuration. Larger models improve some tested dimensions, but false-clean errors remain and targeted requalification is not supported.
This does not reopen G-ROUTE4, establish production safety or demonstrate Phase B generalization.

## Smallest Prospective Follow-Up

Start with a calendar-boundary-only large-model diagnostic on fresh leap/year/366-day cases and within-month controls. The leap subtype failed in all 12 observations, representing two fixtures across three models and two repeats, not 12 independent instances. This is the smallest coherent scope supported by the recurring date pattern. Measure false-clean separately from format success; a deterministic calendar reference-check contrast is justified for investigation, not authorized implementation. E4 is a separate follow-on hypothesis: matched standalone upstream versus standalone comparison controls would distinguish subtask patterns that final Booleans alone cannot localize. Do not automatically retest all seven families or loosen the old gates. New design and execution require separate authorization.

No production adaptive-routing policy follows from this run. Large improves several tested dimensions but is insufficient; mid is not uniformly beneficial; small is not qualified for the tested cells. Deterministic computation/checking is a prospective hypothesis, not runtime authority.

## Verification and Governance

Verified actual committed bytes for 2,895 execution files, 2,893 manifest members, 50 protected artifacts and 8 implementation files. Regenerated 480 requests, replayed all frozen scores and 481 checkpoint lineages, matched the final state/gates/verdict and authorization binding. All watched input hashes are identical before/after. The original evidence manifest and post-execution supplement remain separate and unchanged.

Execution commit: `672e86f9bf1ca3d449ff47371d0c00df0909c120`
Run: `G-EXTRACT1-PHASE-A-7d655fa9285d41b1938dd342bef053f6`

Provider/model/metadata calls in this task: 0. Phase B calls: 0; authorization: false. Corpus, gold, science, implementation, thresholds and historical execution evidence unchanged. G-ROUTE4 remains CLOSED FAILED. Autonomy false; belief effects none.
