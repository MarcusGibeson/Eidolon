# Eidolon research architecture — production migration specification

**Version 2.12, 2026-09-14. Status: the governing migration specification, approved by Marcus.**

**Added in 2.12** (Marcus, 2026-09-14; the G-CAND outcome):
- **G-CAND: BINDING_FAILURE, with OVER_ESCALATION also failing.** This is accepted exactly as scored under `prereg_cand.json`. The completed run is not rescored under any repaired schema or revised gold.
  - **Run:** all 564 calls completed with zero request failures, and no repair retry was needed.
  - **Passed:**
    - claim identity 1.00;
    - belief non-mutation 1.00;
    - scope preservation 1.00;
    - repeatability 1.00, with every flag decision identical across repeats;
    - main recall: adversarial 1.00, fixtures 1.00, real 0.938;
    - the separate supersession gate in both runs: all 6 must-flag cases detected with recency carried, and neither distractor flagged.
  - **Failed:**
    - binding validity: adversarial 0.946, fixtures 0.765, real 0.341, real repeat 0.667;
    - false escalation: adversarial 0.241, real 0.109;
    - therefore precision on the real corpus: 0.432.

    43 of the 45 structural rejections come from one vocabulary collision: the model wrote the recency value "unknown" in the scope time field.
  - **Disclosed pre-run prompt edit:** the approved draft never named the recency tokens (`passage_later`, `passage_earlier`), so no reply could carry them. The contract suite found this before any call, and the tokens were named before registration, together with Marcus's `resolution_needed` field.
  - **Correction:** an interim status note during the run called RT01–RT06 planted contradictions the detector missed. They are must-not-flag items, so leaving them unflagged was correct.
  - No downstream work was started.
- **The authority boundary held.** False candidates caused investigation proposals only, never a belief-state effect. Every candidate was provisional with `belief_effects: "none"`, and the belief sentinel was byte-identical after all 564 items.
- **Architectural reading.** G-CAND did not demonstrate a production-ready candidate detector. It did demonstrate:
  - high contradiction recall;
  - no belief mutation;
  - exact identity preservation;
  - deterministic repeatability;
  - successful supersession detection;
  - strong scope preservation.

  The dominant remaining failure is excessive escalation, not unauthorized belief revision. The distinction matters because the detector is intentionally provisional.
- **Over-escalation classes, kept separate.** No semantic fix is designed yet.
  1. Historical or past-state evidence escalated against a current claim.
  2. Same-topic false statements escalated, though they are not necessarily proposition-level conflicts.
  3. Partial-support and directionality cases.
  4. Navigation or non-content text.
- **Before any G-CAND rerun:**
  - **A. A binding-only schema repair:** distinct, non-overlapping vocabularies for the scope-time relationship and for passage recency.
    - Unchanged: candidate semantics, the contradiction definitions, scope semantics, the corpus, thresholds, runtime, one pair per call, uncertainty behaviour and supersession semantics.
    - Contract tests must prove that neither vocabulary is accepted in the other's field.
    - The recorded failed outputs must be shown encodable in the repaired representation without relaxing admission.
  - **B. A re-adjudication of the real candidate gold:**
    - Scope: every real item mapped from G-REL `partial_support`, plus every other real item where the result exposed a plausible mismatch between the old relation gold and candidate semantics.
    - A fresh blind labeller re-labels them under the frozen definitions, and only disagreements are adjudicated.
    - The gold is frozen and hashed before any rerun. Labels are never revised to improve a score.
  - Then work stops for review before any new live call. No G-FID, belief revision, R1, batching or optimization.
- Main and origin/main are untouched.

**Added in 2.11** (Marcus, 2026-09-14): **architectural requirements for future governed belief revision.** These are requirements only. Nothing here is implemented or wired, and none of it authorizes implementation.
- **Destination pipeline:**

  ```
  new observation
  → proposition extraction
  → support and challenge candidate generation
  → authoritative evidence binding
  → structural validation
  → scope and qualifier evaluation
  → authority, currentness and independence
  → corroboration
  → accumulated BeliefEvidenceState
  → claim-type-specific RevisionPolicy
  → BeliefRevisionDecision
  → durable BeliefLineage
  → later outcome evaluation
  → eventually, supervised learning about revision-policy performance
  ```

- **The challenge path:**

  ```
  ContradictionCandidate
  → structural validation
  → scope and qualifier assessment
  → source authority and currentness
  → source independence
  → corroboration (searching for both supporting and conflicting evidence)
  → optional independent semantic assessment
  → evidence aggregation
  → BeliefRevisionDecision
  ```

  A ContradictionCandidate is provisional. Creating it never changes:
  - belief confidence or status;
  - the evidence-policy verdict;
  - supporter or refuter state;
  - belief lineage;
  - active-belief selection.

  It is an observation and a request for investigation, not a belief event.
- **Structural validation proves only structure:** claim identity, evidence membership, required fields, and no evidence outside the authoritative OptionSet or a validated descendant path. It never implies semantic contradiction.
- **Decision vocabulary**, at least: retain, weaken, dispute, suspend, revise, supersede.
- **Principles:**
  1. **Evidence quantity is not enough.** Revision weighs:
     - the proposition relationship and scope compatibility;
     - source authority for the claim type, independence and currentness;
     - evidence quality;
     - corroboration;
     - unresolved counterevidence.

     It never reduces to counting sources.
  2. **Claim type matters.** Separate policies are planned for empirical, definitional or classificatory, predictive, procedural, autobiographical and preference claims, and normative claims if they are ever represented. There is no universal threshold.
  3. **Supersession is not ordinary contradiction.** Explicit supersession events represent an authoritative classification, a governing specification, an API contract, a law or a current standard replacing an earlier one.
  4. **Lineage is preserved, never overwritten:** the old belief, the evidence state at the time, the challenge, the revision decision, the new belief, the reason, and the triggering evidence or policy.
  5. **Unresolved states are allowed.** "No longer confident in A, not yet able to accept B" is represented as disputed, suspended or unresolved.
  6. **Hysteresis.** A meaningful evidence advantage is needed before the active belief switches. Its thresholds are to be developed experimentally and are not chosen now.
  7. **Confidence is separate from revision eligibility.** A slightly more confident alternative does not automatically replace the current belief; eligibility is a governed decision over the evidence state and policy.
- **Required behaviour, checked against the Pluto scenario (not hardcoded):**
  - One source says Pluto is not a planet: a candidate contradiction, perhaps investigation, no automatic replacement.
  - Several independent high-quality sources support the changed classification: a stronger evidence state; the belief may become disputed.
  - The governing astronomical authority formally changes the classification: authoritative supersession evidence; the revision engine may revise the active belief.
  - A later definition makes Pluto a planet again: a new supersession event; the active belief may change again, and earlier states and reasons remain in lineage.
- **Self-development is later and supervised.** Eidolon may eventually analyse her revision history and propose changes to her own epistemic policies. Such changes are supervised self-development that needs review and approval. This is not authorization for autonomous belief-policy modification.
- **G-FID stays**, as one input to this evidence pipeline, not as a prerequisite for letting one model call rewrite a belief.

**Added in 2.10** (Marcus, 2026-09-14; the G-REL2 record completed, and a change of architectural direction):
- **G-REL2, recorded in full:**
  - G5 binding validity was repaired by the schema change.
  - The pre-registered schema-friction hypothesis is CONFOUNDED overall. Removing malformed-output rejection also removed an accidental safety filter: G-REL's malformed outputs and per-field qualifier behaviour had kept some semantic overreach from being admitted.
  - The higher admitted semantic-error counts mostly expose errors already present in the model's proposals, not errors created by the schema repair.
  - G-REL2 is the preferred structural contract: it is faithful, auditable and substantially easier for the model to satisfy. It is also cheaper, as an observed side effect that is not an optimization result.
- **A new authority boundary.** Automatic belief modification must not depend directly on one model-produced refutation judgment.
  - Detecting a possible contradiction is not belief revision.
  - A model's proposal that evidence contradicts a belief is a provisional contradiction candidate: an observation and a request for investigation. It cannot weaken, refute, replace or supersede a durable belief.
  - Authority over belief state belongs to a separate, governed belief-revision mechanism that acts on validated, accumulated evidence.
  - This replaces the 2.9 "fallback", which becomes the general rule.
- **G-REF is withdrawn before any result.** Its objective, showing that a model refutation is trustworthy enough for automatic admission, is superseded.
  - The live run started under `prereg_ref.json` was stopped before it finished.
  - Its partial outputs are kept, unscored and unused.
  - The next experiment is candidate-contradiction detection, designed and pre-registered separately and reviewed before any live call.
- R1 remains blocked. No optimization or batching. Main and origin/main are untouched.

**Added in 2.9** (Marcus, 2026-09-14; the G-REL2 outcome):
- **G-REL2: gate FAIL.** Fixtures passed every rule. On real passages three rules failed:

  | Rule | G-REL | G-REL2 |
  |---|---|---|
  | G1 false refutations | 3 | 11 |
  | G2 direct-support precision | 0.901 | 0.897 |
  | G6 qualifier safety | 0.647 | 0.588 |

  - **G5 binding was repaired by the schema change:** 0.959 on fixtures and 0.974 on real passages, up from 0.816 and 0.691.
  - **The schema-friction causal hypothesis is CONFOUNDED, not cleanly confirmed.** Removing the structural failures also removed accidental rejections of semantic overreach.
  - **The original G-REL schema acted partly as an accidental safety filter.** The higher admitted-error counts are not evidence that the schema repair created those errors. Item-level comparison shows most were already present in what the model proposed:
    - 22 of 250 real items changed their proposed relation;
    - the model proposed false refutations 17 times in both versions, and false direct supports 8 times in both.
  - **G-REL2 is the preferred structural base:** it is more faithful, more auditable, and much easier for the model to satisfy.
  - **Measured side effect:** shorter structured output cut the average time per pair from about 33 s to about 17 s. This is not an optimization result, and no optimization work starts.
- **Next: G-REF, a narrow experiment on refutation semantics** using the G-REL2 structural contract as its fixed base.
  - **Hypothesis:** a model-assisted refutation can be admitted safely only when the passage explicitly expresses a proposition incompatible with the immutable target claim under demonstrated overlapping scope.
  - **Held fixed:** direct-support semantics, the corpus and gold where applicable, the runtime and model, one pair per call, and the G-REL2 schema. The zero-false-refutation rule stays.
  - G-FID is not started. After G-REF, work stops for review.
  - If G-REF establishes reliable refutation semantics, G-FID (qualifier and scope fidelity) comes next.
- **Fallback architecture**, if G-REF still produces systematic false refutations: direct support may be admitted automatically, but refutation stays provisional and review-required, and cannot automatically revise belief state.
- R1 remains blocked. No batching or optimization.

**Added in 2.8** (Marcus, 2026-09-14; the G-REL outcome):
- **G-REL: FAIL** under the pre-registered scorer, scored against gold that was independently double-labelled and adjudicated. The run was 424 calls on `qwen3.8:27b`, with no identity or runtime failure. There are three distinct failure classes:
  1. **Contract/schema failure.** G5 binding validity was 0.816 on fixtures and 0.691 on real passages. Much of it is representation friction:
     - schema values outside the allowed vocabulary, mostly a clause status written into qualifier fields;
     - attempts to represent unstated clauses where the schema had no place for them;
     - quoted spans shortened with an ellipsis.

     It is not treated as equivalent to semantic evidence hallucination.
  2. **Semantic fidelity failure.** G6 qualifier safety was 0.647 on real passages. Real modality, instruction or purpose form, question fragments and dropped conditions were admitted as direct support. Qualifier detection was 0.94 on synthetic items but 0.47 on real ones, which is a generalization gap.
  3. **Residual refutation failure.** G1 counted three false refutations on real passages. Two are clear semantic errors. The third depends on an adjudication disagreement in which the independent labeller chose refutation.
- **Improvement over G-XS on the same real pairs:**
  - all 21 G-XS false supports became zero admitted direct supports;
  - only 2 of the 19 G-XS false refutations were admitted as refutations;
  - real direct-support precision was 0.901 and recall 0.842; real refutation recall was 0.80.
- **The outside-knowledge self-report gave no observed protection:** the model never reported using outside knowledge. That field is not treated as an effective safeguard unless later evidence establishes otherwise.
- **The validator's guarantee is structural.** It checks the admission contract, not semantic entailment.
- **Next: G-REL2, a schema-only repair.** Its hypothesis: most G5 failure comes from a mismatch between the distinctions the model tries to express and the output schema, not from failing to identify the evidence relationship.
  - Only the schema and structural contract change.
  - These stay fixed: the corpus, the adjudicated gold, the relation vocabulary, the support, refutation and qualifier reasoning instructions, the model and runtime, the thresholds, batching, and one pair per call.
  - If G5 passes while G1–G4 and G6 stay materially stable, the hypothesis is supported and G-FID comes next. If G5 stays substantially below its bar, work stops for reassessment rather than stacking semantic changes onto an unresolved contract problem.
- **No optimization or batching of G-REL yet.** Its reference cost, about 33 s per pair, is far outside the budget, but semantic correctness comes first. R1 remains blocked.

**Added in 2.7** (Marcus, 2026-09-13; the G-R2 outcome and a new gate before R1):
- **G-R2: HARMFUL under the registered decision rule.** Relaxing the single-finding cardinality constraint recovers mechanism structure that the legacy singular contract suppresses, but also increases unsupported proposition generation. Multi-finding representation is therefore promising as a representation change but is not safe for integration without a stronger proposition-level support and fidelity mechanism. The result is not evidence that multi-finding representation itself is unsuitable.
  - **Positive finding:** the multi-finding arm expressed mechanism structure the legacy synthesis did not.
  - **Blocking finding:** the multi-finding arm increased unsupported proposition generation and so failed D2.
  - **Measurements** (28/28 calls parsed; both reps identical; blind labels):

    | Arm | Supported core mechanism stages | Supported mechanism findings | Unsupported |
    |---|---|---|---|
    | Legacy | 0 | 0 | 0 of 7 |
    | Multi | 5 | 3 | 5 of 30 (0.167) |
    | R1 reference | — | 5 | 9 of 42 (0.214) |

    - In the multi arm, 25 of 30 findings were supported. All 5 unsupported findings were grounded by production to passages that only partly state them: a dropped hedge, an infobox, a table of contents, and a claim combining two passages.
    - The R1 reference shows that per-passage atomic extraction does not by itself provide epistemic safety.
  - **Caveats:**
    - The pre-registered 5-stage mechanism ceiling was wrong: finding-level labels found stages in passages that the older passage labels had called summaries.
    - The TCP stages rest on a single claim about a proposed deep-reinforcement-learning controller.
    - There was one blind labeller.
- **The shared failure.** G-XS, G-R2 and the R1 reference show one semantic failure. The model treats passages as licensing propositions that they only partly state, imply only with outside knowledge, or do not state at all. It does not reliably distinguish "this passage is related to the claim" from "this passage licenses this exact proposition".
- **New gate before R1: G-REL (proposition relationship).** Designed and pre-registered harness-only; not production-wired.
  - **Its question:** what exact semantic relation holds between this passage and this immutable proposition. It does not ask whether the proposition is true.
  - **Relations:** direct_support, partial_support, explicit_refutation, scope_or_condition_difference, irrelevant, ambiguous.
  - **No naked labels.** Every non-irrelevant assessment binds:
    - the immutable claim and the assessed claim clause;
    - an exact evidence span;
    - qualifier compatibility (modality, quantifier, population, condition, polarity, time, units);
    - whether the passage licenses it directly or it needs outside inference.
  - **Refutation is strict.** Explicit refutation requires an incompatible proposition under overlapping scope. A same-topic falsehood is not a refutation, and a same-topic truth is not support.
- **G-FID is now a dependency of the proposition-relationship layer**, while staying separately measurable.
- **R1 stays blocked until:**
  1. the value of richer representation is established (G-R2 partly demonstrates it);
  2. proposition-level support and refutation are trustworthy on real passages (G-REL);
  3. qualifier and scope fidelity is demonstrated (G-FID);
  4. the resulting assessor has a measured cost compatible with the episode budget, or a validated equivalent optimization exists.
- **Double labelling before promotion.** Before any redesigned assessor is promoted, a subset of its evaluation labels is independently double-labelled and disagreements are adjudicated. The subset covers especially partial support, dropped hedges, condition mismatches, inferred contradictions, derived imperatives and scope changes.
- **No optimization of the failed G-XS implementation.** The order is: correct semantics, then a trustworthy reference, then its measured runtime, and only then batching or filtering tested against that reference.
- **E1 stays on the near-term roadmap** but is not inserted while this semantic diagnosis is under way.

**Added in 2.6** (Marcus, 2026-09-13; the G-XS outcome):
- **G-XS: FAIL** under the pre-registered scorer, recorded as two independent failures (28 fixtures and 42 app-path findings, 2 reps each, `qwen3.8:27b`):
  1. **Semantic failure.** On real application passages the assessor overreaches at the proposition level: it supports or refutes from topical, hedged or boilerplate text that does not state or contradict the claim.
     - False refutations: 19 (bar 0).
     - Support precision: 0.475, against the registered 0.810 bar (own-passage VERIFY).
     - The false sets repeat across successful reps.
  2. **Cost failure.** The unbatched reference makes one call per finding × other source (about 30 calls per topic), which is well outside the 300 s episode budget.
     - Combined retrieval + replayed pipeline + XS, from the clean rep: XS mean 469 s, total mean 604 s; 2 of 7 topics fit within 300 s.
     - This combined figure is a capacity estimate, not a measured end-to-end runtime on the same evidence.
- **What passed:**
  - immutable claim text, digest and finding identity;
  - OptionSet and evidence containment;
  - the 27/27 contract suite;
  - fixture semantics (all 8 types, both reps);
  - supporter and refuter recall (1.0 everywhere);
  - deterministic labels whenever calls succeeded.
- **Consequence.** The tested three-way assessor (supports / refutes / unclear) is unsuitable, in its current form, as the authoritative cross-source assessor on real application passages. It is not repaired, batched, parallelized, compressed or otherwise optimized before its assessment semantics are redesigned.
- **R1 is now gated by two separate questions:**
  1. Does multi-finding representation materially improve extraction and reasoning? (G-R2, next)
  2. Can a proposition-level cross-source assessor be designed that is trustworthy on real passages? (the G-XS redesign, future)
- **G-R2 stays a narrow isolation experiment.**
  - Same frozen offers, same authoritative OptionSets, same production runtime and configuration.
  - No A3, O3 or C1, and no change to the cross-source assessor, the composer or the evidence policy.
  - Only the synthesis representation changes, from the singular-finding contract to a bounded multi-finding contract.
  - It is evaluated with the existing direct grounding and independent blind labels, never with the failed G-XS assessor.
  - After G-R2, work stops for review before R1 is built.
- **Future G-XS redesign (noted, not implemented):**
  - Richer relations: direct support, partial support, explicit contradiction, scope or condition change, irrelevant, ambiguous.
  - Exact evidence spans and qualifier overlap.
  - Adversarial cases in which a passage makes true or false statements about the same topic without supporting or refuting the target proposition.

**Added in 2.5** (Marcus, 2026-09-12, while G-XS ran; roadmap only, no gate outcome recorded here):
- **G-R2 moves ahead of R1.** After the G-XS review and before R1 is implemented, run the narrow G-R2 experiment: multi-finding synthesis in one call, on the same frozen offers and the production `qwen3.8:27b` runtime.
  - If it materially improves mechanism extraction without increasing unsupported claims, that result decides whether R1 is still necessary or should be simplified.
  - G-R2 is no longer only an optional later parity check.
- **E1 joins the near-term architecture-validation roadmap:** a matched comparison of the full system against a minimal governed agent with identical tools, authority and budgets, plus oracle-evidence ablations. It does not interrupt the migration.
- **A future atomic-claim fidelity gate (G-FID).** Conditions, quantifiers, populations, units and time scope must survive decomposition into atomic claims.
  - The 20-word bound is a transport limit, not a semantic one; a claim that loses a qualifier is a different claim.
- **G-XS runs unchanged as pre-registered.** Its relation vocabulary (supports / refutes / unclear) and thresholds are not changed mid-run.
  - Its known limits are reported with its result: partial support and scope change collapse into unclear, and lineage is page-level.
- **Helper defects outside the research path** are recorded separately and not fixed on this branch.

**Added in 2.4** (experimental-record repair and G-RETRY, Marcus, 2026-09-12):
- **Runtime-model deviation.** The first live runs of C0/C1 and G-RETRY used isolated data directories that silently resolved `qwen2.5:7b` instead of the registered `qwen3.8:27b`.
  - Their behavioural verdicts are invalid as production-model verdicts.
  - The runs and their hashes are kept as deviation evidence, not deleted or rewritten.
  - The model-free contract and parity evidence from those gates stays valid.
  - Harness runs now receive only the production local-model settings, verify the complete resolved configuration before any measured call, fail closed on any model but `qwen3.8:27b`, and record the configuration and the Ollama state.
- **The reruns on `qwen3.8:27b` are the authoritative behavioural results.**
  - **C0/C1: MIXED / NO DETECTABLE EFFECT** (E7). Not integrated; the cap stays 3.
  - **G-RETRY: PASS** and integrated (`ddd1577`).
- **G-COST: PASS WITH QUALIFICATION** (§6). Full budget viability stays unresolved until cross-source assessment and the D7 composer exist and are measured. No optimization is authorized.
- **Retrieval reliability.** 11 of 14 G-COST live retrievals reached the source-failure limit. This is recorded as an observation and not addressed on this branch.
- **Step status:** G-N1, G-INV, G-SCHEMA and G-RETRY passed; G-COST passed with qualification. Nothing further is enabled.

**Added in 2.3** (after G-SCHEMA passed):
- **Two versions, two contracts.** The history contract version (`bounded_research_history.CONTRACT_VERSION`, `v2503.3`) keeps describing the legacy history-record and export contract, and does not change. `finding_schema_version` versions the multi-finding research representation and is present only on a report that uses that representation.
- **Legacy reports get no migration metadata.** `finding_schema_version`, `synthesis_path` and any equivalent field are never added to legacy reports for consistency. Keeping their keys, digests, projections and bytes unchanged is intentional. A report without `finding_schema_version` is, by contract, the legacy single-finding representation.
- **Boundaries established by G-SCHEMA** are recorded in §7a and stay in force until a later gate changes one explicitly.

**What the approval covers:**
- **Implementation may begin, narrowly and behind gates**, starting with the behaviour-neutral list refactor (G-N1).
- **After each gate passes, work stops** so the actual diff and the gate evidence can be reviewed before the next step is enabled.
- **Basis of the review:** Marcus reviewed the v2 contents and the consistency-review results as reported in the session, not a rendering of the published page. This file is the governing text.

**Added in 2.1:**
- the claim-immutability invariant for cross-source assessment (Layer 3, step 5, and G-XS);
- fail-closed failure semantics for the mechanism path (§3a);
- the judge's 700-character bound, frozen for the whole migration (Layer 5).

**Added in 2.2** (Marcus's six tightenings, made before G-RETRY ran):
- **Blocking vs measuring.** Which conditions block admission and which only measure is now stated explicitly (§3b), and D1 is reworded to match.
- **Whole-answer assessment.** The frozen 700-character judge stays for comparison, and a whole-answer assessment is required before promotion (G-WHOLE).
- **G-XS recall.** G-XS must recover known supporters and refuters, not only avoid false refutations.
- **Early cost probe.** The reference execution pattern is cost-probed before R1 is built (G-COST), and batching is evaluated against the reference.
- **G-RETRY scope.** The full-set retry applies to findings-only runs except demand, which keeps the one-passage retry (D4).
- **Demand milestone.** The original demand trial is tracked as a separate acceptance milestone (§9, M-DEMAND).

**Nothing beyond the gated steps is authorized.**

The production freeze still applies. A3, O3, C-singleton, the date fallback, the multi-finding machinery and the offer-cap change stay out of the repo until the gates in §6 pass. Every repo change needs Marcus's approval before it is pushed.

**What v2 changes from v1:**
- D1–D6 are recorded as approved, with Marcus's qualifications, and D7 is added.
- Findings from a design-only consistency review against the source are incorporated (§8).
  - The most important: R1, as tested, cannot produce corroboration or grounded refutation.
  - A cross-source assessment component and its blocking gate G-XS are therefore added.

---

## 0. Scope and standing principles

**In scope: the mechanism route of the findings-only path.** That means final-phase synthesis with no `requested_result_count`, and `requested_relation(objective) == "mechanism"`. "How does X work" objectives take this route (`research_evidence_policy.py:754`), and every experiment measured it.

**Stays on today's single-finding path in v1:**
- **Other findings-only objectives,** including "why" questions (`explanation`, which is depth-requesting but untested).
- **The demand single-dimension path** (`objective_shape == "single_candidate_dimension"`; D4). It uses the same findings-only prompt today, so routing must exclude it explicitly — for R1 and for every other change made on the shared findings-only path.
- **Candidate discovery and opportunity synthesis:** unchanged.

**Principles, unchanged:**
- **No loosening.** Never loosen an evidence gate or pad the corpus with weaker sources; fix observations and modelling. Evidence behind a gate is not automatically evidence lost.
- **One change at a time.** Each validation changes one semantic judgment; a gate passing never promotes two things at once.
- **Content-free receipts.** Receipts carry codes, counts and digests only, never claim text, passages or URLs. The report may show finding text, as today.
- **Measurements never refuse; requirements are named.** Every condition is either a blocking requirement or a report-only measurement, and §3b lists which. The evidence policy and the answer judge stay report-only (D6).
- **No thinking mode.** With JSON it returns an empty response; without JSON one call takes about 842 s against a 300 s budget.
- **"Supported" means grounded, model-judged support, not verified truth.** Grounding proves the passage was offered and observed and that the claim digest matches. Whether the passage supports the claim is still a model judgment (`semantic_support_verified: False`), and the report must keep saying so.

---

## 1. What the experiments earned

| # | Result | Evidence | Status |
|---|---|---|---|
| E1 | Thinking harder is not the fix | One call takes 842 s against a 300 s budget; JSON output fails | Rejected |
| E2 | Observation defects are real and fixable without loosening | Date fallback: 27/27 dates correct, 0 false; 6 sources rescued; end to end, mechanism passages 15→29 and stages 15→19 | Candidate (G-DATE) |
| E3 | Excerpt construction loses most of the mechanism | A3: held-out recall 0.342→0.729, precision 0.186→0.340. It used about 14% more characters under the same cap, so it is not "same budget". Captures used `create_session` | Candidate (G-A3) |
| E4 | Offer ranking loses mechanism | O3: 9/40→15/40 mechanism passages; core-stage recall 0.347→0.820; about 12% more characters | Candidate (G-O3) |
| E5 | Source selection works on metadata only; relevance is full-page | An offline replay reproduced selection on all 7 topics | Structural fact |
| E6 | URL document-form words misclassify publishers | "guide" and "review" misclassify dn.org and IJCOPE. "best" and "ideas" are retained; "guide" is a removal candidate | Measured; change deferred |
| E7 | The 3-passage cap constrains exposure and use, but raising it alone is not enough | C0/C1 on `qwen3.8:27b`: exposure 4→28, mechanism cited 4→8, grounded mechanism 0→6, unsupported findings 0→0; better on 3 of 7 topics and worse on none, below the 4-of-7 bar; the finding largely unchanged on most topics. **MIXED / NO DETECTABLE EFFECT.** The earlier FAIL (grounded mechanism 0→0, unsupported findings 8→10) came from an invalid `qwen2.5:7b` run (2.4) | Not harmful and sometimes useful, but not sufficient alone. Not integrated; the cap stays 3 (G-CAP) |
| E8 | The one-finding / exact-claim contract is the acceptance bottleneck | C0/C1 on `qwen3.8:27b`: richer grounded mechanism evidence, while the single finding still compresses it into a generic one-line claim on most topics | Earned |
| E9 | Atomic multi-step extraction works | PASS on TCP and mRNA; exact TCP replication REPLICATED; 0 invented, all steps grounded | Earned |
| E10 | One passage may yield several findings | TCP passage → 3 atomic steps; Van Jacobson → 4 | Earned |
| E11 | Stage-less findings belong in context | PASS on all 8 criteria; TCP precision 0.625→1.0, judge partial→complete | Earned |
| E12 | A persistent stage vocabulary is unnecessary | Winner C won through its flag plus ordering, not its vocabulary or clustering | Earned |
| E13 | A per-finding transient role deliberation is enough | C-singleton HOLDS on all 8 criteria. Precision 0.858→0.794 vs C; order 0.874→0.895; calls 64–271→13–29 | Earned |
| E14 | Clustering's only real contribution was suppressing paraphrased summaries | Photo residual 0.8→0.533 | Open (X-SUM) |
| E15 | Causal ordering is imperfect | TCP order 0.375; GPS control 1.0→0.0 | Open (X-ORD) |
| E16 | The frame word "works" is not a general cause | Q0 vs QE: no effect. QE vs QS: retrieval changed on 7 of 7 topics with no yield change | Earned: no query-word purification |

**Evidence limits:**
- The topics are 7 held-out "how X works" subjects plus TCP and mRNA as development topics.
- Counts per topic are small, and results are sensitive to the draw.
- The model is deterministic at temperature 0.
- The excerpt, offer and date harnesses captured through `create_session`, so "research" leaked into their terms.
- **Every harness judge result was bounded to the first 700 characters of the answer.** The harnesses called `judge_answer_quality`, which truncates at `_clean(finding, 700)` (adapter `:549`), so judge levels for longer composed answers saw only their opening.
- **R1 was tested with same-passage verification only** (§8, finding 1).
- **Mechanism success is not demand success.** Nothing here shows that Eidolon can evaluate SaaS demand, competition and feasibility; that is M-DEMAND (§9).

---

## 2. The pipeline as built (main `03aa99a`)

```
plan_public_search_queries (bounded_research_reasoning)   evidence terms = query tokens
  → search → candidates
  → adapter.observe                                        governed_public_web_research_adapter.py:739
       relevance = matched terms in full page / min(6, n)  :777-779
       machine-readable dates → derive_source_freshness    :789-796
       excerpt = _focused_excerpt(visible, terms, 12)      :847
  → select_citable_evidence (policy, receipt rows only)    bawr:1718 → research_evidence_policy:1146
  → adapter.synthesize                                     :861   (deadline = 300 s − time already spent)
       per-document budget max(320, min(2400, 7200//n))    :888
       passage_options(cid, joined excerpt), first 3       :912-928 · rca:129
       prompt: "Return at most one finding";              :938-966
               each assessment's claim = the finding summary; one assessment per offered source
       JSON-repair retry: first fitting passage per source :1069-1115
               (keeps its first-pass passage_index)
       assess_source_claims (grounding)                    :1127-1131
  → _complete_finding_citations                            bawr:274 / :1733
  → validate_research_synthesis (enforcing)                bounded_research_reasoning:1703 / bawr:1759
       findings path: ok if ≥1 row admitted; rows → reasonable_inferences ("inference");
       rows cut at 8 before counting (:1753, :2263); title required (:1772); duplicate titles rejected
       rendered: "Cited source interpretations (not independently verified)"
  → model_assessed_conclusion (demand only, enforcing)     rca:312 / bawr:1763
  → _judge_answer_quality (report-only; input ≤700 chars)  bawr:372 / :1784 · adapter:538-580
  → _evaluate_evidence_policy (report-only)                bawr:339 / :1789
  → training capture (if argument OR training policy)      bawr:925 / :1823
  → _surface_grounded_refutations                          bawr:223 / :1875
  → report status; history projection                      bawr:1908 · bounded_research_history:150/:455
```

**The six single-finding sites:**

| Site | Location | Current assumption |
|---|---|---|
| Synthesis contract | adapter `:964`, `:957` | At most one finding; every assessment's claim equals its summary |
| Citation completion | bawr `:296` | Returns `{}` unless exactly 1 finding |
| Refutation surfacing | bawr `:239` | Returns 0 unless exactly 1 finding |
| Evidence policy | bawr `:346` | `findings[0]` only |
| Answer judge | bawr `:384` | `findings[0].summary` only, truncated to 700 characters |
| Demand gate | rca `:321` | `finding_not_singular`; any assessment with a different claim denies |

`architecture_outcome_evaluation.py:43` belongs to a different subsystem and is out of scope.

**Report readers bound to the single shape:**
- `bounded_research_history` projects `evidence_policy_evaluation` (`:455`) and `citation_completion` (`:150`) as single mappings with fixed fields.
- `conversational_research_actions` counts `reasonable_inferences` and `unresolved_disagreements` (`:305-306`, `:596`). That count is already the right semantics for per-finding disagreement rows.

---

## 3. Target architecture

### Layer 1 — Evidence acquisition and observation

| Component | Production today | v1 decision | Candidate | Gate |
|---|---|---|---|---|
| Retrieval and query construction | `plan_public_search_queries` | **Unchanged** (E16) | none | — |
| Search-query vs evidence-term language | One derivation | **Unchanged in behaviour.** Named as two interfaces with identical values | none; 8b9e412 unmerged | — |
| Publisher date observation | Machine-readable dates only | Unchanged until the gate passes | Visible-date fallback: publication keywords only; publication and update distinct | **G-DATE** |
| Source classification | `_PROMOTIONAL_PATH` URL words | Unchanged | "guide" narrowing (deferred); dn.org (separate) | own pre-registration |
| Admissibility | `select_citable_evidence` | **Unchanged** | none | — |
| Relevance | Full-page term count / min(6, n) | **Unchanged** | none | — |
| Excerpt construction | `_focused_excerpt` (A0) | Unchanged until the gate passes | A3 | **G-A3** |

### Layer 2 — Evidence presentation

**`OptionSet`.** A document's passage options are computed once per document per synthesis attempt into an ordered list of `{index, passage_id, text}`. Offer, grounding, extraction, verification, cross-source assessment and every retry consume the same object. This is the C0/C1 invariant made a production assertion (**G-INV**).

**Retry, current behaviour.** Identity already survives retry: retry passages keep their first-pass `passage_index`. Exposure does not: at most one passage per source is re-offered.

**Components:**
- **Ranking.** Page order, first 3 → candidate O3 (**G-O3**).
- **Cap.** An `OptionSet` parameter; the global `PASSAGE_OPTION_LIMIT` stays because `research_evidence_directions` bound it at import. The value stays **3** until **G-CAP** passes under the multi-finding contract (E7).
- **Budgets.** The global 7200 and the per-document `max(320, min(2400, 7200//n))` are unchanged. Characters and tokens offered are reported per source; any candidate consuming more is compared at matched consumption.
- **Retry semantics.** A retry changes format only and carries the same `OptionSet` (**G-RETRY**).
  - This applies to findings-only runs **except demand**, which keeps the one-passage retry until M-DEMAND (D4, §9).
  - A shorter prompt, if ever needed, becomes a new, separately recorded attempt.
- **Document order.** Candidate, then citation ID. Unchanged.

### Layer 3 — Atomic multi-finding synthesis

**Contract.** Evidence → a set of atomic findings. Each finding has:
- `claim`: one proposition, at most 20 words, stated from its passage;
- `support`: one or more `(citation_id, option index)` references;
- `uncertainties`.

The relation is many-to-many: a passage may support several findings (E10), and a finding may be supported by several passages.

**R1 (earned; the reference implementation):**
1. **Extract.** One call per offered passage (`EXTRACT_MULTI`): zero to 4 steps; no definitions, variants, history or context; separate steps kept separate.
2. **Verify.** An independent call per step (`VERIFY`) on its own passage, returning supports, refutes or unclear. The extractor never certifies itself.
3. **Ground.** `assess_source_claims` with each step as its own claim. Semantics are unchanged: they are already claim-keyed.
4. **Deduplicate.** Exact deduplication with `normalized_claim_text`. **Duplicates merge their support references rather than dropping them.** The harness kept only the first occurrence, which discards corroboration. The harness's near-duplicate rule is not portable and does not ship.
5. **Cross-source assessment (new, untested; blocking gate G-XS).** Each deduplicated claim is assessed against the *other* offered sources' passages, so supporting and refuting evidence from other publishers can be grounded.
   - Proposed form: one call per source, listing that source's `OptionSet` and the claims extracted elsewhere. It returns, per claim, supports, refutes or unclear with an option index.
   - Rows go through `assess_source_claims` unchanged.
   - Without this step, R1 yields one supporting source per claim and **no grounded refutation at all**. That would regress the validated refutation behaviour and leave D2 unpopulated. So it is **blocking**.
   - **The two phases have distinct jobs.** Extraction grounding proves where an atomic claim came from. Cross-source assessment determines what the rest of the eligible evidence says about that claim.
   - **Claim immutability (invariant).** Cross-source assessment may change a finding's evidence state, supporters, refuters and policy eligibility. **It may never rewrite the claim.**
     - The claim text and its `claim_digest` are byte-identical before and after assessment.
     - Every assessment row binds to that exact digest.
     - If assessment suggests a claim is badly framed, the claim is rejected, or a *new* candidate claim enters through the explicit candidate path: extraction, verification and grounding, under its own digest.
     - Wording is never adjusted until the evidence agrees.
     - This is enforced by an assertion, and a violation is a hard failure (G-XS).

**R1 is the reference behaviour, not a committed execution pattern.** One model call per passage, per claim and per classification may be too expensive on the local 27B model. Its cost is probed before R1 is built (**G-COST**). Batched variants — several passages per extraction call, several claims per verification or classification call — are candidates, measured against R1's outputs. A batched variant replaces a reference stage only when it matches the reference on G-COST's pre-registered metrics.

**R2 (untested):** one synthesis call returning N findings. It may replace R1 only after parity (**G-R2**, optional).

**Failure accounting.** Every extraction, verification and assessment call gets at most one repair retry over the identical input. Failed calls are counted and persisted per run; the harnesses did not persist them.

**Bounds:**
- At most 4 steps per passage; at most 6 citation IDs per finding.
- An explicit finding cap, **truncated and reported**. It replaces the validator's invisible cut at 8.
- `qwen3.8:27b`, thinking off, temperature 0.0.

### Layer 4 — Per-finding epistemic semantics

**Every property is judged per finding, on that finding's own claim and citations. Nothing is borrowed across findings.**

**Admission states (D1, D2):**

| State | Condition | Where it goes |
|---|---|---|
| **Supported** | ≥1 grounded supporting passage for this exact atomic claim, and no grounded refutation | Eligible for the explanation. The evidence policy's verdict — for example, whether this claim shape would need several independent publishers — is **measured** per finding and does **not** block in v1 (D6, §3b). On the atomic path each step carries its measured policy state as a visible fixed-code annotation, so a claim shown despite a failed measurement is never presented as policy-admitted |
| **Disputed** | Grounded support **and** grounded refutation | Kept out of the causal chain. Presented separately, with supporters and refuters listed apart. Never resolved by counting citations |
| **Unsupported / unresolved** | No grounded support: unverified, ungrounded, or only unclear assessments | Diagnostic and research state only (counts, digests). **Never asserted answer content** |

**Properties:**

| Property | Per-finding definition | Answer-level meaning |
|---|---|---|
| Grounded support | `grounded_supporting_citation_ids(assessments, claim)`, from own-passage verification plus G-XS rows | Decides Supported |
| Grounded refutation | `grounded_refuting_citation_ids(assessments, claim)`, from G-XS rows (and own-passage VERIFY "refutes") | Decides Disputed. One entry per disputed finding in `unresolved_disagreements`; the refuter never joins the finding's citations |
| Citation completion | `_complete_finding_citations` per finding; `model_payload` preserved | Per-finding counts |
| Corroboration / independence | `independence_summary` over the finding's grounded supporters | Never pooled across findings. Measured, not blocking (§3b) |
| Cross-finding contradiction | **Not defined in v1** | Recorded as a known gap; G-WHOLE reviews contradictions within an answer |
| Uncertainty | The finding's `uncertainties` | Limitations stay a separate list |
| Evidence currency | Citation conditions over the finding's cited sources | Measured, not blocking (§3b) |
| Evidence policy | `evaluate_policy` once per finding; one policy per run | A per-finding list; `enforced: False` unchanged (D6) |
| Enforcing admission | `validate_research_synthesis` per finding. The claim replaces the title; the reported cap replaces the invisible cut at 8 | Report ready if ≥1 finding is admitted (unchanged rule) |
| Demand gate | Unchanged in v1 (D4) | — |

**Each single-finding site, rewritten:**

| Site | Target |
|---|---|
| Synthesis contract | R1 on the mechanism route; legacy call everywhere else |
| Citation completion | A per-finding loop; with one finding, identical to today |
| Refutation surfacing | One disagreement entry per disputed finding |
| Evidence policy | A per-finding list plus run-level pool fields |
| Answer judge | Judges the composed explanation (Layer 5) |
| Demand gate | Unchanged; its all-assessments-match rule remains |

**Report schema.** With one finding, the report and both history projections are byte-identical to today (**G-N1**). With more than one:
- `evidence_policy_evaluation` keeps its run-level fields (available admissible evidence, authority states, source selection) and gains `finding_evaluations: [...]` plus aggregate counts.
- The finding-verdict fields are not duplicated at the top level.
- `bounded_research_history` gains bounded, fixed-code projections for the new lists.
- **Versioning (2.3, G-SCHEMA).** The multi-finding representation is versioned by `finding_schema_version` (`v2731.4`), present only on a report that uses it. The history contract version (`CONTRACT_VERSION`, `v2503.3`) keeps describing the legacy history-record and export contract and is **not** bumped: it is embedded in every history record and export, so a bump would change every legacy record although G-SCHEMA is behaviour-neutral.

### Layer 5 — Explanation construction (mechanism route only)

```
Supported findings (Disputed and Unsupported excluded, per D1/D2)
  → C-singleton  C's exact flag prompt per finding, as a one-member group; name discarded, never persisted;
                 anything but true → context
  → separation   mechanism | context   (context kept and shown)
  → cleanup      exact normalized deduplication; paraphrased-summary suppression open (X-SUM)
  → ordering     ORDER_ALL over mechanism findings; the guard drops nothing; the valid-order count is reported
  → composition  (D7) deterministic, from grounded claims only
```

**D7 — partial survival and causal linkage:**
1. **Compose from what survives.** The explanation is built from the Supported findings. The candidate mechanism is never an all-or-nothing unit; A, B and D are presented even if C failed.
2. **Ordering is not causation.** A position in the proposed order asserts sequence at most, never a causal edge.
   - A causal link appears only where a Supported finding's own grounded claim states it ("loss detection triggers window reduction").
   - The composer never writes connectives ("which causes", "then", "leading to") between separate findings.
3. **Gaps are represented, not bridged.** The answer states that adjacent steps are not asserted to be causally connected unless a step says so.
   - Where an Unsupported extracted step falls between two Supported ones in the proposed order, the answer says the intermediate connection was **not established by the researched evidence**. The unsupported step's text is never shown as content.
   - That marking is untested (**X-GAP**). Until it passes, only the general statement ships.

**The composed answer:**
- **Proposed causal order:** the mechanism steps, each with its own citations and its policy-measurement annotation (§3b).
- **Context.**
- **Disputed evidence:** supporters and refuters listed separately.
- **Limitations.**
- **The provenance disclaimer:** each step's passage was observed and judged supportive by the model; the claims are not independently verified.

No new model prose follows ordering.

**Answer judge.** It judges the composed mechanism chain against the requested relation.
- Its 700-character input bound is made explicit: the chain is bounded to the limit, and truncation is reported (`answer_quality_input_truncated`).
- **The bound stays at 700 for the whole migration.** Changing the ruler while the architecture changes would make before/after judge levels incomparable.
- Historical judge levels read as "complete, as far as the judge saw in the first 700 characters". They remain valid comparisons between arms that went through the same judge.
- The judge stays report-only; it needs at least 5 s left and at most 30 s (adapter `:555`, `:573`).

**Whole-answer assessment before promotion (G-WHOLE).** An opening-only score cannot show that a longer explanation works as a whole: the opening could improve while errors appear later. Before the atomic path is promoted, every composed answer in the G-MF runs is assessed in full.
- **Deterministic trace:** every asserted sentence maps to a Supported finding and that finding's citations. This is possible because composition is deterministic.
- **Blind hand review of the complete output:** unsupported claims, contradictory statements within the answer, and causal links the findings do not state.
- It is a promotion gate, run in the harness. It is not a run-time measurement and does not replace the frozen judge.

**Receipts.** Counts of findings extracted, verified, grounded, supported, disputed, unsupported, mechanism, context and truncated; failed calls; the valid-order count; claim digests. Never claim text.

**Training capture (D5).** The mechanism route bypasses capture **whether it was requested by argument or by `training_policy.research_enabled`** (bawr `:925`). It records the fixed status `training_capture_not_designed`. Legacy paths are unchanged.

### 3a. Failure semantics of the mechanism path (fail closed)

**Rule.** If the atomic mechanism path fails, the run ends with an explicit research failure or an insufficient-evidence result. It **never** silently falls back to today's single-finding synthesis and presents that as an equivalent success.

**Why.** A silent fallback would produce an answer and superficially successful telemetry, while hiding which architecture produced it. That would make every validation of the new path unreadable.

**Path provenance.** Every atomic-path run records `synthesis_path: atomic_mechanism` together with `finding_schema_version`. Legacy reports carry neither, by design (2.3): a report without `finding_schema_version` is, by contract, the legacy single-finding representation, and legacy bytes are never changed to add provenance. Routing (§0) is decided **before** synthesis. A run routed to `atomic_mechanism` can end in only two ways:
- an atomic-path result;
- an atomic-path failure.

**Run-level failure codes** (fixed vocabulary; the report status is insufficient evidence or failed, never ready):

| Code | Cause |
|---|---|
| `mechanism_path_deadline_exhausted` | The synthesis deadline was reached before composition |
| `mechanism_path_extraction_failed` | No passage produced a parseable extraction after its repair retry |
| `mechanism_path_no_supported_findings` | Extraction ran, but no finding reached the Supported state (an insufficient-evidence result, not a technical failure) |
| `mechanism_path_stage_failed:<stage>` | A whole stage (verification, grounding, cross-source assessment, classification, ordering, composition) could not complete for the run |

**Per-item failures inside a stage** are counted and persisted per run. They never produce positive evidence:
- **A failed extraction call:** that passage yields no findings.
- **A failed verification call:** the finding is Unsupported.
- **A failed cross-source call:** that source contributes no assessments. The report counts it, and the answer's limitations state that the findings could not be checked against that many sources.
- **A failed or unparsed classification flag:** the finding goes to context (C's rule: anything but true).
- **A failed ordering call:** the guard keeps every finding in its original order, and a zero valid-order count is reported.

**A future fallback, if it is ever wanted,** needs a separate decision and must have all four of:
- an explicit fallback code;
- provenance naming the path that produced the answer;
- separate metrics;
- no representation as a successful atomic-path run.

G-MF requires **zero silent fallbacks**. Path provenance must be present on every run.

### 3b. What blocks and what only measures

Every condition is exactly one of three kinds:
- **Blocking:** its failure keeps content out of the answer.
- **Measured:** recorded for the operator; its failure never removes content.
- **Promotion gate:** blocks promoting a component, never a run.

| Condition | Kind | When it fails | Scope |
|---|---|---|---|
| Observed citations and a claim (`validate_research_synthesis`) | Blocking | The row is rejected and does not appear | All paths, unchanged |
| Option-set identity and passage provenance (grounding) | Blocking | The assessment is rejected (disqualifying) | All paths |
| Grounded support for the exact atomic claim (D1) | Blocking | Unsupported: never asserted | Atomic path |
| Grounded refutation of the exact atomic claim (D2) | Blocking for the causal chain | Disputed: shown separately, never in the chain | Atomic path. On the legacy path it is surfaced as a disagreement, unchanged |
| Demand gate (`model_assessed_conclusion`: independent lineages, currency, stance, claim binding) | Blocking | The demand inference is refused | Demand, unchanged |
| Evidence-policy conditions: corroboration, publisher independence, currency, authority, producer independence, `grounded_refutation` as a policy condition, `would_admit` | **Measured** (D6) | Recorded per finding. **The finding can still appear.** On the atomic path each step shows its measured policy state as a fixed-code annotation. On the legacy path the answer is unchanged and the state is in the receipt only, as today | All paths |
| Answer judge (700 characters, frozen) | Measured | Recorded | All paths |
| G-WHOLE, G-XS, G-MF and the other §6 gates | Promotion gate | The component is not promoted | Harness |

**Consequence.** No statement in this specification guarantees that a claim in an answer passed the evidence policy. Moving any measured condition to blocking is a separate decision with its own experiment (D6).

---

## 4. Not changed by this design

- Evidence policy conditions and thresholds.
- `select_citable_evidence`.
- The relevance formula.
- Query planning.
- `_PROMOTIONAL_PATH`.
- Content-free receipts.
- The model and thinking-off setting.
- The candidate-discovery and opportunity contracts.
- The demand path, including its one-passage repair retry.
- Non-mechanism findings-only objectives stay off the atomic path. Their repair retry does change with G-RETRY.
- The report-only status of the policy and the judge.
- The session budget (D3).

---

## 5. Decisions (approved by Marcus, 2026-09-12)

| # | Decision |
|---|---|
| **D1** | **Grounded support is the minimum blocking requirement for the explanation. The evidence policy measures whether a claim shape would need more, and in v1 that measurement does not block (D6, §3b).** Three states: Supported (eligible), Disputed (D2), and Unsupported/unresolved (diagnostic only, never asserted). Corroboration is not required universally |
| **D2** | **Disputed findings stay out of the causal chain** and are presented separately, with supporting and refuting evidence. Eidolon never silently picks the side with more citations |
| **D3** | **Measure integrated cost first. Optimize structurally. Raise the 300 s mechanism budget only if measured quality requires it, by a separate decision.** 900 s is an emergency ceiling, not a target. The reference pattern is cost-probed before R1 is built (G-COST). G-TIME must report extraction, verification, grounding, cross-source assessment, C-singleton and ordering costs; total wall-clock time; model calls; tokens; safe parallelism; and duplicated work |
| **D4** | **Demand stays single-finding in v1,** and every change on the shared findings-only path excludes demand unless it is explicitly included and tested. The refactor is list-capable with G-N1 parity, but demand generation stays singular. Demand has its own acceptance milestone (M-DEMAND, §9) |
| **D5** | **Training capture is off on the new path until explicitly designed.** A design must name which representation is training material (raw extraction, verified, grounded, policy-accepted, classified, or the ordered explanation), what provenance accompanies it, and how disputed or rejected findings are kept out of positive examples |
| **D6** | **No enforcement change in this migration.** Today's policy behaviour is preserved except where multi-finding semantics require an explicit equivalent. Any move from report-only to enforced conditions needs its own experiment and authorization |
| **D7** | **Compose from surviving findings; ordering does not assert causation.** Causal linkage must be independently supported (stated by a grounded claim) or represented as unknown. Gaps are represented, never bridged |

---

## 6. Required validation before implementation or promotion

All gates are pre-registered. Harnesses are hashed, labels are blind and hashed before scoring, objectives go through `parse_conversational_research_request`, and "undetermined" is legitimate. The pass rules are drafts that each gate's own pre-registration finalizes.

| Gate | Component | Protocol | Draft pass rule | If it fails |
|---|---|---|---|---|
| **G-INV** | `OptionSet` | Fixture test that fails loudly: offer, grounding, extraction, assessment and retry | 0 violations; the test fails on a deliberately broken build | Blocks Layer 2 |
| **G-RETRY** | Retry (findings-only, except demand) | Contract and parity differential against the previous gate, plus a live forced-retry comparison on identical evidence (`prereg_retry.json`) | Non-retry runs, first attempts, demand and policy unchanged; the retry offers exactly the first attempt's set; grounding stays inside the set; a causal witness; no new generation failures or unsupported findings | Blocks the retry change. **Outcome: PASS on `qwen3.8:27b`** (`ddd1577`): contract and parity proof against `34167e0`; live, unsupported findings 0 vs 0 and grounded support beyond passage 1 4→20. The earlier DEFERRED outcome (B2, unsupported findings 4 vs 8) came from an invalid `qwen2.5:7b` run (2.4) |
| **G-N1** | Layer 4 refactor | Stored corpus with exactly 1 finding; the existing suite (`v2501_7`, `v2502_*`, `v2731_0_4` to `v2731_2_7`) | Byte-identical reports and history projections; suite unchanged apart from known pre-existing failures | Blocks multi-finding. **Outcome: PASS** (`2ed3161`) |
| **G-SCHEMA** | Report shape, N>1 | Fixture reports with several findings through `bounded_research_history` and `conversational_research_actions` | Projections fixed-code and bounded; counts correct; content-free receipts; policy-measurement annotations present on atomic steps | Blocks R1. **Outcome: PASS** (`d8c6f57`); versioned by `finding_schema_version`, history contract version unchanged (2.3); boundaries in §7a |
| **G-COST** | Reference execution cost (D3), **early** | Harness-only, **before R1 is built**: the reference R1 + cross-source + C-singleton + ordering pipeline on replayed app-path evidence, instrumented per stage (calls, prompt and output tokens, seconds, time left at synthesis start); then batched variants compared with the reference's outputs | Costs reported per stage. A batched variant may replace a reference stage only if it matches the reference on the pre-registered output metrics (claims extracted and grounded, support and refutation states, mechanism flags) | Informs D3 and the shape of the R1 build; R1 is not built around an unmeasured execution pattern. **Outcome: PASS WITH QUALIFICATION** (2.4): on 14 replayed runs the measured reference stages take 125 s mean (42–203) in 28 calls, which fits the 300 s budget after 9–17 s of retrieval. Cross-source assessment and the D7 composer do not exist yet and are unmeasured, so full budget viability is unresolved. No optimization is authorized |
| **G-XS** | Cross-source assessment | App-path replay; claims × other sources hand-labelled blind (supports / refutes / neither), **including planted contradicting passages whose correct label is refutes**; claim text and digest recorded before and after assessment | Supports precision ≥ own-passage VERIFY's; **support recall** and **refutation recall** on labelled pairs each at or above a pre-registered bar, so answering "unclear" to every contradiction fails; the unclear rate reported per labelled class; **false refutations = 0**; **claim mutations = 0** (text and digest byte-identical; every row binds to the unchanged digest); cost reported | **Blocks R1 shipping** (refutation must not regress). **Outcome (2.6): FAIL** on two independent counts. Semantic: 19 false refutations; support precision 0.475 vs 0.810. Cost: the unbatched reference is far over budget (a capacity estimate). Immutability, containment, contract, fixtures and recall passed. The three-way assessor is unsuitable as specified and is redesigned before any optimization |
| **G-MF** | Layers 3–5 end to end | Live app path, production vs R1 + XS + Layer 5, identical retrieval (replayed); mechanism topics plus non-mechanism and demand controls; induced-failure runs (deadline, extraction, cross-source) | Supported mechanism findings up on ≥4 of 7 topics; asserted unsupported content = 0; 0 invented; judge not lower; controls byte-unchanged; **path provenance on every atomic-path run** (legacy reports stay unmarked by contract, 2.3); **zero silent fallbacks** (induced failures end in their §3a codes) | Harness-only; back to design |
| **G-WHOLE** | The whole composed answer | Every composed answer in the G-MF runs: deterministic sentence-to-finding trace, plus blind hand review of the complete output | 0 asserted sentences without a Supported finding; 0 contradictions within an answer; 0 causal links the findings do not state; unsupported claims reported | **Blocks promotion** |
| **G-TIME** | Cost (D3) | Instrumented G-MF runs: per-stage time, calls and tokens; time left at synthesis start; parallelism and duplicated work | Within the current budget, or a recorded D3 decision after optimization | D3 |
| **G-A3** | Excerpt | App objective path; retrieval captured and replayed; A0 vs A3 at **matched characters and matched tokens**; blind labels | Recall and core coverage better on ≥4 held-out topics, worse on ≤1; precision not lower by >0.05; downstream offer (production and O3) not worse | Excerpts stay A0. **The architecture is unaffected** |
| **G-O3** | Offer ranking | After G-A3; offline replay; equal count and budget | Mechanism passages and core-stage recall up; stage recall never lower | Page order stays |
| **G-DATE** | Date observation | Held-out app-path pages; every date verified by hand; selection replay plus end to end | **Zero false dates**; publication and update distinct | The fallback does not ship |
| **G-CAP** | Offer cap | C0/C1 protocol under R1 | Acceptance up; unsupported findings not increased | The cap stays 3 |
| **G-R2** | Single-call multi-finding synthesis | **Before R1 (2.5):** the same frozen offers and production runtime as C0/C1 and G-COST; the legacy one-finding call vs a multi-finding call; blind labels; pre-registered | Mechanism extraction materially better on the pre-registered measure; unsupported claims not increased | Decides whether R1 is needed as specified, simplified, or replaced. **Outcome (2.7): HARMFUL** under the registered rule. D1 held: 5 supported core stages vs 0, and 3 supported mechanism findings vs 0. D2 failed: unsupported findings rose from 0/7 to 5/30. Multi-finding representation is promising but not safe to admit with the current support semantics |
| **G-REL** (2.7) | Proposition relationship (the shared support, refutation and qualifier layer) | Adversarial fixtures plus real-passage pairs reused from the G-XS and G-R2 failures, labelled blind. One call per (immutable proposition, offered passage). The six relations, each bound to a claim clause, an exact evidence span, qualifier compatibility and a relation basis; a mechanical validator admits a relation only when those fields are consistent | Pre-registered in `prereg_rel.json` | **Blocks R1** and any redesigned cross-source assessor. **Outcome (2.8): FAIL** in three classes: contract/schema (G5 0.816 / 0.691), semantic fidelity (G6 0.647 on real passages) and residual refutation (G1: 3, one adjudication-dependent). The improvement over G-XS on the same pairs is large. G-REL2 tests a schema-only repair. **G-REL2 (2.9): gate FAIL.** G5 was repaired (0.959 / 0.974), but the hypothesis is CONFOUNDED: the old schema was partly an accidental safety filter. G-REL2 is the structural base |
| **G-REF** (2.9) | Refutation semantics on the G-REL2 base | Adversarial refutation fixtures plus the G-REL corpora with their adjudicated gold. A proposed refutation must bind the target clause, the passage segment, the proposition the segment expresses, the dimension of incompatibility, population, condition and time comparisons, and whether the incompatibility is directly stated | Pre-registered in `prereg_ref.json`; zero false refutations; refutation recall; direct support and binding stable | Fallback: refutation stays provisional and review-required. **Withdrawn (2.10)** before any result; superseded by candidate-contradiction detection and governed belief revision |
| **G-CAND** (2.10) | Candidate-contradiction detection, with no belief authority | Adversarial, G-REL fixture and real pairs, plus 10 supersession items. A ContradictionCandidate is bound to the immutable claim and exact segments, and carries incompatibility, scope, recency, uncertainty and `resolution_needed`. It is provisional, with no belief effect | Pre-registered in `prereg_cand.json`: recall ≥ 0.85, false escalation ≤ 0.10, precision ≥ 0.80, binding ≥ 0.95, identity and non-mutation = 1.00, scope preservation ≥ 0.80, repeatability ≥ 0.95; plus a separate supersession gate | Candidates stay provisional under any outcome. **Outcome (2.12): BINDING_FAILURE, with OVER_ESCALATION also failing.** Recall, identity, non-mutation, scope preservation, repeatability and the supersession gate passed. A binding-only time/recency repair and a re-adjudication of the real gold come before any rerun |
| **G-FID** (future, 2.5) | Atomic-claim fidelity | Decomposed claims vs their source passages, hand-labelled blind for dropped or altered qualifiers (condition, quantifier, population, unit, time scope) | Qualifier loss below a pre-registered bar; a lost qualifier makes a new claim, never a silent narrowing | Blocks promotion of atomic extraction. **Dependency of G-REL (2.7):** it is measured with G-REL's qualifier compatibility and remains separately reported |

**Open experiments, non-blocking and reported:**
- **X-SUM:** paraphrased-summary suppression.
- **X-ORD:** ordering reliability.
- **X-GAP:** explicit gap marking (D7). Until it passes, only the general "not asserted causal" statement ships.

**Architecture validation (near-term, outside the migration sequence, 2.5):** E1 is a matched comparison of the full system against a minimal governed agent with identical tools, authority and budgets, plus oracle-evidence ablations. It is scheduled without interrupting the migration.

---

## 7. Proposed integration order

Each step makes one semantic change and is independently revertible. Each needs its gate, then Marcus's approval, then the push.

1. **Behaviour-neutral list refactor (G-N1). This is the first implementation step.**
   - Per-finding primitives for citation completion, refutation surfacing, the policy measurement and the answer judge's claim.
   - They sit behind two named cardinality rules that reproduce today exactly:
     - `_sole_finding`: completion and surfacing act only on exactly one finding;
     - `_first_finding`: the policy and the judge read the first finding of any number. That asymmetry is recorded current behaviour.
   - The synthesis prompt, the demand gate and the report projections are untouched. A projection change is a schema change and belongs to step 4.
   - **After G-N1 passes, work stops** for review of the actual diff and the gate evidence before any behavioural change is enabled.
2. **`OptionSet` identity refactor.** No behaviour change (G-INV). **PASS** (`499723f`).
3. **Retry semantics** (G-RETRY): findings-only runs except demand. **PASS** on `qwen3.8:27b` (`ddd1577`). The earlier DEFERRED outcome came from an invalid `qwen2.5:7b` run (2.4).
4. **Multi-finding report schema** (G-SCHEMA). **PASS** (`d8c6f57`); boundaries in §7a.
5. **Reference cost probe (G-COST)**, harness-only, before R1 is built; batched candidates measured against the reference. **PASS WITH QUALIFICATION** (2.4): cross-source assessment and the composer are still unmeasured, and no optimization is authorized.
   - 5a. **G-R2 (2.5)**, harness-only, after the G-XS review and before R1 is implemented. Its result decides whether step 6 builds R1 as specified or a simpler form. **Outcome (2.7): HARMFUL** under the registered rule, with the positive mechanism finding recorded.
   - 5b. **G-REL (2.7)**, harness-only: design, pre-register, and review before any live run; then measure its semantics and cost. Nothing is optimized before its semantic reference passes. **Outcome (2.8): FAIL.** Next is G-REL2, a schema-only repair; after it, either G-FID or a stop for reassessment. **G-REL2 (2.9): FAIL.** G5 was repaired; the hypothesis is confounded.
   - 5c. **G-REF (2.9)**, harness-only: refutation semantics on the G-REL2 base, pre-registered before implementation. Afterwards, work stops for review. The next step is then G-FID if refutation is reliable, or otherwise the provisional-refutation fallback. **Withdrawn (2.10):** its run was stopped unscored. The next experiment is candidate-contradiction detection.
   - 5d. **G-CAND (2.10)**, harness-only: candidate-contradiction detection with no belief authority. **Outcome (2.12): BINDING_FAILURE**, with OVER_ESCALATION also failing; the authority boundary held. Before any rerun come the binding-only time/recency repair and the re-adjudication of the real gold, then review.
6. **R1 with cross-source assessment** on the mechanism route, in the execution pattern G-COST supports (G-XS, G-MF, G-TIME). **Gated (2.6)** by two separate questions: G-R2's result on multi-finding representation, and a redesigned, trustworthy proposition-level cross-source assessor. **Blocked (2.7)** until all four R1 prerequisites hold: richer representation shown to add value, G-REL, G-FID, and a measured compatible cost.
7. **Explanation construction** (Layer 5, D7): validated in the G-MF runs, promoted only after G-WHOLE, and shipped as its own step.
8. **Candidates, each when its gate passes:** G-DATE, G-A3, G-O3, G-CAP.

If any step-8 component fails, the architecture stands and only that component returns to design. **The return point for the original objective is M-DEMAND (§9).**

### 7a. Migration boundaries established by G-SCHEMA

These boundaries stay in force until a later gate changes one explicitly (Marcus, 2026-09-12).
- **Claim-dependent measurements stay per finding.** Authority states and tiers, claim-source relationships, available admissible evidence, and every other policy field that depends on the finding's claim-source relationship live in that finding's entry. Only `RUN_LEVEL_EVALUATION_KEYS` are stated once. None is promoted to run-level state.
- **The Markdown export refuses multi-finding reports** (`multi_finding_report_export_not_migrated`) until its Layer 5 semantics are designed.
- **Chat review and count semantics are unchanged.** `conversational_research_review` and `_research_report_message` keep counting rows as today. What those counts mean for an atomic explanation is decided with Layer 5 (steps 6–7), before any multi-finding report reaches chat.
- **The answer judge is unchanged.** It reads the first finding, and its 700-character bound stays frozen.
- **Legacy reports carry no path provenance or migration metadata** (2.3).
- **The multi-finding report builder stays unwired.** `_multi_finding_report_fields` has no production call site.

---

## 8. Consistency review against the source (design-only, 2026-09-12)

| # | Checked | Finding | Resolution in v2 |
|---|---|---|---|
| 1 | Grounded support and refutation vs R1 | Production's single call assesses **every offered source** against the claim (`assessment_cap` = source count, adapter `:933`); that is where corroboration and refutation come from. R1 as tested verifies each step **only against its own passage** (`mech_multistep.verify_and_ground`), and the harness dedupe kept only the first occurrence | Cross-source assessment added (Layer 3, step 5); **G-XS is blocking**; dedupe merges support |
| 2 | Six single-finding sites | All six confirmed; `architecture_outcome_evaluation.py:43` is unrelated | Unchanged |
| 3 | Validator | Findings path is ok with ≥1 admitted row, and no recommendation is needed (`:2081-2086`). Rows cut at 8 **before** counting (`:1753`, `:2263`), so truncation is invisible. Title required; duplicate titles rejected; rows are "inference"; rendered disclaimer "not independently verified" | Reported cap; the claim stands in for the title; the disclaimer is kept in Layer 5 |
| 4 | Synthesis schema and retry | Retry keeps the first-pass `passage_index` (identity holds) but re-offers at most one passage per source (exposure shrinks). The demand path uses the same findings-only prompt | G-RETRY; explicit routing that excludes demand and non-mechanism objectives from R1. **Correction (2.2):** the retry change itself sits on the shared findings-only path, so it now explicitly excludes demand, which keeps the one-passage retry |
| 5 | Citation completion | Single-finding only; preserves `model_payload`; `MAX_FINDING_CITATION_IDS` = 6 | Per-finding loop; G-N1 |
| 6 | Policy | `evaluate_policy` judges the verdict over the finding's own citations, with pool fields reported separately; `enforced: False` | Per-finding list plus run-level pool fields; D6; blocking vs measured stated in §3b (2.2) |
| 7 | Report readers | `bounded_research_history` projects `evidence_policy_evaluation` and `citation_completion` as single mappings; `conversational_research_actions` counts rows | G-SCHEMA; contract version bump |
| 8 | Answer judge | Input truncated at 700 characters (adapter `:549`); needs ≥5 s left, 30 s maximum. **Harness judge results were bounded the same way** | The bound made explicit and truncation reported; caveat added to §1; G-WHOLE added before promotion (2.2) |
| 9 | Demand | `model_assessed_conclusion` requires one finding, and any assessment with another claim denies | Unchanged in v1 (D4); routing excludes it; M-DEMAND tracks the demand objective (2.2) |
| 10 | Runtime budget | The synthesis deadline is 300 s minus the time retrieval already spent; the judge needs ≥5 s | G-COST before R1 (2.2); G-TIME measures the time left at synthesis start and per-stage cost (D3) |
| 11 | Training capture | Enabled by argument **or** `training_policy.research_enabled` (bawr `:925`) | The mechanism route bypasses both, with a fixed status (D5) |
| 12 | Routing | `requested_relation` maps "how…" and "works" to `mechanism` (`:754`); "why" maps to `explanation` (untested) | R1 only for `mechanism` in v1 |

---

## 9. Acceptance milestones

The migration exists to produce a usable research system. Gates prove components; milestones prove the system does what it was built for.

**M-MECH — mechanism research v1.** G-MF, G-TIME and G-WHOLE pass on the mechanism route, and the step-7 explanation is promoted. This is the controlled testing ground, and it is where this migration's evidence comes from.

**M-DEMAND — the original objective (tracked return point).** Eidolon evaluates SaaS demand, competition, implementation dependencies and free-tier feasibility for real candidates. That is the seven-domain demand trial that started this work.
- **Success at M-MECH does not demonstrate M-DEMAND.** Demand has different semantics: independence requirements, customer evidence, promotional and vendor restrictions, currency and multiple-publisher requirements.
- **Return point:** after M-MECH, or earlier if Marcus directs.
- **Prerequisites:**
  1. diagnose the pre-existing `v2730_demand_support` failure, which fails on untouched `03aa99a` and is kept off the migration branch;
  2. decide, from a concrete demand use case, whether demand benefits from atomic findings (D4) and from the full-set repair retry;
  3. re-run the demand trial with the architecture's observation and presentation fixes under the unchanged demand gates.
- **Acceptance** is the demand trial's own pre-registered criteria, not the mechanism gates.
