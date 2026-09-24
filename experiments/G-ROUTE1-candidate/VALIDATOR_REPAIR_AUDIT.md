# G-ROUTE1 Validator Repair Audit

Date: 2026-09-24
Verdict: **CLEAN**
Authority: non-authoritative implementation audit; no provider, execution, routing, source-application, or belief authority.
Provider generation calls during repair and audit: **0**.

## Finding

Both validators de-duplicated model-supplied lists with `set()` and performed identity lookups against
sets and dict keys. A structurally legal answer whose elements are objects or nested lists raised
`TypeError` instead of being judged. R2 halted at schedule position 57 on exactly this.

The defect class was wider than the observed crash:

| Path | Field | Operational validator | Frozen evaluator |
|---|---|---|---|
| `research.v1` | `uncertainties` | safe | raised |
| `research.v1` | `citations`, `lineages` | raised | raised |
| `synthesis.v1` | `observation_ids` | raised | safe |
| `planning.v1` | `evidence_ids`, `depends_on` | raised | safe |

Repairing only the observed crash would have left four live crash sites on fixtures the frozen
schedule reaches.

## Repair

Each validator gained a local `_text_items` helper that returns the text elements of a model-supplied
list and records anything else under `*_element_type_mismatch`. Non-text elements are excluded from
de-duplication and identity lookups. They are never stringified into a shape that could compare equal
to gold, and they never raise. The helper is duplicated rather than shared so the gold-blind validator
and the evaluator continue to share no judgment code.

Element-type failures carry the existing `type_mismatch` token, so they mark the output structurally
invalid exactly as `extraction_type_mismatch` already did, and they fall inside the existing
grounding-validity predicates for citations, lineages, observations, evidence and dependencies.

One deliberate non-change: the gold-blind validator still accepts non-text `uncertainties` in
`research.v1`, because it never enforced that element's type and never crashed on it. Tightening it
would be a new gate, not a crash repair. The evaluator rejects it, so the case surfaces as a
false-clean — which is the phenomenon this benchmark exists to measure, honestly recorded rather than
quietly closed.

## Verification

32 independent checks, all passing.

**The repair changes no observed judgment.** All 56 observations persisted by R2 were re-validated with
the repaired validators. Operational acceptance, semantic hard-gate outcome and full reason lists are
identical on every record: **0 verdict changes**. The repair converts crashes into recorded failures
and nothing else.

**No path raises, and no malformed answer passes.** All six sites were re-probed with objects, nested
lists and mixed text-and-object elements. Zero crashes; zero evaluator passes.

**The benchmark survives the answer that killed R2.** A standalone provider-free 216-call run with the
exact R2-killing shape injected at `GROUTE1-RESEARCH-R3-R1-small` completes: 216 calls persisted,
completed position 216, next position 217, and result, manifest, terminal receipt, Activity and
checkpoint all `complete`. The injected answer is recorded with no infrastructure failure, marked
false-clean, and its cell does not qualify — 71 of 72 cells qualify instead of 72.

**Scientific content is untouched.** Between the R2 and R3 execution freezes, `corpus.json`,
`gold.json`, `prompt_profiles.json`, `thresholds.json`, `schedule.json`, `model_bindings.json`, the
scorer, runner, persistence, provider, Activity adapter, coding runner and both contract modules are
byte-identical. Only the two validators, their tests, the freeze builder, the validator contract, the
deterministic test record and the fixture freeze changed.

## Deterministic suites

| Suite | Tests | Result |
|---|---|---|
| `g_route1_execution_tests.py` | 22 | PASS |
| `g_route1_fixture_tests.py` | 15 | PASS |
| `g_route1_freeze_tests.py` | 9 | PASS |
| `g_route1_execution_freeze_tests.py` | 8 | PASS |
| `g_route1_mechanical_pilot_tests.py` | 10 | PASS |
| `adaptive_cognitive_routing_design_tests.py` | 1 | PASS |
| `py_compile` of the execution modules | 1 | PASS |

New adversarial coverage: `uncertainties`, `citations` and `lineages` carrying objects, nested lists,
mixed text-and-object, and non-list values on the evaluator side; `citations`, `lineages`,
`observation_ids`, `evidence_ids` and `depends_on` on the gold-blind side; and a full 216-call run that
completes with a non-hashable answer preserved as scientific data.

## Lineage

R2 is preserved exactly as executed and was **not resumed**. Its 56 observations remain `incomplete`
with no terminal receipt and no terminal checkpoint. The R3 freeze carries the true prior-execution
record forward — 57 provider generation calls and 1 benchmark launch across R1 and R2 — while its own
counters remain 0, because R3 has never been executed.

Preserved byte-for-byte: `EXECUTION_FREEZE_CANDIDATE_R1.json`, `EXECUTION_FREEZE_CANDIDATE_R2.json`,
`FIXTURE_VALIDATOR_FREEZE_R1.json`.

Production routing: disabled. Automatic escalation: disabled. Belief effects: `none`.
No benchmark was launched and no model was contacted by this repair or this audit.
