# Step-7 ruling: annotation of the historical fix-round wording

Operator ruling, 2026-09-29, on external corpus review round 1, finding B1 (MUST-FIX). The ruling is bound verbatim in
`corpus_review/round1/OPERATOR_RULINGS_R1.json`. This annotation adds to the historical records; it does not edit or
rewrite them.

## The ruling

Design step 7 ("'Failing again' means the re-adjudication does not end in 'keep', and the fixture is then replaced")
does not require automatic replacement merely because a fixed fixture's re-adjudication result does not literally end
in "keep". The controlling question is whether re-adjudication establishes an unresolved defect in the fixture/gold
pair. If the remaining disagreement is caused only by a fenced (non-admissible) adjudicator answer, and the corrected
fixture and gold remain independently defensible under the frozen procedure, the fixture may be retained.

It applies consistently to the nine retained fixed fixtures. No re-adjudication is required.

| Batch | Fixtures | Fix round | Operator keep |
|---|---|---|---|
| B′ | B4-RSRCH-R2-06, B4-RSRCH-R2-14, B4-RSRCH-R3-14, B4-RSRCH-R3-18 | `g4adj-bmain-fix1-20260929T171651Z` | `f07b1a2` |
| A′ | A4-EXTR-R1-03, A4-RSRCH-R2-01, A4-RSRCH-R2-02, A4-RSRCH-R4-03, A4-SYNTH-R2-03 | `g4adj-amain-fix1-20260929T185315Z` | `c70d6f6` |

## Timing (disclosed, not rewritten)

- **A′ declared its reading before its fix-round disposition.** The A′ operator decisions (`8dc222f`, 14:49:45 EDT)
  state, for each fix: "kept only if all three agree, otherwise back to the operator before any replacement". The A′
  fix run started after that (18:53:17Z), and the operator keeps followed at `c70d6f6`.
- **B′ did not settle it until after its fix-round results and the reserve-defect information were known.** The B′
  operator decisions (`6818c50`, 13:13:14 EDT) state only "if it fails, the frozen replacement procedure applies". The
  fix-round outcome record (`01e6ad3`, 13:21:08 EDT) labelled the four "not keep" and, in `fixes/LATENT_DEFECTS.md`,
  "did not end in keep", noting that each one's only matching reserve carries the P6 "only" defect. The operator keeps
  were recorded after that, at `f07b1a2` (13:52:38 EDT).

## Historical wording, read under this ruling

| Record | Wording (unchanged) | Reading under the ruling |
|---|---|---|
| `runs/g4adj-bmain-fix1-20260929T171651Z/FIX_ROUND_REPORT.json`, `outcomes` for the four B′ fixtures | "not keep: operator decision required (frozen rule 6 within the rule-7 re-adjudication)" | The re-adjudication did not end in an automatic keep, so it went to the operator. It is not a step-7 "failing again": the operator found no unresolved defect in the fixture/gold pair, and kept each fixture ("gold right → keep"). |
| `fixes/LATENT_DEFECTS.md`, "Directly relevant now" | "The four round-1 fixes that did not end in keep" | The same four; they did not end in an automatic keep. Their P6 reserves were not drawn. |
| `runs/g4adj-amain-fix1-20260929T185315Z/FIX_ROUND_REPORT.json`, `if_not_kept` | "not keep would mean replacement from the matching A′ reserve" | A statement of the option available before the operator decided; the operator kept all five. |

The recorded adjudicator verdicts are unchanged in every record: each fenced answer remains a disagreement.
