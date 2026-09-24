# Adaptive Cognitive Routing: inspection and benchmark design

**Status:** design-only checkpoint; no production router, benchmark runner, model call, or routing authority exists.

**Source checkpoint:** `8a2c15d35cb1ff36a97e6c91c89920d4529f07f9` (`v2735.0` semantic-fidelity closure).

**Design predecessor:** `d6fde928071c1df31e264576b256111f9921186a` (binary routing design before the mid-tier correction).

## Goal

Determine, with frozen task- and risk-specific evidence, which of three installed model tiers can safely handle a bounded class of work before any production routing behavior is implemented. The governing rule is **cheapest qualified model, with escalation only when evidence justifies it**. The intended future flow is:

```
task input
  -> deterministic task class and independent consequence risk
  -> cheapest model qualified for the exact task-class/risk cell (7B, then 14B, then 27B)
  -> model call through the existing provider transport
  -> deterministic structural, grounding, and authority checks
  -> accept, fail closed, or escalate to the next stronger qualified tier
  -> provenance receipt
```

Model self-reported confidence is never a qualification or acceptance signal. A routing policy may be proposed only after a frozen benchmark has produced reproducible evidence.

## Current architecture map

There is one broadly shared transport but no shared cognitive-routing seam. Callers choose the configured model before creating `LocalModelClient`; by the time transport receives a request, task class, consequence risk, validator contract, and escalation policy are not represented.

| Surface | Model/config selection | Request behavior | Validation / acceptance | Activity and accounting | Routing implication |
|---|---|---|---|---|---|
| Ordinary conversation | `conversation_runtime.py` loads the one operator setting through `LocalModelConfig.from_settings`; per-lane output limits may be applied | one non-stream or one streamed request; stream is never retried | response cleaning plus deterministic action-claim, follow-up, target, grounding, and quality checks | turn receipt records one request and transport retry count; chat stream exposes content-free provider events | a future decision must occur before client construction and must preserve streaming and turn receipts |
| Compatibility generation | `local_brain.py` resolves the same setting and permits an explicit model override | generate, stream, or JSON helper | JSON helper returns a parse-error wrapper; friendly errors are converted to text | no common Activity job; transport metrics are not returned by the helper | not suitable as the authoritative router because failures can be converted into ordinary text |
| Bounded conversation cognition | `conversation_cognition_bounded_generation.py` captures a configured profile digest | one bounded non-stream request in a wall-clock executor | profile binding, arbitration, and bounded-generation state | content-minimized receipts; profile digest is available | a useful future integration point after classification, not a general policy owner |
| Public-web research synthesis | `governed_public_web_research_adapter.py` uses the configured model with task-specific token limits, structured JSON, and transport retry disabled | candidate discovery, evidence synthesis, quality judgment, and a bounded schema-repair attempt | schema, citation identity, evidence dimensions, signed observations, source lineage, and answer-quality gates | semantic attempts are counted explicitly; raw public passages are transient; no shared Activity producer was found in this path | research requires its own quality corpus and must not be judged by JSON validity alone |
| Independent experiment review | `experiment_review.py` and `experiment_review_hierarchical.py` use the configured model, temperature 0, structured JSON, long timeout, and no transport retry | bounded per-part and hierarchical synthesis calls; one explicit repair attempt can occur | schema, grounding, role lineage, coverage, mutation guard, and final mechanical verification | `review_activity.py` provides the strongest shared Activity integration and counts calls, retries, observations, and synthesis units | long-context synthesis must preserve role semantics, not merely coverage |
| Isolated coding / repair | `isolated_coding_execution.py`, `structured_development_generation.py`, `conversational_supervised_repair_execution.py`, and `v1489_generic_self_development_execution.py` each build their own coding envelope | structured full-file or anchored edits, sometimes multiple semantic repair attempts | authority binding, allowed paths, exact replacements, syntax, focused tests, source snapshots, and apply boundaries | coding receipts count semantic attempts, but some paths use the configured transport retry policy and therefore need explicit benchmark retry accounting | coding qualification must require an isolated apply, compile, and focused-test result; parse success is insufficient |
| Reflection / planning | `model_backed_reflective_session.py` and `native_reflection_evaluation.py` use the configured model directly | bounded JSON reflection or small evaluation calls | outcome enum, uncertainty bounds, evidence references, no-authority language | bounded runtime records; provider counting is path-specific | useful as a separate task class because authority and uncertainty constraints dominate |
| Training benchmark | `model_training/training_operator.py` adapts the configured provider to a frozen evaluation corpus | explicit operator-authorized model calls only | frozen-corpus scoring and sealed result identity | provider count is retained | infrastructure can inform later runner design, but training authority and routing qualification must remain separate |
| Readiness / diagnostics | `local_model_readiness.py`, `native_conversation_validation.py`, and `local_model.py` health methods | provider metadata and explicit smoke calls | model identity, service health, latency, quality probes | bounded diagnostics | metadata inspection is not model qualification; smoke output cannot become a routing policy |
| Frozen experiments | G-CORROB uses `tools/g_corrob1_provider.py`; G-SYNTH1-R2 uses its preserved qualification harness | experiment-specific, digest-bound behavior | experiment-specific frozen policy and scorer | experiment-specific receipts and Activity | these are historical evidence, not production router implementations |

### Shared transport facts

`local_model.py` owns provider-neutral HTTP, model-return identity checks, generation options, cancellation, bounded non-stream retries, non-replayed streams, and provider metrics. It does not know why a request exists. It is therefore the correct execution layer and the wrong policy layer.

The current settings schema has one generation model. Several callers alter temperature, token budget, timeout, JSON mode, or retry behavior independently. A future router must return an immutable decision envelope to the caller; it must not mutate global settings or silently switch the configured model.

### Accounting risks found during inspection

1. `LocalModelClient.generate` can retry transport failures according to the configured retry limit. Some callers record one semantic request plus `last_retry_count`; others record only that the provider was contacted. A benchmark must force `retry_limit=0` and count every provider invocation itself.
2. Research and review implement explicit semantic repair attempts above transport. Those attempts must remain distinct from transport retries.
3. `local_brain.py` converts provider errors to friendly response text. Benchmark code must call the typed transport directly so an error cannot be scored as an answer.
4. Activity coverage is uneven. Experiment review and G-CORROB have first-class Activity producers; ordinary conversation has stream events and turn receipts; public-web research and several coding paths have local receipts but no common long-running Activity contract.
5. `qualifications/g_synth1_r2_harness.py` has a known promotion-accounting defect. Its frozen result remains valid historical evidence, but the harness is explicitly excluded from benchmark execution until a prospective repair and regression test exist.

## Installed candidate inventory

Read-only local metadata inspection initially found the 7B and 27B candidates. The operator then explicitly authorized installation of the exact mid-tier tag `qwen3:14b`; its download and SHA-256 verification completed successfully. No model was loaded for generation or called.

| Tier | Model | Local ID | Parameters | Quantization | Declared context | Local size | Current role |
|---|---|---|---:|---|---:|---:|---|
| small | `qwen2.5:7b` | `845dbda0ea48` | 7.6B | Q4_K_M | 32,768 | 4.7 GB | cheapest qualification candidate |
| mid | `qwen3:14b` | `bdbd181c33f2` | 14.8B | Q4_K_M | 40,960 | 9.3 GB | intermediate qualification and escalation candidate |
| large | `qwen3.8:27b` | `22130167c4c2` | 27.3B plus vision projector | Q4_K_M | 262,144 | 17 GB | incumbent runtime model and strongest installed candidate |

The mid-tier model is from the Qwen3 family, exposes completion, tool, and thinking capabilities, and exceeds the benchmark's planned 8,192-token context cap. Its local Ollama manifest digest is `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`, and its installed weight-blob binding is `sha256:a8cc1361f3145dc01f6d77c6c82c9116b9ffe3c97b34716fe20418455876c40e`. Its Q4_K_M quantization and common Ollama transport make it technically suitable for all planned task-class envelopes; benchmark evidence, not metadata, must determine which task/risk cells it qualifies for.

The operator runtime currently selects `qwen3.8:27b`, 8,192 context, 350 default output tokens, temperature 0.45, top-p 0.9, top-k 40, repeat penalty 1.1, thinking off, one transport retry, and a 300-second read timeout. The short IDs above are inventory evidence, not execution-freeze digests.

## Task taxonomy

Task class describes the cognitive contract. Consequence risk is classified independently.

| Class | Provider needed | Primary challenge | Deterministic evidence required |
|---|---|---|---|
| `deterministic_only` | no | routing should avoid a model call entirely | exact parser/rule result and no-provider receipt |
| `ordinary_conversation` | yes | natural response, continuity, and action-claim discipline | conversation quality, grounding, target, and authority checks |
| `structured_extraction` | yes | exact JSON/schema/binding from bounded input | parse, schema, enum, binding, quote/grounding, and forbidden-field checks |
| `grounded_research_synthesis` | yes | independent evidence, calibrated recommendation, and citation lineage | every material claim grounded; source independence and uncertainty preserved; no unsupported winner |
| `hierarchical_semantic_synthesis` | yes | long-context compression without semantic-role drift | no silent drop, no role loss, valid accounting, safe refusal, and operator-inspected promotion sample |
| `coding_generation_repair` | yes | bounded source edit that actually works | authority/path binding, isolated apply, compile, focused tests, regression checks, and unchanged protected source |
| `reflective_planning` | yes | uncertainty-aware planning without authority inflation | schema, evidence references, uncertainty, no fabricated execution, and no belief/action authority |

## Consequence-risk taxonomy

Risk never changes the task class and never creates authority.

| Risk | Meaning | Proposed future constraint |
|---|---|---|
| `R0` | deterministic/no-model work | no model call |
| `R1` | reversible private wording with no external factual or action consequence | any model qualified for the task class |
| `R2` | factual synthesis, recommendations, or plans that could guide operator decisions | qualified model plus grounding/uncertainty validation |
| `R3` | source candidate, security/governance interpretation, or action-adjacent artifact | strongest qualified model; deterministic validation and operator-controlled downstream action |
| `R4` | frozen experiments, gold/threshold/policy, release/promotion, provider management, beliefs, or authority | no adaptive automatic selection; exact pre-bound model/capability and existing approval boundary |

## Benchmark candidate G-ROUTE1

This checkpoint defines the design, not the corpus or execution freeze.

### Corpus plan

Create 24 fresh fixtures, four per model-backed task class and one for each R1-R4 consequence-risk tier, with three frozen repeats per model: 216 intended calls. Each class contains clean controls, a boundary case, and an adversarial case. The `deterministic_only` class is evaluated without provider calls.

The same prompt, fixture, order schedule, context limit, output cap, sampling options, and validator apply to all three candidates. Candidate identity is not exposed in prompts. Calls are single-job and sequential. Transport retry is zero. Any semantic repair stage is measured as a separate, prospectively specified condition rather than hidden inside first-pass quality.

The corpus must be authored and independently audited before freeze. Existing G-EVID1/G-CORROB failures and G-SYNTH1-R2 sentences may define general semantic classes but may not be copied, paraphrased, or used as answer-revealing development cases. The frozen G-SYNTH1-R2 harness is not reusable.

### Per-class envelopes

The benchmark preserves each production class's relevant envelope rather than forcing one artificial universal prompt:

- conversation uses streaming and records first transport chunk, first visible token, total latency, and output tokens;
- structured extraction uses non-stream JSON with the frozen schema;
- research uses frozen public-source excerpts and signed source identities, never live web collection;
- hierarchical synthesis uses the production prompt/validator/governance after the accounting defect is prospectively repaired;
- coding uses disposable fixture repositories and isolated apply/compile/test verification;
- reflection/planning uses bounded JSON and no-authority checks.

Thinking is off for all candidates, context is capped at 8,192, and task-specific output caps are frozen before calls. A cold-load probe is reported separately from warm execution and excluded from quality denominators.

### Quality and cost decision rule

Selection is lexicographic: safety and contract validity, then task utility, then cost.

Qualification is never global. Every result occupies one exact **task class × consequence risk × model tier** matrix cell. The six model-backed task classes, four risk tiers, and three model tiers create 72 required qualification cells. R4 cells may be measured as evidence, but R4 remains ineligible for adaptive selection because its existing exact pre-bound model and approval boundaries prevail.

For a model tier to qualify in one task/risk cell:

1. every authority, privacy, binding, provenance, and structural hard gate passes on every repeat;
2. no accepted output contains an evaluator-confirmed false-clean failure that the proposed production validator would miss;
3. the class-specific utility floor is met prospectively;
4. repeat instability stays within the frozen class limit;
5. all provider calls and outputs have complete reconstructable provenance.

Among qualified tiers in the exact cell, selection walks `qwen2.5:7b` → `qwen3:14b` → `qwen3.8:27b` and stops at the first qualified tier. If 7B is not qualified but 14B is, 14B is selected; if neither is qualified but 27B is, 27B is selected; if no tier qualifies, execution fails closed without silently choosing a model. Measured median and p95 latency, first-token latency where relevant, tokens per second, model size/residency cost, and provider-call count characterize cost, but cannot override a qualification failure.

The required decision cases are explicit: all three qualified selects 7B; only 14B and 27B qualified selects 14B; only 27B qualified selects 27B; no qualified tier produces `no_qualified_model`. After a validator-detectable runtime failure, escalation selects the next stronger qualified tier, so a qualified 14B tier cannot be bypassed on the way from 7B to 27B.

This rule intentionally prevents a small model from qualifying merely because malformed outputs are easy to detect. False-clean semantic failures are first-class blockers unless a deterministic production validator actually catches them.

### Escalation evaluation

The benchmark records, without extra calls, adjacent-tier and end-to-end cases where a cheaper tier fails and a stronger tier succeeds on the same frozen fixture/repeat. Those matched outputs estimate:

- validator-detectable failures eligible for one future escalation;
- false-clean failures that would escape escalation;
- escalation catch rate;
- unnecessary escalation rate;
- end-to-end quality after hypothetical escalation;
- added latency and call cost.

A future runtime may escalate only to the next stronger tier that is qualified for the same task/risk cell. It cannot skip a qualified 14B tier, though it may bypass a tier already proven unqualified for that exact cell. The full ladder permits at most two explicit escalations, never silently falls back, changes providers, broadens authority, retries indefinitely, or accepts a stronger output without the same deterministic validators.

## Metrics and units

Results must separate fixture, repeat, provider call, candidate, task class, and risk tier. At minimum report:

- hard-gate pass/fail by fixture, repeat, task class, risk tier, and model tier;
- first-pass structural and grounding validity;
- task-specific utility pass rate;
- false-clean semantic failure count;
- safe-refusal and false-refusal counts;
- repeat agreement and disposition stability;
- median/p95 first-token and total latency;
- prompt/output token counts and tokens per second;
- cold-load time separately from warm latency;
- provider calls, explicit semantic repairs, and transport retries;
- 7B→14B and 14B→27B escalation-eligible, caught, missed, and unnecessary-escalation counts;
- selected-tier outcome (`small`, `mid`, `large`, or `no_qualified_model`) for every task/risk cell;
- model identity/configuration and raw-output digests;
- validator and scorer versions/digests.

No aggregate score may hide a hard-gate failure.

## Activity and concurrency contract

The future runner must use the shared Activity contract and one global local-model research lease. Safe live fields are phase, candidate ID, task class, completed/total fixtures, calls completed/total, elapsed time, structural-failure count, and terminal state. Prompt text, fixture content, model output, expected labels, quality judgments, and routing decisions remain absent during collection.

Pause/cancel must preserve append-only lineage. Resume requires exact artifact, model, configuration, schedule, validator, and scorer digests. A stale or different model cannot resume the run.

## Stop and abort rules

Before any live call, stop on corpus, prompt, model, configuration, schedule, validator, scorer, Activity, or provenance drift. During collection, malformed output is an observed failure, not a reason to tune or retry. Provider mismatch, fallback, namespace contamination, missing persistence, accounting disagreement, or Activity mutation invalidates the run mechanically. Quality failure is a valid benchmark result and must not trigger prompt, threshold, or fixture repair in place.

## Required work before live benchmarking

1. Author and independently audit the 24-fixture corpus and class-specific gold/validators.
2. Prospectively repair the G-SYNTH harness accounting defect or implement a fresh equivalent runner with a regression proving promotions update local role accounting.
3. Implement an immutable task/risk decision record, benchmark runner, scorer, model/config verifier, append-only persistence, Activity adapter, and one-job lease in isolation from production routing.
4. Run deterministic/adversarial tests and a no-generation mechanical pilot.
5. Prepare and audit an execution freeze.
6. Obtain explicit operator authorization for the live benchmark.
7. Only after reviewed evidence exists, propose a production router as a separate governed change.

## Current conclusion

The complete 7B → 14B → 27B ladder is now locally available and represented in every qualification and scoring dimension. There is still no qualification evidence to route any production task to a different model. G-ROUTE1 is ready for fixture and validator construction, not a model-selection switch.
