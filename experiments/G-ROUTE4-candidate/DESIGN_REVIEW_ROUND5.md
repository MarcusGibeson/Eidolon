# G-ROUTE4 design review, round 5

Date: 2026-09-29.
Reviewed: `DESIGN_CANDIDATE.md` revision 5 (commit `69a1cec`).
Answered by: revision 6.

Gate: the operator's safety-gated rule, as in the earlier rounds.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | 0 BLOCKING, 5 MUST-FIX, 5 notes |
| B | Protocol, R7 reuse, implementability | 0 BLOCKING, 3 MUST-FIX, 7 notes |

**What was confirmed:**
- Every previously verified number reproduced again (Reviewer A).
- The tokenizer, the 25% boilerplate rule and the shared-rule removal match G-ROUTE3's code.
- The G-ROUTE1/G-ROUTE3 bindings equality and the closure hold (Reviewer B).
- The D8 remainder text matches all 16 G-ROUTE3 research prompts.
- The resumed kill point at N−1 is implementable.

Both reviews were read-only, with no provider contact.

## Reviewer A

| # | Class | Finding | Disposition in revision 6 |
|---|---|---|---|
| M1 | MUST-FIX | The same-family template gate was ambiguous: either vacuous, or infeasible, depending on the 30% cap's denominator. | **Simplified.** Template removal is dropped. Family templates count as content, and every pair, same-family included, must meet the 0.20 limit. No template loosening remains. |
| M2 | MUST-FIX | The pool was undefined; pooling loosened entity detection; the exemption lists were not frozen. | One pool per class for every check (the sealed main corpus and reserve, plus G-ROUTE3 A and B). G-ROUTE3's exemption lists are frozen byte-identical. The pooled vocabulary and the detector's blind spots are declared, with a supplementary exact comparison of structured values. The cross-experiment boilerplate blind spot is declared. |
| M3 | MUST-FIX | The action-set exclusion plus the planning and synthesis signature exemption allowed identical gold. | No two fixtures may have identical canonical gold, within G-ROUTE4 and against G-ROUTE3. |
| M4 | MUST-FIX | The audit sample was unstratified, predictable and without consequence. | Every A′ fixture gets the full three-adjudicator treatment. The B′ sample is stratified per cell and chosen by commit-then-reveal from the seal. A replacement inherits sampled status. Any fix in a sampled cell triggers the full treatment for that whole cell. |
| M5 | MUST-FIX | The answer-position balance was undefined with mixed option counts, and could not be preserved by replacements. | Every conversation fixture has 4 options (declared). Gold position is a blueprint and reserve-matching feature. |
| Notes | — | Reserve depth and family; the id-exclusion scope; the untouched subset is the most filtered; removal by trigram set; the reserve total. | A′ reserves share their slot's family, and the halt risk is declared. The id exclusion is limited to structural-id fields. A disputed-but-kept subset is added. All removal is by trigram set. The total is about 200. |

## Reviewer B

| # | Class | Finding | Disposition in revision 6 |
|---|---|---|---|
| M1 | MUST-FIX | The grading differential could not be built against G-ROUTE3's file-bound entry points. | The forked entry points under test are named. `indexed_fixture_gold` and `runtime_fixtures` are injected in each process, with ids mapped. One `routing_lookup` is applied at `decide`, never through `verify_table`. Aggregates and cell verdicts go to the oracle. |
| M2 | MUST-FIX | Git commit ids inside committed blobs escaped normalization. | Git blob, tree and commit ids, including `evidence_head_before` and `*_commit` fields, are derived digests. The object chain is rebuilt in order with the fixed date. Phases A, the table freeze and B are covered. |
| M3 | MUST-FIX | The frozen allowlist missed references the design requires. | Named entries for: the bindings equality test, the seed-disjointness test, the module-rule test and probes, both differentials, and the data-root test (a static read or subprocess). |
| Notes | — | Guarded list; dependency versions; D8 spacing; differential inputs (bodies, fault-free run, union map); threshold keys; the data-root test importing G-ROUTE3; audit-sample scope; fixes failing re-checks; repeated combinations exhausting the reserve. | All answered in revision 6. |

## Next

Revision 6 goes to review under the operator's chosen acceptance path.
