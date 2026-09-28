# G-ROUTE4 obligations

Date: 2026-09-29.
Source: the final design review round (`DESIGN_REVIEW_ROUND6.md`) of `DESIGN_CANDIDATE.md` revision 6. The design
is accepted under the operator's decision D11.

**Precedence.** This document **overrides any conflicting wording** in `DESIGN_CANDIDATE.md` and the earlier review
records. Where the design text and an obligation differ, the obligation governs.

**Binding.**
- Each obligation must be met, and verified at the stage named, before the next stage may start.
- Nothing is waived by silence. An obligation changes only through a recorded operator decision.
- No G-ROUTE4 model call, corpus generation or implementation work begins before this document is committed.

**Stages:**

| Stage | What it is |
|---|---|
| **BP** | Authoring blueprint, frozen before authoring |
| **SEAL** | The seal commit and the audit sample, before the first adjudication |
| **CR** | External corpus review |
| **IR** | Implementation review |
| **CERT** | Certification campaign and differentials |

## Obligations

### O1: an unpredictable, unique audit sample (Reviewer A MF1, Reviewer B MF3)

- The blueprint contains **no** audit-sample seed. The "audit-sample seed" in the design's order of work, step 2, is
  withdrawn.
- **The seal commit** is the single commit on `main` whose parent is the frozen blueprint commit. It adds:
  - the sealed digests of the corpus, gold, rationales and reserve;
  - the frozen adjudicator configuration (O2).
- **The sample** is taken per B′ cell: the k fixtures with the smallest `sha256(ascii(seal_commit_id) + ":" +
  fixture_id)`. k is 10% of the cell, rounded up: 3 per conversation cell, 2 per other eligible cell, and 1 per R4
  cell, 38 in total.
- **Recording:** the frozen tool computes the sample list, and it is committed **before the first adjudication
  session**.
- **Only one seal.** The seal commit id is recorded, and any later re-seal is refused. If one ever happens, both
  samples are disclosed and their union is audited.
- **Verification (SEAL, CR):**
  - git parentage shows exactly one seal commit;
  - the committed sample is recomputed from the formula and matches;
  - the first adjudication session is logged after the sample commit.

### O2: frozen adjudicator configuration; no silent re-runs (Reviewer A MF2)

- **Frozen in the seal commit, before the first session:**
  - the adjudicator model id and version;
  - the prompt template and its digest;
  - the tool settings and input rendering.

  They are identical for every session: A′, B′ and reserve.
- **Changes:** any change needs a recorded operator decision, and every fixture is then re-adjudicated from scratch.
- **Binding answer:** for each fixture × adjudicator slot, the answer is that of the **first logged invocation that
  produced a final message**. The only retry is the single retry of a no-answer (a session error with no final
  message).
- **Parse failures:** an adjudicator output that fails operational parsing counts as a disagreement.
- **Verification (CR):**
  - the session log shows one configuration digest throughout;
  - the invocation ordinals per slot show no earlier invocation with a final message that went unused.

### O3: entity and identifier comparison across all classes (Reviewer A MF3)

- **Scope:** the named-entity and identifier check compares the entity sets of **all** G-ROUTE4 fixtures pairwise.
  That covers the main corpus and reserve, **across every class**, among themselves and against **all** G-ROUTE3 A
  and B fixtures, as G-ROUTE3's own check did.
- **Pooling:** only the lowercase-vocabulary computation uses the per-class pool, as declared.
- **Verification (CR):** the independence tool's scope string and `INDEPENDENCE_REPORT.json` show cross-class
  comparison with 0 shared entities and identifiers.

### O4: conversation gold structure stated honestly (Reviewer A MF4)

- G-ROUTE3's fine signature is undefined for conversation. Conversation is therefore declared as having **no
  gold-structure signature**, as in G-ROUTE3. It relies on:
  - the family rules;
  - the answer-position balance;
  - the no-identical-gold rule;
  - the corpus review.
- The design's claim of a conversation fine-signature check is withdrawn.
- **Verification (CR):** the tool's scope string and the report list conversation as "no signature".

### O5: no family template treated as boilerplate (Reviewer A MF5)

- **Reporting:** for each class, the independence tool reports every boilerplate trigram that occurs in a frozen
  family template, with its pool frequency.
- **Assertion:** no trigram specific to a **single family** is boilerplate. If one is, work goes back to design
  review.
- **Verification (BP, CR):** the blueprint feasibility check and the final report both show zero single-family
  boilerplate trigrams.

### O6: the supplementary exact-value comparison is specified (Reviewer A MF6)

- **The blueprint specifies:**
  - **fields:** the structured input fields compared, per class;
  - **normalization:** casefold and strip;
  - **exclusions:** only the closed-vocabulary sets and the structural-id fields the design declares, plus numbers
    and booleans if declared in the blueprint;
  - **gate:** 0 shared values, within G-ROUTE4 (main corpus and reserve) and against G-ROUTE3.
- **The tool** implements exactly that, and the report lists the fields and value counts compared.
- **Verification (BP, CR).**

### O7: the lifecycle differential covers every module-bound call (Reviewer B MF1)

- **The differential specification** lists every in-process module-bound call reachable from launch, the table
  freeze and Phase B. At minimum:
  - `verify_table` in `phase_b_preconditions`;
  - `request_body` in `phase_a_checks` and in the collection fallback;
  - `json_digest`;
  - `load_bound_inputs` / `standard_guarded_files`.
- **Each call** is either replaced by an identical injected stub in both processes, or its per-side value is added
  to the identity-substitution table.
- **Injection:** grading-differential names are patched where they are bound (`from`-imports), and the id mapping
  satisfies `attach_semantics`'s corpus prefix check.
- **Verification (CERT):**
  - the certification report shows Phase A, the table freeze and Phase B reaching `completed` on both sides;
  - there are zero residual differences after the design's normalization.

### O8: the thresholds carry every key the forked code reads (Reviewer B MF2)

- **Contents:** the G-ROUTE4 thresholds include `false_clean_allowed: 0`, and every other key read by the forked
  `qualify`, `score` and gate code, beyond the five the design lists.
- **Test:** a test derives the set of keys the forked code reads by static reading, and asserts that the frozen
  thresholds contain **exactly** that set.
- **Verification (IR).**

### O9: sentence meanings are certified, not only their syntax (Reviewer B note N2)

- **The forked launcher enforces, and certification proves by a refusal case for each:**
  - `<binding>` equals the digest of the G-ROUTE4 freeze in force;
  - `<table>` equals the frozen table in `D/tables`;
  - `m` equals n−1, and the plain and "after integrity failure" launch forms are used exclusively as R7 §9 rules;
  - resume is byte-identical to the consumed sentence;
  - only launch sentences authorize generation;
  - the `Clear … orphan run` phase letter matches the run id's phase.
- **Declared:** the `--resume` and `--abandon` preflights make metadata-only contact with the provider (model
  receipts).
- **Resume check (optional):** `run_created.freeze_binding` equals the freeze binding in force, certified.
- **Verification (IR, CERT).**

## Carried notes (tracked; checked at the named stage)

| # | Note | Stage |
|---|---|---|
| N1 | "Canonical gold" for the no-identical-gold rule is defined in the blueprint: key order, whitespace and list order. | BP |
| N2 | The figure "P(fewer than 76) ≈ 0.001" is labelled as a projection for qualified-start cases, which is a lower bound on P(stops < 76). | IR, in the results template |
| N3 | The cross-experiment boilerplate blind spot is restated as needing about 22 or more G-ROUTE4 fixtures at a pool of about 150 or more, not "a few". | CR |
| N4 | For sampled agreed fixtures, the text is clarified: the two further adjudicators always run, and the operator is involved only on disagreement. Any disagreement within a sampled cell is also reported. | SEAL |
| N5 | Authors are declared not blind to G-ROUTE3 outputs or the diagnosis. The corpus reviewers check difficulty parity per pattern. | CR |
| N6 | The shape-disclosure audit's "no residual gap" test is backed by a frozen table mapping each validator-enforced rule to the text that discloses it. | BP |
| N7 | Whether a fixed fixture's new text replaces the old one in the pool, and whether boilerplate is recomputed, is stated. | BP |
| N8 | The maximum same-family A′–B′ Jaccard per cell is reported. | CR |
| N9 | The test proving the forked independence module's exemption lists and tokenizer are byte-identical to G-ROUTE3's is named in `G3_REFERENCE_ALLOWLIST`. | IR |
| N10 | The stale "revision 5" label in the order of work is corrected. | Done |

## Next phase (not started)

1. **Authoring blueprint:** per-cell features and their crossing, families and templates, caps, reserve
   composition, O6's comparison specification, N1, N6 and N7. Frozen by commit, with its feasibility checks.
2. **Seal commit (O1, O2):** corpus, gold, rationales and reserve sealed, and the adjudicator configuration frozen.
3. **Audit sample (O1):** derived by the frozen tool and committed.
4. **First adjudication batch,** started by the operator in chat (D10).

No G-ROUTE4 model call, implementation work or execution freeze happens before its own stage and authorization.
