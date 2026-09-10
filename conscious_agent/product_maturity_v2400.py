from __future__ import annotations

"""Era 10 portable desktop-product maturity contracts.

This module consolidates existing desktop/dashboard owners into a quiet, chat-first
product contract.  It does not launch the desktop shell, modify native startup,
install updates, create tray entries, or claim Windows/accessibility evidence.
"""

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v2425.9"
MIN_WIDTH = 360
MIN_HEIGHT = 480
MAX_SCALE = 250
PRIMARY_SURFACES = {"chat", "status", "review"}
LIFECYCLE_STATES = {"cold", "starting", "ready", "degraded", "update_available", "update_review", "stopped"}
LIFECYCLE_EVENTS = {
    ("cold", "start"): "starting",
    ("starting", "startup_ready"): "ready",
    ("starting", "startup_degraded"): "degraded",
    ("degraded", "recover"): "ready",
    ("ready", "update_detected"): "update_available",
    ("update_available", "review_update"): "update_review",
    ("update_review", "defer_update"): "ready",
    ("ready", "stop"): "stopped",
    ("degraded", "stop"): "stopped",
}

_DENIED = {
    "desktop_launched": False,
    "tray_modified": False,
    "startup_modified": False,
    "notification_sent": False,
    "update_installed": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _finite_int(value: Any, *, minimum: int, maximum: int) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or int(f) != f:
        return None
    i = int(f)
    return i if minimum <= i <= maximum else None


def build_chat_first_shell_projection(
    *, width_px: Any, height_px: Any, scaling_percent: Any = 100,
    primary_surface: str = "chat", pending_review_count: Any = 0,
    notification_count: Any = 0, advanced_requested: bool = False,
) -> dict[str, Any]:
    width = _finite_int(width_px, minimum=MIN_WIDTH, maximum=16384)
    height = _finite_int(height_px, minimum=MIN_HEIGHT, maximum=16384)
    scale = _finite_int(scaling_percent, minimum=50, maximum=MAX_SCALE)
    pending = _finite_int(pending_review_count, minimum=0, maximum=100000)
    notices = _finite_int(notification_count, minimum=0, maximum=100000)
    primary = str(primary_surface or "").strip().lower()
    errors: list[str] = []
    if width is None: errors.append("invalid_width")
    if height is None: errors.append("invalid_height")
    if scale is None: errors.append("invalid_scaling")
    if pending is None: errors.append("invalid_pending_review_count")
    if notices is None: errors.append("invalid_notification_count")
    if primary not in PRIMARY_SURFACES: errors.append("invalid_primary_surface")
    if errors:
        return {"ok": False, "status": "product_shell_projection_blocked", "errors": errors, "content_free": True, **_DENIED}
    compact = width < 760
    result = {
        "ok": True,
        "status": "chat_first_shell_projected",
        "contract_version": CONTRACT_VERSION,
        "viewport": {"width_px": width, "height_px": height, "scaling_percent": scale, "compact": compact},
        "primary_surface": primary,
        "chat_column_max_px": 980 if not compact else width,
        "chat_first": primary == "chat",
        "advanced_controls_collapsed": not bool(advanced_requested),
        "quiet_status": pending == 0 and notices == 0,
        "attention_badges": {"pending_reviews": pending, "notifications": notices},
        "persistent_primary_actions": ["new_conversation", "conversation_history", "status", "review_center"],
        "secondary_surfaces_disclosed_on_demand": True,
        "native_desktop_evidence_required": True,
        "operator_trial_required": True,
        "content_free": True,
        **_DENIED,
    }
    result["projection_digest"] = _digest(result)
    return result


def build_accessibility_fixture(
    *, width_px: Any, height_px: Any, scaling_percent: Any,
    keyboard_only: bool, reduced_motion: bool, high_contrast: bool,
    visible_focus: bool = True, composer_reachable: bool = True,
) -> dict[str, Any]:
    shell = build_chat_first_shell_projection(width_px=width_px, height_px=height_px, scaling_percent=scaling_percent)
    if not shell.get("ok"):
        return {"ok": False, "status": "accessibility_fixture_blocked", "shell": shell, "content_free": True, **_DENIED}
    failures = []
    if keyboard_only and not visible_focus: failures.append("keyboard_focus_not_visible")
    if not composer_reachable: failures.append("composer_not_reachable")
    result = {
        "ok": not failures,
        "status": "portable_accessibility_fixture_ready" if not failures else "portable_accessibility_fixture_failed",
        "shell_projection_digest": shell["projection_digest"],
        "keyboard_only": bool(keyboard_only),
        "reduced_motion": bool(reduced_motion),
        "high_contrast": bool(high_contrast),
        "visible_focus": bool(visible_focus),
        "composer_reachable": bool(composer_reachable),
        "failure_codes": failures,
        "native_screen_reader_evidence_collected": False,
        "native_multi_monitor_evidence_collected": False,
        "content_free": True,
        **_DENIED,
    }
    result["fixture_digest"] = _digest(result)
    return result


def advance_desktop_product_lifecycle(
    *, current_state: str, event: str, evidence_digest: str,
    update_install_authorized: bool = False,
) -> dict[str, Any]:
    state = str(current_state or "").strip().lower()
    evt = str(event or "").strip().lower()
    digest = str(evidence_digest or "").strip().lower()
    if state not in LIFECYCLE_STATES or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return {"ok": False, "status": "product_lifecycle_transition_blocked", "reason": "invalid_state_or_evidence", "content_free": True, **_DENIED}
    if update_install_authorized or evt in {"install_update", "apply_update", "promote"}:
        return {"ok": False, "status": "product_lifecycle_authority_boundary", "reason": "installation_separate_operator_decision", "content_free": True, **_DENIED}
    next_state = LIFECYCLE_EVENTS.get((state, evt))
    if next_state is None:
        return {"ok": False, "status": "product_lifecycle_transition_blocked", "reason": "unsupported_transition", "content_free": True, **_DENIED}
    result = {
        "ok": True,
        "status": "product_lifecycle_transition_ready",
        "current_state": state,
        "event": evt,
        "next_state": next_state,
        "evidence_digest": digest,
        "update_install_authorized": False,
        "operator_install_decision_required": bool(next_state == "update_review"),
        "content_free": True,
        **_DENIED,
    }
    result["transition_digest"] = _digest(result)
    return result


def build_product_maturity_acceptance(
    *, shell: Mapping[str, Any], accessibility: Mapping[str, Any],
    lifecycle_scenarios: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    shell_digest = str(shell.get("projection_digest") or "")
    shell_unsigned = dict(shell); shell_unsigned.pop("projection_digest", None)
    accessibility_digest = str(accessibility.get("fixture_digest") or "")
    accessibility_unsigned = dict(accessibility); accessibility_unsigned.pop("fixture_digest", None)
    shell_ok = bool(shell.get("ok") and len(shell_digest) == 64 and shell_digest == _digest(shell_unsigned))
    accessibility_shell_digest = str(accessibility.get("shell_projection_digest") or "")
    access_ok = bool(
        accessibility.get("ok") and len(accessibility_digest) == 64
        and accessibility_digest == _digest(accessibility_unsigned)
        and len(accessibility_shell_digest) == 64
        and all(character in "0123456789abcdef" for character in accessibility_shell_digest.lower())
    )
    scenarios = list(lifecycle_scenarios)
    valid_lifecycle = 0
    for row in scenarios:
        if not isinstance(row, Mapping):
            continue
        transition_digest = str(row.get("transition_digest") or "")
        unsigned = dict(row); unsigned.pop("transition_digest", None)
        if row.get("ok") and row.get("status") == "product_lifecycle_transition_ready" and len(transition_digest) == 64 and transition_digest == _digest(unsigned):
            valid_lifecycle += 1
    lifecycle_ok = bool(scenarios) and valid_lifecycle == len(scenarios)
    result = {
        "ok": shell_ok and access_ok and lifecycle_ok,
        "status": "portable_product_maturity_acceptance_ready" if shell_ok and access_ok and lifecycle_ok else "portable_product_maturity_acceptance_blocked",
        "chat_first": bool(shell.get("chat_first")),
        "quiet_status": bool(shell.get("quiet_status")),
        "accessibility_fixture_passed": access_ok,
        "lifecycle_scenario_count": len(scenarios),
        "valid_lifecycle_scenario_count": valid_lifecycle,
        "windows_desktop_trial_required": True,
        "native_tray_installer_update_evidence_required": True,
        "content_free": True,
        **_DENIED,
    }
    result["acceptance_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "build_chat_first_shell_projection", "build_accessibility_fixture",
    "advance_desktop_product_lifecycle", "build_product_maturity_acceptance",
]
