# G-ROUTE1 Blocked Scientific Execution — R2

Date: 2026-09-24
Status: preserved incomplete scientific execution. Not a scientific result.
Authority: none. No gate reinterpreted, no threshold moved, no protected dependency patched.

## What happened

The authorized one-shot execution of `G-ROUTE1-EXECUTION-R2` passed every preflight check and began the frozen
216-call schedule. It stopped at schedule position 57 when the **frozen evaluator raised an unhandled
`TypeError`** on a provider output it should have classified as a model-produced failure.

```
tools/g_route1_validators.py:124  _normalize_research
    if len(uncertainties) != len(set(uncertainties)):
TypeError: unhashable type: 'dict'
```

The run was classified `incomplete` under the frozen abort rules. Nothing was retried, repaired, or invented.

- run/job id: `groute1_20260924T022359279436Z`
- source commit during execution: `91ba0d2e13f2820326022b0164f17731f386e161`
- execution-freeze digest bound into the authorization: `0c2f8da7805c4cf4e474b828ea7b5b29b9a33104821ff3ffefa1e3172e8c827f`
- scheduled calls 216 · persisted calls 56 · provider generation calls 57
- position 57 was contacted but its output was never durably persisted, so it is lost, not recoverable, and not re-requested

## The defect

`_normalize_research` de-duplicates `uncertainties`, `citations` and `lineages` with `set()`. A response whose
elements are objects or lists rather than strings raises `TypeError` before any judgment is formed. The gold-blind
operational validator carries the same defect on `citations` and `lineages`.

Reproduced offline against the frozen modules, with zero provider calls:

| Output shape | Operational validator | Frozen evaluator |
|---|---|---|
| `uncertainties: [str]` | accepted | judged (fails gold) |
| `uncertainties: [object]` | accepted | **TypeError** |
| `uncertainties: [list]` | accepted | **TypeError** |
| `citations: [object]` | **TypeError** | **TypeError** |
| `lineages: [object]` | **TypeError** | **TypeError** |

This violates the benchmark's own stated principle that a wrong or malformed model answer is scientific data.
A model that answers badly in a structurally legal way can halt the benchmark instead of scoring zero.

Affected protected artifacts, unchanged by this task:

- `tools/g_route1_validators.py` — `09ccdeea1ccf0a6178ebe3f9b76696e99e3170173a485a2bf9eb91d54f66d27e`
- `tools/g_route1_operational.py` — `52385711a8457b0583c8369606d09f49e03af20fca1193206cba8143c9eb08b1`

## Integrity of what was collected

Every one of the 56 persisted records verified: sequential positions 1–56, no duplicates, no omissions within
range, record digests valid, schedule binding exact, request-body digests recomputed and matching, raw provider
envelopes matching their recorded digests, requested model equal to returned model on every call, zero provider
fallbacks, zero transport failures. The mutation guard `36ced1f08130f89361437bd6ee38e0b7a9f113ceb9db921a8f00a11b03776d48`
agrees before and after, and no frozen artifact drifted during execution.

Terminal state is `incomplete` across run manifest and Activity. No terminal receipt and no terminal checkpoint
exist, which is correct: the completion contract is satisfied only by a complete run.

## Not scored

The benchmark was not scored. 160 of 216 calls were never made, 3 of 72 qualification cells hold three
observations, and missing data cannot pass. No qualification matrix, routing summary, or escalation result is
claimed from this run. The preserved observations are evidence about infrastructure, not about model capability.

## Superseded prospectively

R2 is preserved exactly as executed. It is not edited and not reinterpreted. A repair belongs in a separate
governed task that fixes the evaluator defect, re-runs the deterministic suites, and issues a new execution freeze
(`R3`) for fresh one-shot authorization. R1 remains historical at
`836ee16db8a6f92e08570473c1e553a8ff564e785feb2c80b9ceb56750770029`.

Production routing: disabled. Belief effects: `none`. Automatic escalation: disabled.
Corpus, gold, validators, scorer, thresholds, schedule, policies and model bindings were not altered.
