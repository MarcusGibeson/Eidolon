# G-ROUTE2 — prospective experiment design

Status: **design and freeze only.** No model has been contacted under this contract.
Provider generation calls: **0**. Production routing: disabled. Belief effects: `none`.

G-ROUTE1 is historical scientific evidence and is neither modified nor reinterpreted here. Its
raw records are read once, read-only, for a diagnostic replay that is explicitly labelled
non-canonical.

## The two research questions

G-ROUTE2 answers two questions that G-ROUTE1 entangled, and keeps them separable by construction.

**Q1 — transport.** How does tier qualification change when a harmless JSON transport wrapper is
normalized prospectively and identically for every model?

G-ROUTE1 measured 31/72 structural validity for `qwen3.8:27b` against 72/72 for `qwen3:14b`. All 41
of the 27B's `malformed_json` rejections were ```` ```json ```` fences whose contents parsed cleanly, and
the 14B never fenced once. The frozen contract was right to fail them, but the resulting ordering is
a formatting convention, not a difference in reasoning. Q1 asks what is left once that is removed.

**Q2 — stopping.** Can a stronger prospective escalation policy reduce false-clean early stops
without destroying useful admission?

G-ROUTE1 recorded 56 false-cleans, and 35 of them stopped simulated escalation at a tier whose
answer was semantically wrong. Gold-blind operational acceptance — the only signal a real router
could consult — shipped those answers. Q2 asks what deterministic, observable evidence beyond bare
acceptance is needed before a router may stop.

The two questions are deliberately not one question. Normalization changes what is *measured*;
the escalation policy changes what is *shipped*. The policy fires `transport_wrapper_normalized`
at every risk class, so a canonicalized response can never itself end escalation, which keeps
Q1's answer from leaking into Q2's.

## Design: paired within-response scoring

Every JSON-profile output is scored twice from the same bytes — once under the raw transport
contract G-ROUTE1 used, once under the normalized contract. The transport effect is therefore a
**within-sample** contrast with no cross-run sampling noise, and formatting and reasoning effects
stay separable inside a single experiment.

Qualification is decided under the normalized contract. The raw-contract matrix is scored and
reported beside it.

## Corpus: the exact G-ROUTE1 corpus, reused deliberately

G-ROUTE2 reuses `G-ROUTE1-FIXTURES-R1` and `G-ROUTE1-GOLD-R1` byte-for-byte, with both digests bound
into the freeze and verified before schedule construction.

This is not convenience. Q1 is a contrast about transport. Changing the corpus at the same time as
the transport contract would confound the variable under study with corpus difficulty and make Q1
unanswerable. The full reasoning, including what reuse costs, is in `CONTAMINATION_ANALYSIS.md`.

The consequence is stated plainly: **G-ROUTE2 is a controlled contrast, not independent
replication.** Independent replication on a fresh sibling corpus is a separate later experiment and
is not claimed here.

What does change: fresh seeds (base 42000, no overlap with G-ROUTE1's 41000 range), a different
schedule ordering salt, and a distinct `GROUTE2-` call-id namespace. The observations are new draws.

## Unchanged on purpose

Model identities, every generation option, the evaluator-only gold, the frozen validators and the
prompt profiles are identical to G-ROUTE1. G-ROUTE2 changes the transport contract and the routing
policy and nothing else, so any difference in qualification is attributable to those two changes.

## Structure preserved

Qualification remains per `task class × risk class × model`, 72 cells, 3 observations each, missing
data cannot pass, and there is no global model winner and no averaging across tasks. The matrix still
supports 7B qualifies, 14B qualifies, 27B qualifies, no model qualifies, and insufficient evidence.
Selection remains cheapest qualified tier, and only after qualification is established under the new
contract. R4 remains evidence-only.

## Three verdicts, never one

`output_accepted`, `model_cell_qualified` and `safe_to_stop_escalation` are separate and may
disagree in any combination. See `ESCALATION_POLICY.md`.

## Execution shape

24 fixtures × 3 models × 3 repeats = 216 calls. Fresh session per call, zero retries, no output
repair, no silent fallback. Schedule, gold, thresholds, normalization contract, escalation policy and
scorer are all frozen before contact.
