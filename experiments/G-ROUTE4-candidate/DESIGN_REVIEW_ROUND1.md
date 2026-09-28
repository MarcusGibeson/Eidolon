# G-ROUTE4 design review, round 1

Date: 2026-09-28.
Reviewed: `DESIGN_CANDIDATE.md` revision 1 (commit `ef96d95`).
Answered by: revision 2.

Gate: the operator's safety-gated rule. **BLOCKING** means the design would allow one of the following:
1. a repeated call;
2. best-of-N or optional stopping;
3. contact without the correct sentence;
4. a silent scientific or grading change;
5. a contradiction with an operator decision or a standing constraint.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | FINDINGS: 2 BLOCKING, 10 MUST-FIX, 7 notes. All the arithmetic in revision 1 checked out. |
| B | Protocol integrity, R7 reuse, implementability | FINDINGS: 1 BLOCKING, 10 MUST-FIX, 5 notes |

Both reviews were read-only, with no provider contact.

## Operator decisions after this round (2026-09-28)

| # | Decision |
|---|---|
| D1, revised | Phase B′ calls **all three tiers** on every case. Router-only would need a data-dependent lifecycle and its own design review. |
| D6, revised | **Coding is deferred** to its own experiment, with a real sandbox and a hardened AST gate. |
| D9, new | Phase B′ has **300 eligible cases** (84 conversation, 216 other) plus 5 R4 cases, making 915 calls. |

## Security finding recorded with this round (Reviewer B, M3)

**The coding runner is not a sandbox.** `run_isolated_fixture` runs `python -I` in a temporary folder as the user,
with no filesystem or network restriction.

**The AST gate can be bypassed.** The frozen `validate_candidate_ast` accepts:
- `bool = eval; bool(s)`;
- a parameter defaulting to `open`;
- an `@eval` decorator;
- `from pathlib import PurePosixPath as eval`.

**No bypass was used.** A read-only scan of all 85 G-ROUTE3 coding outputs (every attempt) found no rebinding of a
built-in, no decorator, no dunder access and no dangerous name. The only import was the permitted
`from pathlib import PurePosixPath`.

**No production code is affected.** The runner is used only by the G-ROUTE research tools; nothing in
`conscious_agent/` imports it.

**Disposition:** coding is deferred (D6, revised). The later coding experiment needs a real sandbox, and an AST gate
that is the primary control, with a certification probe per bypass.

## Reviewer A

| # | Class | Finding | Disposition in revision 2 |
|---|---|---|---|
| B1 | BLOCKING (4) | Coding stops are structurally safe, so they would dilute the pooled unsafe gate once coding qualifies. | Coding is out of scope (D6). The unsafe gate counts every stop, and every stop can be unsafe. |
| B2 | BLOCKING (4) | NOT_TESTABLE below the new floors hides failures that G-ROUTE3 would call FAIL. | A three-way rule per gate. FAIL applies at the floor if the bound misses, at n ≥ 10 on G-ROUTE3's observed-rate standard, and at any n if the opposite bound excludes the threshold. G-ROUTE3's evaluation order is kept. |
| M1 | MUST-FIX | The 0.312 bound assumes independent repeats; 8/8 changes what "qualified" means. | Both bounds are reported per cell (observation-level 0.312, fixture-level 0.527), with the clustering declared. The stricter meaning is declared, with P(qualify) figures, and the 0.60 rationale is restated. |
| M2 | MUST-FIX | The "confirmatory" label is wrong for a changed policy. | Retitled. G-ROUTE4 tests its own policy, is not a replication, and is never pooled with G-ROUTE3. |
| M3 | MUST-FIX | Power was not declared; resizing was not excluded. | A power table is published. The exact B′ size and composition are frozen before contact (D9). B′ is never resized, topped up or pooled, and NOT_TESTABLE is final. Seeds per position are fixed and identical across attempts. |
| M4 | MUST-FIX | Oversampling was unquantified; the P2 estimand was undefined. | An exact per-cell allocation. The direction of oversampling is declared conservative. An equal-weight-by-class rate is added as descriptive. P2's reporting rule is defined, including the case where small does not qualify. |
| M5 | MUST-FIX | Stops are clustered by template. | The contamination and independence reports are required, with a template cap of 25% of a class's B′ cases. Per-template breakdowns and a cluster-level sensitivity bound are reported without gating. Exchangeability is declared. |
| M6 | MUST-FIX | Adjudication could act as a difficulty filter; authoring could be contaminated. | Adjudication is fully specified: the adjudicator is named, blind and sealed. A fixture is fixed only for a documented defect, and kept unchanged when the adjudicator erred. Replacements come from a reserve in a fixed order, with counts disclosed. Also: a frozen authoring blueprint, no pretesting on models, and no items derived from inspected G-ROUTE3 items. |
| M7 | MUST-FIX | The research pattern mix decides qualification. | An identical per-cell pattern allocation in A′ and B′, balanced across R1–R4 and derived from the construct, with `single_lineage_support` holding in 50% of fixtures per cell. Research qualification is declared conditional on that mix, and the construct is not comparable with G-ROUTE3's. |
| M8 | MUST-FIX | Router-only was under-specified. | Superseded: D1 is revised to all three tiers, which restores all counterfactual measures. |
| M9 | MUST-FIX | S1's standard and odds were overstated. | S1 is pilot and descriptive, with no verdict. The predictive probability of at least 5 escalated stops is given as about 0.6–0.8. |
| M10 | MUST-FIX | D6 and D8 need criteria. | D6: coding is deferred. D8: the derivability rule is extended to every enforced output shape in all five profiles, with a disclosure audit. |
| Notes | — | Exact computation; code for the correct-stop lower bound; intersection-union test; frozen descriptive metrics; R4 zero calls; exact numbers. | Exact computation is stated. The intersection-union test is declared. The metrics are frozen in code. R4 is evidence-only. All counts are exact. |

## Reviewer B

| # | Class | Finding | Disposition in revision 2 |
|---|---|---|---|
| B1 | BLOCKING (5) | The router-only B′ call list depends on the A′ table and on outputs, which contradicts "the schedule never changes after contact". | D1 is revised to all three tiers. The fixed, fully enumerated schedule is frozen before contact, and routing is computed gold-blind afterwards, as in G-ROUTE3. |
| M1 | MUST-FIX | R7 cannot run a data-dependent schedule. | Superseded by D1: R7's fixed-schedule guarantees apply unchanged. |
| M2 | MUST-FIX | Experiment identity and separation from G-ROUTE3 were unspecified. | New `g_route4_*` modules. All identity constants are listed. A new data root, with mutual refusal between the two experiments. The experiment name is checked on open. A full G-ROUTE4 sentence set. Every G-ROUTE3 and G-ROUTE1 file stays byte-identical. |
| M3 | MUST-FIX | The D6 security argument was inverted, and the gate is bypassable. | Coding is deferred, and the finding is recorded above. |
| M4 | MUST-FIX | D6 versioning conflicts with the frozen coding validator. | Moot: coding is deferred. |
| M5 | MUST-FIX | Sizing rested on G-ROUTE3's rates; the figures were approximate. | Exact frozen counts (D9) and a power table across stop rates of 0.40–0.73. The estimand is stated, and NOT_TESTABLE is final. |
| M6 | MUST-FIX | Gate semantics under bounds; S1 was listed under gates. | The per-gate partition is pre-registered, including FAIL when the lower bound exceeds 0.10. FAIL means "not shown". S1 is descriptive only. |
| M7 | MUST-FIX | Adjudication was under-specified. | As A-M6: who adjudicates, what they are blind to, sealing, resolution by a second adjudicator and then the operator (never the author), fix vs keep vs drop, the reserve, a cap of 2 rounds, and disclosure. The same rules apply to A′ and B′. |
| M8 | MUST-FIX | Corpus construction was informed by failures. | As A-M7, plus contamination and independence reports against G-ROUTE3 A/B, including Corpus B. |
| M9 | MUST-FIX | D8 was only paraphrased; "unchanged prompt" was undefined. | The verbatim sentence and its insertion point are frozen. The prompt is defined as the G-ROUTE3 rule body, byte-identical, plus the sentence. A freeze-time test checks it. |
| M10 | MUST-FIX | Missing steps. | The ordering lists every step: the blueprint; authoring, adjudication and corpus review; implementation, its review, certification and the differential; the freeze; each phase with its sentence and audit; the table sentence and the table on `main`; the results record. The Phase B′ preconditions are adapted. |
| Notes | — | Correlated repeats; the escalation odds; the runbook window; frozen metrics; determinism (hash, id). | Correlated repeats: both bounds are reported. Escalation: pilot. Runbook: windows are reserved. Metrics: frozen in code. Determinism: moot, since coding is deferred. |

## Next

Revision 2 goes to two fresh reviewers (round 2) under the same gate.
