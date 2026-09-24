# G-ROUTE3 routing policy

Contract: `g-route3.routing.v1` · implementation `tools/g_route3_routing.py`

## Inputs the router may use

Task class, risk class, the frozen qualification table, model availability, the gold-blind operational
validation of the canonicalized payload (`g-route3.operational-validator.v2`), the transport normalization outcome, provider and infrastructure
status, isolated coding execution evidence, and two conservative triggers.

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

Contract `g-route3.triggers.v1`, implementation `tools/g_route3_triggers.py`. G-ROUTE2's policy module is
not modified.

Retained as **additional conservative escalation reasons**, never as evidence that an answer is correct:

- `grounding_weak` — a settled research claim cites no source or lineage; a synthesis statement cites no
  observation, or shares no content token (a number, or a word of four or more letters) with the observations
  it cites; or a planning step cites no evidence. Tokens split on every non-alphanumeric character and at every
  digit–letter boundary, so a faithful restatement such as "11C for 40min" of "11 C for 40 min" is grounded.
- `structural_anomaly` — empty content where the profile requires content.

Retired, with reasons recorded in `thresholds.json`:

- `source_independence_insufficient` — its condition, an independent lineage available *for this particular
  claim*, cannot be decided without knowing which sources are about which claim, which is a semantic judgment.
  The fixture-wide approximation fired on correct answers (B-RESEARCH-R3-2) and let a wrong answer stop.
  Retired after the round-1 external review.
- `transport_wrapper_normalized` — qualification already runs under the normalized contract with zero
  false-cleans allowed, so a qualified tier's canonicalized output carries the same evidence as a raw one.
  Normalization is recorded and reported, not used to block.
- `validator_coverage_thin` — it would block conversation stops at R2 and R3 regardless of qualification,
  and so prevent the primary question from being measured in those cells.
- `repeat_disagreement` — Corpus B has one sample per tier, and a live router would pay for repeats. Repeat
  stability is required inside qualification instead, where all four observations must pass.

The coding branch of `grounding_weak` was removed. Failed coding evidence is never operationally accepted, so
that branch could not fire on an accepted output.

Some branches inside the triggers are defensive: they are total over any payload, but they cannot fire on an output the operational validator has already accepted, such as an unparseable payload or an empty claim list. The module lists them. No retained trigger is dead code. Both retained triggers fire in a deterministic test. Neither fires on any of the 96
reference answers or the 48 alternative correct answers, and a test asserts this. The suite also asserts
that the retired triggers are absent from the router.

Model self-reported confidence is not used anywhere.
