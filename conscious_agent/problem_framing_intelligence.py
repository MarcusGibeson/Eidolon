from __future__ import annotations

"""Era 3 problem framing and clarification judgment.

The module turns a private operator request into a bounded, attributable problem
frame without granting execution authority.  Private request text remains in the
external runtime record; public projections expose only bounded semantic items
and digests.  Corrections are revision/digest bound so stale UI controls fail
closed.
"""

from collections import defaultdict
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1725.9"
SCHEMA_VERSION = "1"
MAX_TEXT = 12000
MAX_ITEMS = 32
MAX_ITEM_CHARS = 320

AUTHORITY_FLAGS = {
    "problem_framing_authorized": True,
    "clarification_judgment_authorized": True,
    "execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "external_research_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "model_management_authorized": False,
    "standing_authority_granted": False,
}

_GOAL = re.compile(r"\b(?:build|create|make|develop|implement|fix|repair|add|improve|reduce|increase|continue|preserve|ensure|keep|remove|replace|refactor|investigate|understand|compare|analy[sz]e)\b", re.I)
_HARD = re.compile(r"\b(?:must|must not|do not|don't|never|exactly|only|at most|at least|without|cannot|can't|required|remain|preserve|exclude)\b", re.I)
_SOFT = re.compile(r"\b(?:prefer|preferably|ideally|should|would like|I'd like|i would like|nice to have|if practical|when practical)\b", re.I)
_ASSUMPTION = re.compile(r"\b(?:assuming|assume|probably|likely|I think|we think|appears|seems|expected to)\b", re.I)
_ACCEPTANCE = re.compile(r"\b(?:pass(?:es|ed)?|verify|verified|test(?:s|ed)?|no regressions?|under\s+\d|less than\s+\d|at most\s+\d|at least\s+\d|exactly\s+\d|within\s+\d|zero\s+failures?|measur(?:e|able)|acceptance|success criteria|source immutability|privacy check)\b", re.I)
_CONSEQUENTIAL = re.compile(r"\b(?:delete|destroy|production|credential|secret|password|token|payment|publish|install|promote|certify|model management|authority|destructive|live source|migration)\b", re.I)
_RESEARCHABLE = re.compile(r"\b(?:current|latest|version|documentation|specification|benchmark|compare|research|investigate|unknown|verify externally)\b", re.I)
_REVERSIBLE = re.compile(r"\b(?:draft|preview|simulate|prototype|isolated|sandbox|read[- ]only|inspect|analy[sz]e|plan|proposal)\b", re.I)

_FRAME = re.compile(r"^frame problem:\s*(?P<text>.+)$", re.I | re.S)
_SHOW = re.compile(r"^(?:show|inspect) problem frame (?P<id>problem_[a-f0-9]{24})[.!?]*$", re.I)
_JUDGE = re.compile(r"^judge clarification for problem frame (?P<id>problem_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I)
_CANCEL = re.compile(r"^cancel problem frame (?P<id>problem_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I)
_CORRECT = re.compile(
    r"^correct problem frame (?P<id>problem_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64}) "
    r"(?P<field>goal|hard_constraint|soft_preference|assumption|unknown|acceptance_criterion) "
    r"(?P<index>[1-9][0-9]*) to (?P<value>.+)$", re.I | re.S
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: Any, limit: int = MAX_ITEM_CHARS) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?;])\s+|\n+", text)
    out: list[str] = []
    for raw in chunks:
        value = _clean(raw)
        if value and value not in out:
            out.append(value)
        if len(out) >= MAX_ITEMS:
            break
    return out


def _items(sentences: Iterable[str], pattern: re.Pattern[str], kind: str, provenance: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sentence in sentences:
        if not pattern.search(sentence):
            continue
        text = _clean(sentence)
        out.append({
            "item_id": f"{kind}_{_digest({'kind': kind, 'text': text, 'source': provenance})[:16]}",
            "kind": kind,
            "text": text,
            "provenance": provenance,
            "explicit": True,
            "confidence": 1.0,
        })
        if len(out) >= MAX_ITEMS:
            break
    return out


def _constraint_signature(text: str) -> tuple[str, bool]:
    lowered = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    negative = bool(re.search(r"\b(?:must not|do not|don't|never|cannot|can't|without|exclude)\b", lowered))
    lowered = re.sub(r"\b(?:must|not|do|don't|never|cannot|can't|required|remain|preserve|without|exclude|only|at most|at least|exactly)\b", " ", lowered)
    tokens = [t for t in lowered.split() if len(t) > 2 and t not in {"the", "and", "with", "that", "this", "from", "into", "while"}]
    return " ".join(tokens[:8]), negative


def _contradictions(constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[bool, list[dict[str, Any]]]] = defaultdict(lambda: {True: [], False: []})
    for row in constraints:
        signature, negative = _constraint_signature(row.get("text") or "")
        if signature:
            groups[signature][negative].append(row)
    out = []
    for signature, sides in groups.items():
        if sides[True] and sides[False]:
            out.append({
                "contradiction_id": f"contradiction_{_digest(signature)[:16]}",
                "signature_digest": _digest(signature),
                "negative_item_ids": [r["item_id"] for r in sides[True]],
                "positive_item_ids": [r["item_id"] for r in sides[False]],
                "status": "unresolved",
            })
    return out[:16]


def _inferred_unknowns(*, goals: list[dict[str, Any]], acceptance: list[dict[str, Any]], project_evidence: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    unknowns: list[str] = []
    if not goals:
        unknowns.append("primary_goal_not_explicit")
    if not acceptance:
        unknowns.append("measurable_acceptance_criteria_missing")
    evidence = dict(project_evidence or {})
    if evidence and not evidence.get("project_root_digest") and not evidence.get("workspace_digest"):
        unknowns.append("project_target_not_attributable")
    result = []
    for code in unknowns:
        result.append({
            "item_id": f"unknown_{_digest(code)[:16]}", "kind": "unknown", "text": code,
            "provenance": "derived_from_missing_contract", "explicit": False, "confidence": 1.0,
        })
    return result


def _private_path(frame_id: str, runtime_root: str | Path | None = None) -> Path:
    return _store_root(runtime_root) / "problem_frames" / f"{frame_id}.json"


def _serialized_frame_mutation(function):
    def wrapped(frame_id: str, *args: Any, **kwargs: Any):
        with metadata_mutation_lock(_private_path(frame_id, kwargs.get("runtime_root"))):
            return function(frame_id, *args, **kwargs)
    return wrapped


def _public_items(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        text = _clean(row.get("text"))
        item = {
            "item_id": row.get("item_id"),
            "kind": row.get("kind"),
            "provenance": row.get("provenance"),
            "explicit": bool(row.get("explicit")),
            "confidence": row.get("confidence"),
            "text_digest": _digest(text),
            "text_exposed": False,
        }
        if row.get("supersedes_item_id"):
            item["supersedes_item_id"] = row.get("supersedes_item_id")
        if row.get("provenance") == "derived_from_missing_contract":
            item["reason_code"] = text
        public.append(item)
    return public


def _public(record: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(record)
    fields = ("goals", "hard_constraints", "soft_preferences", "assumptions", "unknowns", "acceptance_criteria", "contradictions")
    result = {
        "ok": bool(row.get("ok", True)),
        "status": row.get("status"),
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "problem_frame_id": row.get("problem_frame_id"),
        "revision": int(row.get("revision") or 0),
        "request_digest": row.get("request_digest"),
        "project_evidence_digest": row.get("project_evidence_digest"),
        "cancelled": bool(row.get("cancelled")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "private_request_stored_externally": True,
        "private_request_exposed": False,
        "raw_project_evidence_exposed": False,
        **AUTHORITY_FLAGS,
    }
    for field in fields:
        values = row.get(field) or []
        result[field] = values if field == "contradictions" else _public_items(values)
    result["counts"] = {field: len(result[field]) for field in fields}
    result["problem_frame_digest"] = _digest({k: v for k, v in result.items() if k != "problem_frame_digest"})
    return result


def build_problem_frame(
    request_text: str,
    *,
    project_evidence: Mapping[str, Any] | None = None,
    source_kind: str = "operator_request",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    text = _clean(request_text, MAX_TEXT)
    if not text:
        return {"ok": False, "status": "request_required", **AUTHORITY_FLAGS}
    sentences = _sentences(text)
    goals = _items(sentences, _GOAL, "goal", source_kind)
    if not goals and sentences:
        first = sentences[0]
        goals = [{"item_id": f"goal_{_digest(first)[:16]}", "kind": "goal", "text": first, "provenance": source_kind, "explicit": True, "confidence": 0.8}]
    hard = _items(sentences, _HARD, "hard_constraint", source_kind)
    soft = _items(sentences, _SOFT, "soft_preference", source_kind)
    assumptions = _items(sentences, _ASSUMPTION, "assumption", source_kind)
    acceptance = _items(sentences, _ACCEPTANCE, "acceptance_criterion", source_kind)
    explicit_unknowns = []
    for sentence in sentences:
        if "?" in sentence or re.search(r"\b(?:unknown|unclear|not sure|don't know|do not know)\b", sentence, re.I):
            value = _clean(sentence)
            explicit_unknowns.append({"item_id": f"unknown_{_digest(value)[:16]}", "kind": "unknown", "text": value, "provenance": source_kind, "explicit": True, "confidence": 1.0})
    unknowns = explicit_unknowns + _inferred_unknowns(goals=goals, acceptance=acceptance, project_evidence=project_evidence)
    # deterministic dedupe
    seen = set(); unknowns = [r for r in unknowns if not (r["text"] in seen or seen.add(r["text"]))][:MAX_ITEMS]
    project_digest = _digest(dict(project_evidence or {})) if project_evidence else ""
    intake_key = _digest({"request": text, "project": project_digest, "source": source_kind})
    frame_id = f"problem_{intake_key[:24]}"
    existing = _read_json(_private_path(frame_id, runtime_root))
    if existing:
        return {**_public(existing), "status": "problem_frame_current"}
    now = _now()
    record = {
        "ok": True,
        "status": "problem_frame_ready",
        "problem_frame_id": frame_id,
        "revision": 1,
        "request_text_private": text,
        "request_digest": _digest(text),
        "project_evidence_private": dict(project_evidence or {}),
        "project_evidence_digest": project_digest,
        "source_kind": _clean(source_kind, 80),
        "goals": goals,
        "hard_constraints": hard,
        "soft_preferences": soft,
        "assumptions": assumptions,
        "unknowns": unknowns,
        "acceptance_criteria": acceptance,
        "contradictions": _contradictions(hard),
        "corrections": [],
        "cancelled": False,
        "created_at": now,
        "updated_at": now,
    }
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(_private_path(frame_id, runtime_root), record)
    return _public(record)


def inspect_problem_frame(frame_id: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_private_path(frame_id, runtime_root))
    if not record:
        return {"ok": False, "status": "problem_frame_not_found", "problem_frame_id": frame_id, **AUTHORITY_FLAGS}
    return _public(record)


def _decision(record: Mapping[str, Any]) -> dict[str, Any]:
    request = str(record.get("request_text_private") or "")
    contradictions = record.get("contradictions") or []
    unknowns = record.get("unknowns") or []
    acceptance = record.get("acceptance_criteria") or []
    consequential = bool(_CONSEQUENTIAL.search(request))
    reversible = bool(_REVERSIBLE.search(request))
    researchable = bool(_RESEARCHABLE.search(request))
    explicit_unknown_count = sum(1 for r in unknowns if r.get("explicit"))
    missing_acceptance = any(r.get("text") == "measurable_acceptance_criteria_missing" for r in unknowns)
    if record.get("cancelled"):
        action, reason = "stop", "problem_frame_cancelled"
    elif contradictions:
        action, reason = "ask", "contradictory_requirements"
    elif consequential and (explicit_unknown_count or missing_acceptance):
        action, reason = "ask", "consequential_ambiguity"
    elif consequential:
        action, reason = "proceed_bounded", "consequential_but_explicit_contract"
    elif researchable and explicit_unknown_count:
        action, reason = "research", "externally_verifiable_unknown"
    elif missing_acceptance and reversible:
        action, reason = "prototype", "reversible_probe_can_reduce_ambiguity"
    elif unknowns and reversible:
        action, reason = "infer_reversibly", "low_risk_reversible_unknowns"
    elif unknowns:
        action, reason = "ask", "material_unknowns"
    else:
        action, reason = "proceed_bounded", "problem_frame_sufficient"
    return {
        "ok": True,
        "status": "clarification_judgment_ready",
        "problem_frame_id": record.get("problem_frame_id"),
        "problem_frame_digest": _public(record)["problem_frame_digest"],
        "judgment": action,
        "reason_code": reason,
        "question_pressure": "high" if action == "ask" else ("medium" if action in {"research", "prototype"} else "low"),
        "unknown_count": len(unknowns),
        "contradiction_count": len(contradictions),
        "acceptance_criterion_count": len(acceptance),
        "consequential_request": consequential,
        "reversible_probe_available": reversible,
        "research_may_help": researchable,
        "silent_risky_assumption_permitted": False,
        "automatic_execution": False,
        **AUTHORITY_FLAGS,
    }


def judge_clarification(frame_id: str, expected_digest: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    record = _read_json(_private_path(frame_id, runtime_root))
    if not record:
        return {"ok": False, "status": "problem_frame_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["problem_frame_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_problem_frame_digest", "current_digest": current, **AUTHORITY_FLAGS}
    return _decision(record)


@_serialized_frame_mutation
def correct_problem_frame(frame_id: str, expected_digest: str, field: str, index: int, value: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    mapping = {
        "goal": "goals", "hard_constraint": "hard_constraints", "soft_preference": "soft_preferences",
        "assumption": "assumptions", "unknown": "unknowns", "acceptance_criterion": "acceptance_criteria",
    }
    if field not in mapping:
        return {"ok": False, "status": "correction_field_invalid", **AUTHORITY_FLAGS}
    path = _private_path(frame_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "problem_frame_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["problem_frame_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_problem_frame_digest", "current_digest": current, **AUTHORITY_FLAGS}
    rows = list(record.get(mapping[field]) or [])
    position = int(index) - 1
    if position < 0 or position >= len(rows):
        return {"ok": False, "status": "correction_index_invalid", **AUTHORITY_FLAGS}
    clean = _clean(value)
    if not clean:
        return {"ok": False, "status": "correction_value_required", **AUTHORITY_FLAGS}
    before = dict(rows[position])
    rows[position] = {
        **before,
        "text": clean,
        "item_id": f"{field}_{_digest({'text': clean, 'revision': int(record.get('revision') or 1)+1})[:16]}",
        "provenance": "operator_correction",
        "explicit": True,
        "confidence": 1.0,
        "supersedes_item_id": before.get("item_id"),
    }
    record[mapping[field]] = rows
    record.setdefault("corrections", []).append({"field": field, "index": int(index), "superseded_item_id": before.get("item_id"), "replacement_item_id": rows[position]["item_id"], "at": _now()})
    record["revision"] = int(record.get("revision") or 1) + 1
    record["updated_at"] = _now()
    record["contradictions"] = _contradictions(list(record.get("hard_constraints") or []))
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result["status"] = "problem_frame_corrected"; return result


@_serialized_frame_mutation
def cancel_problem_frame(frame_id: str, expected_digest: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    path = _private_path(frame_id, runtime_root); record = _read_json(path)
    if not record:
        return {"ok": False, "status": "problem_frame_not_found", **AUTHORITY_FLAGS}
    current = _public(record)["problem_frame_digest"]
    if expected_digest != current:
        return {"ok": False, "status": "stale_problem_frame_digest", "current_digest": current, **AUTHORITY_FLAGS}
    if record.get("cancelled"):
        result = _public(record); result["status"] = "problem_frame_already_cancelled"; return result
    record["cancelled"] = True; record["revision"] = int(record.get("revision") or 1) + 1; record["updated_at"] = _now()
    record["private_record_digest"] = _digest({k: v for k, v in record.items() if k != "private_record_digest"})
    _atomic_json(path, record)
    result = _public(record); result["status"] = "problem_frame_cancelled"; return result


def process_problem_framing_control(user_text: str, *, project_evidence: Mapping[str, Any] | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    lowered = text.lower()
    if any(token in lowered for token in (" and install", " and promote", " and execute", " and delete", " and run it")) and any(key in lowered for key in ("problem frame", "frame problem")):
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", **AUTHORITY_FLAGS}
    match = _FRAME.fullmatch(text)
    if match:
        return {"active": True, **build_problem_frame(match.group("text"), project_evidence=project_evidence, runtime_root=runtime_root)}
    match = _SHOW.fullmatch(text)
    if match:
        return {"active": True, **inspect_problem_frame(match.group("id").lower(), runtime_root=runtime_root)}
    match = _JUDGE.fullmatch(text)
    if match:
        return {"active": True, **judge_clarification(match.group("id").lower(), match.group("digest").lower(), runtime_root=runtime_root)}
    match = _CANCEL.fullmatch(text)
    if match:
        return {"active": True, **cancel_problem_frame(match.group("id").lower(), match.group("digest").lower(), runtime_root=runtime_root)}
    match = _CORRECT.fullmatch(text)
    if match:
        return {"active": True, **correct_problem_frame(match.group("id").lower(), match.group("digest").lower(), match.group("field").lower(), int(match.group("index")), match.group("value"), runtime_root=runtime_root)}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "SCHEMA_VERSION", "AUTHORITY_FLAGS", "build_problem_frame", "inspect_problem_frame",
    "judge_clarification", "correct_problem_frame", "cancel_problem_frame", "process_problem_framing_control",
]
