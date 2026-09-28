# G-ROUTE4: qualification routing under a stricter, pre-registered policy (design candidate)

Status: **design candidate, revision 2.**
- Nothing is frozen. No model has been contacted for G-ROUTE4, and no corpus or gold exists yet.
- Production routing stays disabled whatever the result. Belief effects are `none`.
- Revision 1 received design review round 1:
  - Reviewer A: 2 BLOCKING, 10 MUST-FIX.
  - Reviewer B: 1 BLOCKING, 10 MUST-FIX.
  - Each finding and how this revision answers it is in `DESIGN_REVIEW_ROUND1.md`.

**The process, before anything runs:**
1. This design is accepted by fresh reviewers under the safety-gated rule.
2. An authoring blueprint is frozen.
3. The corpora are authored, and their gold is independently adjudicated.
4. Implementation, then an implementation review and certification.
5. An execution freeze.
6. The operator's verbatim sentence for each phase, with an independent audit after each phase.

## Origin, and what this experiment is

G-ROUTE3 closed as **PASS WITH LIMITATIONS (pilot-qualified)** (`experiments/G-ROUTE3-candidate/RESULTS.md`).
Its targets carried forward are:
- unsafe-stop confidence;
- conversation on the small tier;
- escalation;
- grounded research.

They were chosen **from G-ROUTE3's results**, so they generate hypotheses and are declared as such.

**G-ROUTE4 tests G-ROUTE4's own routing policy.** That policy differs from G-ROUTE3's in four ways:
- 8/8 qualification;
- independently adjudicated gold;
- the D8 research prompt sentence;
- no coding class.

It is **not** a replication of G-ROUTE3, and its evidence is **never pooled or combined** with G-ROUTE3's.

G-ROUTE3 is closed:
- it is never rescored, extended or re-read;
- its corpora are never G-ROUTE4 validation data;
- every G-ROUTE3 and G-ROUTE1 file stays byte-identical.

## Scope

**Task classes:** ordinary conversation, structured extraction, hierarchical semantic synthesis, reflective
planning, grounded research synthesis. Risk classes R1–R4. R4 stays evidence-only.

**Coding is deferred (revised D6).** The review established two facts:
- The coding runner (`run_isolated_fixture`) is not a sandbox. It runs model-written code as the user, with no
  filesystem or network restriction.
- The AST gate is the real barrier, and it can be bypassed: by rebinding a name (`bool = eval`), a parameter
  default, a decorator, or an import alias.

A read-only scan of all 85 G-ROUTE3 coding outputs found none of these constructs. The only import was the
permitted `pathlib`, so the weakness was never used. Widening the allowlist would raise the risk, so coding moves
to its own later experiment. That experiment needs:
- a real sandbox: a restricted token, no network, no filesystem access outside a scratch folder;
- a hardened AST gate that is the primary control, with an exhaustive ruling table and a certification probe per
  bypass.

The G-ROUTE3 diagnostic (28 of 72 coding outputs denied for pure built-ins such as `len`) is carried to that
experiment.

## Questions

**P1: routing safety, confirmatory for this policy.** On the frozen validation corpus, is the true unsafe-stop rate at
most 0.10, and the true correct-stop rate of qualified-start cases at least 0.60? Each is judged at one-sided 95%
confidence, with an exact binomial (Clopper-Pearson) bound.

**P2: conversation on the cheapest tier.** Descriptive (D2): the conversation stratum's unsafe-stop rate and bound,
with the small tier broken out.

**S1: escalation.** Pilot, descriptive only (see Gates).

**S3: grounded research.** Can a tier qualify for research on fresh, adjudicated fixtures, and is its failure
judgment or bookkeeping?

## Diagnostics carried in from G-ROUTE3 (exploratory, read-only; they motivate, never decide)

- **Grounded research:** `RESEARCH_DIAGNOSIS.md`. G-ROUTE3's 41 research mismatches cluster into four patterns:
  - uncertainty-code bookkeeping (involved in 32; `single_lineage_support` differs in 30);
  - about-ness and scope (11);
  - conflict and governing-source rules (11);
  - output element shape (4 primary, 18 involved).

  The large tier never misjudged a claim's status or about-ness.
- **Conversation:** in some fixtures all tiers converged on the same non-gold option. That is the reason for
  independent gold adjudication.
- **Coding:** carried to the deferred coding experiment.

## Identity and separation (all new; nothing edited in place)

- **Code:**
  - G-ROUTE4 runs from new modules (`tools/g_route4_*`). They carry R7's lifecycle design unchanged in structure
    (journal and replay over a fixed schedule), with every identity constant parameterized.
  - G-ROUTE3's modules, G-ROUTE1's modules and every G-ROUTE3 file stay **byte-identical**, so G-ROUTE3's drift
    checks and reproducibility are untouched.
  - The research validator is imported unchanged, with no contract change.
- **Identity constants, all distinct from G-ROUTE3's:**

  | Constant | G-ROUTE4 value |
  |---|---|
  | experiment name (checked when a data root is opened) | `G-ROUTE4` |
  | data root | `C:\Users\marcu\AppData\Local\Eidolon\research\g_route4` |
  | genesis string | `g-route4-ledger` |
  | lease tag, evidence identity, run-id prefixes | `groute4a-`, `groute4b-` |
  | seed ranges | 47001–47999 (A′), 48001–48999 (B′) |
  | table path on `main` | `experiments/G-ROUTE4-candidate/QUALIFICATION_TABLE.json` |

  The rest of the constants are as listed:
  - guarded paths and frozen artifacts pointing at `experiments/G-ROUTE4-candidate/`;
  - expected call counts, fixtures per cell, repeats, thresholds and bound texts.
- **Sentences:** every command has a `G-ROUTE4` sentence: launch A′ and B′, the distinct launch after an integrity
  failure, resume, abandon, declare, clear orphan, and freeze table. A G-ROUTE3 sentence, ledger or binding can
  never authorize anything in G-ROUTE4, and G-ROUTE4's never authorize anything in G-ROUTE3.
- **Data roots:** each experiment's freeze writer and lifecycle refuse the other's data root.

## Schedule (fixed before any contact)

Both phases use a **fixed, fully enumerated schedule** frozen before contact:
- every position has its call id, seed and request digest;
- positions are identical across attempts.

Phase B′ calls **all three tiers on every case** (revised D1). Routing is computed afterwards, gold-blind, from the
sealed records by the frozen router, exactly as in G-ROUTE3. So R7's guarantees apply unchanged: no position is
sent twice, replay is deterministic, attempts are protected, and denominators are defined. The all-tier design
restores the generalization table, false-negative qualification, and "false-clean caught because the tier is
unqualified".

**Phase A′ (qualification):** 5 classes × R1–R4 × 4 fixtures = **80 fixtures**, × 3 tiers × 2 repeats = **480 calls**.

**Phase B′ (validation), exact composition (D9):**

| Stratum | Cases per cell | Cells | Cases |
|---|---|---|---|
| Ordinary conversation, R1–R3 | 28 | 3 | 84 |
| Extraction, synthesis, planning, research, R1–R3 | 18 | 12 | 216 |
| **Eligible total** | | | **300** |
| R4, one per class (evidence-only, never routed) | 1 | 5 | 5 |
| **B′ fixtures** | | | **305**, × 3 tiers = **915 calls** |

- **The P1 estimand** is the rate over this pre-registered mix.
- **Conversation is oversampled.** That is conservative for P1, because G-ROUTE3's unsafe stops were in
  conversation. An equal-weight-by-task-class rate is reported descriptively.
- **B′ is never resized,** topped up, extended or pooled, after A′ or after B′. NOT_TESTABLE is a final outcome.

## Corpora

**Derivability, extended to output shape (D8 as a criterion).**
- G-ROUTE3's derivability rule is kept: every closed label is offered as an allowed set, every enforced ordering is
  stated, and every constraint is disclosed.
- It is extended to **every output shape a validator enforces, in all five profiles**: container types, element
  types and key sets.
- A disclosure audit of each profile's prompt against its validator is frozen with the corpora.

**Research prompt (D8), verbatim.**
- The research prompt is the G-ROUTE3 research rule body, byte-identical; only the subject phrase varies.
- After the sentence "Each claim object has exactly the keys claim_id, status, citations and lineages.", this
  sentence is inserted:

  > "The reply's claims is a list of claim objects; in each claim object, citations is a list of source_id strings
  > and lineages is a list of lineage-name strings; uncertainties is a list of code strings."

- A freeze-time test checks the identity and the insertion.
- The research validator is unchanged, with exact matching. Every judgment rule is unchanged.

**Authoring blueprint, frozen before authoring.**
- It fixes a per-cell feature allocation for every class.
- For research:
  - the eight G-ROUTE3 construct patterns (S1–S8) are allocated identically in A′ and B′, balanced across R1–R4;
  - whether `single_lineage_support` holds is balanced at 50/50 within every cell.
- The allocation is derived from the construct, not from G-ROUTE3's failure rates.
- Research qualification is declared conditional on that mix. S3's construct is declared not comparable with
  G-ROUTE3's.

**Authoring rules:**
- no fixture is pretested on any model;
- no A′ or B′ item is derived from a G-ROUTE3 item whose model outputs were inspected;
- G-ROUTE3's corpora serve only as development material for validators and templates.

**Contamination and independence.** `CONTAMINATION_ANALYSIS.md` and `INDEPENDENCE_REPORT.json` cover A′↔B′ and
A′/B′↔G-ROUTE3 A/B. They cover G-ROUTE3's already-seen Corpus B in particular.
- **Template cap:** no template family exceeds 25% of a class's B′ cases.
- **Reporting:** per-template and per-cell breakdowns are reported. A cluster-level sensitivity bound, taking
  fixture families as the unit, is reported without gating.
- The P1 bounds are declared **conditional on fixtures being exchangeable within the frozen mix**.

**Independent gold adjudication (A′ and B′ alike).**
- **Adjudicator:** a fresh Claude session, never a pinned model and never Ollama. The model id and version, and the
  adjudication prompt, are frozen and recorded.
  - It sees only the model-facing fixture.
  - It is blind to gold, the authoring rationale, G-ROUTE3 outputs and the diagnosis.
  - Its answers are **sealed by a committed digest before gold is revealed**.
- **Disagreements** go to a second, independent adjudicator session. Anything still unresolved goes to the
  operator, who applies the derivability rule. The author never decides a disagreement.
- **Fix, keep or drop:**
  - a fixture is **fixed** only when gold is wrong or the input is ambiguous, with the defect documented;
  - if the adjudicator erred and gold is confirmed, the fixture is **kept unchanged**;
  - a fixture is never dropped for being hard;
  - a fixture that cannot be fixed is replaced from a **pre-authored reserve, in a fixed order**, and the
    replacement is adjudicated from scratch;
  - there are at most 2 replacement rounds per slot.
- **Records:** per-cell fix and drop counts and the adjudicator disagreement rate are disclosed. The records are
  bound in the execution freeze.

## Qualification (Phase A′)

- **8/8 unanimity (D4):** 4 fixtures × 2 repeats.
- **Declared:** this is materially stricter than G-ROUTE3's 4/4. At a per-observation pass probability of 0.9,
  the chance to qualify falls from 0.656 to 0.430; at 0.95, from 0.815 to 0.663.
- **Every cell reports two bounds:**
  - the observation-level bound (0 failures in 8 gives 0.312);
  - the fixture-level bound (0 failures in 4 fixtures gives 0.527).
- Repeats of one fixture are correlated, so the fixture-level bound is the honest one for new fixtures.
- G-ROUTE3's rationale for the 0.60 correct-stop threshold ("four out of four") is restated for 8/8.
- Everything else in G-ROUTE3's qualification contract is carried over: no infrastructure failures, no
  returned-model mismatches, the exact design, and a READY audit.

## Gates (frozen before contact)

All bounds are exact one-sided Clopper-Pearson bounds at α = 0.05, computed exactly: "upper bound ≤ 0.10" means
P(X ≤ k | n, 0.10) ≤ 0.05. FAIL means "not shown"; for the unsafe gate, not shown to be at most 0.10.

**Unsafe-stop gate.** n is the number of stops. Coding is out of scope, so every stop can be unsafe.

| Outcome | Condition |
|---|---|
| PASS | n ≥ 76 and the upper bound ≤ 0.10 |
| FAIL | n ≥ 76 and the upper bound > 0.10; **or** n ≥ 10 and the observed rate > 0.10 (G-ROUTE3's failure standard kept); **or** the lower bound > 0.10 at any n |
| NOT_TESTABLE | otherwise |

**Correct-stop gate.** n is the number of qualified-start cases.

| Outcome | Condition |
|---|---|
| PASS | n ≥ 30 and the lower bound ≥ 0.60 |
| FAIL | n ≥ 30 and the lower bound < 0.60; **or** n ≥ 10 and the observed rate < 0.60; **or** the upper bound < 0.60 at any n |
| NOT_TESTABLE | otherwise |

**Primary status**, in G-ROUTE3's order:
1. FAILED_INTEGRITY if integrity fails. Integrity means: 915 recorded B′ calls, 300 eligible and 5 R4 cases
   decided, 0 unqualified-tier terminal results, 0 gold-leakage events.
2. FAIL if any gate fails.
3. NOT_TESTABLE if any gate is not testable.
4. PASS.

The two gates form an intersection-union test, so no multiplicity adjustment is needed.

**Power (declared).** The table gives P(PASS) for the unsafe gate by true unsafe rate. Each range spans stop rates
of 0.40–0.73 per eligible case, which is 120–219 stops at 300 cases:

| True unsafe rate | P(PASS) |
|---|---|
| 0.02 | 0.99–1.00 |
| 0.03 | 0.93–1.00 |
| 0.05 | 0.61–0.86 |
| 0.07 | 0.26–0.43 |

At G-ROUTE3's point estimate (0.09), P1 is unlikely to pass, and that outcome is reported as it is.

**P2 (descriptive):**
- The conversation-stratum unsafe-stop count, n and upper bound are reported whenever there is at least one stop,
  with the small tier broken out.
- If the small tier does not qualify for conversation under 8/8, P2 reports "no small-tier conversation stops: not
  observable". That is a declared possible outcome.

**S1 (pilot, descriptive):**
- It reports escalations, escalated stops, and the correct and unsafe counts among them, with bounds.
- It reaches **no PASS/FAIL verdict**.
- The predictive probability of at least 5 escalated stops is about 0.6–0.8. It rests on G-ROUTE3's single observed
  escalation.

**Research, descriptive, defined in frozen code:**
- claim-level agreement: the share of claims whose status, citations and lineages all equal gold;
- uncertainty-code agreement: exact set equality;
- element-shape failures: a count.

## Phase B′ preconditions (R7 §10, adapted)

- A′ is complete and committed, and it is the only completed A′ attempt.
- The READY A′ audit exists, and the table has been frozen by the G-ROUTE4 freeze-table sentence.
- The table is on `main` at the G-ROUTE4 path, byte-identical, with one version.
- Every table cell has the 8-observation shape.
- The freeze, the endpoint and the model receipts are verified. Ollama is at the pinned version, re-checked before
  every launch.

## Order of work and authorization

1. **Design review.** This revision goes to fresh reviewers, with further rounds until accepted.
2. **Authoring blueprint** frozen.
3. **Corpora:**
   - A′ (80 fixtures), B′ (305) and reserves authored;
   - the derivability and shape-disclosure audit;
   - blind adjudication;
   - the contamination and independence reports;
   - an external review of the corpora.
4. **Implementation** in new `g_route4_*` modules, then:
   - an implementation review;
   - the full certification campaign;
   - a differential against G-ROUTE3's R7 on synthetic data (identity aside).
5. **Execution freeze** (G-ROUTE4 binding).
6. **Phase A′.** Operator sentence, then the independent A′ audit, then the freeze-table sentence, then the table on
   `main`.
7. **Phase B′.** Operator sentence, then the independent B′ audit, then the results record.

**Runbook:** reserve uninterrupted windows of about 3.2 hours for A′ and about 6 hours for B′. Stopping closes the
attempt. Check the Ollama version before each launch.

## Operator decisions

| # | Decision | Chosen |
|---|---|---|
| D1 | Phase B′ calls | **All three tiers** (revised 2026-09-28 after design review round 1; router-only would need a lifecycle redesign) |
| D2 | P2 conversation stratum | **Reported with its bound**, not gating |
| D3 | Escalation | **Pilot, descriptive only** (revised: B′ is sized by P1 power, D9) |
| D4 | Qualification scale | **8 observations per cell** (4 fixtures × 2 repeats), with both bounds reported |
| D5 | R4 in Phase B′ | **One per class** (5), evidence-only |
| D6 | Coding | **Deferred to its own experiment** with a real sandbox and a hardened gate (revised after design review round 1) |
| D7 | Grounded research | **Diagnose, then include.** The diagnosis is done; the validator is unchanged |
| D8 | Research output element types | **The verbatim sentence above**, plus a shape-disclosure audit of all profiles |
| D9 | Phase B′ size | **300 eligible cases** (84 conversation, 216 other) plus 5 R4 cases: 915 calls |

## Standing constraints (unchanged)

- Eidolon is not made autonomous.
- Nothing about the corpus, gold, validators, scorer, thresholds, schedule, qualification policy, escalation
  policy or model bindings changes after provider contact.
- Failed gates are never reinterpreted, and criteria are never loosened.
- Model answers are never repaired with extra calls.
- No production routing or belief effects.
- Invalid and failed results are preserved honestly.
- One local-model research job runs at a time.
- A protected dependency that is wrong at preflight stops the run.
- Authorization binds the exact digest; every phase needs the operator's verbatim sentence.
