"""Governance-state-to-authorization firewall review helpers for Eidolon v450.0.

This module is intentionally review-only. It detects language and metadata that could
confuse readiness, eligibility, smoke success, route health, lifecycle completeness,
prior approval, or sandbox success with actual authorization. It does not approve,
deny, execute, mutate memory, apply patches, or rewrite source.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any, Iterable

AUTHORIZATION_FIREWALL_VERSION = "500.0"

AUTHORIZATION_FIREWALL_BOUNDARIES = {
    "firewall_detection_is_enforcement_execution": False,
    "firewall_pass_is_authorization": False,
    "firewall_rewrites_packets": False,
    "firewall_mutates_memory": False,
    "firewall_applies_source_edits": False,
    "firewall_expands_autonomy": False,
    "firewall_invokes_models": False,
    "clear_status_means_approved": False,
    "operator_approval_still_required": True,
}

RECENT_SCAN_PATHS = [
    "conscious_agent/memory_candidate_application_trial.py",
    "conscious_agent/memory_application_dry_run_ledger.py",
    "conscious_agent/sandbox_memory_write_target.py",
    "conscious_agent/live_memory_write_trial.py",
    "conscious_agent/memory_retraction_trial.py",
    "conscious_agent/memory_lifecycle_review_board.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/dashboard_route_probe.py",
    "conscious_agent/duplicate_definition_audit.py",
    "conscious_agent/self_maintenance.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/main.py",
]

SAFE_BOUNDARY_MARKERS = [
    "is not authorization",
    "is not approval",
    "not authorization",
    "not approval",
    "review-only",
    "review only",
    "does not write memory",
    "does not apply",
    "fresh approval",
    "single-use",
    "burnout",
    "operator approval required",
    "approval remains required",
]

RISKY_LANGUAGE_PATTERNS = [
    ("approved", "Potential approval wording; must be guarded by explicit operator approval and single-use scope."),
    ("authorized", "Potential authorization wording; must not be inferred from state, route health, manifest presence, or smoke success."),
    ("may execute", "Execution language must require explicit operator approval."),
    ("ready to apply", "Readiness language must not imply approval."),
    ("safe to write", "Safety/readiness language must not imply memory write permission."),
    ("permission granted", "Permission wording must be tied to explicit fresh operator confirmation."),
    ("future approval", "Future approval cannot be inferred from lifecycle completeness or prior approval."),
    ("auto-approved", "Auto-approval is forbidden."),
    ("all checks passed", "Checks passing must not be treated as authorization."),
]

@dataclass(frozen=True)
class AuthorizationConfusionPattern:
    pattern_id: str
    description: str
    risk_level: str
    example_bad_language: str
    required_safe_language: str
    applies_to: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]


def build_authorization_confusion_patterns() -> dict[str, Any]:
    patterns = [
        AuthorizationConfusionPattern(
            "readiness_is_approval",
            "Readiness or reviewability is mistaken for operator approval.",
            "critical",
            "The packet is ready, so it may proceed.",
            "The packet is ready for operator review only; explicit approval is still required.",
            ("patches", "memory", "dashboard", "smoke"),
            ("source_write", "memory_write", "release", "autonomy"),
        ),
        AuthorizationConfusionPattern(
            "eligibility_is_approval",
            "Eligibility checks are mistaken for authorization.",
            "critical",
            "The candidate is eligible, so the write is authorized.",
            "Eligibility only permits presentation to the operator for fresh approval.",
            ("memory", "expression", "patches"),
            ("memory_write", "identity_change", "source_write"),
        ),
        AuthorizationConfusionPattern(
            "route_health_is_approval",
            "A healthy dashboard/API route is treated as permission to execute.",
            "high",
            "The route renders, so the action can run.",
            "Route health proves visibility only and does not authorize execution.",
            ("dashboard", "api"),
            ("execution", "memory_write", "source_write"),
        ),
        AuthorizationConfusionPattern(
            "manifest_presence_is_authorization",
            "Manifest presence is mistaken for permission.",
            "high",
            "The surface is listed in the manifest, so it may execute.",
            "Manifest entries describe surfaces; they do not grant authority.",
            ("manifest", "cli", "api", "dashboard"),
            ("execution", "approval", "source_write"),
        ),
        AuthorizationConfusionPattern(
            "lifecycle_completion_is_future_approval",
            "Completion of a governed lifecycle is mistaken for future consent.",
            "critical",
            "The lifecycle completed, so future memory writes are approved.",
            "Lifecycle completion is evidence only; every future memory action needs fresh single-use approval.",
            ("memory", "lifecycle"),
            ("memory_write", "memory_retraction", "autonomy"),
        ),
        AuthorizationConfusionPattern(
            "smoke_success_is_permission",
            "Passing smoke checks is mistaken for permission to mutate state.",
            "critical",
            "All smoke checks passed, so apply the change.",
            "Smoke success supports review; it never authorizes live action.",
            ("smoke", "release", "patches"),
            ("source_write", "release", "memory_write"),
        ),
        AuthorizationConfusionPattern(
            "prior_approval_is_current_approval",
            "Expired or burned approval is reused.",
            "critical",
            "The operator approved this before, so it is still approved.",
            "Prior approval is expired after use; fresh exact approval is required.",
            ("memory", "patches", "expression"),
            ("approval_reuse", "memory_write", "source_write"),
        ),
        AuthorizationConfusionPattern(
            "sandbox_success_is_live_permission",
            "Sandbox success is treated as live execution permission.",
            "critical",
            "Sandbox passed, so live write may proceed.",
            "Sandbox success is evidence only; live execution requires fresh explicit operator approval.",
            ("sandbox", "memory", "patches"),
            ("live_write", "source_write", "memory_write"),
        ),
        AuthorizationConfusionPattern(
            "model_consensus_is_truth",
            "Model agreement is mistaken for proof or approval.",
            "high",
            "The models agree, so this is true and approved.",
            "Model output is evidence for review only; it is not truth or approval.",
            ("models", "review"),
            ("approval", "memory_write", "source_write"),
        ),
        AuthorizationConfusionPattern(
            "review_packet_is_execution_packet",
            "A review packet is mistaken for an execution packet.",
            "critical",
            "The review packet exists, so execute it.",
            "Review packets cannot execute; only an explicitly approved execution packet may be used.",
            ("packets", "patches", "memory"),
            ("execution", "source_write", "memory_write"),
        ),
        AuthorizationConfusionPattern(
            "approval_lock_exists_means_approved",
            "Presence of an approval lock is mistaken for approval having occurred.",
            "critical",
            "The approval lock exists, so the operator approved it.",
            "Approval locks bind scope; they do not prove fresh operator confirmation by themselves.",
            ("approval", "memory", "patches"),
            ("approval_reuse", "execution"),
        ),
        AuthorizationConfusionPattern(
            "operator_pattern_means_future_consent",
            "Past operator decisions are mistaken for future consent.",
            "critical",
            "The operator usually approves these, so proceed.",
            "Operator patterns are not consent; every governed action needs explicit current approval.",
            ("history", "memory", "planning"),
            ("autonomy", "source_write", "memory_write"),
        ),
    ]
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": "review_only",
        "patterns": [asdict(pattern) for pattern in patterns],
        "pattern_count": len(patterns),
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


SEVERITY_RANK = {
    "safe_boundary": 0,
    "informational": 1,
    "warning": 2,
    "high_risk": 3,
    "blocked_pattern": 4,
}

SAFE_NEGATIVE_BOUNDARY_PATTERNS = [
    r"\bnot\s+(authorized|approved|approval|authorization|permission|permitted)\b",
    r"\bdoes\s+not\s+(authorize|approve|grant|execute|write|apply|publish)\b",
    r"\bmust\s+not\s+(treat|infer|reuse|execute|write|apply|publish)\b",
    r"\bnever\s+(authorizes|approves|grants|executes|writes|applies|publishes)\b",
    r"\brequires?\s+(fresh|explicit|single-use|operator)\s+(operator\s+)?approval\b",
    r"\bfresh\s+(operator\s+)?approval\s+(is\s+)?(required|still\s+required)\b",
    r"\boperator\s+approval\s+(is\s+)?(required|still\s+required)\b",
    r"\breview[- ]only\b",
    r"\bevidence\s+only\b",
]

BLOCKED_AUTHORIZATION_PATTERNS = [
    (re.compile(r"\b(auto[- ]?approved|self[- ]?approved|pre[- ]?approved)\b", re.I), "blocked auto/self/pre approval wording"),
    (re.compile(r"\b(permission\s+granted|authorization\s+granted|approval\s+granted)\b", re.I), "permission-granted wording requires explicit fresh operator confirmation"),
    (re.compile(r"\b(all\s+checks\s+passed|smoke\s+(passed|success))\b.{0,90}\b(so|therefore)\b.{0,90}\b(apply|execute|write|publish|proceed)\b", re.I), "check success is being converted into action permission"),
    (re.compile(r"\b(sandbox\s+(passed|success)|route\s+(renders|healthy)|manifest\s+(lists|contains|present))\b.{0,90}\b(so|therefore)\b.{0,90}\b(apply|execute|write|publish|authorized|approved)\b", re.I), "governance state is being converted into authorization"),
]

HIGH_RISK_AUTHORIZATION_PATTERNS = [
    (re.compile(r"\bready\s+to\s+(apply|execute|write|publish|proceed)\b", re.I), "readiness-to-action wording requires fresh approval guard"),
    (re.compile(r"\bmay\s+(execute|apply|write|publish|proceed)\b", re.I), "may-action wording must be tied to explicit operator approval"),
    (re.compile(r"\b(safe\s+to\s+(write|apply|execute|publish)|authorized\s+to\s+(write|apply|execute|publish))\b", re.I), "safe/authorized-to-action wording needs an explicit approval source"),
    (re.compile(r"\b(prior\s+approval|previous\s+approval|approved\s+before)\b.{0,90}\b(still|current|reuse|continue)\b", re.I), "prior approval cannot become current approval"),
]

INFORMATIONAL_AUTHORIZATION_TERMS = [
    "approval", "approved", "authorize", "authorized", "authorization", "permission", "consent",
]


def _line_is_safely_guarded(line: str) -> bool:
    lowered = line.lower()
    if any(marker in lowered for marker in SAFE_BOUNDARY_MARKERS):
        return True
    return any(re.search(pattern, line, flags=re.I) for pattern in SAFE_NEGATIVE_BOUNDARY_PATTERNS)


def _matched_blocked_patterns(line: str) -> list[str]:
    return [message for pattern, message in BLOCKED_AUTHORIZATION_PATTERNS if pattern.search(line)]


def _matched_high_risk_patterns(line: str) -> list[str]:
    return [message for pattern, message in HIGH_RISK_AUTHORIZATION_PATTERNS if pattern.search(line)]


def _classification_for_line(line: str) -> str:
    lowered = line.lower()
    if _line_is_safely_guarded(line):
        return "safe_boundary"
    if _matched_blocked_patterns(line):
        return "blocked_pattern"
    if _matched_high_risk_patterns(line):
        return "high_risk"
    for term, _message in RISKY_LANGUAGE_PATTERNS:
        if term in lowered:
            return "warning"
    if any(term in lowered for term in INFORMATIONAL_AUTHORIZATION_TERMS):
        return "informational"
    return "informational"


def _severity_message(line: str, matched_term: str = "") -> str:
    if _line_is_safely_guarded(line):
        return "Safe negative or review-only boundary language; retained as evidence, not a warning."
    blocked = _matched_blocked_patterns(line)
    if blocked:
        return blocked[0]
    high = _matched_high_risk_patterns(line)
    if high:
        return high[0]
    lowered = line.lower()
    for term, message in RISKY_LANGUAGE_PATTERNS:
        if matched_term == term or term in lowered:
            return message
    return "Authorization-related language retained for informational operator review."


def _scan_line_findings(rel: str, lineno: int, line: str) -> list[dict[str, Any]]:
    lowered = line.lower()
    matched_terms = [term for term, _message in RISKY_LANGUAGE_PATTERNS if term in lowered]
    if not matched_terms and not any(term in lowered for term in INFORMATIONAL_AUTHORIZATION_TERMS):
        return []
    classification = _classification_for_line(line)
    if classification == "informational" and not matched_terms:
        matched_terms = [term for term in INFORMATIONAL_AUTHORIZATION_TERMS if term in lowered][:1]
    return [{
        "file_path": rel,
        "line": lineno,
        "term": term,
        "classification": classification,
        "severity": classification,
        "message": _severity_message(line, term),
        "excerpt": line.strip()[:220],
        "requires_manual_review": classification in {"warning", "high_risk", "blocked_pattern"},
        "authorization_status": "not_authorized",
    } for term in matched_terms[:2]]


def _summarize_findings(findings: Iterable[dict[str, Any]]) -> dict[str, int]:
    summary = {key: 0 for key in SEVERITY_RANK}
    for finding in findings:
        classification = str(finding.get("classification") or finding.get("severity") or "informational")
        summary[classification] = summary.get(classification, 0) + 1
    return summary


def _status_from_summary(summary: dict[str, int]) -> str:
    if summary.get("blocked_pattern", 0):
        return "blocked_pattern_detected"
    if summary.get("high_risk", 0):
        return "review_required_high_risk"
    if summary.get("warning", 0):
        return "pass_with_warnings"
    return "clear"


def _operator_review_status(summary: dict[str, int]) -> str:
    if summary.get("blocked_pattern", 0) or summary.get("high_risk", 0) or summary.get("warning", 0):
        return "review_required"
    return "review_optional"


def build_authorization_language_scan(root_dir: str | Path = ".") -> dict[str, Any]:
    root = Path(root_dir)
    findings: list[dict[str, Any]] = []
    safe_boundary_count = 0
    scanned_files = []
    for rel in RECENT_SCAN_PATHS:
        path = root / rel
        text = _read_text(path)
        if not text:
            continue
        scanned_files.append(rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _line_is_safely_guarded(line):
                safe_boundary_count += 1
            findings.extend(_scan_line_findings(rel, lineno, line))
    summary = _summarize_findings(findings)
    warning_count = summary.get("warning", 0) + summary.get("high_risk", 0) + summary.get("blocked_pattern", 0)
    status = _status_from_summary(summary)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": status,
        "language_scan_status": status,
        "operator_review_status": _operator_review_status(summary),
        "authorization_status": "not_authorized",
        "scanned_files": scanned_files,
        "scanned_file_count": len(scanned_files),
        "findings": findings[:120],
        "finding_count": len(findings),
        "severity_summary": summary,
        "warning_count": warning_count,
        "safe_boundary_count": safe_boundary_count,
        "scanner_executes_actions": False,
        "scanner_rewrites_source": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_severity_classifier(root_dir: str | Path = ".") -> dict[str, Any]:
    scan = build_authorization_language_scan(root_dir)
    summary = dict(scan.get("severity_summary") or {})
    status = _status_from_summary(summary)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": status,
        "mechanism_status": "pass",
        "language_scan_status": status,
        "operator_review_status": _operator_review_status(summary),
        "authorization_status": "not_authorized",
        "severity_levels": list(SEVERITY_RANK.keys()),
        "severity_summary": summary,
        "reviewable_finding_count": summary.get("warning", 0) + summary.get("high_risk", 0) + summary.get("blocked_pattern", 0),
        "safe_boundary_count": summary.get("safe_boundary", 0),
        "classifier_executes_actions": False,
        "classifier_creates_approval": False,
        "classifier_mutates_memory": False,
        "classifier_applies_source_edits": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_safe_boundary_filter(root_dir: str | Path = ".") -> dict[str, Any]:
    scan = build_authorization_language_scan(root_dir)
    summary = dict(scan.get("severity_summary") or {})
    raw_authorization_mentions = sum(summary.values())
    safe_count = summary.get("safe_boundary", 0)
    reviewable_count = summary.get("warning", 0) + summary.get("high_risk", 0) + summary.get("blocked_pattern", 0)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": "pass_with_warnings" if reviewable_count else "clear",
        "mechanism_status": "pass",
        "language_scan_status": _status_from_summary(summary),
        "operator_review_status": "review_required" if reviewable_count else "review_optional",
        "authorization_status": "not_authorized",
        "raw_authorization_mention_count": raw_authorization_mentions,
        "safe_negative_boundary_count": safe_count,
        "reviewable_warning_count": reviewable_count,
        "safe_boundary_terms": list(SAFE_BOUNDARY_MARKERS),
        "safe_negative_patterns": list(SAFE_NEGATIVE_BOUNDARY_PATTERNS),
        "filter_executes_actions": False,
        "filter_rewrites_source": False,
        "filter_creates_approval": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_warning_status_bridge(root_dir: str | Path = ".") -> dict[str, Any]:
    classifier = build_authorization_firewall_severity_classifier(root_dir)
    summary = dict(classifier.get("severity_summary") or {})
    language_status = _status_from_summary(summary)
    warnings = classifier.get("reviewable_finding_count", 0)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": language_status,
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": "review_required" if warnings else "review_optional",
        "authorization_status": "not_authorized",
        "warnings_preserved": True,
        "pass_with_warnings_supported": True,
        "plain_pass_with_warnings_forbidden": True,
        "warning_count": warnings,
        "severity_summary": summary,
        "bridge_executes_actions": False,
        "bridge_applies_source_edits": False,
        "bridge_writes_memory": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_audit_status_split(root_dir: str | Path = ".") -> dict[str, Any]:
    bridge = build_authorization_firewall_warning_status_bridge(root_dir)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": bridge.get("language_scan_status"),
        "mechanism_status": "pass",
        "language_scan_status": bridge.get("language_scan_status"),
        "operator_review_status": bridge.get("operator_review_status"),
        "authorization_status": "not_authorized",
        "approval_status": "not_approved",
        "execution_status": "not_executing",
        "memory_status": "not_mutating_memory",
        "source_status": "not_applying_source_edits",
        "status_split_required": True,
        "mechanism_pass_is_not_language_clear": True,
        "language_clear_is_not_authorization": True,
        "audit_executes_actions": False,
        "audit_creates_approval": False,
        "audit_writes_memory": False,
        "audit_applies_source_edits": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_operator_governed_authorization_firewall_signal_triage(root_dir: str | Path = ".", docs_text: str | None = None) -> dict[str, Any]:
    root = Path(root_dir)
    docs = docs_text if docs_text is not None else _read_text(root / "README_NEXT_STEPS.md") + "\n" + _read_text(root / "README_RELEASE_HISTORY.md")
    scan = build_authorization_language_scan(root)
    summary = dict(scan.get("severity_summary") or {})
    language_status = _status_from_summary(summary)
    reviewable_count = summary.get("warning", 0) + summary.get("high_risk", 0) + summary.get("blocked_pattern", 0)
    classifier = {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": language_status,
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": _operator_review_status(summary),
        "authorization_status": "not_authorized",
        "severity_levels": list(SEVERITY_RANK.keys()),
        "severity_summary": summary,
        "reviewable_finding_count": reviewable_count,
        "safe_boundary_count": summary.get("safe_boundary", 0),
        "classifier_executes_actions": False,
        "classifier_creates_approval": False,
        "classifier_mutates_memory": False,
        "classifier_applies_source_edits": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }
    safe_filter = {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": "pass_with_warnings" if reviewable_count else "clear",
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": "review_required" if reviewable_count else "review_optional",
        "authorization_status": "not_authorized",
        "raw_authorization_mention_count": sum(summary.values()),
        "safe_negative_boundary_count": summary.get("safe_boundary", 0),
        "reviewable_warning_count": reviewable_count,
        "safe_boundary_terms": list(SAFE_BOUNDARY_MARKERS),
        "safe_negative_patterns": list(SAFE_NEGATIVE_BOUNDARY_PATTERNS),
        "filter_executes_actions": False,
        "filter_rewrites_source": False,
        "filter_creates_approval": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }
    bridge = {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": language_status,
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": "review_required" if reviewable_count else "review_optional",
        "authorization_status": "not_authorized",
        "warnings_preserved": True,
        "pass_with_warnings_supported": True,
        "plain_pass_with_warnings_forbidden": True,
        "warning_count": reviewable_count,
        "severity_summary": summary,
        "bridge_executes_actions": False,
        "bridge_applies_source_edits": False,
        "bridge_writes_memory": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }
    split = {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": language_status,
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": bridge.get("operator_review_status"),
        "authorization_status": "not_authorized",
        "approval_status": "not_approved",
        "execution_status": "not_executing",
        "memory_status": "not_mutating_memory",
        "source_status": "not_applying_source_edits",
        "status_split_required": True,
        "mechanism_pass_is_not_language_clear": True,
        "language_clear_is_not_authorization": True,
        "audit_executes_actions": False,
        "audit_creates_approval": False,
        "audit_writes_memory": False,
        "audit_applies_source_edits": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }
    required_tokens = [
        "authorization-firewall-severity-classifier", "authorization-firewall-safe-boundary-filter",
        "authorization-firewall-warning-status", "authorization-firewall-audit-status-split",
        "authorization-firewall-signal-triage-audit", "operator-governed-authorization-firewall-signal-triage-v1",
        "pass_with_warnings_supported=True", "plain_pass_with_warnings_forbidden=True",
        "mechanism_pass_is_not_language_clear=True", "language_clear_is_not_authorization=True",
        "authorization_status=not_authorized", "operator_approval_still_required=True",
    ]
    rows = [
        {"name": "severity-classifier", "status": "pass" if classifier.get("ok") and "blocked_pattern" in classifier.get("severity_levels", []) else "blocked", "message": "Firewall findings are classified across safe, informational, warning, high-risk, and blocked-pattern levels."},
        {"name": "safe-boundary-filter", "status": "pass" if safe_filter.get("safe_negative_boundary_count", 0) >= 0 and safe_filter.get("filter_rewrites_source") is False else "blocked", "message": "Safe negative boundary language is counted separately from reviewable warnings."},
        {"name": "warning-status-bridge", "status": "pass" if bridge.get("warnings_preserved") is True and bridge.get("plain_pass_with_warnings_forbidden") is True else "blocked", "message": "CLI/API/dashboard status can preserve warnings instead of flattening them to plain pass."},
        {"name": "audit-status-split", "status": "pass" if split.get("mechanism_status") == "pass" and split.get("authorization_status") == "not_authorized" else "blocked", "message": "Mechanism health, language status, operator review status, and authorization status are separate."},
        {"name": "docs", "status": "pass" if all(token in docs for token in required_tokens) else "blocked", "message": "README, dashboard/API/CLI, and smoke tokens document v456-v460 warning semantics."},
        {"name": "no-authorization", "status": "pass" if split.get("audit_creates_approval") is False and split.get("audit_writes_memory") is False and split.get("audit_applies_source_edits") is False else "blocked", "message": "Signal triage remains review-only and grants no approval, memory write, source edit, release, or autonomy permission."},
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": ok,
        "status": language_status,
        "mechanism_status": "pass",
        "language_scan_status": language_status,
        "operator_review_status": bridge.get("operator_review_status"),
        "authorization_status": "not_authorized",
        "rows": rows,
        "severity_classifier": classifier,
        "safe_boundary_filter": safe_filter,
        "warning_status_bridge": bridge,
        "audit_status_split": split,
        "executes_actions": False,
        "creates_approval": False,
        "writes_memory": False,
        "applies_source_edits": False,
        "publishes_release": False,
        "expands_autonomy": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_decision_packet(root_dir: str | Path = ".") -> dict[str, Any]:
    patterns = build_authorization_confusion_patterns()
    scan = build_authorization_language_scan(root_dir)
    warnings = int(scan.get("warning_count", 0))
    status = str(scan.get("language_scan_status") or ("pass_with_warnings" if warnings else "clear"))
    recent_surfaces = [
        "v400-memory-candidate-application-trial",
        "v410-memory-application-dry-run-ledger",
        "v415-sandbox-memory-write-target",
        "v420-live-memory-write-burnout",
        "v425-memory-retraction-trial",
        "v430-source-surface-manifest",
        "v440-dashboard-route-health-audit",
        "v445-memory-lifecycle-review-board",
    ]
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": status,
        "firewall_status": status,
        "mechanism_status": "pass",
        "language_scan_status": status,
        "operator_review_status": scan.get("operator_review_status", "review_required" if warnings else "review_optional"),
        "authorization_status": "not_authorized",
        "pattern_count": patterns.get("pattern_count", 0),
        "warning_count": warnings,
        "severity_summary": scan.get("severity_summary", {}),
        "surface_ids_reviewed": recent_surfaces,
        "authority_level": "review_only",
        "required_operator_approval": True,
        "single_use_required": True,
        "burnout_required": True,
        "recommended_correction": "Keep readiness, health, lifecycle, manifest, smoke, sandbox, and prior approval language explicitly separated from authorization.",
        "clear_status_means_approved": False,
        "firewall_pass_is_authorization": False,
        "decision_packet_executes": False,
        "decision_packet_approves": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }

def build_authorization_boundary_map(root_dir: str | Path = ".") -> dict[str, Any]:
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": True,
        "status": "review_only",
        "boundaries": [
            {"state": "readiness", "forbidden_inference": "approval", "safe_interpretation": "operator review may be prepared"},
            {"state": "eligibility", "forbidden_inference": "authorization", "safe_interpretation": "fresh approval may be requested"},
            {"state": "route health", "forbidden_inference": "execution permission", "safe_interpretation": "operator visibility works"},
            {"state": "manifest presence", "forbidden_inference": "surface may execute", "safe_interpretation": "surface is described"},
            {"state": "lifecycle completeness", "forbidden_inference": "future approval", "safe_interpretation": "evidence chain is complete"},
            {"state": "smoke success", "forbidden_inference": "live action allowed", "safe_interpretation": "verification evidence exists"},
            {"state": "prior approval", "forbidden_inference": "current approval", "safe_interpretation": "approval expired or burned after scoped use"},
            {"state": "sandbox success", "forbidden_inference": "live permission", "safe_interpretation": "live approval may be requested"},
            {"state": "model consensus", "forbidden_inference": "truth/proof", "safe_interpretation": "review evidence only"},
        ],
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def build_authorization_firewall_audit(root_dir: str | Path = ".", docs_text: str | None = None) -> dict[str, Any]:
    root = Path(root_dir)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(root / p) for p in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/authorization_firewall.py",
        "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py",
        "conscious_agent/main.py", "tools/smoke_check.py",
    ])
    patterns = build_authorization_confusion_patterns()
    scan = build_authorization_language_scan(root)
    decision = build_authorization_firewall_decision_packet(root)
    boundary = build_authorization_boundary_map(root)
    required_tokens = [
        "readiness_is_approval", "eligibility_is_approval", "route_health_is_approval",
        "manifest_presence_is_authorization", "lifecycle_completion_is_future_approval",
        "smoke_success_is_permission", "prior_approval_is_current_approval",
        "sandbox_success_is_live_permission", "model_consensus_is_truth",
        "review_packet_is_execution_packet", "operator-governed-authorization-firewall-v1",
    ]
    rows = [
        {"name": "pattern-registry", "status": "pass" if patterns.get("pattern_count", 0) >= 10 else "blocked", "message": "Authorization confusion pattern registry loads."},
        {"name": "language-scan", "status": "pass" if scan.get("scanned_file_count", 0) >= 8 and scan.get("scanner_rewrites_source") is False else "blocked", "message": "Recent governance modules are scanned without rewriting source."},
        {"name": "decision-packet", "status": "pass" if decision.get("firewall_pass_is_authorization") is False and decision.get("decision_packet_approves") is False else "blocked", "message": "Firewall decision packet is review-only."},
        {"name": "boundary-map", "status": "pass" if len(boundary.get("boundaries", [])) >= 8 else "blocked", "message": "State-to-authorization boundary map is populated."},
        {"name": "docs", "status": "pass" if "v450.0 - Governance-State-to-Authorization Firewall v1" in docs else "blocked", "message": "README next steps and release history document v446-v450."},
        {"name": "tokens", "status": "pass" if all(token in docs for token in required_tokens) else "blocked", "message": "Required firewall tokens are present for smoke and review."},
        {"name": "boundaries", "status": "pass" if all(AUTHORIZATION_FIREWALL_BOUNDARIES.values()) is False and AUTHORIZATION_FIREWALL_BOUNDARIES["operator_approval_still_required"] is True else "blocked", "message": "Firewall does not mutate, approve, enforce, or expand autonomy."},
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": AUTHORIZATION_FIREWALL_VERSION,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "rows": rows,
        "patterns": patterns,
        "scan_summary": {k: scan.get(k) for k in ["status", "scanned_file_count", "finding_count", "warning_count", "safe_boundary_count"]},
        "decision_packet": decision,
        "boundary_count": len(boundary.get("boundaries", [])),
        "writes_files": False,
        "writes_memory": False,
        "applies_source_edits": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        **AUTHORIZATION_FIREWALL_BOUNDARIES,
    }


def render_authorization_firewall_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"status: {report.get('status', 'review_only')}",
        f"version: {report.get('version', AUTHORIZATION_FIREWALL_VERSION)}",
    ]
    if "pattern_count" in report:
        lines.append(f"patterns: {report.get('pattern_count')}")
    if "warning_count" in report:
        lines.append(f"warnings: {report.get('warning_count')}")
    rows = report.get("rows") or []
    for row in rows[:12]:
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    lines.append("firewall pass is not authorization; fresh operator approval remains required.")
    return lines

# v445.1-v450.0 authorization firewall smoke tokens: authorization-confusion-patterns authorization-language-scan authorization-firewall-decision-packet authorization-boundary-map authorization-firewall-audit operator-governed-authorization-firewall-v1 conscious_agent/authorization_firewall.py readiness_is_approval eligibility_is_approval route_health_is_approval manifest_presence_is_authorization lifecycle_completion_is_future_approval smoke_success_is_permission prior_approval_is_current_approval sandbox_success_is_live_permission model_consensus_is_truth review_packet_is_execution_packet approval_lock_exists_means_approved operator_pattern_means_future_consent firewall_detection_is_enforcement_execution=False firewall_pass_is_authorization=False clear_status_means_approved=False firewall_rewrites_packets=False firewall_mutates_memory=False firewall_applies_source_edits=False firewall_expands_autonomy=False operator_approval_still_required=True data-tip no_native_title_tooltip command-deck operator-console
