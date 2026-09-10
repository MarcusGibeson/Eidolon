from __future__ import annotations

"""v1256.9 read-only Persistent Development Sessions checkpoint.

This checkpoint inspects source and structured release metadata only. It does
not read operator development-session runtime state, resume work, contact a
provider, run project commands/tests, apply/rollback a candidate, repair runtime
metadata, or grant authority. Behavioral evidence is retained in v1256.0-.8.
"""

import ast
import hashlib
from pathlib import Path
from typing import Any

try:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint
    from release_authority import WORKING_SOURCE_VERSION
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint  # type: ignore
    from release_authority import WORKING_SOURCE_VERSION  # type: ignore

CONTRACT_VERSION = "v1256.9"

_REQUIRED_SOURCE = (
    "conscious_agent/persistent_development_sessions_foundations.py",
    "conscious_agent/persistent_development_sessions.py",
    "conscious_agent/persistent_development_sessions_reliability.py",
    "conscious_agent/ordinary_chat_development_campaign.py",
    "tools/v1256_0_2_persistent_development_session_foundations_tests.py",
    "tools/v1256_3_5_persistent_development_session_integration_tests.py",
    "tools/v1256_6_8_persistent_development_session_reliability_tests.py",
    "tools/v1256_9_persistent_development_sessions_checkpoint_tests.py",
)


def _root(value: str | Path | None = None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(node.value)
            except (TypeError, ValueError):
                return None
    return None


def build_persistent_development_sessions_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(source_root)
    files = {relative: root / relative for relative in _REQUIRED_SOURCE}
    foundations = files["conscious_agent/persistent_development_sessions_foundations.py"]
    integration = files["conscious_agent/persistent_development_sessions.py"]
    reliability = files["conscious_agent/persistent_development_sessions_reliability.py"]
    ordinary = files["conscious_agent/ordinary_chat_development_campaign.py"]
    foundation_text = foundations.read_text(encoding="utf-8") if foundations.is_file() else ""
    integration_text = integration.read_text(encoding="utf-8") if integration.is_file() else ""
    reliability_text = reliability.read_text(encoding="utf-8") if reliability.is_file() else ""
    ordinary_text = ordinary.read_text(encoding="utf-8") if ordinary.is_file() else ""
    denied = _literal_assignment(foundations, "DENIED_AUTHORITY") if foundations.is_file() else None
    record = lookup_checkpoint("1256.9")

    checks = {
        "working_source_at_or_after_v1256_9": tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1256, 9),
        "required_v1256_surfaces_present": all(path.is_file() for path in files.values()),
        "foundation_contract_retained": _literal_assignment(foundations, "CONTRACT_VERSION") == "v1256.2" if foundations.is_file() else False,
        "integration_contract_retained": _literal_assignment(integration, "CONTRACT_VERSION") == "v1256.5" if integration.is_file() else False,
        "reliability_contract_retained": _literal_assignment(reliability, "CONTRACT_VERSION") == "v1256.8" if reliability.is_file() else False,
        "session_authority_defaults_denied": isinstance(denied, dict) and bool(denied) and not any(bool(value) for value in denied.values()),
        "requirements_plan_attempt_evidence_present": all(token in foundation_text for token in ("requirements_digest", "plan_digest", "attempt_evidence", "verification_digest")),
        "restart_safe_resume_present": "resume_persistent_development_session" in integration_text and "existing_exact_authorization_required" in integration_text,
        "duplicate_progress_dedup_present": "identity_digest" in integration_text and "operation_status\": \"restored" in integration_text,
        "stale_source_guard_present": "operator_reconcile_source" in foundation_text and "stale_source_detected" in foundation_text,
        "expired_lease_recovery_projection_present": "expired_lease_recovery_requires_original_exact_authorization" in integration_text,
        "corrupt_metadata_recovery_present": "session_recovered_from_authoritative_lineage" in reliability_text and "persistent_development_session_quarantine" in reliability_text,
        "ordinary_chat_session_controls_present": "process_persistent_development_session_control" in ordinary_text,
        "operator_handoff_present": "build_persistent_development_session_handoff" in reliability_text,
        "v1256_9_registered_exactly": bool(record and record.test_selector == "tools/v1256_9_persistent_development_sessions_checkpoint_tests.py"),
    }
    hashes = {relative: _sha256(path) for relative, path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version="1256.9",
        status="persistent_development_sessions_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "required_source_count": len(_REQUIRED_SOURCE),
            "present_source_count": len(hashes),
            "source_sha256": hashes,
            "behavioral_evidence": [
                "tools/v1256_0_2_persistent_development_session_foundations_tests.py",
                "tools/v1256_3_5_persistent_development_session_integration_tests.py",
                "tools/v1256_6_8_persistent_development_session_reliability_tests.py",
            ],
            "requirements_preserved_across_restart": True,
            "plans_preserved_across_restart": True,
            "attempt_and_verification_evidence_preserved": True,
            "duplicate_execution_authorized": False,
            "automatic_resume_authorized": False,
            "provider_contact_authorized": False,
            "project_mutation_authorized": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "certification_authorized": False,
            "release_authorized": False,
            "permanent_approval_granted": False,
            "independent_authority_granted": False,
            "native_windows_lock_long_path_restart_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_persistent_development_sessions_checkpoint"]
