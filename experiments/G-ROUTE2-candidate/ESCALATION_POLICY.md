# G-ROUTE2 routing policy

Contract: `g-route2.routing-policy.v1`
Implementation: `tools/g_route2_policy.py`

## Three verdicts that must never collapse into one

| Verdict | Question | Source |
|---|---|---|
| `output_accepted` | Is this response structurally usable? | gold-blind operational validator, on the canonicalized payload |
| `model_cell_qualified` | Has this tier been shown capable of this task at this risk? | frozen routing-table lookup for `task × risk × tier` |
| `safe_to_stop_escalation` | May the router ship this response without corroboration? | accepted, and no deterministic trigger fired |

They are separate because G-ROUTE1 showed what happens when they are not. A response can be
structurally perfect from a tier that has never qualified for the cell; a qualified tier can produce
a response carrying an escalation trigger; an accepted response at an evidence-only risk class can
never stop. All three combinations are exercised in the adversarial suite.

`safe_to_stop_escalation` is the table-free verdict and is the primary reported metric, because it
needs no gold and no qualification table and is therefore deployable as-is.
`safe_to_stop_table_bound` additionally requires the cell to be qualified.

## Escalation triggers

Every trigger is deterministic and computable from the model output, the model-facing fixture input
and the frozen routing table alone. **No trigger reads gold. No trigger reads the model's
self-reported confidence.** Gold appears only in scoring.

| Trigger | Fires when |
|---|---|
| `transport_wrapper_normalized` | the response needed canonicalization, at any risk class |
| `evidence_only_risk` | the risk class is R4 |
| `validator_coverage_thin` | the profile's gold-blind validator does no field-level verification, above R1 |
| `grounding_weak` | a settled claim, statement or step binds no evidence, or coding evidence has no test |
| `source_independence_insufficient` | several cited sources collapse to one lineage *and* another lineage was available |
| `structural_anomaly` | an accepted payload carries empty content where the profile requires content |
| `repeat_disagreement` | repeats of the same fixture and tier disagree on acceptance |

### Why `transport_wrapper_normalized` fires at every risk class

The replay diagnostic over G-ROUTE1's raw records showed that canonicalizing 60 fenced outputs would
have produced **+36 operational acceptances but only +6 semantic passes** — roughly thirty of the
newly accepted responses were wrong. Normalization on its own makes the gold-blind stop signal
*less* safe, by converting silent transport rejections, which correctly escalated, into
confident-looking acceptances of wrong answers.

Firing at every risk class makes the gate "zero unsafe terminal acceptance attributable solely to
normalization" structurally guaranteed rather than empirically hoped for, and keeps Q1 from leaking
into Q2. Normalization changes what is measured; it never changes what is shipped.

### Why `validator_coverage_thin` covers conversation fixtures

`conversation.v1` acceptance checks length and a forbidden-action-claim regex and nothing else. It
performs no field-level verification against the fixture, so its acceptance carries almost no
evidence. This is inspectable from the validator source without reference to any outcome. It is
exempt at R1, where a wrong conversational answer is low-consequence.

### A trigger that fires on the reference answer measures the corpus

Two trigger definitions were discarded during design for exactly this reason, before freeze:

* requiring two citations and two lineages for a settled claim — the frozen corpus binds each claim
  to a single source, so the *reference* answer would have tripped it and research could never have
  stopped;
* treating any two same-lineage citations as insufficient independence — `RESEARCH-R3`'s evidence is
  legitimately single-lineage, and its reference answer cites two sources from that one lineage.

The surviving definitions require that a genuinely independent citation was available and was not
taken. The suite permanently asserts that **no trigger fires on any fixture's reference answer**,
except the two deliberately structural ones, and that at least twelve fixtures spanning five task
classes can actually stop. A policy that escalates everything is trivially safe and useless.

## Simulation

`small → mid → large → no_qualified_model`, in that order, stopping at the first tier where
`safe_to_stop_escalation` holds. An accepted mid-tier response is never skipped in favour of large.
Simulation only: production routing is not invoked and automatic escalation remains disabled.

## What this policy does not claim

It is not a semantic oracle. It cannot tell a true answer from a false one, and it is not treated as
if it could. It identifies deterministic, independently observable reasons to *doubt* a stop, which
is a strictly weaker and honestly achievable thing.
