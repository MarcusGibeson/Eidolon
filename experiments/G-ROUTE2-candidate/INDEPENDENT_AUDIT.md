# G-ROUTE2 Independent Design Audit

Date: 2026-09-24
Verdict: **READY**
Authority: non-authoritative design audit. It grants no execution, provider, routing, source-apply
or belief authority, and it changes no artifact.
Provider generation calls during design and audit: **0**.

## Normalization scope

The layer canonicalizes two shapes and refuses everything else. Prose around the payload, multiple
fenced blocks, multiple JSON values, malformed JSON, unsupported fence tags, unterminated fences and
ambiguous nesting all fail closed and reach structural validation as the model wrote them. Root type
is left to structural validation, so no structural opinion is smuggled into a transport outcome.

The layer is a pure function of the output text and the validator profile, with no clock, randomness
or external state. Determinism is asserted directly.

**Audited: in scope, narrow, model-agnostic, applied identically to all three tiers.**

## Semantic non-interference

Three independent demonstrations agree.

By construction, the only transformation is delimiter removal, and the layer refuses its own output
if the canonicalized payload does not parse equal to the fence body. By test, `semantic_values_preserved`
holds on every adversarial case including a pretty-printed body. By replay over all 216 frozen
G-ROUTE1 raw records: every raw output byte-preserved, every parsed value unchanged, and **zero
judged semantic failures converted into passes**. The only outcomes that change are failures whose
sole cause was a transport parse error, which is the intended effect.

Independent re-derivation confirms the replay harness itself: replaying the raw contract reproduces
G-ROUTE1's canonical figures exactly — 104 operational acceptances and 48 semantic passes — so the
harness is measuring the same thing the frozen scorer measured.

**Audited: normalization does not change semantic values and does not suppress semantic failures.**

## False-clean measurability

False-clean is defined identically under both contracts as operational acceptance with evaluator
failure, and is reported per cell and globally, never folded into an accuracy figure. Validator-
detected and validator-missed failures are reported separately and must sum to total semantic
failures, an arithmetic identity the G-ROUTE1 audit already exercised.

**Audited: measurable and separately reported.**

## Escalation policy observability

Every trigger was traced to its inputs. All seven read only the model output, the model-facing
fixture input, and the frozen routing table. None reads gold. None reads a self-reported confidence
field. The policy record carries `uses_gold: false` and
`uses_model_self_reported_confidence: false`, and the suite asserts both.

The three verdicts are separately represented and are exercised in disagreeing combinations:
accepted-but-unqualified, qualified-but-triggered, accepted-but-never-safe at evidence-only risk.

One design property deserves explicit note. `transport_wrapper_normalized` fires at every risk
class, which makes the gate "zero unsafe terminal acceptance attributable solely to normalization"
**structurally guaranteed rather than empirically tested**. That is a legitimate way to hold a
safety property, but it must be read as a design invariant and not as an empirical finding. The
freeze and the threshold rationale both say so.

**Audited: deterministic, observable, and honest about what is guaranteed by construction.**

## Thresholds

All numeric gates are recorded before contact with `thresholds_frozen_before_provider_contact: true`
and are justified by what each gate is for rather than by any observed number. The unsafe-early-stop
bound and the useful-admission floor are declared judgment calls, made before any G-ROUTE2 output
exists, and are stated as such.

**Audited: frozen before contact, justified prospectively.**

## Corpus contamination

Reuse is argued from the structure of Q1 rather than from convenience, and the cost is stated
plainly: G-ROUTE2 is a controlled contrast, not independent replication. Model exposure is analysed
and dismissed on mechanism — static local weights pinned by digest, an unpublished corpus, fresh
sessions, no cross-call state — with the seed-honoring caveat retained.

The audit agrees that the real contamination risk is the designer, not the models, and finds the
three mitigations adequate: thresholds frozen and prose-justified; trigger definitions
calibration-free; and two candidate triggers discarded for firing on the corpus's own reference
answers, with that property now permanently asserted.

`transport_wrapper_normalized` was motivated by the replay diagnostic. This is design informed by
observed data and is declared in both the policy and the contamination analysis. It takes no
threshold, fires on a recorded boolean, and moves only in the conservative direction, so it is
informed rather than fitted. **Recorded as a known and declared influence, not a finding against.**

**Audited: analysed explicitly, reuse justified, costs stated.**

## Task and risk balance

24 fixtures across 6 task classes, 4 per class, 6 per risk class, 72 cells, 3 repeats each. The
schedule is balanced so each tier leads exactly once per fixture across its three repeats, and the
schedule validator fails closed on count, duplicate, position, coverage and first-tier imbalance.

**Audited: balanced and unchanged from the inherited design.**

## Qualification arithmetic

Qualification requires three complete observations, three operational acceptances, three evaluator
passes, no false-clean, no infrastructure failure and no returned-model mismatch. A two-observation
cell is verified to be incomplete and unqualified, and no zero-observation cell can qualify.
Structural validity alone cannot qualify. Per-cell structure is preserved with no global winner.

**Audited: no vacuous pass, no pass on missing data, no averaging.**

## Leakage from G-ROUTE1 outcomes

The replay reads G-ROUTE1's raw records read-only and is labelled
`counterfactual / prospective normalization diagnostic` with `is_canonical_result: false` and
`amends_g_route1: false`. Its figures appear in no G-ROUTE2 qualification. The suite re-verifies
every digest in the G-ROUTE1 result package, so an accidental modification fails a test.

**Audited: no retroactive reinterpretation, no reuse of G-ROUTE1 results as new-contract results.**

## Authority boundaries

`production_routing_authorized: false`, `automatic_escalation_authorized: false`,
`belief_effects: none` in the thresholds, the policy records and the freeze. Every simulation record
carries `production_routing_invoked: false`. No runner is wired to a provider in this phase.

**Audited: no production-routing authority, no belief effects.**

## Execution harness

The governed runner is bound into the freeze alongside the reused G-ROUTE1 persistence, provider and
Activity layers, which it imports without modification. It refuses to contact a provider without an
authorization artifact carrying the exact freeze digest and the matching confirmation string, and
rejects a wrong digest, a wrong benchmark name and a G-ROUTE1-shaped confirmation. A mutation guard
over 19 paths is recomputed before every call and again after scoring.

A complete provider-free 216-call run reaches five-view terminal agreement at 216/217, resume after
terminal is refused before the provider is callable, pause at four calls resumes to exactly 216 with
no duplicates, and a returned-model mismatch stops the run incomplete without retry.

Two defects were found and fixed during harness construction, both of the same family the design
phase already surfaced twice — a rule that cannot fire is a rule the document lies about:

* `repeat_disagreement` had no producer. Nothing compared the repeats, so the trigger could never
  have fired in a real run. Scoring now settles every record's verdicts once the repeats exist.
* Isolated coding evidence was not persisted on the record, so when scoring re-derived the verdicts
  it saw no test evidence and fired `grounding_weak` on all 36 coding calls. The runner now stores
  it, and a regression asserts the trigger stays silent on passing coding answers.

**Audited: the harness exists, is bound by digest, and is guarded during execution.**

## Verdict

**READY** for explicit scientific execution authorization. No model may be contacted under this
contract until that authorization is issued separately and bound to the frozen digest.
