from __future__ import annotations

"""Integrated Era 7 tools/research/voice/multimodal portable boundary."""

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from local_tool_interaction_v2100 import process_era7_tool_control, tool_contract_registry
from research_web_intelligence_v2100 import process_era7_research_control, FRESHNESS_DAYS, SOURCE_QUALITY
from voice_audio_interaction_v2100 import process_era7_voice_control, public_voice_state, read_voice_state
from multimodal_context_v2100 import process_era7_multimodal_control, public_multimodal_state, read_multimodal_state

CONTRACT_VERSION = "v2199.9"

_DENIED = {
    "tool_executed": False,
    "browser_contacted": False,
    "network_contacted": False,
    "provider_contacted": False,
    "microphone_accessed": False,
    "speaker_accessed": False,
    "screen_captured": False,
    "document_opened": False,
    "message_sent": False,
    "source_modified": False,
    "memory_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _component_digest(value: Mapping[str, Any], digest_key: str, ignored: set[str]) -> str:
    row = dict(value or {})
    supplied = _hex64(row.get(digest_key))
    calculated = _digest({key: item for key, item in row.items() if key not in ignored | {digest_key}})
    return supplied if supplied and supplied == calculated else ""


def build_era7_interaction_snapshot(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    tools = tool_contract_registry()
    voice = public_voice_state(read_voice_state(runtime_root=runtime_root))
    visual = public_multimodal_state(read_multimodal_state(runtime_root=runtime_root))
    result = {
        "ok": True,
        "status": "era7_interaction_snapshot",
        "contract_version": CONTRACT_VERSION,
        "tools": {
            "tool_class_count": tools.get("tool_class_count"),
            "registry_digest": tools.get("registry_digest"),
            "native_execution_deferred": True,
        },
        "research": {
            "source_quality_codes": sorted(SOURCE_QUALITY),
            "freshness_policies": dict(FRESHNESS_DAYS),
            "governed_browser_required": True,
            "network_contacted": False,
        },
        "voice": voice,
        "multimodal": visual,
        "authority_boundary": {
            "planning_or_inspection_can_grant_execution": False,
            "generated_prose_is_execution_evidence": False,
            "generated_prose_is_research_evidence": False,
            "unobserved_visual_content_may_be_described": False,
            "audio_or_screen_devices_require_native_adapter": True,
        },
        **_DENIED,
    }
    result["snapshot_digest"] = _digest(result)
    return result


def prepare_era7_interaction_packet(
    *, operation_id: str, tool_preview: Mapping[str, Any] | None = None,
    research_request: Mapping[str, Any] | None = None, voice_turn: Mapping[str, Any] | None = None,
    multimodal_workflow: Mapping[str, Any] | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(operation_id or "").strip()
    if not token:
        return {"ok": False, "status": "era7_operation_identity_required", **_DENIED}
    components = {}
    if tool_preview:
        digest = _component_digest(tool_preview, "preview_digest", {"prepared_at"})
        if not digest or tool_preview.get("state") != "preview_only":
            return {"ok": False, "status": "invalid_era7_tool_component", **_DENIED}
        components["tool_preview_digest"] = digest
    if research_request:
        digest = _component_digest(research_request, "request_digest", set())
        if not digest or research_request.get("browser_execution_admitted") is not False:
            return {"ok": False, "status": "invalid_era7_research_component", **_DENIED}
        components["research_request_digest"] = digest
    if voice_turn:
        digest = _component_digest(voice_turn, "turn_digest", {"created_at", "updated_at"})
        if not digest:
            return {"ok": False, "status": "invalid_era7_voice_component", **_DENIED}
        components["voice_turn_digest"] = digest
    if multimodal_workflow:
        digest = _component_digest(multimodal_workflow, "workflow_digest", set())
        if not digest or multimodal_workflow.get("workflow_executed") is not False:
            return {"ok": False, "status": "invalid_era7_multimodal_component", **_DENIED}
        components["multimodal_workflow_digest"] = digest
    if not components:
        return {"ok": False, "status": "era7_interaction_component_required", **_DENIED}
    packet = {
        "contract_version": CONTRACT_VERSION,
        "operation_digest": _digest(token),
        "components": components,
        "component_count": len(components),
        "requires_component_specific_native_adapters": True,
        "requires_authoritative_terminal_receipts_for_effect_claims": True,
        "prepared_not_executed": True,
        **_DENIED,
    }
    packet["packet_digest"] = _digest(packet)
    return {"ok": True, "status": "era7_interaction_packet_prepared_not_executed", "packet": packet, **_DENIED}


def process_era7_interaction_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {"show tools research voice and multimodal status", "inspect era7 interaction status", "show era7 interaction status"}
    if raw in exact:
        return {"active": True, **build_era7_interaction_snapshot(runtime_root=runtime_root)}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era7_integrated_read_only_scope_expansion_rejected", **_DENIED}
    for processor in (
        lambda t: process_era7_tool_control(t),
        lambda t: process_era7_research_control(t),
        lambda t: process_era7_voice_control(t, runtime_root=runtime_root),
        lambda t: process_era7_multimodal_control(t, runtime_root=runtime_root),
    ):
        result = processor(text)
        if result.get("active"):
            return result
    return {"active": False}


__all__ = ["CONTRACT_VERSION", "build_era7_interaction_snapshot", "prepare_era7_interaction_packet", "process_era7_interaction_control"]
