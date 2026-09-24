# G-ROUTE2 contamination and comparability analysis

Decision: **reuse the exact G-ROUTE1 fixture corpus and evaluator-only gold** under a new transport
contract, with fresh seeds and a fresh schedule.

Both options were assessed. Reuse was chosen because it is the only design that answers Q1, not
because it is cheaper.

## Why not a fresh sibling corpus

A fresh corpus with matched task classes, risk structure, difficulty and validator coverage would
give independent replication. It would also change two variables at once. Q1 asks what happens to
qualification when the transport contract changes; measuring that on different fixtures confounds
the transport change with corpus difficulty, and no arithmetic afterwards can separate them. A
sibling corpus answers a different and later question — does the G-ROUTE1 result generalize — which
is worth asking on its own and is not asked here.

## What reuse costs, stated plainly

**G-ROUTE2 is a controlled contrast, not independent replication.** It cannot confirm that the
G-ROUTE1 findings generalize beyond these 24 fixtures. Nothing in the freeze claims otherwise.

## Model exposure

The three models are static local weights — `qwen2.5:7b`, `qwen3:14b`, `qwen3.8:27b` — pinned by
manifest digest and blob digest, unchanged since G-ROUTE1 and unchanged by it. The corpus was
authored for this project and has never been published. Every call runs in a fresh session with zero
retries and no cross-call state, so nothing carries between G-ROUTE1 and G-ROUTE2 or between calls
within either.

There is therefore no mechanism by which a model could have learned this corpus from having been
asked it before. Prior exposure exists in the sense that the same prompts were sent; it does not
exist in any sense that could change a response. Seeds differ (42000 base against G-ROUTE1's 41000
range) so the draws are independent, though Ollama does not attest that a submitted seed was
honored, so independence is assumed rather than proven.

## The contamination that is real: the designer

The meaningful risk is not the models. It is that the G-ROUTE1 outcomes are known to whoever designs
G-ROUTE2, and could be used to fit the new contract to a result already seen.

Three places that could have happened, and what was done about each:

**Thresholds.** Every numeric gate was fixed before any G-ROUTE2 output exists, recorded in
`thresholds.json` with `thresholds_frozen_before_provider_contact: true`, and justified in prose by
what the gate is for rather than by any observed number. The unsafe-early-stop bound of 0.05 is the
point at which a stop signal stops being worth consulting at all; the useful-admission floor of 0.25
is the point below which adaptive routing saves too little to justify the machinery.

**Trigger definitions.** `transport_wrapper_normalized` was motivated by the replay diagnostic — the
observation that canonicalizing 60 outputs would add 36 acceptances but only 6 correct answers. That
is design informed by observed data, and it is declared rather than hidden. It is *calibration-free*:
the trigger takes no threshold and fires on a boolean the normalization layer already records, in the
conservative direction. The distinction that matters is between being informed by evidence and being
fitted to it; nothing here is fitted.

**Trigger vacuity.** Two candidate definitions were discarded because they fired on the corpus's own
reference answers, which would have measured the corpus rather than the model. The suite now asserts
permanently that no trigger fires on any reference answer, and that admission stays non-trivial.

## Leakage boundaries held

G-ROUTE1's results are not reused as if produced under the new contract. The replay diagnostic reads
its raw records read-only, is labelled `counterfactual / prospective normalization diagnostic`,
carries `is_canonical_result: false` and `amends_g_route1: false`, and its numbers appear nowhere in
any G-ROUTE2 qualification. The G-ROUTE1 result package digests are re-verified by the suite so any
accidental modification fails a test.

## Comparability

Model identities, every generation option, the gold, the validators and the prompt profiles are
byte-identical to G-ROUTE1, and the digests are bound into the freeze and checked before the schedule
is built. G-ROUTE2 changes the transport contract and the routing policy and nothing else.

The strongest comparison is not against G-ROUTE1 at all: each G-ROUTE2 response is scored under both
contracts from the same bytes, so the transport effect is measured within-sample, free of any
sampling or cross-run difference.
