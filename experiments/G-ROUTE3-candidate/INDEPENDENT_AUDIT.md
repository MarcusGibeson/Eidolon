# G-ROUTE3 Design Audit

Date: 2026-09-24
Revision: **R3**
Verdict: **READY for external round-3 review.** This is not a verdict that Phase A may be authorized.
Authority: non-authoritative. It grants no execution, provider, routing or belief authority and changes no
artifact. Provider generation calls during design, review and repair: **0**.

## Read this first: what this audit is worth

This audit was performed by the agent that wrote the corpora and the code. It said READY for R1 and again
for R2. Each time, an external review then found blocking defects it had missed; see
`EXTERNAL_REVIEW_ROUND1.md` and `EXTERNAL_REVIEW_ROUND2.md`.

It is a record of what the author checked, not an assurance. The R3 freeze goes to fresh external
reviewers. Phase A may be authorized only if that review is clean, and only against the exact R3 binding.

## Round-3 repair, summarized

Every round-2 finding is repaired. `EXTERNAL_REVIEW_ROUND2.md` names the test that locks each one.

Both operator decisions are implemented:

- conversation uses a disclosed answer frame instead of phrase anchors;
- coding compares `old` ignoring trailing newlines.

The boundary no longer trusts any unsealed Phase A field:

- the qualification table is re-derived from the sealed call records;
- the terminal receipt chains to those records and to the score;
- authorizations are numbered attempts in a fixed ledger;
- the synthetic path requires a declared synthetic provider;
- a test binds the runtime import closure to both the freeze and the guard.

## Findings of this author pass, beyond round 2

All were repaired before the freeze.

| # | Finding | Repair |
|---|---|---|
| 1 | The runtime import-closure test found two `conscious_agent` modules (`json_storage.py`, `metadata_mutation_coordination.py`) imported by the activity module but not guarded | Added to the guard and to the freeze |
| 2 | The new coarse research signature and the derived-field extraction signature flagged four same-cell pairs. In three of them the reasoning differs: research R2 and R3 each pair a conflicting-sources fixture with a narrower-scope fixture, and extraction R1 pairs copying a value with computing one. The fourth, A-RESEARCH-R1-1 / B-RESEARCH-R1-2, is a genuine same-shape pair. | The signatures were refined to tell the three different-reasoning pairs apart. B-RESEARCH-R1-2 was changed so both its claims are contradicted by numbers. |
| 3 | The two R4 synthesis references were about 270 tokens compact, too close to the 350-token cap | Observations shortened. Assembly now bounds every JSON reference. |
| 4 | Conversation answers sat at almost the same option index | Answer positions are pseudo-random. Assembly and a test check the spread. |
| 5 | The trigger note overstated one condition: a synthesis statement with no cited observation is already rejected operationally | Corrected after probing which conditions are live on accepted outputs |
| 6 | Phase B checked preconditions before the synthetic-provider rule | The rule is now checked first |

## Checks performed for R3

**Corpus construction.** These checks run in `authoring/assemble_g3.py`, which writes nothing unless every
check passes.

- **Shape.** 48 fixtures per corpus, 2 per cell, in disjoint namespaces.
- **Reference answers.**
  - Every reference answer passes the G-ROUTE3 operational validator and the G-ROUTE3 semantics. For coding,
    it also passes the isolated runner inside the whitelist.
  - Every buggy coding source fails its own tests.
  - For every coding fixture, a correct fix whose `old` lacks the final newline, or has an extra one, is
    accepted by both validators.
  - No trigger fires on any reference answer.
- **Alternative and incorrect replies.** All 48 alternative correct replies are accepted by both validators,
  and all 64 incorrect replies are rejected.
- **Conversation.** Every prompt ends with the answer-frame instruction, every gold answer is a listed
  option, and answer positions vary.
- **Output budget.** Every JSON prompt discloses the output budget, and every JSON reference answer is at
  most about 250 tokens compact.
- **Planning.** Actions are never listed in gold order.
- **Extraction.** String values are verbatim spans, and enum values are in their schemas.
- **Synthesis.** Anchors are substrings of their observations.
- **Visibility.** Every closed-vocabulary gold code is model-visible.
- **Patterns.** No author-assigned pattern is shared within a cell.

**Arithmetic.** Every computed gold value introduced in round 3 was re-derived by hand: dates, times,
counts, percentages and capacities.

**Independence.** `INDEPENDENCE_REPORT.json` is valid with 0 findings. The fine and coarse structural checks
find no undeclared same-cell pair, and the 16 planning pairs are declared.

**Deterministic tests.** These are in `tools/g_route3_tests.py`, with results in
`DETERMINISTIC_TEST_RESULTS.json`. They include:

- the round-2 reviewer's own fabricated-Phase-A probe, which is now refused;
- a score and a table edited together and resealed, which is refused;
- a synthetic run relabelled as real in its run manifest, which is refused;
- numbered authorization attempts:
  - an attempt can pause and resume;
  - reuse under another run id or another run root is refused;
  - a later attempt breaks disclosure;
- the real path from Phase A through the table to Phase B, under numbered authorizations;
- the synthetic path refused for an undeclared provider;
- coding host timeouts attributed by a baseline run of the unchanged source;
- the audit bound to its run, and a frozen artifact refused as the audit document;
- the runtime import closure bound to both the freeze and the guard.

**Unchanged and re-confirmed:**

- Routing is gold-blind.
- An unqualified tier is never contacted, and never gives a terminal result.
- `no_qualified_model` makes zero routing calls, and R4 is evidence-only.
- Qualification requires exactly 2 × 2 observations.
- Gate order is `FAILED_INTEGRITY`, then `FAIL`, then `NOT_TESTABLE`, then `PASS`.
- Denominators sum to 48 and 144.

## Residual limitations accepted into the R3 freeze

- **Pilot scale.** 0 failures in 4 bounds the per-cell failure rate only below 0.527.
- **Given classes.** Task and risk classes are given to the router, not inferred.
- **Conversation.** It is a multiple-choice construct. Explanations are not graded, except for action
  claims, so conversation measures choosing the right decision and not over-claiming. It does not measure
  open-ended phrasing.
- **Planning.** It tests exact rule-following on one declared template.
- **Research.** Cells are validated on B against different sub-skills from those qualified on A in the same
  cell.
- **Synthesis.** Anchors are stems, and can pass a restatement that reverses the meaning.
- **Difficulty matching.** It is the author's judgment.
- **Unequal denominators.** B success needs 2 of 2 and A qualification needs 4 of 4. Per-observation rates
  are reported.
- **Local seals carry no secret.** A forger who rewrites every sealed record consistently is stopped only
  procedurally: the Phase A result package is committed to git before Phase B is authorized.
- **Ollama.** It does not attest that generation options or seeds are honored.
- **Earlier experiments.** G-ROUTE1 and G-ROUTE2 keep the derivability and conversation-validator caveats,
  and neither is rescored.

## Verdict

**READY for external round-3 review** of the R3 freeze. Phase A may be authorized only after that review is
clean, and only by the verbatim string `Authorize G-ROUTE3 phase A execution <R3 binding> attempt 1`.
