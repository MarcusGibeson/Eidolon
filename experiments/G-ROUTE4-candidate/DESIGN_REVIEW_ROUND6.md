# G-ROUTE4 design review, round 6 (final)

Date: 2026-09-29.
Reviewed: `DESIGN_CANDIDATE.md` revision 6 (commit `05cf92e`).
Outcome: **accepted** under the operator's decision D11.

**D11** (2026-09-29): one final round on revision 6. If neither reviewer finds anything BLOCKING, the design is
accepted under the safety-gated rule. Any remaining MUST-FIX items become written obligations, verified at the corpus
review and the implementation review, as with R7.

| Reviewer | Focus | Verdict |
|---|---|---|
| A | Scientific and statistical design | **0 BLOCKING**, 6 MUST-FIX, 9 notes |
| B | Protocol, R7 reuse, implementability | **0 BLOCKING**, 3 MUST-FIX, 6 notes |

Both reviews were read-only, with no provider contact.
- The automatic safety check was unavailable while Reviewer B ran. The operator's assistant verified afterwards that
  nothing changed:
  - no `g_route4_*` code exists;
  - no G-ROUTE4 data root exists;
  - the G-ROUTE4 folder held only design documents;
  - `git status` was clean at `05cf92e`, in sync with `origin/main`.

## Why nothing is BLOCKING (both reviewers)

| Class | Reviewers' reasoning |
|---|---|
| **No position sent twice** | A fixed, fully enumerated all-tier schedule with seeds identical across attempts. R7's journal and replay guarantees are carried; only the coding kinds are removed, as integrity failures. |
| **No best-of-N or optional stopping** | No pinned model runs before the freeze. B′ is never resized, and NOT_TESTABLE is final. R7's attempt rules and freeze-writer refusals are carried. Adjudication selects only on the outcomes of Claude adjudicators and the operator, and that filter is declared. |
| **No contact without the verbatim sentence** | Every template is G-ROUTE4-specific. Bindings must equal the freeze in force, and resume needs the exact consumed sentence. G-ROUTE3 and G-ROUTE4 authorizations, ledgers, data roots and bindings cannot cross. |
| **No gate passes without evidence or hides a failure** | PASS needs n ≥ 76 and an exact upper bound ≤ 0.10, or n ≥ 30 and a lower bound ≥ 0.60. G-ROUTE3's observed-rate FAIL at n ≥ 10 is kept. The precedence matches G-ROUTE3. Every loosening is declared, and the validators, semantics and routing are unchanged. |
| **No contradiction with D1–D11 or the standing constraints** | Confirmed by both reviewers. |

**Numbers.** Every number was re-verified with exact arithmetic:
- the floors of 76 and 30/23;
- the power table (minimum at n = 128, maximum at n = 215) and a size of at most 0.05;
- the qualification figures and bounds;
- the E1 figure;
- the seeds, composition, allocation and caps;
- 38 sampled fixtures and 160 extra A′ sessions;
- the D8 sentence digest.

## Round-5 findings: confirmation

| Reviewer | Round-5 item | Final-round status |
|---|---|---|
| A | M1 same-family gate | CONFIRMED |
| A | M2 pool and exemption lists | PARTIAL → O3, O6 |
| A | M3 identical gold | CONFIRMED (canonical form → N1) |
| A | M4 audit sample | PARTIAL → O1 |
| A | M5 answer positions | CONFIRMED |
| B | M1 grading-differential entry points | CONFIRMED |
| B | M2 git ids inside blobs | CONFIRMED |
| B | M3 allowlist | CONFIRMED (→ N9) |
| B | threshold keys | PARTIAL → O8 |

## Final-round MUST-FIX items, carried as obligations

| Finding | Obligation |
|---|---|
| A MF1 / B MF3: the audit-sample seed contradicted the seal-derived sample; a seal could be re-made | O1 |
| A MF2: adjudicator configuration recorded but not frozen; no-re-run rule | O2 |
| A MF3: entity comparison narrowed to within a class | O3 |
| A MF4: the conversation fine-signature check is vacuous | O4 |
| A MF5: template trigrams could become boilerplate | O5 |
| A MF6: the supplementary exact comparison was unspecified | O6 |
| B MF1: the lifecycle differential's Phase B calls are module-bound | O7 |
| B MF2: the thresholds key list was incomplete | O8 |
| B note N2: sentence meanings | O9 |

Notes from both reviewers are tracked as N1–N10 in `G-ROUTE4_OBLIGATIONS.md`.

## Design review history

| Round | Revision | A | B |
|---|---|---|---|
| 1 | 1 | 2 BLOCKING, 10 MUST-FIX | 1 BLOCKING, 10 MUST-FIX |
| 2 | 2 | 0, 6 | 0, 11 |
| 3 | 3 | 0, 6 | 0, 9 |
| 4 | 4 | 0, 4 | 0, 4 |
| 5 | 5 | 0, 5 | 0, 3 |
| 6 (final) | 6 | 0, 6 | 0, 3 |

**Accepted.** Next, per `G-ROUTE4_OBLIGATIONS.md`: the authoring blueprint, then the seal commit, then the audit
sample, then the first adjudication batch. Nothing runs before the operator starts it.
