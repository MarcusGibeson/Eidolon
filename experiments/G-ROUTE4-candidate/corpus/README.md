# G-ROUTE4 corpus authoring (pre-seal staging)

Authored to the frozen blueprint at commit `1156d06`. Nothing here is sealed or adjudicated, and no model has been
contacted. **Status: all five classes are authored and pass together after the pre-seal repair; a fresh complete-
corpus pre-seal review of the repaired checkpoint comes next. No seal exists.**

**Not on `main` on purpose.** The seal must be the single commit on `main` whose parent is `1156d06`
(`BLUEPRINT_FREEZE.json`, `seal_requirement`). Any earlier commit on `main` would break that, so this folder lives only
on the `g-route4/authoring-staging` branch until the seal. That branch is never merged.

## Files

| File | Role |
|---|---|
| `author_extraction.py` | The 106 extraction slot specs (preserved). Derived gold is computed with exact decimal and calendar arithmetic. Writes `staging/extraction.json`. |
| `author_synthesis.py` | The 100 synthesis slots (re-authored in the repair): one-sentence observations at G-ROUTE3-comparable length, role binding, merges, conclusions, substantive required terms, rationales and reserves. Writes `staging/synthesis.json`. |
| `author_planning.py` | The 100 planning slots (preserved). Writes `staging/planning.json`. |
| `author_conversation.py` | The 142 Conversation slots (re-authored in the repair): natural first-person requests with real clock times, dates, units and prices, and a ledger binding every sentence to the facts the answer depends on. Writes `staging/conversation.json`. |
| `author_research.py`, `research_topics.py` | The 136 Grounded Research slots (re-authored in the repair): natural claims, independent paraphrased sources from meaningful publisher lineages, value-only P8 sources, and an unambiguous P7 construction. Writes `staging/research.json`. |
| `names.py` | The frozen syllable bank (18 consonants × 5 vowels, 2–3 syllables), seeded and deterministic. |
| `name_stream.py`, `name_stream.json` | The committed invented-name stream (1,432 names) and its dictionary-free replay. Every author reads names from here; a missing or altered artifact fails closed. |
| `build_name_stream.py`, `english_vocabulary.py` | Build-time only: derive or verify the stream from the local spell-checker dictionaries (`--write`, `--verify`), or replay it without them (`--replay`). Nothing else imports the dictionary. |
| `check_corpus.py` | Every text-dependent rule of blueprint §3, §4, §6, §7 and §13, plus the pre-seal repair gates. Writes `staging/CHECK_REPORT.json`. |
| `seal_layout.py`, `SEAL_LAYOUT.md` | The future seal layout and its blind-separation check. Defines the seal; creates none. |
| `adjudicator_config.py`, `staging/ADJUDICATOR_CONFIG.json` | The O2 adjudicator configuration, prepared and digested for the seal (not frozen; no contact). |
| `O3_IDENTIFIER_DECISION.md` | The recorded O3 identifier decision. |
| `test_check_corpus.py` | 16 Extraction and pooled-rule defects. |
| `test_synthesis_corpus.py` | 9 Synthesis defects. |
| `test_planning_corpus.py` | 19 Planning and O3 identifier-gate defects. |
| `test_conversation_corpus.py` | 16 Conversation, reserve, O6 and N1 defects. |
| `test_research_corpus.py` | 29 Research, lineage, temporal, scope, reserve and canonical-gold defects. |
| `test_repairs_corpus.py` | 38 pre-seal repair gates and proofs (see below). |

Run (no dictionary, network or model is needed; the tokenizer file is read from the local tiktoken cache only):

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
python -B test_repairs_corpus.py staging/extraction.json staging/synthesis.json staging/planning.json staging/conversation.json staging/research.json
python -B build_name_stream.py --replay
python -B adjudicator_config.py
```

## Pre-seal repair (after the complete-corpus review of 14e4e06)

The review returned NOT_READY. The accepted design, the frozen blueprint and G-ROUTE3 are unchanged; every slot keeps
its family, features, risk, phase and role. Extraction and Planning fixtures, gold and design records are
byte-identical (only their staging metadata now names the committed name stream).

- **Filler removed (Conversation, Synthesis, Research).** The earlier independence pass rested on task-irrelevant
  provenance sentences. With that filler stripped, the 14e4e06 corpus had 290 Conversation, 333 Synthesis and 22
  Research pairs over 0.20 (maxima 0.4583, 0.4792, 0.2941). The repaired classes carry no filler; the task content
  itself is diverse: maxima 0.0976, 0.0764 and 0.1788, with 0 pairs over 0.20.
- **Task-relevant overlap gate.** Every free-text sentence of the three repaired classes is bound to the authoring
  ledger (a Conversation unit carries recomputed facts; a Research claim or source is the authored statement for its
  relation; a Synthesis observation carries substantive required terms), one sentence per unit within a padding cap.
  Overlap is measured a second time on that bound text only. Filler cannot rescue a failing pair: it is either an
  unbound sentence, a sentence over the cap, or removed before measurement (proved in `test_repairs_corpus.py`).
- **Reply length.** Every gold reply, serialized compactly, is at most 250 cl100k_base tokens against the models'
  350-token output cap (`num_predict`). The tokenizer file is pinned by sha256 and read only from the local cache;
  without it the gate measures UTF-8 bytes, a strict upper bound, and fails closed. Synthesis: median 164, maximum
  231 (G-ROUTE3: 167 and 201). Pretty-printed replies are reported as a diagnostic; the largest is Planning's 326
  (preserved class, compact maximum 227).
- **Required terms.** Every Synthesis required term is observation content: it is not a scaffolding word, it cannot
  be satisfied from the title, opening, rule text or role names, and each observation has a term no other
  observation contains. A reply that copies all of the scaffolding but no finding fails the frozen validator for 425
  of 425 observations.
- **Conversation parity.** CV2 states clock times or dates, CV3 states measured quantities with a unit conversion in
  every fixture, CV6 states calendar dates, and nothing is a pre-evaluated flag. Four options, the frozen gold
  position, one near miss and two zero-condition options, and all slot assignments are unchanged.
- **Research parity.** Sources are the authored paraphrases for their relation (never the claim sentence, never the
  claim with a negation inserted), each names its subject, P8 sources report a value only (no threshold, no
  comparison word, as in G-ROUTE3's own P8 items), lineages are region-issuer-channel publisher names, and a repeated
  lineage is written as a reissue. The opening follows "Assess the claims about <subject>". The D8 sentence is
  byte-identical in all 136 prompts.
- **P7 and single_lineage_support.** The code's truth is now required to be the same whether lineages are counted
  over cited or over supporting sources (checked for every Research fixture). B4-RSRCH-R1-15, B4-RSRCH-R2-15,
  B4-RSRCH-R3-15 and A4-RSRCH-R3-X04 are re-authored so the later-dated source denies wherever the code must be
  false.
- **Equivalent decision clauses.** Research signatures are also compared with the decision rule normalized to its
  clause kind (focal two-lineage, all-supported, or temporal all-supported), so rewording cannot hide a repeated gold
  structure between A′ and B′. The A4-RSRCH-R3-04 / B4-RSRCH-R3-X08 clash is resolved by authoring, not by wording:
  0 canonical and 0 frozen-signature clashes.
- **O3 identifier gate.** See `O3_IDENTIFIER_DECISION.md`: the frozen checker stays byte-identical (pinned digest),
  and the pinned supplementary identifier check is the binding prospective gate for G-ROUTE4. G-ROUTE3 is not
  rescored.
- **Dictionary.** Names come from the committed stream. The 37 English words the syllable bank met and rejected are
  committed, so the stream replays exactly with no dictionary; the dictionary digests remain recorded for
  `--verify`. No dictionary content beyond those words is committed.
- **Seal layout and O2.** Defined and tested; no seal and no contact (`SEAL_LAYOUT.md`, `adjudicator_config.py`).
- **Synthesis name draws.** Synthesis text uses no invented names. Its 396 stream draws are kept (so every later
  class keeps its names) and recorded as `unused_stream_draws`, not as invented names.
- **Checker robustness.** A gold whose recommendation is not in its own list is now reported instead of crashing
  the frozen fine-signature computation.

## Decisions recorded for review

- **"The English vocabulary" (blueprint §4) names no word list.** The names were screened once against the en_US and
  en_GB dictionaries of the locally installed VS Code spell checker (359,358 lowercase words), read-only, with
  nothing downloaded. Their file digests, the decoded word-set digest and the 37 English words the bank met are in
  `name_stream.json`; the dictionaries themselves are not ours to redistribute and are not needed to reproduce the
  corpus. A different list would only re-screen names, deterministically.
- **O3 vocabulary.** The lowercase vocabulary is computed per class pool, as the design declares. For G-ROUTE3
  fixtures, the entity set is also computed with G-ROUTE3's own all-corpus vocabulary, and the union is used. This
  is the stricter reading.
- **Name continuity.** Later classes must continue the same name-bank sequence, or pass every used name as `avoid`.
  Checking all staged classes together catches any reuse.
- **Synthesis name continuity.** The authoring script replays and asserts all 96 Extraction draws before assigning
  Synthesis ordinals 97-492. (Since the repair, Synthesis text uses no names; the draws are kept as
  `unused_stream_draws`.)
- **O5 is vacuous in extraction.** The largest family has 18 of 122 pool fixtures, and the boilerplate threshold is
  30.5, so no single-family trigram can become boilerplate here.
- **O5 remains non-triggerable for a Synthesis-only family.** Its pool is 116 and the threshold is 29, while the
  largest Synthesis family has 17 authored fixtures. The checker reports all 11 boilerplate trigrams (after the
  repair) and confirms that zero are specific to one family.
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

- **Synthesis similarity replacements (superseded by the pre-seal repair, which re-authored Synthesis without the
  per-observation filler these relied on).** The first deterministic draft reused family wording too heavily and was
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
  finds 17 G-ROUTE4 and 11 G-ROUTE3 identifiers, with 0 shared. The decision is now recorded in
  `O3_IDENTIFIER_DECISION.md`: the pinned supplementary check is the binding prospective O3 identifier gate.
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

### Conversation (re-authored in the pre-seal repair)

- **Frozen shape.** Every fixture has four invented-name options, the frozen gold position, exactly one near miss that
  meets the first condition and fails the second (at depth 2: a correct first step and a wrong second step), and
  two options that meet neither. All 142 slot assignments are unchanged.
- **Natural requests.** The model-facing input is `answer_options` and a first-person `message`: one request
  sentence and one sentence per option, each stating real facts (clock times, dates, measured quantities with a unit
  conversion, prices, percentages, counts). The authoring ledger (`message_units`) binds every sentence to its facts;
  the checker re-derives each fact's surface, confirms it appears in its sentence, and recomputes both conditions
  with its own implementation. No sentence carries no fact, and nothing is a pre-evaluated flag.
- **Wording fixes during the repair.** Eight CV3 templates stated every quantity in one unit; they now require a
  conversion (for example a plan in kilograms against boxes in grams). Eleven CV4 depth-1 templates with a limit of
  one used a plural noun after it ("at most 1 nights"); the noun is now singular. Values were unchanged by the
  grammar fix.
- **Correction to the earlier record.** The 14e4e06 README described `B4-CONV-R3-X04` as depth 2. Its frozen slot is
  CV6, depth 1, gold position 4, and it is authored to that slot.
- **O5.** The class pool is 158 (boilerplate at 39.5 occurrences) and the largest family has 24 fixtures, so O5 cannot
  trigger; all 7 boilerplate trigrams are checked and none is specific to one family.
- **O6 scope.** Conversation compares every string leaf except `message`, which now means the answer options.
- **Result.** 142 fixtures, 0 problems; maximum Jaccard 0.0976 (`B4-CONV-R2-15` vs `A4-CONV-R3-X03`), identical on
  task-relevant text; gold replies at most 43 tokens; all 41 reserves match.

### Grounded Research (re-authored in the pre-seal repair)

- **Frozen shape and balance.** 136 fixtures: 16 A main, 55 B main, 16 A reserves and 49 B reserves, with the frozen
  P1-P8 allocation exact. Across 341 claims: 147 supported, 140 contradicted and 54 unresolved. Uncertainty ledger:
  69 single-lineage, 20 unaddressed-claim, 17 conflicting-source and 17 scope-mismatch findings.
- **Content.** Claims are natural statements from per-risk topic libraries (`research_topics.py`), two invented
  names per fixture as subjects. Each topic has two support and two denial paraphrases; a source is always one of the
  paraphrases for its relation, never the claim sentence and never the claim with a negation inserted, and it names
  its subject (a P3 source names the other subject only). Independent publishers never share wording: at most two
  lineages state the same relation about a claim, each with its own paraphrase, and a reissue repeats its
  publisher's wording under a reissue marker. Two weak support paraphrases were replaced in the read-through (a
  season-relative lift service date; "loops room by room").
- **P8.** Both sources report a capacity or limit value below the claim's threshold, from different lineages, and
  state neither the threshold nor any comparison word; the contradiction has to be inferred, as in G-ROUTE3's own P8
  items. Nine value statements that did not contradict an "at least" claim (for example "the oldest copy is V days
  old") were replaced by capacity or limit statements.
- **P7.** Two dated notices disagree and the later-dated source governs, with both cited. Wherever the frozen feature
  makes single_lineage_support false, the later source denies, so the code's truth is the same under the cited- and
  the supporting-lineage readings; the checker requires that for every Research fixture.
- **Decisions.** Recommendation pairs are fixture-specific snake_case verbs from per-risk lists. Rules are worded in
  several equivalent ways, and the checker normalizes each rule to its clause kind and compares canonical signatures
  by decision class, so neither rewording nor a temporal clause can hide a repeated gold structure.
- **Lineages.** 476 unique region-issuer-channel publisher names across 607 sources (590 cited bindings, 459
  distinct cited-lineage bindings); none crosses a fixture boundary or matches G-ROUTE3.
- **O5.** Pool 152 (boilerplate at 38) and largest family 25, so O5 cannot trigger; 27 boilerplate trigrams checked,
  none specific to one family.
- **Result.** 136 fixtures, 0 problems; maximum Jaccard 0.1788 (`A4-RSRCH-R3-02` vs `B4-RSRCH-R3-X11`), identical on
  task-relevant text; gold replies at most 179 tokens; all 65 reserves match; 0 frozen and 0 canonical signature
  clashes.

### Complete corpus

584 fixtures, 0 problems: 0 pairs over 0.20 on full and on task-relevant text in every class, 0 O3 shared entities,
0 shared identifiers under the O3 identifier gate, 0 O6 collisions, 0 N1 duplicates, 0 signature clashes, every
reserve matched, every gold reply within 250 tokens. Adversarial suites: 89/89 (old) and 38/38 (repair gates). No
model or adjudicator was contacted, and no seal was created.
