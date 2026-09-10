from __future__ import annotations

"""v1249 Feature Freeze and Final Hardening.

Read-only freeze evidence for the v1250 milestone. The module inventories stable
public surfaces, classifies proposed changes, and reports final hardening status.
It never edits source, invokes tools/providers, executes tests, or grants release
or execution authority.
"""

import ast
import copy
import hashlib
import html
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1249.8"
MILESTONE_NAME = "Feature Freeze and Final Hardening"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"

AUTHORITY_FLAGS = {
    "freeze_registry_inspection_authorized": True,
    "freeze_manifest_inspection_authorized": True,
    "hardening_report_inspection_authorized": True,
    "source_mutation_authorized": False,
    "interface_mutation_authorized": False,
    "feature_addition_authorized": False,
    "breaking_change_authorized": False,
    "provider_contact_authorized": False,
    "prompt_transmission_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "cognition_write_authorized": False,
    "message_send_authorized": False,
    "notification_send_authorized": False,
    "session_launch_authorized": False,
    "session_resume_authorized": False,
    "automatic_retry_authorized": False,
    "background_continuation_authorized": False,
    "approval_creation_authorized": False,
    "approval_consumption_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

FREEZE_DOMAINS = (
    "mind_and_cognition", "ordinary_conversation", "project_understanding",
    "initiative_and_proposals", "supervised_development", "provider_and_models",
    "installation_lifecycle", "privacy_and_secrets", "operator_dashboards",
    "checkpoint_registry", "release_verification", "source_only_packaging",
)
ALLOWED_CHANGE_CLASSES = (
    "defect_correction", "security_correction", "verification_correction",
    "documentation_correction", "compatibility_correction",
)
BLOCKED_CHANGE_CLASSES = (
    "new_feature", "scope_expansion", "breaking_interface",
    "authority_expansion", "unreviewed_dependency",
)
REVIEW_DECISIONS = ("accept_for_separate_work", "hold", "reject", "request_changes")

_REQUIRED_SURFACES: dict[str, tuple[str, ...]] = {
    "conscious_agent/release_metadata.py": (
        'WORKING_SOURCE_VERSION = "1249.9"',
        "v1249.9 Feature Freeze and Final Hardening Checkpoint",
        "v1250.0-v1250.2 Desktop Codex Integrated Beta Milestone Foundations",
    ),
    "conscious_agent/ordinary_chat_development_campaign.py": (
        "process_feature_freeze_final_hardening_control",
    ),
    "conscious_agent/api_server.py": (
        "feature-freeze-registry", "feature-freeze-manifest",
        "feature-freeze-final-hardening-report", "feature-freeze-final-hardening-checkpoint",
    ),
    "conscious_agent/dashboard.py": (
        "/feature-freeze-final-hardening", "/api/feature-freeze-final-hardening",
    ),
    "conscious_agent/unified_operator_dashboard.py": (
        "feature-freeze-final-hardening",
    ),
    "eidolon.py": (
        '"feature-freeze-registry"', '"feature-freeze-manifest"',
        '"feature-freeze-final-hardening-report"', '"feature-freeze-final-hardening-checkpoint"',
    ),
    "tools/release_verify.py": (
        "v1249.2-feature-freeze-final-hardening-foundations",
        "v1249.5-feature-freeze-review-and-interface-stability",
        "v1249.8-feature-freeze-adversarial-reliability",
        "v1249.9-feature-freeze-final-hardening-checkpoint",
    ),
    "README_NEXT_STEPS.md": ("v1249.9", "v1250.0-v1250.2"),
    "README_RELEASE_HISTORY.md": ("v1249.9 Feature Freeze and Final Hardening",),
}

_SHOW_REGISTRY = re.compile(r"^show feature freeze registry[.!?]*$", re.I)
_SHOW_MANIFEST = re.compile(r"^show feature freeze manifest[.!?]*$", re.I)
_SHOW_REPORT = re.compile(r"^show feature freeze(?: and)? final hardening report[.!?]*$", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _base() -> dict[str, Any]:
    return {
        "content_free": True, "read_only": True, "historical_records_immutable": True,
        "runtime_data_read": False, "runtime_data_written": False,
        "source_modified": False, "authority_granted": False,
        **AUTHORITY_FLAGS,
    }


def feature_freeze_registry() -> dict[str, Any]:
    domains = []
    for index, code in enumerate(FREEZE_DOMAINS, 1):
        row = {"domain_code": code, "ordinal": index, "frozen": True, "content_free": True}
        row["domain_digest"] = _digest(row)
        domains.append(row)
    row = {
        "ok": True,
        "status": "feature_freeze_registry_ready",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "domain_count": len(domains),
        "domains": domains,
        "allowed_change_classes": list(ALLOWED_CHANGE_CLASSES),
        "blocked_change_classes": list(BLOCKED_CHANGE_CLASSES),
        "review_decisions": list(REVIEW_DECISIONS),
        "feature_freeze_active": True,
        "new_capability_work_blocked": True,
        "corrections_require_separate_governed_work": True,
        **_base(),
    }
    row["registry_digest"] = _digest(row)
    return row


def _source_inventory(source: Path) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    python_count = 0
    byte_count = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in {"data", "__pycache__", ".git"} for part in rel.parts):
            continue
        data = path.read_bytes()
        byte_count += len(data)
        if path.suffix == ".py":
            python_count += 1
        rows.append({"relative_path": rel.as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    return rows, python_count, byte_count


def _is_forbidden_source_entry(relative_path: Path) -> bool:
    parts = relative_path.parts
    if "data" in parts and relative_path.as_posix() != "data/settings.json":
        return True
    # Local bytecode is generated verification state, not source inventory.
    # Archive privacy is verified against the concrete ZIP separately.
    if "__pycache__" in parts or relative_path.suffix in {".pyc", ".pyo"}:
        return False
    return (
        ".git" in parts
        or relative_path.suffix == ".zip"
    )


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"}
                for t in node.targets
            ):
                names.update(ast.literal_eval(node.value))
    except Exception:
        return set()
    return names


def build_feature_freeze_manifest(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    inventory, python_count, byte_count = _source_inventory(source)
    surface_rows = []
    for relative_path, tokens in sorted(_REQUIRED_SURFACES.items()):
        path = source / relative_path
        exists = path.is_file()
        text = path.read_text(encoding="utf-8") if exists else ""
        checks = [token in text for token in tokens]
        row = {
            "surface_code": relative_path.replace("/", ":"),
            "relative_path_digest": _digest(relative_path),
            "exists": exists,
            "required_token_count": len(tokens),
            "required_tokens_present": sum(checks),
            "stable": exists and all(checks),
            "surface_sha256": hashlib.sha256(path.read_bytes()).hexdigest() if exists else "",
        }
        row["surface_digest"] = _digest(row)
        surface_rows.append(row)
    stage_text = (source / "tools/release_verify.py").read_text(encoding="utf-8") if (source / "tools/release_verify.py").is_file() else ""
    required_stages = {
        "v1249.2-feature-freeze-final-hardening-foundations",
        "v1249.5-feature-freeze-review-and-interface-stability",
        "v1249.8-feature-freeze-adversarial-reliability",
        "v1249.9-feature-freeze-final-hardening-checkpoint",
    }
    stages = _quick_stage_names(stage_text)
    result = {
        "ok": all(row["stable"] for row in surface_rows) and required_stages.issubset(stages),
        "status": "feature_freeze_manifest_stable" if all(row["stable"] for row in surface_rows) and required_stages.issubset(stages) else "feature_freeze_manifest_blocked",
        "contract_version": CONTRACT_VERSION,
        "source_file_count": len(inventory),
        "source_byte_count": byte_count,
        "python_file_count": python_count,
        "inventory_digest": _digest(inventory),
        "surface_count": len(surface_rows),
        "stable_surface_count": sum(1 for row in surface_rows if row["stable"]),
        "surfaces": surface_rows,
        "required_release_stage_count": len(required_stages),
        "required_release_stages_present": len(required_stages & stages),
        "public_interfaces_frozen": all(row["stable"] for row in surface_rows),
        "breaking_changes_blocked": True,
        "feature_additions_blocked": True,
        **_base(),
    }
    result["manifest_digest"] = _digest(result)
    return result


def classify_freeze_change(*, change_class: str, affected_surface_digests: Sequence[str], evidence_digest: str, rationale_digest: str) -> dict[str, Any]:
    token = str(change_class or "").strip().lower()
    surfaces = sorted({str(x).strip().lower() for x in affected_surface_digests if str(x).strip()})
    digests_valid = bool(evidence_digest) and bool(rationale_digest) and all(re.fullmatch(r"[a-f0-9]{64}", value) for value in (str(evidence_digest).lower(), str(rationale_digest).lower(), *surfaces))
    known = token in ALLOWED_CHANGE_CLASSES or token in BLOCKED_CHANGE_CLASSES
    eligible = token in ALLOWED_CHANGE_CLASSES and digests_valid
    row = {
        "ok": known and digests_valid,
        "status": "freeze_change_eligible_for_separate_review" if eligible else "freeze_change_blocked",
        "contract_version": CONTRACT_VERSION,
        "change_class": token,
        "affected_surface_count": len(surfaces),
        "affected_surface_digests": surfaces,
        "evidence_digest": str(evidence_digest).lower(),
        "rationale_digest": str(rationale_digest).lower(),
        "known_change_class": known,
        "allowed_change_class": token in ALLOWED_CHANGE_CLASSES,
        "blocked_change_class": token in BLOCKED_CHANGE_CLASSES,
        "separate_work_eligible": eligible,
        "mutation_performed": False,
        **_base(),
    }
    row["change_request_digest"] = _digest(row)
    return row


def review_freeze_change(*, change_request: Mapping[str, Any], decision: str, expected_change_request_digest: str) -> dict[str, Any]:
    token = str(decision or "").strip().lower()
    current = str(change_request.get("change_request_digest") or "")
    canonical = {key: value for key, value in dict(change_request).items() if key != "change_request_digest"}
    content_digest_valid = bool(current) and _digest(canonical) == current
    exact = bool(current) and current == str(expected_change_request_digest or "") and content_digest_valid
    valid = token in REVIEW_DECISIONS and exact and change_request.get("ok") is True
    accepted = valid and token == "accept_for_separate_work" and change_request.get("separate_work_eligible") is True
    row = {
        "ok": valid,
        "status": "freeze_change_review_recorded" if valid else "freeze_change_review_blocked",
        "contract_version": CONTRACT_VERSION,
        "decision": token,
        "change_request_digest": current,
        "expected_change_request_digest": str(expected_change_request_digest or ""),
        "exact_digest_match": exact,
        "content_digest_valid": content_digest_valid,
        "accepted_for_separate_work": accepted,
        "source_change_performed": False,
        "release_decision_created": False,
        **_base(),
    }
    row["review_digest"] = _digest(row)
    return row


def _source_stat_signature(source: Path) -> str:
    rows = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in {"data", "__pycache__", ".git"} for part in rel.parts):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        rows.append((rel.as_posix(), int(stat.st_mtime_ns), int(stat.st_size)))
    return _digest(rows)


@lru_cache(maxsize=8)
def _build_final_hardening_report_cached(source_text: str, source_signature: str) -> dict[str, Any]:
    del source_signature  # cache key; the body reads the selected source on a miss
    source = Path(source_text)
    manifest = build_feature_freeze_manifest(source_root=source)
    syntax_failures: list[str] = []
    python_count = 0
    for path in sorted(source.rglob("*.py")):
        rel = path.relative_to(source)
        if any(part in {"data", "__pycache__", ".git"} for part in rel.parts):
            continue
        python_count += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=rel.as_posix())
        except Exception:
            syntax_failures.append(_digest(rel.as_posix()))
    forbidden = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if _is_forbidden_source_entry(rel):
            forbidden.append(_digest(rel.as_posix()))
    api_text = (source / "conscious_agent/api_server.py").read_text(encoding="utf-8")
    dashboard_text = (source / "conscious_agent/dashboard.py").read_text(encoding="utf-8")
    checkpoint_ids = set()
    try:
        from checkpoint_registry import inspect_checkpoint_registry
        checkpoint_ids = {str(x.get("checkpoint_id")) for x in inspect_checkpoint_registry(source_root=source).get("checkpoints", [])}
    except Exception:
        pass
    retained_ids = {
        "mindful-execution-alpha-integration-benchmark-checkpoint",
        "dynamic-execution-plan-revision-checkpoint",
        "dependency-aware-execution-checkpoint",
        "resource-concurrency-governance-checkpoint",
        "requirement-quality-assessment-checkpoint",
        "evidence-backed-development-outcome-lessons-checkpoint",
        "goal-motivation-work-priority-integration-checkpoint",
        "multi-tool-orchestration-checkpoint",
        "broader-project-language-adapters-checkpoint",
        "adversarial-execution-cognitive-boundary-checkpoint",
        "integrated-developer-beta-checkpoint",
        "unified-operator-dashboard-checkpoint",
        "installation-lifecycle-integration-checkpoint",
        "provider-fallback-model-governance-checkpoint",
        "long-running-multi-day-session-continuity-checkpoint",
        "cross-session-project-understanding-checkpoint",
        "initiative-proposal-pacing-checkpoint",
        "privacy-security-secret-management-audit-checkpoint",
        "integrated-mind-conversation-development-benchmark-checkpoint",
    }
    checks = {
        "manifest_stable": manifest.get("ok") is True,
        "python_syntax_clean": not syntax_failures,
        "source_only_boundary_clean": not forbidden,
        "get_only_api_surface_present": all(token in api_text for token in ("feature-freeze-registry", "feature-freeze-manifest", "feature-freeze-final-hardening-report", "feature-freeze-final-hardening-checkpoint")),
        "dashboard_inspection_only": "/feature-freeze-final-hardening" in dashboard_text,
        "retained_checkpoint_lineage_present": retained_ids.issubset(checkpoint_ids),
        "new_features_blocked": True,
        "authority_expansion_blocked": True,
        "release_still_ungranted": True,
    }
    passed = sum(map(bool, checks.values()))
    result = {
        "ok": passed == len(checks),
        "status": "feature_freeze_final_hardening_ready" if passed == len(checks) else "feature_freeze_final_hardening_blocked",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "python_file_count": python_count,
        "syntax_failure_count": len(syntax_failures),
        "syntax_failure_digests": syntax_failures,
        "forbidden_source_entry_count": len(forbidden),
        "forbidden_source_entry_digests": forbidden,
        "retained_checkpoint_required_count": len(retained_ids),
        "retained_checkpoint_present_count": len(retained_ids & checkpoint_ids),
        "manifest_digest": manifest.get("manifest_digest"),
        **_base(),
    }
    result["hardening_report_digest"] = _digest(result)
    return result


def build_final_hardening_report(*, source_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    cached = _build_final_hardening_report_cached(str(source), _source_stat_signature(source))
    return copy.deepcopy(cached)


def feature_freeze_dashboard_record() -> dict[str, Any]:
    report = build_final_hardening_report()
    return {
        "ok": report.get("ok") is True,
        "status": report.get("status"),
        "title": MILESTONE_NAME,
        "passed": report.get("passed"),
        "total": report.get("total"),
        "source_file_count": build_feature_freeze_manifest().get("source_file_count"),
        "feature_freeze_active": True,
        "safe_next_action": "operator_inspection_only",
        "get_only": True,
        **_base(),
    }


def render_feature_freeze_dashboard_html() -> str:
    row = feature_freeze_dashboard_record()
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(MILESTONE_NAME) + "</title>"
        "<style>body{font-family:system-ui;background:#0d1117;color:#e6edf3;padding:24px}.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;max-width:900px}.muted{color:#8b949e}</style></head>"
        "<body><main><h1>" + html.escape(MILESTONE_NAME) + "</h1><div class='card'>"
        f"<p>Status: <strong>{html.escape(str(row.get('status')))}</strong></p>"
        f"<p>Hardening checks: {row.get('passed')}/{row.get('total')}</p>"
        "<p class='muted'>GET-only freeze inspection. No card, review, or report edits source, adds features, expands authority, certifies, promotes, or releases Eidolon.</p>"
        "</div></main></body></html>"
    )


def feature_freeze_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "feature_freeze_unknown")
    if status == "feature_freeze_registry_ready":
        return f"Feature freeze registry: {row.get('domain_count')} frozen domains. Corrections require separate governed work."
    if "manifest" in status:
        return f"Feature freeze manifest: {row.get('stable_surface_count')}/{row.get('surface_count')} required surfaces stable. No authority granted."
    return f"Feature freeze and final hardening: {status}. Checks: {row.get('passed')}/{row.get('total')}. No source or release authority granted."


def process_feature_freeze_final_hardening_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    text = str(user_text or "").strip()
    if _SHOW_REGISTRY.fullmatch(text):
        row = feature_freeze_registry()
    elif _SHOW_MANIFEST.fullmatch(text):
        row = build_feature_freeze_manifest()
    elif _SHOW_REPORT.fullmatch(text):
        row = build_final_hardening_report()
    else:
        return {"active": False}
    return {"active": True, "response": feature_freeze_response(row), "feature_freeze_final_hardening": row, "action_taken": False, "authority_granted": False}
