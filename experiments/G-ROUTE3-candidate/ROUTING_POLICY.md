# G-ROUTE3 routing policy

Contract: `g-route3.routing.v1` · implementation `tools/g_route3_routing.py`

## Inputs the router may use

Task class, risk class, the frozen qualification table, model availability, the gold-blind operational
validation of the canonicalized payload, the transport normalization outcome, provider and infrastructure
status, isolated coding execution evidence, and three conservative triggers.

It never receives validation gold, semantic correctness, expected answers, fixture safety labels, or any
scorer output. It sees a whitelisted **runtime view** of each output. `assert_gold_blind` rejects any view
carrying a semantic or gold field, and the routing module imports no gold loader. Both properties are
asserted in tests.

## Three verdicts, never one

| Verdict | Meaning |
|---|---|
| `output_accepted` | the canonicalized output passes the frozen operational contract and no infrastructure failure occurred |
| `model_cell_qualified` | the table lists this tier as qualified for this task × risk cell |
| `safe_to_stop_escalation` | accepted **and** qualified **and** no conservative trigger fired **and** not R4 |

An accepted output from an unqualified tier can never stop routing.

## Starting tier

The cheapest **qualified** tier for the cell. Unqualified tiers are never contacted by the router.

| Qualified tiers | Start | Ladder |
|---|---|---|
| 7B, 14B, 27B | 7B | 7B → 14B → 27B |
| 14B, 27B | 14B | 14B → 27B |
| 7B, 27B | 7B | 7B → 27B (14B skipped) |
| 27B only | 27B | 27B |
| none | — | `no_qualified_model`, zero routing calls |

## Escalation

If a qualified tier's output is rejected, or a trigger fires, the router moves to the **next higher
qualified tier only**. An unqualified intermediate tier is skipped, and a qualified one is never skipped. If
no higher qualified tier remains, the outcome is `escalation_exhausted`, a fail-closed terminal state.
An unqualified model is never used silently.

R4 cases return `evidence_only` with no routing contact, as in every prior G-ROUTE experiment.

## Triggers

Retained as **additional conservative escalation reasons**, never as evidence that an answer is correct:

- `grounding_weak` — a settled claim, statement or step binds no evidence, or coding evidence has no test;
- `source_independence_insufficient` — several cited sources collapse to one lineage when another lineage
  was available;
- `structural_anomaly` — empty content where the profile requires content.

Retired, with reasons recorded in `thresholds.json`:

- `transport_wrapper_normalized` — qualification already runs under the normalized contract with zero
  false-cleans allowed, so a qualified tier's canonicalized output carries the same evidence as a raw one.
  Normalization is recorded and reported, not used to block.
- `validator_coverage_thin` — it would block conversation stops at R2 and R3 regardless of qualification,
  and so prevent the primary question from being measured in those cells.
- `repeat_disagreement` — Corpus B has one sample per tier, and a live router would pay for repeats. Repeat
  stability is required inside qualification instead, where all four observations must pass.

No trigger is dead code. Every retained trigger fires in a deterministic test, and the suite asserts that the
retired ones are absent from the router.

Model self-reported confidence is not used anywhere.
