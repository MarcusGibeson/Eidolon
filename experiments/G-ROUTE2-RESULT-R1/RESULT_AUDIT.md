# G-ROUTE2 Scientific Result Audit

Date: 2026-09-24
Verdict: **CLEAN WITH LIMITATIONS**
Scientific status: **Q1 answered · Q2 FAILED its prospective gates**
Authority: non-authoritative result audit. It alters no record, score or verdict.

Run `groute2_20260924T112152427806Z`, candidate `G-ROUTE2-EXECUTION-R1`, source commit `a7b2012c`,
authorization `Authorize G-ROUTE2 execution 5f869283…` issued verbatim by the operator and matching the
live binding exactly.

## Execution is sound

216 scheduled, 216 persisted, 216 provider contacts, 0 provider failures, 0 duplicates, 0 omissions,
positions contiguous. Every record digest verifies; every schedule binding, request-body digest and raw
envelope matches; requested equals returned model on all 216. Normalization was re-run on every raw
output and reproduced every stored record exactly; semantic values and raw bytes were preserved on all
216. Isolated coding evidence is present on all 36 coding records. The mutation guard agrees before and
after, and no frozen artifact drifted.

Result, manifest, terminal receipt, Activity and checkpoint all read `complete` at 216/217. Resume after
terminal was refused with `terminal_route_run_not_resumable` and zero provider calls. The sealed score
`34f1d859…` was recomputed byte-identically, and the qualification matrix was recounted from raw records
without the scorer under both contracts: 19 normalized, 13 raw — exact.

## Q1 — transport: answered

| | raw contract | normalized contract |
|---|---|---|
| structural validity | 155 | 212 |
| operational acceptance | 109 | 149 |
| semantic correctness | 52 | 65 |
| false-clean | 57 | 84 |
| qualified cells | **13** | **19** |

Scored from the same bytes, so the difference is the transport rule and nothing else. All six gained
cells belong to `qwen3.8:27b`: structured extraction R1, R3, R4 and coding R1, R2, R4. Under the raw
contract the 27B could not qualify for coding at all; under the normalized contract it is the **only**
tier that qualifies for coding, in three of four risk classes. The 7B and 14B gained nothing.

The fence pattern replicated on independent draws: 37 of 60 JSON-profile calls fenced on the 27B, 20 on
the 7B, 0 on the 14B, against G-ROUTE1's 41, 19 and 0. One `invalid_json` and one `wrapper_rejected`
occurred live and failed closed as designed.

The cost of normalization is real and was predicted by the replay diagnostic: it adds 13 correct
answers but 27 false-cleans. Transport tolerance improves measurement of capability and worsens the
gold-blind acceptance signal at the same time.

## Q2 — stopping: failed

| Gate | Frozen bound | Observed |
|---|---|---|
| unsafe early stops, share of stops | ≤ 0.05 | **0.556** |
| useful admission, share of fixture-repeats | ≥ 0.25 | **0.167** |
| unsafe acceptance from normalization | 0 | 0 |
| crashes from model output | 0 | 0 |
| normalization changed semantic values | 0 | 0 |
| qualified cells complete, no vacuous pass | required | held |

27 stops: 12 correct, 15 wrong. All 15 unsafe stops were `qwen3:14b` answers that were structurally
perfect and semantically wrong, in hierarchical synthesis (9), grounded research (3) and reflective
planning (3). They tripped no trigger: the 14B never fences, answered consistently across repeats, and
bound evidence in the expected shape.

**The triggers do not discriminate.** Against bare normalized acceptance on the same responses — a
descriptive comparison, not a gate — the policy cut unsafe stops from 35 to 15 but cut correct stops
from 27 to 12. The unsafe share moved from 56.5% to 55.6%. The triggers escalate right and wrong answers
at nearly the same rate; they reduce the volume of false-clean stops only by stopping less.

`repeat_disagreement`, now functional, fired on 75 records and was the most active trigger after the
structural ones. It measures instability, and the 14B's wrong answers were stable.

## What the evidence points to — diagnostic, not a result

The design reserved a secondary `safe_to_stop_table_bound` check, which also requires the tier to be
qualified for the cell. The frozen scorer does not emit it. Computed afterwards with the frozen
functions and the in-sample table: **15 unsafe stops become 0, and all 12 correct stops remain.**

This is circular. The table was built from these same responses using gold, so it cannot contain the
cells where these responses failed. It is not evidence that the policy works. It does say where to look:
every unsafe stop happened in a task class where no tier qualified. Stop safety in this corpus is a
property of the cell, not of the individual response. Testing that honestly needs a routing table from
an independent run, and the G-ROUTE2 design forbade reusing G-ROUTE1 results under the new contract.
That is a question for a future prospective experiment, not something this run can settle.

## Qualification

19 of 72 cells qualify under the normalized contract. Structured extraction qualifies on every tier at
every risk class. Conversation qualifies at R1 (small, large) and R4 (small, mid). Coding qualifies only
on the 27B at R1, R2 and R4. **No tier qualifies anywhere in grounded research synthesis, hierarchical
semantic synthesis or reflective planning** — the same three task classes G-ROUTE1 found empty.

Routing: `use_small` for conversation R1 and extraction R1–R3; `use_large` for coding R1–R2;
`no_qualified_model` for conversation R2–R3, coding R3, and all of research, synthesis and planning at
R1–R3; R4 evidence-only.

## Invalid run preserved

`groute2_20260924T111500685334Z` ran 6 calls under a binding the operator had not authorized — the
authorization named `051d2b09…`, the run executed `5f869283…` after the harness was added. It is
classified `INVALID / UNAUTHORIZED_EXECUTION_BINDING_MISMATCH`, stopped at a call boundary, terminal,
proven non-resumable, and preserved under `invalid_run_binding_mismatch/`. Its authorization artifact is
marked void. Its records are not scientific observations and are used nowhere in this result.

## Limitations

- **Controlled contrast, not independent replication.** 24 fixtures, one corpus.
- **Q2's failure is prospective and final for this policy.** Thresholds were frozen before contact and
  are not revisited.
- **The table-bound figures are in-sample** and are reported as a pointer, not a finding.
- **Ollama 0.34.3 attests no option or seed honoring.** Timings and token counts are observed.

## Boundaries

Production routing never invoked and not implemented. Automatic escalation disabled. `belief_effects:
none` on every record. G-ROUTE1 untouched. Corpus, gold, thresholds, schedule, scorer, validators,
normalization contract, policy and model bindings unaltered during execution.
