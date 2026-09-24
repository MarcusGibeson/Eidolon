# G-ROUTE1 deterministic validator audit

**Verdict:** `VALIDATOR SIGNOFF CLEAN FOR FIXTURE FREEZE`

This audit covers the validator contract only. It does not claim that the future runner, scorer, Activity adapter, provider configuration, or production router exists.

## Adversarial matrix

| Attack | Expected behavior | Deterministic proof |
|---|---|---|
| empty or malformed structured output | fail closed | object parser tests through malformed-schema cases |
| conversation claims an action completed | fail hard gate | staging-token adversarial fixture test |
| extraction omits/adds/invents a field | fail hard gate | provider-proposal extra-field test |
| repeated citation presented as independence | fail hard gate | duplicate-lineage research test |
| recommendation exceeds evidence rule | fail hard gate | same-lineage upgrade overrecommendation test |
| synthesis changes semantic role | fail hard gate | R4 role-drift test |
| synthesis silently drops an observation | fail hard gate | R4 dropped-observation test |
| synthesis merges unlike roles | fail hard gate | validator role-set rule |
| coding changes an unapproved path | fail hard gate | traversal-repair wrong-path test |
| coding evidence absent or digest-mismatched | fail hard gate | isolated-evidence tests |
| validator directly executes model source | impossible in this module | coding validator has no subprocess or dynamic execution path |
| plan claims completed work | fail hard gate | R4 planning adversarial test |
| plan requests expanded authority | fail hard gate | R4 planning adversarial test |
| model tier changes expected answer | impossible by contract | prompt profiles and validators contain no model/tier branch |
| gold enters model-facing corpus | fail structural checks | corpus/gold separation test |
| R4 result creates adaptive authority | denied | design-bound R4 evidence-only test |

## Reference validation

- All 24 authored reference outputs pass their respective validators.
- The four authored coding reference candidates compile and pass their focused tests in disposable directories.
- Coding model output will require separately produced, digest-bound isolated-run evidence. The validator cannot manufacture that evidence.
- Every result includes `belief_effects = none` and `routing_authority = false`.

## Known limitations retained for the next phase

1. Conversation checks are deterministic contract checks, not a comprehensive subjective-quality evaluator.
2. Coding execution evidence is specified and validated, but the isolated runner that produces it is intentionally not part of this corpus freeze.
3. No scorer, schedule, Activity adapter, persistence layer, provider verifier, or benchmark runner is implemented here.
4. Model-specific qualification remains completely unknown until an independently authorized frozen run occurs.

These limitations do not invalidate the fixture/validator freeze. They prevent it from being mistaken for an executable benchmark.
