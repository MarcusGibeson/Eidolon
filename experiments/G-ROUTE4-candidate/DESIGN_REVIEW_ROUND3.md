# G-ROUTE4 design review, round 3

Date: 2026-09-28.
Reviewed: `DESIGN_CANDIDATE.md` revision 3 (commit `1451d57`).
Answered by: revision 4.

Gate: the operator's safety-gated rule, as in the earlier rounds.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | 0 BLOCKING, 6 MUST-FIX, 9 notes |
| B | Protocol, R7 reuse, implementability | 0 BLOCKING, 9 MUST-FIX, 9 notes |

**What both reviewers confirmed:**
- Every number in revision 3 reproduced exactly.
- The gate rules are coherent: Reviewer A's exact-rational brute force covered n ≤ 250.
- The imported-unchanged modules load no G-ROUTE3 data and no coding runner.
- The sentence templates are unambiguous.
- The D8 insertion point appears exactly once in all 16 research prompts.

**Reviewer A's projection:** from G-ROUTE3's per-cell pass rates, 8/8 qualification gives a median of 182
qualified-start cases (10–90%: 144–218), and P(fewer than 76) ≈ 0.001.

Both reviews were read-only, with no provider contact.

## Operator decision after this round (2026-09-28)

**D8, amended.** The research sentence now adds:
- "exactly one … carrying that claim's claim_id";
- "distinct code strings".

The previously approved wording omitted two rules the validators enforce: duplicate uncertainty codes are rejected,
and claim ids must equal the input's. The amended sentence (sha256 `f3c383d9…ab47`) was re-approved.

## Reviewer A

| # | Class | Finding | Disposition in revision 4 |
|---|---|---|---|
| M1 | MUST-FIX | The prose said "below 76 stops → NOT_TESTABLE", contradicting the gate tables. | Reworded: P1 cannot PASS below 76 stops, and its status follows the gate tables. The configurations are labelled upper-bound cases. |
| M2 | MUST-FIX | The independence standard was looser than G-ROUTE3's without saying so, and underspecified. | G-ROUTE3's standard is the floor: trigram Jaccard ≤ 0.20 after declared boilerplate, 0 shared entities, identifiers, values, actions and lineages, fine-signature checks, and the answer-position check, using the same tokenizer. The shared research patterns and coarse signatures are a declared loosening, with the reason. Feasibility is checked. |
| M3 | MUST-FIX | "Fresh families" contradicted family sharing with G-ROUTE3; there was a selection risk. | All families are new. No item is derived from any G-ROUTE3 item. |
| M4 | MUST-FIX | Wrong cap arithmetic; no per-cell cap. | The base is defined (R4 counted), giving at least 5 families per class. A per-cell cap of one third, and a declared cell-level family gap. |
| M5 | MUST-FIX | Seeds off by one (repeats are 1-based). | The ranges are corrected to 470001–470792 and 480001–483041, and the base is stated. |
| M6 | MUST-FIX | The reserve would run out; "failing again" was undefined; 2-of-3 disagreement was kept without the operator. | Reserve per feature combination. "Failing again" is defined. A first disagreement goes to two more blind adjudicators, both must agree, otherwise the operator. Rules for new reserve authored after outcomes are known. "Never dropped for being hard" is restored. |
| Notes | — | Floor rationale; power independence; the 0.73 basis; E1 escalations vs stops; research metric definitions and population; generalization method; the P7/P8 counts and crossing; two "shown worse" claims; the cluster-bound label. | All answered in Gates, Corpora and Descriptive reporting. |

## Reviewer B

| # | Class | Finding | Disposition in revision 4 |
|---|---|---|---|
| M1 | MUST-FIX | The grep test had a hole, and its exception could not be implemented. | Case-insensitive `g[-_ ]?route[-_ ]?3`, with one frozen `G3_REFERENCE_ALLOWLIST`. |
| M2 | MUST-FIX | Renaming contracts contradicted the imported modules; bindings schema literals. | Carried contract ids keep their G-ROUTE3 names, by attribute. G-ROUTE4 writes its own bindings file, with an equality test against G-ROUTE3's. |
| M3 | MUST-FIX | The import-or-fork table was not closed. | `platform` and `fs` are forked. `g_route1_execution_contract` and `g_route1_freeze` are imported and guarded. The runner fork's scope is stated, without the coding runner or persistence. `independence`, tests and differential are forked. A closure rule. The module rule covers every `g_route3_*` module. |
| M4 | MUST-FIX | Seeds off by one. | As A-M5. |
| M5 | MUST-FIX | The D8 claim to disclose every shape rule was false for uncertainties. | The operator re-approved an amended sentence that states distinct codes and claim ids. Its sha256 is frozen. |
| M6 | MUST-FIX | The certification base schedule contains coding. | A 4-position non-coding base schedule. The resumed `awaiting_execution` case and worker drift are dropped. Changed kill-point counts are declared. |
| M7 | MUST-FIX | The differential could not be implemented as written. | Normalization defined: mask tokens, substitute identities, re-seal, compare trees. A shared stub scorer. The G-ROUTE3 side runs in a separate subprocess. |
| M8 | MUST-FIX | Adjudication: sequential keeping, "no answer", reserve, rounds, batches. | Two further blind adjudicators must both agree. "No answer" is defined, and a second counts as a disagreement. Reserve per feature combination. Halt when the round cap is hit. A batch is defined. |
| M9 | MUST-FIX | Independence checks came after the seal, with no path for failures. | Mechanical checks come before the seal. Review-driven changes go through a fix or replacement with re-adjudication. |
| Notes | — | The run-id format; re-checking the experiment name after the lease; the fixture prefix check; pattern-label definitions; one job at a time; the sentence digest; the wider module rule; claim ids in D8; the operational wrapper. | All answered. The patterns are renamed P1–P8 with their G-ROUTE3 construct names. The one-job rule is declared runbook-only. |

## Next

Revision 4 goes to two fresh reviewers (round 4) under the same gate.
