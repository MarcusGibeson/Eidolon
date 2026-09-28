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

**Grounded research:**
- the dominant semantic failure is `research_judgment_mismatch` (41 outputs): the claim judgments differ from gold;
- the other failures are malformed JSON (13) and citation or uncertainty element-type mismatches (20).

The false-clean answers are well-formed but wrongly judged. This is a reasoning or grounding failure, not a format
failure.

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

**Coding allowlist (S2).** The allowlist is re-derived from a **stated criterion**, not from the list of observed
denials:
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
Observations per cell are an open decision (D4):
- 4, as in G-ROUTE3 (0/4 gives an upper bound of 0.527);
- or 8 (0/8 gives 0.312).

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
  At G-ROUTE3's rate this needs about 125 eligible cases; the plan is about 150, with conversation R1–R3
  oversampled for P2.
- R4 stays evidence-only, with a small set of R4 cases to exercise that behaviour deterministically (D5).

**Escalation (S1).** Escalation needs a routed attempt rejected in a cell with at least two qualified tiers.
G-ROUTE3's rate was about 1 in 23 routed attempts:

| Routed attempts | Expected escalations | P(at least 5) |
|---|---|---|
| 115 | 5 | 0.56 |
| 150 | 6.5 | 0.78 |
| 200 | 8.7 | 0.94 |

These count escalations, not escalated stops, so the true chances are lower. Two options (D3):
- size B′ for about 200 routed attempts;
- or add a separately analysed, pre-registered format-stress stratum. That raises the rejection rate by
  construction, never by choosing cases expected to fail.

S1 stays non-gating unless the operator decides otherwise.

**Grounded research (S3).**
1. First, a read-only diagnosis of G-ROUTE3's 41 judgment mismatches, which classifies each as misjudged status,
   misread source or possible fixture ambiguity.
2. Then the operator decides (D7) between:
   - including research in A′/B′ with the unchanged prompt and validators on fresh fixtures;
   - or deferring research to its own experiment.

A prompt or validator change counts as a protocol change and needs its own pre-registration.

**Proposed gates** (frozen before contact; judged on bounds):
- **Primary:** unsafe-stop exact one-sided 95% upper bound at most 0.10, evaluable only with at least 76 stops.
- **Primary:** correct-stop exact one-sided 95% lower bound at least 0.60, evaluable only with at least 30
  qualified-start cases.
- **Primary:** 0 unqualified-tier terminal results, 0 gold leakage events, denominator integrity.
- **P2 (D2):** a reported conversation-stratum unsafe bound, gating only if the operator decides so before the
  freeze.
- **S1:** as in G-ROUTE3 (at least 5 escalated stops to evaluate), plus a reported bound.

## Cost

At G-ROUTE3's pace (about 24 s per call on average across tiers):
- **Phase A′:** 288 calls at 4 observations per cell (about 2 hours); 576 at 8 (about 4 hours).
- **Phase B′:** about 150 eligible cases.
  - **Router-only** (D1): about 160–210 routing calls, about 1.5 hours.
  - **With G-ROUTE3's all-tier diagnostics:** about 470 calls, about 3 hours.

## Open decisions for the operator (before the design review freezes them)

| # | Decision | Options |
|---|---|---|
| D1 | Phase B′ diagnostic calls | router-only (cheaper; loses the false-negative-qualification measure) · or all three tiers, as in G-ROUTE3 |
| D2 | P2 conversation stratum | reported only · or gating |
| D3 | Escalation | size for about 200 routed attempts · or a pre-registered format-stress stratum · or report descriptively only |
| D4 | Qualification scale | 4 observations per cell · or 8 |
| D5 | R4 in Phase B′ | a minimal deterministic set · or excluded |
| D6 | Coding allowlist | approve the stated criterion · or keep G-ROUTE3's list (coding is then expected to stay unqualified) |
| D7 | Grounded research | include in A′/B′ after the diagnosis · or defer to its own experiment |

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
