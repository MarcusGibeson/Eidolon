# G-ROUTE1 Scientific Execution Authorization Handoff

G-ROUTE1 is repaired, deterministically verified, audited, and frozen for operator review. The repair
performed no scientific model call and launched no benchmark.

## Candidate

- status: `READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION`
- candidate: `G-ROUTE1-EXECUTION-R3`
- implementation commit: `4fa5978799492939178c8c1fd6b2ef0bd316539e`
- fixture/validator freeze: `G-ROUTE1-FIXTURE-VALIDATOR-R2`

Digests are recorded in `EXECUTION_FREEZE_CANDIDATE.json` and must be read from it, not from this page.
Verify with `python tools/g_route1_execution_freeze.py`, which rebuilds the manifest from disk and
fails closed on any drift.

## Why R3 exists

R2 was authorized, passed preflight, and stopped at schedule position 57 of 216. The frozen evaluator
raised `TypeError` on a structurally legal answer whose `uncertainties` were objects rather than
strings, so a wrong model answer crashed the benchmark instead of scoring zero. See
`BLOCKED_EXECUTION_R2_EVALUATOR_DEFECT.md` for the preserved run and `VALIDATOR_REPAIR_AUDIT.md` for
the repair and its verification.

Both validators now classify non-text list elements under `*_element_type_mismatch` instead of raising,
across `uncertainties`, `citations`, `lineages`, `observation_ids`, `evidence_ids` and `depends_on`.
All 56 observations persisted by R2 were re-validated with the repaired validators with **zero verdict
changes**, so the repair converts crashes into recorded failures and alters no observed judgment.

## Preserved history

R2 is preserved exactly as executed and was not resumed: 56 persisted observations, terminal state
`incomplete`, no terminal receipt, no terminal checkpoint, position 57 contacted but never persisted
and never re-requested. Its freeze is preserved byte-for-byte as `EXECUTION_FREEZE_CANDIDATE_R2.json`,
R1 as `EXECUTION_FREEZE_CANDIDATE_R1.json`, and the superseded fixture freeze as
`FIXTURE_VALIDATOR_FREEZE_R1.json`.

R3 carries the true prior-execution lineage — 57 provider generation calls and 1 benchmark launch
across R1 and R2 — while its own `provider_generation_calls` and `benchmark_launches` remain 0, because
R3 has never been executed. **Do not launch from any superseded freeze.**

## Unchanged by the repair

`corpus.json`, `gold.json`, `prompt_profiles.json`, `thresholds.json`, `schedule.json`,
`model_bindings.json`, the scorer, runner, persistence layer, provider boundary, Activity adapter,
coding runner and both contract modules are byte-identical to R2. The benchmark definition is
unchanged: 24 fixtures x 3 models x 3 repeats = 216 calls, 72 qualification cells, 3 observations per
cell, missing data cannot pass.

## Before authorizing

Independently verify the current freeze, confirm its authority flags are all false and its own
execution counters are 0, review `VALIDATOR_REPAIR_AUDIT.md`, and confirm the protected corpus, gold,
scorer, thresholds, schedule, policies and model bindings retain their R2 digests. Authorization must
be one-shot and bound to this exact R3 freeze digest.

Production routing and belief effects remain disabled.
