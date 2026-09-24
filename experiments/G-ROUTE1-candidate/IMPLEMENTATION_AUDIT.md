# G-ROUTE1 Independent Implementation Audit

Date: 2026-09-23  
Verdict: **CLEAN**  
Authority: non-authoritative review; no execution, routing, source-application, or belief authority.

## Scope and method

The audit traced deterministic stub records from frozen fixture and scheduled identity through request rendering, provider boundary, raw persistence, gold-blind operational validation, frozen semantic evaluation, qualification scoring, escalation simulation, Activity projection, checkpoint/resume, and terminal state. It also reviewed exact model/config binding, the global single-job lease, mutation guard, abort semantics, and the absence of production-routing imports.

## Requirement matrix

| Requirement | Implementation | Deterministic proof | Status |
|---|---|---|---|
| Exactly 216 calls | `g_route1_execution_contract.build_schedule` | complete/unique/balanced schedule test | clean |
| Three exact models | `model_bindings.json` and provider receipt verifier | manifest/config drift tests | clean |
| Gold blindness at runtime acceptance | `g_route1_operational.validate_operational` | false-clean test proves operational accept can disagree with evaluator | clean |
| Evaluator-only gold | frozen `g_route1_validators` invoked after operational validation | frozen fixture tests and request-blindness test | clean |
| No retry or repair | frozen config and one provider invocation per schedule row | mismatch test stops after one call | clean |
| Append-only evidence | `RouteRunStore` exclusive-create records | duplicate-write and digest-corruption tests | clean |
| Pause/resume | digest-bound checkpoint and exact next position | pause after four calls, resume to 216 without duplicate/skip | clean |
| One research job | shared root lease | competing-run lease test | clean |
| Activity isolation | allowlisted operational fields and shared active clock | content rejection and cumulative-progress test | clean |
| Qualification arithmetic | 72 cells x 3 observations | complete synthetic run and vacuous-pass test | clean |
| False-clean visibility | operational acceptance plus semantic failure | explicit extraction false-clean regression | clean |
| Escalation order | `small -> mid -> large -> none` | mid acceptance and all-reject tests | clean |
| Incomplete semantics | provider mismatch/exception terminal receipts | single-attempt abort tests | clean |
| Strict mutation guard | complete behaviorally relevant path set | source-change digest test | clean |
| No production routing | scorer simulation only; no production router import | static inspection and report flag | clean |
| No belief effects | all contracts and records bind `none` | fixture, runner, and freeze assertions | clean |

## Known failure-mode audit

| Failure mode | Expected behavior | Observed deterministic behavior |
|---|---|---|
| malformed model output | preserve and score as scientific failure | passed |
| returned model mismatch | preserve call, stop incomplete, no retry | passed |
| provider boundary exception | append failure receipt, stop incomplete | passed |
| duplicate output | exclusive creation rejects | passed |
| missing observation | no complete verdict and no vacuous qualification | passed |
| checkpoint corruption | resume fails closed | passed |
| dependency drift | mutation digest changes and resume/live check fails | passed |
| false-clean answer | count and block exact qualification cell | passed |
| small rejected, mid accepted | stop simulated ladder at mid | passed |
| every tier rejected | return `no_qualified_model` | passed |

## Findings

No blocking or important implementation defect remained after repair of three audit findings: prompt binding initially covered only the shared profile, the lease was initially per-run rather than global, and resumed records were initially read by filename rather than schedule position. Each was corrected before freeze preparation and covered by regression tests.

## Limitations

1. Ollama 0.34.3 exposes submitted options but does not attest that each option is honored internally. A later explicitly authorized mechanical pilot is required for observed seed and session behavior.
2. Pause is supported only between provider calls. An interruption after contact but before durable record creation invalidates completeness and is never silently retried.
3. The coding fixture runner is intentionally restricted to the small audited fixture language and is not a general-purpose hostile-code sandbox.
4. Ollama controls model residency; the implementation does not claim a portable, attested model unload while paused.
5. This audit used deterministic stubs only. It establishes mechanical integrity, not model qualification.

Provider generation calls: **0**. Benchmark launches: **0**. Production routing changes: **0**. Belief effects: **none**.
