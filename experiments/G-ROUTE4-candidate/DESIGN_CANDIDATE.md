# G-ROUTE4: qualification routing under a stricter, pre-registered policy (design candidate)

Status: **design candidate, revision 3.**
- Nothing is frozen. No model has been contacted for G-ROUTE4, and no corpus or gold exists yet.
- Production routing stays disabled whatever the result. Belief effects are `none`.
- Review so far:

  | Round | Reviewed | Reviewer A | Reviewer B | Record |
  |---|---|---|---|---|
  | 1 | revision 1 | 2 BLOCKING, 10 MUST-FIX | 1 BLOCKING, 10 MUST-FIX | `DESIGN_REVIEW_ROUND1.md` |
  | 2 | revision 2 | 0 BLOCKING, 6 MUST-FIX | 0 BLOCKING, 11 MUST-FIX | `DESIGN_REVIEW_ROUND2.md` |

  This revision answers every round-2 finding.

**Before anything runs:**
1. Design acceptance.
2. The authoring blueprint.
3. Corpora with adjudicated gold.
4. Implementation, an implementation review and certification.
5. An execution freeze.
6. The operator's verbatim sentence for each phase, with an independent audit after each phase.

## Origin, and what this experiment is

G-ROUTE3 closed as **PASS WITH LIMITATIONS (pilot-qualified)** (`experiments/G-ROUTE3-candidate/RESULTS.md`).
Its carried-forward targets are:
- unsafe-stop confidence;
- conversation on the small tier;
- escalation;
- grounded research.

They were chosen **from G-ROUTE3's results**, so they generate hypotheses and are declared as such.

**G-ROUTE4 tests G-ROUTE4's own routing policy.** That policy differs from G-ROUTE3's in five ways:
- 8/8 qualification;
- independently adjudicated gold;
- output shapes disclosed in full (D8);
- no coding class;
- fresh template families.

G-ROUTE4 is **not** a replication of G-ROUTE3, and its evidence is **never pooled or combined** with G-ROUTE3's.

G-ROUTE3 is closed: it is **never rescored or reinterpreted**. G-ROUTE3's files may be read, for the contamination
analysis, the prompt identity test and the differential. Its corpora are never G-ROUTE4 validation data, and every
G-ROUTE3 and G-ROUTE1 file stays byte-identical.

## Scope

**Task classes:** ordinary conversation, structured extraction, hierarchical semantic synthesis, reflective
planning, grounded research synthesis. Risk classes R1–R4. R4 stays evidence-only.

**Models and generation, carried unchanged:**
- **Models:** qwen2.5:7b (small), qwen3:14b (mid) and qwen3.8:27b (large), with the manifest and blob digests of
  `experiments/G-ROUTE3-candidate/model_bindings.json`. A byte-identical copy becomes G-ROUTE4's guarded bindings.
- **Provider:** Ollama 0.34.3, recorded in the freeze and checked before every launch.
- **Generation:** the G-ROUTE3 generation configuration (including `num_predict` 350).
- **Contracts:** the conversation frame v3, operational validator v2, semantics v1 and triggers v1.

**Coding is deferred (D6).**
- The coding runner is not a sandbox, and its AST gate can be bypassed.
- The finding and a clean scan of G-ROUTE3's 85 coding outputs are recorded in `DESIGN_REVIEW_ROUND1.md`.
- Coding moves to its own later experiment, with a real sandbox and a hardened AST gate as the primary control.

## Questions

**P1: routing safety for this policy.** On the frozen validation corpus, given the A′ table that is actually
produced:
- is the true unsafe-stop rate at most 0.10?
- is the true correct-stop rate of qualified-start cases at least 0.60?

Each is judged at one-sided 95% confidence with exact binomial bounds, under the evaluability floors of the Gates
section.

**P2: conversation on the cheapest tier.** Descriptive (D2).

**E1: escalation.** Pilot, descriptive only. (Renamed from S1 to avoid a clash with the research pattern names.)

**R1: grounded research.** Can a tier qualify for research on fresh, adjudicated fixtures, and is its failure judgment
or bookkeeping?

## Diagnostics carried in from G-ROUTE3 (exploratory, read-only; they motivate, never decide)

- **Grounded research:** `RESEARCH_DIAGNOSIS.md`. G-ROUTE3's 41 research mismatches cluster into four patterns:
  - uncertainty-code bookkeeping (involved in 32);
  - about-ness and scope (11);
  - conflict and governing-source rules (11);
  - output element shape (4 primary, 18 involved).

  The large tier never misjudged about-ness. Its only wrong claim statuses were two cases where it read a governing
  source's denial as support.
- **Conversation:** in some fixtures all tiers converged on the same non-gold option. That is the reason for gold
  adjudication.
- **Coding:** carried to the deferred coding experiment.

## Identity and separation

**Modules: imported or forked.**

| Imported unchanged (byte-identical, guarded) | Forked into new `g_route4_*` modules (identity parameterized) |
|---|---|
| `g_route1_validators`, `g_route1_operational`, `g_route1_contract`, `g_route1_provider`, `g_route2_normalization`, `g_route3_conversation`, `g_route3_semantics`, `g_route3_operational`, `g_route3_triggers`, `g_route3_routing`; `experiments/G-ROUTE1-candidate/prompt_profiles.json` | `contract`, `qualification`, `validation`, `scorer`, `runner` (the collection path only), `lifecycle`, `journal`, `evidence`, `launch`, `freeze`, `campaign`, `tests` |

- `g_route3_platform` and `g_route3_fs` are imported unchanged if a grep confirms they carry no identity literal.
  Otherwise they are forked.
- **Forked grading or routing code carries a proof of equality.** A differential on shared synthetic records shows
  that its outputs equal G-ROUTE3's, wherever the rules coincide.
- **No G-ROUTE4 process loads `g_route1_coding_runner` or `g_route3_worker`.** This is checked through the digests
  of every loaded module.
- **The guarded list** is every imported module, every `g_route4_*` module, the G-ROUTE1 prompt profiles, and
  G-ROUTE4's corpora, gold, schedules, thresholds, bindings and freeze.

**Identity constants.** Each G-ROUTE3 value on the left is replaced by the G-ROUTE4 value on the right. A test
greps every `g_route4_*` module and fails on any `G-ROUTE3`, `GROUTE3`, `g-route3`, `groute3` or `g_route3_`
identity literal. The only exception is the import statements of the modules listed as imported unchanged.

| Constant | G-ROUTE3 | G-ROUTE4 |
|---|---|---|
| experiment name in `root.json` (checked on open) | `G-ROUTE3` | `G-ROUTE4` |
| data root | `…\research\g_route3` | `C:\Users\marcu\AppData\Local\Eidolon\research\g_route4` |
| ledger genesis | `g-route3-ledger` | `g-route4-ledger` |
| lease holder tag | `g-route3-r7` | `g-route4-r7` |
| pinned thread name | `g-route3-pinned` | `g-route4-pinned` |
| evidence author and committer | `G-ROUTE3 evidence <g-route3-evidence@localhost>` | `G-ROUTE4 evidence <g-route4-evidence@localhost>` |
| evidence index file, root commit message | `g-route3-index`, `G-ROUTE3 evidence root` | `g-route4-index`, `G-ROUTE4 evidence root` |
| run-id prefixes | `groute3a-`, `groute3b-` | `groute4a-`, `groute4b-` |
| call-id prefix | `GROUTE3-` | `GROUTE4-` |
| fixture-id namespace | `A-…`, `B-…` | `A4-…`, `B4-…` |
| corpus, gold, schedule, table ids | `G-ROUTE3-CORPUS-X`, `-GOLD-X`, `-SCHEDULE-X`, `G-ROUTE3-QUALIFICATION-TABLE` | the same pattern with `G-ROUTE4` |
| schedule salts | `G-ROUTE3-A`, `G-ROUTE3-B` | `G-ROUTE4-A`, `G-ROUTE4-B` |
| contract and schema versions | `g-route3.*` | `g-route4.*` (every one renamed) |
| freeze candidate id; superseded list | `G-ROUTE3-EXECUTION-R7`; R1–R6 | `G-ROUTE4-EXECUTION-R1`; empty |
| threshold id | `G-ROUTE3-THRESHOLDS-R6` | `G-ROUTE4-THRESHOLDS-R1` |
| artifact folder; table path on `main` | `experiments/G-ROUTE3-candidate/…` | `experiments/G-ROUTE4-candidate/…`; `…/G-ROUTE4-candidate/QUALIFICATION_TABLE.json` |

**Seeds.**
- **Formula:** seed = base + fixture_index × 10 + repeat, where the fixture index is the zero-based position in
  the corpus.
- **Bases and ranges:**

  | Phase | Base | Range |
  |---|---|---|
  | A′ | 470000 | 470000–470791 |
  | B′ | 480000 | 480000–483040 |

  Both are disjoint from G-ROUTE3's 43001–44471.
- **Tiers:** all three tiers share the seed of a fixture × repeat group, as in G-ROUTE3.
- **Attempts:** seeds are identical across attempts.

**Sentences.** These ASCII templates are verbatim. `<binding>` and `<table>` are 64 lowercase hex characters, and
`<n>` and `<m>` are positive integers. G-ROUTE3's sentences match none of them.
- `Authorize G-ROUTE4 phase A execution <binding> attempt <n>`
- `Authorize G-ROUTE4 phase A execution <binding> attempt <n> after integrity failure of attempt <m>`
- `Authorize G-ROUTE4 phase B execution <binding> table <table> attempt <n>`
- `Authorize G-ROUTE4 phase B execution <binding> table <table> attempt <n> after integrity failure of attempt <m>`
- `Abandon G-ROUTE4 phase <A|B> attempt <n> after failed preflight`
- `Declare G-ROUTE4 phase <A|B> attempt <n> integrity failure`
- `Clear G-ROUTE4 phase <A|B> orphan run <run_id>`
- `Freeze G-ROUTE4 qualification table from phase A attempt <n> of execution <binding>`

Resume uses the consumed launch sentence, as in R7.

**Data roots.**
- **G-ROUTE3's side already refuses** without any code change. `g_route3_freeze.DATA_ROOT` is a literal, and
  `verify_manifest` rebuilds the manifest from it. A G-ROUTE4 test asserts this.
- **G-ROUTE4's side checks first, read-only.** Before setup, the lease, or any write, G-ROUTE4 checks the literal
  data-root path and, if `root.json` is committed, its experiment name. Any other root or name refuses.

## Coding exclusion in the R7 fork

- The corpus loader refuses any `coding.v1` profile or coding task class.
- `RunSpec.coding` is asserted to be empty.
- The execution entry kinds stay in the grammar only as forbidden kinds. Replay treats any `execution_started` or
  `execution_recorded` entry as an integrity failure. That makes the coding replay states unreachable, and the
  protection clause keyed to a clean `execution_recorded` does not apply.
- There is no worker. `Runtime.worker` is absent, and the scorer's coding branch and executable derivation are
  removed from the fork.
- The freeze's AST recursion band is not measured, since no candidate code exists.
- **Certification:**
  - **Dropped:** the sandbox-failure sweep, Ctrl+C during the sandbox, and worker module drift.
  - **Added:** a probe proving that an injected execution entry is an integrity failure, and a probe proving that
    the coding runner is never loaded.
  - **Kept:** every other R7 campaign section, including kills, power loss, damage, flush failures, environment,
    gap seeds, review seeds and resumed interrupts.

## Schedule (fixed before any contact)

Both phases use a **fixed, fully enumerated schedule**, frozen before contact:
- every position has its call id, seed and request digest;
- positions are identical across attempts.

Phase B′ calls all three tiers on every case (D1). Routing is computed afterwards, gold-blind, from the sealed
records by the frozen router, as in G-ROUTE3. R7's guarantees therefore apply unchanged: no position is sent twice,
replay is deterministic, attempts are protected, and denominators are defined.

**Phase A′:** 5 classes × R1–R4 × 4 fixtures = **80 fixtures**, × 3 tiers × 2 repeats = **480 calls**, 60 cells.

**Phase B′ (D9):**

| Stratum | Cases per cell | Cells | Cases |
|---|---|---|---|
| Ordinary conversation, R1–R3 | 28 | 3 | 84 |
| Extraction, synthesis, planning, research, R1–R3 | 18 | 12 | 216 |
| **Eligible total** | | | **300** |
| R4, one per class (evidence-only) | 1 | 5 | 5 |
| **B′ fixtures** | | | **305**, × 3 tiers = **915 calls** |

- **The P1 estimand** is the rate over this mix, **given the realized A′ table**.
- **Conversation is oversampled.** That is conservative for P1 only if conversation qualifies, and it rests on
  G-ROUTE3's hypothesis-generating result. If conversation does not qualify, oversampling lowers n instead.
- **B′ is never resized,** topped up, extended or pooled. NOT_TESTABLE is final.

## Corpora

**Output-shape disclosure (D8, decided 2026-09-28).**
- **Research prompt:** the G-ROUTE3 research rule body, byte-identical; only the subject phrase varies.
- **Inserted sentence:** exactly once, immediately after `Each claim object has exactly the keys claim_id, status,
  citations and lineages.`, separated by one ASCII space, with ASCII punctuation and no surrounding quotes:

  ```
  Reply with a JSON object whose keys are exactly claims, recommendation and uncertainties: claims is a list with one claim object for each input claim; in each claim object, status is one of supported, contradicted or unresolved, citations is a list of distinct source_id strings, and lineages is a list of distinct lineage-name strings; recommendation is a string; uncertainties is a list of code strings.
  ```

  It discloses every output-shape rule the frozen research validator enforces. It changes no judgment rule, and the
  validator is unchanged.
- **The other four classes:**
  - A shape-disclosure audit compares each profile's validator-enforced shapes (containers, element types, key
    sets, uniqueness, identity with the input) with its prompt.
  - Every gap is closed by a pre-registered sentence in the freshly authored **fixture prompt**. G-ROUTE1's system
    prompts stay byte-identical.
  - The review already found two such gaps: synthesis `statements` and planning `steps` are lists, with
    string-list id fields.
  - The sentences are frozen with the corpora and checked in the external corpus review.
- **Freeze-time tests:**
  - every research prompt equals the rule body, the subject phrase and the D8 sentence at its point;
  - the audit finds no residual gap in any class.

**Authoring blueprint** (frozen before authoring). Research allocation (declared: it rests on the construct, not
on G-ROUTE3's failure rates):

| Research cell | A′ (4 fixtures) | B′ (18 fixtures; R4: 1) |
|---|---|---|
| R1 | S1 S2 S3 S4 | S1–S8 × 2, plus S1 S2 |
| R2 | S5 S6 S7 S8 | S1–S8 × 2, plus S3 S4 |
| R3 | S1 S3 S5 S7 | S1–S8 × 2, plus S5 S6 |
| R4 | S2 S4 S6 S8 | S7 (evidence-only) |

- **`single_lineage_support` holds in:**
  - 2 of 4 fixtures in every A′ research cell;
  - 9 of 18 in every eligible B′ research cell;
  - the R4 case: declared "holds".
- **Declared coverage gap:** an A′ research cell qualifies on 4 patterns, while its B′ cell tests all 8. So B′
  tests generalization across patterns within the construct.
- Research qualification is conditional on this allocation, and its construct is not comparable with G-ROUTE3's.
- **The other classes' feature allocations** are frozen in the blueprint in the same exact per-cell form.

**Template families and independence.**
- **Shared template families.** A′ and B′ share a set of families per class. Every B′ family appears in A′ and every
  A′ family in B′, with at least 1 fixture each.
- **Cap.** No family exceeds 25% of a class's B′ cases. That gives at least 4 families per class, and at least 5
  for conversation (85 cases).
- **Planning.** G-ROUTE3 used one declared planning template; G-ROUTE4's planning construct uses at least 4
  families. That is a declared construct change.
- **What may be shared** across A′/B′ and with G-ROUTE3's corpora: the construct, pattern labels and template
  families.
- **What must be fresh:**
  - entity names, numbers, dates and answer values;
  - no gold answer structure repeated within a cell;
  - no fixture with a content-4-gram Jaccard similarity above 0.5 to any other G-ROUTE4 fixture, or to any
    G-ROUTE3 fixture (A or B).
- `CONTAMINATION_ANALYSIS.md` and `INDEPENDENCE_REPORT.json` report these measures per class, and are reviewed in
  the external corpus review.
- **Cluster-sensitivity bound.** The unit is a template family; a family is unsafe if any of its stops is unsafe.
  The bound is an exact binomial bound on families. It is reported, never gating, and declared near-uninformative
  (about 5 families per class).
- P1 is declared **conditional on fixtures being exchangeable within the frozen mix**. Unsafe stops cluster by cell.

**Authoring rules:**
- no fixture is pretested on a pinned model or any Ollama model;
- no item is derived from a G-ROUTE3 item whose outputs were inspected;
- G-ROUTE3's corpora are development material only.

**Gold adjudication** (A′, B′ and reserves alike; each batch started by the operator in chat).
1. **Seal first.** The full corpus, gold, rationales and a reserve of 20% per cell (rounded up) are committed by
   digest before the first adjudication. After adjudication starts, gold changes only through a recorded fix.
2. **Sessions.** One fixture per fresh Claude session, never a pinned model and never Ollama. The model id and
   version and the frozen prompt are recorded.
   - The session sees only the model-facing fixture.
   - It is blind to gold, rationale, G-ROUTE3 outputs and the diagnosis.
   - Each answer is sealed by a committed digest before comparison.
   - Every invocation is logged with its transcript digest. The first sealed answer is the answer, with no re-runs.
     An invocation that produces no answer is logged and retried once.
3. **Disagreement** means the answer fails the frozen semantic validator against gold.
4. **Decision table:**

   | First adjudicator | Second (fresh, equally blind) | Third (fresh, blind) | Outcome |
   |---|---|---|---|
   | agrees | — | — | keep |
   | disagrees | agrees | — | keep (adjudicator error) |
   | disagrees | disagrees | agrees | keep |
   | disagrees | disagrees | disagrees | the operator decides, against the derivability rule only, with a written reason |

   The operator's options are: **gold wrong → fix gold**; **input ambiguous → fix input**; **gold right → keep**.
   The operator is not blind; this is declared.
5. **Fixes.** A fixed fixture is re-adjudicated from scratch, with at most **one fix per fixture**. Failing again
   means it is replaced.
6. **Replacements.** Taken from the slot's reserve in a fixed order, with the same blueprint features (pattern,
   `single_lineage_support`, family, cap). They are adjudicated from scratch. There are at most 2 rounds.
7. **Exhaustion.** If the reserve for a slot is exhausted, authoring **halts before the freeze**. The corpus is never
   shrunk, and D9 is never changed. More reserve needs a recorded operator decision.
8. **Records.** Per-cell fix and replacement counts and disagreement rates are disclosed, and bound in the freeze.

## Qualification (Phase A′)

- **8/8 unanimity:** 4 fixtures × 2 repeats.
- **Declared stricter** than G-ROUTE3's 4/4. P(qualify) falls from 0.656 to 0.430 at a per-observation pass
  probability of 0.9, and from 0.815 to 0.663 at 0.95.
- **Every cell reports:**
  - the observation-level bound (0 failures in 8 gives 0.312);
  - the fixture-level bound (0 failures in 4 fixtures gives 0.527, against G-ROUTE3's fixture-level 0.776 for 2
    fixtures).
  Repeats are correlated, so the fixture-level bound is the honest one.
- **The 0.60 correct-stop rationale is restated.** A qualified cell needed eight of eight correct across four
  independent fixtures. A correct-stop rate below 60% on new cases would mean the label carries too little
  predictive information.
- G-ROUTE3's qualification contract is carried over otherwise.

## Gates (frozen before contact)

**Bounds.** Exact one-sided Clopper-Pearson at α = 0.05. With k events out of n:

| Statement | Exact form |
|---|---|
| upper bound ≤ 0.10 | P(X ≤ k \| n, 0.10) ≤ 0.05 |
| lower bound > 0.10 | P(X ≥ k \| n, 0.10) < 0.05 |
| lower bound ≥ 0.60 | P(X ≥ x \| n, 0.60) ≤ 0.05 |
| upper bound < 0.60 | P(X ≤ x \| n, 0.60) < 0.05 |

n = 0 is NOT_TESTABLE. Every result reports k, n and both bounds.

**Floors, with their rationale:**
- **76 stops:** the smallest n at which the unsafe gate can pass with 3 unsafe stops.
- **30 qualified-start cases:** at least 23 correct are needed there for a lower bound of at least 0.60.
- G-ROUTE3's observed-rate standard at n ≥ 10 is kept for FAIL.
- The floors are stricter than G-ROUTE3's, never looser. Identical evidence can be NOT_TESTABLE just below a floor
  and FAIL just above it; this is declared.

**Unsafe-stop gate** (n = stops; every stop can be unsafe):

| Outcome | Condition |
|---|---|
| PASS | n ≥ 76 and the upper bound ≤ 0.10 |
| FAIL (shown worse) | the lower bound > 0.10, at any n ≥ 1 |
| FAIL (not shown) | n ≥ 76 and the upper bound > 0.10; or n ≥ 10 and the observed rate > 0.10 |
| NOT_TESTABLE | otherwise |

**Correct-stop gate** (n = qualified-start cases):

| Outcome | Condition |
|---|---|
| PASS | n ≥ 30 and the lower bound ≥ 0.60 |
| FAIL (shown worse) | the upper bound < 0.60, at any n ≥ 1 |
| FAIL (not shown) | n ≥ 30 and the lower bound < 0.60; or n ≥ 10 and the observed rate < 0.60 |
| NOT_TESTABLE | otherwise |

**Integrity** is all of G-ROUTE3's integrity gates, with FAILED_INTEGRITY if any is violated:
- denominator integrity (915 B′ calls, 300 eligible and 5 R4 cases decided, per-cell composition as in D9);
- 0 unqualified-tier terminal results;
- 0 gold-leakage events;
- 0 table mutations after Phase B′ starts;
- 0 benchmark crashes from model output;
- 0 missing-data qualifications.

**Primary status:** FAILED_INTEGRITY, then FAIL, then NOT_TESTABLE, then PASS. The two gates form an
intersection-union test, so no multiplicity adjustment is needed.

**Power (declared).** The table gives the minimum and maximum of P(PASS) for the unsafe gate over n = 120–219
stops. The range comes from 300 eligible cases at 0.40–0.73 stops per case; G-ROUTE3's rate was 0.61, and 8/8
lowers it.

| True unsafe rate | P(PASS), minimum–maximum |
|---|---|
| 0.02 | 0.985–1.000 |
| 0.03 | 0.908–0.998 |
| 0.05 | 0.541–0.877 |
| 0.07 | 0.201–0.457 |
| 0.09 | 0.05–0.12 |

**Stops arrive in whole cells.** They come in blocks of about 28 per qualified conversation cell and 18 per other
cell. P1 is NOT_TESTABLE whenever fewer than 76 stops occur. That happens when the qualified cells with a starting
tier give at most 4 other-class cells and no conversation cell; or 1 conversation cell and at most 2 others; or 2
conversation cells and at most 1 other. Under 8/8 this is a declared, real possibility.

**P2 (descriptive).** Two figures, each with k, n and an upper bound:
- the conversation stratum's unsafe stops, with the small tier broken out;
- because all three tiers are called, the small tier's conversation semantic-failure rate on all 84 conversation
  cases, as a diagnostic counterfactual, whether or not small qualifies.

**E1 (pilot, descriptive).**
- It reports escalations, escalated stops, and the correct and unsafe counts among them, with bounds.
- It reaches no verdict.
- The planning figure is P(at least 5 escalated stops) ≈ 0.62–0.80. That uses a Jeffreys Beta(1.5, 21.5) prior on
  G-ROUTE3's 1 escalation in 22 qualified starts, over 120–219 qualified starts. It is optimistic, because
  escalation needs at least 2 qualified tiers in a cell, which is rarer under 8/8.

**Descriptive reporting** (frozen in code; never gating):
- an equal-weight-by-class unsafe rate over classes with at least 1 stop, without a bound;
- research claim-level agreement, uncertainty-code agreement and element-shape failures;
- per-template and per-cell breakdowns, and the cluster-sensitivity bound.

**Generalization** (descriptive, redefined). Each eligible B′ cell reports its semantic pass rate and exact 95%
interval beside its A′ verdict and A′ bounds. G-ROUTE3's generalization labels ("2 of 2") are not used, because B′
cells now hold 18 or 28 cases.

## Scoring shapes in the fork

- Denominators: 915 and 305.
- The thresholds schema:
  - `observations_required` 8, `fixtures_per_cell` 4, `repeats` 2;
  - floors of 76, 30 and 10;
  - the exact bound forms.
- The B′ loader checks the D9 per-cell composition (28, 18 or 1).
- The secondary escalation verdict and the "excluding coding" metric are removed.

## Phase B′ preconditions

R7 §10 items 1–11 apply unchanged, except:
- 60 cells instead of 72;
- the 8-observation cell shape;
- G-ROUTE4 paths, sentences and identity.

## Certification and differential

- **The full R7 certification campaign**, adapted as in "Coding exclusion", on the `g_route4_*` modules.
- **A lifecycle differential** runs a shared non-coding synthetic schedule through G-ROUTE3's R7 and through the
  G-ROUTE4 fork. The journal entries, ledger and evidence commits must be equal apart from the identity strings.
- **An independently written oracle** covers the rules that differ by design: 8/8 qualification, the three-way
  gates, and the exact bounds including the lower bound. It is checked exhaustively over every (n, k) with n ≤ 400.

## Order of work and authorization

1. **Design review** until accepted. This is revision 3.
2. **Authoring blueprint** frozen: per-cell features, template families, reserve slots.
3. **Corpora:**
   - authoring, then the shape-disclosure audit, then the corpus and gold digest seal;
   - adjudication, with the operator starting each batch;
   - the contamination and independence reports;
   - **the external corpus review**: two fresh reviewers under the safety-gated rule; accepted at 0 BLOCKING with
     every MUST-FIX resolved.
4. **Implementation** in `g_route4_*`, then an implementation review, certification and the differential.
5. **Execution freeze** (G-ROUTE4 binding, Ollama version recorded).
6. **Phase A′:**
   - the operator's sentence;
   - an independent A′ audit by a fresh Claude session with no authoring context, declared not to be an operator
     audit;
   - the freeze-table sentence;
   - the table on `main`.
7. **Phase B′:** the operator's sentence, then an independent B′ audit by a fresh session, then the results record.

Production routing stays disabled whatever the result.

**Runbook:**
- Reserve uninterrupted windows of about 3.2 hours for A′ and about 6 hours for B′.
- An interrupt closes a fresh attempt. Under ruling 12, a resumed attempt interrupted before its first new call stays
  open, and an interrupt after collection exits without closing.
- Check the Ollama version before each launch.

## Operator decisions

| # | Decision | Chosen |
|---|---|---|
| D1 | Phase B′ calls | **All three tiers** (revised after round 1) |
| D2 | P2 conversation stratum | **Reported with its bound**, not gating |
| D3 | Escalation | **Pilot, descriptive.** Originally "size for about 200 routed attempts"; that became moot when the operator chose D9, and is recorded here as a consequence, not a new decision |
| D4 | Qualification scale | **8 observations per cell**, with both bounds reported |
| D5 | R4 in Phase B′ | **A minimal set:** one per class |
| D6 | Coding | **Deferred** to its own experiment (revised after round 1) |
| D7 | Grounded research | **Diagnose, then include.** The diagnosis is done; the validator is unchanged |
| D8 | Output-shape disclosure | **The verbatim research sentence above; all classes audited; gaps closed in fixture prompts** (operator approval of the exact wording and scope, 2026-09-28, after round 2) |
| D9 | Phase B′ size | **300 eligible cases** plus 5 R4 cases: 915 calls |
| D10 | Adjudication authorization | **The operator starts each batch in chat**; every session is logged and sealed (2026-09-28) |

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
