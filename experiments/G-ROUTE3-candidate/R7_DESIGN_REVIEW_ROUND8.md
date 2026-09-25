# R7 lifecycle design review, round 8 (safety-gated)

Date: 2026-09-25
Reviewed: `R7_LIFECYCLE_DESIGN.md` revision 8. The design is at commit `0b753ce` and the gate ruling at `8c7af28`.
The document digest is `55485260…15cc03`.

**Gate (operator ruling after round 7).** Only five classes of finding block:
1. a repeated call (G1);
2. best-of-N (G3);
3. contact without the correct verbatim sentence;
4. a silent scientific or grading change;
5. a contradiction with operator rulings.

Every other finding becomes a mandatory obligation for the implementation review and the certification
campaign.

| Reviewer | Focus | Verdict | Blocking |
|---|---|---|---|
| A | Journal and replay correctness, and recoverability | **CLEAN** | 0. There are 13 obligations and 2 non-blocking items. |
| B | Scientific integrity, and authorization and attempt semantics | FINDINGS | 1, in class 4. There are obligations and non-blocking items. |

Both reviews were read-only and contacted no provider. Both reviewers ran offline probes of R6's pure functions
with bytecode writing disabled.

What each reviewer verified:
- **Reviewer A:** every §6 and §7 `closed` publication against the R3 reason function, and G1 on every path.
- **Reviewer B:** R6 and R7 give identical values at every step for six coding variants, including lone
  surrogates, fences, trailing newlines and split pairs, through to `collect_evaluation`.

## Blocking finding and its resolution

**B-N1 (class 4): grading depends on recursion depth.**

*Finding.* Whether `json.loads` and R6's recursive helpers succeed on outputs nested near Python's recursion limit
depends on how deep the call stack already is. B measured parse limits of 992, 982 and 972 at +0, +10 and
+20 caller frames. B also showed `_coding_candidate_error` flipping between `None` and `RecursionError` on the
same input.

R7 runs these functions at different depths than R6 did, so outputs in a narrow band could be graded or
attributed differently, and that difference was undeclared. R6 itself was not consistent here, because launch
and resume ran at different depths.

**Revision 9:**
- **Pinned budget.** Every function that handles model output runs from a fresh thread at a pinned stack size,
  recursion limit and entry depth. This makes R7 deterministic across the holder, worker, scorer and R3, and
  across launch and resume.
- **Declared band.** The band where R7 may differ from R6's own, variable, result is declared as a carried R6
  residual (§1.2), and belongs to the grading record (§22).
- **Certification case.** The campaign covers nesting 960–1000. The confirmation review below widened this.

**Related, from Reviewer A's O1 and Reviewer B's O4.** R3's re-derivation of `executable_sha256` depended on
stack depth, on the corpus and on the guarded code. That made replay impure, and could turn drift into a false
integrity failure. Revision 9 changes this:
- `execution_started` now **stores** `executable_json`, and the worker runs exactly those bytes.
- R3 checks only its own sha256, which is pure.
- The re-derivation equality check moves to the scorer, after the drift check, at the pinned budget.

**Also in revision 9, from Reviewer A's O5.** §10.8 now excludes commit ids as well as the restore log.

## Round-7 closure

- **Reviewer A:** F1–F10 are all closed.
- **Reviewer B:** B1–B4 are closed. B1 is closed for encoding; the depth issue is the new B-N1 above.

## Obligations

Every remaining item from both reviewers is recorded in `R7_IMPLEMENTATION_OBLIGATIONS.md`. The implementation
review must check each one, and each lists its certification-campaign case.

## Confirmation review of revision 9 (one fresh reviewer, safety-gated)

**Verdict: FINDINGS.** There was one narrow class-4 finding, fixed in text.

**Determinism.** Determinism was confirmed on CPython 3.11.9 on Windows. On a pinned fresh thread (64 MiB stack,
recursion limit 1000), `json.loads` reached nesting 991 whatever the spawning thread's depth, and in two
processes. R6's chain gave identical results at every depth from 955 to 1000. On the main thread, the flip point
moved.

**Finding.** The declared band covered only JSON nesting. It missed `validate_candidate_ast`, which converts the
AST at three times the recursion limit. On the main thread, a whitelist-clean `new` with a binary chain of about
2,940–2,970 terms is rejected with `RecursionError` at a deeper launcher depth, which counts as the model's
failure. At the pinned budget the same candidate is accepted and can pass. The pinned values were also not
stated.

**Fixed in revision 9:**
- The values are pinned: limit 1000, 64 MiB stack, and one shared `run_pinned` wrapper for the holder, the worker
  and the scorer.
- The band is declared for each mechanism: JSON about 960–1000, and syntax-tree chains about 2,900–2,980 terms.
- The measured thresholds are recorded in the freeze, and both bands are certification cases.
- The band is listed in §22.

**Non-blocking items, also fixed:**
- The holder derives the executable from the in-memory corpus, bound by digest, never re-read after the drift
  check.
- The resume wording is corrected.
- The stale mention of R3 is removed.
- The scope of the scorer check is defined:
  - for the current attempt, a mismatch is an integrity failure;
  - for earlier closed attempts, a mismatch is disclosed, and the position counts as undeterminable.
- `run_pinned` re-raises exceptions with their class intact.
- The worker reports the digests of the modules it loaded, and a mismatch refuses as drift.
