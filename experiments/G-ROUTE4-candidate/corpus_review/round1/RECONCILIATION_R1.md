# G-ROUTE4 external corpus review, round 1: reconciliation

Date: 2026-09-29. Design order of work 3.7. **Status: OPEN.** Three MUST-FIX findings from Reviewer A need fixture
changes, and the design routes those through the frozen fix or replacement procedure with re-adjudication (step 10).
Nothing has been applied; the operator decides.

## The two reviews

| Reviewer | Focus | Report (exact bytes) | Verdict |
|---|---|---|---|
| A | Corpus content: derivability of all 385 final main fixtures, D8, difficulty parity, the 20 fixes, disclosures | `outputs/REVIEWER_A_REPORT.md`, sha256 `8219822cb9104b106281d22033f7c34335fa0bce88e17fe2bb527c662535b5f5` | FINDINGS: BLOCKING 0, MUST-FIX 3, NOTE 8 |
| B | Protocol and provenance: O1–O6, N3, N7, N8, adjudication procedure, seal, reports | `outputs/REVIEWER_B_REPORT.md`, sha256 `0eba8701a8cec21df82f846c7faacbba92a78f405abbff88d0b29cb2fe9f3320` | FINDINGS: BLOCKING 0, MUST-FIX 2, NOTE 8 |

- Both reviewed commit `97afe8a`, were fresh, read-only `claude-opus-5-5` sessions, and made no repository or provider
  changes.
- Reviewer A was resumed in the same session after a provider rate limit (operator decision 1a). Its 385 derivations
  were sealed by digest before it opened gold, and are unchanged since the interruption
  (`outputs/REVIEWER_A_RESUMPTION_RECORD.json`).
- **BLOCKING: 0 from either reviewer.**

## Where the reviewers meet

| Topic | Reviewer A | Reviewer B | Reconciled |
|---|---|---|---|
| O2 under `7691126e…` | Nothing that bears on what the adjudicator saw, or on how gold was judged, changed (item 7) | PASS; adjudication satisfies O2 (B3, B4 notes) | **Agree: O2 satisfied.** |
| Kept SY1 main fixtures (4) | **A1 MUST-FIX:** gold not uniquely derivable; inconsistent with the 8 fixed SY1 fixtures | The latent-defect lists are complete and accurate; derivability outside B's scope | **No conflict** (different scopes). B's check confirms the disclosure; A's finding on derivability stands unopposed. |
| B′ disagreement causes | A6: 24 content differences among fenced answers, all on sealed versions of later-fixed fixtures; the closure totals are accurate | B2 MUST-FIX: the B′ `by_cause` partition hides 16 fenced + content | **Consistent.** A's 24 = 8 A′ + 16 B′, the erratum's figure. B2 is resolved by erratum 1. |
| A4-PLAN-R3-04 | A7 NOTE: three refusals; A's independent derivation **equals gold** | B5 NOTE: no independent adjudicator evidence; carry to review | **Agree on the facts.** Carried under step 10 for the operator (below). |
| Independence tool | A11 NOTE: dd8193b is not an ancestor of HEAD (on the staging branch); digest matches there | B7 NOTE: the right tool for this stage; freeze condition set | **Consistent.** |
| Latent-defect disclosures | Accurate and complete; no undisclosed fixture shares a disclosed defect; A2 and A3 are **new** defects of another kind | Lists match B's mechanical scan | **Agree** on the disclosed defects. |
| B′ closure wording | A10 NOTE: `residual_limitations` says "22 fixtures / 14 reserves", predating the addendum (now 15 reserves) | — | Wording only (below). |

## Disposition of every finding

**Resolved or recorded (operator rulings, `OPERATOR_RULINGS_R1.json`, commit `ae62dba`):** B1 (step-7 ruling and
annotation), B2 (erratum 1), B3 (O2 disclosure), B4 and B6 (no action), B7 and B8 (freeze conditions), B9 (kept
disclosure), B10 (provenance bound).

**Open MUST-FIX (fixture changes; operator decision required before anything is applied):**

| Id | Fixture(s) | Defect (verified against the text) | Audit sample | Frozen remedies (step 10) |
|---|---|---|---|---|
| A1 | A4-SYNTH-R1-01 (A′); B4-SYNTH-R1-02, B4-SYNTH-R2-15, B4-SYNTH-R3-08 (B′) | SY1: the cause is stated only under role `diagnosis`; the rule says "a finding directly states the cause" (the disclosed latent defect) | none sampled | **Fix** (each fixture's one fix; none used yet): the same role relabel as the 8 recorded SY1 fixes, then re-check, then re-adjudication (A′: three adjudicators; B′: the B′ procedure). **Replacement:** A4-SYNTH-R1-X01 carries the same defect; B′ reserves B4-SYNTH-R1-X02, B4-SYNTH-R2-X03, B4-SYNTH-R3-X04 have no known defect. |
| A2 | B4-CONV-R1-08 | "dispatches on 2045-11-18 after 2 days of packing": read literally, all four options meet both dates; only "dispatch = date + packing" yields gold Yulofu | not sampled | **Fix** (one fix): make the dispatch date unambiguous, then re-check and B′ re-adjudication. **Replacement:** B4-CONV-R1-X08 (gold position 4 × depth 2; no known defect). |
| A3 | B4-CONV-R2-28 | Wapodi "can start on 2046-02-03 and needs 11 days": counting the start day as day 1 finishes 02-13 (valid), otherwise 02-14 (invalid), so Wapodi and gold Vuboyi can both be valid | not sampled | **Fix** (one fix): state the finishing convention or the end date, then re-check and B′ re-adjudication. **Replacement:** B4-CONV-R2-X04 (gold position 4 × depth 1; no known defect). |

Because none of these B′ fixtures is in the audit sample, the pre-registered full-cell consequence is not triggered by
any of these remedies. Either remedy needs new adjudicator sessions (provider contact under O2 `7691126e…`), which the
operator starts per D10. After any change, the caps and independence checks are re-run over the whole pool (step 8),
and the independence and contamination reports and closure records are regenerated for the changed final corpus.

**Carried under step 10, for an operator disposition:**
- **B5 / A7, A4-PLAN-R3-04.** Not modified. Both reviewers agree it has no substantive adjudication (three refusals);
  Reviewer A's independent derivation equals gold, and neither reviewer found a derivability defect. By the operator's
  ruling, the refusals alone cannot authorize a post hoc gold change.

**Notes proposing disclosure only (no fixture change):**
- **A4.** Research P4: A′ has P4 only with sls false, in the redundant form, so A′ qualification never tests
  repost-only support; B′ does (three fixtures). A consequence of the frozen allocation.
- **A5.** Synthesis SY4, SY5 and SY6 have a constant conclusion per family (declared by the blueprint), so the
  conclusion component is weak there.
- **A10.** `B_MAIN_CLOSURE.json` `residual_limitations` counts 22 fixtures and 14 reserves; the addendum makes 15
  reserves. The closed file is not edited; a wording erratum would carry it.

**Notes with no action:** A6, A8, A9, A11.

## What closes round 1

Every MUST-FIX resolved (A1, A2, A3 open), and 0 BLOCKING (met). The operator decides the remedy for each of A1–A3,
the disposition of A4-PLAN-R3-04, and whether A4, A5 and A10 are recorded as disclosures.
