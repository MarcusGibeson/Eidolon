# G-ROUTE4: qualification routing under a stricter, pre-registered policy (design candidate)

Status: **design candidate, revision 4.**
- Nothing is frozen. No model has been contacted for G-ROUTE4, and no corpus or gold exists yet.
- Production routing stays disabled whatever the result. Belief effects are `none`.
- Review so far:

  | Round | Reviewed | Reviewer A | Reviewer B | Record |
  |---|---|---|---|---|
  | 1 | revision 1 | 2 BLOCKING, 10 MUST-FIX | 1 BLOCKING, 10 MUST-FIX | `DESIGN_REVIEW_ROUND1.md` |
  | 2 | revision 2 | 0 BLOCKING, 6 MUST-FIX | 0 BLOCKING, 11 MUST-FIX | `DESIGN_REVIEW_ROUND2.md` |
  | 3 | revision 3 | 0 BLOCKING, 6 MUST-FIX | 0 BLOCKING, 9 MUST-FIX | `DESIGN_REVIEW_ROUND3.md` |

  This revision answers every round-3 finding.

**Before anything runs:**
1. Design acceptance.
2. The authoring blueprint.
3. Corpora with independence checks and adjudicated gold.
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
- **all-new template families**, none carried from G-ROUTE3.

G-ROUTE4 is **not** a replication of G-ROUTE3, and its evidence is **never pooled or combined** with G-ROUTE3's.

G-ROUTE3 is closed: it is **never rescored or reinterpreted**. G-ROUTE3's files may be read, for the contamination
analysis, the prompt identity test and the differential. Its corpora are never G-ROUTE4 validation data, and every
G-ROUTE3 and G-ROUTE1 file stays byte-identical.

## Scope

**Task classes:** ordinary conversation, structured extraction, hierarchical semantic synthesis, reflective
planning, grounded research synthesis. Risk classes R1–R4. R4 stays evidence-only.

**Carried unchanged:**
- **Models:** qwen2.5:7b, qwen3:14b and qwen3.8:27b, with the manifest and blob digests of G-ROUTE3's bindings.
  G-ROUTE4 writes its own bindings file with renamed ids (`g-route4.model-bindings.v1`,
  `G-ROUTE4-MODEL-BINDINGS-R1`). A test asserts that its `bindings`, `generation_configuration` and
  `provider_version` equal G-ROUTE3's `model_bindings.json`.
- **Provider and generation:** Ollama 0.34.3, recorded in the freeze and checked before every launch. The G-ROUTE3
  generation configuration (including `num_predict` 350).
- **Contracts:** carried by module attribute, **keeping their G-ROUTE3 names**, because they belong to the modules
  imported unchanged: the conversation frame v3, operational validator v2, semantics v1, triggers v1 and
  routing v1.

**Coding is deferred (D6).**
- The coding runner is not a sandbox, and its AST gate can be bypassed. See `DESIGN_REVIEW_ROUND1.md`.
- Coding moves to its own later experiment, with a real sandbox and a hardened AST gate as the primary control.

## Questions

**P1: routing safety for this policy.** On the frozen validation corpus, given the A′ table that is actually
produced:
- is the true unsafe-stop rate at most 0.10?
- is the true correct-stop rate of qualified-start cases at least 0.60?

Each is judged at one-sided 95% confidence with exact binomial bounds, per the gate tables.

**P2: conversation on the cheapest tier.** Descriptive (D2).

**E1: escalation.** Pilot, descriptive only.

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

## Identity and separation

**Modules: imported or forked.**

| Imported unchanged (byte-identical, guarded) | Forked into `g_route4_*` (identity parameterized) |
|---|---|
| `g_route1_validators`, `g_route1_operational`, `g_route1_contract`, `g_route1_provider`, `g_route1_execution_contract`, `g_route1_freeze`, `g_route2_normalization`, `g_route3_conversation`, `g_route3_semantics`, `g_route3_operational`, `g_route3_triggers`, `g_route3_routing`; `experiments/G-ROUTE1-candidate/prompt_profiles.json` | `platform`, `fs`, `contract`, `qualification`, `validation`, `scorer`, `lifecycle`, `journal`, `evidence`, `launch`, `freeze`, `runner`, `independence`, `campaign`, `tests`, `differential` |

- **The runner fork** provides only what R7 uses: `GovernedOllamaProvider`, the fixed endpoint,
  `verify_model_receipts`, `sanitize_strings` and the guarded paths. It imports neither `g_route1_coding_runner` nor
  `g_route1_persistence`.
- **Closure rule:** an imported-unchanged module imports only imported-unchanged modules. This is checked by a test
  over the import graph.
- **Guarded list:** every transitively loaded repository module, the prompt profiles, and G-ROUTE4's corpora, gold,
  schedules, thresholds, bindings and freeze.
- **Module rule:** no `g_route3_*` module other than the five imported unchanged is ever loaded by a G-ROUTE4
  process, and neither is `g_route1_coding_runner`. This is checked through the digests of every loaded module.
- **Forked grading or routing code carries a proof of equality.** A differential on shared records shows its
  outputs equal G-ROUTE3's wherever the rules coincide.

**Identity constants.**
- **Grep test:** the pattern `(?i)g[-_ ]?route[-_ ]?3` must not appear in any `g_route4_*` module, except entries
  on one frozen allowlist (`G3_REFERENCE_ALLOWLIST`). The allowlist holds:
  - the imported-unchanged module paths;
  - the carried contract ids, referenced by attribute;
  - the named read-only references to G-ROUTE3 in the data-root refusal test, the prompt identity test, the
    contamination check and the differential.
- **Values:**

  | Constant | G-ROUTE3 | G-ROUTE4 |
  |---|---|---|
  | experiment name in `root.json` | `G-ROUTE3` | `G-ROUTE4`, checked read-only before setup or the lease, and again after the lease |
  | data root | `…\research\g_route3` | `C:\Users\marcu\AppData\Local\Eidolon\research\g_route4` |
  | benchmark id; development run roots | `G-ROUTE3`; `data/g_route3` | `G-ROUTE4`; `data/g_route4` |
  | ledger genesis; lease holder; pinned thread | `g-route3-ledger`; `g-route3-r7`; `g-route3-pinned` | `g-route4-ledger`; `g-route4-r7`; `g-route4-pinned` |
  | evidence author/committer; index file; root message | `G-ROUTE3 evidence <g-route3-evidence@localhost>`; `g-route3-index`; `G-ROUTE3 evidence root` | the same with `G-ROUTE4` / `g-route4` |
  | run ids | `groute3[ab]-NNN-<16 hex>` | `groute4[ab]-NNN-<16 hex>` |
  | call-id prefix; fixture namespace | `GROUTE3-`; `A-`, `B-` | `GROUTE4-`; `A4-`, `B4-` (the schedule and loader prefix checks updated) |
  | corpus, gold, schedule, table and threshold ids; schedule salts | `G-ROUTE3-…` | `G-ROUTE4-…` |
  | G-ROUTE4-owned contract and schema versions; error codes | `g-route3.*`; `g_route3_phase_*` | `g-route4.*`; `g_route4_phase_*` |
  | freeze candidate id; superseded list | `G-ROUTE3-EXECUTION-R7`; R1–R6 | `G-ROUTE4-EXECUTION-R1`; empty |
  | campaign workdir; artifact folder; table on `main` | `%TEMP%\g_route3_campaign`; `experiments/G-ROUTE3-candidate/…` | `%TEMP%\g_route4_campaign`; `experiments/G-ROUTE4-candidate/…`; `…/G-ROUTE4-candidate/QUALIFICATION_TABLE.json` |

**Seeds.**
- **Formula:** seed = base + fixture_index × 10 + repeat, with a zero-based fixture index and **one-based repeats**,
  as in G-ROUTE3.
- **Ranges:**

  | Phase | Range |
  |---|---|
  | A′ | 470001–470792 |
  | B′ | 480001–483041 |

  Both are disjoint from G-ROUTE3's 43001–44471.
- **Tiers** share the seed of a fixture × repeat group.
- **Attempts:** seeds are identical across attempts.

**Sentences.** These ASCII templates are verbatim and matched in full.
- `<binding>` and `<table>` are 64 lowercase hex characters.
- `<n>` and `<m>` match `[1-9][0-9]*`.
- `<run_id>` matches `groute4[ab]-[0-9]{3}-[0-9a-f]{16}`.

The templates:
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
- **G-ROUTE3's side already refuses:** `g_route3_freeze.DATA_ROOT` is a literal, and `verify_manifest` rebuilds the
  manifest from it. A test asserts this.
- **G-ROUTE4's side** checks the literal path and the committed experiment name read-only, before setup, the lease
  or any write. After taking the lease it checks the name again.

**One job at a time.** Leases are per data root, so this rule is enforced by the runbook, not by code. That is
declared.

## Coding exclusion in the R7 fork

- The corpus loader refuses any `coding.v1` profile or coding task class.
- `RunSpec.coding` is asserted to be empty.
- The execution kinds are forbidden. Any `execution_started` or `execution_recorded` entry fails R7 §5 R3 and is an
  integrity failure. That makes the coding replay states unreachable, and the protection clause keyed to
  `execution_recorded` does not apply.
- There is no worker, and the scorer's coding branch and executable derivation are removed. The AST recursion band
  is not measured.
- **Certification:**
  - **The campaign's base synthetic schedule** is 4 non-coding positions. G-ROUTE3's put a coding call at position 2.
  - **Dropped:** the sandbox-failure sweep, Ctrl+C during the sandbox, worker module drift, and the resumed
    `awaiting_execution` interrupt case.
  - **Added:** probes proving an injected execution entry is an integrity failure, and that the coding runner and
    the other `g_route3_*` modules are never loaded.
  - **Kept:** every other section.
  - Kill-point counts differ from G-ROUTE3's certification, which is declared.

## Schedule (fixed before any contact)

Both phases use a **fixed, fully enumerated schedule**, frozen before contact:
- every position has its call id, seed and request digest;
- positions are identical across attempts.

Phase B′ calls all three tiers on every case (D1). Routing is computed afterwards, gold-blind, from the sealed
records by the frozen router. R7's guarantees therefore apply unchanged: no position is sent twice, replay is
deterministic, attempts are protected, and denominators are defined.

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
  G-ROUTE3's hypothesis-generating result.
- **B′ is never resized,** topped up, extended or pooled. NOT_TESTABLE is final.

## Corpora

**Output-shape disclosure (D8; wording approved and amended by the operator, 2026-09-28).**
- **Research prompt:** the G-ROUTE3 research rule body, byte-identical; only the subject phrase varies.
- **Inserted sentence:** exactly once, immediately after `Each claim object has exactly the keys claim_id, status,
  citations and lineages.`, separated by one ASCII space. 454 ASCII characters, sha256
  `f3c383d92b5ca1cb99008b49864f7330b6515c93f8e795a6c135f1326844ab47`:

  ```
  Reply with a JSON object whose keys are exactly claims, recommendation and uncertainties: claims is a list with exactly one claim object for each input claim, carrying that claim's claim_id; in each claim object, status is one of supported, contradicted or unresolved, citations is a list of distinct source_id strings, and lineages is a list of distinct lineage-name strings; recommendation is a string; uncertainties is a list of distinct code strings.
  ```

  **What it discloses:** together with the rule body, every output-shape rule the frozen research validators
  enforce:
  - the top-level keys;
  - one object per input claim, with its id;
  - the status values;
  - distinct citations, lineages and codes;
  - the string and list types.

  It changes no judgment rule, and the validators are unchanged.
- **The other four classes:**
  - A shape-disclosure audit compares validator-enforced shapes with the system prompt plus the fixture prompt.
  - Gaps are closed by pre-registered sentences in the freshly authored fixture prompts. G-ROUTE1's system prompts
    stay byte-identical.
- **Freeze-time tests:**
  - the research prompt equals the rule body, the subject phrase and the sentence, and matches the sentence's
    sha256;
  - the audit, evaluating the rule body and the sentences together, finds no residual gap in any class.

**Authoring blueprint** (frozen before authoring). The research patterns are G-ROUTE3's construct patterns:

| Label | Pattern |
|---|---|
| P1 | positive lineage count rule |
| P2 | direct contradiction |
| P3 | other subject, unaddressed |
| P4 | same-lineage repetition |
| P5 | conflict unresolved |
| P6 | narrower scope |
| P7 | conflict settled by rule |
| P8 | quantitative contradiction |

These are relabelled P1–P8 here to avoid a clash with source ids such as `S1`.

| Research cell | A′ (4 fixtures) | B′ (18 fixtures; R4: 1) |
|---|---|---|
| R1 | P1 P2 P3 P4 | P1–P8 × 2, plus P1 P2 |
| R2 | P5 P6 P7 P8 | P1–P8 × 2, plus P3 P4 |
| R3 | P1 P3 P5 P7 | P1–P8 × 2, plus P5 P6 |
| R4 | P2 P4 P6 P8 | P7 (evidence-only) |

- **`single_lineage_support` holds in:**
  - 2 of 4 fixtures per A′ research cell;
  - 9 of 18 per eligible B′ research cell.
- **Declared:**
  - the exact pattern × `single_lineage_support` crossing is fixed in the blueprint;
  - across eligible B′, P7 and P8 appear 6 times and P1–P6 7 times;
  - an A′ cell's pattern subset is confounded with its risk class;
  - an A′ research cell qualifies on 4 patterns, while its B′ cell tests all 8;
  - research qualification is conditional on this allocation, and not comparable with G-ROUTE3's.
- The other classes' feature allocations are frozen in the same exact per-cell form.

**Template families.**
- **All families are new;** none is carried from G-ROUTE3, so none can be chosen by G-ROUTE3's outcomes.
- Every B′ family appears in A′ and every A′ family in B′, at the class level.
- **Class cap.** No family exceeds 25% of a class's B′ cases, counting R4 (85 conversation, 55 per other class).
  That means at least 5 families per class.
- **Cell cap.** No family exceeds one third of a B′ cell (at most 9 of 28, at most 6 of 18).
- **Declared cell-level gap:** a B′ cell may contain families absent from its A′ cell.
- **Planning** uses at least 5 families, where G-ROUTE3 used 1. That is a declared construct change.

**Independence standard.** G-ROUTE3's measured standard is the floor, and the same tokenizer is used (the forked
`independence` module).
- **Text overlap:** word-trigram Jaccard at most 0.20 between any two G-ROUTE4 fixtures, and between any G-ROUTE4
  fixture and any G-ROUTE3 fixture (A or B).
  - Lowercased, split on non-alphanumerics.
  - The **declared boilerplate** is removed first: the frozen rule bodies, the D8 and disclosure sentences, and
    each family's frozen template text.
- **Nothing shared:** 0 shared entities, identifiers, extraction values, planning actions or source lineages,
  within G-ROUTE4 and against G-ROUTE3.
- **Gold structure:** no fine gold-answer signature (G-ROUTE3's signature definitions) is repeated between A′ and
  B′ in the same cell.
- **Conversation:** the answer-position check is carried.
- **Declared loosening:** pattern labels **are** shared between A′ and B′ in research, and so are coarse
  signatures. G-ROUTE3 forbade both within a cell. The reason is that 8/8 needs 4 fixtures per cell, and R1 measures
  generalization within the construct.
- Feasibility is checked against the blueprint before authoring.
- `CONTAMINATION_ANALYSIS.md` and `INDEPENDENCE_REPORT.json` report every measure per class.
- P1 is declared **conditional on fixtures being exchangeable within the frozen mix**. Unsafe stops cluster by cell.

**Authoring rules:**
- no fixture is pretested on a pinned model or any Ollama model;
- no item is derived from any G-ROUTE3 item;
- G-ROUTE3's corpora are development material for tooling only.

**Gold adjudication** (A′, B′ and reserves; D10).
1. **Batches.** A batch is one named corpus part: A′ main, B′ main, or a reserve set, given as a list of fixture ids.
   The operator starts each batch in chat.
2. **Before the seal:** the mechanical independence checks and the caps pass.
3. **Seal.** Corpus, gold, rationales and the reserve are committed by digest before the first adjudication.
   - **The reserve** holds one fixture per distinct blueprint feature combination present in each cell, and at
     least 20% of the cell.
   - After the seal, gold changes only through a recorded fix.
4. **Sessions.** One fixture per fresh Claude session, never a pinned model and never Ollama. The model id and
   version and the frozen prompt are recorded.
   - The session is blind to gold, rationale, G-ROUTE3 outputs and the diagnosis.
   - Its answer is sealed by a committed digest before comparison.
   - Every invocation is logged with its transcript digest, and the first sealed answer is the answer.
   - **"No answer"** means a session error with no final message. It is retried once, and a second no-answer
     counts as a disagreement.
5. **Disagreement** means the answer fails the frozen semantic validator against gold.
6. **Decision.** If the first adjudicator agrees, the fixture is kept. If it disagrees, **two further fresh blind
   adjudicators** answer:
   - **both agree:** keep;
   - **otherwise:** the operator decides, against the derivability rule only, with a written reason. The operator
     is not blind; this is declared.

   The operator's options are: **gold wrong → fix gold**; **input ambiguous → fix input**; **gold right → keep**.
   A fixture is never dropped for being hard.
7. **Fixes.** A fixed fixture is re-adjudicated from scratch with the same procedure. It has at most one fix.
   **"Failing again"** means the re-adjudication does not end in "keep", and the fixture is then replaced.
8. **Replacements** are taken from the reserve matching the slot's blueprint features, in a fixed order, and
   adjudicated from scratch. There are at most 2 rounds per slot.
9. **Halt.** If the round cap is hit, or the matching reserve is exhausted, authoring **halts before the freeze**.
   The corpus is never shrunk, and D9 never changes.
   - More reserve needs a recorded operator decision.
   - Any new reserve is authored to the blueprint, declared as authored after adjudication outcomes were known,
     sealed, adjudicated from scratch, and disclosed.
10. **Review-driven changes.** A change driven by the corpus review goes through a fix (counted as the fixture's one
    fix) or a replacement, with re-adjudication.
11. **Records.** Per-cell fix and replacement counts and disagreement rates are disclosed, and bound in the freeze.

## Qualification (Phase A′)

- **8/8 unanimity:** 4 fixtures × 2 repeats. It is declared stricter than 4/4: P(qualify) is 0.430 against 0.656 at
  p = 0.9, and 0.663 against 0.815 at p = 0.95.
- **Every cell reports:**
  - the observation-level bound (0/8 gives 0.312);
  - the fixture-level bound (0/4 gives 0.527, against G-ROUTE3's fixture-level 0.776).
  The fixture-level bound is the honest one.
- **The 0.60 rationale is restated for 8/8.** A qualified cell needed eight of eight correct across four
  independent fixtures. Below 60% correct stops on new cases, the label carries too little predictive information.
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

**Floors:**
- **76 stops:** the smallest n at which the unsafe gate passes with 3 unsafe stops. That meets G-ROUTE3's own
  rationale of "more than one case of margin".
- **30 qualified-start cases:** at least 23 correct are needed there for a lower bound of at least 0.60. It never
  binds a P1 PASS, because an unsafe PASS needs at least 76 stops, and qualified starts are at least the number of
  stops. It governs the correct-stop gate's FAIL and NOT_TESTABLE outcomes.
- G-ROUTE3's observed-rate FAIL standard at n ≥ 10 is kept.
- The floors are stricter, never looser. Identical evidence can be NOT_TESTABLE just below a floor and FAIL just
  above it; this is declared.
- "FAIL (shown worse)" can be claimed on either gate, each at 5%, without adjustment; this is declared.

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

**Integrity:** FAILED_INTEGRITY if any of G-ROUTE3's integrity gates is violated:
- denominators (915 calls; 300 eligible and 5 R4 cases decided; the D9 per-cell composition);
- 0 unqualified-tier terminal results;
- 0 gold-leakage events;
- 0 table mutations after Phase B′ starts;
- 0 benchmark crashes from model output;
- 0 missing-data qualifications.

**Primary status:** FAILED_INTEGRITY, then FAIL, then NOT_TESTABLE, then PASS. The two gates form an
intersection-union test, so no multiplicity adjustment is needed.

**Power (declared).** The table gives the minimum and maximum of P(PASS) for the unsafe gate over n = 120–219
stops (the extremes fall at n = 128 and n = 215). It assumes independent stops, but stops cluster by cell, which is
declared.

| True unsafe rate | P(PASS), minimum–maximum |
|---|---|
| 0.02 | 0.985–1.000 |
| 0.03 | 0.908–0.998 |
| 0.05 | 0.541–0.877 |
| 0.07 | 0.201–0.457 |
| 0.09 | 0.05–0.12 |

At a true rate of 0.10, P(PASS) is at most 0.05.

**Basis of the 0.40–0.73 stop-rate range.** G-ROUTE3's overall rate was 0.61. In the classes where it qualified,
22 of 24 eligible cases stopped (0.92). A projection of G-ROUTE3's per-cell pass rates under 8/8 gives a median of
182 qualified-start cases (10–90%: 144–218), and P(fewer than 76) ≈ 0.001.

**P1 below 76 stops.** P1 cannot PASS below 76 stops. Its status then follows the gate tables: FAIL whenever a FAIL
condition holds, NOT_TESTABLE otherwise.

Stops come in whole-cell blocks: at most 28 per qualified conversation cell and 18 per other cell. Configurations
that cap stops below 76, even if every qualified-start case stops, are:

| Qualified conversation cells | Other cells, at most |
|---|---|
| 0 | 4 |
| 1 | 2 |
| 2 | 1 |

These are upper-bound cases. Exhausted escalations can make stops fewer still.

**P2 (descriptive).** Each figure reports k, n and a two-sided exact 95% interval:
- the conversation stratum's unsafe stops, with the small tier broken out;
- the small tier's conversation semantic-failure rate on all 84 conversation cases, as a diagnostic
  counterfactual.

**E1 (pilot, descriptive).**
- It reports escalations, escalated stops, and the correct and unsafe counts among them, with bounds.
- It reaches no verdict.
- The planning figure is P(at least 5 escalations) ≈ 0.62–0.80. That uses a Jeffreys Beta(1.5, 21.5) prior on
  G-ROUTE3's 1 in 22, over 120–219 qualified starts.
- It is optimistic twice over: escalation needs at least 2 qualified tiers in a cell, and escalated stops are at
  most escalations.

**Descriptive reporting** (frozen in code; never gating):
- an equal-weight-by-class unsafe rate over classes with at least 1 stop, without a bound;
- **research metrics over every research output of every tier, in A′ and B′:**
  - claim-level agreement: the share of claims whose status, citations and lineages all equal gold;
  - uncertainty-code agreement: exact set equality with gold;
  - element-shape failures: a count;
- per-template and per-cell breakdowns;
- the cluster bound, labelled "P(a template family has at least one unsafe stop)". It is an exact bound on
  families, and near-uninformative with about 5 families per class.

**Generalization** (descriptive). For each tier and each eligible B′ cell, it reports the semantic hard-gate pass
rate with a two-sided exact 95% Clopper-Pearson interval, beside the A′ verdict and the A′ pass rate on the same
basis. G-ROUTE3's generalization labels are not used.

## Scoring shapes in the fork

- Denominators: 915 and 305.
- The thresholds schema:
  - `observations_required` 8, `fixtures_per_cell` 4, `repeats` 2;
  - floors of 76, 30 and 10;
  - the exact bound forms.
- The B′ loader checks the D9 per-cell composition (28, 18 or 1) and the `A4-`/`B4-` prefixes.
- The secondary escalation verdict and the "excluding coding" metric are removed.

## Phase B′ preconditions

R7 §10 items 1–11 apply unchanged, except:
- 60 cells instead of 72;
- the 8-observation cell shape;
- G-ROUTE4 paths, sentences and identity.

## Certification and differential

- **The full R7 certification campaign,** adapted as in "Coding exclusion", on the `g_route4_*` modules.
- **A lifecycle differential.** A shared 4-position non-coding synthetic schedule runs through G-ROUTE3's R7 and
  through the G-ROUTE4 fork, with a **shared stub scorer**.
  - The G-ROUTE3 side runs in a separate subprocess, so no G-ROUTE4 process loads its modules.
  - **Normalization before comparison:**
    - mask random tokens (`root_id`, run tokens);
    - substitute identity strings, per the identity table;
    - re-seal the entries;
    - compare the journal entry sequences, the ledger payloads and the evidence **trees**, not commit ids.
  - The derived `scored`/`completed` payloads come from the shared stub, so they compare equal too.
- **An independently written oracle** covers the rules that differ by design: 8/8 qualification, the three-way
  gates, and the exact bounds including the lower bound. It is checked over every (n, k) with n ≤ 400.

## Order of work and authorization

1. **Design review** until accepted. This is revision 4.
2. **Authoring blueprint** frozen: per-cell features and their crossing, families, caps, reserve composition.
   Independence feasibility is checked.
3. **Corpora:**
   1. authoring;
   2. the shape-disclosure audit;
   3. mechanical independence checks and caps;
   4. the seal;
   5. adjudication, batch by batch, each started by the operator;
   6. the contamination and independence reports;
   7. **the external corpus review:** two fresh reviewers under the safety-gated rule. It is accepted at 0
      BLOCKING with every MUST-FIX resolved; changes go through fixes or replacements with re-adjudication.
4. **Implementation** in `g_route4_*`, then an implementation review, certification and the differential.
5. **Execution freeze** (G-ROUTE4 binding, Ollama version recorded).
6. **Phase A′:**
   - the operator's sentence;
   - an independent A′ audit by a fresh Claude session with no authoring context;
   - the freeze-table sentence;
   - the table on `main`.
7. **Phase B′:** the operator's sentence, then an independent B′ audit by a fresh session, then the results record.

Production routing stays disabled whatever the result.

**Runbook:**
- Reserve uninterrupted windows of about 3.2 hours for A′ and about 6 hours for B′.
- An interrupt closes a fresh attempt. Under ruling 12, a resumed attempt interrupted before its first new call stays
  open, and an interrupt after collection exits without closing.
- Check the Ollama version before each launch.
- Run one local-model job at a time.

## Operator decisions

| # | Decision | Chosen |
|---|---|---|
| D1 | Phase B′ calls | **All three tiers** (revised after round 1) |
| D2 | P2 conversation stratum | **Reported with its bound**, not gating |
| D3 | Escalation | **Pilot, descriptive** (a consequence of D9) |
| D4 | Qualification scale | **8 observations per cell**, with both bounds reported |
| D5 | R4 in Phase B′ | **A minimal set:** one per class |
| D6 | Coding | **Deferred** to its own experiment (revised after round 1) |
| D7 | Grounded research | **Diagnose, then include.** The diagnosis is done; the validators are unchanged |
| D8 | Output-shape disclosure | **The verbatim research sentence (sha256 `f3c383d9…ab47`); all classes audited; gaps closed in fixture prompts.** Approved after round 2; the wording was amended and re-approved after round 3 to add "exactly one … carrying that claim's claim_id" and "distinct code strings" |
| D9 | Phase B′ size | **300 eligible cases** plus 5 R4 cases: 915 calls |
| D10 | Adjudication authorization | **The operator starts each batch in chat;** every session is logged and sealed |

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
