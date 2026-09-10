from __future__ import annotations

"""Era 7 visual/document evidence and explicit observation boundaries.

Operator-shared media may be represented by content digests, regions, OCR or
visual-observation receipts, and timestamps. This module never captures a
screen, opens a camera, runs OCR, reads image bytes, or invents observations.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from paths import DATA_DIR
from browser_validation import CONTRACT_VERSION as RETAINED_BROWSER_VALIDATION_VERSION

CONTRACT_VERSION = "v2199.9"
NATIVE_OBSERVATION_RECEIPT_VERSION = "era7-native-visual-observation-v1"
SCHEMA_VERSION = "1"
STATE_FILE = "era7_multimodal_evidence.json"
MAX_ITEMS = 128
MAX_REGIONS = 256
MAX_OBSERVATIONS = 512
SOURCE_TYPES = ("operator_image", "operator_screenshot", "document_page", "selected_screen_frame")
RETENTION_POLICIES = ("turn_only", "session", "explicit_memory_candidate", "do_not_retain")
OBSERVATION_KINDS = ("visual", "ocr", "layout", "ui_state", "document_structure")

_DENIED = {
    "screen_captured": False,
    "camera_accessed": False,
    "image_bytes_read": False,
    "ocr_executed": False,
    "document_opened": False,
    "provider_contacted": False,
    "tool_executed": False,
    "memory_modified": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _token(value: Any, limit: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text or len(text) > limit or not re.fullmatch(r"[a-z0-9_.:-]+", text): return ""
    return text


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None: current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text: return None
    try: dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError: return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _valid_observation_receipt(
    value: Mapping[str, Any], *, item_id: str, content_digest: str,
    region_id: str, observation_kind: str, observation_digest: str,
) -> str:
    row = dict(value or {})
    supplied = _hex64(row.pop("receipt_digest", ""))
    exact = bool(
        row.get("contract_version") == NATIVE_OBSERVATION_RECEIPT_VERSION
        and row.get("receipt_kind") == "visual_observation"
        and row.get("authoritative") is True
        and row.get("terminal") is True
        and _token(row.get("item_id"), 120) == item_id
        and _hex64(row.get("content_digest")) == content_digest
        and _token(row.get("region_id"), 120) == region_id
        and str(row.get("observation_kind") or "").strip().lower() == observation_kind
        and _hex64(row.get("observation_digest")) == observation_digest
        and _hex64(row.get("operation_digest"))
        and _hex64(row.get("terminal_result_digest"))
        and supplied
        and supplied == _digest(row)
    )
    return supplied if exact else ""


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "multimodal" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "items": {}, "observations": [], "processed_events": [], "raw_media_persisted": False, "raw_ocr_text_persisted": False}


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    if not isinstance(state.get("items"), dict): state["items"] = {}
    if not isinstance(state.get("observations"), list): state["observations"] = []
    if not isinstance(state.get("processed_events"), list): state["processed_events"] = []
    state["raw_media_persisted"] = False; state["raw_ocr_text_persisted"] = False
    return state


def read_multimodal_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def public_multimodal_state(state: Mapping[str, Any], *, now: datetime | None = None, stale_after_seconds: int = 30) -> dict[str, Any]:
    current = _now(now)
    items = []
    for item_id, raw in sorted((state.get("items") or {}).items()):
        row = dict(raw or {}); captured = _parse_time(row.get("captured_at")); age = None
        if captured is not None: age = max(0, int((current - captured).total_seconds()))
        stale = bool(row.get("source_type") == "selected_screen_frame" and (age is None or age > stale_after_seconds))
        items.append({
            "item_id": item_id, "source_type": row.get("source_type"), "content_digest": row.get("content_digest"),
            "width": row.get("width"), "height": row.get("height"), "page_number": row.get("page_number"),
            "sensitive": bool(row.get("sensitive")), "retention_policy": row.get("retention_policy"),
            "accessible": bool(row.get("accessible", True)), "age_seconds": age, "stale": stale,
            "region_count": len(row.get("regions") or []),
        })
    observations = [dict(x) for x in state.get("observations", []) if isinstance(x, Mapping)]
    result = {
        "contract_version": CONTRACT_VERSION, "revision": int(state.get("revision") or 0),
        "items": items, "item_count": len(items), "observation_count": len(observations),
        "raw_media_persisted": False, "raw_ocr_text_persisted": False,
        "inaccessible_items_must_remain_unobserved": True, "stale_screen_frames_must_be_reobserved": True,
        "retained_browser_validation_contract_version": RETAINED_BROWSER_VALIDATION_VERSION,
        "new_capture_engine_created": False,
        **_DENIED,
    }
    result["state_digest"] = _digest(result)
    return result


def register_visual_evidence(
    *, item_id: str, source_type: str, content_digest: str, captured_at: str, width: int = 0, height: int = 0,
    page_number: int = 0, sensitive: bool = False, retention_policy: str = "turn_only", accessible: bool = True,
    event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    iid = _token(item_id, 120); st = str(source_type or "").strip().lower(); cd = _hex64(content_digest)
    retention = str(retention_policy or "turn_only").strip().lower(); captured = _parse_time(captured_at)
    if not iid or st not in SOURCE_TYPES or not cd or captured is None or retention not in RETENTION_POLICIES or not str(event_id or "").strip():
        return {"ok": False, "status": "valid_visual_evidence_contract_required", **_DENIED}
    try:
        width_value = int(width or 0); height_value = int(height or 0); page_value = int(page_number or 0)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "invalid_visual_dimensions_or_page", **_DENIED}
    if width_value < 0 or height_value < 0 or page_value < 0:
        return {"ok": False, "status": "invalid_visual_dimensions_or_page", **_DENIED}
    if retention == "do_not_retain":
        return {
            "ok": True, "status": "visual_evidence_transient_not_persisted",
            "item": {"item_id": iid, "source_type": st, "content_digest": cd, "sensitive": bool(sensitive), "retention_policy": retention, "accessible": bool(accessible)},
            "persisted": False, "raw_media_persisted": False, "raw_ocr_text_persisted": False, **_DENIED,
        }
    path = _state_path(runtime_root); ed = _digest(str(event_id))
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_multimodal_state(runtime_root=runtime_root)
        if any(x.get("event_digest") == ed for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            return {"ok": True, "status": "visual_evidence_event_replayed", "state": public_multimodal_state(state), "idempotent": True, **_DENIED}
        existing = (state.get("items") or {}).get(iid)
        if existing and existing.get("content_digest") != cd:
            # Same logical item can only be replaced by a new explicit event if
            # the old evidence is preserved as superseded lineage.
            lineage = list(existing.get("superseded_content_digests") or [])[-8:]
            lineage.append(existing.get("content_digest"))
        else:
            lineage = list((existing or {}).get("superseded_content_digests") or [])[-8:]
        row = {
            "item_id": iid, "source_type": st, "content_digest": cd, "captured_at": captured.isoformat(),
            "width": width_value, "height": height_value, "page_number": page_value,
            "sensitive": bool(sensitive), "retention_policy": retention, "accessible": bool(accessible),
            "regions": [], "superseded_content_digests": lineage,
        }
        state["items"][iid] = row
        if len(state["items"]) > MAX_ITEMS:
            for key in list(state["items"])[:-MAX_ITEMS]: state["items"].pop(key, None)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": ed, "kind": "register", "item_id": iid}])[-512:]
        write_json_atomic(path, state)
        return {"ok": True, "status": "visual_evidence_registered_metadata_only", "state": public_multimodal_state(state), **_DENIED}


def register_region_observation(
    *, item_id: str, expected_content_digest: str, region_id: str, observation_kind: str,
    observation_digest: str, confidence: float, bounds: Mapping[str, Any], event_id: str,
    observation_receipt: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    iid = _token(item_id, 120); rid = _token(region_id, 120); kind = str(observation_kind or "").strip().lower()
    cd = _hex64(expected_content_digest); od = _hex64(observation_digest)
    if not iid or not rid or kind not in OBSERVATION_KINDS or not cd or not od or not str(event_id or "").strip():
        return {"ok": False, "status": "valid_region_observation_contract_required", **_DENIED}
    receipt_digest = _valid_observation_receipt(
        observation_receipt or {}, item_id=iid, content_digest=cd, region_id=rid,
        observation_kind=kind, observation_digest=od,
    )
    if not receipt_digest:
        return {"ok": False, "status": "authoritative_visual_observation_receipt_required", **_DENIED}
    try:
        confidence_value = float(confidence)
        if not math.isfinite(confidence_value):
            raise ValueError
        conf = round(max(0.0, min(1.0, confidence_value)), 3)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "valid_observation_confidence_required", **_DENIED}
    try:
        box = {k: round(float(bounds.get(k)), 4) for k in ("x", "y", "w", "h")}
    except (TypeError, ValueError, AttributeError):
        return {"ok": False, "status": "normalized_region_bounds_required", **_DENIED}
    if any(not math.isfinite(v) or v < 0 or v > 1 for v in box.values()) or box["x"] + box["w"] > 1.0001 or box["y"] + box["h"] > 1.0001:
        return {"ok": False, "status": "region_bounds_out_of_range", **_DENIED}
    path = _state_path(runtime_root); ed = _digest(str(event_id))
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_multimodal_state(runtime_root=runtime_root)
        if any(x.get("event_digest") == ed for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            return {"ok": True, "status": "visual_observation_event_replayed", "state": public_multimodal_state(state), "idempotent": True, **_DENIED}
        item = (state.get("items") or {}).get(iid)
        if not item: return {"ok": False, "status": "visual_item_not_found", **_DENIED}
        if item.get("content_digest") != cd: return {"ok": False, "status": "stale_visual_content_digest", **_DENIED}
        if item.get("accessible") is not True: return {"ok": False, "status": "inaccessible_visual_item_cannot_be_observed", **_DENIED}
        obs = {"item_id": iid, "content_digest": cd, "region_id": rid, "kind": kind, "observation_digest": od, "confidence": conf, "bounds": box, "native_receipt_digest": receipt_digest, "raw_text_stored": False}
        item["regions"] = ([x for x in item.get("regions", []) if x.get("region_id") != rid] + [obs])[-MAX_REGIONS:]
        state["observations"] = (state.get("observations", []) + [obs])[-MAX_OBSERVATIONS:]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": ed, "kind": "observation", "item_id": iid, "region_id": rid}])[-512:]
        write_json_atomic(path, state)
        return {"ok": True, "status": "visual_region_observation_recorded", "observation": obs, "state": public_multimodal_state(state), **_DENIED}


def build_visual_claim(
    *, item_id: str, region_ids: Iterable[str], claim_code: str, runtime_root: str | Path | None = None,
    now: datetime | None = None, stale_after_seconds: int = 30,
) -> dict[str, Any]:
    state = read_multimodal_state(runtime_root=runtime_root); item = (state.get("items") or {}).get(str(item_id or ""))
    if not item: return {"ok": False, "status": "visual_item_not_found", "claim_supported": False, **_DENIED}
    if item.get("accessible") is not True: return {"ok": False, "status": "visual_item_inaccessible", "claim_supported": False, **_DENIED}
    captured = _parse_time(item.get("captured_at")); age = None if captured is None else max(0, int((_now(now)-captured).total_seconds()))
    if item.get("source_type") == "selected_screen_frame" and (age is None or age > stale_after_seconds):
        return {"ok": False, "status": "stale_screen_frame_requires_reobservation", "claim_supported": False, "age_seconds": age, **_DENIED}
    wanted = {_token(x, 120) for x in region_ids if _token(x, 120)}
    observations = [dict(x) for x in item.get("regions", []) if isinstance(x, Mapping) and x.get("region_id") in wanted]
    if not wanted or len(observations) != len(wanted):
        return {"ok": False, "status": "all_claim_regions_require_observation_evidence", "claim_supported": False, **_DENIED}
    code = _token(claim_code, 120)
    if not code: return {"ok": False, "status": "typed_visual_claim_code_required", "claim_supported": False, **_DENIED}
    confidence = round(min(float(x.get("confidence") or 0.0) for x in observations), 3)
    claim = {
        "claim_code": code, "item_id": str(item_id), "content_digest": item.get("content_digest"),
        "region_ids": sorted(wanted), "observation_digests": sorted(x.get("observation_digest") for x in observations),
        "confidence": confidence, "age_seconds": age, "claim_supported": confidence > 0.0,
        "raw_observation_content_included": False, "observation_boundary_explicit": True,
    }
    claim["claim_digest"] = _digest(claim)
    return {"ok": True, "status": "visual_claim_grounded_in_observations", "claim": claim, **_DENIED}


def prune_multimodal_evidence(
    *, scope: str, event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Honor turn/session retention without promoting media into memory."""
    mode = str(scope or "").strip().lower()
    if mode not in {"turn_end", "session_end"} or not str(event_id or "").strip():
        return {"ok": False, "status": "valid_multimodal_prune_scope_and_event_required", **_DENIED}
    path = _state_path(runtime_root); ed = _digest(str(event_id))
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_multimodal_state(runtime_root=runtime_root)
        if any(x.get("event_digest") == ed for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            return {"ok": True, "status": "multimodal_prune_replayed", "state": public_multimodal_state(state), "idempotent": True, **_DENIED}
        remove_policies = {"turn_only"} if mode == "turn_end" else {"turn_only", "session"}
        removed = []
        for iid, row in list((state.get("items") or {}).items()):
            if str((row or {}).get("retention_policy") or "") in remove_policies:
                removed.append({"item_id_digest": _digest(iid), "content_digest": str((row or {}).get("content_digest") or "")})
                state["items"].pop(iid, None)
        remaining_ids = set(state["items"])
        state["observations"] = [x for x in state.get("observations", []) if isinstance(x, Mapping) and x.get("item_id") in remaining_ids]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": ed, "kind": mode, "removed_count": len(removed)}])[-512:]
        write_json_atomic(path, state)
        return {
            "ok": True, "status": "multimodal_retention_pruned", "scope": mode, "removed_count": len(removed),
            "removed_evidence": removed, "memory_candidates_created": False, "state": public_multimodal_state(state), **_DENIED,
        }


def prepare_multimodal_workflow(
    *, workflow: str, item_ids: Iterable[str], operation_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    code = _token(workflow, 80); allowed = {"screenshot_explanation", "ui_troubleshooting", "document_understanding", "selected_screen_context"}
    if code not in allowed or not str(operation_id or "").strip():
        return {"ok": False, "status": "typed_multimodal_workflow_and_operation_required", **_DENIED}
    state = read_multimodal_state(runtime_root=runtime_root); refs = []
    for iid in list(item_ids)[:32]:
        item = (state.get("items") or {}).get(str(iid or ""))
        if item:
            refs.append({"item_id": str(iid), "content_digest": item.get("content_digest"), "source_type": item.get("source_type"), "accessible": bool(item.get("accessible")), "sensitive": bool(item.get("sensitive"))})
    packet = {
        "contract_version": CONTRACT_VERSION, "workflow": code, "operation_digest": _digest(str(operation_id)),
        "evidence_items": refs, "evidence_item_count": len(refs), "capture_required_for_missing_items": True,
        "inaccessible_content_must_not_be_described": True, "stale_frames_must_be_reobserved": True,
        "sensitive_retention_requires_operator_policy": True, "workflow_executed": False, **_DENIED,
    }
    packet["workflow_digest"] = _digest(packet)
    return {"ok": True, "status": "multimodal_workflow_prepared_not_executed", "workflow": packet, **_DENIED}


def process_era7_multimodal_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {"show multimodal context status", "inspect multimodal context status", "show era7 visual evidence contract"}
    if raw in exact:
        return {"active": True, "ok": True, "status": "era7_multimodal_contract_inspected", "state": public_multimodal_state(read_multimodal_state(runtime_root=runtime_root)), "native_capture_deferred": True, **_DENIED}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era7_multimodal_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "NATIVE_OBSERVATION_RECEIPT_VERSION", "SOURCE_TYPES", "RETENTION_POLICIES", "OBSERVATION_KINDS", "read_multimodal_state",
    "public_multimodal_state", "register_visual_evidence", "register_region_observation", "build_visual_claim",
    "prune_multimodal_evidence", "prepare_multimodal_workflow", "process_era7_multimodal_control",
]
