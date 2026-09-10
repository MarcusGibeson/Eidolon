from __future__ import annotations

"""Read-only v1190.5 Operator Navigation and Coordinated Experience checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_experience_foundations import build_unified_experience_snapshot
from unified_experience_foundations_checkpoint import _surface_rows
from unified_experience_navigation import coordinate_experience_navigation, create_navigation_request, create_navigation_review, navigation_public_summary

CONTRACT_VERSION = "v1190.5"
_CHECKPOINT_ID = "unified-experience-navigation:v1190.5"
_EXCLUDED = {"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports"}
_LIMITATIONS = (
    "Navigation changes only the content-free operator focus and does not mutate subsystem state.",
    "Current snapshot and context digests are caller-supplied evidence rather than independently fetched live state.",
    "Historical navigation, queueing, cancellation, and latency hardening remain outside v1190.3-v1190.5.",
    "No approval is created or consumed and no action, recovery, provider, model, installation, promotion, certification, publication, or release authority is invoked.",
    "Desktop Codex and native-provider review remain deferred until v1200.",
)


def _h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


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
        count += 1; digest.update(relative.encode()); digest.update(b"\0"); digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count


def _snapshot() -> dict[str, Any]:
    context = _h("v1190.5:context")
    rows = _surface_rows(context_digest=context, focus_domain="campaign")
    return build_unified_experience_snapshot(
        experience_id="unified-experience-1190-5",
        context_digest=context,
        surfaces=rows,
        selected_surface_id="experience-surface-campaign",
        operator_view_digest=_h("v1190.5:view"),
    )


def _request(snapshot: dict[str, Any], *, to_domain: str = "approval", reason: str = "review_required") -> dict[str, Any]:
    return create_navigation_request(
        navigation_id="navigation-request-1190-5",
        experience_id=str(snapshot["experience_id"]),
        snapshot_digest=str(snapshot["unified_experience_digest"]),
        from_surface_id="experience-surface-campaign",
        from_domain="campaign",
        to_surface_id=f"experience-surface-{to_domain}",
        to_domain=to_domain,
        reason=reason,
        context_digest=str(snapshot["context_digest"]),
        operator_review_digest=_h("v1190.5:navigation-operator-review"),
    )


def build_unified_experience_navigation_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve(); del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []; require = lambda value: checks.append(bool(value))
    snapshot = _snapshot(); request = _request(snapshot)
    approved_review = create_navigation_review(navigation_digest=request["navigation_digest"], decision="approve", review_id="navigation-review-approve", operator_review_digest=_h("review:approve"))
    approved = coordinate_experience_navigation(snapshot=snapshot, navigation=request, review=approved_review, current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    require(approved.get("status") == "navigation_ready"); require(approved.get("focus_changed") is True); require(approved.get("presented_domain") == "approval"); require(approved.get("presented_state") == "approved_not_executed"); require(approved.get("accountable_transition") is True)
    summary = navigation_public_summary(approved); require(summary.get("content_free") is True); require(summary.get("authority_granted") is False); require(summary.get("execution_invoked") is False)

    outcomes: dict[str, dict[str, Any]] = {}
    for decision in ("reject", "defer"):
        review = create_navigation_review(navigation_digest=request["navigation_digest"], decision=decision, review_id=f"navigation-review-{decision}", operator_review_digest=_h(f"review:{decision}"))
        outcomes[decision] = coordinate_experience_navigation(snapshot=snapshot, navigation=request, review=review, current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
        require(outcomes[decision].get("status") == f"navigation_{'rejected' if decision == 'reject' else 'deferred'}"); require(outcomes[decision].get("focus_changed") is False); require(outcomes[decision].get("presented_domain") == "campaign")

    blocked: dict[str, dict[str, Any]] = {}
    stale_snapshot = dict(request); stale_snapshot["snapshot_digest"] = _h("stale"); stale_snapshot["navigation_digest"] = _digest({k:v for k,v in stale_snapshot.items() if k != "navigation_digest"})
    blocked["stale_snapshot"] = coordinate_experience_navigation(snapshot=snapshot, navigation=stale_snapshot, review=create_navigation_review(navigation_digest=stale_snapshot["navigation_digest"], decision="approve", review_id="review-stale-snapshot", operator_review_digest=_h("review:stale")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    stale_context = dict(request); stale_context["context_digest"] = _h("wrong-context"); stale_context["navigation_digest"] = _digest({k:v for k,v in stale_context.items() if k != "navigation_digest"})
    blocked["stale_context"] = coordinate_experience_navigation(snapshot=snapshot, navigation=stale_context, review=create_navigation_review(navigation_digest=stale_context["navigation_digest"], decision="approve", review_id="review-stale-context", operator_review_digest=_h("review:context")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    bad_focus = dict(request); bad_focus["from_surface_id"] = "experience-surface-planning"; bad_focus["from_domain"] = "planning"; bad_focus["navigation_digest"] = _digest({k:v for k,v in bad_focus.items() if k != "navigation_digest"})
    blocked["stale_focus"] = coordinate_experience_navigation(snapshot=snapshot, navigation=bad_focus, review=create_navigation_review(navigation_digest=bad_focus["navigation_digest"], decision="approve", review_id="review-stale-focus", operator_review_digest=_h("review:focus")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    no_op = dict(request); no_op.update({"to_surface_id":"experience-surface-campaign", "to_domain":"campaign"}); no_op["navigation_digest"] = _digest({k:v for k,v in no_op.items() if k != "navigation_digest"})
    blocked["no_op"] = coordinate_experience_navigation(snapshot=snapshot, navigation=no_op, review=create_navigation_review(navigation_digest=no_op["navigation_digest"], decision="approve", review_id="review-no-op", operator_review_digest=_h("review:no-op")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    tampered = dict(request); tampered["to_domain"] = "result"
    blocked["tampered"] = coordinate_experience_navigation(snapshot=snapshot, navigation=tampered, review=approved_review, current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    private = dict(request); private["message_text"] = "forbidden"; private["navigation_digest"] = _digest({k:v for k,v in private.items() if k != "navigation_digest"})
    blocked["private"] = coordinate_experience_navigation(snapshot=snapshot, navigation=private, review=create_navigation_review(navigation_digest=private["navigation_digest"], decision="approve", review_id="review-private", operator_review_digest=_h("review:private")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    authority = dict(request); authority["authority_requested"] = True; authority["navigation_digest"] = _digest({k:v for k,v in authority.items() if k != "navigation_digest"})
    blocked["authority"] = coordinate_experience_navigation(snapshot=snapshot, navigation=authority, review=create_navigation_review(navigation_digest=authority["navigation_digest"], decision="approve", review_id="review-authority", operator_review_digest=_h("review:authority")), current_context_digest=snapshot["context_digest"], current_snapshot_digest=snapshot["unified_experience_digest"])
    for row in blocked.values(): require(row.get("status") == "blocked"); require(row.get("error_count", 0) > 0); require(row.get("focus_changed") is False); require(row.get("authority_granted") is False); require(row.get("execution_invoked") is False)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "unified-experience-navigation-checkpoint"), None)
    require(descriptor is not None); require((descriptor or {}).get("contract_version") == CONTRACT_VERSION); require((descriptor or {}).get("builder") == "build_unified_experience_navigation_checkpoint"); require(not registry.get("duplicate_checkpoint_ids")); require(not registry.get("duplicate_builder_targets"))
    privacy = package_privacy_summary_for_root(source); require(privacy.get("forbidden_entry_count", 0) == 0); require(privacy.get("private_content_finding_count", 0) == 0)
    after_digest, after_count = _tree_signature(source); require(before_digest == after_digest); require(before_count == after_count)
    return {
        "ok": all(checks), "passed": sum(checks), "total": len(checks), "contract_version": CONTRACT_VERSION, "checkpoint_id": _CHECKPOINT_ID,
        "read_only": True, "post_available": False, "content_free": True, "source_modified": False, "runtime_mutated": False,
        "production_source_modified": False, "sandbox_modified": False, "provider_contacted": False, "model_contacted": False,
        "automatic_continuation": False, "approval_created": False, "approval_consumed": False, "execution_invoked": False,
        "authority_granted": False, "authority_preserved": True, "desktop_verification_deferred_until_v1200": True,
        "source_signature_before": before_digest, "source_signature_after": after_digest, "source_file_count": before_count,
        "summary": {"approved_navigation_count": 1, "rejected_navigation_count": 1, "deferred_navigation_count": 1, "blocked_boundary_case_count": len(blocked), "from_domain": "campaign", "presented_domain": approved.get("presented_domain", "")},
        "limitations": list(_LIMITATIONS),
        "structural_digest": _digest({"checkpoint_id": _CHECKPOINT_ID, "approved": approved.get("transition_digest", ""), "blocked": {k:v.get("transition_digest", "") for k,v in sorted(blocked.items())}}),
    }
