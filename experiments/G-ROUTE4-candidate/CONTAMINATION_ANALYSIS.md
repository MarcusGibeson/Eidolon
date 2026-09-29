# G-ROUTE4 contamination and independence analysis

Design order of work, step 3.6. Written over the **final corpus**: the sealed corpus (seal `50e6b46`) with the 20 authorized, recorded round-1 fixes overlaid (14 B′, 6 A′). No fixture was replaced, no reserve was drawn, and the seal is not modified. The measured values are in `INDEPENDENCE_REPORT.json` (sha256 `59a4a224d510beeb995c9981b91bb423773b57450f2404ec9dc7c826191949d4`); the adjudication records are in `adjudication/A_MAIN_CLOSURE.json` (sha256 `1eb6f3fb2aa660a67493102b75bd9343758b422c00c4894e09819eecf244f022`) and `adjudication/B_MAIN_CLOSURE.json`.

**Result: every frozen independence measure passes on the final corpus, with 0 problems. The same tool gives 0 problems on the sealed corpus alone, and no class-level measure changes between the two.**

## Binding

| Item | Value |
|---|---|
| Seal commit | `50e6b46994299ffd71c97aa3f81f30637efaba1c` |
| Blueprint commit | `1156d0645b1b113b91c65e4a485b7f75ffa10061` |
| Audit sample commit | `29f5a477693d703699af62f9fc0e0945c9c66be2` |
| Fixes, B′ round 1 | commit `28718001d8e47194a93e444c771ec1167c040c28`; 14 fixtures; FIX_RECORD sha256 `d4f81a8e3b439b07…` |
| Fixes, A′ round 1 | commit `8774a57a4bfc8d9f0f214d05253c016795385d43`; 6 fixtures; FIX_RECORD sha256 `661b75ce861ef545…` |
| Final A′ main (80), model-facing / gold | `bc1938b754f4566f482df5369b8ee02f92297018d6ada02eab8e91e40709a4ec` / `696ff00fd3074aef808c93300684fa3c7d82395636cf3722875d9babc65842b2` |
| Final B′ main (305), model-facing / gold | `111f95c65fc3708ac187ca3315de6f71ef58f32626bd4992a1d4d532405a3c30` / `aa297b4dba84a524601d02f11f37dd34d30f1e094e642b8b1928ff726bcb0e96` |
| Reserves (80 A′, 119 B′), unchanged | `5f6962f928d6b03d…`, `eb7051a67b3157ea…` |
| Tool | `check_corpus.py` at staging `dd8193b` (sha256 `b3f6500b4b39a80c…`), the authoring-stage independence tool of blueprint §4, which ran before the seal and at every fix re-check |
| Frozen G-ROUTE3 detector | `tools/g_route3_independence.py`, sha256 `177aa18abc21057d…` (pinned; unchanged) |
| Generated at | parent commit `c70d6f6ce6a532df3afc95f7ad27b89129e776f8` |

The stage-4 forked module `g_route4_independence` does not exist yet (implementation is order-of-work step 4). Its byte-identity test (N9) is verified at the implementation review, and the step-8 final re-check before the freeze is still to come.

## Frozen measures on the final corpus

One pool per class: all 584 G-ROUTE4 fixtures (A′ and B′, main and reserve) plus G-ROUTE3's A and B fixtures of that class. A fixed text replaces its old text, and boilerplate is recomputed over the whole pool (N7).

| Measure | Frozen criterion | Sealed | Final | Status |
|---|---|---|---|---|
| Word-trigram Jaccard, every pair (same-family included), after pinned-text and 25% boilerplate removal | ≤ 0.2 | 0 pairs over | 0 pairs over (max 0.1788) | pass |
| Named entities shared (O3; all classes, main and reserve, pairwise and against all G-ROUTE3) | 0 | 0 | 0 (697 G-ROUTE4 entities; 20 G-ROUTE3) | pass |
| Identifiers shared (O3 identifier gate) | 0 | 0 | 0 (17 G-ROUTE4, 11 G-ROUTE3) | pass |
| Exact structured values shared (O6) | 0 | 0 | 0 (1777 G-ROUTE4 values compared) | pass |
| Research source lineages repeated across fixtures | 0 | — | 0 (476 lineages) | pass |
| Planning action names repeated | 0 | — | 0 (515 names) | pass |
| Identical canonical gold (N1) | 0 | 0 | 0 | pass |
| Fine gold signature repeated A′/B′ in a cell (research, extraction) | 0 | 0 | 0 | pass |
| Canonical research signature (decision clause normalized) repeated A′/B′ | 0 | 0 | 0 | pass |
| O5: boilerplate trigrams in a family template; single-family boilerplate | 0; 0 | — | 0; 0 | pass |
| Conversation: 4 options; gold positions within 1 per cell | all; ≤ 1 | — | 142 of 142; balanced in every cell | pass |

Conversation has **no gold-structure signature** (O4), as in G-ROUTE3. It relies on the family rules, the answer-position balance, the no-identical-gold rule and the corpus review. Planning and synthesis are exempt from the fine-signature rule (declared loosening). Research pattern labels and coarse signatures are shared between A′ and B′ within a cell by design (declared loosening; 8/8 needs four A′ fixtures per cell).

## Overlap by class

| Class | Pool | Boilerplate trigrams | Max Jaccard (full content) | Max pair | Max Jaccard (ledger-bound text) | Pairs over 0.20 |
|---|---|---|---|---|---|---|
| Research | 152 | 27 | 0.1788 | A4-RSRCH-R3-02 / B4-RSRCH-R3-X11 | 0.1788 | 0 |
| Synthesis | 116 | 11 | 0.0764 | B4-SYNTH-R3-16 / B4-SYNTH-R4-X01 | 0.0764 | 0 |
| Conversation | 158 | 7 | 0.0976 | B4-CONV-R2-15 / A4-CONV-R3-X03 | 0.0976 | 0 |
| Planning | 116 | 34 | 0.0619 | B4-PLAN-R1-07 / A4-PLAN-R1-X03 | 0.0619 | 0 |
| Extraction | 122 | 6 | 0.1224 | A4-EXTR-R4-03 / A4-EXTR-R4-X03 | 0.1224 | 0 |

O6 compared values by class: Research 476; Conversation 568; Planning 615; Extraction 118. Fields: Research: source lineages; Conversation: every input field except the message; Planning: allowed action names and the objective; Extraction: gold values of free-text (non-enum) string fields.

## N8: maximum same-family A′–B′ overlap per cell (main corpora)

| Class | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Research | 0.0955 (RS3, 12 pairs) | 0.1597 (RS2, 12 pairs) | 0.0581 (RS4, 12 pairs) | 0.0 (RS3, 1 pair) |
| Synthesis | 0.0449 (SY4, 12 pairs) | 0.0241 (SY1, 12 pairs) | 0.0455 (SY4, 12 pairs) | no same-family pair |
| Conversation | 0.0412 (CV4, 20 pairs) | 0.0508 (CV6, 18 pairs) | 0.0429 (CV5, 18 pairs) | no same-family pair |
| Planning | 0.0514 (PL3, 12 pairs) | 0.0324 (PL6, 12 pairs) | 0.0594 (PL3, 12 pairs) | 0.0 (PL1, 1 pair) |
| Extraction | 0.0182 (EX4, 12 pairs) | 0.0495 (EX5, 12 pairs) | 0.0351 (EX5, 12 pairs) | no same-family pair |

Read from the tool's own trigram sets, which are reconstructed and asserted equal to its reported class maxima before use. The largest is research R2 (A4-RSRCH-R2-04 / B4-RSRCH-R2-14), well under 0.20.

## Sealed structure against the effects of the 20 fixes

The pre-existing structure is the sealed corpus measured alone: 0 problems. After the fixes, every class-level value above (pool, boilerplate count, maximum and maximum pair, entity and identifier counts, O6 values, N1, both signature checks) is **identical** to the sealed value. The fixes moved only their own fixtures' overlap:

| Fixed fixture | Round | Max Jaccard, sealed text | Max Jaccard, fixed text | Partner (fixed) |
|---|---|---|---|---|
| A4-EXTR-R1-03 | A′ round 1 | 0.0275 | 0.0275 | B4-EXTR-R1-01 |
| A4-RSRCH-R2-01 | A′ round 1 | 0.0974 | 0.0995 | B4-RSRCH-R2-11 |
| A4-RSRCH-R2-02 | A′ round 1 | 0.1116 | 0.1121 | B4-RSRCH-R2-18 |
| A4-RSRCH-R4-03 | A′ round 1 | 0.0492 | 0.0495 | A4-RSRCH-R4-X03 |
| A4-SYNTH-R2-03 | A′ round 1 | 0.0397 | 0.0261 | B4-SYNTH-R3-08 |
| A4-SYNTH-R4-01 | A′ round 1 | 0.039 | 0.0192 | A4-SYNTH-R4-X01 |
| B4-RSRCH-R1-06 | B′ round 1 | 0.1118 | 0.1124 | B4-RSRCH-R1-X06 |
| B4-RSRCH-R1-14 | B′ round 1 | 0.1773 | 0.1786 | B4-RSRCH-R1-03 |
| B4-RSRCH-R2-06 | B′ round 1 | 0.0798 | 0.0806 | B4-RSRCH-R2-X01 |
| B4-RSRCH-R2-14 | B′ round 1 | 0.1575 | 0.1597 | A4-RSRCH-R2-04 |
| B4-RSRCH-R3-04 | B′ round 1 | 0.1058 | 0.1064 | B4-RSRCH-R3-X01 |
| B4-RSRCH-R3-06 | B′ round 1 | 0.0971 | 0.0976 | B4-RSRCH-R3-X02 |
| B4-RSRCH-R3-14 | B′ round 1 | 0.0884 | 0.0897 | A4-RSRCH-R3-02 |
| B4-RSRCH-R3-18 | B′ round 1 | 0.0828 | 0.0838 | B4-RSRCH-R3-10 |
| B4-SYNTH-R1-01 | B′ round 1 | 0.0278 | 0.0148 | B4-SYNTH-R3-15 |
| B4-SYNTH-R1-03 | B′ round 1 | 0.0152 | 0.0205 | B4-SYNTH-R1-15 |
| B4-SYNTH-R2-13 | B′ round 1 | 0.0294 | 0.0179 | B4-SYNTH-R2-14 |
| B4-SYNTH-R2-14 | B′ round 1 | 0.0211 | 0.0196 | B4-SYNTH-R3-09 |
| B4-SYNTH-R3-07 | B′ round 1 | 0.0221 | 0.0147 | A4-SYNTH-R3-01 |
| B4-SYNTH-R3-09 | B′ round 1 | 0.0229 | 0.0196 | B4-SYNTH-R2-14 |

- **Research (11 fixtures, 12 source texts:** P6 'only' removed, the P4 anonymity support and the weekend support rewritten): each fixture's maximum moved by +0.0003 to +0.0022. The largest fixed-fixture value is 0.1786, under the 0.20 bound.
- **Synthesis (8 fixtures, SY1 role relabels):** maxima moved by -0.0198 to +0.0053; the largest is 0.0261.
- **Extraction (1 fixture, schema key rename):** moved by +0.0000.
- **Declared fix-text exemption.** The tool's authoring-paraphrase rule accepts only authored paraphrase texts, so the 12 fixed research source texts are declared to it, keyed by claim, relation and body. Disabled, the tool flags exactly those 12 sources and nothing else. This rule is authoring conformance, not an independence measure; no independence measure is exempted.

## Exposure and contamination

**Tested models.** The tiers are the local ollama 0.34.3 models bound in G-ROUTE1's `model_bindings.json` (small `qwen2.5:7b`, mid `qwen3:14b`, large `qwen3.8:27b`), each pinned by manifest and blob digest. No G-ROUTE4 execution code exists yet and no Phase A′ or Phase B′ call has been made. The authoring rule forbids pretesting any fixture on a pinned or Ollama model, and every adjudication journal records only `claude-opus-5-5`. Pinned weights cannot be changed by anything done here.

**Adjudication exposure (declared).** The model-facing text of the 385 main fixtures (never gold) was sent to Anthropic's Messages API for gold adjudication, `claude-opus-5-5` under the O2 amendment: 259 A′ invocations and 507 B′ sessions, every one logged in a hash-chained journal. The 199 reserve fixtures were never sent (checked against every journal). The corpus text has therefore left this machine; it cannot influence the pinned tiers.

**Adjudicator filter (declared residual filter, step 12).** Only fixtures that a Claude adjudicator disputed, or that the audit sample caught, were scrutinized, so the corpus may drift toward items a frontier model can solve. A′ descriptive subsets: 54 untouched and 20 disputed-but-kept-unchanged (B′: 243 and 48). These are descriptive and never gating. Every fixed fixture is flagged.

**Authors and operator (declared, N5).** The authors were not blind to G-ROUTE3's outputs or the research diagnosis, and no item is derived from a G-ROUTE3 item. The operator who decided escalations was not blind (declared). 'Gold right → keep' decisions: B′ 38 (34 unchanged, 4 after their fix), A′ 25 (20 unchanged, 5 after their fix); 20 fixtures were fixed once. The corpus reviewers check difficulty parity per pattern (N5).

**G-ROUTE3.** Read only, as the pool's comparison set. Its corpora, gold and frozen detector are byte-identical to the staging checkpoint (digests in the report). It is not rescored or reinterpreted; its identifier-branch defect is disclosed in `sealed/O3_IDENTIFIER_DECISION.md` and not applied backwards.

## Declared blind spots

- **Cross-experiment boilerplate (N3, restated).** A trigram present in all 16 of G-ROUTE3's fixtures of a class becomes boilerplate, and invisible to the cross-experiment check, once about 22 or more G-ROUTE4 fixtures copy it, at pools of about 150 (research 152, conversation 158); not "a few".
- **Entity detector:** sentence-initial words and values at the start of JSON strings; the O6 exact-value comparison covers the latter.
- **Declared exclusions:** closed-vocabulary values offered as allowed sets, and structural ids (`[A-Z][0-9]+`) in structural-id fields only.
- **Signatures:** conversation has none (O4); planning and synthesis are exempt.
- **Difficulty matching** is the authors' judgment, not measured on any model.

## Warnings and latent issues carried to the corpus review

- **A4-SYNTH-R1-01** (final main corpus): SY1 cause under role 'diagnosis'; kept by operator decision (all three answers reached the gold conclusion; the only disagreement was a code fence).
- **B4-SYNTH-R1-02** (final main corpus): SY1 cause under role 'diagnosis'; kept (first adjudicator agreed).
- **B4-SYNTH-R2-15** (final main corpus): SY1 cause under role 'diagnosis'; kept (first adjudicator agreed).
- **B4-SYNTH-R3-08** (final main corpus): SY1 cause under role 'diagnosis'; kept (first adjudicator agreed).
- **Unused reserves with known defects** (never drawn, never sent): P6 'only': A4-RSRCH-R2-X02, A4-RSRCH-R4-X03, B4-RSRCH-R1-X06, B4-RSRCH-R1-X14, B4-RSRCH-R2-X06, B4-RSRCH-R2-X14, B4-RSRCH-R3-X06, B4-RSRCH-R3-X14; SY1 diagnosis role: A4-SYNTH-R1-X01, A4-SYNTH-R2-X03, A4-SYNTH-R4-X01, B4-SYNTH-R1-X01, B4-SYNTH-R3-X03; weak anonymity paraphrase: B4-RSRCH-R3-X03; weak weekend (courier) paraphrase: B4-RSRCH-R2-X04.
- Under step 10, a change driven by the corpus review goes through a fix (the fixture's one fix; the 20 fixed fixtures have used theirs) or a replacement, with re-adjudication, and the independence checks are re-run.
- Adjudication disagreements were dominated by code-fenced JSON; see the closure records.

