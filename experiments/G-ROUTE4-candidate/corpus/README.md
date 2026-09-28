# G-ROUTE4 corpus authoring (pre-seal staging)

Authored to the frozen blueprint at commit `1156d06`. Nothing here is sealed or adjudicated, and no model has been
contacted. **Status: Structured Extraction and Hierarchical Semantic Synthesis authored; the other three classes are not started.**

**Not committed on purpose.** The seal must be the single commit on `main` whose parent is `1156d06`
(`BLUEPRINT_FREEZE.json`, `seal_requirement`). Any earlier commit on `main` would break that, so this folder stays in
the working tree until the seal.

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

Run:

```
python -B author_extraction.py
python -B author_synthesis.py
python -B check_corpus.py staging/extraction.json staging/synthesis.json
python -B test_check_corpus.py staging/extraction.json
python -B test_synthesis_corpus.py staging/extraction.json staging/synthesis.json
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
