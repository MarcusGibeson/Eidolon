"""The committed G-ROUTE4 invented-name stream (authoring reproducibility without a local dictionary).

The names were drawn once from the frozen syllable bank (names.py) and screened against the English vocabulary
decoded from the locally installed VS Code spell-checker dictionaries (english_vocabulary.py). Those dictionaries
are not vendored: their licences are not ours to redistribute. Instead, name_stream.json commits:

- the exact ordered stream of every name drawn by every class (1,432 names);
- the per-class draw counts, in authoring order;
- the sha256 of the two source dictionary files and of the decoded, sorted lowercase word set, plus the
  procedure, so anyone holding the same dictionaries can re-derive the stream (build_name_stream.py --verify);
- the handful of examined bank candidates that the dictionary rejected as English words (english_rejections), so
  that anyone WITHOUT the dictionary can re-derive the identical stream from names.py and G-ROUTE3's inventory
  (replay_without_dictionary below). The checker runs that replay on every check.

Authors replay names from this artifact. Reproduction FAILS CLOSED: a missing artifact, or one whose digest differs
from the value pinned below, raises instead of silently falling back to a dictionary or a different stream.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARTIFACT = HERE / "name_stream.json"
PINNED_STREAM_SHA256 = "0b73b101d00a558cbbf2f5ae61cdf2cbb07c04400901aafaf85413b04e092230"
CLASS_ORDER = ("structured_extraction", "hierarchical_semantic_synthesis", "reflective_planning",
               "ordinary_conversation", "grounded_research_synthesis")


class NameStreamUnavailable(RuntimeError):
    pass


def stream_digest(names):
    return hashlib.sha256(json.dumps(list(names), ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_artifact(path=ARTIFACT, pinned=PINNED_STREAM_SHA256):
    if not Path(path).is_file():
        raise NameStreamUnavailable(f"name-stream artifact missing: {path} (reproduction fails closed)")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    names = data.get("names")
    if not isinstance(names, list) or stream_digest(names) != data.get("stream_sha256"):
        raise NameStreamUnavailable("name-stream artifact is internally inconsistent (stream_sha256 mismatch)")
    if pinned is not None and data["stream_sha256"] != pinned:
        raise NameStreamUnavailable(f"name-stream artifact digest {data['stream_sha256']} differs from the pinned "
                                    f"{pinned} (reproduction fails closed)")
    if sum(data["class_draws"].values()) != len(names) or list(data["class_draws"]) != list(CLASS_ORDER):
        raise NameStreamUnavailable("name-stream artifact class draws do not account for the stream")
    return data


def replay_without_dictionary(data):
    """Re-derive the stream with no dictionary: the syllable bank consults the English set only for the candidates
    it examines, so the committed rejections stand in for the dictionary exactly. Fails closed on any difference,
    and on a rejection the bank never examined (the list must be exactly the examined English candidates)."""
    from names import NameBank
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402  read-only G-ROUTE3 inventory
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    screen = data.get("screen", {})
    rejections = screen.get("english_rejections")
    if not isinstance(rejections, list) or rejections != sorted(set(rejections)):
        raise NameStreamUnavailable("name-stream artifact has no usable english_rejections list")
    bank = NameBank(set(rejections), set(g3_entities) | set(g3_lineages))
    names = [bank.take() for _ in range(len(data["names"]))]
    examined = bank._order[:bank._pos]
    if names != data["names"]:
        raise NameStreamUnavailable("dictionary-free replay does not reproduce the committed name stream")
    if len(examined) != screen.get("candidates_examined") or not set(rejections) <= set(examined):
        raise NameStreamUnavailable("english_rejections are not exactly examined candidates")
    return {"names": len(names), "candidates_examined": len(examined), "english_rejections": len(rejections),
            "stream_sha256": stream_digest(names)}


class NameStream:
    def __init__(self, path=ARTIFACT):
        self.data = load_artifact(path)
        self.names = self.data["names"]
        self.position = 0

    def take(self, n=1):
        if self.position + n > len(self.names):
            raise NameStreamUnavailable("name stream exhausted; the committed artifact must be rebuilt first")
        out = self.names[self.position:self.position + n]
        self.position += n
        return out

    def skip_through(self, task_class):
        """Advance past every class up to and including task_class, in authoring order."""
        total = 0
        for tc in CLASS_ORDER:
            total += self.data["class_draws"][tc]
            if tc == task_class:
                break
        else:
            raise KeyError(task_class)
        self.position = total

    def provenance(self):
        return {"artifact": "name_stream.json", "stream_sha256": self.data["stream_sha256"],
                "names": len(self.names), "screen": self.data["screen"]}
