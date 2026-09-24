# G-ROUTE1 Scoring Contract

Status: implementation candidate; no benchmark execution authority.

## Units and denominators

- 24 unique fixtures.
- 72 exact task-class x risk-class x model-tier qualification cells.
- 3 scientific repeats per cell.
- 216 scheduled calls total.
- No ambiguity diagnostics exist in this corpus; their denominator is explicitly zero and excluded from crisp rates.

An exact qualification cell passes only when all three scheduled observations exist, all three are operationally accepted, all three pass the frozen evaluator, no false-clean error occurs, no infrastructure failure occurs, and no returned-model mismatch occurs. Aggregate performance cannot override a hard failure. Missing observations cannot pass vacuously.

## Validation separation

The runner applies a gold-blind operational validator first. The frozen evaluator-only validator then measures semantic correctness. An output accepted by the operational validator but rejected by the evaluator is a false-clean error and blocks that exact cell.

The primary result is the 72-cell qualification matrix. Latency and token throughput are descriptive and are never allowed to qualify a semantically failing cell. There is no overall model leaderboard.

## Escalation simulation

Simulation begins at `small`, then checks `mid`, then `large`, and finally returns `no_qualified_model`. An accepted mid-tier observation prevents a jump to large. A false-clean acceptance is reported as incorrectly preventing escalation. This is evaluation only; production routing and automatic escalation remain disabled.
