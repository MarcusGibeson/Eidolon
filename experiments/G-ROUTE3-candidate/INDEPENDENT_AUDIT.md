# G-ROUTE3 Design Audit

Date: 2026-09-24
Revision: **R4**
Verdict: **READY for external round-4 review.** This is not a verdict that Phase A may be authorized.
Authority: non-authoritative. This audit grants no execution, provider, routing or belief authority, and it
changes no artifact. Provider generation calls during design, review and repair: **0**.

## Read this first: what this audit is worth

The agent that wrote the corpora and the code also wrote this audit. For R1, R2 and R3 it said READY, and
each time an external review found blocking defects it had missed; see the three `EXTERNAL_REVIEW_ROUND*.md`
records. This document records what the author checked. It is not an assurance.

The R4 freeze goes to fresh external reviewers. Phase A may be authorized only if that review is clean, and
only against the exact R4 binding.

## Round-4 repair, summarized

Every round-3 finding is repaired or declared. `EXTERNAL_REVIEW_ROUND3.md` names the test that locks each one.

Both operator decisions are implemented:

- Conversation is a two-line disclosed frame (`Answer`, `Actions taken`). The prose is not graded.
- A new attempt may follow only attempts that did not complete.

On the boundary:

- **Launcher.** Authorized runs go only through a frozen launcher. It builds the Ollama provider itself, and
  the authorized path refuses any other provider type and any override of the guarded root.
- **Authorization.** It is consumed inside the run lease, after the run exists. A resume must match the run
  id, the ledger's run root and the resume flag.
- **Sealed records.** Every call record carries the synthetic flag.
- **Provider evidence.** Phase B verifies each Phase A record against the provider's own raw body.
- **Only one complete attempt.** The Phase A run named in the table must be the only complete Phase A
  attempt.
- **Stuck attempts.** These can only be abandoned explicitly, with a recorded reason.

## Findings of this author pass, beyond round 3

| # | Finding | Repair |
|---|---|---|
| 1 | Under the new attempt rule, a killed run that cannot resume would block every later attempt forever | `abandon_attempt` and `--abandon`, requiring a reason that is disclosed with the attempt's outcome |
| 2 | "Actions taken: none (I have no tools)" and "No actions taken" are natural truthful values that an exact "none" check would reject | A small declared set of no-action forms, each optionally followed by a note |
| 3 | `**Answer:** P1` left a one-sided emphasis run in the value | Emphasis is stripped from both ends on every pass |
| 4 | The Ollama adapter's model inspection reads the G-ROUTE1 model bindings file | That file is now frozen and guarded as well. Receipts are still verified against G-ROUTE3's own bindings. |
| 5 | Phase B checked preconditions before refusing a synthetic Phase B on a real Phase A | The synthetic-provider rule and the synthetic-Phase-A requirement are checked first |

## Checks performed for R4

**Corpus construction** (`authoring/assemble_g3.py` writes nothing unless every check passes):

- **Alternative and incorrect replies.** All 48 alternative correct replies are accepted by both validators.
  They include a greeting line, decorated answer values, no-action forms carrying a note, and hypothetical
  prose. All 80 incorrect replies are rejected: wrong option, declared action, missing field, unlisted
  option.
- **Carried over from R3.** Every other R3 construction check still passes.

**Arithmetic.** Every gold value introduced in round 4 was re-derived by hand:

- A-CONV-R1-1: only Wednesday 10:00 is a weekday morning at 08:00 or later.
- B-CONV-R3-1: ages 28, 15 and 25 days, against a limit of more than 20.

**Independence.** The report is valid with 0 findings. Cross-cell shape matches are listed as
information; most of them come from the declared planning template.

**Deterministic tests** (`tools/g_route3_tests.py`; results in `DETERMINISTIC_TEST_RESULTS.json`). They
reproduce each of the round-3 reviewer's attacks, all now refused:

- the same run id under another root;
- a stub provider with empty raw bodies;
- resuming a finished synthetic run under a real authorization, then resealing its receipt;
- an attempt after a complete one, in both phases.

They also cover:

- legitimate retry after an incomplete attempt, with both attempts disclosed;
- the abandon step;
- the launcher's exact-sentence parsing and its own-provider construction;
- the two-field conversation grading;
- per-class unsafe-stop reporting.

## Residual limitations accepted into the R4 freeze

- **Pilot scale.** 0 failures in 4 bounds the per-cell failure rate only below 0.527.
- **Given classes.** Task and risk classes are given to the router, not inferred.
- **Conversation is closed-field.** It measures choosing the listed decision and declaring no action. The
  prose is not graded, so prose that contradicts the answer, or over-claims, goes undetected.
- **Planning.** It tests exact rule-following on one declared template.
- **Research.** Cells are validated on B with different sub-skills from those qualified on A.
- **Synthesis.** Statements are verbatim copies, so synthesis measures role assignment, coverage, merging
  and the conclusion, not paraphrase.
- **Difficulty matching.** This is the author's judgment.
- **Unequal denominators.** B success needs 2 of 2 and A qualification needs 4 of 4. Per-observation rates
  are reported.
- **Unsafe stops in coding.** Coding stops cannot be unsafe. The pooled gate is unchanged, and the rate
  excluding coding is reported.
- **Local seals carry no secret.** A forger who controls the machine and rewrites every sealed record, raw
  bodies included, consistently is stopped only procedurally: the Phase A result package is committed to
  git before Phase B is authorized.
- **Ollama.** It does not attest that options or seeds are honored.
- **G-ROUTE1 and G-ROUTE2.** Both keep their earlier caveats and are not rescored.

## Verdict

**READY for external round-4 review** of the R4 freeze. Phase A may be authorized only after that review is
clean. The authorization is the verbatim sentence `Authorize G-ROUTE3 phase A execution <R4 binding> attempt 1`,
given to `tools/g_route3_launch.py`.
