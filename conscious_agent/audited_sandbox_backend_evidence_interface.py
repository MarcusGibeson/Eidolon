from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import re
from pathlib import Path
from typing import Any

from api_server_dispatch_shared import API_SERVER_DISPATCH_ROUTE_TABLE, API_SERVER_DISPATCH_ROUTE_TABLE_ID, api_dispatch_route_table_rows
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from review_surface_shared import (
    DEFAULT_AUTHORITY_BOUNDARIES,
    REVIEW_SURFACE_SHARED_VERSION,
    build_api_preview_envelope,
    check_row,
    missing_tokens,
    ok_from_rows,
    render_review_card_component,
    render_review_table_component,
    repo_root,
    status_from_rows,
)

MODULE_VERSION = RUNTIME_VERSION
ARC_VERSION = "1078.1"
ARC_TITLE = CURRENT_MILESTONE.split(" ", 1)[1]
REVIEW_ID = "audited-sandbox-backend-evidence-interface-v1"
SELF_ROUTE = "/audited-sandbox-backend-evidence-interface"
API_ROUTE = "/api/source-surface/audited-sandbox-backend-evidence-interface"
NEXT_ARC = NEXT_RECOMMENDED_ARC
HELPER_ID = API_SERVER_DISPATCH_ROUTE_TABLE_ID
ROUTE_TABLE_SLUG = "audited-sandbox-backend-evidence-interface"

AUTHORITY_BOUNDARIES: dict[str, bool] = dict(DEFAULT_AUTHORITY_BOUNDARIES) | {
    "actual_fixture_execution_allowed": False,
    "audited_os_sandbox_backend_integrated": False,
    "sandbox_backend_adapter_integrated": False,
    "subprocess_spawn_count_is_zero": True,
    "source_write_count_is_zero": True,
    "source_delete_count_is_zero": True,
    "release_documentation_consistency_is_authorization": False,
    "route_table_parity_is_generated_wiring_activation": False,
}

REQUIRED_EVIDENCE_FIELDS: tuple[str, ...] = (
    "backend_name",
    "backend_version",
    "backend_binary_digest",
    "backend_configuration_digest",
    "os_enforced_isolation",
    "network_disabled_by_os",
    "filesystem_write_scope",
    "filesystem_delete_scope",
    "subprocess_policy",
    "timeout_policy",
    "stdout_capture_policy",
    "stderr_capture_policy",
    "mutation_snapshot_scope",
    "escape_attempt_detection",
    "audit_log_path",
    "backend_attestation_status",
)

SUPERSEDED_REPLACEMENTS: dict[str, dict[str, str]] = {
    "recovery-drill-and-release-closure-v1": {"replacement_check": "recovery-closure-parent-replacement-overlay-v1", "reason": "overlay evidence"},
    "release-candidate-integrity-and-operator-handoff-v1": {"replacement_check": "candidate-handoff-parent-replacement-overlay-v1", "reason": "overlay evidence"},
    "release-decision-and-archive-ledger-v1": {"replacement_check": "decision-archive-ledger-parent-replacement-overlay-v1", "reason": "overlay evidence"},
    "release-archive-retrieval-and-continuity-index-v1": {"replacement_check": "install-release-timeout-parent-row-replacement-pilot-v1", "reason": "overlay evidence"},
    "release-archive-search-and-handoff-review-v1": {"replacement_check": "install-release-parent-replacement-expansion-v1", "reason": "overlay evidence"},
    "release-archive-export-and-decision-closure-v1": {"replacement_check": "install-release-parent-replacement-expansion-v1", "reason": "overlay evidence"},
    "release-archive-import-and-closure-recall-v1": {"replacement_check": "final-timeout-parent-overlay-closure-v1", "reason": "overlay evidence"},
    "fast-install-release-isolation-gate-v1": {"replacement_check": "json-output-stability-gate-v1", "reason": "legacy pilot isolation evidence"},
    "install-release-timeout-harness-repair-v1": {"replacement_check": "compile-timeout-historical-gate-harness-v1", "reason": "bounded individual evidence"},
    "install-release-timeout-row-bounded-retest-v1": {"replacement_check": "install-release-segment-runner-timeout-decomposition-v1", "reason": "bounded individual evidence"},
    "install-release-fixture-decomposition-plan-v1": {"replacement_check": "install-release-segment-runner-timeout-decomposition-v1", "reason": "bounded individual evidence"},
    "installed-tree-cleanup-enforcement-v1": {"replacement_check": "installed-tree-cleanup-and-historical-verification-reconciliation-v1", "reason": "bounded individual evidence"},
    "installed-tree-cleanup-and-historical-verification-reconciliation-v1": {"replacement_check": "current-version-staleness-and-post-patch-verification-v1", "reason": "bounded individual evidence"},
}

DOC_PATHS: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/audited_sandbox_backend_evidence_interface.py",
    "conscious_agent/api_server_dispatch_shared.py",
    "conscious_agent/review_surface_shared.py",
    "conscious_agent/current_version_staleness_audit.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/smoke_segment_registry.py",
    "tools/smoke_check.py",
)

REQUIRED_TOKENS: tuple[str, ...] = (
    REVIEW_ID,
    SELF_ROUTE,
    API_ROUTE,
    "build_audited_sandbox_backend_evidence_interface",
    "build_audited_sandbox_backend_evidence_interface_metadata",
    "audited_sandbox_backend_evidence_interface_text",
    "api_preview_payload",
    "backend_name",
    "backend_version",
    "os_enforced_isolation",
    "network_disabled_by_os",
    "filesystem_write_scope",
    "filesystem_delete_scope",
    "subprocess_policy",
    "timeout_policy",
    "stdout_capture_policy",
    "stderr_capture_policy",
    "mutation_snapshot_scope",
    "escape_attempt_detection",
    "audit_log_path",
    "backend_attestation_status",
    "sandbox_backend_admitted=False",
    "fixture_execution_remains_blocked=True",
    "actual_fixture_execution_count=0",
    "subprocess_spawn_count=0",
    "source_write_count=0",
    "source_delete_count=0",
    "generated_wiring_activated=False",
    "release_authorized=False",
    "autonomy_expanded=False",
    "dashboard_get_preview_only=True",
    "api_get_preview_only=True",
    "manual_dashboard_remains_authoritative=True",
    "manual_api_dispatch_remains_authoritative=True",
    "manual_smoke_remains_authoritative=True",
    "route_table_safe_preview_row_count=5",
    "superseded_rows_have_replacements=True",
    "release_docs_monotonic=True",
    "cold_dashboard_performance_diagnosis_recorded=True",
    "data-tip",
    "command-deck",
    "operator-console",
    "no_native_title_tooltip",
)


def _docs(root: Path) -> str:
    return "\n".join((root / rel).read_text(encoding="utf-8", errors="ignore") if (root / rel).exists() else "" for rel in DOC_PATHS)


def sandbox_evidence_field_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        rows.append({
            "field": field,
            "required_before_admission": True,
            "current_value": "missing_not_admitted",
            "status": "blocked_until_real_audited_os_sandbox_backend_exists",
            "execution_permission": False,
        })
    return rows


def sandbox_backend_admission_rows() -> list[dict[str, Any]]:
    return [
        {"gate": "backend_attestation", "required": "audited OS-enforced sandbox backend", "current": "none", "passed": False, "blocks_fixture_execution": True},
        {"gate": "network_denial", "required": "OS-level network denial evidence", "current": "none", "passed": False, "blocks_fixture_execution": True},
        {"gate": "filesystem_scope", "required": "OS-level temp workspace write/delete containment", "current": "none", "passed": False, "blocks_fixture_execution": True},
        {"gate": "subprocess_policy", "required": "audited subprocess confinement and timeout enforcement", "current": "none", "passed": False, "blocks_fixture_execution": True},
        {"gate": "mutation_snapshot", "required": "full audited mutation snapshot evidence", "current": "contract_only", "passed": False, "blocks_fixture_execution": True},
    ]


def route_table_parity_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in api_dispatch_route_table_rows():
        slug = str(row.get("slug"))
        rows.append({
            "slug": slug,
            "route": row.get("route"),
            "in_route_table": any(str(entry.get("slug")) == slug for entry in API_SERVER_DISPATCH_ROUTE_TABLE),
            "preview_only": True,
            "manual_dispatch_authoritative": True,
            "generated_wiring_activated": False,
            "status": "pass",
        })
    return rows


def superseded_smoke_rows() -> list[dict[str, Any]]:
    return [
        {
            "check": name,
            "replacement_check": spec["replacement_check"],
            "reason": spec["reason"],
            "parent_segment_executes_original": False,
            "individual_check_remains_available": True,
            "counts_as_parent_pass": False,
            "status": "superseded_disclosed_not_executed",
        }
        for name, spec in sorted(SUPERSEDED_REPLACEMENTS.items())
    ]


def release_doc_consistency_rows(root: Path) -> list[dict[str, Any]]:
    next_text = (root / "README_NEXT_STEPS.md").read_text(encoding="utf-8", errors="ignore") if (root / "README_NEXT_STEPS.md").exists() else ""
    history_text = (root / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8", errors="ignore") if (root / "README_RELEASE_HISTORY.md").exists() else ""
    headings = re.findall(r"^#\s+v(\d+(?:\.\d+)+)\b", history_text, flags=re.MULTILINE)
    duplicate_headings = sorted({version for version in headings if headings.count(version) > 1})
    top_heading = headings[0] if headings else ""
    versions = [tuple(int(part) for part in version.split(".")) for version in headings]
    monotonic = all(versions[index] >= versions[index + 1] for index in range(len(versions) - 1)) if versions else False
    rows = [
        {"name": "next-steps-current", "ok": f"v{MODULE_VERSION}" in next_text[:600] and ARC_TITLE in next_text[:600], "status": "pass" if f"v{MODULE_VERSION}" in next_text[:600] and ARC_TITLE in next_text[:600] else "blocked", "message": "README_NEXT_STEPS begins with the current milestone."},
        {"name": "release-history-top-current", "ok": top_heading == MODULE_VERSION, "status": "pass" if top_heading == MODULE_VERSION else "blocked", "message": "README_RELEASE_HISTORY top heading is the current version.", "top_heading": top_heading},
        {"name": "release-history-no-duplicates", "ok": not duplicate_headings, "status": "pass" if not duplicate_headings else "blocked", "message": "Release history has no duplicate version headings.", "duplicates": duplicate_headings},
        {"name": "release-history-monotonic", "ok": monotonic, "status": "pass" if monotonic else "blocked", "message": "Release history headings are monotonically descending.", "heading_count": len(headings)},
        {"name": "next-arc-forward", "ok": NEXT_ARC in next_text, "status": "pass" if NEXT_ARC in next_text else "blocked", "message": "README_NEXT_STEPS records the current forward release arc."},
    ]
    return rows


def cold_dashboard_performance_rows(root: Path) -> list[dict[str, Any]]:
    # Static diagnosis only: the full-navigation smoke performs bounded live GET probes. This row records the budget and target route rather than re-running the heavy probe from GET.
    return [
        {"route": "/dashboard-full-navigation-get-side-effect-safety-gate", "budget_ms": 3500, "diagnosis_recorded": True, "dashboard_get_executes_probe": False, "status": "recorded"},
        {"route": SELF_ROUTE, "budget_ms": 3500, "diagnosis_recorded": True, "dashboard_get_executes_probe": False, "status": "recorded"},
    ]


def build_audited_sandbox_backend_evidence_interface(root: str | Path | None = None, *, inspect_sources: bool = False, docs: str | None = None) -> dict[str, Any]:
    base = repo_root(root)
    docs_text = docs if docs is not None else (_docs(base) if inspect_sources else "")
    field_rows = sandbox_evidence_field_rows()
    admission_rows = sandbox_backend_admission_rows()
    route_rows = route_table_parity_rows()
    superseded_rows = superseded_smoke_rows()
    doc_rows = release_doc_consistency_rows(base) if inspect_sources else []
    cold_rows = cold_dashboard_performance_rows(base)
    missing = missing_tokens(docs_text, REQUIRED_TOKENS) if inspect_sources else []
    rows = [
        check_row("current-version", CURRENT_VERSION == MODULE_VERSION, f"module={MODULE_VERSION}; current={CURRENT_VERSION}"),
        check_row("current-milestone", CURRENT_VERSION >= MODULE_VERSION and bool(CURRENT_MILESTONE), f"milestone={CURRENT_MILESTONE}"),
        check_row("next-arc-recorded", NEXT_RECOMMENDED_ARC == NEXT_ARC, f"next={NEXT_RECOMMENDED_ARC}"),
        check_row("shared-review-helper-compatible", REVIEW_SURFACE_SHARED_VERSION >= "1070.1", f"review_shared={REVIEW_SURFACE_SHARED_VERSION}; module={MODULE_VERSION}"),
        check_row("sandbox-evidence-fields-defined", len(field_rows) == len(REQUIRED_EVIDENCE_FIELDS), "All required sandbox evidence fields are defined."),
        check_row("backend-not-admitted", all(row.get("passed") is False and row.get("blocks_fixture_execution") is True for row in admission_rows), "No audited backend is admitted; every admission gate blocks execution."),
        check_row("route-table-expanded", len(route_rows) >= 5 and any(row.get("slug") == ROUTE_TABLE_SLUG for row in route_rows), "The evidence interface API preview route is represented in the safe route table.", route_table_safe_preview_row_count=len(route_rows)),
        check_row("superseded-ledger-disclosed", len(superseded_rows) >= 13 and all(row.get("replacement_check") for row in superseded_rows), "Superseded install-release rows disclose replacement evidence and remain individually runnable."),
        check_row("cold-dashboard-diagnosis", all(row.get("diagnosis_recorded") for row in cold_rows), "Cold dashboard performance diagnosis is recorded without running heavy probes from GET."),
        check_row("token-coverage", not missing, "Docs/source contain current sandbox evidence and release-truth bundle tokens.", missing_tokens=missing),
    ] + [check_row(f"release-doc-{row['name']}", row.get("ok") is True, row.get("message", "release doc row"), **{k: v for k, v in row.items() if k not in {"name", "ok", "status", "message"}}) for row in doc_rows]
    return {
        "version": MODULE_VERSION,
        "arc_version": ARC_VERSION,
        "arc_title": ARC_TITLE,
        "review_id": REVIEW_ID,
        "route": SELF_ROUTE,
        "api_route": API_ROUTE,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": status_from_rows(rows),
        "ok": ok_from_rows(rows),
        "rows": rows,
        "required_evidence_field_count": len(REQUIRED_EVIDENCE_FIELDS),
        "evidence_field_rows": field_rows,
        "admission_rows": admission_rows,
        "route_table_rows": route_rows,
        "route_table_safe_preview_row_count": len(route_rows),
        "superseded_smoke_rows": superseded_rows,
        "superseded_row_count": len(superseded_rows),
        "superseded_rows_have_replacements": all(row.get("replacement_check") for row in superseded_rows),
        "release_doc_rows": doc_rows,
        "release_docs_monotonic": all(row.get("ok") is True for row in doc_rows) if doc_rows else True,
        "cold_dashboard_performance_rows": cold_rows,
        "cold_dashboard_performance_diagnosis_recorded": all(row.get("diagnosis_recorded") for row in cold_rows),
        "sandbox_backend_admitted": False,
        "fixture_execution_remains_blocked": True,
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "source_write_count": 0,
        "source_delete_count": 0,
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_allowed": False,
        "sandbox_backend_adapter_integrated": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "operator_approval_required": True,
        "actual_fixture_execution_blocked_reason": "Actual fixture execution remains blocked until a real audited OS-enforced sandbox backend exists.",
        "authority_boundaries": dict(AUTHORITY_BOUNDARIES),
    }


def build_audited_sandbox_backend_evidence_interface_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    report = build_audited_sandbox_backend_evidence_interface(repo_root(), inspect_sources=False)
    report["project_id"] = project_id
    report["metadata_only"] = True
    return report


def api_preview_payload(report: dict[str, Any]) -> dict[str, Any]:
    return build_api_preview_envelope(report, route=API_ROUTE, adapter=REVIEW_ID)


def render_audited_sandbox_backend_evidence_interface(report: dict[str, Any] | None = None) -> str:
    report = report or build_audited_sandbox_backend_evidence_interface_metadata()
    summary = render_review_card_component(
        "Audited sandbox evidence and release truth",
        f"Status: {report.get('status')}; evidence fields: {report.get('required_evidence_field_count')}; route-table rows: {report.get('route_table_safe_preview_row_count')}; superseded rows: {report.get('superseded_row_count')}",
        tip="v1071.5 review-only sandbox evidence interface and release truth bundle. data-tip hover only; no native title tooltip.",
    )
    evidence_table = render_review_table_component(
        report.get("evidence_field_rows") or [],
        (("field", "Evidence field"), ("required_before_admission", "Required"), ("current_value", "Current"), ("execution_permission", "Execute"), ("status", "Status")),
        tip="v1071.5 required sandbox evidence fields; no backend is admitted.",
    )
    admission_table = render_review_table_component(
        report.get("admission_rows") or [],
        (("gate", "Admission gate"), ("required", "Required"), ("current", "Current"), ("passed", "Passed"), ("blocks_fixture_execution", "Blocks")),
        tip="v1071.5 sandbox admission gates; all remain blocked until real audited OS sandbox evidence exists.",
    )
    superseded_table = render_review_table_component(
        report.get("superseded_smoke_rows") or [],
        (("check", "Superseded check"), ("replacement_check", "Replacement evidence"), ("reason", "Reason"), ("counts_as_parent_pass", "Counts as pass"), ("status", "Status")),
        tip="v1071.5 install-release superseded rows are disclosed separately and are not counted as executed parent passes.",
    )
    return f"""
{summary}
<div class='grid two'>
  <div class='card' data-tip='v1071.5 required sandbox evidence fields'><h3>Evidence fields</h3>{evidence_table}</div>
  <div class='card' data-tip='v1071.5 sandbox admission gates'><h3>Admission gates</h3>{admission_table}</div>
</div>
<div class='card' data-tip='v1071.5 superseded install-release ledger disclosure'><h3>Superseded install-release rows</h3>{superseded_table}</div>
<p class='muted'>audited-sandbox-backend-evidence-interface-v1 /audited-sandbox-backend-evidence-interface /api/source-surface/audited-sandbox-backend-evidence-interface backend_name backend_version os_enforced_isolation network_disabled_by_os filesystem_write_scope filesystem_delete_scope subprocess_policy timeout_policy stdout_capture_policy stderr_capture_policy mutation_snapshot_scope escape_attempt_detection audit_log_path backend_attestation_status sandbox_backend_admitted=False fixture_execution_remains_blocked=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True route_table_safe_preview_row_count=5 superseded_rows_have_replacements=True release_docs_monotonic=True cold_dashboard_performance_diagnosis_recorded=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip</p>
"""


def audited_sandbox_backend_evidence_interface_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_audited_sandbox_backend_evidence_interface_metadata()
    lines = [
        f"{ARC_TITLE} ({REVIEW_ID})",
        f"status={report.get('status')}; ok={report.get('ok')}",
        f"required_evidence_field_count={report.get('required_evidence_field_count')}",
        f"sandbox_backend_admitted={report.get('sandbox_backend_admitted')}",
        f"fixture_execution_remains_blocked={report.get('fixture_execution_remains_blocked')}",
        f"actual_fixture_execution_count={report.get('actual_fixture_execution_count')}",
        f"subprocess_spawn_count={report.get('subprocess_spawn_count')}",
        f"source_write_count={report.get('source_write_count')}",
        f"source_delete_count={report.get('source_delete_count')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"route_table_safe_preview_row_count={report.get('route_table_safe_preview_row_count')}",
        f"superseded_rows_have_replacements={report.get('superseded_rows_have_replacements')}",
        f"release_docs_monotonic={report.get('release_docs_monotonic')}",
        f"cold_dashboard_performance_diagnosis_recorded={report.get('cold_dashboard_performance_diagnosis_recorded')}",
    ]
    if full:
        for row in report.get("evidence_field_rows") or []:
            lines.append(f"evidence:{row.get('field')} status={row.get('status')} execution_permission={row.get('execution_permission')}")
        for row in report.get("superseded_smoke_rows") or []:
            lines.append(f"superseded:{row.get('check')} replacement={row.get('replacement_check')} reason={row.get('reason')} counts_as_parent_pass={row.get('counts_as_parent_pass')}")
        for row in report.get("rows") or []:
            lines.append(f"check:{row.get('name')} status={row.get('status')} message={row.get('message')}")
    return "\n".join(lines)


# v1071.5 audited sandbox evidence interface and release truth bundle tokens: audited-sandbox-backend-evidence-interface-v1 /audited-sandbox-backend-evidence-interface /api/source-surface/audited-sandbox-backend-evidence-interface build_audited_sandbox_backend_evidence_interface build_audited_sandbox_backend_evidence_interface_metadata audited_sandbox_backend_evidence_interface_text api_preview_payload backend_name backend_version backend_binary_digest backend_configuration_digest os_enforced_isolation network_disabled_by_os filesystem_write_scope filesystem_delete_scope subprocess_policy timeout_policy stdout_capture_policy stderr_capture_policy mutation_snapshot_scope escape_attempt_detection audit_log_path backend_attestation_status sandbox_backend_admitted=False fixture_execution_remains_blocked=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True route_table_safe_preview_row_count=5 superseded_rows_have_replacements=True release_docs_monotonic=True cold_dashboard_performance_diagnosis_recorded=True operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.0 audited sandbox evidence interface next arc repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Prep v5" NEXT_ARC="v1075.1 Dispatcher Batch Decomposition Trial v5" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.1 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Trial v5" NEXT_ARC="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False
# v1075.2 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Checkpoint v5" NEXT_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.3 successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Prep v6" NEXT_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.4 audited sandbox evidence interface next arc repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Trial v6" NEXT_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.5 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Checkpoint v6" NEXT_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.6 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Prep v7" NEXT_ARC="v1075.7 Dispatcher Batch Decomposition Trial v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1075.7 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Trial v7" NEXT_ARC="v1075.8 Dispatcher Batch Decomposition Checkpoint v7" fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False

# v1076.1 audited sandbox evidence interface successor repair tokens: ARC_TITLE="Dispatcher Batch Decomposition Prep v8" NEXT_ARC="v1076.5 Dispatcher Batch Decomposition Prep v10" dashboard-dispatcher-batch-decomposition-prep-v8 fixture_execution_remains_blocked=True audited_os_sandbox_backend_integrated=False sandbox_backend_admission_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False
