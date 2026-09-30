# G-ROUTE4 contamination and independence analysis: final corpus after corpus review round 1

Successor to `CONTAMINATION_ANALYSIS.md` (not modified; it remains the record of the 20-fix corpus that the external corpus review examined). The **final corpus** is the seal with all **26** recorded fixes overlaid: B′ round 1 (14), A′ round 1 (6) and the review-driven cr1 fixes (6). No fixture was replaced and no reserve was drawn.

Values: `INDEPENDENCE_REPORT_CR1.json` (sha256 `23828827ac0e36663b7db3217308910ca4e4323314c6eb97504bbd84a410893c`). Adjudication: `adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json` (`08561c8429d7fe73…`) and `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json` (`9ad124e2e66c3553…`).

**Result: every frozen independence measure passes on the final corpus, with 0 problems, and all 63 class-level values recorded in the frozen `INDEPENDENCE_REPORT.json` are reproduced exactly.** The re-check uses the pinned authoring-stage tool that produced those values; the re-check with the stage-4 forked module is a freeze condition (B7) and has not been run, because that module does not exist yet.

## Binding

| Item | Value |
|---|---|
| Fixes, B′ round 1 | commit `28718001d8e4`; 14 fixtures |
| Fixes, A′ round 1 | commit `8774a57a4bfc`; 6 fixtures |
| Fixes, cr1 | commit `2baa3936ddd4`; 6 fixtures |
| Final A′ main (80), model-facing / gold | `9272070be34c821ff9df2aa74c997ce3dbd8ba7059b134b4f999c25be7e5df28` / `55b006c2bd438d8862c3321aa932c45cb8570776510e132e4eacca32ac268e9a` |
| Final B′ main (305), model-facing / gold | `a27c7638c53117de606e4b8289d382036968f1fbabc4e6a6d922146d3541872d` / `8c134f610740f86fad645504065bdbcd83a29a8bf74683d3745fafc9c2a1beea` |
| Tool | `check_corpus.py` at staging `dd8193b` (sha256 `b3f6500b4b39a80c…`) |
| Generated at | parent commit `3d9b2418043c064909d0c624ae5a692f28b60151` |

## Frozen measures: frozen report against the final corpus

| Measure | Criterion | Frozen report (20 fixes) | Final (26 fixes) |
|---|---|---|---|
| Trigram Jaccard, every pair | ≤ 0.2 | 0 pairs over | 0 pairs over (max 0.1788) |
| Shared named entities (O3) | 0 | 0 | 0 |
| Shared identifiers (O3) | 0 | 0 | 0 |
| Identical canonical gold (N1) | 0 | 0 | 0 |
| Fine signature repeated A′/B′ in a cell | 0 | 0 | 0 |
| Canonical research signature repeated | 0 | 0 | 0 |
| Shared exact values (O6) | 0 | 0 | 0 |
| O5 single-family boilerplate | 0 | 0 | 0 |
| Conversation near-miss construct | all | 142 | 142 of 142 |

## Overlap by class (final corpus)

| Class | Pool | Boilerplate trigrams | Max Jaccard | Max pair | Pairs over 0.20 |
|---|---|---|---|---|---|
| Research | 152 | 27 | 0.1788 | A4-RSRCH-R3-02 / B4-RSRCH-R3-X11 | 0 |
| Synthesis | 116 | 11 | 0.0764 | B4-SYNTH-R3-16 / B4-SYNTH-R4-X01 | 0 |
| Conversation | 158 | 7 | 0.0976 | B4-CONV-R2-15 / A4-CONV-R3-X03 | 0 |
| Planning | 116 | 34 | 0.0619 | B4-PLAN-R1-07 / A4-PLAN-R1-X03 | 0 |
| Extraction | 122 | 6 | 0.1224 | A4-EXTR-R4-03 / A4-EXTR-R4-X03 | 0 |

## N8: maximum same-family A′–B′ overlap per cell (main corpora)

| Class | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Research | 0.0955 (RS3, 12 pairs) | 0.1597 (RS2, 12 pairs) | 0.0581 (RS4, 12 pairs) | 0.0 (RS3, 1 pair) |
| Synthesis | 0.0449 (SY4, 12 pairs) | 0.0305 (SY1, 12 pairs) | 0.0455 (SY4, 12 pairs) | no same-family pair |
| Conversation | 0.0412 (CV4, 20 pairs) | 0.0508 (CV6, 18 pairs) | 0.0429 (CV5, 18 pairs) | no same-family pair |
| Planning | 0.0514 (PL3, 12 pairs) | 0.0324 (PL6, 12 pairs) | 0.0594 (PL3, 12 pairs) | 0.0 (PL1, 1 pair) |
| Extraction | 0.0182 (EX4, 12 pairs) | 0.0495 (EX5, 12 pairs) | 0.0351 (EX5, 12 pairs) | no same-family pair |

## Effects of the six review-driven fixes (cr1)

| Fixed fixture | Finding | Max Jaccard, sealed text | Max Jaccard, fixed text |
|---|---|---|---|
| A4-SYNTH-R1-01 | A1 | 0.0278 | 0.0261 |
| B4-CONV-R1-08 | A2 | 0.0276 | 0.0276 |
| B4-CONV-R2-28 | A3 | 0.0276 | 0.0276 |
| B4-SYNTH-R1-02 | A1 | 0.0111 | 0.0215 |
| B4-SYNTH-R2-15 | A1 | 0.0368 | 0.0305 |
| B4-SYNTH-R3-08 | A1 | 0.0397 | 0.0331 |

Of the 20 earlier fixed fixtures, 6 now have a different maximum overlap, all synthesis fixtures sharing relabelled role names with the new SY1 fixes: A4-SYNTH-R2-03 0.0261 → 0.0331 (with B4-SYNTH-R3-08); A4-SYNTH-R4-01 0.0192 → 0.0253 (with B4-SYNTH-R3-08); B4-SYNTH-R1-01 0.0148 → 0.0208 (with A4-SYNTH-R1-01); B4-SYNTH-R2-13 0.0179 → 0.0213 (with A4-SYNTH-R1-01); B4-SYNTH-R2-14 0.0196 → 0.0215 (with B4-SYNTH-R1-02); B4-SYNTH-R3-09 0.0196 → 0.0206 (with B4-SYNTH-R1-02). The largest is 0.0331, under the 0.20 bound; the other 14 are unchanged. The fix-text exemption still covers exactly the 12 declared research source texts; the cr1 fixes need none.

## Exposure and contamination

**Adjudication exposure (declared).** In addition to the sessions recorded in `CONTAMINATION_ANALYSIS.md` (259 A′ and 507 B′), the review-driven fixes were re-adjudicated in 3 A′ and 7 B′ remediation sessions (`claude-opus-5-5`, O2 `7691126e…`; each slot contacted once; 0 retries, 0 in doubt). Only model-facing text was sent; no reserve fixture was sent. The tested tiers are pinned local models and were not contacted.

**Residual filter (declared, step 12).** Descriptive subsets, never gating: A′ 54 untouched and 19 disputed-but-kept-unchanged; B′ 238 and 48. Every fixed fixture is flagged (A′ 7, B′ 19).

**Operator decisions (declared, non-blind).** 'Gold right → keep': A′ 24 (19 unchanged, 5 after their fix); B′ 39 (34 unchanged, 5 after their fix). Retentions after a fix follow the operator's B1 step-7 ruling (`adjudication/errata/STEP7_RULING_ANNOTATION.md`).

## Disclosures added by corpus review round 1

- **A4-PLAN-R3-04:** The three adjudicator refusals are retained as a disclosed limitation of its historical adjudication. Reviewer A independently derived the reference answer and matched gold, and neither reviewer identified a derivability defect. The refusals alone do not justify a fixture or gold change.
- **A4:** The A′ corpus does not exercise research P4 in the case where reposts are the only support, while B′ does (B4-RSRCH-R1-12, B4-RSRCH-R2-12, B4-RSRCH-R3-12). No fixture is added or modified to eliminate it.
- **A5:** Synthesis families SY4, SY5 and SY6 have a constant conclusion within each family (decision_reserved, constraint_breached and behavior_by_design respectively). This is not a defect and does not authorize a corpus change.
- **Errata to `B_MAIN_CLOSURE.json`** (the closed file is unchanged): erratum 1 (the B′ disagreement causes: 91 fenced format-only, 16 fenced with a content disagreement, 24 content-only) and erratum 2 (15 reserves with known defects, not 14).

## Latent defects

- **Final main corpus:** no fixture carries a known unfixed defect. The four SY1 fixtures and the two conversation fixtures named by the review were fixed and re-adjudicated.
- **Unused reserves with known defects** (never drawn, never sent): P6 'only': A4-RSRCH-R2-X02, A4-RSRCH-R4-X03, B4-RSRCH-R1-X06, B4-RSRCH-R1-X14, B4-RSRCH-R2-X06, B4-RSRCH-R2-X14, B4-RSRCH-R3-X06, B4-RSRCH-R3-X14; SY1 diagnosis role: A4-SYNTH-R1-X01, A4-SYNTH-R2-X03, A4-SYNTH-R4-X01, B4-SYNTH-R1-X01, B4-SYNTH-R3-X03; weak anonymity paraphrase: B4-RSRCH-R3-X03; weak weekend (courier) paraphrase: B4-RSRCH-R2-X04.

## Declared blind spots and conditions carried to the freeze

- The blind spots in `CONTAMINATION_ANALYSIS.md` are unchanged (N3; the entity detector's sentence-initial and JSON-string-start cases, covered by O6; the declared exclusions; no conversation signature; planning and synthesis exempt; difficulty matching by judgment).
- **B7:** the final independence re-check with the forked module must reproduce these values before the freeze.
- **B8:** the B′ fix-round per-cell counts are bound in `B_MAIN_CLOSURE_ADDENDUM_CR1.json` for the freeze records.

