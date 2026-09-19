# G-CORROB1-R2 pre-pilot independent gold signoff

**Result:** `GOLD SIGNOFF REQUIRES REPAIR`

**Scope:** fresh semantic review of all 32 corpus items against the frozen R2
semantic contract, performed separately from scorer implementation and without
provider/model contact. Deterministic consistency checks were not treated as
semantic evidence. No corpus, gold, prompt, policy, threshold, or scorer value
was changed.

## Review method

For each item, the review separately inspected proposition and evidence meaning,
relation, entity/population scope, temporal applicability, quantifiers,
qualifiers, conjunctions, binding, and operational eligibility. A crisp item
passes only when the evidence supports one defensible semantic tuple under the
contract without relying on unstated facts.

## Item-level review

| ID | Independent semantic assessment | Binding, qualifiers, and temporal review | Operational eligibility | Result |
|---|---|---|---|---|
| R01 | `supports / match / compatible` | Complete dated audit binds the whole twelve-parcel population; every member has a successful scan. | `use` | Agree. |
| R02 | `contradicts / match / compatible` | Complete dated population contains an explicit counterexample to `every`; no continuity assumption is needed. | `abstain` | Agree. |
| R03 | `supports / match / compatible` | One identified Lysa orchard is a sufficient witness for `some`; unknown remaining orchards do not weaken the existential. | `use` | Agree. |
| R04 | `partial / evidence_narrower / compatible` | Evidence covers one of four orchards, a strict subset of the universal population. | `investigate` | Agree. |
| R05 | `supports / match / compatible` | The universal routing rule and medical-kit exception exactly match the proposition's qualifier. | `use` | Agree. |
| R06 | `contradicts / match / compatible` | The named exception class is expressly routed exclusively south and never north. | `abstain` | Agree. |
| R07 | `supports / match / compatible` | Permission, employee population, archive, and staffed-hours qualifier all match. | `use` | Agree. |
| R08 | `contradicts / match / compatible` | `At any time` includes unstaffed hours, for which entry is explicitly denied. | `abstain` | Agree. |
| R09 | `supports / match / compatible` | `Every operator must` entails the asserted obligation in the same bay. | `use` | Agree. |
| R10 | `contradicts / match / compatible` | A mandatory rule contradicts the proposition's explicit negation of obligation. | `abstain` | Agree. |
| R11 | `supports / match / compatible` | `May submit` directly establishes permission before noon; optionality is compatible with permission. | `use` | Agree. |
| R12 | `contradicts / match / compatible` | `Optional, not required` directly negates the asserted obligation. | `abstain` | Agree. |
| R13 | `supports / match / compatible` | Signed registry directly binds Halcyon to H-204. | `use` | Agree. |
| R14 | `contradicts / match / compatible` | Signed registry directly binds Zephyr to Z-881 and distinguishes the two units, contradicting H-204 for Zephyr. | `abstain` | Agree. |
| R15 | `supports / match / compatible` | The eastern turbine is uniquely identified and directly recorded as T-9. | `use` | Agree. |
| R16 | `partial / evidence_narrower / compatible` | One of three turbines is T-9; two blank model fields leave the universal proposition unresolved. | `investigate` | Agree. |
| R17 | `supports / match / compatible` | Requested date lies inside the explicit inclusive validity interval. | `use` | Agree. |
| R18 | `contradicts / match / compatible` | Explicit invalidity starts at 00:00 on the requested date, covering that date. | `abstain` | Agree. |
| R19 | `supports / match / compatible` | 18:30 is strictly inside the explicit same-date closure interval. | `use` | Agree. |
| R20 | `contradicts / match / compatible` | Explicit reopening at 19:00 contradicts closure at 19:30. | `abstain` | Agree. |
| R21 | `supports / match / compatible` | A signed record of completed sanitation cycle S-44 on the date establishes that Mixer M completed a sanitation cycle that day. | `use` | Agree. |
| R22 | `unclear / unclear / compatible` | S-44 is recorded as aborted and no *later* cycle is recorded, but the proposition does not name S-44 and the evidence does not exclude an *earlier* completed cycle. The evidence therefore does not entail that Mixer M completed no sanitation cycle that day. | `investigate` | **Disagree: proposed `contradicts / match / compatible` gold is not crisp.** |
| R23 | `supports / match / compatible` | Final certified result directly binds bridge and test ID LT-6 to PASS. | `use` | Agree. |
| R24 | `unclear / match / compatible` | Prediction is about the correct bridge/test but no outcome exists; under the contract, a prediction is not a proper component of passing. | `investigate` | Agree. |
| R25 | `supports / match / compatible` | Legend directly defines the triangular glyph as east. | `use` | Agree. |
| R26 | `contradicts / match / compatible` | Direct east definition contradicts the asserted west meaning. | `abstain` | Agree. |
| R27 | `supports / match / compatible` | Signed rota exactly binds team, desk, and date. | `use` | Agree. |
| R28 | `irrelevant / mismatch / compatible` | Same-date menu has no probative or entity link to the desk assignment. | `abstain` | Agree. |
| D01 | `unclear / unclear / compatible` | `It` can grammatically refer to cup or vase; the referent is genuinely unresolved. | Diagnostic `investigate`; excluded from crisp accuracy. | Genuine ambiguity confirmed. |
| D02 | `unclear / match / unclear` | 2032-09-06 is a Monday, but the applicable public-holiday jurisdiction/status is unstated, so the exception cannot be resolved. | Diagnostic `investigate`; excluded from crisp accuracy. | Genuine ambiguity confirmed. |
| D03 | `unclear / match / compatible` | Whole-centimeter rounding cannot establish exact underlying length `10.0`; several measurements map to the display. | Diagnostic `investigate`; excluded from crisp accuracy. | Genuine ambiguity confirmed. |
| D04 | `unclear / unclear / compatible` | Without punctuation or clarification, adjective scope over coordinated `technicians and managers` is genuinely unresolved. | Diagnostic `investigate`; excluded from crisp accuracy. | Genuine ambiguity confirmed. |

## Blocking finding

`R22` fails the crisp-primary requirement. The frozen passage establishes that
cycle S-44 did not complete and that no later cycle occurred. It does not state
that S-44 was the only sanitation cycle on 2032-08-02, does not exclude an
earlier completed cycle, and the proposition does not name S-44. Consequently:

- proposed `contradicts` is not entailed;
- proposed `match` assumes an unstated event binding;
- `abstain` would be safe, but safe disposition does not cure questionable gold;
- retaining the item would compromise semantic-accuracy and error metrics.

The smallest principled repair would be either to bind the proposition explicitly
to cycle S-44 or to state in the evidence that S-44 was the only sanitation cycle
for Mixer M on that date. Either option changes corpus semantics and therefore
requires a documented design revision, complete gold re-audit, revised digests,
and a new freeze candidate. This report does not choose or apply either repair.

## Stop-boundary result

Because a gold defect was discovered before provider contact, the instructed
stop rule applies. Provider/configuration preflight, execution-freeze creation,
and freeze audit were not started. Pilot authorization and experiment
authorization remain false.
