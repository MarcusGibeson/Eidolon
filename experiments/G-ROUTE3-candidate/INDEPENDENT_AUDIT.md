# G-ROUTE3 Design Audit

Date: 2026-09-24
Revision: **R6**
Verdict: **READY for external round-6 review.** This is not a verdict that Phase A may be authorized.
Authority: non-authoritative. It grants no execution, provider, routing or belief authority, and changes no
artifact. Provider generation calls during design, review and repair: **0**.

## Read this first: what this audit is worth

The agent that wrote the corpora and the code also wrote this audit.

- It said READY for R1 through R5, and each time an external review found blocking defects it had missed.
- In round 5, both blocking classes had been "repaired" only for the exact case the earlier probe used.

This document is a record of what the author checked, not an assurance. The R6 freeze goes to fresh
external reviewers under the operator's threat model (an honest operator, tamper-evident records).

## Round-6 repair: by class, not by instance

**Model output and the coding sandbox.** Any exception raised before the sandbox subprocess starts is the
model's failure, whatever its type. Only the subprocess stage can report a host failure.

**Finalization.** A single idempotent `_finalize` replaces the per-window recovery code. `--resume` routes
any run that holds every record, or is already complete, into it. A checkpoint one record behind is
reconciled.

**Closure.** Every non-complete end is a sealed closure record, anchored in git. A closed run is never
resumable.

**Git evidence.**

- Anchors are always re-applied (idempotently).
- An authorized Phase B requires the Phase A ledger, the run anchor and the table to be committed.
- The table is frozen by a governed launcher command.
- Orphan folders are cleared by a recorded step.

**Small repairs.**

- The launcher neutralizes proxies.
- Audit paths are absolute.
- Synthesis text normalizes typographic hyphens.
- `collect_evaluation` sanitizes its own input.

## Findings of this author pass, beyond round 5

| # | Finding | Repair |
|---|---|---|
| 1 | A new test showed that `collect_evaluation`, called directly on a raw lone surrogate, returned a record that could not be sealed | It sanitizes its input first, as the runner does |

## Checks performed for R6

- **Construction and independence.** The corpus and gold are byte-identical to R5 (checked with git), so all
  R5 construction checks still pass. The independence report is valid.
- **Declared per-cell tables.** `CONTAMINATION_ANALYSIS.md` now declares two tables: synthesis
  conclusion-rule families and research recommendation direction.
- **Deterministic tests.** They cover:
  - a full Phase A with pathological coding candidates (3,200-dash chains, JSON nested 1,500 deep, 3,000
    nested parentheses), which completes with no infrastructure failure;
  - every finalization crash window, each followed by `--resume` and a Phase B that is valid to open;
  - a checkpoint one record behind, at both the end and mid-run;
  - a closed run with an edited manifest, which is refused;
  - orphan clearing;
  - a Phase B refused when Phase A evidence is not committed;
  - a failed consumption anchor, re-applied on resume;
  - the governed table freeze, with a relative audit path resolved to an absolute one;
  - proxy neutralization.

## Residual limitations accepted into the R6 freeze

- **Pilot scale.** Zero failures in 4 bounds the per-cell failure rate below 0.527 and no lower.
- **Router inputs.** Task and risk classes are given to the router, not inferred.
- **Conversation** is a closed-field construct, and its prose is not graded.
- **Planning** uses one declared template.
- **Synthesis** statements are verbatim.
- **Research** cells are validated with different sub-skills from the ones they were qualified on.
- **Difficulty matching** is the author's judgment. Coding R1 is harder in B, which lowers only admission.
- **Unequal denominators.** B success needs 2 of 2, while A qualification needs 4 of 4.
- **Coding stops cannot be unsafe.** The pooled unsafe-stop gate is unchanged, and the rate excluding coding
  is reported.
- **Out of scope by the threat model:** a deliberate local adversary. Git anchor commits make one visible.
- **Ollama** does not attest that options or seeds are honoured.
- **G-ROUTE1 and G-ROUTE2** keep their earlier caveats and are not rescored.

## Verdict

**READY for external round-6 review** of the R6 freeze. Phase A may be authorized only after that review is
clean. The authorization is the verbatim sentence `Authorize G-ROUTE3 phase A execution <R6 binding> attempt 1`,
given to `tools/g_route3_launch.py`.
