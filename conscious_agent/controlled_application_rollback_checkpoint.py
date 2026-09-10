from __future__ import annotations

"""v1255.9 read-only Controlled Application and Rollback checkpoint.

The checkpoint inspects source and structured release metadata only. It does not
read private development runtime state, apply or roll back a candidate, execute
project commands/tests, contact a provider, create backups, or grant authority.
Behavioral evidence remains in the retained v1255.0-.8 deterministic suites.
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

CONTRACT_VERSION = "v1255.9"

_REQUIRED_SOURCE = (
    "conscious_agent/controlled_application_rollback_foundations.py",
    "conscious_agent/controlled_application_rollback.py",
    "conscious_agent/controlled_application_rollback_reliability.py",
    "conscious_agent/ordinary_chat_development_campaign.py",
    "tools/v1255_test_support.py",
    "tools/v1255_0_2_controlled_application_foundations_tests.py",
    "tools/v1255_3_5_controlled_application_integration_tests.py",
    "tools/v1255_6_8_controlled_application_reliability_tests.py",
    "tools/v1255_9_controlled_application_rollback_checkpoint_tests.py",
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


def build_controlled_application_rollback_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(source_root)
    files = {relative: root / relative for relative in _REQUIRED_SOURCE}
    foundations = files["conscious_agent/controlled_application_rollback_foundations.py"]
    execution = files["conscious_agent/controlled_application_rollback.py"]
    reliability = files["conscious_agent/controlled_application_rollback_reliability.py"]
    ordinary = files["conscious_agent/ordinary_chat_development_campaign.py"]
    foundation_text = foundations.read_text(encoding="utf-8") if foundations.is_file() else ""
    execution_text = execution.read_text(encoding="utf-8") if execution.is_file() else ""
    reliability_text = reliability.read_text(encoding="utf-8") if reliability.is_file() else ""
    ordinary_text = ordinary.read_text(encoding="utf-8") if ordinary.is_file() else ""
    denied = _literal_assignment(foundations, "DENIED_AUTHORITY") if foundations.is_file() else None
    record = lookup_checkpoint("1255.9")

    checks = {
        "working_source_at_or_after_v1255_9": tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1255, 9),
        "required_v1255_surfaces_present": all(path.is_file() for path in files.values()),
        "foundation_contract_retained": _literal_assignment(foundations, "CONTRACT_VERSION") == "v1255.2" if foundations.is_file() else False,
        "application_contract_retained": _literal_assignment(execution, "CONTRACT_VERSION") == "v1255.5" if execution.is_file() else False,
        "reliability_contract_retained": _literal_assignment(reliability, "CONTRACT_VERSION") == "v1255.8" if reliability.is_file() else False,
        "preparation_authority_defaults_denied": isinstance(denied, dict) and bool(denied) and not any(bool(value) for value in denied.values()),
        "exact_application_authorization_present": "Authorize controlled application for request" in foundation_text,
        "separate_exact_rollback_authorization_present": "Authorize controlled rollback for request" in execution_text,
        "deferred_private_backup_present": "immediately_before_first_authorized_write" in foundation_text,
        "selective_conflict_detection_present": "unrelated_source_changes_allowed" in foundation_text and "windows_casefold_conflict" in foundation_text,
        "verification_failure_auto_restore_present": "controlled_application_verification_failed_rolled_back" in execution_text,
        "expired_lease_recovery_present": "controlled_application_completed_recovered" in execution_text,
        "ordinary_chat_controls_present": "process_controlled_application_rollback_control" in ordinary_text,
        "operator_handoff_present": "build_controlled_application_operator_handoff" in reliability_text,
        "v1255_9_registered_exactly": bool(record and record.test_selector == "tools/v1255_9_controlled_application_rollback_checkpoint_tests.py"),
    }
    hashes = {relative: _sha256(path) for relative, path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version="1255.9",
        status="controlled_application_rollback_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "required_source_count": len(_REQUIRED_SOURCE),
            "present_source_count": len(hashes),
            "source_sha256": hashes,
            "behavioral_evidence": [
                "tools/v1255_0_2_controlled_application_foundations_tests.py",
                "tools/v1255_3_5_controlled_application_integration_tests.py",
                "tools/v1255_6_8_controlled_application_reliability_tests.py",
            ],
            "controlled_application_authority_requires_exact_operator_phrase": True,
            "rollback_requires_separate_exact_operator_phrase": True,
            "installation_authorized": False,
            "promotion_authorized": False,
            "certification_authorized": False,
            "release_authorized": False,
            "permanent_approval_granted": False,
            "independent_authority_granted": False,
            "native_windows_junction_atomic_replace_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_controlled_application_rollback_checkpoint"]
