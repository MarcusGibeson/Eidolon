# G-ROUTE4 external corpus review, round 1: final reconciliation

**Status: OPEN at an operator decision point.** Successor to `RECONCILIATION_R1.md` (not modified).

## Closing conditions

| Condition | Met | Evidence |
|---|---|---|
| repaired fixtures completed re-adjudication | yes | CLOSED: 6 of 6 kept, 0 replaced |
| every MUST-FIX from both reviewers resolved | yes | 5 MUST-FIX (A1-A3, B1, B2): all resolved |
| disclosures and errata recorded | yes | A4-PLAN-R3-04, A4, A5 disclosures; errata 1 and 2; B3 O2 disclosure; B10 provenance |
| independence re-check (pinned authoring-stage tool) reproduces the frozen values | yes | 63 class-level values reproduced; bounds met; 0 problems |
| final independence re-check using the forked module reproduces the frozen values | **no** | NOT RUN: the forked module g_route4_independence does not exist (tools/g_route4_*: none); it is written in design step 4 (implementation), which is not authorized; nothing was substituted for it |

## MUST-FIX findings (both reviewers)

| Finding | Reviewer | Status | Resolution |
|---|---|---|---|
| B1 | B | RESOLVED | operator step-7 ruling; historical wording annotated (adjudication/errata/STEP7_RULING_ANNOTATION.md) |
| B2 | B | RESOLVED | erratum 1 bound to the unchanged B_MAIN_CLOSURE.json |
| A1 | A | RESOLVED | 4 fixtures fixed (cr1) and re-adjudicated; all kept |
| A2 | A | RESOLVED | B4-CONV-R1-08 fixed (cr1) and re-adjudicated; kept |
| A3 | A | RESOLVED | B4-CONV-R2-28 fixed (cr1) and re-adjudicated; kept |

BLOCKING findings: 0 from either reviewer.

## Remediation outcome

- A4-SYNTH-R1-01: keep (frozen rule)
- B4-CONV-R1-08: keep (frozen rule)
- B4-CONV-R2-28: keep (frozen rule)
- B4-SYNTH-R1-02: keep (frozen rule)
- B4-SYNTH-R2-15: gold right -> keep (operator, B1 ruling)
- B4-SYNTH-R3-08: keep (frozen rule)

## Notes and conditions

- **Recorded disclosures:** A4-PLAN-R3-04 (kept with disclosure), A4 (research P4 coverage), A5 (synthesis constant conclusions), B3 (O2 reclassification), B9 (gold changes in 9 fixes).
- **Errata to `B_MAIN_CLOSURE.json`:** 1 (disagreement causes) and 2 (15 reserves).
- **Freeze conditions:** B7 (the forked-module re-check reproduces the values) and B8 (B′ fix-round per-cell counts, now bound in `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json`).
- **No action:** A6, A8, A9, A11, B4, B6.

## Successor records (the closed records are unchanged)

- `INDEPENDENCE_REPORT_CR1.json`: sha256 `23828827ac0e36663b7db3217308910ca4e4323314c6eb97504bbd84a410893c`
- `CONTAMINATION_ANALYSIS_CR1.md`: sha256 `8158107f89476d1dddb797f99c31843874adb5eea505a4deff27542c840c7001`
- `adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json`: sha256 `08561c8429d7fe73ceda737a4d232790846348c3138ba39200a6b901bee787ec`
- `adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json`: sha256 `9ad124e2e66c35537a09e9f137c0e0b8d17ec747f11494bac5c025543a725236`
- `adjudication/fixes/cr1_bmain/FIX_CHECK_REPORT.json`: sha256 `9472fd763b144b01f510c50b168f30e2ed95a49cc1e527357e09e11f75ced784`
- `corpus_review/round1/REMEDIATION_CLOSURE_R1.json`: sha256 `353a917779aea3e85917965206a0e6c67a2d9b8f711e8c6362a49c4a8280e581`

Final corpus (26 fixes): A′ `9272070be34c821ff9df2aa74c997ce3dbd8ba7059b134b4f999c25be7e5df28` / gold `55b006c2bd438d8862c3321aa932c45cb8570776510e132e4eacca32ac268e9a`; B′ `a27c7638c53117de606e4b8289d382036968f1fbabc4e6a6d922146d3541872d` / gold `8c134f610740f86fad645504065bdbcd83a29a8bf74683d3745fafc9c2a1beea`.

## Open point

The operator made the forked-module re-check a condition of closing round 1. That module is produced by design step 4 (implementation), which follows the external corpus review in the frozen order of work and is not authorized, so the condition cannot be met at this stage. The same re-check is already a freeze condition (B7). The operator decides how round 1 proceeds; no criterion has been weakened or reinterpreted here.

