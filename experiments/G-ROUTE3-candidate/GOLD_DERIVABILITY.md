# Gold derivability

**Rule.** The gold answer for every fixture must be derivable from what the model is shown: the profile
system prompt, the fixture prompt and the fixture input. Concretely:

1. every closed-vocabulary label in gold — research recommendations and uncertainty codes, synthesis
   conclusions and roles, planning actions and uncertainty codes, extraction enum values — appears in the
   model-facing text as an explicit allowed set;
2. every ordering the validator enforces is stated in the prompt (planning step numbering, dependency
   chaining, evidence-id order, uncertainty-code order);
3. every execution constraint is disclosed: the full coding whitelist, including that only `.parts` may be
   read, that helper functions may not be called, and every denied statement form; the conversation
   answer frame and length limit; and the 350-token output budget in every JSON prompt;
4. where selection is required (which planning actions to include, which sources to cite, which status a
   claim takes, which conclusion applies), the rule that decides it is stated, and overlapping rules carry
   an explicit order;
5. every format the grader enforces is stated: exact key sets, `depends_on` as a list, and extraction spans
   copied as written without leading articles or labels;
6. no grader rejects a correct answer for wording the model was never told to use. Conversation is judged
   on a disclosed closed option set, not on phrase anchors. Each conversation fixture carries three
   alternative correct replies in varied formats and four incorrect ones, and both validators are run on all
   of them;
7. no listed order gives the answer away: planning actions are never listed in gold order, and a
   conversation answer's position in its option list is pseudo-random.

The rule is checkable without any model output. It is enforced by `authoring/assemble_g3.py`, which refuses to
write the corpora if any check fails, and by deterministic tests over all 96 fixtures.

Items 1–4 alone were not enough. Two external pre-contact reviews found correct answers still failing on
hidden grader rules. Items 5–7 and the wider item 3 come from those reviews; see
`EXTERNAL_REVIEW_ROUND1.md` and `EXTERNAL_REVIEW_ROUND2.md`.

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

## A second defect in G-ROUTE1's conversation operational check

The round-1 external review found a grader rule in `g_route1_operational.py` that no model was told about.
For `conversation.v1` it rejects any reply containing words such as "completed", "approved", "deployed" or
"I have", **including negations**. "The refund hasn't been completed" is rejected, even when the fixture's
own prompt asks the model not to describe the refund as completed.

G-ROUTE1 and G-ROUTE2 used this check. Some of their conversation rejections and non-qualifications may
therefore reflect wording, not behavior. This has **not** been quantified, and neither experiment is rescored
or amended. Their conversation results carry this caveat alongside the research, synthesis and planning
caveat above.

## What G-ROUTE3 does about it

For research, synthesis, extraction and planning, the semantic evaluator `g_route1_validators.py` is used
byte-for-byte. Research, synthesis and planning remain strict exact-match profiles, and planning still
requires exact equality, including list order. Coding uses the same evaluator, after `old` is canonicalized
for trailing newlines only.

The operational check is `g_route3_operational.py`. It is G-ROUTE1's operational validator for every
profile except conversation and coding. Conversation uses the disclosed answer frame, with an action-claim
check that never matches a negation. Coding uses the same trailing-newline canonicalization. G-ROUTE1's
module is not modified.

Everything else was repaired in the fixtures, not the checks:

- vocabularies are supplied;
- ordering conventions and rule precedence are stated;
- selection rules are explicit;
- the complete coding whitelist is disclosed in every coding prompt;
- conversation fixtures state their answer options and the frame, and the output budget is stated.

## Limitation this introduces

Making gold derivable narrows what some fixtures test. A planning fixture now tests whether a model follows
stated precedence, exclusion and ordering rules exactly, not whether it can invent a good plan unaided.
That is a deliberate trade: a fixture whose answer cannot be derived tests the grader, not the model.
