from __future__ import annotations

"""v1257.9 read-only Diagnostic and Repair Reasoning checkpoint.

The checkpoint inspects source and structured release metadata only.  It never
opens operator runtime diagnosis records, runs diagnostics/tests, contacts a
provider, creates a repair, applies a candidate, or grants authority.
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

CONTRACT_VERSION = "v1257.9"

_REQUIRED_SOURCE = (
    "conscious_agent/diagnostic_repair_reasoning_foundations.py",
    "conscious_agent/diagnostic_repair_reasoning.py",
    "conscious_agent/diagnostic_repair_reasoning_reliability.py",
    "conscious_agent/isolated_coding_execution.py",
    "conscious_agent/persistent_development_sessions_foundations.py",
    "tools/v1257_0_2_diagnostic_repair_reasoning_foundations_tests.py",
    "tools/v1257_3_5_diagnostic_repair_reasoning_integration_tests.py",
    "tools/v1257_6_8_diagnostic_repair_reasoning_reliability_tests.py",
    "tools/v1257_9_diagnostic_repair_reasoning_checkpoint_tests.py",
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


def build_diagnostic_repair_reasoning_checkpoint(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = _root(source_root)
    files = {relative: root / relative for relative in _REQUIRED_SOURCE}
    foundations = files["conscious_agent/diagnostic_repair_reasoning_foundations.py"]
    integration = files["conscious_agent/diagnostic_repair_reasoning.py"]
    reliability = files["conscious_agent/diagnostic_repair_reasoning_reliability.py"]
    execution = files["conscious_agent/isolated_coding_execution.py"]
    sessions = files["conscious_agent/persistent_development_sessions_foundations.py"]
    foundation_text = foundations.read_text(encoding="utf-8") if foundations.is_file() else ""
    integration_text = integration.read_text(encoding="utf-8") if integration.is_file() else ""
    reliability_text = reliability.read_text(encoding="utf-8") if reliability.is_file() else ""
    execution_text = execution.read_text(encoding="utf-8") if execution.is_file() else ""
    sessions_text = sessions.read_text(encoding="utf-8") if sessions.is_file() else ""
    denied = _literal_assignment(foundations, "DENIED_AUTHORITY") if foundations.is_file() else None
    record = lookup_checkpoint("1257.9")
    checks = {
        "working_source_at_or_after_v1257_9": tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1257, 9),
        "required_v1257_surfaces_present": all(path.is_file() for path in files.values()),
        "foundation_contract_retained": _literal_assignment(foundations, "CONTRACT_VERSION") == "v1257.2" if foundations.is_file() else False,
        "integration_contract_retained": _literal_assignment(integration, "CONTRACT_VERSION") == "v1257.5" if integration.is_file() else False,
        "reliability_contract_retained": _literal_assignment(reliability, "CONTRACT_VERSION") == "v1257.8" if reliability.is_file() else False,
        "diagnostic_authority_defaults_denied": isinstance(denied, dict) and bool(denied) and not any(bool(value) for value in denied.values()),
        "competing_hypotheses_present": all(token in foundation_text for token in ("form_competing_explanations", "disproof_test", "root_cause_proven")),
        "focused_diagnostics_present": all(token in integration_text for token in ("individual_test_file_isolation", "changed_source_syntax_guard", "run_focused_diagnostics")),
        "repair_prompt_receives_diagnosis": "diagnostic_context" in execution_text and "provider_repair_context" in execution_text,
        "genuine_blocker_postures_present": all(token in integration_text for token in ("blocked_environment", "blocked_stale_source", "blocked_repeated_failed_repair")),
        "duplicate_diagnostic_lease_present": "diagnostic_operation_in_progress" in integration_text and "lease_expires_unix" in integration_text,
        "tamper_and_health_inspection_present": "diagnostic_repair_reasoning_health_blocked" in reliability_text and "diagnostic_result_" in reliability_text,
        "persistent_session_links_diagnostic_evidence": all(token in sessions_text for token in ("diagnostic_result_digest", "diagnostic_repair_posture", "diagnostic_preferred_hypothesis")),
        "operator_handoff_present": "build_diagnostic_repair_operator_handoff" in reliability_text,
        "v1257_9_registered_exactly": bool(record and record.test_selector == "tools/v1257_9_diagnostic_repair_reasoning_checkpoint_tests.py"),
    }
    hashes = {relative: _sha256(path) for relative, path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version="1257.9",
        status="diagnostic_repair_reasoning_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "required_source_count": len(_REQUIRED_SOURCE),
            "present_source_count": len(hashes),
            "source_sha256": hashes,
            "behavioral_evidence": [
                "tools/v1257_0_2_diagnostic_repair_reasoning_foundations_tests.py",
                "tools/v1257_3_5_diagnostic_repair_reasoning_integration_tests.py",
                "tools/v1257_6_8_diagnostic_repair_reasoning_reliability_tests.py",
            ],
            "competing_explanations_required": True,
            "root_cause_proven_by_default": False,
            "focused_diagnostics_bounded": True,
            "repeated_failed_repair_blocked": True,
            "environment_failure_can_block_repair": True,
            "persistent_session_diagnostic_lineage": True,
            "provider_contact_authorized": False,
            "diagnostic_execution_authorized": False,
            "repair_authorized": False,
            "project_mutation_authorized": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "certification_authorized": False,
            "release_authorized": False,
            "permanent_approval_granted": False,
            "independent_authority_granted": False,
            "native_windows_cross_process_diagnostic_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_diagnostic_repair_reasoning_checkpoint"]
