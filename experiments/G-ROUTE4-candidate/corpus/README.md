# G-ROUTE4 corpus authoring (pre-seal staging)

Authored to the frozen blueprint at commit `1156d06`. Nothing here is sealed or adjudicated, and no model has been
contacted. **Status: Structured Extraction authored; the other four classes are not started.**

**Not committed on purpose.** The seal must be the single commit on `main` whose parent is `1156d06`
(`BLUEPRINT_FREEZE.json`, `seal_requirement`). Any earlier commit on `main` would break that, so this folder stays in
the working tree until the seal.

## Files

| File | Role |
|---|---|
| `author_extraction.py` | The 106 extraction slot specs. Derived gold is computed with exact decimal and calendar arithmetic. Writes `staging/extraction.json`. |
| `names.py` | Invented names from the frozen syllable bank (18 consonants × 5 vowels, 2–3 syllables), seeded and deterministic. |
| `english_vocabulary.py` | The English word list used for the name screen (see below). |
| `check_corpus.py` | Every text-dependent rule of blueprint §3, §4, §6, §7 and §13. Writes `staging/CHECK_REPORT.json`. |
| `test_check_corpus.py` | Plants one defect per rule and confirms the checker catches each (16 of 16). |

Run:

```
python -B author_extraction.py
python -B check_corpus.py staging/extraction.json
python -B test_check_corpus.py staging/extraction.json
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
- **O5 is vacuous in extraction.** The largest family has 18 of 122 pool fixtures, and the boilerplate threshold is
  30.5, so no single-family trigram can become boilerplate here.
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
