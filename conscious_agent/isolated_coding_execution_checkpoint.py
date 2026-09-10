from __future__ import annotations

"""v1254.9 read-only Isolated Coding Execution checkpoint.

This checkpoint inspects only source and release metadata. It does not read
private runtime state, contact a provider, execute project tests or commands,
materialize a workspace, recover a campaign, mutate source, or grant authority.
Behavioral evidence is supplied by the retained v1254.0-.8 deterministic suites;
this surface verifies that the expected implementation, integration, reliability,
and release boundaries are present for operator/Desktop review.
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

CONTRACT_VERSION = "v1254.9"

_REQUIRED_SOURCE = (
    "conscious_agent/isolated_coding_execution_foundations.py",
    "conscious_agent/isolated_coding_execution.py",
    "conscious_agent/isolated_coding_execution_reliability.py",
    "conscious_agent/ordinary_chat_development_campaign.py",
    "tools/v1254_0_2_isolated_coding_execution_foundations_tests.py",
    "tools/v1254_3_5_isolated_coding_execution_integration_tests.py",
    "tools/v1254_6_8_isolated_coding_execution_reliability_tests.py",
    "tools/v1254_9_isolated_coding_execution_checkpoint_tests.py",
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


def build_isolated_coding_execution_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(source_root)
    files = {relative: root / relative for relative in _REQUIRED_SOURCE}
    source_exists = all(path.is_file() for path in files.values())

    foundations = files["conscious_agent/isolated_coding_execution_foundations.py"]
    execution = files["conscious_agent/isolated_coding_execution.py"]
    reliability = files["conscious_agent/isolated_coding_execution_reliability.py"]
    ordinary = files["conscious_agent/ordinary_chat_development_campaign.py"]
    foundation_authority = _literal_assignment(foundations, "AUTHORITY_STATE") if foundations.is_file() else None
    execution_text = execution.read_text(encoding="utf-8") if execution.is_file() else ""
    reliability_text = reliability.read_text(encoding="utf-8") if reliability.is_file() else ""
    ordinary_text = ordinary.read_text(encoding="utf-8") if ordinary.is_file() else ""
    record = lookup_checkpoint("1254.9")

    checks = {
        "working_source_retains_v1254_9_or_later": tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1254, 9),
        "required_v1254_surfaces_present": source_exists,
        "foundation_contract_retained": _literal_assignment(foundations, "CONTRACT_VERSION") == "v1254.2" if foundations.is_file() else False,
        "execution_contract_retained": _literal_assignment(execution, "CONTRACT_VERSION") == "v1254.5" if execution.is_file() else False,
        "reliability_contract_retained": _literal_assignment(reliability, "CONTRACT_VERSION") == "v1254.8" if reliability.is_file() else False,
        "foundation_authority_defaults_denied": isinstance(foundation_authority, dict) and bool(foundation_authority) and not any(bool(value) for value in foundation_authority.values()),
        "exact_execution_authorization_present": "Authorize isolated coding execution for request" in execution_text,
        "bounded_attempt_limit_present": _literal_assignment(execution, "MAX_EXECUTION_ATTEMPTS") == 3,
        "selected_project_application_stays_denied": '"source_application_authorized": False' in execution_text and '"selected_project_modified": False' in execution_text,
        "test_tamper_rejection_present": "existing_project_test_change_rejected" in execution_text,
        "stale_source_rechecked_around_generation": execution_text.count("check_coding_source_freshness(request_id") >= 2,
        "ordinary_chat_bridge_present": "prepare_isolated_coding_from_approved_proposal" in ordinary_text and "process_isolated_coding_execution_control" in ordinary_text,
        "operator_handoff_present": "build_isolated_coding_operator_handoff" in reliability_text,
        "expired_lease_recovery_disposition_present": "same_exact_authorization_may_recover" in reliability_text,
        "v1254_9_registered_exactly": bool(record and record.test_selector == "tools/v1254_9_isolated_coding_execution_checkpoint_tests.py"),
    }
    hashes = {relative: _sha256(path) for relative, path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version="1254.9",
        status="isolated_coding_execution_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "required_source_count": len(_REQUIRED_SOURCE),
            "present_source_count": len(hashes),
            "source_sha256": hashes,
            "behavioral_evidence": [
                "tools/v1254_0_2_isolated_coding_execution_foundations_tests.py",
                "tools/v1254_3_5_isolated_coding_execution_integration_tests.py",
                "tools/v1254_6_8_isolated_coding_execution_reliability_tests.py",
            ],
            "selected_project_application_authorized": False,
            "installation_authorized": False,
            "release_authorized": False,
            "permanent_approval_granted": False,
            "independent_authority_granted": False,
            "native_windows_junction_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_isolated_coding_execution_checkpoint"]
