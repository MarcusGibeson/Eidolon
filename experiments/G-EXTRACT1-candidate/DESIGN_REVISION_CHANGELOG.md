# G-EXTRACT1 Design Revision Changelog

This record maps the second adversarial rereview of commit `9ada6f4ceefb805340d0f2226b33a68357ad6788` to design candidate v3. All changes are prospective design-document changes. No blueprint, fixture, reserve, runner, scorer, provider call, or experiment run was created.

## Second-rereview findings

| Finding | Disposition | Candidate v3 repair |
|---|---|---|
| Model-facing operation definitions were underconstrained | Resolved | Added finite `g-extract1.operation-definitions.v1`: exact opening, exact sentence catalog, exact placeholders, one/two-node limit, deterministic order, finite unit-conversion sentences, historical absence sentence, and explicit prohibitions. Free-form instruction text is forbidden. |
| Primary family assignment remained subjective | Resolved | Added frozen metadata schema and first-match predicates for E7, E5, E4, E1, E2, E3, and E6. Difficulty, importance, principal challenge, and author intent are not inputs. |
| Contamination/fingerprint rules were not reproducible | Resolved | Added exact character set, payload, schema serialization, normalization, tokenizer, 5-gram/Jaccard algorithm, six finite fingerprint components, canonical bytes, all-pairs scope, collision rules, near-replay rule, and two-implementation differential requirement. |
| Ambiguity output classifier was not fully mechanical | Resolved | Bound historical `provided|not_provided` and exact `not_provided` instruction. Added nine first-match outcomes using observable fields only. Prose is JSON parse failure; no refusal/evasion interpretation remains. |
| `INVALID` included a subjective catchall | Resolved | Added finite precontact, invalid, incomplete, and abort event catalogs. Removed `cannot be trusted`. Bound provider failures, omissions, interruptions, corrupt evidence, and post-contact gold defects to deterministic classes. |
| Model blob hashes existed only in machine form | Resolved | Added all three blob SHA-256 values to normative Markdown. |
| Seed formula existed only in machine form | Resolved | Added both seed bases, exact formula, collision audit, and balanced-order rule to normative Markdown. |
| Legacy-sized prefix existed only in machine form | Resolved | Added the eight-observation reporting-only prefix and its non-gating status to normative Markdown. |
| Phase B vaguely invoked all redundant guardrails | Resolved | Markdown and JSON now enumerate Phase B family and binding guardrails and mark correlated repeat false-clean not applicable because Phase B has one observation per fixture. |
| Validator PASS was overstated | Resolved | The design now limits validator claims to deterministic structural and cross-representation consistency. The validator checks exact structured fields and explicitly disclaims scientific validity and adversarial-review replacement. |
| Reserve replacement could break composed quotas | Resolved | Reserve identity now binds composed row and required secondary features; activation must preserve every composed count or stop. |

## Prior findings retained as repaired

| Earlier finding | Candidate v3 status |
|---|---|
| Ambiguity recognition versus containment | Retained and tightened in ambiguity v2; malformed containment never earns semantic recognition. |
| Enforceable baseline prompt | Retained and tightened in baseline v2; subject rendering is catalog-only and exact baseline artifacts remain path/hash/blob bound. |
| Nondeterministic final results | Retained and tightened in result-state v2 with finite integrity events and first-match predicates. |
| E5/E6/E7 overlap | Retained as deterministic first-match metadata predicates. |
| Missing composed reasoning | Retained as four explicit, non-overlapping quota rows totaling eight fixtures per phase/round. |
| Historical replay versus class recurrence | Retained: replay/near-replay is prohibited, abstract operation/failure recurrence is allowed. |
| Exact-value representation ambiguity | Retained in exact-value comparator v1; `5`, `5.0`, and `5e0` behavior is type-specific and prospective. |
| Opportunistic reserve activation | Retained as one mapped reserve per slot, precontact-only activation, and full refreeze. |
| Confidence overclaim | Retained: confidence bounds are authored-benchmark decision statistics only. |
| Redundant gates obscured | Retained with every gate labeled independent, enforced redundant, or not applicable. |
| Phase A to Phase B carry-forward | Retained as exact cell state transitions, machine-built entrant set, no pooling, and no reentry. |
| Governance gaps | Retained with separate blueprint, authoring, implementation, pilot, execution-freeze, Phase A, and Phase B authority. |

## Intentionally retained design judgments

- The verified gate mathematics and counts are unchanged.
- Zero false-clean remains an independent gate. Family floors, binding zero-error, and Phase A correlated-repeat checks remain visible redundant guardrails.
- Clopper-Pearson values remain decision statistics for this authored benchmark, not population estimates.
- The operational validator remains unchanged. Any operational acceptance that the semantic comparator rejects is false-clean.
- Timezone conversion remains out of scope.
- G-ROUTE4 remains closed failed and immutable.

## Unresolved until later separately authorized phases

- No fixture exists yet; authorability and actual corpus diversity require a separately authorized blueprint and authoring review.
- The G-EXTRACT1 semantic scorer and comparator are identities only until separately implemented and audited.
- Provider option honoring remains unattested internally by Ollama.
- Scientific validity still requires independent design rereview; deterministic validation cannot grant it.
