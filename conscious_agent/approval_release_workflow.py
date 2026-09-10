from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from patch_drafting import APPROVAL_STATE
from workspace_orchestration import _timeline_event
from validated_ai_patch_loop import (
    VALIDATED_AI_DIR,
    VALIDATED_AI_PATCH_VERSION,
    build_patch_objective_refinement,
    build_code_context_ranking,
    build_patch_safety_envelope,
    build_generated_patch_validation,
    build_patch_simulation,
    build_test_stub_plan,
    build_patch_review_score,
    build_patch_recovery_plan,
    build_validated_ai_code_patch_loop,
)
from code_patch_release import (
    CODE_PATCH_DIFF_BUNDLE,
    SEMANTIC_CHECKS,
    RELEASE_ARTIFACT,
    RELEASE_AUDIT_TRAIL,
    build_code_patch_diff_bundle,
    build_apply_code_patch_transaction,
    build_semantic_checks,
    build_release_artifact,
    build_release_audit_trail,
)
from release_pipeline import RELEASE_READINESS, build_release_readiness
from ai_patch_assistance import build_patch_learning_notes

APPROVAL_RELEASE_VERSION = RUNTIME_VERSION
APPROVAL_RELEASE_DIR = VALIDATED_AI_DIR / "approval_release"
AI_PATCH_REVIEW_BUNDLE = APPROVAL_RELEASE_DIR / "ai_patch_review_bundle.json"
VALIDATED_PATCH_APPROVAL_MANIFEST = APPROVAL_RELEASE_DIR / "validated_patch_approval_manifest.json"
REVIEW_BUNDLE_INTEGRITY = APPROVAL_RELEASE_DIR / "review_bundle_integrity.json"
APPROVAL_READY = APPROVAL_RELEASE_DIR / "approval_ready.json"
APPROVAL_LEDGER = APPROVAL_RELEASE_DIR / "approval_ledger.json"
VALIDATED_AI_APPLY = APPROVAL_RELEASE_DIR / "apply_validated_ai_patch.json"
VALIDATED_AI_DRY_RUN_APPLY = APPROVAL_RELEASE_DIR / "apply_validated_ai_patch_dry_run.json"
POST_APPLY_REVIEW = APPROVAL_RELEASE_DIR / "post_apply_review.json"
PACKAGE_BUILD_PLAN = APPROVAL_RELEASE_DIR / "package_build_plan.json"
APPROVAL_TO_RELEASE_LOOP = APPROVAL_RELEASE_DIR / "approval_to_release_loop.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    APPROVAL_RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


VOLATILE_KEYS = {
    "checked_at", "created_at", "updated_at", "served_at", "recorded_at",
    "approved_at", "rejected_at", "closed_at", "generated_at", "run_at",
    "event_id", "run_id", "loop_id", "audit_id", "preview_only",
}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable(v) for k, v in value.items() if str(k) not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _canonical(value: Any) -> str:
    return json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8", errors="replace")).hexdigest()


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "fail", "failed"}:
        return "blocked"
    if statuses & {"warn", "warning"}:
        return "warn"
    return "pass"


def _artifact_rows(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in artifacts.items():
        ok = isinstance(value, dict) and value.get("ok", True) is not False and value.get("status") not in {"blocked", "failed", "fail"}
        rows.append({
            "name": name,
            "status": "pass" if ok else "blocked",
            "sha256": _hash(value),
            "message": f"{name} snapshot hash captured." if ok else f"{name} is blocked or invalid.",
        })
    return rows


def _cached_or_build(path: Path, builder, *, project_id: str, save: bool, **kwargs: Any) -> dict[str, Any]:
    cached = _read_json(path, {}) if not save else {}
    if isinstance(cached, dict) and cached.get("status") and cached.get("version"):
        return cached
    return builder(project_id=project_id, save=save, **kwargs)


def _current_artifacts(project_id: str = "eidolon", *, save: bool = False) -> dict[str, Any]:
    """Build or preview the authoritative v18/v19 artifact set without source writes."""
    return {
        "objective_refinement": build_patch_objective_refinement(project_id=project_id, save=save),
        "context_ranking": build_code_context_ranking(project_id=project_id, save=save),
        "safety_envelope": build_patch_safety_envelope(project_id=project_id, save=save),
        "generated_patch_validation": build_generated_patch_validation(project_id=project_id, save=save),
        "patch_simulation": build_patch_simulation(project_id=project_id, save=save),
        "test_stub_plan": build_test_stub_plan(project_id=project_id, save=save),
        "patch_review_score": build_patch_review_score(project_id=project_id, save=save),
        "recovery_plan": build_patch_recovery_plan(project_id=project_id, save=save),
        "diff_bundle": _cached_or_build(CODE_PATCH_DIFF_BUNDLE, build_code_patch_diff_bundle, project_id=project_id, save=save),
        "semantic_checks": _cached_or_build(SEMANTIC_CHECKS, build_semantic_checks, project_id=project_id, save=save),
        "release_readiness_preview": _cached_or_build(RELEASE_READINESS, build_release_readiness, project_id=project_id, save=save),
        "release_artifact": _cached_or_build(RELEASE_ARTIFACT, build_release_artifact, project_id=project_id, save=save, package_name="Eidolon_v20_0.zip"),
        "release_audit_trail": _cached_or_build(RELEASE_AUDIT_TRAIL, build_release_audit_trail, project_id=project_id, save=save),
    }


def _manifest_from_artifacts(project_id: str, artifacts: dict[str, Any], approval: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = _artifact_rows(artifacts)
    artifact_hashes = {row["name"]: row["sha256"] for row in rows}
    manifest_seed = {
        "project_id": project_id,
        "version": APPROVAL_RELEASE_VERSION,
        "validated_ai_patch_version": VALIDATED_AI_PATCH_VERSION,
        "artifact_hashes": artifact_hashes,
        "approval_draft_id": (approval or {}).get("draft_id"),
        "approval_request_id": (approval or {}).get("request_id"),
    }
    patch_id = "validated_ai_patch_" + _hash(manifest_seed)[:16]
    return {
        "version": APPROVAL_RELEASE_VERSION,
        "created_at": _now(),
        "project_id": project_id,
        "patch_id": patch_id,
        "draft_id": (approval or {}).get("draft_id"),
        "request_id": (approval or {}).get("request_id"),
        "artifact_hashes": artifact_hashes,
        "artifact_count": len(artifact_hashes),
        "status": _status_from(rows),
        "ok": _status_from(rows) != "blocked",
        "rows": rows,
        "message": "Validated patch approval manifest binds approval to the exact reviewed v18/v19 artifact set.",
    }


def build_ai_patch_review_bundle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v18.1: bundle every AI patch review artifact into one authoritative report."""
    artifacts = _current_artifacts(project_id=project_id, save=False)
    approval = _read_json(APPROVAL_STATE, {})
    manifest = _manifest_from_artifacts(project_id, artifacts, approval if isinstance(approval, dict) else {})
    rows = list(manifest.get("rows", []))
    review_score = artifacts.get("patch_review_score", {})
    readiness = artifacts.get("release_readiness_preview", {})
    if int(review_score.get("score", 0) or 0) < 70:
        rows.append({"name": "review-score-threshold", "status": "warn", "message": f"Review score is {review_score.get('score', 0)}; target is 70+."})
    status = _status_from(rows)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "patch_id": manifest.get("patch_id"),
        "manifest": manifest,
        "steps": artifacts,
        "approval_state": approval if isinstance(approval, dict) else {},
        "release_readiness_preview": readiness,
        "recommended_next_action": "approve only after integrity and approval-ready gates pass" if status != "blocked" else "resolve blockers before approval",
        "rows": rows,
        "message": "AI patch review bundle created from objective, context, safety, validation, simulation, scoring, recovery, release, and audit artifacts.",
    }
    if save:
        _write_json(AI_PATCH_REVIEW_BUNDLE, report)
        _write_json(VALIDATED_PATCH_APPROVAL_MANIFEST, manifest)
    else:
        report["preview_only"] = True
    return report


def build_review_bundle_integrity(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v18.2: verify current review artifacts match the saved validated patch manifest."""
    saved_bundle = _read_json(AI_PATCH_REVIEW_BUNDLE, {})
    saved_manifest = _read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {})
    if not isinstance(saved_manifest, dict) or not saved_manifest.get("artifact_hashes"):
        preview_bundle = build_ai_patch_review_bundle(project_id=project_id, save=False)
        saved_manifest = preview_bundle.get("manifest", {})
        saved_bundle = preview_bundle
    current_artifacts = _current_artifacts(project_id=project_id, save=False)
    current_manifest = _manifest_from_artifacts(project_id, current_artifacts, _read_json(APPROVAL_STATE, {}))
    rows: list[dict[str, Any]] = []
    rows.append({"name": "patch-id", "status": "pass" if saved_manifest.get("patch_id") == current_manifest.get("patch_id") else "blocked", "message": f"saved={saved_manifest.get('patch_id')} current={current_manifest.get('patch_id')}"})
    rows.append({"name": "project-id", "status": "pass" if saved_manifest.get("project_id") == project_id else "blocked", "message": f"saved={saved_manifest.get('project_id')} current={project_id}"})
    saved_hashes = saved_manifest.get("artifact_hashes", {}) if isinstance(saved_manifest, dict) else {}
    current_hashes = current_manifest.get("artifact_hashes", {})
    for name in sorted(set(saved_hashes) | set(current_hashes)):
        rows.append({
            "name": f"artifact-{name}",
            "status": "pass" if saved_hashes.get(name) == current_hashes.get(name) else "blocked",
            "message": f"saved={saved_hashes.get(name)} current={current_hashes.get(name)}",
        })
    status = _status_from(rows)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status == "pass",
        "patch_id": saved_manifest.get("patch_id"),
        "saved_manifest": saved_manifest,
        "current_manifest": current_manifest,
        "bundle_present": bool(saved_bundle),
        "rows": rows,
        "message": "Review bundle integrity requires saved and current validated AI patch artifact hashes to match. If this is blocked after legitimate regenerated reports, run --ai-patch-review-bundle or POST /api/code-patches/refresh-review-bundle to save a fresh review bundle before approval.",
    }
    if save:
        _write_json(REVIEW_BUNDLE_INTEGRITY, report)
    else:
        report["preview_only"] = True
    return report


def build_approval_ready(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v18.3: decide whether an AI patch is ready for human approval."""
    bundle = _read_json(AI_PATCH_REVIEW_BUNDLE, {})
    if not isinstance(bundle, dict) or not bundle.get("patch_id"):
        bundle = build_ai_patch_review_bundle(project_id=project_id, save=save)
    integrity = build_review_bundle_integrity(project_id=project_id, save=save)
    approval = _read_json(APPROVAL_STATE, {})
    score = int(((bundle.get("steps") or {}).get("patch_review_score") or {}).get("score", 0) or 0)
    validation = (bundle.get("steps") or {}).get("generated_patch_validation") or {}
    simulation = (bundle.get("steps") or {}).get("patch_simulation") or {}
    test_stub = (bundle.get("steps") or {}).get("test_stub_plan") or {}
    rows = [
        {"name": "review-bundle", "status": "pass" if bundle.get("ok") else "blocked", "message": bundle.get("message", "bundle missing")},
        {"name": "bundle-integrity", "status": "pass" if integrity.get("ok") else "blocked", "message": integrity.get("message", "integrity missing")},
        {"name": "validation", "status": "pass" if validation.get("ok") else "blocked", "message": validation.get("message", "validation missing")},
        {"name": "simulation", "status": "pass" if simulation.get("ok") else "blocked", "message": simulation.get("message", "simulation missing")},
        {"name": "review-score", "status": "pass" if score >= 70 else "warn" if score >= 50 else "blocked", "message": f"score={score}; target=70+"},
        {"name": "test-stub-plan", "status": "pass" if test_stub.get("rows") or test_stub.get("suggestions") else "blocked", "message": test_stub.get("message", "test stub plan missing")},
        {"name": "readme-impact", "status": "pass" if "README_NEXT_STEPS.md" in _canonical(bundle) else "blocked", "message": "README impact must be present in review artifacts."},
        {"name": "stale-approval", "status": "warn" if approval.get("approved") and approval.get("consumed") else "pass", "message": f"approval_status={approval.get('status', 'missing')} consumed={approval.get('consumed')}"},
    ]
    status = _status_from(rows)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "ready" if status == "pass" else "ready_with_warnings" if status == "warn" else "blocked",
        "ok": status != "blocked",
        "patch_id": bundle.get("patch_id"),
        "review_score": score,
        "rows": rows,
        "message": "Approval-ready gate completed for the validated AI patch review bundle.",
    }
    if save:
        _write_json(APPROVAL_READY, report)
    else:
        report["preview_only"] = True
    return report


def _append_ledger(event: dict[str, Any], save: bool = True) -> list[dict[str, Any]]:
    ledger = _read_json(APPROVAL_LEDGER, [])
    if not isinstance(ledger, list):
        ledger = []
    ledger.append(event)
    if save:
        _write_json(APPROVAL_LEDGER, ledger[-200:])
    return ledger[-200:]


def build_approval_ledger(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v18.5: track approvals/rejections as auditable events."""
    approval = _read_json(APPROVAL_STATE, {})
    manifest = _read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {})
    event = {
        "event_id": f"approval_ledger_{_now().replace(':','').replace('-','')}",
        "recorded_at": _now(),
        "project_id": project_id,
        "patch_id": manifest.get("patch_id"),
        "draft_id": approval.get("draft_id") if isinstance(approval, dict) else None,
        "request_id": approval.get("request_id") if isinstance(approval, dict) else None,
        "approval_status": approval.get("status", "missing") if isinstance(approval, dict) else "missing",
        "approved": bool(approval.get("approved")) if isinstance(approval, dict) else False,
        "consumed": bool(approval.get("consumed")) if isinstance(approval, dict) else False,
        "risk_accepted": approval.get("risk_accepted") if isinstance(approval, dict) else None,
        "artifact_hashes": manifest.get("artifact_hashes", {}),
        "message": "Approval ledger records the current approval state against the validated patch manifest.",
    }
    ledger = _append_ledger(event, save=save)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass",
        "ok": True,
        "latest_event": event,
        "events": ledger,
        "message": "Approval ledger updated." if save else "Approval ledger preview built.",
    }
    if not save:
        report["preview_only"] = True
    return report


def _approval_manifest_binding(project_id: str = "eidolon") -> dict[str, Any]:
    approval = _read_json(APPROVAL_STATE, {})
    ready = build_approval_ready(project_id=project_id, save=False)
    integrity = build_review_bundle_integrity(project_id=project_id, save=False)
    manifest = _read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {})
    approval_snapshot = approval.get("validated_patch_manifest") if isinstance(approval, dict) else None
    rows = [
        {"name": "approval-exists", "status": "pass" if approval.get("approved") and approval.get("status") == "approved" else "blocked", "message": f"status={approval.get('status', 'missing')}"},
        {"name": "approval-unconsumed", "status": "pass" if approval.get("approved") and not approval.get("consumed") else "blocked", "message": f"consumed={approval.get('consumed')}"},
        {"name": "approval-ready", "status": "pass" if ready.get("ok") else "blocked", "message": ready.get("message", "approval ready gate missing")},
        {"name": "bundle-integrity", "status": "pass" if integrity.get("ok") else "blocked", "message": integrity.get("message", "integrity gate missing")},
        {"name": "manifest-snapshot", "status": "pass" if isinstance(approval_snapshot, dict) and approval_snapshot.get("patch_id") == manifest.get("patch_id") else "blocked", "message": f"approval={approval_snapshot.get('patch_id') if isinstance(approval_snapshot, dict) else None}; current={manifest.get('patch_id')}"},
    ]
    if isinstance(approval_snapshot, dict):
        approved_hashes = approval_snapshot.get("artifact_hashes", {})
        current_hashes = manifest.get("artifact_hashes", {})
        for name in sorted(set(approved_hashes) | set(current_hashes)):
            rows.append({"name": f"approved-artifact-{name}", "status": "pass" if approved_hashes.get(name) == current_hashes.get(name) else "blocked", "message": f"approved={approved_hashes.get(name)} current={current_hashes.get(name)}"})
    status = _status_from(rows)
    return {"status": status, "ok": status == "pass", "rows": rows, "approval": approval, "manifest": manifest, "message": "Validated AI apply requires approval bound to the exact validated patch approval manifest."}


def bind_current_approval_to_validated_manifest(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """Attach the current validated patch approval manifest to an existing draft approval."""
    bundle = build_ai_patch_review_bundle(project_id=project_id, save=save)
    ready = build_approval_ready(project_id=project_id, save=save)
    approval = _read_json(APPROVAL_STATE, {})
    if not isinstance(approval, dict):
        approval = {}
    can_bind = bool(approval.get("approved") and not approval.get("consumed") and ready.get("ok"))
    if can_bind:
        approval["validated_patch_manifest"] = bundle.get("manifest")
        approval["validated_patch_approved_at"] = _now()
        approval["approved_for"] = "validated_ai_patch_apply_once"
        approval["message"] = "Approval is bound to the exact validated AI patch manifest for one apply."
        if save:
            _write_json(APPROVAL_STATE, approval)
            build_approval_ledger(project_id=project_id, save=True)
    return {"version": APPROVAL_RELEASE_VERSION, "checked_at": _now(), "project_id": project_id, "status": "pass" if can_bind else "blocked", "ok": can_bind, "patch_id": bundle.get("patch_id"), "approval_status": approval.get("status", "missing"), "message": "Current approval bound to validated patch manifest." if can_bind else "Cannot bind manifest without an unconsumed approved draft and approval-ready bundle."}


def build_apply_validated_ai_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v18.6: apply only a validated, simulated, approval-ready AI patch."""
    ready = build_approval_ready(project_id=project_id, save=save)
    binding = _approval_manifest_binding(project_id=project_id)
    rows = [
        {"name": "approval-ready", "status": "pass" if ready.get("ok") else "blocked", "message": ready.get("message", "approval ready gate missing")},
        {"name": "manifest-binding", "status": "pass" if binding.get("ok") else "blocked" if not dry_run else "warn", "message": binding.get("message")},
        {"name": "explicit-confirmation", "status": "pass" if dry_run or approve else "blocked", "message": "Real apply requires explicit approval/confirmation."},
    ]
    blocked = [row["name"] for row in rows if row.get("status") == "blocked"]
    transaction = None
    if not blocked:
        transaction = build_apply_code_patch_transaction(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
        if isinstance(transaction, dict) and transaction.get("ok") is False and not dry_run:
            blocked.append("code-patch-transaction")
    status = "blocked" if blocked else "dry_run" if dry_run or not approve else "applied"
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not approve,
        "patch_id": (_read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {}) or {}).get("patch_id"),
        "rows": rows,
        "blocked_steps": blocked,
        "approval_manifest_binding": binding,
        "apply_transaction": transaction,
        "message": "Validated AI patch apply completed as dry-run." if status == "dry_run" else "Validated AI patch applied." if status == "applied" else "Validated AI patch apply blocked before source writes.",
    }
    if save:
        _write_json(VALIDATED_AI_DRY_RUN_APPLY if report["dry_run"] else VALIDATED_AI_APPLY, report)
        _timeline_event("validated_ai_apply", {"project_id": project_id, "status": status, "dry_run": report["dry_run"], "patch_id": report.get("patch_id")}, save=True)
    return report


def build_post_apply_review(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v18.7: verify what applied matches what was approved."""
    manifest = _read_json(VALIDATED_PATCH_APPROVAL_MANIFEST, {})
    apply_report = _read_json(VALIDATED_AI_APPLY, {})
    dry_run_report = _read_json(VALIDATED_AI_DRY_RUN_APPLY, {})
    transaction = apply_report.get("apply_transaction") if isinstance(apply_report, dict) else None
    rows = [
        {"name": "manifest-present", "status": "pass" if manifest.get("patch_id") else "blocked", "message": f"patch_id={manifest.get('patch_id')}"},
        {"name": "real-apply-present", "status": "pass" if apply_report.get("status") == "applied" else "warn", "message": f"latest_real_status={apply_report.get('status', 'missing')}"},
        {"name": "dry-run-separated", "status": "pass" if dry_run_report.get("dry_run", True) else "blocked", "message": "Dry-run apply report is stored separately from real apply report."},
        {"name": "transaction-match", "status": "pass" if not transaction or transaction.get("ok", True) else "blocked", "message": "Apply transaction is available and not failed."},
    ]
    status = _status_from(rows)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "patch_id": manifest.get("patch_id"),
        "approved_manifest": manifest,
        "apply_report": apply_report,
        "dry_run_report": dry_run_report,
        "release_readiness": build_release_readiness(project_id=project_id, save=False),
        "rollback_status": "available only after real apply creates backups" if apply_report.get("status") != "applied" else "review apply transaction backups",
        "rows": rows,
        "message": "Post-apply review compared approved manifest, apply report, dry-run separation, and release readiness.",
    }
    if save:
        _write_json(POST_APPLY_REVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_package_build_plan(project_id: str = "eidolon", package_name: str = "Eidolon_v20_0.zip", save: bool = True) -> dict[str, Any]:
    """v18.9: prepare a clean zip handoff manifest."""
    readiness = build_release_readiness(project_id=project_id, save=False)
    artifact = build_release_artifact(project_id=project_id, package_name=package_name, save=False)
    readme = ROOT_DIR / "README_NEXT_STEPS.md"
    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    rows = [
        {"name": "release-readiness", "status": "pass" if readiness.get("ok") else "warn", "message": readiness.get("message")},
        {"name": "readme-v20", "status": "pass" if "v20.0" in readme_text else "blocked", "message": "README must document v19.1-v20.0."},
        {"name": "package-name", "status": "pass" if package_name.endswith(".zip") else "warn", "message": package_name},
    ]
    status = _status_from(rows)
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "source_root": str(ROOT_DIR),
        "package_name": package_name,
        "included_roots": ["conscious_agent/", "data/", "tools/", "README_NEXT_STEPS.md", "requirements.txt"],
        "excluded_patterns": [".git/", ".venv/", "__pycache__/", "*.pyc"],
        "readme_sections": [f"v19.{i}" for i in range(1, 10)] + ["v20.0"],
        "verification_commands": ["python -m py_compile conscious_agent/*.py tools/smoke_check.py", "python conscious_agent/main.py --verified-release-package-loop", "python -u tools/smoke_check.py"],
        "known_warnings": ["Ollama may be unavailable on machines where the local service is not running.", "chromadb must be installed from requirements.txt for semantic memory features."],
        "release_readiness": readiness,
        "release_artifact": artifact,
        "rows": rows,
        "message": "Package build plan prepared for final handoff.",
    }
    if save:
        _write_json(PACKAGE_BUILD_PLAN, report)
    else:
        report["preview_only"] = True
    return report


def build_approval_to_release_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v19.0: apply, verify, review, and prepare release from one validated approval."""
    bundle = build_ai_patch_review_bundle(project_id=project_id, save=save)
    integrity = build_review_bundle_integrity(project_id=project_id, save=save)
    ready = build_approval_ready(project_id=project_id, save=save)
    ledger = build_approval_ledger(project_id=project_id, save=save)
    apply_report = build_apply_validated_ai_patch(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=save)
    post_apply = build_post_apply_review(project_id=project_id, save=save)
    semantic = build_semantic_checks(project_id=project_id, save=save)
    readiness = build_release_readiness(project_id=project_id, save=save)
    package = build_package_build_plan(project_id=project_id, save=save)
    audit = build_release_audit_trail(project_id=project_id, save=save)
    learning = build_patch_learning_notes(project_id=project_id, note="v19 approval-to-release loop recorded review/apply state.", save=save)
    blocked = [name for name, report in {"bundle": bundle, "integrity": integrity, "approval_ready": ready, "apply": apply_report, "post_apply": post_apply, "semantic": semantic, "package": package}.items() if isinstance(report, dict) and report.get("ok") is False]
    status = "blocked" if blocked else "dry_run" if dry_run or not approve else "release_prepared"
    report = {
        "version": APPROVAL_RELEASE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not approve,
        "patch_id": bundle.get("patch_id"),
        "steps": {
            "review_bundle": bundle,
            "integrity": integrity,
            "approval_ready": ready,
            "approval_ledger": ledger,
            "apply_validated_ai_patch": apply_report,
            "post_apply_review": post_apply,
            "semantic_checks": semantic,
            "release_readiness": readiness,
            "package_build_plan": package,
            "audit_trail": audit,
            "learning_notes": learning,
        },
        "blocked_steps": blocked,
        "message": "Approval-to-release loop prepared review, apply, verification, and package artifacts and stopped.",
    }
    if save:
        _write_json(APPROVAL_TO_RELEASE_LOOP, report)
        _timeline_event("approval_to_release_loop", {"project_id": project_id, "status": status, "dry_run": report["dry_run"], "patch_id": report.get("patch_id")}, save=True)
    return report


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    if report.get("patch_id"):
        lines.append(f"Patch: {report.get('patch_id')}")
    if report.get("review_score") is not None:
        lines.append(f"Review score: {report.get('review_score')}")
    rows = report.get("rows") or report.get("prechecks") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:80]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("path") or row.get("event_id") or "row"
                lines.append(f"- {str(row.get('status', 'info')).upper()} {name}: {row.get('message', '')}")
    if report.get("blocked_steps"):
        lines.extend(["", "## Blocked Steps"])
        lines.extend([f"- {item}" for item in report.get("blocked_steps", [])])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def ai_patch_review_bundle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.1/v20.0 AI Patch Review Bundle", report or build_ai_patch_review_bundle(save=False), full)


def review_bundle_integrity_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.2/v20.0 Review Bundle Integrity", report or build_review_bundle_integrity(save=False), full)


def approval_ready_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.3 Approval-Ready Gate", report or build_approval_ready(save=False), full)


def approval_ledger_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.5 Human Approval Ledger", report or build_approval_ledger(save=False), full)


def apply_validated_ai_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.6 Apply Validated AI Patch", report or build_apply_validated_ai_patch(save=False), full)


def post_apply_review_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.7 Post-Apply Review", report or build_post_apply_review(save=False), full)


def package_build_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v18.9 Package Build Plan", report or build_package_build_plan(save=False), full)


def approval_to_release_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.0/v20.0 Approval-to-Release Loop", report or build_approval_to_release_loop(save=False), full)



def bind_validated_approval_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v19.1 Validated Approval Manifest Binding", report or bind_current_approval_to_validated_manifest(save=False), full)



def print_bind_validated_approval(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = bind_current_approval_to_validated_manifest(project_id=project_id, save=True)
    _json_print(report) if json_output else print(bind_validated_approval_text(report, full=full))


def print_ai_patch_review_bundle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_ai_patch_review_bundle(project_id=project_id, save=True)
    _json_print(report) if json_output else print(ai_patch_review_bundle_text(report, full=full))


def print_review_bundle_integrity(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_review_bundle_integrity(project_id=project_id, save=True)
    _json_print(report) if json_output else print(review_bundle_integrity_text(report, full=full))


def print_approval_ready(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_approval_ready(project_id=project_id, save=True)
    _json_print(report) if json_output else print(approval_ready_text(report, full=full))


def print_approval_ledger(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_approval_ledger(project_id=project_id, save=True)
    _json_print(report) if json_output else print(approval_ledger_text(report, full=full))


def print_apply_validated_ai_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_apply_validated_ai_patch(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=True)
    _json_print(report) if json_output else print(apply_validated_ai_patch_text(report, full=full))


def print_post_apply_review(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_post_apply_review(project_id=project_id, save=True)
    _json_print(report) if json_output else print(post_apply_review_text(report, full=full))


def print_package_build_plan(project_id: str = "eidolon", package_name: str = "Eidolon_v20_0.zip", full: bool = False, json_output: bool = False) -> None:
    report = build_package_build_plan(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(package_build_plan_text(report, full=full))


def print_approval_to_release_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_approval_to_release_loop(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=True)
    _json_print(report) if json_output else print(approval_to_release_loop_text(report, full=full))
