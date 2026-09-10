from __future__ import annotations
"""v1369 evidence-driven UI fault classification without UI mutation."""
import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1369.8"
DENIED = {
    "source_mutation_authorized": False,
    "ui_mutation_authorized": False,
    "browser_execution_authorized": False,
    "provider_contact_authorized": False,
    "network_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "application_authorized": False,
}
ORDER = ("layout", "focus", "state_ownership", "navigation", "request_lifecycle", "rendering")


def _d(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def diagnose_ui(observation: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(observation, Mapping):
        return {"ok": False, "status": "ui_evidence_invalid", "action_executed": False, **DENIED}

    classes: list[str] = []
    reasons: dict[str, list[str]] = {key: [] for key in ORDER}

    def flag(kind: str, condition: bool, reason: str) -> None:
        if condition:
            if kind not in classes:
                classes.append(kind)
            reasons[kind].append(reason)

    # A browser/tool policy failure without product observation is an environment limitation,
    # not evidence that the UI product itself is defective.
    environment_limited = bool(observation.get("browser_policy_blocked") or observation.get("browser_launch_failed")) and not bool(observation.get("product_runtime_observed"))
    if not environment_limited:
        flag("layout", any(bool(observation.get(k)) for k in ("overlap_detected", "content_clipped", "offscreen_control", "unexpected_overflow", "narrow_layout_failed")), "geometry_or_responsive_failure")
        flag("focus", observation.get("focus_visible") is False or observation.get("focus_order_valid") is False or bool(observation.get("focus_trapped")) or bool(observation.get("focus_missing")), "focus_contract_failure")
        flag("state_ownership", bool(observation.get("duplicate_state_owner")) or bool(observation.get("stale_state_rendered")) or bool(observation.get("state_source_conflict")), "state_ownership_failure")
        flag("navigation", observation.get("route_resolved") is False or observation.get("history_consistent") is False or bool(observation.get("dead_destination")), "navigation_contract_failure")
        flag("request_lifecycle", bool(observation.get("duplicate_request")) or bool(observation.get("stuck_loading")) or bool(observation.get("late_result_after_cancel")) or bool(observation.get("unreconciled_request")), "request_lifecycle_failure")
        flag("rendering", bool(observation.get("render_error")) or bool(observation.get("hydration_mismatch")) or bool(observation.get("required_element_missing")) or observation.get("visual_check_passed") is False, "rendering_failure")

    classes = [kind for kind in ORDER if kind in classes]
    if environment_limited:
        status = "ui_environment_limited"
    elif classes:
        status = "ui_faults_classified"
    else:
        status = "ui_evidence_healthy"

    rec = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "failure_classes": classes,
        "failure_count": len(classes),
        "primary_failure_class": classes[0] if classes else None,
        "reason_codes": {k: tuple(reasons[k]) for k in classes},
        "environment_limited": environment_limited,
        "observation_digest": _d(dict(observation)),
        "screenshot_content_persisted": False,
        "dom_content_persisted": False,
        "raw_ui_content_persisted": False,
        "content_free": True,
        "read_only": True,
        "action_executed": False,
        **DENIED,
    }
    rec["record_digest"] = _d(rec)
    return {"ok": True, "status": status, "ui_diagnosis": rec, "action_executed": False, **DENIED}


def process_ui_diagnosis_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show ui diagnosis", "inspect ui diagnosis", "show interface diagnosis"}:
        return {"active": False}
    rec = dict((project_state or {}).get("ui_diagnosis") or {})
    return {
        "active": True,
        "ok": bool(rec),
        "status": "ui_diagnosis_found" if rec else "ui_diagnosis_missing",
        "ui_diagnosis": rec,
        "action_executed": False,
        **DENIED,
    }
