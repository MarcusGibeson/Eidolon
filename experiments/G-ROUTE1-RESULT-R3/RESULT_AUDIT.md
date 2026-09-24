# G-ROUTE1 R3 Scientific Result Audit

Date: 2026-09-24
Verdict: **CLEAN WITH LIMITATIONS**
Authority: non-authoritative result audit. It alters no record, no score, and no verdict.

Run `groute1_20260924T031646930437Z`, candidate `G-ROUTE1-EXECUTION-R3`, source commit `90ae79ca`,
authorization bound to `9779c29e…d9a5d7b0`.

## Execution is sound

216 scheduled, 216 persisted, 216 provider contacts, 0 provider failures, 0 duplicates, 0 omissions,
positions 1–216 contiguous. Every record digest verifies. Every record's schedule binding — fixture,
task class, risk class, tier, model, repeat, seed, manifest digest, config digest, prompt-template
digest — matches the frozen schedule exactly. Every request-body digest was recomputed from the frozen
corpus and matched. Every raw provider envelope matches its recorded digest and decodes to the stored
envelope. Requested model equals returned model on all 216 calls; no fallback, no alias drift.

The mutation guard `36ced1f0…` agrees before and after, no frozen artifact drifted during execution,
and the source commit is unchanged.

## The completion contract holds

Result, run manifest, terminal receipt, Activity and checkpoint all read `complete`. Completed position
216, next position 217, 216 calls persisted in every view. Resume after terminal was attempted and
rejected with `terminal_route_run_not_resumable` before the provider was callable.

The sealed score record `18c5be66…` was independently recomputed from the raw records and is
byte-identical. The 72-cell qualification matrix was also recounted from the raw records without using
the scorer, and the escalation ladder was re-simulated independently; both reproduce the sealed result
exactly. Arithmetic closes: 112 validator-detected failures + 56 validator-missed = 168 semantic
failures.

## Results as measured

14 of 72 cells qualify, 58 do not, 0 have insufficient evidence. Simulated routing lands on small 30
times, mid 25, large 1, and `no_qualified_model` 16 times across the 72 fixture-repeats.

## Limitation 1 — markdown fences dominate the tier ordering

This is the finding that most affects interpretation, and it is not a capability result.

| Model | Fenced JSON-profile calls | Every fenced payload valid JSON? |
|---|---|---|
| qwen2.5:7b | 19 of 60 | yes |
| qwen3:14b | 0 of 60 | — |
| qwen3.8:27b | 41 of 60 | yes |

All 41 large-tier `malformed_json` rejections are ```json fenced blocks whose contents parse cleanly.
No output was truncated: `done_reason` is `stop` on all 216 calls and no call reached the 350-token cap.

The frozen prompt says to return one compact JSON object and no explanation, so a fenced block is a
contract violation and correctly fails. **The measured result stands and was not rescored.** But the
structural-validity ordering — mid 72/72, small 53/72, large 31/72 — is substantially a formatting
convention difference rather than a difference in reasoning, and must not be read as "the 27B is the
weakest model."

Deciding whether the contract should tolerate a fence is a benchmark design question. It must be
settled deliberately, applied to all three tiers, and re-run — never applied retroactively to this run.

## Limitation 2 — false-clean acceptance is not a safe routing signal

56 of 216 observations were operationally accepted and semantically wrong. 35 of them stopped simulated
escalation at a tier that had answered incorrectly. The gold-blind validator, which is the only signal a
production router could actually use, would have shipped those answers.

Distribution: 21 ordinary conversation, 18 hierarchical semantic synthesis, 11 grounded research
synthesis, 6 reflective planning. By model: 32 qwen3:14b, 15 qwen3.8:27b, 9 qwen2.5:7b. The leading
causes are missing required alternatives (26), conclusion mismatch (18), research judgment mismatch (11)
and missing required text (11).

## Limitation 3 — provider attestation

Ollama 0.34.3 accepts the submitted options and seed but does not attest that any of them were honored
internally. Per-call timings and token counts are observed values, not attested ones.

## Boundaries

Production routing was never invoked and remains disabled. Automatic escalation remains disabled. Every
record carries `belief_effects: none`. The operational validator used no gold on any call, and all 216
records are linked to `G-ROUTE1-GOLD-R1`. Corpus, gold, thresholds, schedule, scorer, validators and
model bindings were not altered during execution.

## One observation worth recording

Schedule position 57, `GROUTE1-RESEARCH-R3-R1-small`, is the call that ended R2. qwen2.5:7b returned the
same malformed shape again — `uncertainties` as a list of objects rather than strings. Under R3 it was
classified `uncertainty_element_type_mismatch`, recorded as false-clean with no infrastructure failure,
and the run continued. The repair was verified against the live failure it was built for, not only
against a test fixture.
