# G-ROUTE3 Design Audit

Date: 2026-09-24
Revision: **R5**
Verdict: **READY for external round-5 review.** This is not a verdict that Phase A may be authorized.
Authority: non-authoritative. It grants no execution, provider, routing or belief authority, and changes no
artifact. Provider generation calls during design, review and repair: **0**.

## Read this first: what this audit is worth

The agent that wrote the corpora and the code also wrote this audit. It said READY for R1 through R4. Each
time, an external review then found blocking defects it had missed; see the four `EXTERNAL_REVIEW_ROUND*.md`
records. In round 4, two of the blocking defects came from a leniency this author added in round 4 itself.

This document records what the author checked. It is not an assurance. The R5 freeze goes to fresh external
reviewers, who are given the operator's threat model. Phase A may be authorized only if that review is clean.

## Threat model (operator decision)

G-ROUTE3 assumes an honest operator and relies on tamper-evident records.

- **What the code must stop:**
  - accidents;
  - misuse through any supported path;
  - cheap tampering.
- **What is out of scope, and declared:**
  - a fake model server;
  - a second checkout;
  - a consistent rewrite of sealed files together with the git history.
- **What counters the out-of-scope cases:** the launcher's local git anchor commits.

## Round-5 repair, summarized

Every round-4 finding is either repaired or declared. See `EXTERNAL_REVIEW_ROUND4.md`, which names the test
that locks each one.

- **Conversation.** The "Actions taken" line is a closed field. The prompt says to write exactly `none`, and
  nothing may follow it.
- **Robustness to model output.** No model output can crash collection, scoring or sealing. A full 288-call
  Phase A with hostile outputs completes.
- **Tamper evidence:**
  - the ledger is hash-chained;
  - the ledger and the fixed run root must agree exactly;
  - the attempt and the authorization are sealed into every record;
  - the endpoint is fixed;
  - the endpoint and the model receipts are recorded;
  - a git anchor commit is made at each consumption and each completion.
- **Lifecycle:**
  - an interrupted finalization completes on resume;
  - a finished collection cannot be abandoned;
  - the host baseline for coding timeouts is honest.
- **Balance.** Within each cell, conversation answers sit at the same position in A and B. A-CONV-R3-2 now
  requires checking an expiry date.

## Findings of this author pass, beyond round 4

| # | Finding | Repair |
|---|---|---|
| 1 | Resuming an attempt would have re-anchored the ledger entry that was already consumed. `git commit` with nothing to commit fails, which would have stopped a legitimate resume. | The runner anchors an entry only when it creates it, and `git_anchor` does nothing when the file is already committed with the same content. Both behaviours are tested. |
| 2 | With 3-option and 4-option fixtures paired in one cell, a per-fixture modulo gave different answer positions in A and B | Each position is computed from the cell and slot, modulo the smallest option count (3). The independence tool now reports any imbalance as a finding; it reports none. |
| 3 | Coding canonicalization, which the runner calls directly, did not tolerate `RecursionError` | It now does |

## Checks performed for R5

**Construction self-validation.** All 48 alternative correct replies are accepted by both validators, and
all 96 incorrect replies are rejected. The incorrect set includes an action smuggled in after "none". All
earlier construction checks still pass.

**Arithmetic.** Every computed gold value added in round 5 was re-derived by hand. A-CONV-R3-2: the
agreement expired on 2034-01-31, before 2034-02-14.

**Independence.** The report is valid with 0 findings. Answer positions are balanced within every cell.

**Deterministic tests.** These are in `tools/g_route3_tests.py`, and their results are in
`DETERMINISTIC_TEST_RESULTS.json`. They include the round-4 reviewer's attacks, now refused or
tamper-evident:
- ledger deletion and replay;
- an edited ledger entry;
- an altered anchor file;
- an endpoint flag.

They also include the reviewer's crashes, now recorded as failures; the interrupted-finalization recovery;
the abandon guard; and the git anchor, which commits exactly one file and does nothing on resume.

## Residual limitations accepted into the R5 freeze

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

**READY for external round-5 review** of the R5 freeze. Phase A may be authorized only after that review is
clean. The authorization is the verbatim sentence `Authorize G-ROUTE3 phase A execution <R5 binding> attempt 1`,
given to `tools/g_route3_launch.py`.
