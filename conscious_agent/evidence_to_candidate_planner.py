from __future__ import annotations

"""Bind attributable product evidence to bounded, review-only development plans."""

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


CONTRACT_VERSION = "v2503.4.1"
MAX_PLANS = 8
MAX_TARGET_FILES = 2
MAX_TEST_FILES = 8
PRODUCT_EVIDENCE_CLASSES = frozenset({
    "operator_reported_defect",
    "failing_test",
    "diagnostic_finding",
    "performance_regression",
    "conversation_quality_finding",
    "missing_capability",
    "security_debt",
})
_PROTECTED_PARTS = frozenset({"data", ".git", ".venv", "venv", "install_backups", "workspaces"})
_SURFACES = {
    "model_quality": (
        ("conscious_agent/conversation_context.py", "conscious_agent/context_assembly_architecture.py"),
        ("conversation", "response", "context"),
    ),
    "conversation": (
        ("conscious_agent/conversation_context.py", "conscious_agent/context_assembly_architecture.py"),
        ("conversation", "response", "context"),
    ),
    "interface": (
        ("conscious_agent/desktop_shell.py", "conscious_agent/dashboard.py"),
        ("desktop", "dashboard", "chat_usability"),
    ),
    "dashboard_or_chat_ui": (
        ("conscious_agent/desktop_shell.py", "conscious_agent/dashboard.py"),
        ("desktop", "dashboard", "chat_usability"),
    ),
    "bounded_research": (
        ("conscious_agent/bounded_research_reasoning.py", "conscious_agent/bounded_autonomous_web_research.py"),
        ("bounded_research", "research", "evidence", "source", "citation", "follow_up"),
    ),
    "research": (
        ("conscious_agent/bounded_research_reasoning.py", "conscious_agent/bounded_autonomous_web_research.py"),
        ("bounded_research", "research", "evidence", "source", "citation", "follow_up"),
    ),
    "session_continuity": (
        ("conscious_agent/conversation_context.py", "conscious_agent/context_assembly_architecture.py"),
        ("continuity", "context", "daily_companion"),
    ),
    "conversation_continuity": (
        ("conscious_agent/conversation_context.py", "conscious_agent/context_assembly_architecture.py"),
        ("continuity", "context", "daily_companion"),
    ),
    "provider_transport": (
        ("conscious_agent/provider_recovery.py", "conscious_agent/provider_availability.py"),
        ("provider", "local_model", "recovery"),
    ),
    "performance": (
        ("conscious_agent/provider_aware_performance.py", "conscious_agent/v1489_product_capability_integration.py"),
        ("performance", "responsiveness", "v1489_product"),
    ),
    "security": (
        ("conscious_agent/security.py", "conscious_agent/privacy_security_findings_receipts.py"),
        ("security", "privacy", "secret"),
    ),
}
_CURRENT_SURFACE_TESTS = {
    "model_quality": (
        "tools/v1085_0_context_assembly_architecture_tests.py",
        "tools/v1500_8_conversation_target_continuity_tests.py",
        "tools/v1500_9_integrated_daily_use_conversation_tests.py",
        "tools/v1500_9_2_conversation_evidence_boundary_tests.py",
    ),
    "conversation": (
        "tools/v1085_0_context_assembly_architecture_tests.py",
        "tools/v1500_8_conversation_target_continuity_tests.py",
        "tools/v1500_9_integrated_daily_use_conversation_tests.py",
        "tools/v1500_9_2_conversation_evidence_boundary_tests.py",
    ),
    "bounded_research": (
        "tools/v2503_4_evidence_language_consistency_source_quality_tests.py",
        "tools/v2503_3_source_independence_recommendation_confidence_tests.py",
        "tools/v2503_2_candidate_specific_evidence_follow_up_tests.py",
        "tools/v2503_3_live_failure_replay_stress_tests.py",
    ),
    "research": (
        "tools/v2503_4_evidence_language_consistency_source_quality_tests.py",
        "tools/v2503_3_source_independence_recommendation_confidence_tests.py",
        "tools/v2503_2_candidate_specific_evidence_follow_up_tests.py",
        "tools/v2503_3_live_failure_replay_stress_tests.py",
    ),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _safe_source_path(source_root: Path, value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip().lstrip("/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts or _PROTECTED_PARTS.intersection(path.parts):
        return ""
    if path.suffix.lower() != ".py" or not text.startswith("conscious_agent/"):
        return ""
    candidate = (source_root / Path(*path.parts)).resolve()
    try:
        candidate.relative_to(source_root)
    except ValueError:
        return ""
    return path.as_posix() if candidate.is_file() else ""


def _surface(row: Mapping[str, Any]) -> str:
    for value in (row.get("issue_domain"), row.get("affected_surface")):
        token = str(value or "").strip().lower()
        if token in _SURFACES:
            return token
    evidence_class = str(row.get("evidence_class") or "")
    return "security" if evidence_class == "security_debt" else "performance" if evidence_class == "performance_regression" else ""


def _target_files(source_root: Path, row: Mapping[str, Any], surface: str) -> list[str]:
    explicit = _safe_source_path(source_root, row.get("source_module"))
    targets = [explicit] if explicit else []
    for value in (_SURFACES.get(surface) or ((), ()))[0]:
        safe = _safe_source_path(source_root, value)
        if safe and safe not in targets:
            targets.append(safe)
        if len(targets) >= MAX_TARGET_FILES:
            break
    return targets


def _test_files(source_root: Path, targets: Iterable[str], surface: str) -> list[str]:
    tools = source_root / "tools"
    if not tools.is_dir():
        return []
    current = [
        value for value in _CURRENT_SURFACE_TESTS.get(surface, ())
        if (source_root / Path(*PurePosixPath(value).parts)).is_file()
    ]
    if current:
        return current[:MAX_TEST_FILES]
    target_tokens = {Path(value).stem.lower() for value in targets}
    surface_tokens = set((_SURFACES.get(surface) or ((), ()))[1])
    ranked: list[tuple[int, str]] = []
    for path in tools.glob("*.py"):
        name = path.name.lower()
        if "test" not in name:
            continue
        score = 4 * sum(token in name for token in target_tokens) + sum(token in name for token in surface_tokens)
        if score:
            ranked.append((-score, path.relative_to(source_root).as_posix()))
    return [path for _, path in sorted(ranked)[:MAX_TEST_FILES]]


def _acceptance(row: Mapping[str, Any], surface: str) -> list[str]:
    supplied = [str(value) for value in row.get("acceptance_criteria") or () if str(value)]
    defaults = [
        "finding_reproduced_with_synthetic_or_operator_supplied_fixture",
        "target_behavior_improves_against_attributable_evidence",
        "focused_regression_checks_pass",
        "source_runtime_and_privacy_boundaries_remain_intact",
    ]
    if surface in {"model_quality", "conversation", "session_continuity", "conversation_continuity"}:
        defaults.append("operator_daily_use_retrial_required")
    return list(dict.fromkeys([*supplied, *defaults]))[:8]


def build_evidence_to_candidate_plans(
    evidence_intake: Mapping[str, Any] | None,
    *,
    source_root: str | Path,
) -> dict[str, Any]:
    """Return deterministic product plans without creating proposals or execution authority."""

    root = Path(source_root).expanduser().resolve()
    plans: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for raw in list((evidence_intake or {}).get("records") or ()):
        row = dict(raw or {})
        evidence_class = str(row.get("evidence_class") or "")
        if evidence_class not in PRODUCT_EVIDENCE_CLASSES or bool(row.get("structural_only")):
            continue
        evidence_id = str(row.get("evidence_id") or "")
        evidence_digest = str(row.get("evidence_digest") or "")
        if not evidence_id or len(evidence_digest) != 64:
            rejected.append({"evidence_id": evidence_id, "reason": "attributable_evidence_identity_required"})
            continue
        surface = _surface(row)
        targets = _target_files(root, row, surface) if surface else []
        tests = _test_files(root, targets, surface) if targets else []
        freshness = str(row.get("freshness") or "unknown")
        ready = bool(surface and targets and tests and freshness != "stale")
        state = "bounded_plan_ready" if ready else "scope_binding_required"
        stable = {
            "evidence_id": evidence_id,
            "evidence_digest": evidence_digest,
            "evidence_class": evidence_class,
            "issue_domain": str(row.get("issue_domain") or "unknown"),
            "affected_surface": surface or str(row.get("issue_domain") or "unknown"),
            "target_files": targets,
            "test_files": tests,
            "acceptance_criteria": _acceptance(row, surface),
            "impact_score": round(max(0.0, min(1.0, float(row.get("impact_score") or 0.0))), 4),
            "confidence": round(max(0.0, min(1.0, float(row.get("confidence") or 0.0))), 4),
            "freshness": freshness,
            "planning_state": state,
            "implementation_ready": ready,
            "operator_review_required": True,
            "content_free": True,
        }
        stable["candidate_plan_id"] = f"devplan_{_digest(stable)[:24]}"
        stable["candidate_plan_digest"] = _digest(stable)
        plans.append(stable)
    plans.sort(key=lambda item: (-int(item["implementation_ready"]), -float(item["impact_score"]), item["candidate_plan_id"]))
    plans = plans[:MAX_PLANS]
    result = {
        "ok": any(plan["implementation_ready"] for plan in plans),
        "status": "bounded_product_candidate_plan_ready" if any(plan["implementation_ready"] for plan in plans) else "no_bounded_product_candidate_plan",
        "contract_version": CONTRACT_VERSION,
        "plans": plans,
        "plan_count": len(plans),
        "ready_count": sum(bool(plan["implementation_ready"]) for plan in plans),
        "rejected": rejected[:MAX_PLANS],
        "rejected_count": len(rejected),
        "private_content_inspected": False,
        "provider_contacted": False,
        "proposal_created": False,
        "workspace_prepared": False,
        "tests_executed": False,
        "source_modified": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["planning_digest"] = _digest({"contract_version": CONTRACT_VERSION, "plans": [p["candidate_plan_digest"] for p in plans], "rejected": rejected})
    return result


def evidence_to_candidate_response(planning: Mapping[str, Any]) -> str:
    ready = next((dict(row) for row in planning.get("plans") or () if row.get("implementation_ready")), None)
    if ready:
        return (
            f"I bound attributable {ready.get('evidence_class')} evidence {ready.get('evidence_id')} to bounded product plan "
            f"{ready.get('candidate_plan_id')} digest {str(ready.get('candidate_plan_digest') or '')[:16]}. The review scope contains "
            f"{len(ready.get('target_files') or ())} source files and {len(ready.get('test_files') or ())} attributable test files. "
            "This is a review-only plan: no proposal, provider request, workspace, test, source change, installation, or authority was created."
        )
    if planning.get("plan_count"):
        return (
            "I found product evidence, but could not bind it to both a confined source scope and attributable tests. "
            "I stopped at scope review instead of inventing an implementable candidate."
        )
    return (
        "No active attributable product finding is available to plan. Record or confirm a concrete operator finding from a daily-use trial, "
        "diagnostic failure, performance regression, security review, or missing-capability review before continuing development."
    )


__all__ = [
    "CONTRACT_VERSION",
    "MAX_PLANS",
    "MAX_TARGET_FILES",
    "MAX_TEST_FILES",
    "PRODUCT_EVIDENCE_CLASSES",
    "build_evidence_to_candidate_plans",
    "evidence_to_candidate_response",
]
