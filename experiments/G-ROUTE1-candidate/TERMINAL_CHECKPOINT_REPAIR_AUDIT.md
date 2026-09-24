# G-ROUTE1 Terminal Checkpoint Repair Audit

Date: 2026-09-23  
Verdict: **CLEAN**  
Authority: non-authoritative implementation audit; no provider, execution, routing, source-application, or belief authority.

## Finding

The scientific runner finalized its result, manifest, and Activity but did not seal the checkpoint terminally. The checkpoint was updated during call persistence and therefore remained `running` at position 217 after a successful provider-free 216-call run. This made the terminal record internally inconsistent and theoretically resumable.

## Repair

The scientific persistence layer now appends a digest-bound terminal receipt, requires complete-state agreement, validates all 216 call records and the sealed score, and replaces the nonterminal checkpoint exactly once with a terminal checkpoint containing `completed_position = 216`, `next_position = 217`, and `calls_persisted = 216`. Identical finalization is idempotent. Conflicting finalization and any resume of a terminal run fail closed before provider invocation.

The scientific implementation remains independent of the mechanical-pilot namespace, schema, and authority. The repair follows the pilot's already verified terminal-sealing principle without importing pilot code or permitting pilot artifacts to satisfy scientific completion.

## Adversarial verification

| Case | Required behavior | Deterministic result |
|---|---|---|
| Provider-free 216-call run | all terminal views complete at 216/217 | pass |
| Resume after complete | reject before provider callable | pass |
| Duplicate finalization | return identical terminal checkpoint | pass |
| Conflicting terminal state | reject | pass |
| Activity disagreement | reject | pass |
| Missing call count | reject | pass |
| Scorer failure after 216 calls | failed, never complete | pass |
| Provider failure | incomplete, no complete checkpoint | pass |
| Paused run | resumable from exact next position | pass |
| Call-record immutability | terminal seal changes no call bytes | pass |

The G-ROUTE1 scientific corpus, evaluator-only gold, validators, scorer, thresholds, qualification policy, escalation policy, schedule, and model bindings were not changed. G-EVID1 and G-CORROB1 were not changed. Provider generation calls: **0**. Scientific launches: **0**. Production routing: **disabled**. Belief effects: **none**.
