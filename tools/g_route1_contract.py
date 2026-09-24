from __future__ import annotations

"""Pure identities and loaders for the design-only G-ROUTE1 fixture freeze."""

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-ROUTE1-candidate"
CORPUS_PATH = DATA / "corpus.json"
GOLD_PATH = DATA / "gold.json"
EXPECTED_FIXTURES = 24
TASK_CLASSES = (
    "ordinary_conversation",
    "structured_extraction",
    "grounded_research_synthesis",
    "hierarchical_semantic_synthesis",
    "coding_generation_repair",
    "reflective_planning",
)
RISK_CLASSES = ("R1", "R2", "R3", "R4")
MODEL_TIERS = ("small", "mid", "large")


def canonical_bytes(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_digest(value: bytes | str) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_file(path: str | Path) -> str:
    return canonical_digest(Path(path).read_bytes())


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_corpus(path: str | Path = CORPUS_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    fixtures = list(payload.get("fixtures") or [])
    if payload.get("schema_version") != "g-route1.fixture-corpus.v1":
        raise ValueError("corpus_schema_mismatch")
    if len(fixtures) != EXPECTED_FIXTURES:
        raise ValueError("corpus_fixture_count_mismatch")
    ids = [str(row.get("fixture_id") or "") for row in fixtures]
    if len(set(ids)) != EXPECTED_FIXTURES or any(not value for value in ids):
        raise ValueError("corpus_fixture_identity_mismatch")
    required = {
        "fixture_id", "task_class", "consequence_risk", "title",
        "validator_profile", "prompt", "input",
    }
    for row in fixtures:
        if set(row) != required:
            raise ValueError(f"corpus_fixture_schema_mismatch:{row.get('fixture_id')}")
        if row["task_class"] not in TASK_CLASSES:
            raise ValueError(f"corpus_task_class_mismatch:{row['fixture_id']}")
        if row["consequence_risk"] not in RISK_CLASSES:
            raise ValueError(f"corpus_risk_class_mismatch:{row['fixture_id']}")
    if tuple(payload.get("model_tiers") or ()) != MODEL_TIERS:
        raise ValueError("corpus_model_tier_mismatch")
    if payload.get("model_input_contains_gold") is not False:
        raise ValueError("corpus_gold_exposure")
    return payload


def load_gold(path: str | Path = GOLD_PATH) -> dict[str, Any]:
    payload = dict(load_json(path))
    items = list(payload.get("items") or [])
    if payload.get("schema_version") != "g-route1.gold.v1":
        raise ValueError("gold_schema_mismatch")
    if payload.get("model_input") is not False:
        raise ValueError("gold_marked_as_model_input")
    if len(items) != EXPECTED_FIXTURES:
        raise ValueError("gold_item_count_mismatch")
    ids = [str(row.get("fixture_id") or "") for row in items]
    if len(set(ids)) != EXPECTED_FIXTURES:
        raise ValueError("gold_item_identity_mismatch")
    for row in items:
        if set(row) != {"fixture_id", "expected", "rationale"}:
            raise ValueError(f"gold_item_schema_mismatch:{row.get('fixture_id')}")
    return payload


def indexed_fixture_gold(
    corpus: dict[str, Any] | None = None,
    gold: dict[str, Any] | None = None,
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    corpus_value = corpus or load_corpus()
    gold_value = gold or load_gold()
    fixtures = {row["fixture_id"]: row for row in corpus_value["fixtures"]}
    judgments = {row["fixture_id"]: row for row in gold_value["items"]}
    if set(fixtures) != set(judgments):
        raise ValueError("corpus_gold_identity_mismatch")
    return {key: (fixtures[key], judgments[key]) for key in fixtures}


__all__ = [
    "ROOT", "DATA", "CORPUS_PATH", "GOLD_PATH", "EXPECTED_FIXTURES",
    "TASK_CLASSES", "RISK_CLASSES", "MODEL_TIERS", "canonical_bytes",
    "canonical_digest", "digest_file", "load_json", "load_corpus",
    "load_gold", "indexed_fixture_gold",
]
