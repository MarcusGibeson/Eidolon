# O3 identifier gate: recorded decision (pre-seal repair)

**Context.** O3 (`G-ROUTE4_OBLIGATIONS.md`) requires the named-entity and identifier comparison across all G-ROUTE4
fixtures of every class, main and reserve, pairwise and against all G-ROUTE3 A and B fixtures. G-ROUTE3's frozen
checker, `tools/g_route3_independence.py`, wraps its identifier pattern in literal backspace bytes (line 57), so its
identifier branch never matches. Only its capitalized-name branch works.

**Decision.**

1. **The frozen G-ROUTE3 checker stays byte-identical.** It is not modified, and it is still run: its entity
   detection feeds the O3 entity comparison exactly as before. `check_corpus.py` pins its sha256
   (`177aa18abc21057d94b1b34c94f7a05960248f0dd29a6d98763660c445b4509b`, content with line endings normalized to
   LF) and reports any change as a failure.
2. **The supplementary identifier check is the binding, prospective O3 identifier gate for G-ROUTE4.** It uses the
   evident intended pattern `\b([A-Z]{1,5}-?\d[\w.-]*)\b`, excludes the design's structural ids (a single capital
   followed by digits in a structural field, such as `C1`, `S2`, `O41`, `F3`, `P1`), and requires:
   - 0 identifiers shared between any two G-ROUTE4 fixtures, or between a G-ROUTE4 fixture and any G-ROUTE3 fixture;
   - every identifier found in a G-ROUTE4 fixture to be declared in its design record.

   The pattern is pinned by sha256 (`a3773a982c16579d94cede99539e0b9cacca1347f96774759a84bbb7788adaae`) in
   `check_corpus.py`, and a changed pattern is a failure.
3. **No rescoring of G-ROUTE3.** G-ROUTE3's results, its independence report and its "0 shared identifiers" claim
   are not re-evaluated, re-scored or reinterpreted. The defect is disclosed; it is not applied backwards.

**Tests.** `test_planning_corpus.py` plants a shared identifier and an undeclared identifier, which the gate catches
while the frozen detector cannot. `test_repairs_corpus.py` proves the two pins fire: a changed gate pattern, and a
changed digest for the frozen checker.

**Current result.** 17 G-ROUTE4 and 11 G-ROUTE3 identifiers, 0 shared, 0 undeclared.
