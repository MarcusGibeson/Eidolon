# G-ROUTE3 Design Audit

Date: 2026-09-24
Revision: **R2**
Verdict: **READY for external round-2 review.** This is not a verdict that Phase A may be authorized.
Authority: non-authoritative. It grants no execution, provider, routing or belief authority, and changes no
artifact. Provider generation calls during design, review and repair: **0**.

## Read this first: what this audit is worth

This audit was performed by the agent that wrote the corpora and the code. In R1 it said READY. Two external
reviewers then found six blocking grader traps, a trigger that fired on correct answers, template reuse
across corpora, a gate that could hide a failure, weak table provenance, and a freeze check that made
Phase B impossible to authorize (`EXTERNAL_REVIEW_ROUND1.md`). It had missed all of them.

So this document is a record of what the author checked, not an assurance. The R2 freeze goes to fresh
external reviewers. Phase A may be authorized only if that review is clean, and only against the exact R2
binding.

## Round-2 repair, summarized

Every round-1 finding is either repaired or explicitly kept and declared. Each entry in
`EXTERNAL_REVIEW_ROUND1.md` names the test or construction check that locks it. In brief:

- **Grader rules.** The conversation operational check is replaced, in a separate module, so that only
  affirmative first-person action claims are rejected. Every other hidden rule was made explicit in the
  prompts:
  - the complete coding whitelist;
  - rule precedence for research statuses and synthesis conclusions;
  - exact key sets and `depends_on` as a list;
  - extraction span conventions;
  - the conversation length limit.
- **Conversation fixtures.** All 16 were rewritten.
- **Triggers.** `source_independence_insufficient` is retired. `grounding_weak` tokenizes robustly. The dead
  coding branch is removed.
- **Boundaries and scoring.**
  - An evaluable failing gate now yields FAIL.
  - Freeze verification survives the table's existence.
  - The table must match the sealed Phase A score, trace to a non-synthetic Phase A run under this freeze,
    disclose every Phase A attempt, and carry an audit bound by document digest.
  - Authorizations are consumed once.
  - A sandbox host failure is infrastructure, not model failure.
  - Qualification requires exactly 2 × 2.
- **A/B separation.** It is scoped to "same construct, fresh instance". Accidental same-template pairs are
  rewritten. Research is assigned by sub-skill. Planning is declared as a single template. A structural
  gold-shape check is added to the independence tool.

## Findings of this author pass, beyond round 1

The author pass for R2 found two more problems, both repaired before the freeze:

| # | Finding | Repair |
|---|---|---|
| 1 | `grounding_weak` still fired on a faithful synthesis restatement when a number was fused to its unit ("11C for 40min" against "11 C for 40 min"). Found by a new regression test. | Tokens split at every digit–letter boundary |
| 2 | A-EXTRACT-R1-1's gold "Branch East" began with what the new extraction rule tells the model to drop as a label, so a rule-following "East" would fail. Found by listing every extraction string gold value in its source context. | Renamed "Eastgate Library". Every other string value was confirmed to follow the leading-label convention. |

## Checks performed for R2

**Corpus construction** (`authoring/assemble_g3.py`, which writes nothing unless every check passes):

- 48 fixtures per corpus, with exactly 2 per cell;
- namespaces are disjoint;
- every reference answer passes the operational validator (G-ROUTE3), the semantic validator (G-ROUTE1)
  and, for coding, the isolated runner inside the whitelist;
- every buggy coding source fails its own tests;
- no trigger fires on any reference answer;
- **48 alternative correct answers are accepted by both validators, and 36 incorrect answers are rejected**;
- every conversation prompt discloses the 600-character limit;
- every coding prompt discloses the full whitelist;
- planning shape is normalized;
- every string extraction value is a verbatim span, and every enum value is in its schema;
- every synthesis anchor is a substring of its observation;
- every closed-vocabulary gold code is model-visible;
- no author-assigned reasoning pattern is shared within a cell.

**Planning order derivability** (a mechanical check over all 32 fixtures). Every consecutive pair of gold
steps shares an evidence item that states a "before" precedence between them. Each fixture has exactly three
such lines, so the total order is fully stated and unique.

**Independence** (`INDEPENDENCE_REPORT.json`, valid, 0 findings):

- highest cross-corpus trigram overlap 0.071 (conversation), with a bound of 0.20;
- 0 shared entities, planning actions, function names, extraction values or lineages;
- 0 same-cell gold-structure matches outside planning;
- the 16 planning pairs are declared.

**Deterministic tests** (`tools/g_route3_tests.py`): the results are in `DETERMINISTIC_TEST_RESULTS.json`.
They include:

- a real (non-synthetic) authorization path through both phases, using a synthetic provider and a stand-in
  freeze file;
- forged-table rejection;
- undisclosed-attempt rejection;
- consumed-authorization refusal;
- sandbox host-failure classification;
- the gate-ordering regression;
- both validators run over every alternative and incorrect answer.

**Unchanged and re-confirmed:**

- The router is gold-blind in code and by test.
- An unqualified tier is never contacted or used as a terminal result.
- `no_qualified_model` makes zero routing calls, and R4 is evidence-only.
- Qualification cannot pass on missing data.
- Normalization is the unchanged G-ROUTE2 contract.
- Denominators sum to 48 cases and 144 observations.
- Thresholds are argued from the design, not from prior observed rates.

## Residual limitations accepted into the R2 freeze

- **Pilot scale.** 0 failures in 4 bounds the per-cell failure rate only below 0.527.
- **Given classes.** Task and risk classes are given to the router, not inferred, so classifier error is
  unmeasured.
- **Conversation checks remain phrase-anchored.** Widened, negation-safe anchors and three tested
  alternatives per fixture reduce brittleness but cannot eliminate it.
- **Planning** tests exact rule-following on one declared template, not open-ended planning.
- **Research** cells are validated on B against different sub-skills from the ones A qualified in that cell.
  This is declared as a harder transfer.
- **Difficulty matching** within cells is the author's judgment and was not measured.
- **Unequal denominators.** B success needs 2/2 while A qualification needs 4/4. Per-observation rates are
  reported beside every generalization label.
- **Extra Phase B calls.** Phase B makes declared diagnostic calls beyond routing calls.
- **Ollama** does not attest option or seed honoring.
- **Caveats on G-ROUTE1 and G-ROUTE2.** Both carry the gold-derivability caveat and, for conversation, the
  operational-check caveat. Neither is rescored.

## Verdict

**READY for external round-2 review** of the R2 freeze. Phase A may be authorized only after that review is
clean, and only by the verbatim string `Authorize G-ROUTE3 phase A execution <R2 binding>`. Phase B
additionally requires a frozen, audited qualification table and its own authorization naming that table's
digest.
