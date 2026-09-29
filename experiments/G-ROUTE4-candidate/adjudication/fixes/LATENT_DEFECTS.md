# G-ROUTE4 known latent defects (report only; nothing altered)

Recorded 2026-09-29, after the B′ main adjudication and the round-1 fixes. The same three input defects that caused
the 14 substantive B′ escalations also exist in fixtures that have not been fixed. **None of these fixtures has been
altered.** This report states what the frozen protocol (DESIGN_CANDIDATE.md "Gold adjudication", steps 1–13;
G-ROUTE4_OBLIGATIONS.md) permits for each category, so the operator can decide before anything is done.

## The defects

| Defect | Construct it breaks | Evidence from B′ adjudication |
|---|---|---|
| **P6 "only"**: the narrower-scope source is worded with an exclusionary "only" | P6 gold (C1 unresolved, `scope_mismatch`) is not uniquely derivable; the source reads as a contradiction | all 7 B′ main P6 fixtures escalated; every answer marked C1 contradicted |
| **SY1 diagnosis role**: the causal statement is under role `diagnosis`, not `finding` | the frozen rule and SY1 definition say "a finding directly states the cause" | 6 of 9 B′ main SY1 fixtures escalated; 16 of 18 answers chose `insufficient_evidence` |
| **Weak anonymity paraphrase**: "strips names from submitted answers" | does not establish anonymity, so a P4 claim reads as one supporting lineage | B4-RSRCH-R3-04: all three answers chose `deny_access` |

## Affected fixtures (22)

| Category | P6 "only" | SY1 diagnosis role | Weak anonymity |
|---|---|---|---|
| **A′ main, not yet adjudicated** | A4-RSRCH-R2-02, A4-RSRCH-R4-03 | A4-SYNTH-R1-01, A4-SYNTH-R2-03, A4-SYNTH-R4-01 | — |
| **A′ reserve** | A4-RSRCH-R2-X02, A4-RSRCH-R4-X03 | A4-SYNTH-R1-X01, A4-SYNTH-R2-X03, A4-SYNTH-R4-X01 | — |
| **B′ reserve** | B4-RSRCH-R1-X06, B4-RSRCH-R1-X14, B4-RSRCH-R2-X06, B4-RSRCH-R2-X14, B4-RSRCH-R3-X06, B4-RSRCH-R3-X14 | B4-SYNTH-R1-X01, B4-SYNTH-R3-X03 | B4-RSRCH-R3-X03 |
| **B′ main, already kept** (first adjudicator agreed) | — | B4-SYNTH-R1-02, B4-SYNTH-R2-15, B4-SYNTH-R3-08 | — |

## What the frozen protocol permits

**A′ main (5, not yet adjudicated).** After the seal, "gold changes only through a recorded fix" (step 3), and a
fix follows an adjudication outcome (steps 6–7) or the external corpus review (step 10). There is no provision to
edit an uncontacted fixture before its adjudication. These fixtures are adjudicated as sealed in the A′ batch, with
the full treatment: three blind adjudicators, kept only if all three agree, otherwise the operator decides (step 6).
If escalated, the operator may choose "input ambiguous → fix input" as that fixture's one fix, and it is then
re-adjudicated from scratch (step 7). The A′ batch is started only by the operator in chat (D10).

**Reserves (14).** A reserve is used only as a replacement: taken from the reserve matching the slot's features, in
a fixed order, and adjudicated from scratch (step 8). There is no provision to edit a sealed reserve before it is
drawn. A replacement that fails moves to the next matching reserve, or authoring halts once the 2-round cap is hit or
the matching reserve is exhausted (steps 8–9). After a halt, "more reserve needs a recorded operator decision": any
new reserve is authored to the blueprint, declared as authored after adjudication outcomes were known, sealed,
adjudicated from scratch, and disclosed (step 9). Each reserve listed here would likely fail for its known defect if
drawn.

**B′ main, already kept (3).** A kept fixture is not reopened by the adjudication procedure; only disputed or
sampled fixtures are scrutinized, which is the declared residual filter (step 12). A change can come only from the
external corpus review: "a change driven by the corpus review goes through a fix (counted as the fixture's one fix)
or a replacement, with re-adjudication" (step 10).

## Directly relevant now

The four round-1 fixes that did not end in keep (B4-RSRCH-R2-06, B4-RSRCH-R2-14, B4-RSRCH-R3-14, B4-RSRCH-R3-18)
each have exactly one matching B′ reserve, and each of those reserves carries the P6 "only" defect:
B4-RSRCH-R2-X06, B4-RSRCH-R2-X14, B4-RSRCH-R3-X14 and B4-RSRCH-R3-X06.

## A structural observation (not a fixture defect)

Most escalations in both the B′ batch and the fix round were code-fenced JSON whose content matched gold. A fixture
fix cannot change an adjudicator's formatting habit, and the frozen validator cannot change after provider contact.
Such escalations can only be resolved by the operator ("gold right → keep"). The A′ batch, where every fixture gets
three adjudicators, should be expected to escalate many format-only fixtures.
