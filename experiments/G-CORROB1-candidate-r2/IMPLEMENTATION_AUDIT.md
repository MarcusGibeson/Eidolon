# G-CORROB1-R2 adversarial implementation audit

**Audit scope:** implementation candidate only. No provider/model call, structural
pilot, experiment run, execution freeze, installation, belief effect, or G-EVID1
change occurred.

**Design basis:** second audit SHA-256
`a06871c1f025526baecaa3724e6e6f7d2929398b745f0e6dcc471c4253331613`.

## Architecture traced end to end

A deterministic correct fixture enters `g_corrob1_runner.execute`, receives one
minimal prompt body from `g_corrob1_contract.semantic_http_body`, is parsed and
strictly validated by `g_corrob1_policy.process_assessment`, governed by the
unchanged G-EVID1 policy, compared only after both role records are durably stored,
scored only after all 192 call records and 96 pair records exist, and projected
to shared Activity using count-only events. The fixture path produced:

- 192 unique call records with 192 distinct nonzero seeds;
- 96 unique pair records;
- 84 primary pairs and 12 diagnostic pairs;
- exact A and B primary semantic accuracy denominators of 84 each;
- 42/42 useful paired admissions for the all-correct fixture;
- zero unsafe use;
- byte-identical requests with Activity enabled, disabled, or failing;
- no provider contact.

## Design requirement to implementation proof

| Design requirement | Implementation location | Deterministic proof | Status |
|---|---|---|---|
| 32 items, 3 repeats, 96 pairs, 192 calls | `g_corrob1_contract.build_schedule` | complete identity/count/balance test | PASS |
| Blind A/B semantic inputs | `semantic_http_body`, `assert_minimal_semantic_body` | body-schema and leakage tests; exact original-prompt rendering | PASS |
| Fresh sessions and no retries | `OllamaExperimentAdapter.generate` | new Session per call; one POST; provider-failure call-count test | PASS for implementation; live interface check pending |
| Exact seeds and balanced order | `seed_for`, `build_schedule` | 192 unique seeds; 48/48 first-role enumeration | PASS |
| Exact configuration and no fallback | provider preflight verifier and adapter | mismatch matrix and returned-model fallback regression | PASS offline; live digest/support pending |
| Malformed/truncated preservation | policy parser, runner call record | malformed and output-cap regressions | PASS |
| Binding and duplicate rejection | runner and append-only store | swapped binding, duplicate record, missing/duplicate unit tests | PASS |
| Frozen individual governance | `individual_governance` delegates to `g_evid1_policy` | exhaustive 300 states: 2 use, 106 investigate, 192 abstain | PASS |
| Exact paired comparison | `compare_pair` | exhaustive 90,000 states: 4 use, 11,660 investigate, 78,336 abstain | PASS |
| Correlated false-clean can reach use | `compare_pair` and scorer | explicit correlated-wrong fixture reaches visible unsafe pair | PASS |
| Separate A/B baselines | scorer condition metrics | pair corruption rejected; role-specific fixed outputs | PASS |
| Fixed scorer denominators | scorer `_validate_units` | missing, duplicate, wrong repeat, duplicate-pair tests | PASS |
| Diagnostics excluded from crisp accuracy | scorer semantic accuracy | denominator fixed at 84; diagnostics reported as 12 separately | PASS |
| Unsafe pair cannot hide in aggregates | scorer condition/gate/correlated records | one-unsafe-pair fixture fails gate and names item/repeat | PASS |
| Exact raw persistence and no overwrite | `RunStore` | malformed raw equality, exclusive create, terminal guards | PASS |
| Full lineage | call and pair records plus score | synthetic end-to-end trace and record digests | PASS |
| Activity is observational only | `CorrobActivity`, runner `emit` guard | on/off/failure parity and forbidden-content scan | PASS |
| Infrastructure failure is not semantic failure | runner terminal handling | transport and provenance failure produce incomplete/no verdict | PASS |
| Semantic failure remains a result | scorer gates | correlated unsafe fixture completes and fails safety gate | PASS |
| Artifact drift blocks execution | freeze verifier and runner authorization guard | candidate/execution manifest verification | PASS offline |
| Belief effects remain none | contracts, records, Activity governance | static and end-to-end assertions | PASS |

## Known failure mode matrix

| Failure mode | Test | Expected behavior | Observed |
|---|---|---|---|
| A or B sees the other output | minimal-body/cross-request scan | other output absent | PASS |
| Gold/disposition/safety leakage | request schema scan | rejected or absent | PASS |
| Wrong model or fallback | preflight and returned-model tests | incomplete before valid verdict | PASS |
| Ignored/unsupported option | support-map test | preflight invalid | PASS |
| Missing/ignored seed | seed-support test | preflight invalid | PASS |
| Malformed JSON | malformed fixture | exact raw preserved; structural abstain; no retry | PASS |
| Truncation | output-cap fixture | truncated reason; structural abstain | PASS |
| Wrong item/evidence binding | structural matrix | invalid and abstain | PASS |
| Wrong request/assessor binding | swapped binding fixture | provenance-incomplete | PASS |
| Duplicate assessment | append-only store | exclusive-write failure | PASS |
| Missing A or B | fixed-unit scorer test | scorer rejection | PASS |
| Duplicate pair | fixed-unit scorer test | scorer rejection | PASS |
| Pair tampering | record digest and recomputation | scorer rejection | PASS |
| Repeat counted as new item | repeat-identity corruption | scorer rejection | PASS |
| Diagnostic enters crisp denominator | denominator assertion | remains outside 84 | PASS |
| Unsafe pair hidden by aggregate | correlated false-clean fixture | named unsafe count and failed gate | PASS |
| Baseline/paired cross-contamination | pair recomputation guard | corrupted pair rejected | PASS |
| Correlated wrong agreement | R02 synthetic failure | paired use remains reachable and unsafe | PASS |
| Activity side channel | snapshot forbidden-content scan | no semantic/evaluation content | PASS |
| Activity changes execution | on/off/failure parity | byte-identical requests and equal report | PASS |
| Interrupted provider | fourth-call failure | append-only partial evidence; incomplete result; no retry | PASS |
| Stale run reuse | duplicate run/store test | fail closed; no overwrite | PASS |
| Artifact/source drift | manifest verifier | digest mismatch blocks execution | PASS offline |
| Unauthorized execution | runner authorization test | refused before store/provider | PASS |

## Configuration audit

The adapter submits model `qwen3.8:27b`, structured non-streaming JSON, the exact
temperature, top-p, top-k, min-p, repeat penalty, context, output cap, stop list,
and per-call seed. It uses a fresh HTTP session and no application retry. A later
authorized preflight must resolve the installed model digest from Ollama and must
reject model fallback.

Ollama does not return an attestation that every submitted option was internally
honored. The implementation reports this limitation rather than converting
submission into proof. A later mechanical pilot can verify request capture and
seed repeatability, but cannot establish statistical or reasoning independence.

## Gold and threshold audit

The scorer did not define its gold. `GOLD_IMPLEMENTATION_AUDIT.md` independently
rechecked all 32 items against proposition/evidence semantics and found no defect.
Its historical-independence requirement remains pending because this Codex task
lineage participated in R2 authoring. Diagnostics remain outside crisp accuracy.

`THRESHOLD_PROVENANCE.md` classifies both zero-unsafe gates as standing safety
principles and the 34/42 and 5/6 utility floors as prospective engineering design
judgments. None was chosen from observed G-EVID1 or G-CORROB1 performance.

## Findings

### BLOCKING before structural pilot

None in the deterministic implementation path.

### REQUIRED before execution freeze

1. Historically independent signoff over all 32 gold items.
2. Exact installed `qwen3.8:27b` content digest and configuration receipt.
3. Authorized mechanical pilot validating provider request capture, model return
   identity, seed submission/repeatability, persistence, and Activity parity.
4. Explicit review of Ollama's inability to attest internal option honoring.
5. A new execution-freeze manifest and exact operator authorization.

### TEST-HARNESS LIMITATION

The shared Activity contract/API suite passed. The native Activity UI qualification
harness could not reach rendering because this Python installation has no usable
Tcl/Tk `init.tcl`. The G-CORROB1 adapter adds no UI-specific contract and writes
the same Activity v1 records already consumed by browser, mobile, and desktop, but
the native visual harness should be rerun on a Tcl/Tk-capable host before execution
freeze review.

### CLEAN

- G-EVID1 files and historical verdict remain untouched.
- No semantic prompt, corpus, gold, policy, metric, or gate changed.
- No production model output was observed.
- No pilot or experiment ran.
- No beliefs, memories, policies, or installations changed.

## Verdict

**READY FOR STRUCTURAL PILOT AND EXECUTION-FREEZE REVIEW.**

This is implementation readiness only. It grants no pilot, provider, freeze,
installation, or experiment-execution authority. The unresolved independent-gold
and live-provider gates prevent execution freeze today.
