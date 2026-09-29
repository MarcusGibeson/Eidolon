"""Build or verify the committed name-stream artifact (name_stream.json). Needs the local spell-checker dictionaries.

    python -B build_name_stream.py --write     # derive the stream from the dictionary and write the artifact
    python -B build_name_stream.py --verify    # re-derive the stream and confirm the committed artifact matches
    python -B build_name_stream.py --replay    # no dictionary: replay from the committed rejections (name_stream.py)

Procedure (deterministic): decode the en_US and en_GB cspell tries (english_vocabulary.py), lowercase the ASCII
words, and screen the frozen syllable bank (names.py, seed "G-ROUTE4 names") against that set, G-ROUTE3's detected
entities and lineages, and every earlier draw. The per-class draw counts are fixed by the class authors:
extraction 96 (its fixtures' names), synthesis 3 or 5 per fixture by band, planning 1, conversation 4, research 2.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from names import NameBank  # noqa: E402
from name_stream import ARTIFACT, CLASS_ORDER, stream_digest  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
EXTRACTION_DRAWS = 96      # fixed by the preserved Extraction authoring (its declared invented names)


def class_draws():
    slots = BLUEPRINT["slots"]
    synth = sum(5 if s["features"]["obs_band"] == "large" else 3 for s in slots
                if s["task_class"] == "hierarchical_semantic_synthesis")
    count = {tc: sum(1 for s in slots if s["task_class"] == tc) for tc in CLASS_ORDER}
    return {"structured_extraction": EXTRACTION_DRAWS, "hierarchical_semantic_synthesis": synth,
            "reflective_planning": count["reflective_planning"],
            "ordinary_conversation": 4 * count["ordinary_conversation"],
            "grounded_research_synthesis": 2 * count["grounded_research_synthesis"]}


def derive():
    from english_vocabulary import english_vocabulary  # build-time only: --replay never imports the dictionary
    english, provenance = english_vocabulary()
    decoded = hashlib.sha256("\n".join(sorted(english)).encode("utf-8")).hexdigest()
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402  read-only G-ROUTE3 inventory
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    bank = NameBank(english, set(g3_entities) | set(g3_lineages))
    draws = class_draws()
    names = [bank.take() for _ in range(sum(draws.values()))]
    examined = bank._order[:bank._pos]
    # the only facts the replay needs from the dictionary: which examined candidates it rejected as English words.
    # These are individual common words (no dictionary content beyond them is committed).
    rejections = sorted({w for w in examined if w in english})
    return {
        "schema_version": "g-route4.name-stream.v1",
        "names": names, "stream_sha256": stream_digest(names), "class_draws": draws,
        "screen": {
            "syllable_bank": "18 consonants x 5 vowels, 2-3 syllables, seed 'G-ROUTE4 names' (names.py)",
            "english_sources": [{"file": s["file"], "sha256": s["sha256"], "ascii_words": s["ascii_words"]}
                                for s in provenance["sources"]],
            "decoded_lowercase_words": provenance["lowercase_words"],
            "decoded_word_set_sha256": decoded,
            "g3_avoid": {"entities": len(g3_entities), "lineages": len(g3_lineages)},
            "candidates_examined": len(examined),
            "english_rejections": rejections,
            "procedure": "build_name_stream.py --verify re-derives this stream from the same dictionaries; "
                         "name_stream.replay_without_dictionary re-derives it from names.py, G-ROUTE3's inventory "
                         "and english_rejections alone, with no dictionary",
        },
    }


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--verify"
    if mode == "--replay":
        from name_stream import replay_without_dictionary, load_artifact  # noqa: E402
        print("name stream replayed without a dictionary:", replay_without_dictionary(load_artifact()))
        sys.exit(0)
    data = derive()
    if mode == "--write":
        ARTIFACT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print("written", ARTIFACT.name, data["stream_sha256"], len(data["names"]))
    else:
        committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        ok = committed == data
        print("name stream re-derived:", "MATCHES" if ok else "DIFFERS", data["stream_sha256"])
        sys.exit(0 if ok else 1)
