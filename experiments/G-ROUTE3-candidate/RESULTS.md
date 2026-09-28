# G-ROUTE3 results

**Status: CLOSED. PASS WITH LIMITATIONS (pilot-qualified).** Closed by the operator on 2026-09-28. The recorded
result stands as it is. G-ROUTE3 is not extended, rescored or re-read; any follow-up is a new, separately
pre-registered experiment (G-ROUTE4). The table is not authorized for production routing.

Recorded 2026-09-28. Both phases ran under the R7 lifecycle, execution freeze `G-ROUTE3-EXECUTION-R7` (binding
`0bfbe6b1ba92c52f5d45cc0935b3684375ac5c0ab8b929ed85a2ca06e2643465`). They used Ollama 0.34.3 at the fixed loopback
endpoint, with the pinned models qwen2.5:7b (small), qwen3:14b (mid) and qwen3.8:27b (large). Every attempt was
launched by the operator's own verbatim sentence. The results are reported as produced; nothing below changes
the frozen rules.

## Questions

- **Primary:** can a task × risk × model qualification table, derived prospectively from one independent
  qualification corpus, safely guide cheapest-qualified model selection and stopping on a separate, unseen
  validation corpus?
- **Secondary:** when a qualified model's output fails deterministic validation, does escalating to the next
  independently qualified tier improve usable admission without creating unsafe stops?

## Attempts (all disclosed)

| Phase | Attempt | Run | Outcome |
|---|---|---|---|
| A | 1 | `groute3a-001-deb591f4a575779c` | Closed by `operator_interrupt` after 52 of 288 calls, before any scoring. The stated reason was run duration. **Optional stopping cannot be excluded.** Its 52 outputs are byte-identical to attempt 2's at the same positions. |
| A | 2 | `groute3a-002-a90ef4e01edaf413` | Completed: 288/288 calls, 0 transport or infrastructure failures. |
| B | 1 | `groute3b-001-3ade26dbf80c8774` | Completed: 144/144 calls, 0 transport or infrastructure failures. |

## Phase A: qualification (Corpus A)

72 cells (6 task classes × 4 risk classes × 3 tiers, 4 observations each). A cell qualifies only when all 4
observations pass semantically.

| Result | Cells |
|---|---|
| qualified | 30 |
| not qualified | 42 |
| insufficient evidence | 0 |

- **Coding generation/repair:** no qualified cell. Most rejections are calls outside the allowlist that the prompt
  discloses.
- **Grounded research synthesis:** no qualified cell.
- **Qualified cells:**
  - the other four task classes, mostly on the mid and large tiers;
  - small qualifies in structured extraction and ordinary conversation (R1, R3, R4).
- **Mid tier on reflective planning:** false-clean in all 16 observations.

The full cells are in `PHASE_A_SCORE_ATTEMPT2.json`.

- **Independent audit:** READY (`PHASE_A_AUDIT_ATTEMPT2.md`). All 72 cells were reproduced byte for byte.
- **Frozen qualification table:** `QUALIFICATION_TABLE.json`, sha256
  `adc5411f1300c8e3dd5e3f2349699c2e9755d73f89fa0e0870d1d70d9f6bf0ab`.

## Phase B: validation (Corpus B, unseen)

48 cases.
- **Routing:** gold-blind, on the frozen table.
- **Calls:** all 144 schedule calls were made, as the protocol specifies. 23 of them are routing calls (22
  first-tier and 1 escalation); the other 121 are diagnostic.
- **Full report:** `PHASE_B_SCORE_ATTEMPT1.json`.
- **Independent audit:** READY (`PHASE_B_AUDIT_ATTEMPT1.md`). The whole report and all 48 decisions were reproduced.

**Primary: PASS** under the pre-registered gates, which are evaluated on observed rates:

| Gate | Threshold | Observed | Uncertainty (from the audit) |
|---|---|---|---|
| Correct stops among qualified-start cases | ≥ 0.60 | 20 / 22 = 0.909 | one-sided 95% lower bound 0.74; robust |
| Unsafe stops among stops | ≤ 0.10 | 2 / 22 = 0.091 | one-sided 95% upper bound 0.259; **passed by less than one case** |
| Terminal results from an unqualified tier | 0 | 0 | — |
| Denominator integrity | required | yes | — |

**Secondary: NOT_TESTABLE.** There was 1 escalated stop (B-EXTRACT-R2-2: small was rejected for a missing field,
and mid was correct), but at least 5 are required for evaluation. No claim is made.

**Where the cases ended:**

| Final outcome | Cases |
|---|---|
| no qualified model | 14 |
| evidence only (R4, never routed) | 12 |
| stopped on mid | 9 |
| stopped on small | 7 |
| stopped on large | 6 |

**Both unsafe stops** were ordinary conversation on the small tier, which the table had qualified after 4/4 in Phase A:
- **B-CONV-R1-1:** the model answered P3; gold is P1.
- **B-CONV-R3-2:** the model answered "passed"; gold is the partial audit-database failure.

These were also the only non-correct qualified-start cases. The other 18 stops (synthesis, planning, extraction)
had none.

**Generalization.** Phase A qualification agreed with Phase B cell-level outcomes as follows:

| Tier | Agreement |
|---|---|
| small | 75% |
| mid | 88% |
| large | 75% |

9 of the 30 qualified cells failed on Corpus B at cell level, 4 of them R4, which is never routed.

## What this supports, and what it does not

- The pre-registered primary criterion was met on this corpus, with these models, at pilot scale. The correct-stop
  gate passed with a wide margin.
- The unsafe-stop gate was met on its observed rate only. A third unsafe stop would have failed it, and the data
  are compatible with a true unsafe rate well above 0.10 (upper bound 0.26). This is not evidence that the true
  rate is at most 0.10. The pre-registered rationale asked for more than one case of margin, and this result has
  less.
- Unsafe stops concentrated in ordinary conversation on the cheapest tier.
- Coding and grounded research had no qualified cells, so the table's behaviour there is untested beyond
  "no qualified model".
- The escalation question remains open.
- Phase A attempt 1 was stopped by the operator. Its outputs match attempt 2's, but optional stopping cannot be
  excluded, and it is disclosed.

## Closure and carried-forward findings

G-ROUTE3 is closed as **PASS WITH LIMITATIONS (pilot-qualified)**:
- It gives meaningful prospective evidence that qualification-based routing works at pilot scale.
- It is not sufficient evidence for production deployment.

Where the table has no qualified model (coding, grounded research), the correct behaviour is that it authorizes
nothing.

Carried forward to G-ROUTE4, as a new experiment:
1. **Unsafe-stop confidence.** Showing a true unsafe rate of at most 0.10 with one-sided 95% confidence needs a
   pre-sized number of stops, fixed in advance:

   | Unsafe stops observed | Stops needed |
   |---|---|
   | 0 | 29 |
   | 1 | 46 |
   | 2 | 61 |
   | 3 | 76 |

   G-ROUTE3 had 22.
2. **Conversation on the small tier.** Both unsafe stops were here, so it is the first validation target.
3. **Escalation.** It remains untested (1 escalated stop out of the 5 required). It needs a pre-registered corpus
   that produces escalations without selecting cases by expected failure.
4. **Coding.** The audit found most rejected coding answers used calls outside the allowlist the prompt
   discloses, which excludes built-ins such as `len`. "No qualified coding model" may partly measure that
   allowlist. Diagnosing it, and any allowlist change, is a protocol change and belongs to G-ROUTE4.
5. **Grounded research.** It fails mainly by false-clean: answers that pass the operational checks but are
   semantically wrong. The diagnosis concerns grounding as well as capability.

## Not done

No production routing was applied (`production_routing_invoked: false`) and no belief effects (`belief_effects:
none`). The evidence repository in the data root holds every journal, ledger entry, the table and both audit copies.
