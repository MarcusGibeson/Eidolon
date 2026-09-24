# G-ROUTE3 Design Audit

Date: 2026-09-24
Verdict: **READY** (after one REVISE cycle)
Authority: non-authoritative. It grants no execution, provider, routing or belief authority and changes no
artifact. Provider generation calls during design and audit: **0**.

**A limit on independence, stated first.** This audit was performed by the same agent that authored the
corpora and the code. It is procedurally separate: it was a distinct adversarial pass, with its own checks
and its own recorded findings. It is not a second pair of eyes. The pre-contact gold review in particular
would benefit from a human reading of all 96 fixtures, and nothing here substitutes for that.

## First pass: REVISE

Seven findings, all repaired before this verdict:

| # | Finding | Repair |
|---|---|---|
| 1 | `A-SYNTH-R1-1`: a battery at 0% five minutes before an outage is suggestive, not an identified cause, so `insufficient_evidence` was defensible | observation reworded so the log attributes the shutdown to the battery |
| 2 | `B-SYNTH-R2-2`: a 2 mm tread is above the 1.6 mm legal minimum, so no harm is indicated and `no_action_needed` was defensible | tread changed to 1.4 mm |
| 3 | `B-CONV-R3-2` rejected the correct answer "Two databases verified and one failed" | accepted phrasings widened to cover natural statements of partial success |
| 4 | `B-CONV-R2-1` rejected the correct answer "It expired in February" | accepted date phrasings widened |
| 5 | `A-CONV-R3-2` accepted "share" but not "send" phrasings of the same refusal | widened |
| 6 | A planning action, `propose_shutdown_date`, appeared in gold in both corpora in the same cell | renamed in Corpus B |
| 7 | The pipeline test never produced a false-clean on an unqualified tier, so the "caught because unqualified" count was unexercised | scenario extended; the count and a false-positive qualification are now asserted |

Findings 3 to 5 are the conversation form of the derivability problem: a correct answer must not fail on
wording the model was never told to use. A regression now locks in natural phrasings.

## Final pass

**Corpus A quality and gold.** All 48 reference answers pass the frozen validators. Every closed-vocabulary
gold code is model-visible, every enforced ordering is stated, the coding whitelist is disclosed, every gold
coding answer passes its tests inside the whitelist, and every buggy source fails. Each fixture's rationale
states why its gold is the single defensible answer. *Residual:* uniqueness was reviewed by the author; see
the limit above.

**Corpus B independence.** No fixture content, entity, identifier, gold action, function name, extraction
value or source lineage is shared with A. The highest trigram overlap is 0.058 against a bound of 0.20. No
reasoning pattern is shared within any of the 24 cells. Shared vocabulary is limited to declared
profile-level rule text.

**Task and risk assignment.** Six classes × R1–R4, two fixtures per cell in each corpus, balanced. Risk
classes are designer judgments of consequence (R1 personal/low, R2 money and routine operations, R3 security
and data, R4 authority and safety) and are applied the same way in both corpora.

**Normalization contract.** The G-ROUTE2 contract is reused unchanged, and transport outcomes are recorded
on every call.

**Qualification criteria.** 4 of 4 complete, accepted, correct, with zero false-cleans. Anything short of
complete evidence is `insufficient_evidence`, which is never operationally qualified. No missing-data pass
and no vacuous pass are possible, and both are asserted by test.

**Sample-size claims.** Stated as pilot scale, with the exact 0.527 bound carried on every cell. No claim
beyond that is made.

**Thresholds.** Frozen before contact and argued from the design's own denominators, not from G-ROUTE2's
observed rates. Both rate gates carry minimum denominators, so a thin table is reported `NOT_TESTABLE`
rather than passing.

**Table-freeze boundary.** The table is write-once, digest-bound and requires a READY audit. It must trace
to a complete Phase A run and its sealed score, and must be bound to this execution freeze. Phase B needs a
second authorization naming the table digest. The table is inside Phase B's mutation guard. Each property is
exercised by a test, including a mid-run table edit that stops the run `incomplete`.

**Runtime lookup and escalation.** The router starts at the cheapest qualified tier, never contacts an
unqualified tier, skips unqualified intermediate tiers, never skips qualified ones, and fails closed when
exhausted. `no_qualified_model` makes zero routing calls. The three verdicts are separate fields.

**Gold blindness.** The routing module imports no gold loader, and runtime views reject semantic fields.
Collection never loads gold, and a full Phase A completes with Corpus B gold made unloadable.

**Scorer and denominators.** 48 cases each receive exactly one outcome, and there are 144 observations.
Routing and diagnostic calls are counted separately and sum to 144. The arithmetic is exercised end to end.

**Triggers.** Three are retained and each fires in a test. Three are retired, with reasons recorded. None is
dead code.

**Contamination from G-ROUTE1 and G-ROUTE2.** No outcome, cell verdict or threshold was carried over. The
derivability rule was motivated by a diagnostic over G-ROUTE2 records; it is a construction property
checkable without model output, and it is declared.

**Authority.** Production routing, automatic escalation and source mutation remain unauthorized. Belief
effects are `none`. G-ROUTE1 and G-ROUTE2 are untouched.

## Residual limitations accepted into the freeze

- The pilot-scale qualification bound is weak by construction.
- Task and risk classes are given to the router, not inferred, so classifier error is unmeasured.
- Conversation remains phrase-matched. Widened alternatives reduce but do not remove brittleness.
- Planning fixtures now test exact rule-following rather than open-ended planning; that trade is declared.
- The Phase B diagnostic calls are necessary for false-negative analysis and cost 144 − (routing calls)
  extra provider calls.
- Ollama does not attest option or seed honoring.

## Verdict

**READY** for explicit scientific execution authorization of Phase A. Phase B additionally requires a frozen,
audited qualification table and its own authorization.
