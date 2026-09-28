# G-ROUTE4 corpus authoring (pre-seal staging)

Authored to the frozen blueprint at commit `1156d06`. Nothing here is sealed or adjudicated, and no model has been
contacted. **Status: all five classes are authored and pass together; the complete-corpus pre-seal review has not
started.**

**Not on `main` on purpose.** The seal must be the single commit on `main` whose parent is `1156d06`
(`BLUEPRINT_FREEZE.json`, `seal_requirement`). Any earlier commit on `main` would break that, so this folder lives only
on the `g-route4/authoring-staging` branch until the seal. That branch is never merged.

## Files

| File | Role |
|---|---|
| `author_extraction.py` | The 106 extraction slot specs. Derived gold is computed with exact decimal and calendar arithmetic. Writes `staging/extraction.json`. |
| `author_synthesis.py` | The 100 synthesis slots, including role binding, merges, conclusions, rationales and reserves. Replays Extraction's names, then continues the same stream. Writes `staging/synthesis.json`. |
| `names.py` | Invented names from the frozen syllable bank (18 consonants × 5 vowels, 2–3 syllables), seeded and deterministic. |
| `english_vocabulary.py` | The English word list used for the name screen (see below). |
| `check_corpus.py` | Every text-dependent rule of blueprint §3, §4, §6, §7 and §13. Writes `staging/CHECK_REPORT.json`. |
| `test_check_corpus.py` | Plants one defect per rule and confirms the checker catches each (16 of 16). |
| `test_synthesis_corpus.py` | Plants nine Synthesis-specific defects and confirms every new check fires over the combined pool. |
| `author_planning.py` | The 100 planning slots: 100 fresh scenarios (30 R1, 30 R2, 30 R3, 10 R4), each cut to its slot's frozen family counts. Gold is computed from the prefix rule, the precedence chain, the addresses and the holding codes. Replays all 492 earlier names, then assigns ordinals 493–592. Writes `staging/planning.json`. |
| `test_planning_corpus.py` | Plants 19 Planning and supplementary-identifier defects and confirms each fires over the combined pool. |
| `author_conversation.py` | The 142 Conversation slots, with exactly four options, recomputable family/depth conditions, frozen answer positions, one near miss and all reserves. Replays all 592 earlier names, then assigns ordinals 593–1160. Writes `staging/conversation.json`. |
| `test_conversation_corpus.py` | Plants 16 Conversation, reserve, O6 and N1 defects and confirms each fires over the four-class pool. |
| `author_research.py` | The 136 Grounded Research slots, including claim/source ledgers, lineage identity, scope, temporal governance, deterministic status/gold derivation, rationales and reserves. Replays all 1,160 earlier names, then assigns ordinals 1161–1432. Writes `staging/research.json`. |
| `test_research_corpus.py` | Plants 29 Research, lineage, temporal, scope, reserve and canonical-gold defects and confirms each fires over the complete five-class pool. |

Run:

```
python -B author_extraction.py
python -B author_synthesis.py
python -B author_planning.py
python -B author_conversation.py
python -B author_research.py
python -B check_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json staging/conversation.json staging/research.json
python -B test_check_corpus.py staging/extraction.json
python -B test_synthesis_corpus.py staging/extraction.json staging/synthesis.json
python -B test_planning_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json
python -B test_conversation_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json staging/conversation.json
python -B test_research_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json staging/conversation.json staging/research.json
```

## Decisions recorded for review

- **"The English vocabulary" (blueprint §4) names no word list.** The screen uses the en_US and en_GB dictionaries of
  the locally installed VS Code spell checker (359,358 lowercase words), read-only, with nothing downloaded. File
  digests are in `CHECK_REPORT.json`. A different list would only re-screen names, deterministically.
- **O3 vocabulary.** The lowercase vocabulary is computed per class pool, as the design declares. For G-ROUTE3
  fixtures, the entity set is also computed with G-ROUTE3's own all-corpus vocabulary, and the union is used. This
  is the stricter reading.
- **Name continuity.** Later classes must continue the same name-bank sequence, or pass every used name as `avoid`.
  Checking all staged classes together catches any reuse.
- **Synthesis name continuity.** The authoring script replays and asserts all 96 Extraction draws before assigning
  Synthesis ordinals 97-492. The two vocabulary source digests remain unchanged.
- **O5 is vacuous in extraction.** The largest family has 18 of 122 pool fixtures, and the boilerplate threshold is
  30.5, so no single-family trigram can become boilerplate here.
- **O5 remains non-triggerable for a Synthesis-only family.** Its pool is 116 and the threshold is 29, while the
  largest Synthesis family has 17 authored fixtures. The checker still reports all 13 boilerplate trigrams and
  confirms that zero are specific to one family.
- **Self-review against G-ROUTE3.** After the mechanical checks passed, a read-through found four drafts that
  shared a scenario with a G-ROUTE3 item. The design's rule is that no item is derived from a G-ROUTE3 item, so all
  four were replaced and every check was re-run:

  | Slot | Draft scenario | G-ROUTE3 item it resembled |
  |---|---|---|
  | A4-EXTR-R1-01 | library hold | A-EXTRACT-R1-1 |
  | A4-EXTR-R2-02 | expense against a limit | A-EXTRACT-R2-1 |
  | A4-EXTR-R3-02 | "today is" overdue check | B-EXTRACT-R4-1 |
  | B4-EXTR-R3-16 | password length against a minimum | B-EXTRACT-R3-1 |

  Each replacement keeps the slot's family, field types and derived count.

- **Synthesis similarity replacements.** The first deterministic draft reused family wording too heavily and was
  rejected with 324 Jaccard violations. Per-observation invented sources and distinct context wording reduced that
  to three; sector-specific scenario replacements reduced it to one. `B4-SYNTH-R2-18` then received a fresh
  discrepancy-note rendering, preserving SY2, `mergeable_pair=no` and `obs_band=small`. The final combined maximum
  is 0.1929 with zero pairs above 0.20.

### Planning

- **Finding: G-ROUTE3's frozen identifier detector is dead code.** In `tools/g_route3_independence.py`, line 57
  wraps the identifier pattern in literal backspace bytes (`\x08`). It therefore never matches, and only
  capitalized-name detection works. G-ROUTE3's own "0 shared identifiers" and the Extraction staging report's
  identifier claim both rested on it. The frozen tool is untouched. `check_corpus.py` adds a separately reported
  **supplementary** screen with the evident intended pattern (`\b…\b`), excluding the design's structural ids. It
  finds 17 G-ROUTE4 and 11 G-ROUTE3 identifiers, with 0 shared. How the forked detector handles this is an operator
  decision before the fork and seal.
- **Metadata fix from that screen.** `B4-EXTR-R2-15` had declared its identifier as `KV-3390.`, with a trailing
  period. It now declares `KV-3390`, and no fixture or gold byte changed.
- **Name continuity.** The script replays and asserts all 492 Extraction and Synthesis draws, then assigns one name
  per planning fixture (ordinals 493–592).
- **PL5 reading.** "One action addresses two evidence items" is realized strictly: exactly one allowed action has
  exactly two addresses, and every other action has one. The existential reading ("some action addresses two")
  would hold in every family and make PL5 indistinguishable. To keep the marker unique, every other family has at
  least two multi-address actions, and both properties are checked.
- **Construction conventions (checked, not frozen rules).**
  - Evidence F1 is a context fact, followed by the precedences and then the unknown statements. Precedences are in
    chain order, except PL4, which lists them out of order as frozen.
  - Offered uncertainty codes are max(2, holding + 1), so at least one code never holds.
  - Evidence ids stay single-digit structural ids.
- **No frozen 40-verb list.** The blueprint's capacity arithmetic (`build_blueprint.py`) mentions "a frozen 40-verb
  list × invented object names", but no such list is frozen anywhere. Actions are plain snake_case English. All 515
  are unique across G-ROUTE4 and against G-ROUTE3, which is checked both by the §4 action rule and by O6.
- **O5 stays vacuous for Planning.** The pool is 116 and the threshold is 29, while the largest planning family has
  19 fixtures. The checker reports the 34 boilerplate trigrams, none of which is specific to one family.
- **Similarity replacements.** Three drafts were too close in substance to a G-ROUTE3 planning item, and one had an
  excluded action that echoed one. All were changed with each slot's family and precedence form preserved:

  | Slot | Draft | G-ROUTE3 item it resembled | Replacement |
  |---|---|---|---|
  | B4-PLAN-R3-11 | authentication log archive (size, verified copy, delete excluded) | A-PLAN-R2-1 invoice archive migration | staff photo consent refresh |
  | B4-PLAN-R3-18 | app key inventory (owners and scopes, rotate excluded) | A-PLAN-R3-2 admin password change | claims office clear-desk sweep |
  | A4-PLAN-R2-04 | expense consolidation with category coding | A-PLAN-R2-2 budget spreadsheet categories | category step and code reworded |
  | B4-PLAN-R3-01 | contractor offboarding with `wipe_contractor_laptop` excluded | A-PLAN-R3-1 remote wipe | excluded action changed to `disable_contractor_logins` |
- **Wording fix.** 33 plural uncertainty subjects (for example "the exhibitor rules") were made singular, so every
  condition "evidence says … is unknown" and every matching evidence sentence is grammatical.
- **Result.** Planning alone: 100 fixtures, 0 problems, maximum Jaccard 0.0619. Combined corpus: 306 fixtures, 0
  problems. Adversarial suites: 19/19 (Planning), 16/16 (Extraction), 9/9 (Synthesis).

### Conversation

- **Frozen shape.** Every fixture has four invented-name options. The checker independently recomputes two
  conditions from the supplied candidate data: exactly one option satisfies both, exactly one satisfies only the
  first, and two satisfy neither. At depth 2 the near miss therefore completes the first step correctly and fails
  the second. Gold position, the declared near miss, the 600-character contract and the disclosed frame are checked.
- **Name continuity.** The author replays and asserts all 592 prior names, then assigns four names per Conversation
  fixture, ordinals 593–1160. The frozen US and UK vocabulary digests are unchanged.
- **Validator routing.** The authoring checker now calls G-ROUTE3's frozen operational and semantic wrappers. Those
  wrappers implement the disclosed Conversation frame and delegate every other profile to the unchanged G-ROUTE1
  validators. No validator source or accepted sentence changed.
- **Identifier handling.** G-ROUTE3's historical backspace-regex defect remains untouched. The separately named
  supplementary G-ROUTE4 screen remains required and reports zero shared identifiers.
- **O5 remains non-triggerable for a Conversation-only family.** The class pool is 158, so boilerplate requires 40
  occurrences, while the largest family has 24 fixtures. All 63 detected boilerplate trigrams are still checked;
  zero are specific to one family.
- **Similarity replacements.** The first compact numeric rendering failed 265 pairwise Jaccard checks. Adding
  fixture-specific provenance context reduced this to 16 and then one. `B4-CONV-R3-X04` received one final fresh
  provenance sentence while preserving CV6, depth 2, position 4 and its reserve match. The final maximum is 0.1953
  (`B4-CONV-R1-28` vs `A4-CONV-R3-X04`), with zero pairs above 0.20.
- **Result.** Conversation alone: 142 fixtures, 0 problems. Four-class corpus: 448 fixtures, 0 problems. All 142
  fixtures have four options and one compliant near miss; all 41 reserves match; the Conversation adversarial suite
  catches 16/16 planted defects.

### Grounded Research

- **Frozen shape and balance.** The class contains 136 fixtures: 16 A main, 55 B main, 16 A reserves and 49 B
  reserves. The frozen P1-P8 allocation is exact, including the two P7/SLS R4 evidence-only fixtures. Across 341
  claims, statuses are 145 supported, 142 contradicted and 54 unresolved. The uncertainty ledger contains 69
  single-lineage, 20 unaddressed-claim, 17 conflicting-source and 17 scope-mismatch findings.
- **Lineage and citation fidelity.** The model-facing records preserve the G-ROUTE3 research schema while an
  authoring-only semantic ledger independently binds every claim, source, relation, lineage, date and quantitative
  value. Gold and rationales are recomputed from that ledger. There are 607 source records, 590 cited source
  bindings, 482 distinct cited-lineage bindings and 499 unique lineages; no lineage crosses a fixture boundary.
- **Temporal and scope cases.** All 18 P7 cases contain two differently dated, conflicting sources and an explicit
  later-source rule with both sources cited. All 17 P6 cases bind a narrower source scope to a broader claim and
  remain unresolved. P3 alternate-subject evidence, P8 below-threshold contradiction direction and support versus
  same-lineage repetition are independently checked.
- **Name and identifier continuity.** The author replays and asserts all 1,160 prior names, then assigns two names per
  Research fixture, ordinals 1161–1432. The frozen US and UK vocabulary digests remain unchanged. G-ROUTE3's frozen
  identifier checker remains untouched and the supplementary intended screen remains mandatory.
- **Construction rewrites.** The first P8 construction used one quantitative source and produced six A/B fine-
  signature clashes with P2. It was replaced prospectively with two independent, mutually consistent below-
  threshold sources. One remaining P7/P8 signature clash was removed with an equivalent P7 decision-rule wording.
  A first generic provenance expansion worsened overlap from 8 to 34 failing pairs and was discarded. Record-
  specific provenance with unique ledger-path values reduced the final Research maximum Jaccard to 0.1510
  (`B4-RSRCH-R1-07` vs `B4-RSRCH-R4-01`), with zero pairs above 0.20. No frozen slot, family, feature or gold rule was
  changed.
- **O5 and pooled obligations.** The Research comparison pool is 152 and its boilerplate threshold is 38, while the
  largest family has 25 fixtures. All 45 detected boilerplate trigrams are still checked; zero are specific to one
  family. The complete five-class pool has 584 fixtures, 1,432 invented names, zero O3 entity/identifier overlap,
  zero O6 exact-value collisions, zero N1 canonical-gold duplicates and zero fine-signature clashes.
- **Result.** Research alone: 136 fixtures, 0 problems. Five-class corpus: 584 fixtures, 0 problems. All 65 Research
  reserves match a main slot, and the Research adversarial suite catches 29/29 planted defects. Across every class,
  all 89/89 planted defects are caught. No model or adjudicator was contacted, and no seal was created.
