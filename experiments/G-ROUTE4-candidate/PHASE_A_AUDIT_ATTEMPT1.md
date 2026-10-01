# G-ROUTE4 Phase A independent qualification audit (attempt 1)

Verdict: READY
Run: groute4a-001-2f9407b8159dc8ac
Scored seal: 162b32a954f08ac45391492d0605254293187f674645cd6f1bbd0d49923cf895
run_created seal: f10b630a9e4a6c14ee14be957cd10924eec4bab8287ed772fe1e33089b4c9c92
Completed seal: b0ce745eccf15e0ddf91c96748244b757ec05fc9b2a1e137fef74b75b23a19b9
Execution freeze binding: 0e02a62eee57b7ed76ae1fe3fc722a36a9a6ad81c3045530a8a4eb244a7184bc
Auditor: Codex independent deterministic replay, 2026-10-01

Source checkout: C:\Users\marcu\Eidolon-g4adj, HEAD 0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28, clean before audit.
Data root audited read-only before table freeze: C:\Users\marcu\AppData\Local\Eidolon\research\g_route4.

## Method and boundaries

- The sealed journal was replayed with the frozen Phase A RunSpec. Provider generation was not invoked.
- Schedule, binding, model, repeat, seed, request/result lineage, and score projections were checked from persisted evidence.
- Cell aggregation and both one-sided exact 95% Clopper-Pearson upper bounds were independently implemented for this audit; g_route4_qualification.qualify() was not called.
- The independently calculated 60 complete cell objects were compared field-for-field with the sealed score.
- No corpus, gold, threshold, schedule, model binding, scoring rule, runtime code, belief, or Phase A output was modified.

## Evidence integrity - PASS

- Journal state: completed; entries: 964.
- Entry kinds: {"call_recorded": 480, "call_started": 480, "completed": 1, "run_created": 1, "scored": 1, "scoring_started": 1}.
- Calls: 480 started and 480 recorded; 480 unique call IDs; positions 1 through 480 exactly once; no duplicates or omissions.
- Every record matches the frozen schedule for call ID, position, fixture, task, risk, tier, model, repeat, and seed.
- Returned model equals requested and scheduled model for all 480 records.
- Infrastructure/transport failures: 0. Model mismatches: 0. Refusals: 0. Integrity mismatches: 0.
- score.json SHA-256: 44d7a2bc62ebb7785b636ba910069e37a89b8ece0973c881164000b3265f18f0 and its parsed value equals the sealed scored report.
- receipt.json SHA-256: 85574883d6d7593d3781e423a386af42f7ef2c7662e0745f228718cdbfcf6ba9.
- Terminal journal SHA-256: 74aea5a678d940d6056122f2d84164f7e1700d706f1ba569f45da66fac3a7702.
- Evidence head before table freeze: 9b717d99879ed05204fd77377252bc5f9ce0f5f7 (terminal A attempt 1).

## Frozen qualification rule - PASS

- Thresholds: {"distinct_fixtures_required": 4, "false_clean_allowed": 0, "missing_data_may_qualify": false, "observations_required": 8, "operational_acceptances_required": 8, "repeats_per_fixture": 2, "semantic_passes_required": 8, "vacuous_pass_allowed": false}.
- Each cell requires exactly 8 complete observations from 4 distinct fixtures with 2 repeats per fixture.
- Qualification requires 8 operational acceptances, 8 semantic passes, 0 false-clean results, and no infrastructure failure.
- Missing or shape-incomplete evidence is insufficient and cannot qualify.

## Independent 60-cell recomputation - PASS

| Task | Risk | Tier | Obs | Complete | Fixtures | Accepted | Pass | False-clean | Infra | Fail UB95 | Failing fixtures | Fixture UB95 | Verdict |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ordinary_conversation | R1 | small | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| ordinary_conversation | R1 | mid | 8 | 8 | 4 | 8 | 3 | 5 | 0 | 0.888887 | 3 | 0.987259 | not_qualified |
| ordinary_conversation | R1 | large | 8 | 8 | 4 | 6 | 6 | 0 | 0 | 0.599689 | 2 | 0.902389 | not_qualified |
| ordinary_conversation | R2 | small | 8 | 8 | 4 | 8 | 4 | 4 | 0 | 0.807097 | 2 | 0.902389 | not_qualified |
| ordinary_conversation | R2 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| ordinary_conversation | R2 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| ordinary_conversation | R3 | small | 8 | 8 | 4 | 8 | 3 | 5 | 0 | 0.888887 | 3 | 0.987259 | not_qualified |
| ordinary_conversation | R3 | mid | 8 | 8 | 4 | 8 | 2 | 6 | 0 | 0.953611 | 3 | 0.987259 | not_qualified |
| ordinary_conversation | R3 | large | 8 | 8 | 4 | 7 | 5 | 2 | 0 | 0.710759 | 2 | 0.902389 | not_qualified |
| ordinary_conversation | R4 | small | 8 | 8 | 4 | 8 | 4 | 4 | 0 | 0.807097 | 2 | 0.902389 | not_qualified |
| ordinary_conversation | R4 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| ordinary_conversation | R4 | large | 8 | 8 | 4 | 7 | 6 | 1 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R1 | small | 8 | 8 | 4 | 7 | 2 | 5 | 0 | 0.953611 | 3 | 0.987259 | not_qualified |
| structured_extraction | R1 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R1 | large | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R2 | small | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| structured_extraction | R2 | mid | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| structured_extraction | R2 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| structured_extraction | R3 | small | 8 | 8 | 4 | 6 | 6 | 0 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R3 | mid | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| structured_extraction | R3 | large | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R4 | small | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R4 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| structured_extraction | R4 | large | 8 | 8 | 4 | 8 | 4 | 4 | 0 | 0.807097 | 2 | 0.902389 | not_qualified |
| grounded_research_synthesis | R1 | small | 8 | 8 | 4 | 6 | 0 | 6 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R1 | mid | 8 | 8 | 4 | 6 | 0 | 6 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R1 | large | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 2 | 0.902389 | not_qualified |
| grounded_research_synthesis | R2 | small | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R2 | mid | 8 | 8 | 4 | 8 | 1 | 7 | 0 | 0.993609 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R2 | large | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 2 | 0.902389 | not_qualified |
| grounded_research_synthesis | R3 | small | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R3 | mid | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R3 | large | 8 | 8 | 4 | 8 | 5 | 3 | 0 | 0.710759 | 2 | 0.902389 | not_qualified |
| grounded_research_synthesis | R4 | small | 8 | 8 | 4 | 6 | 2 | 4 | 0 | 0.953611 | 3 | 0.987259 | not_qualified |
| grounded_research_synthesis | R4 | mid | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| grounded_research_synthesis | R4 | large | 8 | 8 | 4 | 8 | 5 | 3 | 0 | 0.710759 | 2 | 0.902389 | not_qualified |
| hierarchical_semantic_synthesis | R1 | small | 8 | 8 | 4 | 2 | 2 | 0 | 0 | 0.953611 | 3 | 0.987259 | not_qualified |
| hierarchical_semantic_synthesis | R1 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| hierarchical_semantic_synthesis | R1 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| hierarchical_semantic_synthesis | R2 | small | 8 | 8 | 4 | 0 | 0 | 0 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| hierarchical_semantic_synthesis | R2 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| hierarchical_semantic_synthesis | R2 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| hierarchical_semantic_synthesis | R3 | small | 8 | 8 | 4 | 3 | 1 | 2 | 0 | 0.993609 | 4 | 1.0 | not_qualified |
| hierarchical_semantic_synthesis | R3 | mid | 8 | 8 | 4 | 8 | 7 | 1 | 0 | 0.470679 | 1 | 0.751395 | not_qualified |
| hierarchical_semantic_synthesis | R3 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| hierarchical_semantic_synthesis | R4 | small | 8 | 8 | 4 | 0 | 0 | 0 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| hierarchical_semantic_synthesis | R4 | mid | 8 | 8 | 4 | 8 | 6 | 2 | 0 | 0.599689 | 1 | 0.751395 | not_qualified |
| hierarchical_semantic_synthesis | R4 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| reflective_planning | R1 | small | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R1 | mid | 8 | 8 | 4 | 8 | 2 | 6 | 0 | 0.953611 | 3 | 0.987259 | not_qualified |
| reflective_planning | R1 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| reflective_planning | R2 | small | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R2 | mid | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R2 | large | 8 | 8 | 4 | 8 | 7 | 1 | 0 | 0.470679 | 1 | 0.751395 | not_qualified |
| reflective_planning | R3 | small | 8 | 8 | 4 | 7 | 0 | 7 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R3 | mid | 8 | 8 | 4 | 8 | 0 | 8 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R3 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |
| reflective_planning | R4 | small | 8 | 8 | 4 | 5 | 0 | 5 | 0 | 1.0 | 4 | 1.0 | not_qualified |
| reflective_planning | R4 | mid | 8 | 8 | 4 | 8 | 3 | 5 | 0 | 0.888887 | 3 | 0.987259 | not_qualified |
| reflective_planning | R4 | large | 8 | 8 | 4 | 8 | 8 | 0 | 0 | 0.312344 | 0 | 0.527129 | qualified |

## Reproduced outcome - PASS

- Qualified: 12 of 60.
- Not qualified: 48 of 60.
- Insufficient evidence: 0 of 60.
- Every qualified cell has 8/8 complete observations, 4 fixtures, 2 repeats per fixture, 8 acceptances, 8 semantic passes, and 0 false-clean.
- Grounded research synthesis is not qualified for all 12 tier-by-risk cells. No broader inference or repair is made.

### Qualified cells

- ordinary_conversation|R2|large
- structured_extraction|R2|small
- structured_extraction|R2|mid
- structured_extraction|R2|large
- structured_extraction|R3|mid
- hierarchical_semantic_synthesis|R1|large
- hierarchical_semantic_synthesis|R2|large
- hierarchical_semantic_synthesis|R3|large
- hierarchical_semantic_synthesis|R4|large
- reflective_planning|R1|large
- reflective_planning|R3|large
- reflective_planning|R4|large

## Malformed and false-clean handling - PASS

- Structurally malformed normalized outputs: 7.
- Reasons: {"extraction_schema_mismatch": 3, "planning_step_schema_mismatch": 4}.
- Each malformed result remains a recorded observation and is rejected by the frozen operational validator; none was repaired or retried.
- Normalized false-clean results: 182. None was converted into a semantic pass.
- Normalized semantic passes: 254. Operational acceptances: 436.
- Belief effects are none on all 480 records. Production routing was not invoked.

## Table-freeze authorization binding

- Exact sentence: Freeze G-ROUTE4 qualification table from phase A attempt 1 of execution 0e02a62eee57b7ed76ae1fe3fc722a36a9a6ad81c3045530a8a4eb244a7184bc
- It binds attempt 1 to execution freeze 0e02a62eee57b7ed76ae1fe3fc722a36a9a6ad81c3045530a8a4eb244a7184bc.
- This audit authorizes only construction of the immutable qualification table from the sealed Phase A score.
- Phase B remains unauthorized and must not start.

## Verdict

READY
