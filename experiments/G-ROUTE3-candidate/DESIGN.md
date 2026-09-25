# G-ROUTE3 — Out-of-Sample Qualification Routing Validation

Status: **design and freeze only.** No model has been contacted. Provider generation calls: **0**.
Benchmark launches: **0**. Production routing: disabled. Automatic escalation: disabled. Belief effects: `none`.

Revision: **R6.** No earlier freeze was ever authorized; all are preserved and superseded.

- **R1** (binding `64eed1ba…`). An external pre-contact review found hidden grader rules, a trigger that fired
  on correct answers, template reuse between corpora, a gate that could hide a failure, weak table
  provenance, and a freeze check that made Phase B impossible to authorize.
- **R2** (binding `aa5db17a…`). A second review found that:
  - Phase A provenance could be fabricated;
  - authorizations could be reused;
  - conversation phrase anchors still failed in both directions;
  - coding rejected correct fixes over a trailing newline;
  - some runtime modules were unguarded.
- **R3** (binding `f92fd6e0…`). A third review found that:
  - one authorization could drive several runs by changing the run root;
  - the authorized path accepted any provider;
  - a synthetic run could be relabelled;
  - a complete attempt could be repeated best-of-N;
  - the conversation action-claim pattern failed in both directions;
  - synthesis graded keywords the model was never shown.

- **R4** (binding `3660f60f…`). A fourth review found four problems:
  - The "Actions taken" field accepted an action smuggled in after a note, and rejected natural no-action
    forms.
  - Malformed model output could crash collection, so Phase A could never finish.
  - An interrupted finalization could deadlock an attempt.
  - Cheap ledger tampering, or a redirected endpoint, was not tamper-evident.

- **R5** (binding `2e97b75e…`). A fifth review found two problems, each a class that round 5 had repaired
  only for the exact case previously probed:
  - a pathological coding candidate raised an error before the sandbox subprocess started, and the run
    charged it to infrastructure, which stopped Phase A;
  - three crash windows during finalization left an attempt unrecoverable.

  Round 6 repairs each class at its root.

See `EXTERNAL_REVIEW_ROUND1.md` to `EXTERNAL_REVIEW_ROUND5.md`.

**Threat model (operator decision): an honest operator with tamper-evident records.**

- **What the code stops:**
  - accidents;
  - misuse through any supported path;
  - cheap tampering, such as a deleted ledger entry, a replayed sentence, a redirected endpoint or a
    relabelled run.
- **What is out of scope:** a deliberate local adversary. That means someone running a fake model server,
  using a second checkout, or consistently rewriting sealed files.
- **How the out-of-scope case is countered:** by the launcher's local git anchor commits. Every consumed
  authorization and every completed run is committed as it happens.

**Authorized runs** go only through `tools/g_route3_launch.py`:

- It builds the Ollama provider itself, at a fixed local endpoint.
- It reads the operator's verbatim sentence, which names a numbered attempt.
- It uses one fixed run root per phase.
- It anchors each step in git.

An attempt may follow only attempts that did not complete.

## Research questions

**Primary.** Can a task × risk × model qualification table derived prospectively from one independent
qualification corpus safely guide cheapest-qualified model selection and stopping on a separate, unseen
validation corpus?

**Secondary.** When a qualified model's individual output fails deterministic validation, can escalation
to the next independently qualified tier improve usable admission without creating unsafe stops?

The governing principle: **qualification evidence precedes, and is independent of, the validation cases
on which routing safety is measured.**

## Why this experiment exists

G-ROUTE2 showed that per-response triggers cannot tell right answers from wrong ones: they cut correct and
incorrect stops by the same proportion. It also produced a pointer. Every unsafe stop occurred in a task
class where no tier qualified, and requiring cell qualification removed all of them. That pointer was
circular, because its table came from the same gold-labelled run. G-ROUTE3 tests the claim honestly, with
a table that has never seen the cases it is judged on.

## A construction defect found in G-ROUTE1 and G-ROUTE2, and fixed here

Designing fresh corpora exposed a defect in the inherited corpus. It changes how the earlier results should
be read, although neither experiment is rescored. See `GOLD_DERIVABILITY.md`.

In the frozen G-ROUTE1 corpus the gold answers for research, synthesis and planning use exact
closed-vocabulary codes that the model is never shown. **0 of 4** synthesis conclusion codes, **0 of 15**
planning action codes and **1 of 4** research recommendation codes appear anywhere in the model-facing
prompt or input. Replayed read-only over G-ROUTE2's frozen records, models got the research claim
judgments exactly right in 22 of 36 calls but emitted the gold recommendation code 0 times. 33 of 36
synthesis responses failed *only* on the conclusion code. None of 100 emitted plan actions matched a gold
action string. The coding execution whitelist was also undisclosed, and 9 of 36 coding outputs fell outside
it.

"No model qualifies in research, synthesis or planning" in G-ROUTE1 and G-ROUTE2 is therefore substantially
a property of how those fixtures were built, not a capability finding. G-ROUTE3's corpora are built under a
**derivability rule** so the question can actually be answered: every closed-vocabulary label in gold is
given to the model as an allowed set, every ordering the validator enforces is stated in the prompt, and
every execution constraint is disclosed.

For research, synthesis, extraction and planning, the validators are the frozen G-ROUTE1 validators,
byte-for-byte. Two profiles differ, by operator decision after the external reviews:

- **Conversation** uses a **disclosed two-line frame** (`g_route3_conversation.py`). The input lists
  `answer_options`, and the prompt states that the assistant has no tools. The reply opens with two lines:
  `Answer: <option>`, and `Actions taken: none`, which must be written exactly as instructed, with nothing
  after it. Both are closed fields and are graded exactly. The prose after them is not graded. Two earlier approaches each failed external review in
  both directions: phrase anchors, and then scanning the prose for action claims.
- **Coding** compares `old` with the source ignoring trailing newlines only (`g_route3_semantics.py`). Correct,
  test-passing fixes had failed on that one byte.

Nothing else was loosened; the fixtures were made answerable.

## Architecture

```
Corpus A (qualification)  ──►  Phase A run  ──►  score A  ──►  independent audit  ──►  freeze table (write-once, digest-bound)
                                                                                              │
                                              second operator authorization, naming the table digest
                                                                                              ▼
Corpus B (validation)     ──────────────────────────────────►  Phase B run  ──►  gold-blind routing  ──►  judged against B gold
```

Both corpora and both gold files are frozen and digest-bound **before any model contact**, so neither can
be edited in response to the other's results. The execution boundary is enforced separately. Phase B cannot
start without a frozen table that verifies by digest, traces to a complete Phase A run and its sealed score,
and is named in a second authorization.

| | Corpus A | Corpus B |
|---|---|---|
| Role | qualification | validation |
| Fixtures | 48 (2 per task × risk cell) | 48 (2 per task × risk cell) |
| Tiers per fixture | 3 | 3 |
| Repeats | 2 | 1 |
| Calls | 288 | 144 |
| Seeds | 43001–43472 | 44001–44471 |
| Observations per cell for qualification | 4 | — |

**Out of sample means "same construct, fresh instance".** B fixtures are new instances of the constructs
qualified on A: new entities, facts and answers, and a different reasoning problem within each cell wherever
the class allows one. Planning is deliberately one template in both corpora, and that is declared. See
`CONTAMINATION_ANALYSIS.md`.

Six task classes and R1–R4 are preserved and never collapsed. Models are `qwen2.5:7b`, `qwen3:14b` and
`qwen3.8:27b`, with the identical G-ROUTE1 and G-ROUTE2 generation configuration.

## Phase B provider contact

Every Corpus B fixture is observed on all three tiers. Only the observations the router would actually
consume count as routing calls. The rest are **declared controlled diagnostic calls**, required to measure
false-negative qualification (a cell unqualified on A that would have succeeded on B), and are reported
separately and never used as routing results. A cell with no qualified tier returns `no_qualified_model`
with zero routing calls.

## Evidence scale, stated plainly

Four observations per cell over two distinct fixtures is **pilot scale**. Zero failures in four bounds the
true per-cell failure rate below **0.527** at one-sided 95% confidence (exact binomial). A qualified cell is a
screen, not proof of competence, and the table records that bound on every cell. Corpus B exists to test
whether such a screen predicts anything at all.

## Documents

`GOLD_DERIVABILITY.md` · `QUALIFICATION_CONTRACT.md` · `ROUTING_POLICY.md` · `SCORING_CONTRACT.md` ·
`CONTAMINATION_ANALYSIS.md` · `PRODUCTION_ADAPTER_MAPPING.md` · `INDEPENDENT_AUDIT.md` ·
`EXTERNAL_REVIEW_ROUND1.md`
