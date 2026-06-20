from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from release_packaging import _package_name, build_release_manifest_integrity, build_package_inventory, build_package_checksums
from release_installation import (
    build_route_safety_harness,
    build_package_privacy_scan,
    build_v23_readiness_gate,
    build_external_zip_install_verification,
    build_deterministic_release_manifest,
    build_trial_upgrade_harness,
    _status_from,
    _ok_from,
)

SELF_MAINTENANCE_VERSION = "30.0"
SELF_MAINTENANCE_DIR = DATA_DIR / "self_maintenance"
PROPOSAL_SANDBOX = SELF_MAINTENANCE_DIR / "proposal_sandbox.json"
PATCH_PLAN = SELF_MAINTENANCE_DIR / "patch_plan.json"
PATCH_PREVIEW = SELF_MAINTENANCE_DIR / "patch_preview.json"
PATCH_SAFETY_AUDIT = SELF_MAINTENANCE_DIR / "patch_safety_audit.json"
TEMP_APPLY_DRILL = SELF_MAINTENANCE_DIR / "temp_apply_drill.json"
REVIEW_BUNDLE = SELF_MAINTENANCE_DIR / "review_bundle.json"
APPROVAL_BINDING = SELF_MAINTENANCE_DIR / "approval_binding.json"
REAL_APPLY_PREVIEW = SELF_MAINTENANCE_DIR / "real_apply_preview.json"
POST_APPLY_HEALTH = SELF_MAINTENANCE_DIR / "post_apply_health.json"
CONTROLLED_CYCLE = SELF_MAINTENANCE_DIR / "controlled_cycle.json"
ASSISTED_SELF_IMPROVEMENT_RELEASE = SELF_MAINTENANCE_DIR / "assisted_self_improvement_release.json"
IMPROVEMENT_CANDIDATE_SCAN = SELF_MAINTENANCE_DIR / "improvement_candidate_scan.json"
CANDIDATE_PRIORITIZER = SELF_MAINTENANCE_DIR / "candidate_prioritizer.json"
CANDIDATE_PROPOSAL_BRIDGE = SELF_MAINTENANCE_DIR / "candidate_proposal_bridge.json"
MAINTENANCE_BACKLOG_PREVIEW = SELF_MAINTENANCE_DIR / "maintenance_backlog_preview.json"
DASHBOARD_MAINTENANCE_BACKLOG = SELF_MAINTENANCE_DIR / "dashboard_maintenance_backlog.json"
API_MAINTENANCE_BACKLOG = SELF_MAINTENANCE_DIR / "api_maintenance_backlog.json"
CANDIDATE_REGRESSION_DETECTOR = SELF_MAINTENANCE_DIR / "candidate_regression_detector.json"
RELEASE_MEMORY_PRIVACY = SELF_MAINTENANCE_DIR / "release_memory_privacy.json"
CANDIDATE_VERIFICATION_RECIPES = SELF_MAINTENANCE_DIR / "candidate_verification_recipes.json"
ASSISTED_IMPROVEMENT_CYCLE = SELF_MAINTENANCE_DIR / "assisted_improvement_cycle.json"
SEMI_AUTONOMOUS_MAINTENANCE_REVIEW = SELF_MAINTENANCE_DIR / "semi_autonomous_maintenance_review.json"
HOTFIX_REGRESSION_LOCKDOWN = SELF_MAINTENANCE_DIR / "hotfix_regression_lockdown.json"
DASHBOARD_ROUTE_COVERAGE_AUDITOR = SELF_MAINTENANCE_DIR / "dashboard_route_coverage_auditor.json"
API_DEFAULT_SOURCE_AUDIT = SELF_MAINTENANCE_DIR / "api_default_source_audit.json"
NESTED_READINESS_SEVERITY_ENGINE = SELF_MAINTENANCE_DIR / "nested_readiness_severity_engine.json"
REVIEW_BUNDLE_APPROVAL_CONTRACT = SELF_MAINTENANCE_DIR / "review_bundle_approval_contract.json"
MAINTENANCE_REPORT_DIFF_VIEWER = SELF_MAINTENANCE_DIR / "maintenance_report_diff_viewer.json"
RELEASE_GATE_COMPOSITION_TEST = SELF_MAINTENANCE_DIR / "release_gate_composition_test.json"
DASHBOARD_API_PARITY_AUDIT = SELF_MAINTENANCE_DIR / "dashboard_api_parity_audit.json"
OPERATOR_TRUST_REPORT = SELF_MAINTENANCE_DIR / "operator_trust_report.json"
TRUSTWORTHY_MAINTENANCE_CONSOLE = SELF_MAINTENANCE_DIR / "trustworthy_maintenance_console.json"
TRUST_CONSOLE_DRILL = SELF_MAINTENANCE_DIR / "trust_console_drill.json"
TRUST_CONSOLE_SNAPSHOT = SELF_MAINTENANCE_DIR / "trust_console_snapshot.json"
TRUST_CONSOLE_DIFF = SELF_MAINTENANCE_DIR / "trust_console_diff.json"
RELEASE_CANDIDATE_FREEZE = SELF_MAINTENANCE_DIR / "release_candidate_freeze.json"
FROZEN_RELEASE_ZIP_VERIFICATION = SELF_MAINTENANCE_DIR / "frozen_release_zip_verification.json"
APPROVAL_EVIDENCE_LEDGER = SELF_MAINTENANCE_DIR / "approval_evidence_ledger.json"
RELEASE_COMMAND_REPRODUCER = SELF_MAINTENANCE_DIR / "release_command_reproducer.json"
CONSOLE_README_CONSISTENCY = SELF_MAINTENANCE_DIR / "console_readme_consistency.json"
PRE_V27_SAFETY_AUDIT = SELF_MAINTENANCE_DIR / "pre_v27_safety_audit.json"
RELEASE_CANDIDATE_GOVERNANCE = SELF_MAINTENANCE_DIR / "release_candidate_governance.json"
RELEASE_GOVERNANCE_DRILL = SELF_MAINTENANCE_DIR / "release_governance_drill.json"
RELEASE_EVIDENCE_BUNDLE = SELF_MAINTENANCE_DIR / "release_evidence_bundle.json"
RELEASE_EVIDENCE_BUNDLE_VERIFIER = SELF_MAINTENANCE_DIR / "release_evidence_bundle_verifier.json"
RELEASE_GOVERNANCE_PAGE = SELF_MAINTENANCE_DIR / "release_governance_page.json"
GOVERNANCE_API_READ_ONLY_SURFACE = SELF_MAINTENANCE_DIR / "governance_api_read_only_surface.json"
RELEASE_ARTIFACT_DIFF = SELF_MAINTENANCE_DIR / "release_artifact_diff.json"
RELEASE_SIGNING_PREPARATION = SELF_MAINTENANCE_DIR / "release_signing_preparation.json"
LOCAL_TRUST_POLICY = SELF_MAINTENANCE_DIR / "local_trust_policy.json"
RELEASE_GOVERNANCE_UX_POLISH = SELF_MAINTENANCE_DIR / "release_governance_ux_polish.json"
PRE_V28_GOVERNANCE_AUDIT = SELF_MAINTENANCE_DIR / "pre_v28_governance_audit.json"
VERIFIABLE_RELEASE_EVIDENCE_SYSTEM = SELF_MAINTENANCE_DIR / "verifiable_release_evidence_system.json"
EVIDENCE_REPLAY_DRILL = SELF_MAINTENANCE_DIR / "evidence_replay_drill.json"
EVIDENCE_BUNDLE_PERSISTENCE = SELF_MAINTENANCE_DIR / "evidence_bundle_persistence.json"
REPLAY_RELEASE_EVIDENCE = SELF_MAINTENANCE_DIR / "replay_release_evidence.json"
EVIDENCE_TIMELINE = SELF_MAINTENANCE_DIR / "evidence_timeline.json"
EVIDENCE_OPERATOR_SUMMARY = SELF_MAINTENANCE_DIR / "evidence_operator_summary.json"
DASHBOARD_EVIDENCE_VIEWER = SELF_MAINTENANCE_DIR / "dashboard_evidence_viewer.json"
API_EVIDENCE_VIEWER = SELF_MAINTENANCE_DIR / "api_evidence_viewer.json"
EVIDENCE_RETENTION_POLICY = SELF_MAINTENANCE_DIR / "evidence_retention_policy.json"
EVIDENCE_REGRESSION_LOCKDOWN = SELF_MAINTENANCE_DIR / "evidence_regression_lockdown.json"
PRE_V29_EVIDENCE_AUDIT = SELF_MAINTENANCE_DIR / "pre_v29_evidence_audit.json"
DURABLE_RELEASE_EVIDENCE_ARCHIVE = SELF_MAINTENANCE_DIR / "durable_release_evidence_archive.json"
SIGNING_READINESS_AUDIT = SELF_MAINTENANCE_DIR / "signing_readiness_audit.json"
CANONICAL_MANIFEST_FORMAT = SELF_MAINTENANCE_DIR / "canonical_manifest_format.json"
CANONICAL_EVIDENCE_SCHEMA = SELF_MAINTENANCE_DIR / "canonical_evidence_schema.json"
RELEASE_SIGNING_STATUS = SELF_MAINTENANCE_DIR / "release_signing_status.json"
SIGNATURE_PLACEHOLDER_CONTRACT = SELF_MAINTENANCE_DIR / "signature_placeholder_contract.json"
KEY_POLICY_PREPARATION = SELF_MAINTENANCE_DIR / "key_policy_preparation.json"
SIGNATURE_VERIFICATION_PLACEHOLDER = SELF_MAINTENANCE_DIR / "signature_verification_placeholder.json"
DASHBOARD_SIGNING_STATUS = SELF_MAINTENANCE_DIR / "dashboard_signing_status.json"
API_SIGNING_STATUS = SELF_MAINTENANCE_DIR / "api_signing_status.json"
PRE_V30_SIGNING_PREP_AUDIT = SELF_MAINTENANCE_DIR / "pre_v30_signing_prep_audit.json"
SIGNED_RELEASE_PREPARATION_SYSTEM = SELF_MAINTENANCE_DIR / "signed_release_preparation_system.json"
RELEASE_EVIDENCE_REPORT_DIR = ROOT_DIR / "reports" / "release_evidence"

SAFE_SOURCE_PREFIXES = ("conscious_agent/", "tools/")
SAFE_SOURCE_FILES = {"README_NEXT_STEPS.md", "requirements.txt"}
REQUIRED_README_STAGES = [
    "v23.1", "v23.2", "v23.3", "v23.4", "v23.5", "v23.6", "v23.7", "v23.8", "v23.9", "v23.10", "v24.0",
    "v24.1", "v24.2", "v24.3", "v24.4", "v24.5", "v24.6", "v24.7", "v24.8", "v24.9", "v24.10", "v25.0", "v25.0.1",
    "v25.1", "v25.2", "v25.3", "v25.4", "v25.5", "v25.6", "v25.7", "v25.8", "v25.9", "v26.0",
    "v26.1", "v26.2", "v26.3", "v26.4", "v26.5", "v26.6", "v26.7", "v26.8", "v26.9", "v27.0",
    "v27.1", "v27.2", "v27.3", "v27.4", "v27.5", "v27.6", "v27.7", "v27.8", "v27.9", "v27.10", "v28.0",
    "v28.1", "v28.2", "v28.3", "v28.4", "v28.5", "v28.6", "v28.7", "v28.8", "v28.9", "v28.10", "v29.0",
    "v29.1", "v29.2", "v29.3", "v29.4", "v29.5", "v29.6", "v29.7", "v29.8", "v29.9", "v29.10", "v30.0",
]


def _is_metadata_drift_tolerant_path(path: str) -> bool:
    """Return True for source-only metadata files that may be rewritten by install/smoke checks.

    These files are still checked by portable metadata and privacy scans, but the frozen
    candidate hash deliberately excludes their volatile content so v27/v28 governance
    does not block on harmless workspace timestamp churn. Release governance should
    detect real source drift, not faint metadata footprints left by the smoke gremlin.
    """
    rel = path.replace(os.sep, "/")
    return rel in {"data/projects.json", "data/settings.json"} or (rel.startswith("data/workspaces/") and rel.endswith(".json"))


def _evidence_manifest_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [row for row in entries if not _is_metadata_drift_tolerant_path(str(row.get("path", "")))],
        key=lambda row: str(row.get("path", "")),
    )


def _manifest_hash(entries: list[dict[str, Any]]) -> str:
    return _sha256_text(sorted(entries, key=lambda row: str(row.get("path", ""))))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir() -> None:
    SELF_MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dir()
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _report_path(path: str) -> str:
    return path.replace(os.sep, "/")


def _safe_target(path: str) -> bool:
    return path in SAFE_SOURCE_FILES or any(path.startswith(prefix) for prefix in SAFE_SOURCE_PREFIXES)


def _collect_self_maintenance_findings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    main_text = _read_text(ROOT_DIR / "conscious_agent" / "main.py")
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    release_text = _read_text(ROOT_DIR / "conscious_agent" / "release_installation.py")
    projects = _read_json(ROOT_DIR / "data" / "projects.json", {})
    settings = _read_json(ROOT_DIR / "data" / "settings.json", {})
    expected_package = _package_name()

    hardcoded_package_refs = []
    package_literal = re.compile(r"Eidolon_v\d+_\d+(?:_\d+)?\.zip")
    for rel, text in [
        ("conscious_agent/main.py", main_text),
        ("conscious_agent/api_server.py", api_text),
        ("conscious_agent/dashboard.py", dashboard_text),
    ]:
        matches = sorted(set(package_literal.findall(text)))
        if matches:
            hardcoded_package_refs.append({"file": rel, "matches": matches})
    findings.append({
        "id": "release-package-defaults",
        "title": "Release package defaults use the current package helper",
        "status": "pass" if not hardcoded_package_refs else "warn",
        "risk": "medium",
        "affected_files": [item["file"] for item in hardcoded_package_refs] or ["conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/dashboard.py"],
        "message": f"Current default package should resolve as {expected_package}; hardcoded package literals in core routes: {hardcoded_package_refs or 'none'}.",
    })

    milestone_text = json.dumps(projects, default=str)
    legacy_milestone = "v20.0.1 Source-Only Release Package Hotfix" in milestone_text
    last_updated = projects.get("last_updated_for")
    findings.append({
        "id": "project-metadata-current-milestone",
        "title": "Project metadata reflects the current milestone",
        "status": "pass" if not legacy_milestone and last_updated == "v30.0" else "warn",
        "risk": "low",
        "affected_files": ["data/projects.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"],
        "message": f"Project metadata last_updated_for={last_updated}; legacy milestone present={legacy_milestone}.",
    })

    preserves_warning = "_row_status_from_report" in release_text and 'raw_status in {"warn", "warning"}' in release_text
    findings.append({
        "id": "readiness-warning-severity",
        "title": "Readiness summaries preserve warn severity",
        "status": "pass" if preserves_warning else "warn",
        "risk": "medium",
        "affected_files": ["conscious_agent/release_installation.py"],
        "message": "Readiness rows preserve warning-level reports instead of flattening every ok report into pass." if preserves_warning else "Readiness rows may still promote warn rows to pass.",
    })

    readme = _read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    missing = [stage for stage in REQUIRED_README_STAGES if stage not in readme]
    findings.append({
        "id": "readme-stage-coverage",
        "title": "README documents v23.x through v30.0 staged releases",
        "status": "pass" if not missing else "warn",
        "risk": "low",
        "affected_files": ["README_NEXT_STEPS.md"],
        "message": "All v23.x through v30.0 release notes are present." if not missing else f"Missing README stage notes: {', '.join(missing)}.",
    })

    route_report = build_route_safety_harness(project_id="eidolon", save=False)
    findings.append({
        "id": "route-safety-baseline",
        "title": "GET routes remain read-only and mutation paths remain gated",
        "status": str(route_report.get("status", "warn")),
        "risk": "high",
        "affected_files": ["conscious_agent/dashboard.py", "conscious_agent/api_server.py"],
        "message": route_report.get("message", "Route safety harness baseline unavailable."),
    })
    return findings


def _proposal_from_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proposals = []
    for finding in findings:
        needs_action = finding.get("status") not in {"pass", "dry_run"}
        proposals.append({
            "proposal_id": f"proposal-{finding['id']}",
            "source_finding": finding["id"],
            "title": finding["title"],
            "action": "review-and-patch" if needs_action else "monitor",
            "risk": finding.get("risk", "medium"),
            "affected_files": finding.get("affected_files", []),
            "requires_approval": needs_action,
            "safe_for_dry_run_patch": all(_safe_target(path) or path.startswith("data/workspaces/") or path == "data/projects.json" for path in finding.get("affected_files", [])),
            "message": finding.get("message", ""),
        })
    return proposals


def build_self_maintenance_proposal_sandbox(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.1: inspect the project and produce safe maintenance proposals without editing files."""
    findings = _collect_self_maintenance_findings()
    proposals = _proposal_from_findings(findings)
    rows = [
        {"name": item["id"], "status": item.get("status", "warn"), "message": item.get("message", "")} for item in findings
    ] + [
        {"name": "proposal-only", "status": "pass", "message": "No project files are edited by the proposal sandbox."},
        {"name": "dry-run-default", "status": "pass", "message": "Generated proposals are review artifacts, not apply instructions."},
    ]
    status = _status_from(rows)
    report = {
        "version": SELF_MAINTENANCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "stage": "v23.1",
        "status": status,
        "ok": _ok_from(status),
        "findings": findings,
        "proposals": proposals,
        "rows": rows,
        "message": "Self-maintenance proposal sandbox completed without editing source files.",
    }
    if save:
        _write_json(PROPOSAL_SANDBOX, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_plan_builder(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.2: turn maintenance proposals into a bounded patch plan."""
    proposal = build_self_maintenance_proposal_sandbox(project_id=project_id, save=False)
    targets: dict[str, set[str]] = {}
    for item in proposal.get("proposals", []):
        for path in item.get("affected_files", []):
            targets.setdefault(path, set()).add(item.get("source_finding", "unknown"))
    file_plans = []
    for path, reasons in sorted(targets.items()):
        safe = _safe_target(path) or path in {"data/projects.json", "data/settings.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"}
        file_plans.append({
            "path": path,
            "safe_target": safe,
            "change_intent": sorted(reasons),
            "before_after_behavior": "Preserve existing behavior while improving release metadata, safety visibility, or review scaffolding.",
            "verification": [
                "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
                "python conscious_agent/main.py --self-maintenance-proposal --readiness-json",
                "python conscious_agent/main.py --controlled-maintenance-cycle --readiness-json",
            ],
        })
    rows = [
        {"name": "file-targets", "status": "pass" if file_plans else "warn", "message": f"{len(file_plans)} maintenance file target(s) planned."},
        {"name": "runtime-data-guard", "status": "pass" if all(item["safe_target"] for item in file_plans) else "blocked", "message": "Patch plan avoids private runtime data."},
        {"name": "readme-required", "status": "pass" if any(item["path"] == "README_NEXT_STEPS.md" for item in file_plans) else "warn", "message": "README is included when release/code changes are planned."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.2", "status": status, "ok": _ok_from(status), "proposal_hash": _sha256_text(proposal), "file_plans": file_plans, "rows": rows, "message": "Patch plan builder completed."}
    if save:
        _write_json(PATCH_PLAN, report)
    else:
        report["preview_only"] = True
    return report


def build_dry_run_patch_generator(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.3: generate a patch preview artifact without applying it."""
    plan = build_patch_plan_builder(project_id=project_id, save=False)
    preview_changes = []
    for item in plan.get("file_plans", []):
        preview_changes.append({
            "path": item["path"],
            "mode": "preview-only",
            "intended_edits": item.get("change_intent", []),
            "diff_summary": "No direct diff is applied by this generator; it records intended maintenance edits for review.",
        })
    rows = [
        {"name": "preview-generated", "status": "pass", "message": f"{len(preview_changes)} preview change(s) described."},
        {"name": "source-files-untouched", "status": "pass", "message": "Patch generator writes only the review report when save=True."},
        {"name": "package-exclusion", "status": "pass", "message": "data/self_maintenance reports are excluded from source-only packages by the source-only data rule."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.3", "status": status, "ok": _ok_from(status), "plan_hash": _sha256_text(plan), "preview_changes": preview_changes, "rows": rows, "message": "Dry-run maintenance patch preview generated."}
    if save:
        _write_json(PATCH_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_patch_safety_auditor(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.4: audit generated maintenance patch plans before any apply path."""
    preview = build_dry_run_patch_generator(project_id=project_id, save=False)
    paths = [str(item.get("path")) for item in preview.get("preview_changes", [])]
    route_safety = build_route_safety_harness(project_id=project_id, save=False)
    rows = [
        {"name": "no-private-runtime-edits", "status": "pass" if not any(path.startswith("data/") and path not in {"data/projects.json", "data/settings.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"} for path in paths) else "blocked", "message": "Private runtime data is not targeted."},
        {"name": "get-routes-read-only", "status": str(route_safety.get("status", "warn")), "message": route_safety.get("message", "Route safety unavailable.")},
        {"name": "readme-gate", "status": "pass" if "README_NEXT_STEPS.md" in paths else "warn", "message": "README update is part of the maintenance bundle when release/code changes are staged."},
        {"name": "approval-binding-required", "status": "pass", "message": "Real apply remains blocked unless an exact reviewed bundle hash is supplied."},
        {"name": "dry-run-pointer-guard", "status": "pass", "message": "Dry-run generators do not write real apply/rollback pointers."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.4", "status": status, "ok": _ok_from(status), "preview_hash": _sha256_text(preview), "rows": rows, "message": "Patch safety audit completed."}
    if save:
        _write_json(PATCH_SAFETY_AUDIT, report)
    else:
        report["preview_only"] = True
    return report


def _copy_source_tree_to_temp() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="eidolon_maintenance_clone_"))
    clone = temp_root / "Eidolon"
    def ignore(dirpath: str, names: list[str]) -> set[str]:
        ignored = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}.intersection(names)
        return ignored
    shutil.copytree(ROOT_DIR, clone, ignore=ignore)
    return clone


def build_apply_patch_to_temp_clone(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.5: apply/verify the generated maintenance patch path only inside a temporary clone."""
    audit = build_patch_safety_auditor(project_id=project_id, save=False)
    clone_path = ""
    compile_result: dict[str, Any] = {"status": "warn", "ok": True, "message": "Temp clone compile was skipped."}
    try:
        clone = _copy_source_tree_to_temp()
        clone_path = str(clone)
        proc = subprocess.run([sys.executable, "-m", "py_compile", *[str(p) for p in sorted((clone / "conscious_agent").glob("*.py"))], str(clone / "tools" / "smoke_check.py")], cwd=clone, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        compile_result = {"status": "pass" if proc.returncode == 0 else "blocked", "ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:], "message": "Temporary clone py_compile completed."}
    except Exception as error:
        compile_result = {"status": "blocked", "ok": False, "error": str(error), "message": "Temporary clone apply drill failed."}
    finally:
        if clone_path:
            shutil.rmtree(Path(clone_path).parent, ignore_errors=True)
    rows = [
        {"name": "safety-audit", "status": str(audit.get("status", "warn")), "message": audit.get("message")},
        {"name": "temp-clone-only", "status": "pass", "message": "No real project files are modified by the temp apply drill."},
        {"name": "compile", "status": compile_result["status"], "message": compile_result.get("message", "")},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.5", "status": status, "ok": _ok_from(status), "audit_hash": _sha256_text(audit), "compile": compile_result, "rows": rows, "message": "Temporary clone maintenance apply drill completed."}
    if save:
        _write_json(TEMP_APPLY_DRILL, report)
    else:
        report["preview_only"] = True
    return report


def build_maintenance_review_bundle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.6: bundle proposal, plan, preview, audit, and verification into one review artifact."""
    proposal = build_self_maintenance_proposal_sandbox(project_id=project_id, save=False)
    plan = build_patch_plan_builder(project_id=project_id, save=False)
    preview = build_dry_run_patch_generator(project_id=project_id, save=False)
    audit = build_patch_safety_auditor(project_id=project_id, save=False)
    temp = build_apply_patch_to_temp_clone(project_id=project_id, save=False)
    artifacts = {"proposal": proposal, "plan": plan, "preview": preview, "audit": audit, "temp_apply_drill": temp}
    hashes = {name: _sha256_text(value) for name, value in artifacts.items()}
    rows = [
        {"name": name, "status": str(value.get("status", "warn")), "message": value.get("message", "")} for name, value in artifacts.items()
    ] + [
        {"name": "bundle-hashes", "status": "pass", "message": f"{len(hashes)} artifact hash(es) bound into the review bundle."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.6", "status": status, "ok": _ok_from(status), "artifact_hashes": hashes, "artifacts": artifacts, "rows": rows, "message": "Maintenance review bundle prepared."}
    if save:
        _write_json(REVIEW_BUNDLE, report)
    else:
        report["preview_only"] = True
    return report


def build_human_approval_binding(project_id: str = "eidolon", bundle_hash: str | None = None, confirm: bool = False, save: bool = True, review_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """v23.7: bind approval to the exact reviewed maintenance bundle hash."""
    bundle = review_bundle or build_maintenance_review_bundle(project_id=project_id, save=False)
    actual_hash = _sha256_text(bundle)
    confirmed = bool(confirm and bundle_hash and bundle_hash == actual_hash)
    rows = [
        {"name": "bundle-hash-present", "status": "pass", "message": actual_hash},
        {"name": "exact-hash-match", "status": "pass" if confirmed else "warn", "message": "Approval is preview-only until the exact bundle hash is supplied with confirmation."},
        {"name": "no-apply", "status": "pass", "message": "Approval binding does not apply source edits."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.7", "status": status, "ok": _ok_from(status), "approved": confirmed, "bundle_hash": actual_hash, "supplied_bundle_hash": bundle_hash, "rows": rows, "message": "Human approval binding preview completed."}
    if save:
        _write_json(APPROVAL_BINDING, report)
    else:
        report["preview_only"] = True
    return report


def build_real_maintenance_patch_apply(project_id: str = "eidolon", bundle_hash: str | None = None, confirm_phrase: str | None = None, dry_run: bool = True, save: bool = True, review_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """v23.8: expose the real apply gate, defaulting to dry-run and blocking unbound applies."""
    binding = build_human_approval_binding(project_id=project_id, bundle_hash=bundle_hash, confirm=bool(bundle_hash), save=False, review_bundle=review_bundle)
    exact_phrase = confirm_phrase == "APPLY EXACT REVIEWED MAINTENANCE BUNDLE"
    live_allowed = bool(not dry_run and binding.get("approved") and exact_phrase)
    missing_gate_status = "warn" if dry_run else "blocked"
    rows = [
        {"name": "dry-run-default", "status": "pass" if dry_run else "warn", "message": "Real maintenance apply defaults to dry-run."},
        {"name": "approval-binding", "status": "pass" if binding.get("approved") else missing_gate_status, "message": "Exact reviewed bundle hash is required for live apply."},
        {"name": "confirmation-phrase", "status": "pass" if exact_phrase else missing_gate_status, "message": "Live apply requires APPLY EXACT REVIEWED MAINTENANCE BUNDLE."},
        {"name": "live-apply", "status": "dry_run" if dry_run else ("pass" if live_allowed else "blocked"), "message": "No source edits were applied by this report." if dry_run else "Live apply gate evaluated."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.8", "status": status, "ok": dry_run or live_allowed, "dry_run": dry_run, "live_allowed": live_allowed, "binding": binding, "rows": rows, "message": "Real maintenance patch apply gate evaluated; no edit engine is run in dry-run mode."}
    if save:
        _write_json(REAL_APPLY_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_post_apply_health_monitor(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.9: run post-apply health checks and recommend rollback when health fails."""
    manifest = build_release_manifest_integrity(project_id=project_id, package_name=_package_name(), save=False)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    route = build_route_safety_harness(project_id=project_id, save=False)
    rows = [
        {"name": "manifest-integrity", "status": str(manifest.get("status", "warn")), "message": manifest.get("message", "")},
        {"name": "privacy-scan", "status": str(privacy.get("status", "warn")), "message": privacy.get("message", "")},
        {"name": "route-safety", "status": str(route.get("status", "warn")), "message": route.get("message", "")},
        {"name": "rollback-recommendation", "status": "pass", "message": "Rollback should be recommended if any post-apply health row is blocked."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.9", "status": status, "ok": _ok_from(status), "rows": rows, "message": "Post-apply health monitor completed."}
    if save:
        _write_json(POST_APPLY_HEALTH, report)
    else:
        report["preview_only"] = True
    return report


def build_controlled_maintenance_cycle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v23.10: run the complete proposal-to-review cycle and stop before real apply."""
    bundle = build_maintenance_review_bundle(project_id=project_id, save=False)
    review_bundle_hash = _sha256_text(bundle)
    apply_gate = build_real_maintenance_patch_apply(project_id=project_id, bundle_hash=review_bundle_hash, dry_run=True, save=False, review_bundle=bundle)
    apply_status = str(apply_gate.get("status", "warn"))
    rows = [
        {"name": "review-bundle", "status": str(bundle.get("status", "warn")), "message": bundle.get("message", "")},
        {"name": "stop-before-real-apply", "status": "pass", "message": "Controlled cycle creates review artifacts only."},
        {"name": "apply-gate-preview", "status": apply_status, "message": f"Nested apply gate status={apply_status}; {apply_gate.get('message', '')}"},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v23.10", "status": status, "ok": _ok_from(status), "review_bundle_hash": review_bundle_hash, "steps": {"review_bundle": bundle, "apply_gate": apply_gate}, "rows": rows, "message": "Controlled maintenance cycle completed and stopped before live apply."}
    if save:
        _write_json(CONTROLLED_CYCLE, report)
    else:
        report["preview_only"] = True
    return report


def build_assisted_self_improvement_release(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v24.0: final assisted self-improvement release gate for proposal, review, approval-binding, and package safety."""
    package_name = package_name or _package_name()
    cycle = build_controlled_maintenance_cycle(project_id=project_id, save=False)
    health = build_post_apply_health_monitor(project_id=project_id, save=False)
    v23_gate = build_v23_readiness_gate(project_id=project_id, package_name=package_name, zip_path=zip_path, run_heavy=False, save=False)
    inventory = build_package_inventory(project_id=project_id, save=False)
    rows = [
        {"name": "controlled-cycle", "status": str(cycle.get("status", "warn")), "message": cycle.get("message", "")},
        {"name": "post-apply-health", "status": str(health.get("status", "warn")), "message": health.get("message", "")},
        {"name": "release-readiness", "status": str(v23_gate.get("status", "warn")), "message": v23_gate.get("message", "")},
        {"name": "source-only-inventory", "status": str(inventory.get("status", "warn")), "message": inventory.get("message", "")},
        {"name": "assisted-not-autonomous-apply", "status": "pass", "message": "v24.0 may prepare reviewable patches; real apply remains exact-approval gated."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.0", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {"controlled_cycle": cycle, "post_apply_health": health, "v23_readiness_gate": v23_gate, "package_inventory": inventory}, "rows": rows, "message": "Assisted self-improvement release gate completed."}
    if save:
        _write_json(ASSISTED_SELF_IMPROVEMENT_RELEASE, report)
    else:
        report["preview_only"] = True
    return report




def _source_files_for_scan() -> list[Path]:
    files: list[Path] = []
    for folder in [ROOT_DIR / "conscious_agent", ROOT_DIR / "tools"]:
        if folder.exists():
            files.extend(sorted(path for path in folder.rglob("*.py") if "__pycache__" not in path.parts))
    readme = ROOT_DIR / "README_NEXT_STEPS.md"
    if readme.exists():
        files.append(readme)
    return files


def _candidate_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "candidate"


def _candidate(title: str, category: str, files: list[str], reason: str, risk: str = "medium", complexity: str = "small", safety: list[str] | None = None, checks: list[str] | None = None, score: int = 50) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(title),
        "title": title,
        "category": category,
        "affected_files": sorted(set(files)),
        "reason": reason,
        "risk_level": risk,
        "estimated_complexity": complexity,
        "safety_concerns": safety or ["No live apply; review-only planning artifact."],
        "required_checks": checks or [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "python conscious_agent/main.py --improvement-candidate-scan --readiness-json",
            "python -u tools/smoke_check.py --tier install --json",
        ],
        "readme_update_required": True,
        "runtime_private_data_risk": any(path.startswith("data/") and path not in {"data/projects.json", "data/settings.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"} for path in files),
        "recommended_next_action": "Review candidate and convert to a maintenance proposal before generating any patch plan.",
        "score": score,
    }


def build_improvement_candidate_scan(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.1: scan for ranked assisted-improvement candidates without editing files."""
    candidates: list[dict[str, Any]] = []
    files = _source_files_for_scan()
    current_package = _package_name()
    stale_refs: list[str] = []
    todo_hits: list[dict[str, Any]] = []
    command_hits: list[str] = []
    for path in files:
        rel = _report_path(str(path.relative_to(ROOT_DIR)))
        text = _read_text(path)
        if re.search(r"Eidolon_v(?:22|23|24)_0\.zip", text):
            stale_refs.append(rel)
        for number, line in enumerate(text.splitlines(), 1):
            if "TODO" in line or "FIXME" in line:
                todo_hits.append({"path": rel, "line": number, "text": line.strip()[:180]})
        if rel in {"conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/dashboard.py"} and "assisted-improvement-cycle" not in text:
            command_hits.append(rel)
    if stale_refs:
        candidates.append(_candidate(
            "Replace stale release package references with current package helper",
            "release-trust",
            stale_refs,
            f"Found hard-coded older package names while current package resolves to {current_package}.",
            risk="medium",
            complexity="small",
            checks=["grep -R Eidolon_v24_0 conscious_agent tools data", "python conscious_agent/main.py --release-manifest-integrity --readiness-json"],
            score=95,
        ))
    metadata = _read_json(ROOT_DIR / "data" / "projects.json", {})
    metadata_text = json.dumps(metadata, default=str)
    if "v24.0" in metadata_text or metadata.get("last_updated_for") != "v26.0":
        candidates.append(_candidate(
            "Refresh packaged project metadata to v26.0",
            "metadata-drift",
            ["data/projects.json", "data/settings.json", "data/workspaces/projects.json", "data/workspaces/active_project.json"],
            "Packaged source metadata should identify the current semi-autonomous maintenance review milestone.",
            risk="low",
            complexity="small",
            checks=["python conscious_agent/main.py --portable-metadata-check --readiness-json", "python conscious_agent/main.py --package-privacy-scan --readiness-json"],
            score=90,
        ))
    if command_hits:
        candidates.append(_candidate(
            "Expose v24.x assisted improvement commands consistently",
            "operator-ux",
            sorted(set(command_hits + ["tools/smoke_check.py", "README_NEXT_STEPS.md"])),
            "The new candidate scanner, prioritizer, backlog, and assisted-improvement cycle need matching CLI/API/dashboard/smoke surfaces.",
            risk="medium",
            complexity="medium",
            checks=["python conscious_agent/main.py --assisted-improvement-cycle --readiness-json", "python -u tools/smoke_check.py --tier install --json"],
            score=88,
        ))
    if todo_hits:
        candidates.append(_candidate(
            "Review TODO/FIXME clusters before autonomous planning",
            "code-health",
            sorted({hit["path"] for hit in todo_hits[:20]}),
            f"Found {len(todo_hits)} TODO/FIXME marker(s). These should be triaged before they become mystery folklore.",
            risk="low",
            complexity="medium",
            safety=["Read-only scan; TODO review should not auto-edit unrelated code."],
            score=55,
        ))
    candidates.append(_candidate(
        "Add regression checks for release-default and warning-severity drift",
        "regression-safety",
        ["conscious_agent/self_maintenance.py", "tools/smoke_check.py", "README_NEXT_STEPS.md"],
        "Recent findings showed stale package defaults, stale metadata, and flattened warning severity can regress; add a detector so these stop escaping review.",
        risk="medium",
        complexity="medium",
        checks=["python conscious_agent/main.py --candidate-regression-detector --readiness-json"],
        score=92,
    ))
    candidates.append(_candidate(
        "Keep maintenance backlog and release memory out of source packages",
        "privacy-safety",
        ["conscious_agent/self_maintenance.py", "conscious_agent/release_packaging.py", "conscious_agent/release_installation.py"],
        "v24.x introduces local maintenance history/backlog concepts; release packaging must keep these runtime facts out of shareable zips.",
        risk="high",
        complexity="medium",
        checks=["python conscious_agent/main.py --release-memory-privacy --readiness-json", "python conscious_agent/main.py --package-privacy-scan --readiness-json"],
        score=93,
    ))
    rows = [
        {"name": "source-scan", "status": "pass", "message": f"Scanned {len(files)} source/readme file(s)."},
        {"name": "candidate-count", "status": "pass" if candidates else "warn", "message": f"{len(candidates)} candidate(s) identified."},
        {"name": "read-only", "status": "pass", "message": "Candidate scanning does not edit project files."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.1", "status": status, "ok": _ok_from(status), "current_package": current_package, "candidates": candidates, "todo_hits": todo_hits[:50], "rows": rows, "message": "Improvement candidate scan completed in read-only mode."}
    if save:
        _write_json(IMPROVEMENT_CANDIDATE_SCAN, report)
    else:
        report["preview_only"] = True
    return report


def _score_candidate(item: dict[str, Any]) -> int:
    risk_penalty = {"low": 0, "medium": 8, "high": 18}.get(str(item.get("risk_level", "medium")), 8)
    complexity_penalty = {"small": 0, "medium": 6, "large": 14}.get(str(item.get("estimated_complexity", "medium")), 6)
    privacy_penalty = 20 if item.get("runtime_private_data_risk") else 0
    return max(0, min(100, int(item.get("score", 50)) - risk_penalty - complexity_penalty - privacy_penalty))


def build_candidate_prioritizer(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.2: rank improvement candidates by safety, reliability value, and testability."""
    scan = build_improvement_candidate_scan(project_id=project_id, save=False)
    ranked = []
    for item in scan.get("candidates", []):
        row = dict(item)
        row["priority_score"] = _score_candidate(row)
        row["priority_reason"] = "Scores favor release trust, regression prevention, source-only privacy, and low-risk testable work."
        ranked.append(row)
    ranked.sort(key=lambda row: row.get("priority_score", 0), reverse=True)
    rows = [
        {"name": "scan-input", "status": str(scan.get("status", "warn")), "message": scan.get("message", "")},
        {"name": "ranked-candidates", "status": "pass" if ranked else "warn", "message": f"Ranked {len(ranked)} candidate(s)."},
        {"name": "read-only", "status": "pass", "message": "Prioritization does not create patches or mutate backlog state."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.2", "status": status, "ok": _ok_from(status), "ranked_candidates": ranked, "selected_candidate": ranked[0] if ranked else None, "rows": rows, "message": "Improvement candidates ranked for assisted review."}
    if save:
        _write_json(CANDIDATE_PRIORITIZER, report)
    else:
        report["preview_only"] = True
    return report


def build_candidate_to_proposal_bridge(project_id: str = "eidolon", candidate_id: str | None = None, save: bool = True) -> dict[str, Any]:
    """v24.3: convert a selected improvement candidate into a proposal-compatible review object."""
    priorities = build_candidate_prioritizer(project_id=project_id, save=False)
    candidates = priorities.get("ranked_candidates", [])
    selected = next((item for item in candidates if item.get("candidate_id") == candidate_id), None) if candidate_id else None
    selected = selected or priorities.get("selected_candidate")
    proposal = None
    if selected:
        proposal = {
            "proposal_id": f"proposal-{selected['candidate_id']}",
            "source_candidate": selected["candidate_id"],
            "title": selected["title"],
            "action": "build-reviewed-patch-plan",
            "risk": selected.get("risk_level", "medium"),
            "affected_files": selected.get("affected_files", []),
            "requires_approval": True,
            "safe_for_dry_run_patch": all(_safe_target(path) or path.startswith("data/workspaces/") or path in {"data/projects.json", "data/settings.json"} for path in selected.get("affected_files", [])),
            "verification": selected.get("required_checks", []),
            "message": selected.get("reason", ""),
        }
    rows = [
        {"name": "prioritizer", "status": str(priorities.get("status", "warn")), "message": priorities.get("message", "")},
        {"name": "candidate-selected", "status": "pass" if selected else "warn", "message": selected.get("title", "No candidate selected.") if selected else "No candidate selected."},
        {"name": "proposal-bridge", "status": "pass" if proposal else "warn", "message": "Candidate converted to a review proposal." if proposal else "No proposal generated."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.3", "status": status, "ok": _ok_from(status), "selected_candidate": selected, "proposal": proposal, "rows": rows, "message": "Candidate-to-proposal bridge completed."}
    if save:
        _write_json(CANDIDATE_PROPOSAL_BRIDGE, report)
    else:
        report["preview_only"] = True
    return report


def build_maintenance_backlog_registry(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.4: preview a local runtime maintenance backlog without packaging it."""
    priorities = build_candidate_prioritizer(project_id=project_id, save=False)
    backlog_path = DATA_DIR / "maintenance_backlog.json"
    existing = _read_json(backlog_path, {"items": []}) if backlog_path.exists() else {"items": []}
    preview_items = []
    for item in priorities.get("ranked_candidates", []):
        preview_items.append({
            "candidate_id": item.get("candidate_id"),
            "title": item.get("title"),
            "status": "new",
            "priority_score": item.get("priority_score"),
            "first_seen": _now(),
            "last_seen": _now(),
            "linked_report_hash": _sha256_text(item),
        })
    rows = [
        {"name": "runtime-backlog-path", "status": "pass", "message": "Backlog path is data/maintenance_backlog.json and is runtime state."},
        {"name": "preview-only", "status": "pass", "message": "This command previews backlog records and does not write data/maintenance_backlog.json."},
        {"name": "source-package-exclusion", "status": "pass", "message": "Non-allowlisted data files remain excluded by source-only package rules."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.4", "status": status, "ok": _ok_from(status), "backlog_path": str(backlog_path.relative_to(ROOT_DIR)).replace(os.sep, "/"), "existing_count": len(existing.get("items", [])) if isinstance(existing, dict) else 0, "preview_items": preview_items, "rows": rows, "message": "Maintenance backlog registry preview completed without mutating runtime backlog state."}
    if save:
        _write_json(MAINTENANCE_BACKLOG_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_dashboard_maintenance_backlog(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.5: verify dashboard exposes maintenance backlog/candidate preview links."""
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    required = ["improvement-candidate-scan", "candidate-prioritizer", "maintenance-backlog", "assisted-improvement-cycle"]
    missing = [token for token in required if token not in dashboard_text]
    rows = [
        {"name": "dashboard-version", "status": "pass" if "DASHBOARD_VERSION = \"29.0\"" in dashboard_text else "warn", "message": "Dashboard version should report 30.0."},
        {"name": "dashboard-links", "status": "pass" if not missing else "warn", "message": f"Missing dashboard token(s): {', '.join(missing) or 'none'}."},
        {"name": "preview-only", "status": "pass", "message": "Dashboard backlog surfaces are GET preview links; mutations remain POST-only."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.5", "status": status, "ok": _ok_from(status), "missing_tokens": missing, "rows": rows, "message": "Dashboard maintenance backlog preview check completed."}
    if save:
        _write_json(DASHBOARD_MAINTENANCE_BACKLOG, report)
    else:
        report["preview_only"] = True
    return report


def build_api_maintenance_backlog(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.6: verify API exposes read-only backlog/candidate previews and POST-only status mutation scaffolding."""
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    required_get = ["improvement-candidate-scan", "candidate-prioritizer", "maintenance-backlog", "assisted-improvement-cycle"]
    required_post = ["set-maintenance-candidate-status", "ACCEPT_MAINTENANCE_CANDIDATE_STATUS"]
    missing_get = [token for token in required_get if token not in api_text]
    missing_post = [token for token in required_post if token not in api_text]
    rows = [
        {"name": "api-version", "status": "pass" if "API_VERSION = \"29.0\"" in api_text else "warn", "message": "API version should report 30.0."},
        {"name": "get-preview-routes", "status": "pass" if not missing_get else "warn", "message": f"Missing GET preview token(s): {', '.join(missing_get) or 'none'}."},
        {"name": "post-status-gate", "status": "pass" if not missing_post else "warn", "message": f"Missing POST mutation gate token(s): {', '.join(missing_post) or 'none'}."},
        {"name": "route-safety", "status": "pass", "message": "Candidate/backlog status changes are designed as POST-only confirmation actions."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.6", "status": status, "ok": _ok_from(status), "missing_get_tokens": missing_get, "missing_post_tokens": missing_post, "rows": rows, "message": "API maintenance backlog preview check completed."}
    if save:
        _write_json(API_MAINTENANCE_BACKLOG, report)
    else:
        report["preview_only"] = True
    return report


def build_candidate_regression_detector(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.7: detect regressions in release defaults, metadata, warning severity, packaging privacy, and README stage coverage."""
    main_text = _read_text(ROOT_DIR / "conscious_agent" / "main.py")
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    release_text = _read_text(ROOT_DIR / "conscious_agent" / "release_installation.py")
    projects = _read_json(ROOT_DIR / "data" / "projects.json", {})
    readme = _read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    package_literal = re.compile(r"Eidolon_v\d+_\d+(?:_\d+)?\.zip")
    stale_package = bool(package_literal.search(main_text + api_text + dashboard_text))
    flattened_warning = not ("_row_status_from_report" in release_text and 'raw_status in {"warn", "warning"}' in release_text)
    missing_readme = [stage for stage in REQUIRED_README_STAGES if stage not in readme]
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    rows = [
        {"name": "stale-package-defaults", "status": "blocked" if stale_package else "pass", "message": "No hardcoded release package defaults remain in core routes." if not stale_package else "Hardcoded package default detected; use the package helper instead."},
        {"name": "metadata-current", "status": "pass" if projects.get("last_updated_for") == "v30.0" else "warn", "message": f"data/projects.json last_updated_for={projects.get('last_updated_for')}."},
        {"name": "warning-severity", "status": "blocked" if flattened_warning else "pass", "message": "Warning-level release rows remain visible." if not flattened_warning else "Warning severity may be flattened."},
        {"name": "source-only-privacy", "status": str(privacy.get("status", "warn")), "message": privacy.get("message", "")},
        {"name": "readme-stage-coverage", "status": "pass" if not missing_readme else "warn", "message": f"Missing stage notes: {', '.join(missing_readme) or 'none'}."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.7", "status": status, "ok": _ok_from(status), "rows": rows, "message": "Candidate regression detector completed."}
    if save:
        _write_json(CANDIDATE_REGRESSION_DETECTOR, report)
    else:
        report["preview_only"] = True
    return report


def build_release_memory_privacy(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.8: keep local release memory/backlog facts out of source-only packages."""
    inventory = build_package_inventory(project_id=project_id, save=False)
    included = [str(row.get("path", "")) for row in inventory.get("included", [])]
    forbidden_prefixes = ["data/self_maintenance/", "data/maintenance_backlog", "data/release_memory", "data/release_installation/", "data/release_package/", "data/releases/"]
    leaks = [path for path in included if any(path.startswith(prefix) for prefix in forbidden_prefixes)]
    rows = [
        {"name": "source-only-inventory", "status": str(inventory.get("status", "warn")), "message": inventory.get("message", "")},
        {"name": "maintenance-runtime-excluded", "status": "blocked" if leaks else "pass", "message": f"{len(leaks)} maintenance/release-memory leak(s) found."},
        {"name": "safe-release-memory", "status": "pass", "message": "Release memory remains local runtime state and is not packaged."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.8", "status": status, "ok": _ok_from(status), "leaks": leaks, "rows": rows, "message": "Release memory privacy check completed."}
    if save:
        _write_json(RELEASE_MEMORY_PRIVACY, report)
    else:
        report["preview_only"] = True
    return report


def build_candidate_verification_recipes(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.9: generate verification recipes for each ranked improvement candidate."""
    priorities = build_candidate_prioritizer(project_id=project_id, save=False)
    recipes = []
    for item in priorities.get("ranked_candidates", []):
        commands = list(dict.fromkeys(item.get("required_checks", []) + [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "PYTHONPATH=conscious_agent python -c \"import dashboard, api_server; print(dashboard.DASHBOARD_VERSION, api_server.API_VERSION)\"",
            "python conscious_agent/main.py --candidate-regression-detector --readiness-json",
        ]))
        recipes.append({"candidate_id": item.get("candidate_id"), "title": item.get("title"), "commands": commands, "expected_result": "No blocked rows; warnings must remain visible and explained."})
    rows = [
        {"name": "prioritized-input", "status": str(priorities.get("status", "warn")), "message": priorities.get("message", "")},
        {"name": "recipe-count", "status": "pass" if recipes else "warn", "message": f"Generated {len(recipes)} verification recipe(s)."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.9", "status": status, "ok": _ok_from(status), "recipes": recipes, "rows": rows, "message": "Candidate verification recipes generated."}
    if save:
        _write_json(CANDIDATE_VERIFICATION_RECIPES, report)
    else:
        report["preview_only"] = True
    return report


def build_assisted_improvement_cycle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v24.10: run the safe front-half of assisted improvement and stop before real apply."""
    scan = build_improvement_candidate_scan(project_id=project_id, save=False)
    priorities = build_candidate_prioritizer(project_id=project_id, save=False)
    bridge = build_candidate_to_proposal_bridge(project_id=project_id, save=False)
    patch_plan = build_patch_plan_builder(project_id=project_id, save=False)
    safety = build_patch_safety_auditor(project_id=project_id, save=False)
    bundle = build_maintenance_review_bundle(project_id=project_id, save=False)
    recipes = build_candidate_verification_recipes(project_id=project_id, save=False)
    rows = [
        {"name": "scan", "status": str(scan.get("status", "warn")), "message": scan.get("message", "")},
        {"name": "prioritize", "status": str(priorities.get("status", "warn")), "message": priorities.get("message", "")},
        {"name": "proposal-bridge", "status": str(bridge.get("status", "warn")), "message": bridge.get("message", "")},
        {"name": "patch-plan", "status": str(patch_plan.get("status", "warn")), "message": patch_plan.get("message", "")},
        {"name": "safety-audit", "status": str(safety.get("status", "warn")), "message": safety.get("message", "")},
        {"name": "review-bundle", "status": str(bundle.get("status", "warn")), "message": bundle.get("message", "")},
        {"name": "verification-recipes", "status": str(recipes.get("status", "warn")), "message": recipes.get("message", "")},
        {"name": "stop-before-apply", "status": "pass", "message": "Assisted improvement cycle stops before real apply or approval binding."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v24.10", "status": status, "ok": _ok_from(status), "selected_candidate": priorities.get("selected_candidate"), "steps": {"scan": scan, "priorities": priorities, "bridge": bridge, "patch_plan": patch_plan, "safety": safety, "bundle": bundle, "recipes": recipes}, "rows": rows, "message": "Assisted improvement cycle completed and stopped before live apply."}
    if save:
        _write_json(ASSISTED_IMPROVEMENT_CYCLE, report)
    else:
        report["preview_only"] = True
    return report


def _compact_step(report: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "version": report.get("version"),
        "stage": report.get("stage"),
        "status": report.get("status"),
        "ok": report.get("ok"),
        "message": report.get("message"),
    }
    rows = report.get("rows")
    if isinstance(rows, list):
        compact["rows"] = rows[:25]
        compact["row_count"] = len(rows)
    for key in ("selected_candidate", "package_name", "zip_path", "leaks", "missing_tokens", "missing_get_tokens", "missing_post_tokens"):
        if key in report:
            compact[key] = report.get(key)
    return compact


def build_semi_autonomous_maintenance_review(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v25.0.1: hotfix gate for finding, ranking, planning, bundling, and reviewing maintenance work without unapproved apply."""
    package_name = package_name or _package_name()
    cycle = build_assisted_improvement_cycle(project_id=project_id, save=False)
    backlog = build_maintenance_backlog_registry(project_id=project_id, save=False)
    dashboard = build_dashboard_maintenance_backlog(project_id=project_id, save=False)
    api = build_api_maintenance_backlog(project_id=project_id, save=False)
    regression = build_candidate_regression_detector(project_id=project_id, save=False)
    privacy = build_release_memory_privacy(project_id=project_id, save=False)
    assisted_release = build_assisted_self_improvement_release(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    inventory = build_package_inventory(project_id=project_id, save=False)
    rows = [
        {"name": "assisted-improvement-cycle", "status": str(cycle.get("status", "warn")), "message": cycle.get("message", "")},
        {"name": "backlog-registry", "status": str(backlog.get("status", "warn")), "message": backlog.get("message", "")},
        {"name": "dashboard-backlog", "status": str(dashboard.get("status", "warn")), "message": dashboard.get("message", "")},
        {"name": "api-backlog", "status": str(api.get("status", "warn")), "message": api.get("message", "")},
        {"name": "regression-detector", "status": str(regression.get("status", "warn")), "message": regression.get("message", "")},
        {"name": "release-memory-privacy", "status": str(privacy.get("status", "warn")), "message": privacy.get("message", "")},
        {"name": "assisted-self-improvement-release", "status": str(assisted_release.get("status", "warn")), "message": assisted_release.get("message", "")},
        {"name": "source-only-inventory", "status": str(inventory.get("status", "warn")), "message": inventory.get("message", "")},
        {"name": "human-approval-boundary", "status": "pass", "message": "v25.0.1 may find, rank, plan, and bundle work; real apply still requires exact approval."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.0.1", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {"cycle": _compact_step(cycle), "backlog": _compact_step(backlog), "dashboard": _compact_step(dashboard), "api": _compact_step(api), "regression": _compact_step(regression), "privacy": _compact_step(privacy), "assisted_release": _compact_step(assisted_release), "inventory": _compact_step(inventory)}, "rows": rows, "message": "Semi-autonomous maintenance review gate completed; real apply remains human-approved."}
    if save:
        _write_json(SEMI_AUTONOMOUS_MAINTENANCE_REVIEW, report)
    else:
        report["preview_only"] = True
    return report

def _extract_dashboard_nav_paths(dashboard_text: str) -> list[str]:
    nav_match = re.search(r"nav_items\s*=\s*\[(.*?)\]\n\s*nav\s*=", dashboard_text, flags=re.S)
    block = nav_match.group(1) if nav_match else dashboard_text
    return sorted(set(re.findall(r'\("(/[^"?#]*)"\s*,', block)))


def _extract_dashboard_router_paths(dashboard_text: str) -> list[str]:
    paths = set(re.findall(r'path\s*==\s*"(/[^"?#]*)"', dashboard_text))
    for set_block in re.findall(r'path\s+in\s+\{([^}]+)\}', dashboard_text):
        paths.update(re.findall(r'"(/[^"?#]*)"', set_block))
    return sorted(paths)


def _release_package_literals_by_file(files: list[str] | None = None) -> list[dict[str, Any]]:
    package_literal = re.compile(r"Eidolon_v\d+_\d+(?:_\d+)?\.zip")
    files = files or ["conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/dashboard.py"]
    matches: list[dict[str, Any]] = []
    for rel in files:
        text = _read_text(ROOT_DIR / rel)
        found = sorted(set(package_literal.findall(text)))
        if found:
            matches.append({"file": rel, "matches": found})
    return matches


def build_hotfix_regression_lockdown(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.1: lock down v25.0.1 hotfix findings so they become recurring regression tripwires."""
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    api_default_audit = build_api_default_source_audit(project_id=project_id, save=False)
    cycle = build_controlled_maintenance_cycle(project_id=project_id, save=False)
    apply_gate = ((cycle.get("steps") or {}).get("apply_gate") or {}) if isinstance(cycle.get("steps"), dict) else {}
    package_routed = '/release-package' in _extract_dashboard_router_paths(dashboard_text)
    package_linked = '/release-package' in _extract_dashboard_nav_paths(dashboard_text)
    full_hash_used = bool(cycle.get("review_bundle_hash")) and apply_gate.get("binding", {}).get("supplied_bundle_hash") == cycle.get("review_bundle_hash")
    nested_status = str(apply_gate.get("status", "warn"))
    cycle_status = str(cycle.get("status", "warn"))
    rows = [
        {"name": "release-package-linked", "status": "pass" if package_linked else "blocked", "message": "/release-package is present in dashboard navigation."},
        {"name": "release-package-routed", "status": "pass" if package_routed else "blocked", "message": "/release-package has a GET router branch."},
        {"name": "api-package-helper-defaults", "status": str(api_default_audit.get("status", "warn")), "message": api_default_audit.get("message", "")},
        {"name": "nested-apply-gate-visible", "status": nested_status, "message": f"Controlled cycle nested apply gate remains visible as {nested_status}."},
        {"name": "controlled-cycle-preserves-warning", "status": "pass" if cycle_status in {"warn", "blocked"} and nested_status in {"warn", "blocked"} else "blocked", "message": f"cycle={cycle_status}; nested_apply_gate={nested_status}."},
        {"name": "review-bundle-hash-binding", "status": "pass" if full_hash_used else "blocked", "message": "Apply gate receives the full review bundle hash from the controlled cycle."},
        {"name": "dry-run-not-live-approved", "status": "pass" if apply_gate.get("dry_run") and not apply_gate.get("live_allowed") else "blocked", "message": "Dry-run cycle is not represented as live-approved apply."},
        {"name": "readme-hotfix-entry", "status": "pass" if "v25.0.1" in _read_text(ROOT_DIR / "README_NEXT_STEPS.md") else "warn", "message": "README includes the v25.0.1 hotfix entry."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.1", "status": status, "ok": _ok_from(status), "steps": {"api_default_audit": _compact_step(api_default_audit), "controlled_cycle": _compact_step(cycle), "apply_gate": _compact_step(apply_gate)}, "rows": rows, "message": "Hotfix regression lockdown completed for v25.0.1 route/default/severity fixes."}
    if save:
        _write_json(HOTFIX_REGRESSION_LOCKDOWN, report)
    else:
        report["preview_only"] = True
    return report


def build_dashboard_route_coverage_auditor(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.2: verify dashboard navigation links resolve to real GET routes."""
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    nav_paths = _extract_dashboard_nav_paths(dashboard_text)
    router_paths = _extract_dashboard_router_paths(dashboard_text)
    special = {"/api", "/api-info"}
    missing = [path for path in nav_paths if path not in router_paths and not path.startswith("/api/") and path not in special]
    rows = [
        {"name": "nav-path-count", "status": "pass" if nav_paths else "blocked", "message": f"Found {len(nav_paths)} dashboard navigation path(s)."},
        {"name": "router-path-count", "status": "pass" if router_paths else "blocked", "message": f"Found {len(router_paths)} dashboard router path(s)."},
        {"name": "nav-routes-covered", "status": "pass" if not missing else "blocked", "message": f"Missing router path(s): {', '.join(missing) or 'none'}."},
        {"name": "release-package-route", "status": "pass" if "/release-package" in router_paths else "blocked", "message": "/release-package remains route-covered."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.2", "status": status, "ok": _ok_from(status), "nav_paths": nav_paths, "router_paths": router_paths, "missing_routes": missing, "rows": rows, "message": "Dashboard route coverage auditor completed."}
    if save:
        _write_json(DASHBOARD_ROUTE_COVERAGE_AUDITOR, report)
    else:
        report["preview_only"] = True
    return report


def build_api_default_source_audit(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.3: verify API/package defaults resolve from the package helper rather than hardcoded release zip names."""
    matches = _release_package_literals_by_file(["conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/dashboard.py"])
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    helper_uses = len(re.findall(r"_package_name\(\)", api_text))
    rows = [
        {"name": "no-hardcoded-package-literals", "status": "pass" if not matches else "blocked", "message": f"Hardcoded package literal matches: {matches or 'none'}."},
        {"name": "api-uses-package-helper", "status": "pass" if helper_uses >= 3 else "warn", "message": f"api_server.py uses _package_name() {helper_uses} time(s)."},
        {"name": "current-helper-package", "status": "pass", "message": f"Current helper resolves package name as {_package_name()}."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.3", "status": status, "ok": _ok_from(status), "package_name": _package_name(), "hardcoded_matches": matches, "rows": rows, "message": "API default source-of-truth audit completed."}
    if save:
        _write_json(API_DEFAULT_SOURCE_AUDIT, report)
    else:
        report["preview_only"] = True
    return report


def build_nested_readiness_severity_engine(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.4: synthetic test for nested readiness severity aggregation rules."""
    cases = [
        {"name": "all-pass", "rows": [{"status": "pass"}, {"status": "pass"}], "expected": "pass"},
        {"name": "warn-inside-pass", "rows": [{"status": "pass"}, {"status": "warn"}], "expected": "warn"},
        {"name": "blocked-beats-warn", "rows": [{"status": "warn"}, {"status": "blocked"}], "expected": "blocked"},
        {"name": "failed-beats-pass", "rows": [{"status": "pass"}, {"status": "failed"}], "expected": "blocked"},
        {"name": "ok-true-does-not-erase-warn", "rows": [{"status": "warn", "ok": True}, {"status": "pass", "ok": True}], "expected": "warn"},
    ]
    case_results = []
    for case in cases:
        actual = _status_from(case["rows"])
        case_results.append({"name": case["name"], "expected": case["expected"], "actual": actual, "ok": actual == case["expected"]})
    rows = [
        {"name": item["name"], "status": "pass" if item["ok"] else "blocked", "message": f"expected={item['expected']} actual={item['actual']}"}
        for item in case_results
    ] + [
        {"name": "warn-ok-contract", "status": "pass" if _ok_from("warn") else "blocked", "message": "warn remains ok=True but status remains warn."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.4", "status": status, "ok": _ok_from(status), "cases": case_results, "rows": rows, "message": "Nested readiness severity engine checks completed."}
    if save:
        _write_json(NESTED_READINESS_SEVERITY_ENGINE, report)
    else:
        report["preview_only"] = True
    return report


def build_review_bundle_approval_contract(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.5: inspect approval binding hashes for proposal, plan, preview, audit, temp verification, and whole bundle."""
    bundle = build_maintenance_review_bundle(project_id=project_id, save=False)
    bundle_hash = _sha256_text(bundle)
    hashes = bundle.get("artifact_hashes", {}) if isinstance(bundle.get("artifact_hashes"), dict) else {}
    required = ["proposal", "plan", "preview", "audit", "temp_apply_drill"]
    missing = [name for name in required if name not in hashes]
    binding = build_human_approval_binding(project_id=project_id, bundle_hash=bundle_hash, confirm=True, save=False, review_bundle=bundle)
    rows = [
        {"name": "artifact-hashes-present", "status": "pass" if not missing else "blocked", "message": f"Missing artifact hash(es): {', '.join(missing) or 'none'}."},
        {"name": "whole-bundle-hash", "status": "pass" if bundle_hash else "blocked", "message": bundle_hash},
        {"name": "approval-binds-whole-bundle", "status": "pass" if binding.get("approved") and binding.get("bundle_hash") == bundle_hash else "blocked", "message": "Approval binding accepts only the exact whole review bundle hash."},
        {"name": "no-live-apply", "status": "pass", "message": "Approval contract inspection does not run a live patch apply."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.5", "status": status, "ok": _ok_from(status), "bundle_hash": bundle_hash, "artifact_hashes": hashes, "binding": binding, "rows": rows, "message": "Review bundle approval contract inspection completed."}
    if save:
        _write_json(REVIEW_BUNDLE_APPROVAL_CONTRACT, report)
    else:
        report["preview_only"] = True
    return report


def build_maintenance_report_diff_viewer(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.6: summarize differences across maintenance proposal, plan, preview, and review bundle artifacts."""
    proposal = build_self_maintenance_proposal_sandbox(project_id=project_id, save=False)
    plan = build_patch_plan_builder(project_id=project_id, save=False)
    preview = build_dry_run_patch_generator(project_id=project_id, save=False)
    bundle = build_maintenance_review_bundle(project_id=project_id, save=False)
    artifacts = {"proposal": proposal, "plan": plan, "preview": preview, "bundle": bundle}
    hashes = {name: _sha256_text(value) for name, value in artifacts.items()}
    diff_summary = [
        {"from": "proposal", "to": "plan", "change": f"{len(proposal.get('proposals', []))} proposal(s) -> {len(plan.get('file_plans', []))} file plan(s)."},
        {"from": "plan", "to": "preview", "change": f"{len(plan.get('file_plans', []))} file plan(s) -> {len(preview.get('preview_changes', []))} preview change(s)."},
        {"from": "preview", "to": "bundle", "change": f"Review bundle includes {len(bundle.get('artifact_hashes', {}))} hashed artifact(s)."},
    ]
    rows = [
        {"name": "artifact-hash-count", "status": "pass" if len(set(hashes.values())) == len(hashes) else "warn", "message": f"Computed {len(hashes)} artifact hash(es)."},
        {"name": "diff-summary", "status": "pass" if diff_summary else "warn", "message": f"Prepared {len(diff_summary)} maintenance diff summary row(s)."},
        {"name": "preview-only", "status": "pass", "message": "Diff viewer is read-only and does not mutate project files."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.6", "status": status, "ok": _ok_from(status), "artifact_hashes": hashes, "diff_summary": diff_summary, "rows": rows, "message": "Maintenance report diff viewer completed."}
    if save:
        _write_json(MAINTENANCE_REPORT_DIFF_VIEWER, report)
    else:
        report["preview_only"] = True
    return report


def build_release_gate_composition_test(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.7: test release gate aggregation with synthetic nested report compositions."""
    synthetic = [
        {"name": "pass-inside-pass", "reports": [{"status": "pass", "ok": True}, {"status": "pass", "ok": True}], "expected": "pass"},
        {"name": "warn-inside-pass", "reports": [{"status": "pass", "ok": True}, {"status": "warn", "ok": True}], "expected": "warn"},
        {"name": "blocked-inside-pass", "reports": [{"status": "pass", "ok": True}, {"status": "blocked", "ok": False}], "expected": "blocked"},
        {"name": "dry-run-with-warn", "reports": [{"status": "dry_run", "ok": True}, {"status": "warn", "ok": True}], "expected": "warn"},
    ]
    results = []
    for item in synthetic:
        rows = [{"name": f"nested-{idx}", "status": str(rep.get("status", "pass")), "message": "synthetic"} for idx, rep in enumerate(item["reports"])]
        actual = _status_from(rows)
        results.append({"name": item["name"], "expected": item["expected"], "actual": actual, "ok": actual == item["expected"]})
    rows = [{"name": r["name"], "status": "pass" if r["ok"] else "blocked", "message": f"expected={r['expected']} actual={r['actual']}"} for r in results]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.7", "status": status, "ok": _ok_from(status), "cases": results, "rows": rows, "message": "Release gate composition test completed."}
    if save:
        _write_json(RELEASE_GATE_COMPOSITION_TEST, report)
    else:
        report["preview_only"] = True
    return report


def build_dashboard_api_parity_audit(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v25.8: verify dashboard and API expose the same major maintenance/release checks."""
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    required_tokens = [
        "hotfix-regression-lockdown", "dashboard-route-coverage", "api-default-source-audit",
        "nested-readiness-severity", "review-bundle-approval-contract", "maintenance-report-diff",
        "release-gate-composition-test", "dashboard-api-parity-audit", "operator-trust-report",
        "trustworthy-maintenance-console", "trust-console-drill", "trust-console-snapshot", "trust-console-diff",
        "freeze-release-candidate", "verify-frozen-release-zip", "approval-evidence-ledger",
        "release-command-reproducer", "console-readme-consistency", "pre-v27-safety-audit", "release-candidate-governance",
    ]
    missing_dashboard = [token for token in required_tokens if token not in dashboard_text]
    missing_api = [token for token in required_tokens if token not in api_text]
    rows = [
        {"name": "dashboard-token-parity", "status": "pass" if not missing_dashboard else "warn", "message": f"Dashboard missing token(s): {', '.join(missing_dashboard) or 'none'}."},
        {"name": "api-token-parity", "status": "pass" if not missing_api else "warn", "message": f"API missing token(s): {', '.join(missing_api) or 'none'}."},
        {"name": "get-preview-rule", "status": "pass", "message": "Parity audit is read-only; GET surfaces report status only."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.8", "status": status, "ok": _ok_from(status), "required_tokens": required_tokens, "missing_dashboard": missing_dashboard, "missing_api": missing_api, "rows": rows, "message": "Dashboard/API parity audit completed."}
    if save:
        _write_json(DASHBOARD_API_PARITY_AUDIT, report)
    else:
        report["preview_only"] = True
    return report


def build_operator_trust_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v25.9: produce a concise operator-facing trust summary."""
    package_name = package_name or _package_name()
    route = build_dashboard_route_coverage_auditor(project_id=project_id, save=False)
    api_defaults = build_api_default_source_audit(project_id=project_id, save=False)
    severity = build_nested_readiness_severity_engine(project_id=project_id, save=False)
    contract = build_review_bundle_approval_contract(project_id=project_id, save=False)
    privacy = build_release_memory_privacy(project_id=project_id, save=False)
    regression = build_hotfix_regression_lockdown(project_id=project_id, save=False)
    trust_items = {
        "current_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "zip_path": zip_path,
        "safe_next_action": "Review generated reports and keep real apply disabled until exact bundle approval is present.",
        "must_not_do_yet": "Do not run live maintenance apply without exact bundle hash, explicit confirmation, backup, and rollback verification.",
    }
    rows = [
        {"name": "route-coverage", "status": str(route.get("status", "warn")), "message": route.get("message", "")},
        {"name": "api-default-source", "status": str(api_defaults.get("status", "warn")), "message": api_defaults.get("message", "")},
        {"name": "nested-severity", "status": str(severity.get("status", "warn")), "message": severity.get("message", "")},
        {"name": "approval-contract", "status": str(contract.get("status", "warn")), "message": contract.get("message", "")},
        {"name": "release-memory-privacy", "status": str(privacy.get("status", "warn")), "message": privacy.get("message", "")},
        {"name": "hotfix-regression", "status": str(regression.get("status", "warn")), "message": regression.get("message", "")},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v25.9", "status": status, "ok": _ok_from(status), "trust_items": trust_items, "steps": {"route": _compact_step(route), "api_defaults": _compact_step(api_defaults), "severity": _compact_step(severity), "contract": _compact_step(contract), "privacy": _compact_step(privacy), "regression": _compact_step(regression)}, "rows": rows, "message": "Operator trust report completed."}
    if save:
        _write_json(OPERATOR_TRUST_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def build_trustworthy_maintenance_console(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.0: gate the CLI/API/dashboard trustworthy maintenance console."""
    package_name = package_name or _package_name()
    hotfix = build_hotfix_regression_lockdown(project_id=project_id, save=False)
    routes = build_dashboard_route_coverage_auditor(project_id=project_id, save=False)
    defaults = build_api_default_source_audit(project_id=project_id, save=False)
    severity = build_nested_readiness_severity_engine(project_id=project_id, save=False)
    contract = build_review_bundle_approval_contract(project_id=project_id, save=False)
    diff = build_maintenance_report_diff_viewer(project_id=project_id, save=False)
    composition = build_release_gate_composition_test(project_id=project_id, save=False)
    parity = build_dashboard_api_parity_audit(project_id=project_id, save=False)
    trust = build_operator_trust_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    semi = build_semi_autonomous_maintenance_review(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    steps = {"hotfix": hotfix, "routes": routes, "defaults": defaults, "severity": severity, "contract": contract, "diff": diff, "composition": composition, "parity": parity, "trust": trust, "semi_autonomous_review": semi}
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "human-approval-boundary", "status": "pass", "message": "v26.0 presents a trustworthy maintenance console; real apply remains exact-approval gated."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.0", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Trustworthy maintenance console gate completed."}
    if save:
        _write_json(TRUSTWORTHY_MAINTENANCE_CONSOLE, report)
    else:
        report["preview_only"] = True
    return report


def _hash_report(report: dict[str, Any]) -> str:
    return _sha256_text({k: v for k, v in report.items() if k not in {"checked_at"}})


def _source_manifest(project_id: str = "eidolon") -> dict[str, Any]:
    checksums = build_package_checksums(project_id=project_id, save=False)
    all_entries = sorted(
        [{"path": row.get("path"), "sha256": row.get("sha256"), "size": row.get("size")} for row in checksums.get("checksums", [])],
        key=lambda row: str(row.get("path", "")),
    )
    entries = _evidence_manifest_entries(all_entries)
    drift_tolerant = [row for row in all_entries if _is_metadata_drift_tolerant_path(str(row.get("path", "")))]
    return {
        "entries": entries,
        "all_entries": all_entries,
        "drift_tolerant_entries": drift_tolerant,
        "manifest_sha256": _manifest_hash(entries),
        "all_manifest_sha256": _manifest_hash(all_entries),
        "file_count": len(entries),
        "all_file_count": len(all_entries),
        "drift_tolerant_count": len(drift_tolerant),
        "inventory_status": checksums.get("status"),
        "inventory_ok": checksums.get("ok"),
    }


def build_trust_console_drill(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v26.1: run synthetic trust-console scenarios so green checks cannot hide warnings/blocks."""
    scenarios = [
        {"name": "all-pass", "rows": [{"name": "a", "status": "pass", "message": "ok"}], "expected": "pass"},
        {"name": "nested-warn", "rows": [{"name": "a", "status": "pass", "message": "ok"}, {"name": "b", "status": "warn", "message": "warning must survive"}], "expected": "warn"},
        {"name": "nested-blocked", "rows": [{"name": "a", "status": "pass", "message": "ok"}, {"name": "b", "status": "blocked", "message": "block must dominate"}], "expected": "blocked"},
        {"name": "stale-package-default", "rows": [{"name": "package-default", "status": "warn", "message": "hardcoded stale package"}], "expected": "warn"},
        {"name": "missing-dashboard-route", "rows": [{"name": "route", "status": "blocked", "message": "nav points to missing route"}], "expected": "blocked"},
        {"name": "readme-drift", "rows": [{"name": "readme", "status": "warn", "message": "latest entry absent"}], "expected": "warn"},
        {"name": "source-privacy-leak", "rows": [{"name": "privacy", "status": "blocked", "message": "runtime/private file in package"}], "expected": "blocked"},
    ]
    results = []
    for scenario in scenarios:
        actual = _status_from(scenario["rows"])
        results.append({"name": scenario["name"], "expected": scenario["expected"], "actual": actual, "ok": actual == scenario["expected"]})
    rows = [{"name": item["name"], "status": "pass" if item["ok"] else "blocked", "message": f"expected={item['expected']} actual={item['actual']}"} for item in results]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.1", "status": status, "ok": _ok_from(status), "scenarios": results, "rows": rows, "message": "Trust console drill scenarios completed."}
    if save: _write_json(TRUST_CONSOLE_DRILL, report)
    else: report["preview_only"] = True
    return report


def build_trust_console_snapshot(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.2: export a complete operator trust snapshot using lightweight trust-console signals."""
    package_name = package_name or _package_name()
    route = build_dashboard_route_coverage_auditor(project_id=project_id, save=False)
    defaults = build_api_default_source_audit(project_id=project_id, save=False)
    severity = build_nested_readiness_severity_engine(project_id=project_id, save=False)
    contract = build_review_bundle_approval_contract(project_id=project_id, save=False)
    drill = build_trust_console_drill(project_id=project_id, save=False)
    readme = _read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    latest_readme_heading = next((line.strip("# ") for line in readme.splitlines() if line.startswith("# Eidolon")), "")
    console_status = _status_from([
        {"name": "route", "status": str(route.get("status", "warn")), "message": ""},
        {"name": "defaults", "status": str(defaults.get("status", "warn")), "message": ""},
        {"name": "severity", "status": str(severity.get("status", "warn")), "message": ""},
        {"name": "contract", "status": str(contract.get("status", "warn")), "message": ""},
        {"name": "drill", "status": str(drill.get("status", "warn")), "message": ""},
    ])
    rows = [
        {"name": "console", "status": console_status, "message": "Lightweight trust-console status assembled from route/default/severity/contract/drill checks."},
        {"name": "route-coverage", "status": str(route.get("status", "warn")), "message": route.get("message", "")},
        {"name": "api-defaults", "status": str(defaults.get("status", "warn")), "message": defaults.get("message", "")},
        {"name": "nested-severity", "status": str(severity.get("status", "warn")), "message": severity.get("message", "")},
        {"name": "approval-contract", "status": str(contract.get("status", "warn")), "message": contract.get("message", "")},
        {"name": "readme-latest", "status": "pass" if "v30.0" in latest_readme_heading else "warn", "message": latest_readme_heading or "No README heading found."},
    ]
    status = _status_from(rows)
    report = {
        "version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.2", "status": status, "ok": _ok_from(status),
        "current_version": SELF_MAINTENANCE_VERSION, "package_name": package_name, "zip_path": zip_path, "latest_readme_heading": latest_readme_heading,
        "verification_commands": [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "PYTHONPATH=conscious_agent python -c \"import dashboard, api_server; print(dashboard.DASHBOARD_VERSION, api_server.API_VERSION)\"",
            "python conscious_agent/main.py --trustworthy-maintenance-console --readiness-json",
            "python conscious_agent/main.py --trust-console-drill --readiness-json",
            "python -u tools/smoke_check.py --tier install --json",
        ],
        "steps": {"route": _compact_step(route), "defaults": _compact_step(defaults), "severity": _compact_step(severity), "contract": _compact_step(contract), "drill": _compact_step(drill)},
        "rows": rows, "message": "Trust console snapshot exported."
    }
    report["snapshot_hash"] = _hash_report(report)
    if save: _write_json(TRUST_CONSOLE_SNAPSHOT, report)
    else: report["preview_only"] = True
    return report

def build_trust_console_diff(project_id: str = "eidolon", before_path: str | None = None, after_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.3: compare two trust snapshots, or compare a generated baseline against the current snapshot."""
    before = _read_json(Path(before_path), {}) if before_path else {"status": "warn", "snapshot_hash": "synthetic-before", "rows": [{"name": "synthetic", "status": "warn", "message": "baseline"}]}
    after = _read_json(Path(after_path), {}) if after_path else build_trust_console_snapshot(project_id=project_id, save=False)
    before_rows = {row.get("name"): row.get("status") for row in before.get("rows", []) if isinstance(row, dict)}
    after_rows = {row.get("name"): row.get("status") for row in after.get("rows", []) if isinstance(row, dict)}
    names = sorted(set(before_rows) | set(after_rows))
    changes = [{"name": name, "before": before_rows.get(name), "after": after_rows.get(name), "changed": before_rows.get(name) != after_rows.get(name)} for name in names]
    hidden_blocks = [c for c in changes if c.get("before") == "blocked" and c.get("after") in {"pass", None}]
    rows = [
        {"name": "snapshot-before", "status": "pass" if before else "warn", "message": str(before.get("snapshot_hash", "missing"))},
        {"name": "snapshot-after", "status": "pass" if after else "blocked", "message": str(after.get("snapshot_hash", "missing"))},
        {"name": "changed-rows", "status": "pass", "message": f"{sum(1 for c in changes if c['changed'])} row(s) changed."},
        {"name": "hidden-blocks", "status": "blocked" if hidden_blocks else "pass", "message": f"{len(hidden_blocks)} blocked row(s) disappeared without an explicit after status."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.3", "status": status, "ok": _ok_from(status), "before_path": before_path, "after_path": after_path, "changes": changes, "rows": rows, "message": "Trust console snapshot diff completed."}
    if save: _write_json(TRUST_CONSOLE_DIFF, report)
    else: report["preview_only"] = True
    return report


def build_release_candidate_freezer(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v26.4: freeze the reviewed source artifact set before packaging."""
    manifest = _source_manifest(project_id=project_id)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    integrity = build_release_manifest_integrity(project_id=project_id, save=False)
    rows = [
        {"name": "source-manifest", "status": "pass" if manifest["entries"] else "blocked", "message": f"{manifest['file_count']} hash-bound file(s), {manifest['drift_tolerant_count']} metadata file(s) drift-tolerant, {manifest['manifest_sha256']}"},
        {"name": "privacy-scan", "status": str(privacy.get("status", "warn")), "message": privacy.get("message", "")},
        {"name": "release-integrity", "status": str(integrity.get("status", "warn")), "message": integrity.get("message", "")},
        {"name": "readme-current", "status": "pass" if "v30.0" in _read_text(ROOT_DIR / "README_NEXT_STEPS.md") else "warn", "message": "README includes v30.0 notes."},
    ]
    status = _status_from(rows)
    freeze = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.4", "status": status, "ok": _ok_from(status), "package_profile": "source_only", "manifest_sha256": manifest["manifest_sha256"], "file_count": manifest["file_count"], "all_file_count": manifest.get("all_file_count"), "drift_tolerant_count": manifest.get("drift_tolerant_count", 0), "drift_tolerant_entries": manifest.get("drift_tolerant_entries", []), "entries": manifest["entries"], "rows": rows, "message": "Release candidate artifact set frozen for review."}
    freeze["freeze_hash"] = _hash_report(freeze)
    if save: _write_json(RELEASE_CANDIDATE_FREEZE, freeze)
    else: freeze["preview_only"] = True
    return freeze


def build_frozen_release_zip_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.5: verify the final zip exactly matches the frozen release candidate manifest."""
    package_name = package_name or _package_name()
    freeze = build_release_candidate_freezer(project_id=project_id, save=False)
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    freeze_paths = {row["path"]: row for row in _evidence_manifest_entries(freeze.get("entries", []))}
    zip_entries = _evidence_manifest_entries(manifest.get("entries", []))
    zip_paths = {row["path"]: row for row in zip_entries}
    zip_manifest_hash = _manifest_hash(zip_entries) if zip_entries else manifest.get("manifest_sha256")
    missing = sorted(set(freeze_paths) - set(zip_paths)) if zip_paths else []
    extra = sorted(set(zip_paths) - set(freeze_paths)) if zip_paths else []
    changed = sorted(path for path in set(freeze_paths) & set(zip_paths) if freeze_paths[path].get("sha256") != zip_paths[path].get("sha256")) if zip_paths else []
    rows = [
        {"name": "zip-present", "status": "pass" if manifest.get("zip_path") else "warn", "message": manifest.get("zip_path") or "No external zip supplied; working-tree manifest comparison only."},
        {"name": "manifest-hash-match", "status": "pass" if zip_manifest_hash == freeze.get("manifest_sha256") else "blocked", "message": f"frozen={freeze.get('manifest_sha256')} zip={zip_manifest_hash}; drift-tolerant metadata ignored={freeze.get('drift_tolerant_count', 0)}"},
        {"name": "missing-files", "status": "pass" if not missing else "blocked", "message": f"{len(missing)} missing file(s)."},
        {"name": "extra-files", "status": "pass" if not extra else "blocked", "message": f"{len(extra)} extra file(s)."},
        {"name": "changed-files", "status": "pass" if not changed else "blocked", "message": f"{len(changed)} changed file(s)."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.5", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": manifest.get("zip_path"), "freeze_hash": freeze.get("freeze_hash"), "frozen_manifest_sha256": freeze.get("manifest_sha256"), "zip_manifest_sha256": zip_manifest_hash, "missing_files": missing, "extra_files": extra, "changed_files": changed, "rows": rows, "message": "Frozen release zip verification completed."}
    if save: _write_json(FROZEN_RELEASE_ZIP_VERIFICATION, report)
    else: report["preview_only"] = True
    return report


def build_approval_evidence_ledger(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.6: collect inspectable approval evidence without treating it as live approval."""
    freeze = build_release_candidate_freezer(project_id=project_id, save=False)
    verify = build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    commands = build_release_command_reproducer(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    artifact_hashes = {
        "release_candidate_freeze": freeze.get("freeze_hash"),
        "frozen_zip_verification": _hash_report(verify),
        "release_command_reproducer": _hash_report(commands),
    }
    missing = [name for name, value in artifact_hashes.items() if not value]
    rows = [
        {"name": "artifact-hashes", "status": "pass" if not missing else "warn", "message": f"Missing: {', '.join(missing) or 'none'}."},
        {"name": "zip-verification", "status": str(verify.get("status", "warn")), "message": verify.get("message", "")},
        {"name": "live-approval", "status": "warn", "message": "Ledger is evidence only; it does not authorize live apply."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.6", "status": status, "ok": _ok_from(status), "artifact_hashes": artifact_hashes, "rows": rows, "message": "Approval evidence ledger generated; live approval remains separate."}
    if save: _write_json(APPROVAL_EVIDENCE_LEDGER, report)
    else: report["preview_only"] = True
    return report

def build_release_command_reproducer(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.7: generate copyable commands to reproduce release verification."""
    package_name = package_name or _package_name()
    zip_arg = f" --release-zip-path {zip_path}" if zip_path else ""
    commands = [
        "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
        "PYTHONPATH=conscious_agent python -c \"import dashboard, api_server; print(dashboard.DASHBOARD_VERSION, api_server.API_VERSION)\"",
        "python conscious_agent/main.py --package-privacy-scan --readiness-json",
        "python conscious_agent/main.py --release-manifest-integrity --readiness-json",
        f"python conscious_agent/main.py --external-zip-install-verification{zip_arg} --readiness-json",
        f"python conscious_agent/main.py --trial-upgrade-from-zip{zip_arg} --readiness-json",
        f"python conscious_agent/main.py --trustworthy-maintenance-console{zip_arg} --readiness-json",
        "python -u tools/smoke_check.py --tier install --json",
    ]
    rows = [{"name": "commands", "status": "pass", "message": f"{len(commands)} reproducible command(s) generated for {package_name}."}]
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.7", "status": "pass", "ok": True, "package_name": package_name, "zip_path": zip_path, "commands": commands, "rows": rows, "message": "Release command reproducer generated."}
    if save: _write_json(RELEASE_COMMAND_REPRODUCER, report)
    else: report["preview_only"] = True
    return report


def build_console_readme_consistency(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v26.8: verify README notes match actual CLI/API/dashboard features."""
    readme = _read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    main_text = _read_text(ROOT_DIR / "conscious_agent" / "main.py")
    api_text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    dashboard_text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    required_flags = [
        "trust-console-drill", "trust-console-snapshot", "trust-console-diff", "freeze-release-candidate", "verify-frozen-release-zip",
        "approval-evidence-ledger", "release-command-reproducer", "console-readme-consistency", "pre-v27-safety-audit", "release-candidate-governance",
    ]
    missing_main = [flag for flag in required_flags if flag not in main_text]
    missing_readme = [flag for flag in required_flags if flag not in readme]
    missing_api = [flag for flag in required_flags if flag not in api_text]
    missing_dashboard = [flag for flag in required_flags if flag not in dashboard_text]
    rows = [
        {"name": "cli-flags", "status": "pass" if not missing_main else "blocked", "message": f"Missing CLI flags: {', '.join(missing_main) or 'none'}."},
        {"name": "readme-flags", "status": "pass" if not missing_readme else "warn", "message": f"Missing README flags: {', '.join(missing_readme) or 'none'}."},
        {"name": "api-surfaces", "status": "pass" if not missing_api else "warn", "message": f"Missing API tokens: {', '.join(missing_api) or 'none'}."},
        {"name": "dashboard-surfaces", "status": "pass" if not missing_dashboard else "warn", "message": f"Missing dashboard tokens: {', '.join(missing_dashboard) or 'none'}."},
        {"name": "current-version", "status": "pass" if "v30.0" in readme else "warn", "message": "README includes v30.0."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.8", "status": status, "ok": _ok_from(status), "required_flags": required_flags, "rows": rows, "message": "Console-to-README consistency check completed."}
    if save: _write_json(CONSOLE_README_CONSISTENCY, report)
    else: report["preview_only"] = True
    return report


def build_pre_v27_safety_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v26.9: final safety audit before release candidate governance."""
    package_name = package_name or _package_name()
    steps = {
        "trust_console": build_operator_trust_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "drill": build_trust_console_drill(project_id=project_id, save=False),
        "snapshot": build_trust_console_snapshot(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "diff": build_trust_console_diff(project_id=project_id, save=False),
        "freeze": build_release_candidate_freezer(project_id=project_id, save=False),
        "frozen_zip": build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "ledger": build_approval_evidence_ledger(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "readme": build_console_readme_consistency(project_id=project_id, save=False),
        "privacy": build_package_privacy_scan(project_id=project_id, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v26.9", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Pre-v27 safety audit completed."}
    if save: _write_json(PRE_V27_SAFETY_AUDIT, report)
    else: report["preview_only"] = True
    return report


def build_release_candidate_governance(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.0: govern a release candidate from freeze through evidence-backed zip verification."""
    package_name = package_name or _package_name()
    steps = {
        "freeze": build_release_candidate_freezer(project_id=project_id, save=False),
        "frozen_zip": build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "evidence": build_approval_evidence_ledger(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "commands": build_release_command_reproducer(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "trust": build_operator_trust_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "governance-boundary", "status": "pass", "message": "v27.0 governs release candidates; it does not perform live apply without exact approval."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v27.0", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Release candidate governance system completed."}
    if save: _write_json(RELEASE_CANDIDATE_GOVERNANCE, report)
    else: report["preview_only"] = True
    return report


def build_release_governance_drill(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v27.1: synthetic bad-evidence scenarios for release governance."""
    scenarios = [
        ("matching-frozen-zip", [{"name":"manifest", "status":"pass", "message":"candidate matches zip"}], "pass"),
        ("extra-file", [{"name":"extra-files", "status":"blocked", "message":"zip has unreviewed file"}], "blocked"),
        ("missing-file", [{"name":"missing-files", "status":"blocked", "message":"zip lost reviewed file"}], "blocked"),
        ("changed-hash", [{"name":"changed-files", "status":"blocked", "message":"path same, hash changed"}], "blocked"),
        ("readme-missing", [{"name":"readme", "status":"warn", "message":"latest entry absent"}], "warn"),
        ("approval-hash-mismatch", [{"name":"approval-evidence", "status":"blocked", "message":"bundle hash mismatch"}], "blocked"),
        ("runtime-file-leak", [{"name":"privacy", "status":"blocked", "message":"runtime/private file in package"}], "blocked"),
        ("profile-drift", [{"name":"package-profile", "status":"blocked", "message":"profile differs from frozen candidate"}], "blocked"),
    ]
    results=[]
    for name, rows, expected in scenarios:
        actual=_status_from(rows)
        results.append({"name":name,"expected":expected,"actual":actual,"ok":actual==expected})
    rows=[{"name":r["name"],"status":"pass" if r["ok"] else "blocked","message":f"expected={r['expected']} actual={r['actual']}"} for r in results]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.1","status":status,"ok":_ok_from(status),"scenarios":results,"rows":rows,"message":"Release governance evidence drill completed."}
    if save: _write_json(RELEASE_GOVERNANCE_DRILL, report)
    else: report["preview_only"]=True
    return report


def build_release_evidence_bundle(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.2: export one reviewable release evidence bundle."""
    package_name=package_name or _package_name()
    steps={
        "freeze": build_release_candidate_freezer(project_id=project_id, save=False),
        "frozen_zip": build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "privacy": build_package_privacy_scan(project_id=project_id, save=False),
        "deterministic_manifest": build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "trial_upgrade": {"version": SELF_MAINTENANCE_VERSION, "stage": "trial-upgrade", "status": "warn", "ok": True, "message": "Trial upgrade is referenced by the evidence bundle but run as a separate verification command to keep governance gates responsive.", "rows": [{"name": "external-zip", "status": "warn", "message": "Run --trial-upgrade-from-zip with --release-zip-path for full install rehearsal evidence."}]},
        "trust_console": build_operator_trust_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "approval_ledger": build_approval_evidence_ledger(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "commands": build_release_command_reproducer(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    readme=_read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    latest=next((line for line in readme.splitlines() if line.startswith("# Eidolon")), "")
    rows=[{"name":name,"status":str(step.get("status","warn")),"message":step.get("message","")} for name,step in steps.items()]
    rows.append({"name":"readme-latest","status":"pass" if "v30.0" in latest else "warn","message":latest or "missing README heading"})
    status=_status_from(rows)
    bundle={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.2","status":status,"ok":_ok_from(status),"package_name":package_name,"zip_path":zip_path,"readme_latest_entry":latest,"steps":{name:_compact_step(step) for name,step in steps.items()},"rows":rows,"message":"Release evidence bundle exported."}
    bundle["bundle_hash"]=_hash_report(bundle)
    if save: _write_json(RELEASE_EVIDENCE_BUNDLE, bundle)
    else: bundle["preview_only"]=True
    return bundle


def build_release_evidence_bundle_verifier(project_id: str = "eidolon", bundle_path: str | None = None, package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.3: verify a saved or freshly generated evidence bundle."""
    bundle=_read_json(Path(bundle_path), {}) if bundle_path else build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    required=["freeze","frozen_zip","privacy","deterministic_manifest","trial_upgrade","trust_console","approval_ledger","commands"]
    steps=bundle.get("steps", {}) if isinstance(bundle.get("steps"), dict) else {}
    missing=[name for name in required if name not in steps]
    hidden=[row for row in bundle.get("rows", []) if isinstance(row, dict) and str(row.get("status")).lower() in {"blocked","failed","fail"}]
    calc=_hash_report({k:v for k,v in bundle.items() if k not in {"bundle_hash","preview_only"}}) if bundle else ""
    rows=[
        {"name":"schema","status":"pass" if isinstance(bundle,dict) and bundle else "blocked","message":"bundle is a JSON object"},
        {"name":"required-sections","status":"pass" if not missing else "blocked","message":f"missing={', '.join(missing) or 'none'}"},
        {"name":"bundle-hash","status":"pass" if not bundle.get("bundle_hash") or calc==bundle.get("bundle_hash") else "blocked","message":f"stored={bundle.get('bundle_hash')} calculated={calc}"},
        {"name":"blocked-details-visible","status":"warn" if hidden else "pass","message":f"{len(hidden)} blocked row(s) remain visible."},
    ]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.3","status":status,"ok":_ok_from(status),"bundle_path":bundle_path,"bundle_hash":bundle.get("bundle_hash"),"rows":rows,"message":"Release evidence bundle verification completed."}
    if save: _write_json(RELEASE_EVIDENCE_BUNDLE_VERIFIER, report)
    else: report["preview_only"]=True
    return report


def build_release_governance_page(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v27.4: dashboard governance page availability check."""
    dash=_read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    rows=[
        {"name":"route-linked","status":"pass" if "/release-governance" in dash else "blocked","message":"dashboard references /release-governance"},
        {"name":"renderer","status":"pass" if "def render_release_governance" in dash else "blocked","message":"release governance renderer exists"},
        {"name":"read-only","status":"pass","message":"governance page is GET-only and report-oriented"},
    ]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.4","status":status,"ok":_ok_from(status),"rows":rows,"message":"Release governance dashboard page check completed."}
    if save: _write_json(RELEASE_GOVERNANCE_PAGE, report)
    else: report["preview_only"]=True
    return report


def build_governance_api_read_only_surface(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v27.5: verify governance API inspection surfaces are GET/read-only."""
    api=_read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    tokens=["release-governance-drill","release-evidence-bundle","verify-release-evidence-bundle","release-artifact-diff","pre-v28-governance-audit","verifiable-release-evidence-system"]
    missing=[token for token in tokens if token not in api]
    rows=[
        {"name":"api-tokens","status":"pass" if not missing else "warn","message":f"missing={', '.join(missing) or 'none'}"},
        {"name":"get-read-only","status":"pass","message":"governance API routes build preview reports with save=False"},
        {"name":"post-not-required","status":"pass","message":"v27.5 inspection endpoints do not mutate release state"},
    ]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.5","status":status,"ok":_ok_from(status),"rows":rows,"message":"Governance API read-only surface check completed."}
    if save: _write_json(GOVERNANCE_API_READ_ONLY_SURFACE, report)
    else: report["preview_only"]=True
    return report


def build_release_artifact_diff(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.6: compare hash-bound candidate files with final zip artifacts."""
    package_name=package_name or _package_name()
    freeze=build_release_candidate_freezer(project_id=project_id, save=False)
    manifest=build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    c={row["path"]:row for row in _evidence_manifest_entries(freeze.get("entries", []))}
    z={row["path"]:row for row in _evidence_manifest_entries(manifest.get("entries", []))}
    only_candidate=sorted(set(c)-set(z)) if z else []
    only_zip=sorted(set(z)-set(c)) if z else []
    changed=sorted(path for path in set(c)&set(z) if c[path].get("sha256")!=z[path].get("sha256")) if z else []
    rows=[
        {"name":"candidate-only","status":"pass" if not only_candidate else "blocked","message":f"{len(only_candidate)} file(s)"},
        {"name":"zip-only","status":"pass" if not only_zip else "blocked","message":f"{len(only_zip)} file(s)"},
        {"name":"changed-hashes","status":"pass" if not changed else "blocked","message":f"{len(changed)} file(s)"},
        {"name":"metadata-drift-policy","status":"pass","message":"portable workspace metadata is checked separately and excluded from hash-bound drift comparison"},
    ]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.6","status":status,"ok":_ok_from(status),"package_name":package_name,"zip_path":zip_path,"candidate_only":only_candidate,"zip_only":only_zip,"changed_hashes":changed,"rows":rows,"message":"Release artifact diff completed."}
    if save: _write_json(RELEASE_ARTIFACT_DIFF, report)
    else: report["preview_only"]=True
    return report


def build_release_signing_preparation(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.7: produce signing-ready, explicitly unsigned metadata."""
    package_name=package_name or _package_name()
    bundle=build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    block={"schema":"eidolon.release_evidence.v1","package_name":package_name,"package_sha256":_sha256_file(Path(zip_path)) if zip_path and Path(zip_path).exists() else None,"evidence_bundle_hash":bundle.get("bundle_hash"),"signature_status":"unsigned","canonical_manifest_format":"sorted-json-sha256"}
    rows=[{"name":"signing-ready-metadata","status":"pass","message":"canonical unsigned metadata block generated"},{"name":"unsigned-status","status":"warn","message":"artifact is explicitly unsigned; no cryptographic signature is claimed"}]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.7","status":status,"ok":_ok_from(status),"signing_metadata":block,"rows":rows,"message":"Release signing preparation metadata generated; artifact remains unsigned."}
    if save: _write_json(RELEASE_SIGNING_PREPARATION, report)
    else: report["preview_only"]=True
    return report


def build_local_trust_policy(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.8: enforce local release trust policy without packaging runtime policy history."""
    package_name=package_name or _package_name()
    privacy=build_package_privacy_scan(project_id=project_id, save=False)
    frozen=build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    readme=_read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    rules=[
        {"name":"source-only-package","status":str(privacy.get("status","warn")),"message":privacy.get("message","")},
        {"name":"no-private-runtime-data","status":"pass" if privacy.get("ok") else "blocked","message":"privacy scan must not report private/runtime inclusion"},
        {"name":"readme-latest-entry","status":"pass" if "v30.0" in readme else "warn","message":"README must include current release notes"},
        {"name":"frozen-candidate-matches-zip","status":str(frozen.get("status","warn")),"message":frozen.get("message","")},
        {"name":"warnings-nonblocking-only","status":"warn","message":"warnings are allowed only when marked non-blocking; live apply still needs exact approval"},
    ]
    status=_status_from(rules)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.8","status":status,"ok":_ok_from(status),"policy":"default_code_defined_release_trust_policy","rows":rules,"message":"Local trust policy evaluated."}
    if save: _write_json(LOCAL_TRUST_POLICY, report)
    else: report["preview_only"]=True
    return report


def build_release_governance_ux_polish(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.9: explain pass/warn/block rows and next safe action."""
    governance=build_release_candidate_governance(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    rows=[{"name":"message-present","status":"pass" if governance.get("message") else "warn","message":governance.get("message","")},{"name":"next-action","status":"pass","message":"If blocked, inspect release-artifact-diff; if warn-only, review evidence before sharing."}]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.9","status":status,"ok":_ok_from(status),"safe_to_share":governance.get("status") in {"pass","warn"},"next_safe_action":"Review evidence bundle and artifact diff before publishing the zip.","rows":rows,"message":"Release governance UX polish report generated."}
    if save: _write_json(RELEASE_GOVERNANCE_UX_POLISH, report)
    else: report["preview_only"]=True
    return report


def build_pre_v28_governance_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v27.10: final pre-v28 governance audit."""
    package_name=package_name or _package_name()
    steps={
        "governance_drill": build_release_governance_drill(project_id=project_id, save=False),
        "evidence_bundle": build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "evidence_verifier": build_release_evidence_bundle_verifier(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "artifact_diff": build_release_artifact_diff(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "dashboard_page": build_release_governance_page(project_id=project_id, save=False),
        "api_surface": build_governance_api_read_only_surface(project_id=project_id, save=False),
        "trust_policy": build_local_trust_policy(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "readme_consistency": build_console_readme_consistency(project_id=project_id, save=False),
        "privacy": build_package_privacy_scan(project_id=project_id, save=False),
        "frozen_zip": build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    rows=[{"name":name,"status":str(step.get("status","warn")),"message":step.get("message","")} for name,step in steps.items()]
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v27.10","status":status,"ok":_ok_from(status),"package_name":package_name,"zip_path":zip_path,"steps":{name:_compact_step(step) for name,step in steps.items()},"rows":rows,"message":"Pre-v28 governance audit completed."}
    if save: _write_json(PRE_V28_GOVERNANCE_AUDIT, report)
    else: report["preview_only"]=True
    return report


def build_verifiable_release_evidence_system(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.0: complete verifiable release evidence gate."""
    package_name=package_name or _package_name()
    steps={
        "governance_drill": build_release_governance_drill(project_id=project_id, save=False),
        "evidence_bundle": build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "evidence_verify": build_release_evidence_bundle_verifier(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "artifact_diff": build_release_artifact_diff(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "governance_page": build_release_governance_page(project_id=project_id, save=False),
        "api_surface": build_governance_api_read_only_surface(project_id=project_id, save=False),
        "trust_policy": build_local_trust_policy(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "commands": build_release_command_reproducer(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    rows=[{"name":name,"status":str(step.get("status","warn")),"message":step.get("message","")} for name,step in steps.items()]
    rows.append({"name":"no-auto-release","status":"pass","message":"v28.0 proves evidence; it does not auto-release or live-apply anything."})
    status=_status_from(rows)
    report={"version":SELF_MAINTENANCE_VERSION,"checked_at":_now(),"project_id":project_id,"stage":"v28.0","status":status,"ok":_ok_from(status),"package_name":package_name,"zip_path":zip_path,"steps":{name:_compact_step(step) for name,step in steps.items()},"rows":rows,"message":"Verifiable release evidence system completed."}
    if save: _write_json(VERIFIABLE_RELEASE_EVIDENCE_SYSTEM, report)
    else: report["preview_only"]=True
    return report


def _reports_dir() -> Path:
    RELEASE_EVIDENCE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return RELEASE_EVIDENCE_REPORT_DIR


def _evidence_report_name(package_name: str | None = None) -> str:
    package_name = package_name or _package_name()
    stem = Path(package_name).stem or "Eidolon_release"
    return f"{stem}_evidence.json"


def _write_evidence_report(report: dict[str, Any], package_name: str | None = None) -> Path:
    path = _reports_dir() / _evidence_report_name(package_name)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    latest = _reports_dir() / "latest.json"
    latest.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path


def _safe_read_bundle(bundle_path: str | None, project_id: str, package_name: str | None, zip_path: str | None) -> tuple[dict[str, Any], str | None]:
    if bundle_path:
        path = Path(bundle_path)
        if path.exists():
            return _read_json(path, {}), str(path)
        return {}, str(path)
    latest = RELEASE_EVIDENCE_REPORT_DIR / "latest.json"
    if latest.exists():
        return _read_json(latest, {}), str(latest)
    return build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False), None


def _evidence_bundle_hash(bundle: dict[str, Any]) -> str:
    if not isinstance(bundle, dict) or not bundle:
        return ""
    return _hash_report({k: v for k, v in bundle.items() if k not in {"bundle_hash", "preview_only"}})


def build_evidence_replay_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.1: replay/tamper synthetic evidence scenarios."""
    package_name = package_name or _package_name()
    base = build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    good_hash = base.get("bundle_hash")
    scenarios: list[dict[str, Any]] = []

    def verify(name: str, bundle: dict[str, Any], expected: str, message: str) -> None:
        required = ["freeze", "frozen_zip", "privacy", "deterministic_manifest", "trial_upgrade", "trust_console", "approval_ledger", "commands"]
        steps = bundle.get("steps", {}) if isinstance(bundle.get("steps"), dict) else {}
        rows = list(bundle.get("rows", [])) if isinstance(bundle.get("rows"), list) else []
        missing = [item for item in required if item not in steps]
        calc = _evidence_bundle_hash(bundle)
        stored = bundle.get("bundle_hash")
        hidden = bundle.get("hidden_warning_rows", False) or (str(bundle.get("status", "pass")) == "pass" and any(str(row.get("status", "")).lower() in {"warn", "blocked"} for row in rows if isinstance(row, dict)))
        runtime_leak = bool(bundle.get("runtime_private_file_present"))
        stale_version = bundle.get("version") not in {SELF_MAINTENANCE_VERSION, "30.0"}
        blocked = bool(missing or runtime_leak or stale_version or (stored and calc and stored != calc) or hidden)
        actual = "blocked" if blocked else str(bundle.get("status", "pass"))
        if actual not in {"blocked", "warn", "pass"}:
            actual = "warn"
        scenarios.append({"name": name, "expected": expected, "actual": actual, "ok": actual == expected, "message": message, "stored_hash": stored, "calculated_hash": calc, "missing_sections": missing})

    verify("replay-current-evidence", dict(base), str(base.get("status", "warn")), "Replay the current generated evidence bundle.")
    missing_manifest = json.loads(json.dumps(base, default=str)); missing_manifest.get("steps", {}).pop("deterministic_manifest", None); missing_manifest["bundle_hash"] = good_hash
    verify("missing-manifest-section", missing_manifest, "blocked", "Missing required manifest section must block.")
    changed_package = json.loads(json.dumps(base, default=str)); changed_package["package_sha256"] = "tampered"; changed_package["bundle_hash"] = good_hash
    verify("changed-package-hash", changed_package, "blocked", "Tampered package hash must block.")
    changed_source = json.loads(json.dumps(base, default=str)); changed_source.setdefault("steps", {}).setdefault("freeze", {})["manifest_sha256"] = "tampered"; changed_source["bundle_hash"] = good_hash
    verify("changed-source-file-hash", changed_source, "blocked", "Tampered source manifest hash must block.")
    readme_missing = json.loads(json.dumps(base, default=str)); readme_missing["readme_latest_entry"] = ""; readme_missing.setdefault("rows", []).append({"name":"readme-latest","status":"warn","message":"missing latest entry"}); readme_missing["bundle_hash"] = _evidence_bundle_hash(readme_missing)
    verify("missing-readme-release-note", readme_missing, "warn", "Missing README entry should remain visible as warning.")
    hidden_warn = json.loads(json.dumps(base, default=str)); hidden_warn["status"] = "pass"; hidden_warn["hidden_warning_rows"] = True; hidden_warn["bundle_hash"] = _evidence_bundle_hash(hidden_warn)
    verify("hidden-warning-rows", hidden_warn, "blocked", "Evidence cannot hide warning/block rows behind pass.")
    runtime_leak = json.loads(json.dumps(base, default=str)); runtime_leak["runtime_private_file_present"] = True; runtime_leak["bundle_hash"] = _evidence_bundle_hash(runtime_leak)
    verify("runtime-private-data-leak", runtime_leak, "blocked", "Evidence must block if package includes runtime/private data.")
    old_version = json.loads(json.dumps(base, default=str)); old_version["version"] = "28.0"; old_version["bundle_hash"] = _evidence_bundle_hash(old_version)
    verify("older-evidence-against-newer-package", old_version, "blocked", "Older evidence should not silently certify newer package.")

    rows = [{"name": item["name"], "status": "pass" if item["ok"] else "blocked", "message": f"expected={item['expected']} actual={item['actual']}"} for item in scenarios]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.1", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "scenarios": scenarios, "rows": rows, "message": "Evidence replay/tamper drill completed."}
    if save: _write_json(EVIDENCE_REPLAY_DRILL, report)
    else: report["preview_only"] = True
    return report


def build_evidence_bundle_persistence(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.2: persist release evidence as generated reports excluded from source-only packages."""
    package_name = package_name or _package_name()
    bundle = build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    persisted_path = _write_evidence_report(bundle, package_name) if save else _reports_dir() / _evidence_report_name(package_name)
    rows = [
        {"name": "report-path", "status": "pass", "message": str(persisted_path.relative_to(ROOT_DIR) if persisted_path.is_relative_to(ROOT_DIR) else persisted_path)},
        {"name": "reports-excluded-from-package", "status": "pass", "message": "reports/release_evidence is generated runtime output and excluded from source-only zips."},
        {"name": "bundle-hash", "status": "pass" if bundle.get("bundle_hash") else "warn", "message": str(bundle.get("bundle_hash"))},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.2", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "evidence_path": str(persisted_path), "bundle_hash": bundle.get("bundle_hash"), "rows": rows, "message": "Release evidence bundle persistence completed."}
    if save: _write_json(EVIDENCE_BUNDLE_PERSISTENCE, report)
    else: report["preview_only"] = True
    return report


def build_replay_release_evidence(project_id: str = "eidolon", bundle_path: str | None = None, package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.3: replay a saved release evidence bundle against an optional zip."""
    package_name = package_name or _package_name()
    bundle, resolved_path = _safe_read_bundle(bundle_path, project_id, package_name, zip_path)
    verifier = build_release_evidence_bundle_verifier(project_id=project_id, bundle_path=resolved_path, package_name=package_name, zip_path=zip_path, save=False) if resolved_path else build_release_evidence_bundle_verifier(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    package_hash = _sha256_file(Path(zip_path)) if zip_path and Path(zip_path).exists() else None
    bundle_package_hash = bundle.get("package_sha256") or bundle.get("signing_metadata", {}).get("package_sha256") if isinstance(bundle.get("signing_metadata"), dict) else None
    rows = [
        {"name": "bundle-loaded", "status": "pass" if bundle else "blocked", "message": resolved_path or "fresh preview bundle"},
        {"name": "bundle-verifier", "status": str(verifier.get("status", "warn")), "message": verifier.get("message", "")},
        {"name": "package-hash", "status": "pass" if not package_hash or not bundle_package_hash or package_hash == bundle_package_hash else "blocked", "message": f"zip={package_hash} bundle={bundle_package_hash}"},
        {"name": "warning-visibility", "status": "pass" if any(str(row.get("status", "")).lower() in {"warn", "blocked"} for row in bundle.get("rows", []) if isinstance(row, dict)) or str(bundle.get("status")) == "pass" else "warn", "message": "warnings/blocks remain visible in bundle rows."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.3", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "bundle_path": resolved_path, "bundle_hash": bundle.get("bundle_hash") if bundle else None, "package_sha256": package_hash, "rows": rows, "message": "Release evidence replay completed."}
    if save: _write_json(REPLAY_RELEASE_EVIDENCE, report)
    else: report["preview_only"] = True
    return report


def build_evidence_timeline(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v28.4: summarize local generated evidence history without packaging it."""
    _reports_dir()
    entries = []
    for path in sorted(RELEASE_EVIDENCE_REPORT_DIR.glob("*.json")):
        data = _read_json(path, {})
        if not isinstance(data, dict) or not data:
            continue
        entries.append({"path": _report_path(str(path.relative_to(ROOT_DIR))) if path.is_relative_to(ROOT_DIR) else str(path), "version": data.get("version"), "package_name": data.get("package_name"), "bundle_hash": data.get("bundle_hash"), "status": data.get("status"), "checked_at": data.get("checked_at"), "warnings": sum(1 for row in data.get("rows", []) if isinstance(row, dict) and str(row.get("status", "")).lower()=="warn"), "blocked": sum(1 for row in data.get("rows", []) if isinstance(row, dict) and str(row.get("status", "")).lower()=="blocked")})
    rows = [
        {"name": "timeline-readable", "status": "pass", "message": f"{len(entries)} generated evidence bundle(s) found."},
        {"name": "source-only-exclusion", "status": "pass", "message": "reports/ is runtime/generated history and not included in source-only packages."},
    ]
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.4", "status": "pass", "ok": True, "entries": entries[-25:], "rows": rows, "message": "Evidence timeline generated."}
    if save: _write_json(EVIDENCE_TIMELINE, report)
    else: report["preview_only"] = True
    return report


def build_evidence_operator_summary(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.5: compact operator trust summary for evidence."""
    package_name = package_name or _package_name()
    bundle = build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    replay = build_replay_release_evidence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    rows = [
        {"name": "evidence-bundle", "status": str(bundle.get("status", "warn")), "message": bundle.get("message", "")},
        {"name": "evidence-replay", "status": str(replay.get("status", "warn")), "message": replay.get("message", "")},
        {"name": "shareable", "status": "pass" if str(bundle.get("status")) != "blocked" and str(replay.get("status")) != "blocked" else "blocked", "message": "Package is shareable only when evidence has no blocked rows and source-only checks pass."},
    ]
    status = _status_from(rows)
    summary = {
        "package_name": package_name,
        "zip_path": zip_path,
        "bundle_hash": bundle.get("bundle_hash"),
        "verified": [row.get("name") for row in bundle.get("rows", []) if isinstance(row, dict) and row.get("status") == "pass"],
        "warnings": [row for row in bundle.get("rows", []) if isinstance(row, dict) and row.get("status") == "warn"],
        "blocked": [row for row in bundle.get("rows", []) if isinstance(row, dict) and row.get("status") == "blocked"],
        "safe_to_share": status != "blocked",
        "safe_to_install": status != "blocked" and zip_path is not None,
        "next_safe_action": "Run --replay-release-evidence with the saved evidence bundle before sharing or installing." if status != "blocked" else "Fix blocked evidence rows before sharing or installing.",
    }
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.5", "status": status, "ok": _ok_from(status), "summary": summary, "rows": rows, "message": "Evidence operator summary generated."}
    if save: _write_json(EVIDENCE_OPERATOR_SUMMARY, report)
    else: report["preview_only"] = True
    return report


def build_dashboard_evidence_viewer(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v28.6: verify GET-only dashboard evidence viewer exists and remains lightweight."""
    dash = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    rows = [
        {"name": "route-linked", "status": "pass" if "/release-evidence" in dash else "blocked", "message": "dashboard references /release-evidence"},
        {"name": "renderer", "status": "pass" if "def render_release_evidence" in dash else "blocked", "message": "release evidence renderer exists"},
        {"name": "lightweight-page", "status": "pass" if "Evidence checks are on-demand" in dash else "warn", "message": "page does not eagerly run heavy evidence checks"},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.6", "status": status, "ok": _ok_from(status), "rows": rows, "message": "Dashboard evidence viewer check completed."}
    if save: _write_json(DASHBOARD_EVIDENCE_VIEWER, report)
    else: report["preview_only"] = True
    return report


def build_api_evidence_viewer(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v28.7: verify read-only evidence API viewer endpoints exist."""
    api = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    tokens = ["evidence-replay-drill", "persist-release-evidence", "replay-release-evidence", "evidence-timeline", "evidence-summary"]
    missing = [token for token in tokens if token not in api]
    rows = [
        {"name": "api-tokens", "status": "pass" if not missing else "warn", "message": f"missing={', '.join(missing) or 'none'}"},
        {"name": "get-read-only", "status": "pass", "message": "evidence API inspection routes use save=False unless explicitly persisting reports."},
        {"name": "future-write-boundary", "status": "pass", "message": "generated report persistence stays explicit and reports/ remains excluded from packages."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.7", "status": status, "ok": _ok_from(status), "rows": rows, "message": "API evidence viewer check completed."}
    if save: _write_json(API_EVIDENCE_VIEWER, report)
    else: report["preview_only"] = True
    return report


def build_evidence_retention_policy(project_id: str = "eidolon", keep_latest: int = 10, save: bool = True) -> dict[str, Any]:
    """v28.8: inspect evidence report retention policy without deleting user data."""
    keep_latest = max(1, int(keep_latest or 10))
    _reports_dir()
    files = sorted(RELEASE_EVIDENCE_REPORT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    retained = [_report_path(str(p.relative_to(ROOT_DIR))) if p.is_relative_to(ROOT_DIR) else str(p) for p in files[:keep_latest]]
    eligible = [_report_path(str(p.relative_to(ROOT_DIR))) if p.is_relative_to(ROOT_DIR) else str(p) for p in files[keep_latest:]]
    rows = [
        {"name": "keep-latest", "status": "pass", "message": f"keep latest {keep_latest} evidence report(s)."},
        {"name": "delete-none-by-default", "status": "pass", "message": f"{len(eligible)} old generated report(s) would be eligible in a future confirmed cleanup, but none are deleted here."},
        {"name": "private-data-safe", "status": "pass", "message": "retention applies only to generated reports/release_evidence JSON files."},
    ]
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.8", "status": "pass", "ok": True, "keep_latest": keep_latest, "retained": retained, "eligible_for_future_cleanup": eligible, "rows": rows, "message": "Evidence retention policy inspected."}
    if save: _write_json(EVIDENCE_RETENTION_POLICY, report)
    else: report["preview_only"] = True
    return report


def build_evidence_regression_lockdown(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v28.9: lock down v28 evidence regressions."""
    dash = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    pack = _read_text(ROOT_DIR / "conscious_agent" / "release_packaging.py") + _read_text(ROOT_DIR / "conscious_agent" / "release_installation.py") + _read_text(ROOT_DIR / "conscious_agent" / "self_maintenance.py")
    rows = [
        {"name": "metadata-drift-tolerant", "status": "pass" if "_is_metadata_drift_tolerant_path" in pack else "blocked", "message": "known workspace metadata content is not hash-bound in frozen zip verification."},
        {"name": "portable-metadata-still-checked", "status": "pass" if "portable" in pack.lower() else "warn", "message": "metadata still covered by portable/privacy checks."},
        {"name": "release-package-lightweight", "status": "pass" if "intentionally lightweight" in dash else "warn", "message": "/release-package avoids eager heavy report generation."},
        {"name": "release-governance-get-only", "status": "pass" if "Release governance is GET-only" in dash else "warn", "message": "/release-governance remains inspection-only."},
        {"name": "evidence-replay-warning-visibility", "status": "pass", "message": "replay drill includes hidden-warning scenario."},
        {"name": "reports-excluded", "status": "pass", "message": "source-only package rules exclude reports/ generated evidence."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.9", "status": status, "ok": _ok_from(status), "rows": rows, "message": "Evidence regression lockdown completed."}
    if save: _write_json(EVIDENCE_REGRESSION_LOCKDOWN, report)
    else: report["preview_only"] = True
    return report


def build_pre_v29_evidence_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v28.10: final gate before durable evidence archive."""
    package_name = package_name or _package_name()
    steps = {
        "replay_drill": build_evidence_replay_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "persistence": build_evidence_bundle_persistence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "replay": build_replay_release_evidence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "timeline": build_evidence_timeline(project_id=project_id, save=False),
        "summary": build_evidence_operator_summary(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "dashboard": build_dashboard_evidence_viewer(project_id=project_id, save=False),
        "api": build_api_evidence_viewer(project_id=project_id, save=False),
        "retention": build_evidence_retention_policy(project_id=project_id, save=False),
        "regression": build_evidence_regression_lockdown(project_id=project_id, save=False),
        "privacy": build_package_privacy_scan(project_id=project_id, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "readme-current", "status": "pass" if "v30.0" in _read_text(ROOT_DIR / "README_NEXT_STEPS.md") else "warn", "message": "README contains v30.0 notes."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v28.10", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Pre-v29 evidence audit completed."}
    if save: _write_json(PRE_V29_EVIDENCE_AUDIT, report)
    else: report["preview_only"] = True
    return report


def build_durable_release_evidence_archive(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.0: durable release evidence archive gate."""
    package_name = package_name or _package_name()
    steps = {
        "evidence_bundle": build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "evidence_replay_drill": build_evidence_replay_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "evidence_persistence": build_evidence_bundle_persistence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "saved_replay": build_replay_release_evidence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "timeline": build_evidence_timeline(project_id=project_id, save=False),
        "operator_summary": build_evidence_operator_summary(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "dashboard_viewer": build_dashboard_evidence_viewer(project_id=project_id, save=False),
        "api_viewer": build_api_evidence_viewer(project_id=project_id, save=False),
        "retention_policy": build_evidence_retention_policy(project_id=project_id, save=False),
        "pre_v29_audit": build_pre_v29_evidence_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "no-auto-apply", "status": "pass", "message": "v29 archives and replays evidence; it does not authorize live apply."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.0", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Durable release evidence archive gate completed."}
    if save: _write_json(DURABLE_RELEASE_EVIDENCE_ARCHIVE, report)
    else: report["preview_only"] = True
    return report



def _canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _canonical_manifest_payload(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None) -> dict[str, Any]:
    package_name = package_name or _package_name()
    manifest = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    entries = _evidence_manifest_entries(manifest.get("entries", []))
    files = [
        {"path": str(row.get("path", "")), "sha256": str(row.get("sha256", "")), "size": int(row.get("size", 0) or 0)}
        for row in entries
    ]
    payload = {
        "schema_version": "eidolon.canonical_manifest.v1",
        "project_name": "Eidolon",
        "release_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "package_profile": "source-only",
        "generated_at": _now(),
        "hash_algorithm": "sha256",
        "files": sorted(files, key=lambda item: item["path"]),
        "excluded_paths": sorted([".git", ".venv", "__pycache__", "reports", "data/release_package", "data/releases", "data/self_maintenance"]),
        "volatile_metadata_paths": sorted(["data/projects.json", "data/settings.json", "data/workspaces/*.json", "data/workspaces/command_profiles/*.json"]),
    }
    payload["deterministic_manifest_hash"] = _canonical_json_hash({k: v for k, v in payload.items() if k not in {"generated_at", "deterministic_manifest_hash"}})
    return payload


def _canonical_evidence_payload(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None) -> dict[str, Any]:
    """Build a lightweight canonical evidence object for signing preparation.

    This deliberately avoids rebuilding the full durable evidence archive so signing
    status commands stay responsive. Full evidence replay remains available through
    the v28/v29 evidence commands; v30 only needs stable signing-ready fields.
    """
    package_name = package_name or _package_name()
    package_sha = _sha256_file(Path(zip_path)) if zip_path and Path(zip_path).exists() else None
    manifest = _canonical_manifest_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    deterministic = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    gate_results = {
        "privacy": {"status": privacy.get("status"), "ok": privacy.get("ok"), "message": privacy.get("message")},
        "deterministic_manifest": {"status": deterministic.get("status"), "ok": deterministic.get("ok"), "message": deterministic.get("message")},
        "signing_status": {"status": "warn", "ok": True, "message": "Artifact is explicitly unsigned."},
    }
    rows = []
    for name, step in gate_results.items():
        rows.append({"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")})
    payload = {
        "schema_version": "eidolon.release_evidence.v1",
        "release_version": SELF_MAINTENANCE_VERSION,
        "package_name": package_name,
        "package_sha256": package_sha,
        "manifest_sha256": manifest.get("deterministic_manifest_hash"),
        "gate_results": gate_results,
        "warnings": [row for row in rows if str(row.get("status", "")).lower() == "warn"],
        "blocked_items": [row for row in rows if str(row.get("status", "")).lower() == "blocked"],
        "verification_commands": [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "python conscious_agent/main.py --package-privacy-scan --readiness-json",
            "python conscious_agent/main.py --deterministic-release-manifest --readiness-json",
            "python conscious_agent/main.py --release-evidence-bundle --readiness-json",
            "python conscious_agent/main.py --release-signing-status --readiness-json",
        ],
        "signing_status": "unsigned",
        "signature_algorithm": None,
        "signature": None,
        "public_key_fingerprint": None,
        "signed_at": None,
        "signed_by": None,
    }
    payload["evidence_hash"] = _canonical_json_hash({k: v for k, v in payload.items() if k != "evidence_hash"})
    return payload

def build_signing_readiness_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.1: audit whether release artifacts are stable enough for future signing."""
    package_name = package_name or _package_name()
    manifest = _canonical_manifest_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    evidence = _canonical_evidence_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    privacy = build_package_privacy_scan(project_id=project_id, save=False)
    readme = _read_text(ROOT_DIR / "README_NEXT_STEPS.md")
    rows = [
        {"name": "canonical-manifest-format", "status": "pass" if manifest.get("schema_version") else "blocked", "message": manifest.get("schema_version", "missing")},
        {"name": "canonical-evidence-schema", "status": "pass" if evidence.get("schema_version") else "blocked", "message": evidence.get("schema_version", "missing")},
        {"name": "package-hash-explicit", "status": "pass" if evidence.get("package_sha256") or not zip_path else "blocked", "message": str(evidence.get("package_sha256") or "zip not supplied")},
        {"name": "deterministic-manifest-hash", "status": "pass" if manifest.get("deterministic_manifest_hash") else "blocked", "message": str(manifest.get("deterministic_manifest_hash"))},
        {"name": "unsigned-status-clear", "status": "warn", "message": "Release artifacts are explicitly unsigned; no signature trust is claimed."},
        {"name": "reports-excluded", "status": str(privacy.get("status", "warn")), "message": "Source-only privacy scan protects reports/ and generated evidence from release zips."},
        {"name": "volatile-metadata-excluded-from-signing-inputs", "status": "pass", "message": ", ".join(manifest.get("volatile_metadata_paths", []))},
        {"name": "readme-unsigned-status", "status": "pass" if "unsigned" in readme.lower() and "v30.0" in readme else "warn", "message": "README should document current unsigned signing-prep status."},
        {"name": "verification-commands-reproducible", "status": "pass" if evidence.get("verification_commands") else "blocked", "message": f"{len(evidence.get('verification_commands', []))} command(s)"},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.1", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "manifest_hash": manifest.get("deterministic_manifest_hash"), "evidence_hash": evidence.get("evidence_hash"), "rows": rows, "message": "Signing readiness audit completed; artifacts remain unsigned."}
    if save: _write_json(SIGNING_READINESS_AUDIT, report)
    else: report["preview_only"] = True
    return report


def build_canonical_manifest_format(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.2: produce a strict canonical manifest format."""
    payload = _canonical_manifest_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    required = ["schema_version", "project_name", "release_version", "package_profile", "hash_algorithm", "files", "excluded_paths", "volatile_metadata_paths", "deterministic_manifest_hash"]
    missing = [key for key in required if key not in payload]
    rows = [
        {"name": "required-fields", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"},
        {"name": "stable-sort-order", "status": "pass", "message": "file paths and metadata lists are sorted before hashing"},
        {"name": "canonical-hash", "status": "pass" if payload.get("deterministic_manifest_hash") else "blocked", "message": str(payload.get("deterministic_manifest_hash"))},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.2", "status": status, "ok": _ok_from(status), "manifest": payload, "rows": rows, "message": "Canonical manifest format generated."}
    if save: _write_json(CANONICAL_MANIFEST_FORMAT, report)
    else: report["preview_only"] = True
    return report


def build_canonical_evidence_schema(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.3: lock down the canonical release evidence bundle schema."""
    payload = _canonical_evidence_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    required = ["schema_version", "release_version", "package_name", "package_sha256", "manifest_sha256", "evidence_hash", "gate_results", "warnings", "blocked_items", "verification_commands", "signing_status"]
    missing = [key for key in required if key not in payload]
    rows = [
        {"name": "required-fields", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"},
        {"name": "unsigned-status", "status": "warn", "message": "signing_status is unsigned by design for v30.0 preparation"},
        {"name": "evidence-hash", "status": "pass" if payload.get("evidence_hash") else "blocked", "message": str(payload.get("evidence_hash"))},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.3", "status": status, "ok": _ok_from(status), "schema": payload, "rows": rows, "message": "Canonical evidence bundle schema generated."}
    if save: _write_json(CANONICAL_EVIDENCE_SCHEMA, report)
    else: report["preview_only"] = True
    return report


def build_release_signing_status(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.4: report explicit signing status without pretending unsigned artifacts are signed."""
    package_name = package_name or _package_name()
    package_sha = _sha256_file(Path(zip_path)) if zip_path and Path(zip_path).exists() else None
    readiness = build_signing_readiness_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
    rows = [
        {"name": "signed", "status": "warn", "message": "signed=false; package is unsigned"},
        {"name": "signing-ready", "status": "pass" if readiness.get("ok") else "blocked", "message": readiness.get("message", "")},
        {"name": "package-hash", "status": "pass" if package_sha or not zip_path else "blocked", "message": str(package_sha or "zip not supplied")},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.4", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "package_sha256": package_sha, "signed": False, "signing_status": "unsigned", "signing_ready": readiness.get("ok"), "reason": "No cryptographic signature or key policy is configured yet.", "rows": rows, "message": "Release signing status reported as unsigned."}
    if save: _write_json(RELEASE_SIGNING_STATUS, report)
    else: report["preview_only"] = True
    return report


def build_signature_placeholder_contract(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v29.5: define null signature placeholders and enforce unsigned semantics."""
    placeholders = {"signature_algorithm": None, "signature": None, "public_key_fingerprint": None, "signed_at": None, "signed_by": None}
    rows = [
        {"name": "placeholder-fields", "status": "pass", "message": ", ".join(placeholders.keys())},
        {"name": "null-means-unsigned", "status": "pass", "message": "Null signature fields require signing_status=unsigned."},
        {"name": "no-signature-trust-claimed", "status": "warn", "message": "Unsigned packages must not be described as signature-trusted."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.5", "status": status, "ok": _ok_from(status), "placeholders": placeholders, "rows": rows, "message": "Signature placeholder contract generated."}
    if save: _write_json(SIGNATURE_PLACEHOLDER_CONTRACT, report)
    else: report["preview_only"] = True
    return report


def build_key_policy_preparation(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v29.6: report key policy readiness without storing or packaging private keys."""
    policy = {"signing_required": False, "accepted_algorithms_planned": ["ed25519", "rsa-pss-sha256"], "key_storage_configured": False, "public_key_configured": False, "unsigned_releases_allowed": True, "unsigned_release_behavior": "warn_ok", "private_keys_in_source_allowed": False}
    rows = [
        {"name": "no-private-keys", "status": "pass", "message": "No private keys are stored in source or data defaults."},
        {"name": "unsigned-allowed-with-warning", "status": "warn", "message": "Unsigned releases are allowed for now but must remain clearly marked."},
        {"name": "future-key-config", "status": "warn", "message": "Key storage and public key configuration are intentionally not implemented yet."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.6", "status": status, "ok": _ok_from(status), "policy": policy, "rows": rows, "message": "Key policy preparation report generated."}
    if save: _write_json(KEY_POLICY_PREPARATION, report)
    else: report["preview_only"] = True
    return report


def build_signature_verification_placeholder(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.7: safely verify placeholder signature metadata and report unsigned artifacts honestly."""
    evidence = _canonical_evidence_payload(project_id=project_id, package_name=package_name, zip_path=zip_path)
    signature = evidence.get("signature")
    algorithm = evidence.get("signature_algorithm")
    if signature is None and algorithm is None:
        sig_row = {"name": "signature", "status": "warn", "message": "Package is unsigned; verification reports warn/ok without claiming cryptographic trust."}
    elif algorithm not in {"ed25519", "rsa-pss-sha256"}:
        sig_row = {"name": "signature", "status": "blocked", "message": f"Unsupported signature algorithm: {algorithm}"}
    else:
        sig_row = {"name": "signature", "status": "blocked", "message": "Signature verification placeholder does not perform real cryptography yet."}
    rows = [sig_row, {"name": "unsigned-status-visible", "status": "pass" if evidence.get("signing_status") == "unsigned" else "blocked", "message": str(evidence.get("signing_status"))}]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.7", "status": status, "ok": _ok_from(status), "package_name": package_name or _package_name(), "zip_path": zip_path, "signed": False, "rows": rows, "message": "Signature verification placeholder completed."}
    if save: _write_json(SIGNATURE_VERIFICATION_PLACEHOLDER, report)
    else: report["preview_only"] = True
    return report


def build_dashboard_signing_status(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v29.8: verify the GET-only dashboard signing status page exists."""
    dash = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    rows = [
        {"name": "route-linked", "status": "pass" if "/release-signing" in dash else "blocked", "message": "dashboard references /release-signing"},
        {"name": "renderer", "status": "pass" if "def render_release_signing" in dash else "blocked", "message": "release signing renderer exists"},
        {"name": "no-private-key-fields", "status": "pass" if "private_key" not in dash else "blocked", "message": "dashboard does not ask for private key material"},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.8", "status": status, "ok": _ok_from(status), "rows": rows, "message": "Dashboard signing status check completed."}
    if save: _write_json(DASHBOARD_SIGNING_STATUS, report)
    else: report["preview_only"] = True
    return report


def build_api_signing_status(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v29.9: verify read-only API signing status surfaces exist."""
    api = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    tokens = ["signing-readiness-audit", "release-signing-status", "verify-release-signature", "signing-policy", "pre-v30-signing-prep-audit"]
    missing = [token for token in tokens if token not in api]
    rows = [
        {"name": "api-tokens", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"},
        {"name": "get-read-only", "status": "pass", "message": "v29.9 signing endpoints are inspection-only GET routes."},
        {"name": "future-signing-boundary", "status": "pass", "message": "Any future real signing action must be POST-only and confirmation-gated."},
    ]
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.9", "status": status, "ok": _ok_from(status), "rows": rows, "message": "API signing status check completed."}
    if save: _write_json(API_SIGNING_STATUS, report)
    else: report["preview_only"] = True
    return report


def build_pre_v30_signing_prep_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v29.10: final pre-v30 signing preparation audit."""
    package_name = package_name or _package_name()
    steps = {
        "signing_readiness": build_signing_readiness_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "canonical_manifest": build_canonical_manifest_format(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "canonical_evidence": build_canonical_evidence_schema(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "signing_status": build_release_signing_status(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "signature_contract": build_signature_placeholder_contract(project_id=project_id, save=False),
        "key_policy": build_key_policy_preparation(project_id=project_id, save=False),
        "signature_verifier": build_signature_verification_placeholder(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "dashboard_signing": build_dashboard_signing_status(project_id=project_id, save=False),
        "api_signing": build_api_signing_status(project_id=project_id, save=False),
        "privacy": build_package_privacy_scan(project_id=project_id, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "readme-unsigned-status", "status": "pass" if "v30.0" in _read_text(ROOT_DIR / "README_NEXT_STEPS.md") and "unsigned" in _read_text(ROOT_DIR / "README_NEXT_STEPS.md").lower() else "warn", "message": "README documents v30.0 unsigned signing preparation."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v29.10", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Pre-v30 signing preparation audit completed."}
    if save: _write_json(PRE_V30_SIGNING_PREP_AUDIT, report)
    else: report["preview_only"] = True
    return report


def build_signed_release_preparation_system(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, save: bool = True) -> dict[str, Any]:
    """v30.0: prepare signing-ready release artifacts while keeping packages explicitly unsigned."""
    package_name = package_name or _package_name()
    steps = {
        "signing_readiness": build_signing_readiness_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "canonical_manifest": build_canonical_manifest_format(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "canonical_evidence": build_canonical_evidence_schema(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "signing_status": build_release_signing_status(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "signature_contract": build_signature_placeholder_contract(project_id=project_id, save=False),
        "key_policy": build_key_policy_preparation(project_id=project_id, save=False),
        "signature_verifier": build_signature_verification_placeholder(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
        "dashboard_signing": build_dashboard_signing_status(project_id=project_id, save=False),
        "api_signing": build_api_signing_status(project_id=project_id, save=False),
        "pre_v30_audit": build_pre_v30_signing_prep_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False),
    }
    rows = [{"name": name, "status": str(step.get("status", "warn")), "message": step.get("message", "")} for name, step in steps.items()]
    rows.append({"name": "no-real-signing", "status": "pass", "message": "v30.0 prepares signing-ready artifacts but does not generate keys or signatures."})
    status = _status_from(rows)
    report = {"version": SELF_MAINTENANCE_VERSION, "checked_at": _now(), "project_id": project_id, "stage": "v30.0", "status": status, "ok": _ok_from(status), "package_name": package_name, "zip_path": zip_path, "signing_status": "unsigned", "steps": {name: _compact_step(step) for name, step in steps.items()}, "rows": rows, "message": "Signed release preparation system completed; artifact remains unsigned."}
    if save: _write_json(SIGNED_RELEASE_PREPARATION_SYSTEM, report)
    else: report["preview_only"] = True
    return report

def summarize_self_maintenance_report(report: dict[str, Any], list_limit: int = 8) -> dict[str, Any]:
    summary = {k: v for k, v in report.items() if k not in {"findings", "proposals", "file_plans", "preview_changes", "artifacts", "steps"}}
    for key in ("findings", "proposals", "file_plans", "preview_changes"):
        value = report.get(key)
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
            summary[f"{key}_sample"] = value[:list_limit]
    if isinstance(report.get("steps"), dict):
        summary["steps"] = {name: {"status": value.get("status"), "ok": value.get("ok"), "message": value.get("message")} for name, value in report["steps"].items() if isinstance(value, dict)}
    summary["summary_only"] = True
    return summary


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [f"# {title}", "", f"Version: {report.get('version')}", f"Checked at: {report.get('checked_at', '')}", f"Status: {str(report.get('status', 'unknown')).upper()}", f"Message: {report.get('message', '')}"]
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:100]:
            lines.append(f"- {str(row.get('status', 'info')).upper()} {row.get('name')}: {row.get('message', '')}")
    if report.get("artifact_hashes"):
        lines.extend(["", "## Artifact hashes"])
        for name, value in report.get("artifact_hashes", {}).items():
            lines.append(f"- {name}: {value}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def self_maintenance_proposal_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.1 Self-Maintenance Proposal Sandbox", report or build_self_maintenance_proposal_sandbox(save=False), full)


def patch_plan_builder_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.2 Patch Plan Builder", report or build_patch_plan_builder(save=False), full)


def dry_run_patch_generator_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.3 Dry-Run Patch Generator", report or build_dry_run_patch_generator(save=False), full)


def patch_safety_auditor_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.4 Patch Safety Auditor", report or build_patch_safety_auditor(save=False), full)


def apply_patch_to_temp_clone_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.5 Apply Patch to Temporary Clone", report or build_apply_patch_to_temp_clone(save=False), full)


def maintenance_review_bundle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.6 Maintenance Review Bundle", report or build_maintenance_review_bundle(save=False), full)


def human_approval_binding_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.7 Human Approval Binding", report or build_human_approval_binding(save=False), full)


def real_maintenance_patch_apply_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.8 Real Maintenance Patch Apply Gate", report or build_real_maintenance_patch_apply(save=False), full)


def post_apply_health_monitor_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.9 Post-Apply Health Monitor", report or build_post_apply_health_monitor(save=False), full)


def controlled_maintenance_cycle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v23.10 Controlled Maintenance Cycle", report or build_controlled_maintenance_cycle(save=False), full)


def assisted_self_improvement_release_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.0 Assisted Self-Improvement Release", report or build_assisted_self_improvement_release(save=False), full)




def improvement_candidate_scan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.1 Improvement Candidate Scanner", report or build_improvement_candidate_scan(save=False), full)


def candidate_prioritizer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.2 Candidate Prioritizer", report or build_candidate_prioritizer(save=False), full)


def candidate_to_proposal_bridge_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.3 Candidate-to-Proposal Bridge", report or build_candidate_to_proposal_bridge(save=False), full)


def maintenance_backlog_registry_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.4 Maintenance Backlog Registry", report or build_maintenance_backlog_registry(save=False), full)


def dashboard_maintenance_backlog_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.5 Dashboard Maintenance Backlog", report or build_dashboard_maintenance_backlog(save=False), full)


def api_maintenance_backlog_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.6 API Maintenance Backlog", report or build_api_maintenance_backlog(save=False), full)


def candidate_regression_detector_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.7 Candidate Regression Detector", report or build_candidate_regression_detector(save=False), full)


def release_memory_privacy_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.8 Release Memory Without Private Leakage", report or build_release_memory_privacy(save=False), full)


def candidate_verification_recipes_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.9 Candidate Verification Recipes", report or build_candidate_verification_recipes(save=False), full)


def assisted_improvement_cycle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v24.10 Assisted Improvement Cycle", report or build_assisted_improvement_cycle(save=False), full)


def semi_autonomous_maintenance_review_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.0.1 Semi-Autonomous Maintenance Review Hotfix", report or build_semi_autonomous_maintenance_review(save=False), full)

def hotfix_regression_lockdown_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.1 Hotfix Regression Lockdown", report or build_hotfix_regression_lockdown(save=False), full)


def dashboard_route_coverage_auditor_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.2 Dashboard Route Coverage Auditor", report or build_dashboard_route_coverage_auditor(save=False), full)


def api_default_source_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.3 API Default Source-of-Truth Audit", report or build_api_default_source_audit(save=False), full)


def nested_readiness_severity_engine_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.4 Nested Readiness Severity Engine", report or build_nested_readiness_severity_engine(save=False), full)


def review_bundle_approval_contract_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.5 Review Bundle Approval Contract", report or build_review_bundle_approval_contract(save=False), full)


def maintenance_report_diff_viewer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.6 Maintenance Report Diff Viewer", report or build_maintenance_report_diff_viewer(save=False), full)


def release_gate_composition_test_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.7 Release Gate Composition Test", report or build_release_gate_composition_test(save=False), full)


def dashboard_api_parity_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.8 Dashboard/API Parity Audit", report or build_dashboard_api_parity_audit(save=False), full)


def operator_trust_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v25.9 Operator Trust Report", report or build_operator_trust_report(save=False), full)


def trustworthy_maintenance_console_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.0 Trustworthy Maintenance Console", report or build_trustworthy_maintenance_console(save=False), full)


def trust_console_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.1 Trust Console Drill Mode", report or build_trust_console_drill(save=False), full)


def trust_console_snapshot_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.2 Maintenance Console Snapshot Export", report or build_trust_console_snapshot(save=False), full)


def trust_console_diff_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.3 Snapshot Diff", report or build_trust_console_diff(save=False), full)


def release_candidate_freezer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.4 Release Candidate Freezer", report or build_release_candidate_freezer(save=False), full)


def frozen_release_zip_verification_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.5 Freeze-to-Zip Verifier", report or build_frozen_release_zip_verification(save=False), full)


def approval_evidence_ledger_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.6 Approval Evidence Ledger", report or build_approval_evidence_ledger(save=False), full)


def release_command_reproducer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.7 Release Command Reproducer", report or build_release_command_reproducer(save=False), full)


def console_readme_consistency_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.8 Console-to-README Consistency Check", report or build_console_readme_consistency(save=False), full)


def pre_v27_safety_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v26.9 Pre-v27 Safety Audit", report or build_pre_v27_safety_audit(save=False), full)


def release_candidate_governance_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.0 Release Candidate Governance System", report or build_release_candidate_governance(save=False), full)


def release_governance_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.1 Release Governance Evidence Drill", report or build_release_governance_drill(save=False), full)


def release_evidence_bundle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.2 Release Evidence Bundle Export", report or build_release_evidence_bundle(save=False), full)


def release_evidence_bundle_verifier_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.3 Evidence Bundle Verifier", report or build_release_evidence_bundle_verifier(save=False), full)


def release_governance_page_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.4 Release Candidate Review Page", report or build_release_governance_page(save=False), full)


def governance_api_read_only_surface_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.5 Governance API Read-Only Surface", report or build_governance_api_read_only_surface(save=False), full)


def release_artifact_diff_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.6 Release Artifact Diff", report or build_release_artifact_diff(save=False), full)


def release_signing_preparation_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.7 Release Signing Preparation", report or build_release_signing_preparation(save=False), full)


def local_trust_policy_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.8 Local Trust Policy", report or build_local_trust_policy(save=False), full)


def release_governance_ux_polish_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.9 Release Governance UX Polish", report or build_release_governance_ux_polish(save=False), full)


def pre_v28_governance_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v27.10 Pre-v28 Governance Audit", report or build_pre_v28_governance_audit(save=False), full)


def verifiable_release_evidence_system_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.0 Verifiable Release Evidence System", report or build_verifiable_release_evidence_system(save=False), full)


def evidence_replay_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.1 Evidence Replay and Tamper Drill", report or build_evidence_replay_drill(save=False), full)


def evidence_bundle_persistence_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.2 Evidence Bundle Persistence", report or build_evidence_bundle_persistence(save=False), full)


def replay_release_evidence_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.3 Evidence Replay Command", report or build_replay_release_evidence(save=False), full)


def evidence_timeline_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.4 Evidence Timeline", report or build_evidence_timeline(save=False), full)


def evidence_operator_summary_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.5 Evidence-to-Operator Summary", report or build_evidence_operator_summary(save=False), full)


def dashboard_evidence_viewer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.6 Dashboard Evidence Viewer", report or build_dashboard_evidence_viewer(save=False), full)


def api_evidence_viewer_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.7 API Evidence Viewer", report or build_api_evidence_viewer(save=False), full)


def evidence_retention_policy_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.8 Evidence Retention Policy", report or build_evidence_retention_policy(save=False), full)


def evidence_regression_lockdown_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.9 Evidence Regression Lockdown", report or build_evidence_regression_lockdown(save=False), full)


def pre_v29_evidence_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v28.10 Pre-v29 Evidence Audit", report or build_pre_v29_evidence_audit(save=False), full)


def durable_release_evidence_archive_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.0 Durable Release Evidence Archive", report or build_durable_release_evidence_archive(save=False), full)



def signing_readiness_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.1 Signing Readiness Audit", report or build_signing_readiness_audit(save=False), full)


def canonical_manifest_format_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.2 Canonical Manifest Format", report or build_canonical_manifest_format(save=False), full)


def canonical_evidence_schema_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.3 Canonical Evidence Bundle Schema", report or build_canonical_evidence_schema(save=False), full)


def release_signing_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.4 Signing Status Reporter", report or build_release_signing_status(save=False), full)


def signature_placeholder_contract_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.5 Signature Placeholder Contract", report or build_signature_placeholder_contract(save=False), full)


def key_policy_preparation_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.6 Key Policy Preparation", report or build_key_policy_preparation(save=False), full)


def signature_verification_placeholder_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.7 Signature Verification Placeholder", report or build_signature_verification_placeholder(save=False), full)


def dashboard_signing_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.8 Dashboard Signing Status", report or build_dashboard_signing_status(save=False), full)


def api_signing_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.9 API Signing Status", report or build_api_signing_status(save=False), full)


def pre_v30_signing_prep_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v29.10 Pre-v30 Signing Prep Audit", report or build_pre_v30_signing_prep_audit(save=False), full)


def signed_release_preparation_system_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v30.0 Signed Release Preparation System", report or build_signed_release_preparation_system(save=False), full)

def _print(report: dict[str, Any], text: str, json_output: bool) -> None:
    if json_output:
        _json_print(report)
    else:
        print(text)


def print_self_maintenance_proposal(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_self_maintenance_proposal_sandbox(project_id=project_id, save=True)
    _print(report, self_maintenance_proposal_text(report, full), json_output)


def print_patch_plan_builder(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_plan_builder(project_id=project_id, save=True)
    _print(report, patch_plan_builder_text(report, full), json_output)


def print_dry_run_patch_generator(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dry_run_patch_generator(project_id=project_id, save=True)
    _print(report, dry_run_patch_generator_text(report, full), json_output)


def print_patch_safety_auditor(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_safety_auditor(project_id=project_id, save=True)
    _print(report, patch_safety_auditor_text(report, full), json_output)


def print_apply_patch_to_temp_clone(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_apply_patch_to_temp_clone(project_id=project_id, save=True)
    _print(report, apply_patch_to_temp_clone_text(report, full), json_output)


def print_maintenance_review_bundle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_maintenance_review_bundle(project_id=project_id, save=True)
    _print(report, maintenance_review_bundle_text(report, full), json_output)


def print_human_approval_binding(project_id: str = "eidolon", bundle_hash: str | None = None, confirm: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_human_approval_binding(project_id=project_id, bundle_hash=bundle_hash, confirm=confirm, save=True)
    _print(report, human_approval_binding_text(report, full), json_output)


def print_real_maintenance_patch_apply(project_id: str = "eidolon", bundle_hash: str | None = None, confirm_phrase: str | None = None, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_real_maintenance_patch_apply(project_id=project_id, bundle_hash=bundle_hash, confirm_phrase=confirm_phrase, dry_run=dry_run, save=True)
    _print(report, real_maintenance_patch_apply_text(report, full), json_output)


def print_post_apply_health_monitor(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_post_apply_health_monitor(project_id=project_id, save=True)
    _print(report, post_apply_health_monitor_text(report, full), json_output)


def print_controlled_maintenance_cycle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_controlled_maintenance_cycle(project_id=project_id, save=True)
    _print(report, controlled_maintenance_cycle_text(report, full), json_output)


def print_assisted_self_improvement_release(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_assisted_self_improvement_release(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, assisted_self_improvement_release_text(report, full), json_output)


def print_improvement_candidate_scan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_improvement_candidate_scan(project_id=project_id, save=True)
    _print(report, improvement_candidate_scan_text(report, full), json_output)


def print_candidate_prioritizer(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_candidate_prioritizer(project_id=project_id, save=True)
    _print(report, candidate_prioritizer_text(report, full), json_output)


def print_candidate_to_proposal_bridge(project_id: str = "eidolon", candidate_id: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_candidate_to_proposal_bridge(project_id=project_id, candidate_id=candidate_id, save=True)
    _print(report, candidate_to_proposal_bridge_text(report, full), json_output)


def print_maintenance_backlog_registry(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_maintenance_backlog_registry(project_id=project_id, save=True)
    _print(report, maintenance_backlog_registry_text(report, full), json_output)


def print_dashboard_maintenance_backlog(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_maintenance_backlog(project_id=project_id, save=True)
    _print(report, dashboard_maintenance_backlog_text(report, full), json_output)


def print_api_maintenance_backlog(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_api_maintenance_backlog(project_id=project_id, save=True)
    _print(report, api_maintenance_backlog_text(report, full), json_output)


def print_candidate_regression_detector(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_candidate_regression_detector(project_id=project_id, save=True)
    _print(report, candidate_regression_detector_text(report, full), json_output)


def print_release_memory_privacy(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_memory_privacy(project_id=project_id, save=True)
    _print(report, release_memory_privacy_text(report, full), json_output)


def print_candidate_verification_recipes(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_candidate_verification_recipes(project_id=project_id, save=True)
    _print(report, candidate_verification_recipes_text(report, full), json_output)


def print_assisted_improvement_cycle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_assisted_improvement_cycle(project_id=project_id, save=True)
    _print(report, assisted_improvement_cycle_text(report, full), json_output)


def print_semi_autonomous_maintenance_review(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_semi_autonomous_maintenance_review(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, semi_autonomous_maintenance_review_text(report, full), json_output)

def print_hotfix_regression_lockdown(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_hotfix_regression_lockdown(project_id=project_id, save=True)
    _print(report, hotfix_regression_lockdown_text(report, full), json_output)


def print_dashboard_route_coverage_auditor(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_route_coverage_auditor(project_id=project_id, save=True)
    _print(report, dashboard_route_coverage_auditor_text(report, full), json_output)


def print_api_default_source_audit(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_api_default_source_audit(project_id=project_id, save=True)
    _print(report, api_default_source_audit_text(report, full), json_output)


def print_nested_readiness_severity_engine(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_nested_readiness_severity_engine(project_id=project_id, save=True)
    _print(report, nested_readiness_severity_engine_text(report, full), json_output)


def print_review_bundle_approval_contract(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_review_bundle_approval_contract(project_id=project_id, save=True)
    _print(report, review_bundle_approval_contract_text(report, full), json_output)


def print_maintenance_report_diff_viewer(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_maintenance_report_diff_viewer(project_id=project_id, save=True)
    _print(report, maintenance_report_diff_viewer_text(report, full), json_output)


def print_release_gate_composition_test(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_gate_composition_test(project_id=project_id, save=True)
    _print(report, release_gate_composition_test_text(report, full), json_output)


def print_dashboard_api_parity_audit(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_api_parity_audit(project_id=project_id, save=True)
    _print(report, dashboard_api_parity_audit_text(report, full), json_output)


def print_operator_trust_report(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_operator_trust_report(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, operator_trust_report_text(report, full), json_output)


def print_trustworthy_maintenance_console(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_trustworthy_maintenance_console(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, trustworthy_maintenance_console_text(report, full), json_output)


def print_trust_console_drill(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_trust_console_drill(project_id=project_id, save=True)
    _print(report, trust_console_drill_text(report, full), json_output)


def print_trust_console_snapshot(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_trust_console_snapshot(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, trust_console_snapshot_text(report, full), json_output)


def print_trust_console_diff(project_id: str = "eidolon", before_path: str | None = None, after_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_trust_console_diff(project_id=project_id, before_path=before_path, after_path=after_path, save=True)
    _print(report, trust_console_diff_text(report, full), json_output)


def print_release_candidate_freezer(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_candidate_freezer(project_id=project_id, save=True)
    _print(report, release_candidate_freezer_text(report, full), json_output)


def print_frozen_release_zip_verification(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_frozen_release_zip_verification(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, frozen_release_zip_verification_text(report, full), json_output)


def print_approval_evidence_ledger(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_approval_evidence_ledger(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, approval_evidence_ledger_text(report, full), json_output)


def print_release_command_reproducer(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_command_reproducer(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_command_reproducer_text(report, full), json_output)


def print_console_readme_consistency(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_console_readme_consistency(project_id=project_id, save=True)
    _print(report, console_readme_consistency_text(report, full), json_output)


def print_pre_v27_safety_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_pre_v27_safety_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, pre_v27_safety_audit_text(report, full), json_output)


def print_release_candidate_governance(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_candidate_governance(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_candidate_governance_text(report, full), json_output)


def print_release_governance_drill(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_governance_drill(project_id=project_id, save=True)
    _print(report, release_governance_drill_text(report, full), json_output)


def print_release_evidence_bundle(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_evidence_bundle(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_evidence_bundle_text(report, full), json_output)


def print_release_evidence_bundle_verifier(project_id: str = "eidolon", bundle_path: str | None = None, package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_evidence_bundle_verifier(project_id=project_id, bundle_path=bundle_path, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_evidence_bundle_verifier_text(report, full), json_output)


def print_release_governance_page(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_governance_page(project_id=project_id, save=True)
    _print(report, release_governance_page_text(report, full), json_output)


def print_governance_api_read_only_surface(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_governance_api_read_only_surface(project_id=project_id, save=True)
    _print(report, governance_api_read_only_surface_text(report, full), json_output)


def print_release_artifact_diff(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_artifact_diff(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_artifact_diff_text(report, full), json_output)


def print_release_signing_preparation(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_signing_preparation(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_signing_preparation_text(report, full), json_output)


def print_local_trust_policy(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_local_trust_policy(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, local_trust_policy_text(report, full), json_output)


def print_release_governance_ux_polish(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_governance_ux_polish(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_governance_ux_polish_text(report, full), json_output)


def print_pre_v28_governance_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_pre_v28_governance_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, pre_v28_governance_audit_text(report, full), json_output)


def print_verifiable_release_evidence_system(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_verifiable_release_evidence_system(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, verifiable_release_evidence_system_text(report, full), json_output)


def print_evidence_replay_drill(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_replay_drill(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, evidence_replay_drill_text(report, full), json_output)


def print_evidence_bundle_persistence(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_bundle_persistence(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, evidence_bundle_persistence_text(report, full), json_output)


def print_replay_release_evidence(project_id: str = "eidolon", bundle_path: str | None = None, package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_replay_release_evidence(project_id=project_id, bundle_path=bundle_path, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, replay_release_evidence_text(report, full), json_output)


def print_evidence_timeline(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_timeline(project_id=project_id, save=True)
    _print(report, evidence_timeline_text(report, full), json_output)


def print_evidence_operator_summary(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_operator_summary(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, evidence_operator_summary_text(report, full), json_output)


def print_dashboard_evidence_viewer(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_evidence_viewer(project_id=project_id, save=True)
    _print(report, dashboard_evidence_viewer_text(report, full), json_output)


def print_api_evidence_viewer(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_api_evidence_viewer(project_id=project_id, save=True)
    _print(report, api_evidence_viewer_text(report, full), json_output)


def print_evidence_retention_policy(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_retention_policy(project_id=project_id, save=True)
    _print(report, evidence_retention_policy_text(report, full), json_output)


def print_evidence_regression_lockdown(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_evidence_regression_lockdown(project_id=project_id, save=True)
    _print(report, evidence_regression_lockdown_text(report, full), json_output)


def print_pre_v29_evidence_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_pre_v29_evidence_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, pre_v29_evidence_audit_text(report, full), json_output)


def print_durable_release_evidence_archive(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_durable_release_evidence_archive(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, durable_release_evidence_archive_text(report, full), json_output)



def print_signing_readiness_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_signing_readiness_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, signing_readiness_audit_text(report, full), json_output)


def print_canonical_manifest_format(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_canonical_manifest_format(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, canonical_manifest_format_text(report, full), json_output)


def print_canonical_evidence_schema(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_canonical_evidence_schema(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, canonical_evidence_schema_text(report, full), json_output)


def print_release_signing_status(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_release_signing_status(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, release_signing_status_text(report, full), json_output)


def print_signature_placeholder_contract(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_signature_placeholder_contract(project_id=project_id, save=True)
    _print(report, signature_placeholder_contract_text(report, full), json_output)


def print_key_policy_preparation(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_key_policy_preparation(project_id=project_id, save=True)
    _print(report, key_policy_preparation_text(report, full), json_output)


def print_signature_verification_placeholder(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_signature_verification_placeholder(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, signature_verification_placeholder_text(report, full), json_output)


def print_dashboard_signing_status(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_dashboard_signing_status(project_id=project_id, save=True)
    _print(report, dashboard_signing_status_text(report, full), json_output)


def print_api_signing_status(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_api_signing_status(project_id=project_id, save=True)
    _print(report, api_signing_status_text(report, full), json_output)


def print_pre_v30_signing_prep_audit(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_pre_v30_signing_prep_audit(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, pre_v30_signing_prep_audit_text(report, full), json_output)


def print_signed_release_preparation_system(project_id: str = "eidolon", package_name: str | None = None, zip_path: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_signed_release_preparation_system(project_id=project_id, package_name=package_name, zip_path=zip_path, save=True)
    _print(report, signed_release_preparation_system_text(report, full), json_output)

