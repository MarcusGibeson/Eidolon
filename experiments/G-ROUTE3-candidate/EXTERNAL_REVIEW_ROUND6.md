# G-ROUTE3 external pre-contact review, round 6

Date: 2026-09-24
Reviewed artifact: `G-ROUTE3-EXECUTION-R6`, binding `2e5e8cc72570b6be1dd92b1bebe80d0366b3b1c489fb75a8d1f4404886e062e3`
(commit `0a5a5e1`)
Outcome: **not clean.** R6 was never authorized, and it is void. No provider generation calls were made
during the review.

## Reviewers and verdicts

| Reviewer | Scope | Verdict |
|---|---|---|
| Fixtures | All 96 fixtures, derived independently. About 13,000 outputs through a mirror of the runner's per-call path, plus about 95 synthetic Phase A runs. | **FINDINGS:** 3 blocking. On the operator's two questions: every gold answer is derivable, and there are no hidden codes or ordering rules. |
| Boundary | Lifecycle and boundary probes on the authorized path, plus independence | Part 3 **BORDERLINE**. Part 4 **FINDINGS:** 5 blocking. |

## Blocking findings

**Crash safety, from the fixture reviewer:**
- **F1.** A lone surrogate in a research claim id got into validator reasons, which were persisted, so the
  run crashed while sealing.
- **F2.** Deep nesting in a junk key hit recursion limits during sealing or verification. The run crashed,
  or completed and could then never be verified.

**Grading, from the fixture reviewer:**
- **F3.** Only some Unicode dash and space characters were normalized. A correct answer that used U+2010
  (hyphen) or U+202F (narrow no-break space) failed in Corpus A cells.

**Lifecycle, from the boundary reviewer:**
- **L1.** `--resume` through the launcher could not reopen an activity that was already terminal.
- **L2.** The manifest call counter drifted from the sealed records after a crash between sealing a record
  and updating the manifest.
- **L3.** A recorded infrastructure failure was skipped on resume.
- **L4.** Writes were not atomic, so torn files wedged every recovery path.
- **L5.** A ledger anchor that failed before an abandon could never be committed.

## Non-blocking findings

**Grading:**
- A self-recursion rule and several operators were not disclosed.
- The cause of a coding candidate's rejection was not stored.
- The synthesis check was not verbatim.
- A duplicate Answer line was accepted.
- A trailing-strip regex was quadratic.

**Lifecycle:**
- Stale-lease recovery needed a hand edit.
- A two-file tamper was git-visible but not checked by code.
- A host-caused compile failure was charged to the model.
- The `web_security` domain was shared within the coding R3 cell without being declared.

## Response

The operator decided on 2026-09-24 **not** to patch R6 further. Instead, the run lifecycle is to be
restructured around one authoritative journal per run. That journal/replay design is
`R7_LIFECYCLE_DESIGN.md`, which is itself under design review; see `R7_DESIGN_REVIEW_ROUND1.md`.

The crash-safety findings F1 and F2, and every lifecycle finding, are addressed by that design:
- entries hold facts only and pass through `safe_value`;
- publication is atomic;
- state is derived by replay;
- recovery is a single command shape;
- anchoring uses the git evidence ref.

The grading findings (F3 and the non-blocking grading items) are a **scientific change**. They will be
handled in their own change record and review, listing every digest they affect, and are not part of the
lifecycle design.
