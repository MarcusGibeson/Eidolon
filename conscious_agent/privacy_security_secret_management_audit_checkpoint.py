from __future__ import annotations

"""Read-only v1247.9 Privacy, Security, and Secret-Management Audit checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from privacy_security_secret_management_audit import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_privacy_security_secret_management_contract,
    privacy_security_audit_dashboard_record,
    privacy_security_secret_management_registry,
    render_privacy_security_audit_dashboard_html,
    scan_source_package_privacy,
    scan_source_tree_for_secret_findings,
)

CONTRACT_VERSION = "v1247.9"
CHECKPOINT_ID = "privacy-security-secret-management-audit-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {"data", "__pycache__", ".git"} for part in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        rows.append(f"{rel}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name)
                and target.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"}
                for target in node.targets
            ):
                names.update(ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_privacy_security_secret_management_audit_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, count_before = _signature(source)
    contract = build_privacy_security_secret_management_contract()
    registry = privacy_security_secret_management_registry()
    dashboard = privacy_security_audit_dashboard_record()
    page = render_privacy_security_audit_dashboard_html()
    source_scan = scan_source_tree_for_secret_findings(source)
    package_scan = scan_source_package_privacy(source)
    descriptor = next((row for row in inspect_checkpoint_registry(source_root=source).get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID), {})
    names = (
        "conscious_agent/release_metadata.py", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md",
        "tools/release_verify.py", "conscious_agent/api_server.py", "eidolon.py",
        "conscious_agent/ordinary_chat_development_campaign.py", "conscious_agent/dashboard.py",
        "conscious_agent/unified_operator_dashboard.py",
    )
    files = {name: (source / name).read_text(encoding="utf-8") for name in names}
    stages = {
        "v1247.2-privacy-security-secret-management-audit-foundations",
        "v1247.5-privacy-security-secret-management-operator-workflows",
        "v1247.8-privacy-security-secret-management-adversarial-reliability",
        "v1247.9-privacy-security-secret-management-audit-checkpoint",
    }
    docs = (
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1247_0_2.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1247_3_5.md", "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1247_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1247_9_FINAL_VALIDATION.md", "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1247_9.md",
    )
    checks = {
        "contract_ok": contract.get("ok") is True,
        "registry_ok": registry.get("ok") is True,
        "registry_inspection_only": registry.get("inspection_only") is True,
        "eight_classifications": contract.get("eight_finding_classifications") is True and len(registry.get("finding_classifications") or []) == 8,
        "secret_categories": len(registry.get("secret_categories") or []) >= 12,
        "redacted_findings": contract.get("redacted_secret_findings") is True and registry.get("redacted_findings_only") is True,
        "source_scan_ok": source_scan.get("ok") is True,
        "source_scan_no_high_risk": source_scan.get("confirmed_or_likely_count") == 0,
        "source_scan_no_values": source_scan.get("secret_values_returned") is False and source_scan.get("matched_text_returned") is False,
        "package_scan_ok": package_scan.get("ok") is True,
        "package_scan_no_forbidden": package_scan.get("root_forbidden_count") == 0,
        "package_scan_no_private_content": package_scan.get("root_private_content_finding_count") == 0,
        "dashboard_read_only": dashboard.get("read_only") is True and dashboard.get("get_only") is True,
        "dashboard_page": "Privacy, Security, and Secret-Management Audit" in page and "Secret values and matched text are never displayed" in page,
        "metadata": 'WORKING_SOURCE_VERSION = "1247.9"' in files["conscious_agent/release_metadata.py"] and "v1247.9 Privacy, Security, and Secret-Management Audit Checkpoint" in files["conscious_agent/release_metadata.py"] and "v1248.0-v1248.2 Integrated Mind, Conversation, and Development Benchmark Foundations" in files["conscious_agent/release_metadata.py"],
        "readmes": "v1247.9" in files["README_NEXT_STEPS.md"] and "v1247.9 Privacy, Security, and Secret-Management Audit" in files["README_RELEASE_HISTORY.md"],
        "chat": "process_privacy_security_audit_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api": all(token in files["conscious_agent/api_server.py"] for token in ("privacy-security-secret-management-registry", "privacy-security-audits", "privacy-security-audit-reviews", "secret-management-remediation-proposals", "secret-management-remediation-reviews", CHECKPOINT_ID)),
        "cli": all(f'"{token}"' in files["eidolon.py"] for token in ("privacy-security-secret-management-registry", "privacy-security-audits", "privacy-security-audit-reviews", "secret-management-remediation-proposals", "secret-management-remediation-reviews", CHECKPOINT_ID)),
        "dashboard_routes": "/privacy-security-audit" in files["conscious_agent/dashboard.py"] and "/api/privacy-security-audit" in files["conscious_agent/dashboard.py"],
        "unified_dashboard_integration": "privacy-security-audits" in files["conscious_agent/unified_operator_dashboard.py"],
        "release_stages": stages.issubset(_quick_stage_names(files["tools/release_verify.py"])),
        "release_commands": all(stage in files["tools/release_verify.py"] for stage in stages),
        "docs": all((source / name).is_file() for name in docs),
        "registry_present": bool(descriptor),
        "registry_version": descriptor.get("contract_version") == CONTRACT_VERSION,
        "registry_read_only": descriptor.get("read_only") is True,
        "registry_no_inputs": descriptor.get("required_input_count") == 0,
    }
    for key, expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"] = contract.get(key) is expected and registry.get(key) is expected and dashboard.get(key) is expected
    after, count_after = _signature(source)
    checks["source_unchanged"] = before == after and count_before == count_after
    passed = sum(map(bool, checks.values()))
    total = len(checks)
    ok = passed == total
    return {
        "ok": ok,
        "status": "privacy_security_secret_management_audit_checkpoint_ready" if ok else "privacy_security_secret_management_audit_checkpoint_blocked",
        "checkpoint_id": CHECKPOINT_ID,
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "passed": passed,
        "total": total,
        "checks": checks,
        "source_scan_summary": {key: source_scan.get(key) for key in ("status", "scanned_file_count", "finding_count", "classification_counts", "confirmed_or_likely_count", "scan_digest")},
        "package_scan_summary": {key: package_scan.get(key) for key in ("status", "root_forbidden_count", "root_private_content_finding_count", "package_scan_digest")},
        "source_signature_before": before,
        "source_signature_after": after,
        "source_signature_unchanged": before == after,
        "source_file_count_before": count_before,
        "source_file_count_after": count_after,
        "read_only": True,
        "content_free": True,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "secret_values_returned": False,
        "source_modified": False,
        "authority_granted": False,
        **AUTHORITY_FLAGS,
    }
