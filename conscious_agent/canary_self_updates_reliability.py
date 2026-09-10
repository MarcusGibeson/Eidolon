from __future__ import annotations
"""v1296.6-v1296.8 canary false-pass and authority-boundary hardening."""
from pathlib import Path
from typing import Any, Mapping
from canary_self_updates_foundations import DENIED_AUTHORITY, MANDATORY_SIGNALS, NATIVE_SIGNAL, valid_digest

CONTRACT_VERSION = "v1296.8"

def audit_canary_result(result: Mapping[str, Any]) -> dict[str, Any]:
    r = dict(result); findings: list[str] = []
    if not valid_digest(r.get("evaluation_digest")): findings.append("evaluation_digest_missing")
    if r.get("active_replacement_performed") is not False: findings.append("active_replacement_claimed")
    if r.get("requires_separate_v1269_exact_authorization") is not True: findings.append("v1269_authorization_boundary_missing")
    if r.get("canary_success_is_update_authority") is not False: findings.append("canary_conflated_with_update_authority")
    for key in DENIED_AUTHORITY:
        if r.get(key) is not False: findings.append(f"authority_expansion:{key}")
    if r.get("status") == "canary_ready_for_operator_replacement_review" and r.get("native_windows_canary_passed") is not True:
        findings.append("native_pending_promoted_to_full_ready")
    if r.get("status") == "portable_canary_ready_native_pending" and r.get("portable_canary_passed") is not True:
        findings.append("portable_ready_without_portable_pass")
    return {"ok": not findings, "status": "canary_reliability_ready" if not findings else "canary_reliability_blocked", "findings": findings, "read_only": True, "content_free": True, **DENIED_AUTHORITY}

def inspect_canary_surface_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = [
        "conscious_agent/canary_self_updates_foundations.py",
        "conscious_agent/canary_self_updates.py",
        "conscious_agent/canary_self_updates_reliability.py",
        "conscious_agent/governed_self_update.py",
        "conscious_agent/comprehensive_verification.py",
    ]
    checks = {path: (root / path).is_file() for path in required}
    return {"ok": all(checks.values()), "status": "canary_self_update_surface_ready" if all(checks.values()) else "canary_self_update_surface_blocked", "checks": checks, "mandatory_signals": list(MANDATORY_SIGNALS), "native_signal": NATIVE_SIGNAL, "native_windows_validation": "desktop_review_required", "read_only": True, "content_free": True, **DENIED_AUTHORITY}
