# G-CORROB1-R2 second adversarial preregistration audit

**Audit basis:** checkpoint `e1d9fed`, r1 audit SHA-256
`DD9E6F950EA209100757398A408272DAE2DC711E111150798591EC2883AEEFB0`,
and the r2 design artifacts in this directory.

**Execution status:** no model call, runner, scorer, pilot, execution freeze,
installation, authorization, belief effect, or G-EVID1 modification.

**Verdict:** **READY FOR IMPLEMENTATION AND FREEZE PREPARATION**. This is not
readiness to execute. Implementation, independent gold signoff, model/config
resolution, mechanical pilot, implementation audit, execution freeze, and explicit
operator authorization remain future gates.

## 1. Revised question and claim audit

The revised question asks whether same-model, blind repeated semantic assessment
plus a deterministic second-assessment veto reduces unsafe operational use versus
a prospectively designated single-assessment baseline while retaining useful
evidence, and which unsafe errors remain correlated.

This matches the actual architecture. The design explicitly denies model and
evidential independence while preserving assessment blindness and separate seeded
sampling. It can support descriptive comparative claims for this corpus and fixed
configuration. It cannot support independent-reasoner, independent-source,
deployment, or generalization claims.

## 2. Prompt-confound audit

The r1 outcome-derived sentences about the entire claim, population/qualifiers,
and persistence are absent. R2 reproduces the original G-EVID1 prompt wording and
schema. The deterministic design checker rendered all 32 r2 items through both
templates and established byte identity for every item after substituting the
same item fields.

Prompt differences are therefore mechanical storage and new data substitution,
not semantic coaching. **Resolved.**

## 3. Contamination audit

R1 C01, C05-C06, C18, and C19-C20 are absent. R2 contains no exact/at-least
threshold conversion, added-conjunct boundary, prior-state persistence inference,
or current-versus-superseded pair. The new families use distinct constructions:
population coverage, explicit exceptions, deontic modality, named referents,
explicit interval membership, and observed-versus-unobserved outcomes.

No proposition or evidence text exactly matches G-EVID1 or r1. The construction
rationale is recorded item-family by item-family in `CONTAMINATION_LEDGER.md`.
Because the author knew the prior results, this is prospective fresh content, not
a historically blind corpus. That limits external-validity claims but does not
recreate the identified answers. **Resolved for this prospective design; external
blind replication remains a future limitation.**

## 4. Complete r2 gold audit

The semantic contract is holistic: `supports` must entail the complete proposition.
Scope and temporal fields diagnose coverage and applicability; they do not rescue
support. Every crisp primary item has one tuple. Genuine ambiguity is isolated.

| ID | Proposition/evidence judgment | Gold tuple | Eligibility | Audit result |
|---|---|---|---|---|
| R01 | Complete population has twelve of twelve successful scans. | supports / match / compatible | use | Agree; universal proposition entailed. |
| R02 | One member of the complete population is not scanned. | contradicts / match / compatible | abstain | Agree; explicit counterexample falsifies universal. |
| R03 | One named orchard has the property. | supports / match / compatible | use | Agree; existential entailed. |
| R04 | One of four has the property; three unresolved. | partial / evidence_narrower / compatible | investigate | Agree; proper subpopulation established, universal unresolved. |
| R05 | Exception is preserved exactly. | supports / match / compatible | use | Agree. |
| R06 | Excluded medical class is claimed to use the forbidden gate. | contradicts / match / compatible | abstain | Agree; explicit `never` contradiction. |
| R07 | Staffed-hours permission matches. | supports / match / compatible | use | Agree. |
| R08 | “Any time” includes expressly denied unstaffed hours. | contradicts / match / compatible | abstain | Agree. |
| R09 | Mandatory protection rule matches obligation. | supports / match / compatible | use | Agree. |
| R10 | Proposition denies the obligation imposed by the same rule. | contradicts / match / compatible | abstain | Agree; corrected during this audit to make P05 minimal. |
| R11 | Optional permission matches “may.” | supports / match / compatible | use | Agree. |
| R12 | “Required” conflicts with explicitly optional/not-required. | contradicts / match / compatible | abstain | Agree. |
| R13 | Registry directly maps Halcyon to H-204. | supports / match / compatible | use | Agree. |
| R14 | Registry maps Zephyr to Z-881, not H-204. | contradicts / match / compatible | abstain | Agree. |
| R15 | Eastern turbine directly recorded T-9. | supports / match / compatible | use | Agree. |
| R16 | One of three is T-9; two model fields unresolved. | partial / evidence_narrower / compatible | investigate | Agree. |
| R17 | Requested date lies inside explicit permit interval. | supports / match / compatible | use | Agree. |
| R18 | Permit explicitly becomes invalid at requested boundary. | contradicts / match / compatible | abstain | Agree; exact date addressed, so temporal is compatible. |
| R19 | Requested time lies inside explicit closure interval. | supports / match / compatible | use | Agree. |
| R20 | Route explicitly reopened before requested time. | contradicts / match / compatible | abstain | Agree. |
| R21 | Signed completion log records completed cycle. | supports / match / compatible | use | Agree. |
| R22 | Final record says cycle aborted before completion. | contradicts / match / compatible | abstain | Agree. |
| R23 | Final certified result is PASS. | supports / match / compatible | use | Agree. |
| R24 | Prediction exists, but test was not performed. | unclear / match / compatible | investigate | Agree; no observed component of passing is established. |
| R25 | Direct glossary definition matches east. | supports / match / compatible | use | Agree. |
| R26 | Same glossary defines east, contradicting west. | contradicts / match / compatible | abstain | Agree. |
| R27 | Signed dated rota directly matches assignment. | supports / match / compatible | use | Agree. |
| R28 | Same proposition paired with unrelated same-date menu. | irrelevant / mismatch / compatible | abstain | Agree; temporal corrected to compatible because both are dated. |
| D01 | Pronoun can refer to cup or vase. | unclear / unclear / compatible | investigate diagnostic | Agree; genuine referential ambiguity. |
| D02 | Rule depends on unknown holiday status. | unclear / match / unclear | investigate diagnostic | Agree; genuine contextual/temporal ambiguity. |
| D03 | Rounded whole-unit display cannot establish exact decimal. | unclear / match / compatible | investigate diagnostic | Agree; genuine measurement-resolution ambiguity. |
| D04 | Modifier scope over managers is unresolved. | unclear / unclear / compatible | investigate diagnostic | Agree; genuine syntactic ambiguity. |

**Gold-audit result:** all 28 crisp primary items now have one defensible tuple and
operational disposition under the stated contract. The four ambiguous items are
correctly isolated as diagnostics. This audit itself corrected R10's pair design
and R28's temporal gold before any model contact. A separate qualified reviewer
who did not author r2 must still sign the gold before execution freeze.

## 5. Sampling audit

The proposal fixes `qwen3.8:27b`, temperature 0.6, top-p 0.9, top-k 40, min-p 0,
repeat penalty 1.0, context 8192, output cap 350, no stop strings, no streaming,
three repeats, distinct deterministic A/B seeds, fresh sessions, balanced call
order, and one attempt/no repair. The checker confirms 192 distinct nonzero seeds
and 48/48 A-first/B-first balance.

These settings create separately seeded repeated samples, not independent
reasoners. The choice is fixed before outcomes and cannot be tuned through pilot
semantics. Exact installed model/config digests and proof that Ollama honors every
field remain execution-freeze gates. Unsupported seeding blocks freeze.

## 6. Baseline and comparison audit

A is the prospective primary single-assessment baseline; B is a symmetric
sensitivity baseline. A/B role is independent of balanced call order. All three
conditions use the same observations, validation, governor, gold, and items.

The comparison remains maximum-conservative. Its 3x3 table is complete,
commutative, deterministic, and justified by the principle that operational use
requires two individually admissible repeated assessments. It can retain all
useful evidence when both calls are correct; the state-space enumeration does not
imply an empirical near-zero retention rate. The 34/42 utility gate and A/B
baselines expose excessive conservatism instead of relaxing policy.

Structural invalidity is scientifically distinct from semantic abstention even
though both safely prevent use. Correlated false-clean agreement remains paired
use and is explicitly the central failure metric.

## 7. Metric and denominator audit

`METRICS.md` fixes all corpus, role, pair, item, gate, diagnostic, and control
denominators before implementation. A and B are symmetric. Safety, utility,
semantic accuracy, agreement, structural/grounding validity, variability,
provider accounting, runtime, tokens, and cost availability remain separate.

Correlated error has four explicit views: wrong agreement by axis, wrong exact
tuple agreement, forbidden paired use, and diagnostic forbidden paired use. It is
reported by observation, item cluster, family, confidence, and disposition.
High overall agreement cannot erase one unsafe pair.

## 8. Abort and pilot audit

`ABORT_RULES.md` distinguishes an invalid returned assessment (preserve, reject,
continue without retry), infrastructure-incomplete abort, mechanical pilot
failure, scorer failure, telemetry degradation, contamination/gold defect, and a
valid completed semantic failure. A semantic failure cannot trigger repair or
threshold/gold relaxation.

`STRUCTURAL_PILOT_SPEC.md` defines 14 unrelated deterministic fixtures and exact
expected mechanical behavior. It is a specification only; no pilot exists or ran.

## 9. Activity audit

`ACTIVITY_SPEC.md` lists phases and content-free fixed counts for 32 items, 96
pairs, 96 A, 96 B, 192 calls, validation, comparison, scoring, failures, elapsed
time, and terminal state. It expressly forbids item text, prompts, outputs,
semantic labels, confidence, dispositions, gold, safety labels, families, and
scorer results during collection. Telemetry cannot control execution.

Future telemetry on/off and failure parity tests are mandatory. Activity failure
is nonfatal only when scientific behavior and records are unchanged.

## 10. Previous-blocker resolution matrix

| Previous blocker | Revision | Evidence | Status |
|---|---|---|---|
| B1 prompt repair confounded corroboration | Restored original G-EVID1 prompt; removed all outcome-derived coaching. | 32 byte-identical rendered-prompt checks; prompt-delta table. | RESOLVED |
| B2 contaminated primary items | Removed r1 C01, C05-C06, C18, C19-C20; built new constructions and ledger. | `CONTAMINATION_LEDGER.md`; historical exact-text and removed-ID checks. | RESOLVED for prospective r2; external blind replication remains a limitation |
| B3 ambiguous semantic axes/gold | Added holistic semantic contract; one tuple per crisp item; isolated four ambiguity diagnostics; repeated full audit. | `SEMANTIC_CONTRACT.md`, revised gold, table above, 32 policy-consistency checks. | RESOLVED at design level; independent reviewer signoff remains a pre-freeze gate |
| B4 no runner/comparison/scorer/pilot | This task was expressly prohibited from implementing them. Exact interfaces, metrics, aborts, and pilot fixtures are now specified. | Design documents; checker confirms these implementations/runs are absent. | OPEN BY PHASE; this is the next implementation task, not permission to run |
| B5 unresolved sampling configuration | Fixed stochastic settings, seeds, order, isolation, and retry behavior. | `sampling_proposal.json`; 192 seed and 48/48 ordering checks. | RESOLVED as proposal; model digest/provider support remain pre-freeze gates |
| B6 ambiguous scorer denominators/asymmetry | Defined exact A/B-symmetric metrics and fixed denominators. | `METRICS.md`. | RESOLVED at design level; scorer implementation must later prove conformance |
| B7 incomplete pilot/abort rules | Defined failure taxonomy and 14 exact unrelated mechanical fixtures. | `ABORT_RULES.md`, `STRUCTURAL_PILOT_SPEC.md`. | RESOLVED at design level; no pilot implemented or launched |

## 11. New adversarial findings

### BLOCKING before implementation

None found in the revised research question, prompt, corpus semantics, comparison
principle, metric definitions, abort taxonomy, or Activity specification.

### IMPORTANT before execution freeze

1. A qualified reviewer who did not author r2 must independently sign every gold
   item. Any disagreement causes revision/removal and a new audit.
2. Exact local model content/configuration digests and proof of sampling-parameter
   support remain unresolved until freeze preparation.
3. The production runner, comparator, scorer, provider accounting, guards, and
   Activity adapter do not exist by instruction and require adversarial code audit.
4. R2's author knew prior outcomes. Claims must remain corpus-specific; a later
   external replication needs a historically blind corpus author.

### MINOR

- The 34/42 utility floor is a declared engineering feasibility threshold, not an
  optimized scientific constant.
- Two positive and two negative direct controls are enough for a small design but
  do not estimate broad control-family performance.
- Fixed seeded local generation may still have hardware/runtime nondeterminism;
  exact outputs must not be promised as reproducible.

### CLEAN

- G-EVID1 is untouched and remains failed as preregistered.
- R1 remains byte-preserved.
- The research claim matches same-model repeated sampling.
- Prompt coaching and specified contaminated items are removed.
- Semantic axes and ambiguity treatment are explicit.
- Primary and diagnostic strata, minimal-pair metadata, and controls are explicit.
- Baseline, paired comparison, safety, utility, and correlated error are separate.
- Metric denominators are fixed and role-symmetric.
- Abort rules distinguish mechanics, infrastructure, and semantic failure.
- Activity remains observational, content-minimized, and non-authoritative.
- No model, provider, pilot, runner, scorer, freeze, installation, or authority was invoked.
- The read-only design checker passes 122 checks with zero provider calls.

## Final verdict

**READY FOR IMPLEMENTATION AND FREEZE PREPARATION.**

This verdict authorizes nothing. It means the design is coherent enough for a
separate supervised implementation task to build the runner, comparator, scorer,
guards, and Activity adapter, followed by deterministic mechanical tests and a
new implementation audit. It is **not** ready for a model call, pilot, execution
freeze, installation, or experiment run.
