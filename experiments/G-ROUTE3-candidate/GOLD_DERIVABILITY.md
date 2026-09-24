# Gold derivability

**Rule.** The gold answer for every fixture must be derivable from what the model is shown: the profile
system prompt, the fixture prompt and the fixture input. Concretely:

1. every closed-vocabulary label in gold — research recommendations and uncertainty codes, synthesis
   conclusions and roles, planning actions and uncertainty codes, extraction enum values — appears in the
   model-facing text as an explicit allowed set;
2. every ordering the validator enforces is stated in the prompt (planning step numbering, dependency
   chaining, evidence-id order, uncertainty-code order);
3. every execution constraint is disclosed (the coding fixtures' operation whitelist);
4. where selection is required (which planning actions to include, which sources to cite, which status a
   claim takes), the rule that decides it is stated.

The rule is checkable without any model output, and it is enforced by a deterministic test over all 96
fixtures.

## Why

The inherited G-ROUTE1 corpus violated this rule in four places, and doing so decided outcomes.

| Diagnostic over frozen G-ROUTE2 records (read-only, non-canonical) | Result |
|---|---|
| Research claim judgments exactly right | 22 of 36 |
| Research gold recommendation code emitted | **0 of 36** |
| Research gold uncertainty codes emitted | **0 of 36** |
| Research gold recommendation codes visible to the model | 1 of 4 |
| Synthesis responses failing *only* on the conclusion code | **33 of 36** |
| Synthesis gold conclusion codes visible to the model | **0 of 4** |
| Emitted planning actions matching any gold action | **0 of 100** |
| Planning gold actions visible to the model | **0 of 15** |
| Coding outputs outside the undisclosed whitelist | 9 of 36 |

The models were writing prose recommendations ("Do not recommend promotion.") and prose plan steps because
they had never been given the code vocabulary the gold expected. The synthesis itself — roles, coverage,
meaning anchors — was right in 33 of 36 responses that were scored as failures.

## What this means for earlier results

G-ROUTE1 and G-ROUTE2 remain valid executions of their frozen contracts, and neither is rescored or
amended. But the finding that no tier qualifies in grounded research synthesis, hierarchical semantic
synthesis or reflective planning, in both experiments, should be read as **substantially unanswerable as
posed**, not as a negative capability result. G-ROUTE2's 15 unsafe stops, which all fell in those classes,
carry the same caveat.

This diagnostic is stored as `GOLD_DERIVABILITY_DIAGNOSTIC.json`, labelled
`counterfactual design diagnostic`, with `is_canonical_result: false`.

## What G-ROUTE3 does about it

Nothing in the validators changed. G-ROUTE3 uses `g_route1_validators.py` and `g_route1_operational.py`
byte-for-byte. Research, synthesis and planning remain strict exact-match profiles, and planning still
requires exact equality including list order. The fixtures, not the checks, were repaired: vocabularies are
supplied, ordering conventions are stated, selection rules are explicit, and the coding whitelist is
disclosed in every coding prompt.

## Limitation this introduces

Making gold derivable narrows what some fixtures test. A planning fixture now tests whether a model follows
stated precedence, exclusion and ordering rules exactly, not whether it can invent a good plan unaided.
That is a deliberate trade: a fixture whose answer cannot be derived tests the grader, not the model.
