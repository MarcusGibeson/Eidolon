# G-ROUTE4 final results and closure

## Final status

**FAILED.** G-ROUTE4 closed after the preregistered Phase B unsafe-stop ceiling failed. The failure is preserved as
an experimental result, not rewritten as an infrastructure or routing-enforcement failure.

## Bound evidence

- Execution freeze commit: `0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28`
- Phase A run: `groute4a-001-2f9407b8159dc8ac` (`480/480` calls)
- Frozen qualification table: `G-ROUTE4-QUALIFICATION-TABLE`, content digest
  `d91edab014f733c1ef188557268ce1205f82ddd221525285daa01facae02f4b2`
- Phase B run: `groute4b-001-954e9144ee1ce370` (`915/915` calls)
- Phase B score SHA-256: `1cce9a471cb7be727b83225542cbbb3e7bfded2063605f81984741e8c050db96`
- Phase B terminal journal SHA-256: `9396480655b208e4e48a3d3cc1e04f7286aa74f48bd1cc92b421886409c1500a`

The complete artifact lineage and literal hashes are recorded in
`closure/G_ROUTE4_CLOSURE.json`.

## Phase A qualification

Phase A completed cleanly and produced **12 qualified**, **48 not-qualified**, and **0 insufficient** cells. The
qualification table was independently audited, frozen through the governed lifecycle, and reproduced from the
Phase A score without manually added qualifications.

## Phase B integrity and routing

Execution integrity was clean: 915 scheduled calls, 915 persisted calls, no duplicates, omissions, transport
failures, model/config/seed mismatches, or integrity failures. Ten structurally malformed outputs were preserved and
rejected. Independent scorer reconstruction produced zero differences.

The router obeyed the frozen table. There were no unqualified operational uses and no routing-policy violations.
Grounded research remained contained: 54 no-qualified-model outcomes, one R4 evidence-only case, and zero
operational routes.

## Preregistered gates

- Correct-stop floor: **PASS**, 128/154 = 83.1169%; reported 95% bounds 77.3553%-87.8924%.
- Unsafe-stop ceiling: **FAIL**, 20/148 = 13.5135%; reported 95% bounds 9.1388%-19.0280%.

The unsafe-stop ceiling was 1/10 and is not loosened or reinterpreted. Twenty false-clean semantic errors reached
operational stop dispositions. They were concentrated in structured extraction (14), with three in ordinary
conversation, two in reflective planning, and one in hierarchical semantic synthesis.

## Interpretation

The evidence separates four facts that should not be blended together:

1. Experiment execution integrity was clean.
2. Frozen routing-policy enforcement was clean.
3. Phase A qualification and table freezing were mechanically correct.
4. Phase A qualification did not sufficiently predict Phase B safe operational use, especially for structured
   extraction.

The run does not establish a causal mechanism for that predictive-validity failure. It also does not support calling
the outcome a grounded-research routing failure: grounded research was never qualified or operationally routed.

The governed freeze verifier still reports `valid=true` with no reasons. The historical 47-test implementation suite
is not a post-freeze certification suite: its pre-freeze test
`FreezeTests.test_no_freeze_before_the_later_step_4_records` now fails because the authorized execution-freeze file
exists. That stage-limited failure is preserved; neither the test nor the freeze was changed.

The read-only reconstruction of all 20 unsafe stops is in
`closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json`. The smallest evidence-supported next scope is a prospective,
structured-extraction-only requalification study covering fresh date/time, arithmetic, threshold, and full-entity
binding fixtures. No such experiment is designed or authorized by this closure.

Production routing remains disabled. Historical artifacts, the qualification table, corpus, gold, thresholds,
schedules, prompts, and runtime code are unchanged. No provider call or new experiment occurred during closure.
Belief effects remain `none`.
