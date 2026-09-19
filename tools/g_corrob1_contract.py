from __future__ import annotations

"""Pure G-CORROB1-R2 identities, prompt construction, and call scheduling.

This module performs no provider contact, persistence, scoring, or Activity work.
Semantic requests contain only the frozen prompt and provider generation options.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-CORROB1-candidate-r2"
CONTRACT_VERSION = "g-corrob1.r2.implementation-candidate.1"
BELIEF_EFFECTS = "none"
ROLES = ("A", "B")
REPEATS = 3
EXPECTED_ITEMS = 32
EXPECTED_PAIRS = 96
EXPECTED_CALLS = 192


def canonical_bytes(data: bytes | str) -> bytes:
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_digest(data: bytes | str) -> str:
    return hashlib.sha256(canonical_bytes(data)).hexdigest()


def digest_file(path: str | Path) -> str:
    return canonical_digest(Path(path).read_bytes())


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_corpus(path: Path | None = None) -> list[dict[str, Any]]:
    payload = load_json(path or DATA / "corpus.json")
    items = list(payload.get("items") or [])
    if len(items) != EXPECTED_ITEMS or len({str(row.get("item_id")) for row in items}) != EXPECTED_ITEMS:
        raise ValueError("corpus_identity_or_count_mismatch")
    required = {"item_id", "proposition_id", "evidence_id", "proposition", "intended_use", "evidence"}
    for row in items:
        if set(row) != required:
            raise ValueError(f"corpus_item_schema_mismatch:{row.get('item_id')}")
    return items


def load_sampling(path: Path | None = None) -> dict[str, Any]:
    return dict(load_json(path or DATA / "sampling_proposal.json"))


def prompt_template(path: Path | None = None) -> str:
    # The checked-in text artifact has a conventional final file newline; the
    # frozen G-EVID1 in-memory template does not. Provider bytes must match it.
    return (path or DATA / "prompt.txt").read_text(encoding="utf-8").rstrip("\r\n")


def build_prompt(item: Mapping[str, Any], template: str | None = None) -> str:
    return (template if template is not None else prompt_template()).format(
        proposition_id=item["proposition_id"], proposition=item["proposition"],
        intended_use=item["intended_use"], evidence_id=item["evidence_id"], evidence=item["evidence"],
    )


def seed_for(item_id: str, repeat: int, role: str) -> int:
    if role not in ROLES or repeat not in range(1, REPEATS + 1):
        raise ValueError("invalid_seed_identity")
    source = f"G-CORROB1-R2-seed-v1|{item_id}|{repeat}|{role}"
    value = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF
    return value or 1


@dataclass(frozen=True)
class ScheduledCall:
    call_id: str
    pair_id: str
    item_id: str
    repeat: int
    role: str
    ordinal: int
    pair_ordinal: int
    seed: int

    def identity(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id, "pair_id": self.pair_id, "item_id": self.item_id,
            "repeat": self.repeat, "role": self.role, "ordinal": self.ordinal,
            "pair_ordinal": self.pair_ordinal, "seed": self.seed,
        }


def build_schedule(items: Iterable[Mapping[str, Any]] | None = None) -> list[ScheduledCall]:
    rows = list(items if items is not None else load_corpus())
    indexed = {str(row["item_id"]): index for index, row in enumerate(rows, 1)}
    pairs = []
    for item_id in indexed:
        for repeat in range(1, REPEATS + 1):
            order_key = hashlib.sha256(f"G-CORROB1-R2-order-v1|{item_id}|{repeat}".encode("utf-8")).hexdigest()
            pairs.append((order_key, item_id, repeat))
    pairs.sort()
    calls: list[ScheduledCall] = []
    ordinal = 0
    for pair_ordinal, (_, item_id, repeat) in enumerate(pairs, 1):
        roles = ROLES if (indexed[item_id] + repeat) % 2 == 0 else tuple(reversed(ROLES))
        pair_id = f"{item_id}-r{repeat}"
        for role in roles:
            ordinal += 1
            calls.append(ScheduledCall(
                call_id=f"{pair_id}-{role}", pair_id=pair_id, item_id=item_id, repeat=repeat,
                role=role, ordinal=ordinal, pair_ordinal=pair_ordinal, seed=seed_for(item_id, repeat, role),
            ))
    if len(calls) != EXPECTED_CALLS or len({row.call_id for row in calls}) != EXPECTED_CALLS:
        raise AssertionError("schedule_call_count_or_identity_mismatch")
    if len({row.pair_id for row in calls}) != EXPECTED_PAIRS:
        raise AssertionError("schedule_pair_count_mismatch")
    first_roles = [calls[i].role for i in range(0, len(calls), 2)]
    if first_roles.count("A") != 48 or first_roles.count("B") != 48:
        raise AssertionError("schedule_order_balance_mismatch")
    if len({row.seed for row in calls}) != EXPECTED_CALLS:
        raise AssertionError("schedule_seed_collision")
    return calls


def generation_options(seed: int, sampling: Mapping[str, Any] | None = None) -> dict[str, Any]:
    proposal = dict(sampling or load_sampling())
    source = dict(proposal.get("parameters") or {})
    expected = {"temperature", "top_p", "top_k", "min_p", "repeat_penalty", "num_ctx", "num_predict", "stop", "stream"}
    if set(source) != expected:
        raise ValueError("sampling_parameter_schema_mismatch")
    if source.pop("stream") is not False:
        raise ValueError("sampling_stream_must_be_false")
    return {**source, "seed": int(seed)}


def semantic_http_body(item: Mapping[str, Any], call: ScheduledCall,
                       sampling: Mapping[str, Any] | None = None) -> dict[str, Any]:
    proposal = dict(sampling or load_sampling())
    return {
        "model": str(proposal["model_name"]),
        "prompt": build_prompt(item),
        "stream": False,
        "format": "json",
        "options": generation_options(call.seed, proposal),
    }


def request_receipt(item: Mapping[str, Any], call: ScheduledCall,
                    sampling: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = semantic_http_body(item, call, sampling)
    return {
        **call.identity(),
        "prompt_sha256": canonical_digest(body["prompt"]),
        "submitted_body_sha256": canonical_digest(json.dumps(body, sort_keys=True, separators=(",", ":"))),
        "model": body["model"],
        "options": dict(body["options"]),
        "stream": False,
        "structured_json": True,
        "fresh_session_required": True,
        "belief_effects": BELIEF_EFFECTS,
    }


def assert_minimal_semantic_body(body: Mapping[str, Any]) -> None:
    if set(body) != {"model", "prompt", "stream", "format", "options"}:
        raise ValueError("semantic_request_contains_extra_metadata")
    serialized = json.dumps(body, sort_keys=True).casefold()
    forbidden = ("gold_relation", "gold_scope", "gold_temporal", "expected_disposition",
                 "use_permitted", "unsafe_use", "scorer_result", "other_assessment")
    if any(token in serialized for token in forbidden):
        raise ValueError("semantic_request_evaluation_leakage")


__all__ = [
    "ROOT", "DATA", "CONTRACT_VERSION", "BELIEF_EFFECTS", "ROLES", "REPEATS", "EXPECTED_ITEMS",
    "EXPECTED_PAIRS", "EXPECTED_CALLS", "ScheduledCall", "canonical_bytes", "canonical_digest",
    "digest_file", "load_json", "load_corpus", "load_sampling", "prompt_template", "build_prompt",
    "seed_for", "build_schedule", "generation_options", "semantic_http_body", "request_receipt",
    "assert_minimal_semantic_body",
]
