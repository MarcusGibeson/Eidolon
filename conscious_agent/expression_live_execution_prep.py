from __future__ import annotations

from typing import Any

from expression_live_application_packet import (
    build_expression_live_application_eligibility_gate_summary,
    build_expression_live_source_change_manifest_summary,
    build_expression_live_patch_instruction_packet_summary,
    build_expression_live_verification_rollback_packet_summary,
    build_expression_live_application_packet_audit_summary,
)
from expression_promotion_packet import build_expression_promotion_decision_packet_summary
from identity_expression import classify_identity_expression_request

EXPRESSION_LIVE_EXECUTION_PREP_VERSION = "1032.0"
EXPRESSION_LIVE_EXECUTION_PREP_BOUNDARIES = {
    "approval_intake_applies_live_expression": False,
    "approval_intake_treats_packet_as_authorization": False,
    "approval_intake_reuses_stale_approval": False,
    "approval_intake_self_approves": False,
    "approval_intake_continues_automatically": False,
    "transaction_manifest_writes_files": False,
    "transaction_manifest_mutates_source": False,
    "transaction_manifest_updates_version_markers": False,
    "transaction_manifest_includes_private_runtime_paths": False,
    "transaction_manifest_treats_plan_as_execution": False,
    "manual_checklist_executes_commands": False,
    "manual_checklist_applies_patch": False,
    "manual_checklist_runs_smoke": False,
    "manual_checklist_builds_package": False,
    "manual_checklist_inferrs_success_as_approval": False,
    "manual_checklist_infers_success_as_approval": False,
    "rollback_packet_runs_rollback": False,
    "rollback_packet_restores_files": False,
    "rollback_packet_executes_commands": False,
    "rollback_packet_publishes_release": False,
    "rollback_packet_treats_failure_as_auto_recovery": False,
    "execution_prep_applies_live_expression": False,
    "execution_prep_writes_source": False,
    "execution_prep_rewrites_prompts": False,
    "execution_prep_mutates_personality": False,
    "execution_prep_mutates_identity": False,
    "execution_prep_mutates_memory": False,
    "execution_prep_executes_commands": False,
    "execution_prep_runs_rollback": False,
    "execution_prep_publishes_release": False,
    "execution_prep_creates_release_candidate": False,
    "execution_prep_continues_to_execution": False,
    "execution_prep_review_only": True,
    "execution_prep_packet_bound": True,
    "separate_explicit_execution_packet_required": True,
}

APPROVAL_INTAKE_REQUIRED_FIELDS = [
    "operator_approval_id",
    "approval_scope",
    "approval_expiration",
    "target_version",
    "v345_promotion_packet_id",
    "v350_live_application_packet_id",
    "approved_surfaces",
    "approval_purpose",
]

EXPRESSION_EXECUTION_PREP_SURFACES = [
    "chat prompt wording review target",
    "dashboard command-deck microcopy review target",
    "API/CLI user-facing text review target",
    "README/release-history expression documentation review target",
    "safety/refusal warning language review target",
    "version marker and metadata review target",
]

SOURCE_TRANSACTION_READ_SET = [
    "conscious_agent/chat.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/main.py",
    "conscious_agent/self_maintenance.py",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "tools/smoke_check.py",
]

SOURCE_TRANSACTION_PROTECTED_PATHS = [
    "data/autonomy/",
    "data/self_maintenance/",
    "data/tasks.json",
    "memory stores",
    "local model outputs",
    "logs/",
    "release outputs",
    "generated artifacts",
    "private runtime state",
]

MANUAL_EXECUTION_CHECKLIST = [
    "Review v345 promotion packet reference.",
    "Review v350 live application packet reference.",
    "Review fresh approval intake scope and expiration.",
    "Review source transaction read/write/preimage manifest.",
    "Review expression diff and prompt/documentation impact manually.",
    "Run compileall manually only after a later explicit execution packet.",
    "Run fast smoke manually only after a later explicit execution packet.",
    "Run targeted v345/v350/v355 smoke manually only after a later explicit execution packet.",
    "Probe dashboard routes manually only after a later explicit execution packet.",
    "Check dynamic API/CLI parity manually only after a later explicit execution packet.",
    "Build source-only package manually only after a later explicit execution packet.",
    "Run package privacy and extracted zip verification manually.",
    "Record full install smoke status explicitly.",
]

ROLLBACK_DECISION_STATES = [
    "revise-packet",
    "defer-execution",
    "block-execution",
    "return-to-sandbox",
    "prepare-rollback-review",
    "operator-approved-retry-only",
]


def _policy_status(request_text: str | None, context: str) -> dict[str, Any]:
    return classify_identity_expression_request(request_text or "", context=context)


def _risk_flags(text: str | None) -> list[str]:
    lowered = (text or "").lower()
    catalog = {
        "live expression application request": ["apply live expression", "activate expression", "make personality live", "change live personality"],
        "source mutation request": ["write source", "edit files", "apply patch", "change production", "modify chat.py"],
        "prompt identity personality mutation": ["rewrite prompt now", "rewrite identity", "alter personality", "mutate memory", "rewrite purpose"],
        "command execution request": ["run smoke", "execute commands", "compile now", "build package", "run tests"],
        "rollback execution request": ["run rollback", "restore files", "auto recover", "perform rollback"],
        "approval bypass": ["self approve", "approve yourself", "reuse old approval", "skip approval", "no operator needed"],
        "automatic continuation": ["continue to execution", "start execution automatically", "schedule hidden work", "daily loop"],
    }
    return [label for label, needles in catalog.items() if any(needle in lowered for needle in needles)]


def _status(policy: dict[str, Any], flags: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if policy.get("status") == "blocked" or flags or blockers:
        return "blocked"
    if policy.get("status") == "warning":
        return "warning"
    return "reviewable"


def _missing_fields(evidence: dict[str, Any], required: list[str]) -> list[str]:
    missing = []
    for field in required:
        value = evidence.get(field)
        if value is None or value == "" or value == "expired" or value == "out-of-scope":
            missing.append(field)
    return missing


def build_expression_live_execution_approval_intake_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    policy = _policy_status(request_text, "expression live execution approval intake")
    flags = _risk_flags(request_text)
    missing = _missing_fields(evidence, APPROVAL_INTAKE_REQUIRED_FIELDS)
    scope = str(evidence.get("approval_scope") or "").lower()
    purpose = str(evidence.get("approval_purpose") or "").lower()
    blockers: list[str] = []
    if scope not in {"approve-to-prepare-live-expression-execution-packet", "approve-to-execution-prep-only"}:
        blockers.append("approval scope must authorize execution-prep packet preparation only")
    if "execution-prep" not in purpose and "prepare" not in purpose:
        blockers.append("approval purpose must be execution-prep only")
    if str(evidence.get("approval_expiration") or "").lower() in {"", "expired", "stale"}:
        blockers.append("fresh expiration-bound approval is missing or stale")
    return {
        "version": EXPRESSION_LIVE_EXECUTION_PREP_VERSION,
        "state": "live_expression_execution_approval_intake_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "future expression live execution prep surfaces",
        "required_approval_fields": list(APPROVAL_INTAKE_REQUIRED_FIELDS),
        "submitted_evidence_fields": sorted(evidence.keys()),
        "missing_approval_fields": missing,
        "approval_scope": evidence.get("approval_scope"),
        "approval_purpose": evidence.get("approval_purpose"),
        "approved_surfaces": evidence.get("approved_surfaces") or [],
        "v345_promotion_packet_id": evidence.get("v345_promotion_packet_id"),
        "v350_live_application_packet_id": evidence.get("v350_live_application_packet_id"),
        "promotion_decision_packet_reference": build_expression_promotion_decision_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence.get("promotion_packet") if isinstance(evidence.get("promotion_packet"), dict) else {}),
        "forbidden_inference_checks": ["readiness-is-not-approval", "sandbox-success-is-not-approval", "promotion-packet-is-not-authorization", "v350-live-application-packet-is-not-execution-approval"],
        "allowed_next_action": "prepare-execution-prep-packet-only-after-fresh-scope-bound-operator-approval",
        "blockers": blockers + [f"missing:{field}" for field in missing],
        "risk_flags": flags,
        "status": _status(policy, flags, blockers + missing),
        "applies_live_expression": False,
        "treats_packet_as_authorization": False,
        "reuses_stale_approval": False,
        "self_approves": False,
        "continues_automatically": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_source_transaction_preimage_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live source transaction preimage")
    flags = _risk_flags(request_text)
    text = (request_text or "").lower()
    protected_mentions = [path for path in SOURCE_TRANSACTION_PROTECTED_PATHS if path.lower().strip("/") in text]
    write_set = ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "version markers", "project metadata"]
    if "chat" in text or "prompt" in text:
        write_set.append("conscious_agent/chat.py candidate expression surface")
    if "dashboard" in text:
        write_set.append("conscious_agent/dashboard.py candidate microcopy surface")
    blockers = []
    if protected_mentions:
        blockers.append("protected private/runtime path mentioned in transaction request")
    return {
        "version": EXPRESSION_LIVE_EXECUTION_PREP_VERSION,
        "state": "live_source_transaction_preimage_manifest_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "possible future live expression source surfaces",
        "read_set": list(SOURCE_TRANSACTION_READ_SET),
        "candidate_write_set": write_set,
        "protected_path_exclusions": list(SOURCE_TRANSACTION_PROTECTED_PATHS),
        "protected_path_mentions": protected_mentions,
        "preimage_requirements": ["record before-state hash", "record file path", "record intended edit purpose", "record rollback anchor", "record docs/version obligation"],
        "version_marker_impact": ["self_maintenance", "dashboard", "api_server", "release_packaging", "version_state", "settings", "project metadata"],
        "documentation_obligations": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"],
        "rollback_anchor_references": ["pre-change source snapshot", "reverse diff expectation", "operator decision packet"],
        "blockers": blockers,
        "risk_flags": flags,
        "status": _status(policy, flags, blockers),
        "writes_files": False,
        "mutates_source": False,
        "updates_version_markers": False,
        "includes_private_runtime_paths": False,
        "treats_plan_as_execution": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_manual_execution_checklist_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live manual execution checklist")
    flags = _risk_flags(request_text)
    commands_as_text = [
        "python -m compileall conscious_agent tools",
        "python tools/smoke_check.py --tier fast",
        "python tools/smoke_check.py --only operator-governed-expression-promotion-packet-assembly-layer-v1",
        "python tools/smoke_check.py --only operator-governed-expression-live-application-packet-drafting-layer-v1",
        "python tools/smoke_check.py --only operator-governed-expression-live-application-execution-prep-v1",
        "manual dashboard route probes for all v355 routes",
        "manual dynamic API/CLI parity checks for all v355 routes and flags",
        "manual source-only package privacy scan",
        "manual extracted zip compile and smoke check",
    ]
    return {
        "version": EXPRESSION_LIVE_EXECUTION_PREP_VERSION,
        "state": "manual_execution_checklist_text_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "future manual expression execution prep checklist",
        "checklist": list(MANUAL_EXECUTION_CHECKLIST),
        "verification_commands_as_text_only": commands_as_text,
        "human_review_requirements": ["fresh approval intake", "packet id cross-check", "source preimage review", "diff review", "rollback review", "docs/version review"],
        "targeted_smoke_matrix": ["v345", "v350", "v355"],
        "dashboard_route_probe_required": True,
        "api_cli_parity_required": True,
        "full_install_smoke_accountability_note": "Full install smoke must be recorded by the operator when performed; this layer does not run it.",
        "risk_flags": flags,
        "status": _status(policy, flags),
        "executes_commands": False,
        "applies_patch": False,
        "runs_smoke": False,
        "builds_package": False,
        "inferrs_success_as_approval": False,
        "infers_success_as_approval": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_rollback_reversion_packet_summary(
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = _policy_status(request_text, "expression live rollback reversion packet")
    flags = _risk_flags(request_text)
    return {
        "version": EXPRESSION_LIVE_EXECUTION_PREP_VERSION,
        "state": "rollback_reversion_packet_prep_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "target_surface": target_surface or "future expression rollback/reversion packet",
        "pre_change_snapshot_plan": ["capture source preimage", "capture docs preimage", "capture version metadata preimage", "capture package manifest preimage"],
        "reverse_diff_expectations": ["reverse only scoped expression edits", "preserve unrelated operator changes", "verify docs/version rollback", "verify no private runtime paths"],
        "rollback_verification_commands_as_text_only": ["python -m compileall conscious_agent tools", "python tools/smoke_check.py --tier fast", "manual dashboard route probes", "manual package privacy scan"],
        "failure_thresholds": ["compile failure", "fast smoke failure", "dashboard route 500", "API/CLI parity break", "privacy leak", "identity/personality boundary regression"],
        "post_rollback_review_packet": ["failure cause", "reverted surfaces", "remaining drift", "operator decision", "return-to-sandbox recommendation"],
        "operator_decision_states": list(ROLLBACK_DECISION_STATES),
        "risk_flags": flags,
        "status": _status(policy, flags),
        "runs_rollback": False,
        "restores_files": False,
        "executes_commands": False,
        "publishes_release": False,
        "treats_failure_as_auto_recovery": False,
        "review_only": True,
        "policy_decision": policy,
    }


def build_expression_live_execution_prep_audit_summary(
    dashboard_text: str = "",
    profile_name: str | None = None,
    request_text: str | None = None,
    target_surface: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    approval = build_expression_live_execution_approval_intake_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    transaction = build_expression_live_source_transaction_preimage_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    checklist = build_expression_live_manual_execution_checklist_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    rollback = build_expression_live_rollback_reversion_packet_summary(profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence=evidence)
    live_application_packet = build_expression_live_application_packet_audit_summary(dashboard_text=dashboard_text, profile_name=profile_name, request_text=request_text, target_surface=target_surface, evidence={"promotion_packet_id": "v345-reference", "target_version": "v350.0", "operator_decision_state": "approved-to-draft", "approval_scope": "approve-to-draft-live-application-packet", "expiration": "fresh", "risk_status": "reviewable", "allowed_next_action": "draft-live-application-packet"})
    routes = [
        "/expression-live-execution-approval-intake",
        "/expression-live-source-transaction-preimage",
        "/expression-live-manual-execution-checklist",
        "/expression-live-rollback-reversion-packet",
        "/expression-live-execution-prep-audit",
    ]
    missing_routes = [route for route in routes if dashboard_text and route not in dashboard_text]
    flags = sorted(set(approval.get("risk_flags", [])) | set(transaction.get("risk_flags", [])) | set(checklist.get("risk_flags", [])) | set(rollback.get("risk_flags", [])))
    blockers = list(missing_routes)
    for packet in [approval, transaction, checklist, rollback]:
        if packet.get("status") == "blocked":
            blockers.append(str(packet.get("state", "blocked subpacket")))
    return {
        "version": EXPRESSION_LIVE_EXECUTION_PREP_VERSION,
        "state": "expression_live_application_execution_prep_audit_only",
        "profile_name": profile_name or "operator_review_expression_profile",
        "approval_intake_audit": approval,
        "source_transaction_preimage_audit": transaction,
        "manual_execution_checklist_audit": checklist,
        "rollback_reversion_packet_audit": rollback,
        "v350_live_application_packet_reference_audit": live_application_packet,
        "dashboard_routes": routes,
        "missing_dashboard_routes": missing_routes,
        "dashboard_http_route_probe_required": True,
        "api_cli_parity_required": True,
        "readme_release_history_required": True,
        "package_privacy_required": True,
        "risk_flags": flags,
        "blockers": blockers,
        "status": _status(_policy_status(request_text, "expression live execution prep audit"), flags, blockers),
        "applies_live_expression": False,
        "writes_source": False,
        "rewrites_prompts": False,
        "mutates_personality": False,
        "mutates_identity": False,
        "mutates_memory": False,
        "executes_commands": False,
        "runs_rollback": False,
        "publishes_release": False,
        "creates_release_candidate": False,
        "continues_to_execution": False,
        "review_only": True,
        "packet_bound": True,
        "safe_next_action": "Operator may review the live expression execution prep packet. Actual live expression source application still requires a separate explicit operator-approved execution packet.",
        "boundaries": dict(EXPRESSION_LIVE_EXECUTION_PREP_BOUNDARIES),
    }


def render_expression_live_execution_prep_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in summary.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                lines.append(f"- {key}: {len(value)} item(s)")
            else:
                lines.append(f"- {key}: " + ", ".join(str(item) for item in value))
        elif isinstance(value, dict):
            lines.append(f"- {key}: {len(value)} field(s)")
        else:
            lines.append(f"- {key}: {value}")
    return lines
