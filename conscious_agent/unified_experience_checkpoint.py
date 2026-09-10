from __future__ import annotations

"""Read-only v1190.9 Unified Experience checkpoint.

Consolidates the v1190 foundations, operator navigation, coordinated
presentation, stale-state handling, privacy hardening, and reliability-review
contracts. All cases are synthetic and content-free. The checkpoint reads no
private subsystem records and mutates no source or runtime state.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_experience_foundations_checkpoint import build_unified_experience_foundations_checkpoint
from unified_experience_navigation import coordinate_experience_navigation, create_navigation_review, navigation_public_summary
from unified_experience_navigation_checkpoint import _request, _snapshot, build_unified_experience_navigation_checkpoint
from unified_experience_reliability import ACTIONS, INTERRUPTIONS, assess_unified_experience_reliability, create_reliability_assessment, create_reliability_review, reliability_public_summary
from unified_experience_reliability_checkpoint import build_unified_experience_reliability_checkpoint

CONTRACT_VERSION = "v1190.9"
_CHECKPOINT_ID = "unified-experience:v1190.9"
_EXCLUDED = {"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports"}
_LIMITATIONS = (
    "Unified surfaces, freshness, privacy, and authority observations remain caller-supplied content-free evidence.",
    "The checkpoint does not independently fetch live subsystem state or private records.",
    "Approved navigation and reliability review alter presentation evidence only and execute no refresh or recovery.",
    "Queueing, cancellation, latency hardening, and background-work separation begin in v1191.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
)


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256(); count = 0; paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}: paths.append(path)
    for path in sorted(paths):
        try: relative = path.relative_to(root).as_posix(); data = path.read_bytes()
        except OSError: continue
        count += 1; digest.update(relative.encode("utf-8")); digest.update(b"\0"); digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count


def _resign(row: Mapping[str, Any], field: str, **changes: object) -> dict[str, Any]:
    updated = dict(row); updated.update(changes); updated.pop(field, None); updated[field] = _digest(updated); return updated


def _navigation(snapshot: Mapping[str, Any], *, to_domain: str, decision: str = "approve") -> dict[str, Any]:
    request = _request(dict(snapshot), to_domain=to_domain, reason="operator_navigation")
    request = _resign(request, "navigation_digest", navigation_id=f"unified-navigation-{to_domain}-1190-9")
    review = create_navigation_review(
        navigation_digest=request["navigation_digest"], decision=decision,
        review_id=f"unified-navigation-review-{to_domain}-{decision}",
        operator_review_digest=_h(f"v1190.9:navigation:{to_domain}:{decision}"),
    )
    return coordinate_experience_navigation(
        snapshot=snapshot, navigation=request, review=review,
        current_context_digest=str(snapshot["context_digest"]),
        current_snapshot_digest=str(snapshot["unified_experience_digest"]),
    )


def _assessment(*, snapshot: Mapping[str, Any], transition: Mapping[str, Any], interruption: str = "none",
                observed_context_digest: str | None = None, observed_focus_surface_id: str | None = None,
                snapshot_digest: str | None = None, privacy_finding_count: int = 0,
                authority_claim_count: int = 0) -> dict[str, Any]:
    return create_reliability_assessment(
        reliability_id=f"unified-reliability-{interruption}-1190-9",
        experience_id=str(snapshot["experience_id"]),
        snapshot_digest=str(snapshot_digest or snapshot["unified_experience_digest"]),
        transition_digest=str(transition["transition_digest"]),
        expected_context_digest=str(snapshot["context_digest"]),
        observed_context_digest=str(observed_context_digest or snapshot["context_digest"]),
        expected_focus_surface_id=str(transition["presented_surface_id"]),
        observed_focus_surface_id=str(observed_focus_surface_id or transition["presented_surface_id"]),
        interruption=interruption, privacy_finding_count=privacy_finding_count,
        authority_claim_count=authority_claim_count,
    )


def build_unified_experience_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve(); del runtime_root
    before_digest, before_count = _tree_signature(source); checks: list[bool] = []; require = lambda value: checks.append(bool(value))

    retained = (
        build_unified_experience_foundations_checkpoint(source_root=source),
        build_unified_experience_navigation_checkpoint(source_root=source),
        build_unified_experience_reliability_checkpoint(source_root=source),
    )
    for report, version in zip(retained, ("v1190.2", "v1190.5", "v1190.8")):
        for key, value in (
            ("ok", True), ("contract_version", version), ("read_only", True), ("post_available", False),
            ("content_free", True), ("source_modified", False), ("runtime_mutated", False),
            ("provider_contacted", False), ("model_contacted", False), ("execution_invoked", False),
            ("authority_granted", False), ("authority_preserved", True),
            ("desktop_verification_deferred_until_v1200", True),
        ): require(report.get(key) == value)
        require(report.get("passed") == report.get("total"))

    snapshot = _snapshot()
    for key, value in (
        ("status", "ready_for_operator_view"), ("surface_count", 9), ("domain_count", 9),
        ("selected_domain", "campaign"), ("records_duplicated", False), ("content_free", True),
        ("execution_invoked", False), ("authority_granted", False),
    ): require(snapshot.get(key) == value)

    navigable_domains = ("conversation", "cognition", "reasoning", "planning", "approval", "action", "result", "learning")
    approved_transitions: dict[str, dict[str, Any]] = {}
    for domain in navigable_domains:
        row = _navigation(snapshot, to_domain=domain, decision="approve"); approved_transitions[domain] = row
        for key, value in (
            ("status", "navigation_ready"), ("focus_changed", True), ("from_domain", "campaign"),
            ("presented_domain", domain), ("accountable_transition", True), ("content_free", True),
            ("execution_invoked", False), ("automatic_continuation", False), ("authority_granted", False),
        ): require(row.get(key) == value)
        summary = navigation_public_summary(row); require(summary.get("presented_domain") == domain); require(summary.get("content_free") is True); require(summary.get("authority_granted") is False)

    inert_navigation: dict[str, dict[str, Any]] = {}
    for decision, expected in (("reject", "navigation_rejected"), ("defer", "navigation_deferred")):
        row = _navigation(snapshot, to_domain="approval", decision=decision); inert_navigation[decision] = row
        require(row.get("status") == expected); require(row.get("focus_changed") is False); require(row.get("presented_domain") == "campaign"); require(row.get("execution_invoked") is False); require(row.get("authority_granted") is False)

    transition = approved_transitions["approval"]; base = _assessment(snapshot=snapshot, transition=transition); reliability_reviews = 0
    for decision, expected_status in (("approve", "reliability_ready"), ("reject", "reliability_rejected"), ("defer", "reliability_deferred")):
        for action in sorted(ACTIONS):
            review = create_reliability_review(
                reliability_digest=base["reliability_digest"], decision=decision, action=action,
                review_id=f"unified-reliability-review-{decision}-{action}",
                operator_review_digest=_h(f"v1190.9:reliability:{decision}:{action}"),
            )
            result = assess_unified_experience_reliability(
                snapshot=snapshot, transition=transition, assessment=base, review=review,
                current_snapshot_digest=str(snapshot["unified_experience_digest"]),
                current_context_digest=str(snapshot["context_digest"]),
                current_focus_surface_id=str(transition["presented_surface_id"]),
            ); reliability_reviews += 1
            for key, value in (
                ("status", expected_status), ("decision", decision), ("action", action),
                ("snapshot_current", True), ("context_current", True), ("focus_current", True),
                ("privacy_clear", True), ("authority_clear", True), ("operator_review_required", True),
                ("recovery_executed", False), ("subsystem_state_changed", False), ("execution_invoked", False),
                ("automatic_continuation", False), ("authority_granted", False),
            ): require(result.get(key) == value)
            public = reliability_public_summary(result); require(public.get("content_free") is True); require(public.get("recovery_executed") is False); require(public.get("authority_granted") is False)

    variants = {
        "stale_snapshot": _assessment(snapshot=snapshot, transition=transition, interruption="stale_snapshot", snapshot_digest=_h("v1190.9:stale-snapshot")),
        "stale_context": _assessment(snapshot=snapshot, transition=transition, interruption="stale_context", observed_context_digest=_h("v1190.9:stale-context")),
        "stale_focus": _assessment(snapshot=snapshot, transition=transition, interruption="stale_focus", observed_focus_surface_id="experience-surface-planning"),
        "privacy_block": _assessment(snapshot=snapshot, transition=transition, interruption="privacy_block", privacy_finding_count=1),
        "authority_claim": _assessment(snapshot=snapshot, transition=transition, interruption="transition_failure", authority_claim_count=1),
    }
    unsupported = _assessment(snapshot=snapshot, transition=transition); variants["unsupported_interruption"] = _resign(unsupported, "reliability_digest", interruption="unsupported")
    tampered = _assessment(snapshot=snapshot, transition=transition); tampered["experience_id"] = "tampered-experience"; variants["tampered_reliability"] = tampered
    private = _assessment(snapshot=snapshot, transition=transition); variants["private_field"] = _resign(private, "reliability_digest", message_text="forbidden")
    authority = _assessment(snapshot=snapshot, transition=transition); variants["authority_field"] = _resign(authority, "reliability_digest", release_authority=True)
    blocked: dict[str, dict[str, Any]] = {}
    for name, assessment in variants.items():
        review = create_reliability_review(
            reliability_digest=str(assessment.get("reliability_digest", "")), decision="approve", action="hold",
            review_id=f"unified-reliability-blocked-{name}", operator_review_digest=_h(f"v1190.9:blocked:{name}"),
        )
        result = assess_unified_experience_reliability(
            snapshot=snapshot, transition=transition, assessment=assessment, review=review,
            current_snapshot_digest=str(snapshot["unified_experience_digest"]),
            current_context_digest=str(snapshot["context_digest"]),
            current_focus_surface_id=str(transition["presented_surface_id"]),
        ); blocked[name] = result
        require(result.get("status") == "blocked"); require(int(result.get("error_count", 0)) >= 1)
        for key in ("recovery_executed", "subsystem_state_changed", "execution_invoked", "automatic_continuation", "source_modified", "runtime_modified", "provider_contacted", "model_contacted", "authority_granted"):
            require(result.get(key) is False)
        require(result.get("content_free") is True)

    require(set(INTERRUPTIONS) == {"none", "stale_snapshot", "stale_context", "stale_focus", "privacy_block", "transition_failure"})
    require(set(ACTIONS) == {"hold", "refresh_snapshot", "return_to_conversation", "abandon_navigation"})
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "unified-experience-checkpoint"), None)
    require(descriptor is not None); require((descriptor or {}).get("contract_version") == CONTRACT_VERSION); require((descriptor or {}).get("builder") == "build_unified_experience_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids")); require(not registry.get("duplicate_builder_targets")); require(registry.get("provider_contacted") is False); require(registry.get("runtime_data_read") is False); require(registry.get("source_modified") is False)
    privacy = package_privacy_summary_for_root(source); require(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) == 0); require(privacy.get("private_content_finding_count", 0) == 0)
    after_digest, after_count = _tree_signature(source); require(before_digest == after_digest); require(before_count == after_count)
    report = {
        "ok": all(checks), "passed": sum(checks), "total": len(checks), "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID, "read_only": True, "post_available": False, "content_free": True,
        "source_modified": False, "runtime_mutated": False, "production_source_modified": False,
        "sandbox_modified": False, "provider_contacted": False, "model_contacted": False,
        "automatic_refresh": False, "automatic_recovery": False, "automatic_continuation": False,
        "approval_created": False, "approval_consumed": False, "execution_invoked": False,
        "subsystem_state_changed": False, "recovery_executed": False, "policy_modified": False,
        "future_work_selection_modified": False, "authority_granted": False, "authority_preserved": True,
        "desktop_verification_deferred_until_v1200": True, "source_signature_before": before_digest,
        "source_signature_after": after_digest, "source_file_count": before_count,
        "summary": {"retained_bundle_count": 3, "domain_count": 9, "approved_navigation_domain_count": len(approved_transitions),
                    "inert_navigation_decision_count": len(inert_navigation), "reliability_review_case_count": reliability_reviews,
                    "interruption_class_count": len(INTERRUPTIONS), "presentation_action_count": len(ACTIONS),
                    "blocked_boundary_case_count": len(blocked), "initial_focus_domain": "campaign", "reviewed_focus_domain": "approval"},
        "limitations": list(_LIMITATIONS),
    }
    report["structural_digest"] = _digest(report); return report
