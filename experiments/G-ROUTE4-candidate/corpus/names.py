"""Invented names from the frozen syllable bank (blueprint §4: 18 consonants x 5 vowels, 2 or 3 syllables).

Each name is screened, before use, against:
- the English vocabulary (a word list decoded from a local, already-installed spell-checker dictionary; see
  english_vocabulary.py for its provenance and digest);
- G-ROUTE3's detected entities and research lineages (G-ROUTE3's own detector and lowercase-vocabulary rule);
- every name already handed out in G-ROUTE4.
The pool-vocabulary screen (a name whose lowercase form occurs in the pool is invisible to the detector) is run by
the checker over the final pool.
"""

import itertools
import random

CONSONANTS = "bdfghjklmnprstvwyz"          # 18
VOWELS = "aeiou"                           # 5
SYLLABLES = [c + v for c in CONSONANTS for v in VOWELS]
assert len(SYLLABLES) == 90


class NameBank:
    def __init__(self, english: set[str], avoid: set[str], seed: str = "G-ROUTE4 names"):
        rng = random.Random(seed)
        three = ["".join(p) for p in itertools.product(SYLLABLES, repeat=3)]
        two = ["".join(p) for p in itertools.product(SYLLABLES, repeat=2)]
        rng.shuffle(three)
        rng.shuffle(two)
        # mostly three-syllable names, which are rarely English words; every fifth draw is two-syllable
        self._order = []
        t, w = iter(three), iter(two)
        for i in itertools.count():
            try:
                self._order.append(next(w) if i % 5 == 4 else next(t))
            except StopIteration:
                break
            if len(self._order) >= 20000:
                break
        self._english = english
        self._avoid = {a.casefold() for a in avoid}
        self._used: set[str] = set()
        self._pos = 0

    def take(self) -> str:
        while True:
            raw = self._order[self._pos]
            self._pos += 1
            if raw in self._english or raw in self._avoid or raw in self._used:
                continue
            # no name may contain, or be contained in, a name already handed out (keeps entity sets disjoint)
            if any(raw in u or u in raw for u in self._used):
                continue
            self._used.add(raw)
            return raw.capitalize()
