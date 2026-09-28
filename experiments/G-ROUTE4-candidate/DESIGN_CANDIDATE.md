# G-ROUTE4: confirmatory qualification routing (design candidate)

Status: **design candidate only.** Nothing is frozen. No model has been contacted for G-ROUTE4, and no corpus or gold
exists yet. The execution freeze stays unbuilt until the design review is accepted. Production routing stays
disabled, and belief effects are `none`.

This draft goes through the same process as G-ROUTE3's R7 design:
1. two fresh read-only reviewers, under the safety-gated rule;
2. then implementation, an implementation review and certification;
3. then a freeze, and the operator's verbatim sentence for each phase.

## Origin, and what this experiment is not

G-ROUTE3 closed as **PASS WITH LIMITATIONS (pilot-qualified)** (`experiments/G-ROUTE3-candidate/RESULTS.md`):
- the primary gates were met on observed rates;
- unsafe stops were 2 of 22, a pass by less than one case, with a one-sided 95% upper bound of 0.259;
- the escalation question was not testable;
- coding and grounded research had no qualified cells.

G-ROUTE4's targets were **chosen from G-ROUTE3's results**, so they generate hypotheses and are declared as such.
That is why G-ROUTE4 uses entirely fresh corpora and gold, fixed before any contact.

G-ROUTE4 is **not**:
- a rescoring, extension or second reading of G-ROUTE3;
- a reuse of G-ROUTE3's Corpus B as validation data, since it has now been seen;
- a route to production.

G-ROUTE3's corpora may be used only as development material for building fixtures and validators. They are never
used to tune gold or thresholds against observed model outputs.

## What is reused

The whole R7 laboratory:
- the one-journal-per-run lifecycle, replay, recovery and the private evidence repository;
- the attempt ledger and verbatim sentences;
- the table freeze, independent audits and the certification campaign;
- the pinned models (qwen2.5:7b, qwen3:14b, qwen3.8:27b) with the G-ROUTE3 generation configuration, and
  Ollama 0.34.3.

Any code change, such as corpus paths, the coding allowlist or a new gate, goes through an implementation review
and a certification rerun before the freeze.

## Questions

**P1: confirmatory routing safety.**
- **Question:** with a freshly qualified table, is the true unsafe-stop rate at most 0.10, and the true
  correct-stop rate of qualified-start cases at least 0.60, each at one-sided 95% confidence?
- **What changes from G-ROUTE3:** its gates judged **observed rates**. G-ROUTE4's gates judge **exact
  (Clopper-Pearson) bounds**.

**P2: conversation on the cheapest tier.**
- **Question:** is routing safe for ordinary conversation where the small tier qualifies?
- **Why:** both of G-ROUTE3's unsafe stops were conversation on the small tier: B-CONV-R1-1 and B-CONV-R3-2, each
  the wrong answer option.

**S1: escalation.**
- **Question:** when a qualified tier's output fails deterministic validation, does moving to the next qualified
  tier gain correct stops without unsafe ones?
- **Why:** G-ROUTE3 produced 1 escalated stop out of the 5 required.

**S2: coding.** Can any tier qualify for coding once the execution allowlist is principled rather than minimal?

**S3: grounded research.** Why does no tier qualify, and can a tier qualify on a fresh corpus?

## Diagnostics from G-ROUTE3 (exploratory, read-only, never a result)

These were computed on 2026-09-28 from G-ROUTE3's sealed records with the frozen scorer functions. They were read
directly from the journals, with no lifecycle command and no data-root writes. They motivate the design and
change nothing in G-ROUTE3.

**Coding (72 outputs across both phases):**

| Outcome | Outputs |
|---|---|
| passed | 12 |
| compiled, but the focused test failed | 9 |
| malformed JSON | 7 |
| syntax errors | 5 |
| rejected by the candidate validator before execution | 39 |

Of the 39 validator rejections, **28 were denied calls to pure, side-effect-free built-ins or methods**:

| Denied call | Times |
|---|---|
| `len` | 11 |
| `any` | 4 |
| `append` | 3 |
| `isinstance` | 2 |
| `range`, `enumerate`, `find`, `rstrip`, `lstrip`, `isdigit`, `isalnum`, `endswith` | 1 each |

The frozen allowlist (`tools/g_route1_coding_runner.py`) permits only:
- the call names `bool` and `PurePosixPath`;
- the attributes `strip`, `lower`, `split`, `join`, `replace` and `startswith`.

The prompt disclosed it, but it forbids ordinary Python.

**Grounded research:** the full per-case diagnosis of the 41 `research_judgment_mismatch` outputs is in
`RESEARCH_DIAGNOSIS.md` and `RESEARCH_DIAGNOSIS.json`. It corrects this draft's first reading, which blamed
wrong claim judgments. The mismatches cluster tightly:
- **Uncertainty-code bookkeeping: involved in 32 of 41, the primary cause in 13.**
  - `single_lineage_support` differs from gold in 30 of 41.
  - It is a cross-claim code that holds whenever any supported claim rests on one lineage. Models omit it in
    that situation, and also list it for unresolved or contradicted claims.
- **Which sources are "about" a claim, and their scope: primary in 11.** A narrower-scope source is reported as a
  conflict, a source about another venue or version is cited, or two sources of one lineage are counted twice.
- **Conflict and governing-source rules: primary in 11.**
- **Output element shape the prompt does not specify: involved in 18, primary in 4.** In those 4, the substance
  matches gold exactly.

By tier:
- **large** never misjudged a claim's status or about-ness. Its failures are bookkeeping, shape, and two readings
  of a governing source's denial as support.
- **small** makes genuine claim-level errors.

12 of the 26 false-clean answers are bookkeeping errors.

The earlier count of malformed JSON (13) and element-type mismatches (20) covers all research failures, not only
the 41.

**Conversation:** some failures converge across tiers. In Corpus A, both mid and large answered A-CONV-R2-2 with the
same non-gold option in every repeat, and small and mid did the same on A-CONV-R2-1. This does not show the gold
was wrong, and nothing is regraded. It does show that each fixture's gold should be adjudicated independently
before freezing.

## Design

**Corpora.** Fresh Corpus A′ (qualification) and Corpus B′ (validation) under G-ROUTE3's derivability rule:
- every closed label is offered as an allowed set;
- every enforced ordering is stated;
- every execution constraint is disclosed.

Added for G-ROUTE4: **independent gold adjudication before contact.** A fresh reviewer, who has not seen the
fixture's authoring rationale, answers each fixture from its model-facing input alone. Any disagreement with gold
is resolved or the fixture is dropped, all before the freeze, and every resolution is recorded.

**Coding allowlist (S2). Decided (D6): the stated purity rule.** The allowlist is re-derived from a **stated
criterion**, not from the list of observed denials:
- **Allowed:** pure built-ins and methods with no I/O, import, reflection, attribute mutation outside local
  values, or code execution. For example `len`, `any`, `all`, `isinstance`, `range`, `enumerate`, `min`, `max`,
  `sorted`, `str`/`int`/`list`/`dict`/`set`/`tuple` constructors, `append` on local lists, and the read-only
  `str` methods.
- **Still denied:** `getattr`, `setattr`, `eval`, `exec`, `open`, `__import__`, `type`, `vars`, `globals` and
  dunder access.

The sandbox (isolated runner, kill-on-close job) remains the containment; the allowlist is defense in depth. The
criterion, the resulting list and its security argument are frozen and disclosed in every coding prompt. G-ROUTE3's
coding outputs are **not** re-evaluated under it.

**Qualification (Phase A′).** Same cell structure: 6 task classes × R1–R4 × 3 tiers. Unanimity is retained.
- **8 observations per cell (D4):** 4 distinct fixtures × 2 repeats. Zero failures in 8 bounds the per-cell
  failure rate below 0.312, against 0.527 at 4.
- **Size:** 96 fixtures, 576 calls.

**Validation (Phase B′).**
- Routing is gold-blind on the frozen A′ table, with G-ROUTE3's routing policy unchanged. The two retained
  triggers stay; the retired ones stay retired.
- The size of B′ is set in advance from the gates. G-ROUTE3 produced 0.61 stops per eligible (non-R4) case. P1
  needs these stop counts:

  | Unsafe stops observed | Stops needed to meet the bound |
  |---|---|
  | 0 | 29 |
  | 1 | 46 |
  | 2 | 61 |
  | 3 | 76 |

- **The unsafe gate is evaluable only with at least 76 stops.** Fewer stops make P1 NOT_TESTABLE, never a pass.
- **Router-only (D1):** Phase B′ makes only the calls the router consumes. A case with no qualified tier costs
  0 calls. The false-negative-qualification measure is therefore not available, which is declared.
- **Size is set by escalation (D3), not by P1:**
  - the target is about 200 routed attempts, which needs about 300 eligible cases at G-ROUTE3's 0.64 routed
    attempts per eligible case;
  - that also gives about 180 expected stops, well above P1's 76;
  - conversation R1–R3 is oversampled for P2.
- **R4 (D5):** stays evidence-only, with a minimal deterministic set of R4 cases (one per task class) to exercise
  that behaviour end to end.

**Escalation (S1).** Escalation needs a routed attempt rejected in a cell with at least two qualified tiers.
G-ROUTE3's rate was about 1 in 23 routed attempts:

| Routed attempts | Expected escalations | P(at least 5) |
|---|---|---|
| 115 | 5 | 0.56 |
| 150 | 6.5 | 0.78 |
| 200 | 8.7 | 0.94 |

These count escalations, not escalated stops, so the true chances are lower. **Decided (D3):**
- B′ is sized for about 200 routed attempts, with natural escalations only and no case selection;
- S1 stays non-gating.

**Grounded research (S3). Decided (D7): diagnose, then include.** The diagnosis is done (`RESEARCH_DIAGNOSIS.md`).
Research joins A′/B′ on fresh, independently adjudicated fixtures, and:
- **The validator is unchanged:** exact match on claims, recommendation and uncertainties. Nothing is loosened.
- **Fixtures separate the three failure patterns**, so each can be read directly:
  - fixtures where every supported claim has at least two lineages (`single_lineage_support` does not hold);
  - fixtures where it holds only through an uncontroversial claim;
  - narrower-scope and other-subject sources in separate fixtures;
  - conflicts both with and without a governing rule.
- **Descriptive reporting at two levels,** next to the unchanged gate and never gating:
  - claim-level agreement (status, citations, lineages);
  - uncertainty-code agreement.
  A tier's research failures can then be read as judgment or bookkeeping.
- **The prompt:** unchanged under D7, unless the operator adopts D8 below.

A prompt or validator change counts as a protocol change and needs its own pre-registration.

**Proposed gates** (frozen before contact; judged on bounds):
- **Primary:** unsafe-stop exact one-sided 95% upper bound at most 0.10, evaluable only with at least 76 stops.
- **Primary:** correct-stop exact one-sided 95% lower bound at least 0.60, evaluable only with at least 30
  qualified-start cases.
- **Primary:** 0 unqualified-tier terminal results, 0 gold leakage events, denominator integrity.
- **P2 (D2):** reported, not gating. The conversation stratum's unsafe-stop rate and exact 95% upper bound, with
  the small tier broken out.
- **S1:** as in G-ROUTE3 (at least 5 escalated stops to evaluate), plus a reported bound.

## Cost

At G-ROUTE3's pace (about 24 s per call on average across tiers):
- **Phase A′:** 576 calls, about 4 hours.
- **Phase B′:** router-only, about 200 routing calls, about 1.5–2 hours. Routed calls lean towards the cheaper
  tiers.

**Authoring effort.** This is the real cost:
- about 96 qualification fixtures and about 300 validation fixtures, plus the R4 set;
- each fixture has gold, a derivability check and independent adjudication.

Authoring can be staged by task class.

## Operator decisions (2026-09-28)

| # | Decision | Chosen |
|---|---|---|
| D1 | Phase B′ diagnostic calls | **Router-only**; the false-negative-qualification measure is not available (declared) |
| D2 | P2 conversation stratum | **Reported with its bound**, not gating |
| D3 | Escalation | **Size B′ for about 200 routed attempts**; natural escalations only; S1 non-gating |
| D4 | Qualification scale | **8 observations per cell** (4 fixtures × 2 repeats) |
| D5 | R4 in Phase B′ | **A minimal deterministic set** |
| D6 | Coding allowlist | **The stated purity rule**, frozen with its security argument and disclosed in prompts |
| D7 | Grounded research | **Diagnose, then include** with the unchanged prompt and validators |
| D8 | Research output element types | **Open.** The diagnosis found the prompt names the keys of a claim object, but never states that `claims` is a list, or that `citations`, `lineages` and `uncertainties` are lists of strings. 4 outputs failed on shape alone and 14 others were confounded by it. Options: keep the prompt unchanged (consistent with D7), or add a pre-registered sentence stating the element types. That is a prompt change, not a validator change, and touches no judgment. |

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
