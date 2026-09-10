from __future__ import annotations

"""v1247 Privacy, Security, and Secret-Management Audit.

The module prepares redacted, content-free audit evidence and operator-reviewed
remediation proposals.  It may read source/package evidence during an explicit
inspection, but it never returns matched values, rotates credentials, deletes
files, contacts providers, mutates packages, or grants execution authority.
"""

import hashlib
import html
import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from package_integrity import package_privacy_summary_for_root, package_privacy_summary_for_zip
from security_privacy_hardening_foundations import is_link_or_reparse

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1247.8"
MILESTONE_NAME = "Privacy, Security, and Secret-Management Audit"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
MAX_RECORDS = 500

SECRET_CATEGORIES = {
    "credential", "api_key", "access_token", "session_secret", "private_key",
    "certificate", "environment_file", "private_user_data", "private_project_data",
    "provider_prompt", "provider_response", "log_receipt", "backup_crash_artifact",
    "runtime_configuration", "sensitive_path_identifier",
}
FINDING_CLASSIFICATIONS = {
    "confirmed_secret", "likely_secret", "sensitive_metadata", "synthetic_test_canary",
    "allowed_public_identifier", "false_positive", "unverified_finding", "remediated_finding",
}
REMEDIATION_ACTIONS = {"redact", "rotate", "delete", "quarantine", "operator_review", "none"}
AUDIT_REVIEW_DISPOSITIONS = {"accept_findings", "hold", "reject", "request_changes"}
REMEDIATION_REVIEW_DISPOSITIONS = {"accept_plan", "defer", "reject", "request_changes"}

AUTHORITY_FLAGS = {
    "privacy_security_inspection_authorized": True,
    "redacted_audit_preparation_authorized": True,
    "audit_review_authorized": True,
    "remediation_proposal_preparation_authorized": True,
    "remediation_review_authorized": True,
    "secret_value_disclosure_authorized": False,
    "credential_rotation_authorized": False,
    "file_deletion_authorized": False,
    "quarantine_execution_authorized": False,
    "package_mutation_authorized": False,
    "provider_contact_authorized": False,
    "prompt_transmission_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "cognition_write_authorized": False,
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
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_\-]{1,96}$")
_PROJECT = re.compile(r"^project_[a-z0-9_\-]{2,64}$")
_AUDIT = re.compile(r"^privacy_security_audit_[a-f0-9]{24}$")
_AUDIT_REVIEW = re.compile(r"^privacy_security_audit_review_[a-f0-9]{24}$")
_REMEDIATION = re.compile(r"^secret_remediation_proposal_[a-f0-9]{24}$")
_REMEDIATION_REVIEW = re.compile(r"^secret_remediation_review_[a-f0-9]{24}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PRIVATE_FIELD_TOKENS = {
    "secret", "secret_value", "value", "password", "credential_value", "token_value",
    "prompt", "response", "content", "source_text", "matched_text", "raw", "absolute_path",
    "private_key_value", "certificate_value", "environment_value",
}

_SHOW_REGISTRY = re.compile(r"^show privacy security audit registry[.!?]*$", re.I)
_SHOW_AUDITS = re.compile(r"^show privacy security audits[.!?]*$", re.I)
_SHOW_AUDIT_REVIEWS = re.compile(r"^show privacy security audit reviews[.!?]*$", re.I)
_SHOW_REMEDIATIONS = re.compile(r"^show secret management remediation proposals[.!?]*$", re.I)
_SHOW_REMEDIATION_REVIEWS = re.compile(r"^show secret management remediation reviews[.!?]*$", re.I)
_REVIEW_AUDIT = re.compile(
    r"^review privacy security audit (?P<disposition>accept_findings|hold|reject|request_changes) "
    r"for audit (?P<audit>privacy_security_audit_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVIEW_REMEDIATION = re.compile(
    r"^review secret remediation (?P<disposition>accept_plan|defer|reject|request_changes) "
    r"for proposal (?P<proposal>secret_remediation_proposal_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("api_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("access_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("access_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("credential", re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|secret|access[_-]?token)\b\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']")),
)
_SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", "credentials.json", "secrets.json",
    "id_rsa", "id_ed25519", "private.pem", "private.key",
}
_TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg",
    ".js", ".ts", ".java", ".cs", ".go", ".rs", ".php", ".sh", ".ps1", ".html", ".css",
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "privacy-security-secret-management-audit.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for privacy-security audit lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").strip().lower()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _token(value: Any, reason: str, *, pattern: re.Pattern[str] = _TOKEN) -> str:
    text = str(value or "").strip().lower()
    if not pattern.fullmatch(text):
        raise ValueError(reason)
    return text


def _score(value: Any, reason: str) -> float:
    try:
        number = round(float(value), 4)
    except (TypeError, ValueError):
        raise ValueError(reason)
    if number < 0 or number > 1:
        raise ValueError(reason)
    return number


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "secret_values_returned": False,
        "matched_text_returned": False,
        "absolute_paths_returned": False,
        "runtime_records_external": True,
        "historical_records_immutable": True,
        "exact_lineage_required": True,
        "operator_review_required_for_remediation": True,
        "secret_values_disclosed": False,
        "credentials_rotated": False,
        "files_deleted": False,
        "quarantine_executed": False,
        "package_modified": False,
        "provider_contacted": False,
        "prompt_transmitted": False,
        "tool_invoked": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "cognition_written": False,
        "session_launched": False,
        "session_resumed": False,
        "automatic_retry_created": False,
        "background_continuation_created": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["privacy_security_result_digest"] = _digest(row)
    return row


def privacy_security_secret_management_registry() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "privacy_security_secret_management_registry_ready",
        "secret_categories": sorted(SECRET_CATEGORIES),
        "finding_classifications": sorted(FINDING_CLASSIFICATIONS),
        "remediation_actions": sorted(REMEDIATION_ACTIONS),
        "audit_review_dispositions": sorted(AUDIT_REVIEW_DISPOSITIONS),
        "remediation_review_dispositions": sorted(REMEDIATION_REVIEW_DISPOSITIONS),
        "inspection_only": True,
        "redacted_findings_only": True,
        **_base(),
    }
    row["registry_digest"] = _digest(row)
    return row


def _classification_for_match(path: Path, line: str, category: str) -> str:
    lowered_path = path.as_posix().lower()
    lowered_line = line.lower()
    if "/tools/" in f"/{lowered_path}" or path.name.startswith("test_") or "_tests.py" in path.name:
        return "synthetic_test_canary"
    if any(token in lowered_line for token in ("synthetic", "fixture", "canary", "example", "regex", "re.compile", "pattern")):
        return "synthetic_test_canary"
    if path.name in {"privacy_security_secret_management_audit.py", "package_integrity.py"}:
        return "synthetic_test_canary"
    if path.suffix.lower() in {".md", ".txt"}:
        return "sensitive_metadata"
    return "likely_secret" if category != "private_key" else "confirmed_secret"


def scan_source_tree_for_secret_findings(source_root: str | Path, *, max_file_bytes: int = 2_000_000) -> dict[str, Any]:
    root_input = Path(source_root).expanduser()
    if is_link_or_reparse(root_input):
        return _failure("privacy_security_source_scan_blocked", "source_root_link_or_reparse")
    root = root_input.resolve()
    findings: list[dict[str, Any]] = []
    scanned_files = 0
    skipped_files = 0
    if not root.exists() or not root.is_dir():
        return _failure("privacy_security_source_scan_blocked", "source_root_missing")
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if is_link_or_reparse(path):
            identity = {
                "category": "sensitive_path_identifier",
                "classification": "sensitive_metadata",
                "location_digest": hashlib.sha256(rel.as_posix().encode()).hexdigest(),
                "evidence_digest": hashlib.sha256((rel.as_posix() + ":link_or_reparse").encode()).hexdigest(),
                "confidence": 0.99,
                "remediation_code": "operator_review",
            }
            identity["finding_id"] = "secret_finding_" + _digest(identity)[:24]
            findings.append(identity)
            skipped_files += 1
            continue
        if not path.is_file():
            continue
        parts = {part.lower() for part in rel.parts}
        if parts.intersection({".git", "__pycache__", "node_modules", "target", "bin", "obj"}) or path.suffix.lower() in {".zip", ".pyc", ".pyo"}:
            skipped_files += 1
            continue
        if path.name.lower() in _SENSITIVE_NAMES or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            classification = "synthetic_test_canary" if "tools" in parts or path.name.startswith("test_") else "sensitive_metadata"
            identity = {
                "category": "environment_file" if path.name.lower().startswith(".env") else "sensitive_path_identifier",
                "classification": classification,
                "location_digest": hashlib.sha256(rel.as_posix().encode()).hexdigest(),
                "evidence_digest": hashlib.sha256((rel.as_posix() + ":filename").encode()).hexdigest(),
                "confidence": 0.95,
                "remediation_code": "operator_review",
            }
            identity["finding_id"] = "secret_finding_" + _digest(identity)[:24]
            findings.append(identity)
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            skipped_files += 1
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                skipped_files += 1
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped_files += 1
            continue
        scanned_files += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            for category, pattern in _SECRET_PATTERNS:
                if not pattern.search(line):
                    continue
                classification = _classification_for_match(rel, line, category)
                remediation = "operator_review" if classification in {"sensitive_metadata", "synthetic_test_canary"} else "rotate"
                identity = {
                    "category": category,
                    "classification": classification,
                    "location_digest": hashlib.sha256(f"{rel.as_posix()}:{line_number}".encode()).hexdigest(),
                    "evidence_digest": hashlib.sha256(f"{rel.as_posix()}:{line_number}:{category}:{classification}".encode()).hexdigest(),
                    "confidence": 0.99 if classification == "confirmed_secret" else 0.85,
                    "remediation_code": remediation,
                }
                identity["finding_id"] = "secret_finding_" + _digest(identity)[:24]
                findings.append(identity)
    unique = {row["finding_id"]: row for row in findings}
    rows = [unique[key] for key in sorted(unique)]
    counts = {classification: sum(row["classification"] == classification for row in rows) for classification in FINDING_CLASSIFICATIONS}
    result = {
        "ok": counts["confirmed_secret"] == 0 and counts["likely_secret"] == 0,
        "status": "privacy_security_source_scan_clear" if counts["confirmed_secret"] == 0 and counts["likely_secret"] == 0 else "privacy_security_source_scan_blocked",
        "scanned_file_count": scanned_files,
        "skipped_file_count": skipped_files,
        "finding_count": len(rows),
        "classification_counts": counts,
        "confirmed_or_likely_count": counts["confirmed_secret"] + counts["likely_secret"],
        "findings": rows,
        "secret_values_returned": False,
        "matched_text_returned": False,
        "absolute_paths_returned": False,
        "read_only": True,
        **_base(),
    }
    result["scan_digest"] = _digest({key: value for key, value in result.items() if key != "scan_digest"})
    return result


def scan_source_package_privacy(source_root: str | Path, *, zip_path: str | Path | None = None) -> dict[str, Any]:
    root_summary = package_privacy_summary_for_root(source_root)
    zip_summary = package_privacy_summary_for_zip(zip_path) if zip_path else None
    active = zip_summary or root_summary
    row = {
        "ok": active.get("ok") is True,
        "status": "source_package_privacy_clear" if active.get("ok") is True else "source_package_privacy_blocked",
        "root_forbidden_count": int(root_summary.get("forbidden_count") or 0),
        "root_private_content_finding_count": int(root_summary.get("private_content_finding_count") or 0),
        "zip_checked": bool(zip_path),
        "zip_forbidden_count": int((zip_summary or {}).get("forbidden_count") or 0),
        "zip_private_content_finding_count": int((zip_summary or {}).get("private_content_finding_count") or 0),
        "forbidden_entry_digests": [hashlib.sha256(str(value).encode()).hexdigest() for value in active.get("forbidden_entries", [])],
        "blocked_content_categories": sorted(str(value) for value in active.get("blocked_content_categories", [])),
        "read_only": True,
        "authorizes_packaging": False,
        **_base(),
    }
    row["package_scan_digest"] = _digest(row)
    return row


def _normalize_finding(raw: Mapping[str, Any]) -> dict[str, Any]:
    extra = set(raw) - {"finding_code", "category", "classification", "location_digest", "evidence_digest", "confidence", "remediation_code", "remediated"}
    if extra or any(str(key).lower() in _PRIVATE_FIELD_TOKENS for key in raw):
        raise ValueError("raw_or_unsupported_finding_field")
    code = _token(raw.get("finding_code"), "invalid_finding_code")
    category = _token(raw.get("category"), "invalid_finding_category")
    classification = _token(raw.get("classification"), "invalid_finding_classification")
    remediation = _token(raw.get("remediation_code"), "invalid_remediation_code")
    if category not in SECRET_CATEGORIES:
        raise ValueError("unsupported_finding_category")
    if classification not in FINDING_CLASSIFICATIONS:
        raise ValueError("unsupported_finding_classification")
    if remediation not in REMEDIATION_ACTIONS:
        raise ValueError("unsupported_remediation_action")
    identity = {
        "finding_code": code,
        "category": category,
        "classification": classification,
        "location_digest": _hex(raw.get("location_digest"), "invalid_location_digest"),
        "evidence_digest": _hex(raw.get("evidence_digest"), "invalid_evidence_digest"),
        "confidence": _score(raw.get("confidence"), "invalid_finding_confidence"),
        "remediation_code": remediation,
        "remediated": bool(raw.get("remediated")),
    }
    identity["finding_id"] = "privacy_finding_" + _digest(identity)[:24]
    return identity


def prepare_privacy_security_audit(
    project_id: str,
    *,
    audit_scope_code: str,
    source_inventory_digest: str,
    package_digest: str,
    trust_boundary_digests: Iterable[str],
    data_flow_digests: Iterable[str],
    retention_policy_digest: str,
    findings: Sequence[Mapping[str, Any]],
    generation: int = 1,
    previous_audit_id: str = "",
    previous_audit_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = _token(project_id, "invalid_project_id", pattern=_PROJECT)
        scope = _token(audit_scope_code, "invalid_audit_scope_code")
        trust = sorted({_hex(value, "invalid_trust_boundary_digest") for value in trust_boundary_digests or []})
        flows = sorted({_hex(value, "invalid_data_flow_digest") for value in data_flow_digests or []})
        if not trust or not flows:
            raise ValueError("trust_boundary_and_data_flow_evidence_required")
        normalized = sorted((_normalize_finding(row) for row in findings or []), key=lambda row: row["finding_id"])
        if not normalized:
            raise ValueError("audit_findings_required")
        generation_number = int(generation)
        if generation_number < 1:
            raise ValueError("invalid_audit_generation")
        previous_id = str(previous_audit_id or "").strip().lower()
        previous_digest = str(previous_audit_digest or "").strip().lower()
        if generation_number == 1 and (previous_id or previous_digest):
            raise ValueError("initial_audit_cannot_have_previous_lineage")
        if generation_number > 1:
            if not (_AUDIT.fullmatch(previous_id) and _HEX64.fullmatch(previous_digest)):
                raise ValueError("revised_audit_requires_exact_previous_lineage")
            previous = load_privacy_security_audit(previous_id, runtime_root=runtime_root)
            if not previous.get("ok") or previous.get("privacy_security_audit_digest") != previous_digest:
                raise ValueError("stale_or_mismatched_previous_audit")
            if previous.get("project_id") != project or int(previous.get("generation") or 0) + 1 != generation_number:
                raise ValueError("invalid_previous_audit_scope_or_generation")
        counts = {classification: sum(row["classification"] == classification for row in normalized) for classification in FINDING_CLASSIFICATIONS}
        identity = {
            "project_id": project,
            "audit_scope_code": scope,
            "source_inventory_digest": _hex(source_inventory_digest, "invalid_source_inventory_digest"),
            "package_digest": _hex(package_digest, "invalid_package_digest"),
            "trust_boundary_digests": trust,
            "data_flow_digests": flows,
            "retention_policy_digest": _hex(retention_policy_digest, "invalid_retention_policy_digest"),
            "findings": normalized,
            "generation": generation_number,
            "previous_audit_id": previous_id,
            "previous_audit_digest": previous_digest,
        }
        audit_id = "privacy_security_audit_" + _digest(identity)[:24]
        high_risk = counts["confirmed_secret"] + counts["likely_secret"]
        row = _sealed({
            "ok": True,
            "status": "privacy_security_audit_prepared",
            "audit_id": audit_id,
            **identity,
            "finding_count": len(normalized),
            "classification_counts": counts,
            "confirmed_or_likely_count": high_risk,
            "release_blocked_by_secret_findings": high_risk > 0,
            "operator_review_required": True,
            "findings_redacted": True,
            **_base(),
        }, "privacy_security_audit_digest")
        with _lock(runtime_root):
            path = _path("privacy_security_audits", audit_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "privacy_security_audit_digest") else _failure("privacy_security_audit_tampered", "existing_audit_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("privacy_security_audit_blocked", str(exc))


def load_privacy_security_audit(audit_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(audit_id or "").strip().lower()
    if not _AUDIT.fullmatch(token):
        return _failure("privacy_security_audit_not_found", "invalid_audit_id")
    row = _read_json(_path("privacy_security_audits", token, runtime_root))
    if not row:
        return _failure("privacy_security_audit_not_found", "audit_missing")
    return row if _valid(row, "privacy_security_audit_digest") else _failure("privacy_security_audit_tampered", "audit_digest_mismatch")


def review_privacy_security_audit(
    audit_id: str,
    *,
    expected_audit_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        aid = str(audit_id or "").strip().lower()
        if not _AUDIT.fullmatch(aid):
            raise ValueError("invalid_audit_id")
        expected = _hex(expected_audit_digest, "invalid_audit_digest")
        audit = load_privacy_security_audit(aid, runtime_root=runtime_root)
        if not audit.get("ok") or audit.get("privacy_security_audit_digest") != expected:
            raise ValueError("stale_or_mismatched_audit")
        choice = _token(disposition, "invalid_audit_review_disposition")
        if choice not in AUDIT_REVIEW_DISPOSITIONS:
            raise ValueError("unsupported_audit_review_disposition")
        required = f"review privacy security audit {choice} for audit {aid} digest {expected}"
        if str(exact_phrase or "").strip().lower().rstrip(".!?") != required:
            raise ValueError("exact_audit_review_phrase_required")
        identity = {"audit_id": aid, "audit_digest": expected, "project_id": audit.get("project_id"), "disposition": choice}
        review_id = "privacy_security_audit_review_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "privacy_security_audit_review_recorded",
            "review_id": review_id,
            **identity,
            "findings_interpretation_accepted": choice == "accept_findings",
            "remediation_still_requires_separate_proposal": True,
            **_base(),
        }, "privacy_security_audit_review_digest")
        with _lock(runtime_root):
            path = _path("privacy_security_audit_reviews", review_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "privacy_security_audit_review_digest") else _failure("privacy_security_audit_review_tampered", "existing_review_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("privacy_security_audit_review_blocked", str(exc))


def load_privacy_security_audit_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(review_id or "").strip().lower()
    if not _AUDIT_REVIEW.fullmatch(token):
        return _failure("privacy_security_audit_review_not_found", "invalid_review_id")
    row = _read_json(_path("privacy_security_audit_reviews", token, runtime_root))
    if not row:
        return _failure("privacy_security_audit_review_not_found", "review_missing")
    return row if _valid(row, "privacy_security_audit_review_digest") else _failure("privacy_security_audit_review_tampered", "review_digest_mismatch")


def prepare_secret_management_remediation_proposal(
    audit_review_id: str,
    *,
    expected_audit_review_digest: str,
    action_rows: Sequence[Mapping[str, Any]],
    verification_plan_digest: str,
    rollback_plan_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        rid = str(audit_review_id or "").strip().lower()
        if not _AUDIT_REVIEW.fullmatch(rid):
            raise ValueError("invalid_audit_review_id")
        expected = _hex(expected_audit_review_digest, "invalid_audit_review_digest")
        review = load_privacy_security_audit_review(rid, runtime_root=runtime_root)
        if not review.get("ok") or review.get("privacy_security_audit_review_digest") != expected:
            raise ValueError("stale_or_mismatched_audit_review")
        if review.get("disposition") != "accept_findings":
            raise ValueError("accepted_findings_review_required")
        audit = load_privacy_security_audit(str(review.get("audit_id")), runtime_root=runtime_root)
        known = {row["finding_id"]: row for row in audit.get("findings", [])}
        normalized: list[dict[str, Any]] = []
        for raw in action_rows or []:
            if set(raw) - {"finding_id", "action"}:
                raise ValueError("unsupported_remediation_action_field")
            finding_id = str(raw.get("finding_id") or "").strip().lower()
            action = _token(raw.get("action"), "invalid_remediation_action")
            if finding_id not in known or action not in REMEDIATION_ACTIONS:
                raise ValueError("unknown_finding_or_action")
            normalized.append({"finding_id": finding_id, "action": action, "finding_evidence_digest": known[finding_id]["evidence_digest"]})
        normalized.sort(key=lambda row: row["finding_id"])
        if not normalized:
            raise ValueError("remediation_actions_required")
        identity = {
            "audit_review_id": rid,
            "audit_review_digest": expected,
            "audit_id": review.get("audit_id"),
            "project_id": review.get("project_id"),
            "action_rows": normalized,
            "verification_plan_digest": _hex(verification_plan_digest, "invalid_verification_plan_digest"),
            "rollback_plan_digest": _hex(rollback_plan_digest, "invalid_rollback_plan_digest"),
        }
        proposal_id = "secret_remediation_proposal_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "secret_management_remediation_proposal_prepared",
            "proposal_id": proposal_id,
            **identity,
            "action_count": len(normalized),
            "operator_review_required": True,
            "proposal_only": True,
            **_base(),
        }, "secret_remediation_proposal_digest")
        with _lock(runtime_root):
            path = _path("secret_management_remediation_proposals", proposal_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "secret_remediation_proposal_digest") else _failure("secret_management_remediation_proposal_tampered", "existing_proposal_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("secret_management_remediation_proposal_blocked", str(exc))


def load_secret_management_remediation_proposal(proposal_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(proposal_id or "").strip().lower()
    if not _REMEDIATION.fullmatch(token):
        return _failure("secret_management_remediation_proposal_not_found", "invalid_proposal_id")
    row = _read_json(_path("secret_management_remediation_proposals", token, runtime_root))
    if not row:
        return _failure("secret_management_remediation_proposal_not_found", "proposal_missing")
    return row if _valid(row, "secret_remediation_proposal_digest") else _failure("secret_management_remediation_proposal_tampered", "proposal_digest_mismatch")


def review_secret_management_remediation(
    proposal_id: str,
    *,
    expected_proposal_digest: str,
    disposition: str,
    exact_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        pid = str(proposal_id or "").strip().lower()
        if not _REMEDIATION.fullmatch(pid):
            raise ValueError("invalid_remediation_proposal_id")
        expected = _hex(expected_proposal_digest, "invalid_remediation_proposal_digest")
        proposal = load_secret_management_remediation_proposal(pid, runtime_root=runtime_root)
        if not proposal.get("ok") or proposal.get("secret_remediation_proposal_digest") != expected:
            raise ValueError("stale_or_mismatched_remediation_proposal")
        choice = _token(disposition, "invalid_remediation_review_disposition")
        if choice not in REMEDIATION_REVIEW_DISPOSITIONS:
            raise ValueError("unsupported_remediation_review_disposition")
        required = f"review secret remediation {choice} for proposal {pid} digest {expected}"
        if str(exact_phrase or "").strip().lower().rstrip(".!?") != required:
            raise ValueError("exact_remediation_review_phrase_required")
        identity = {"proposal_id": pid, "proposal_digest": expected, "audit_id": proposal.get("audit_id"), "project_id": proposal.get("project_id"), "disposition": choice}
        review_id = "secret_remediation_review_" + _digest(identity)[:24]
        row = _sealed({
            "ok": True,
            "status": "secret_management_remediation_review_recorded",
            "review_id": review_id,
            **identity,
            "plan_interpretation_accepted": choice == "accept_plan",
            "remediation_executed": False,
            "fresh_separate_mutation_authority_required": True,
            **_base(),
        }, "secret_remediation_review_digest")
        with _lock(runtime_root):
            path = _path("secret_management_remediation_reviews", review_id, runtime_root)
            current = _read_json(path)
            if current:
                return current if _valid(current, "secret_remediation_review_digest") else _failure("secret_management_remediation_review_tampered", "existing_review_tampered")
            _atomic_json(path, row)
        return row
    except Exception as exc:
        return _failure("secret_management_remediation_review_blocked", str(exc))


def load_secret_management_remediation_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    token = str(review_id or "").strip().lower()
    if not _REMEDIATION_REVIEW.fullmatch(token):
        return _failure("secret_management_remediation_review_not_found", "invalid_review_id")
    row = _read_json(_path("secret_management_remediation_reviews", token, runtime_root))
    if not row:
        return _failure("secret_management_remediation_review_not_found", "review_missing")
    return row if _valid(row, "secret_remediation_review_digest") else _failure("secret_management_remediation_review_tampered", "review_digest_mismatch")


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    for path in sorted(root.glob("*.json")) if root.exists() else []:
        row = _read_json(path)
        if row and _valid(row, seal_field):
            rows.append({key: row.get(key) for key in keys})
    rows = rows[-MAX_RECORDS:]
    result = {"ok": True, "status": f"{plural}_ready", plural: rows, "count": len(rows), "read_only": True, **_base()}
    result[f"{plural}_digest"] = _digest(rows)
    return result


def public_privacy_security_audits(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("privacy_security_audits", "privacy_security_audit_digest", ("audit_id", "project_id", "audit_scope_code", "generation", "finding_count", "confirmed_or_likely_count", "release_blocked_by_secret_findings", "privacy_security_audit_digest"), "privacy_security_audits", runtime_root)


def public_privacy_security_audit_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("privacy_security_audit_reviews", "privacy_security_audit_review_digest", ("review_id", "audit_id", "project_id", "disposition", "findings_interpretation_accepted", "privacy_security_audit_review_digest"), "privacy_security_audit_reviews", runtime_root)


def public_secret_management_remediation_proposals(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("secret_management_remediation_proposals", "secret_remediation_proposal_digest", ("proposal_id", "audit_id", "project_id", "action_count", "proposal_only", "secret_remediation_proposal_digest"), "secret_management_remediation_proposals", runtime_root)


def public_secret_management_remediation_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("secret_management_remediation_reviews", "secret_remediation_review_digest", ("review_id", "proposal_id", "audit_id", "project_id", "disposition", "plan_interpretation_accepted", "secret_remediation_review_digest"), "secret_management_remediation_reviews", runtime_root)


def privacy_security_audit_dashboard_record(*, runtime_root=None) -> dict[str, Any]:
    audits = public_privacy_security_audits(runtime_root=runtime_root)
    audit_reviews = public_privacy_security_audit_reviews(runtime_root=runtime_root)
    proposals = public_secret_management_remediation_proposals(runtime_root=runtime_root)
    remediation_reviews = public_secret_management_remediation_reviews(runtime_root=runtime_root)
    row = {
        "ok": True,
        "status": "privacy_security_audit_dashboard_ready",
        "read_only": True,
        "get_only": True,
        "audit_count": audits["count"],
        "audit_review_count": audit_reviews["count"],
        "remediation_proposal_count": proposals["count"],
        "remediation_review_count": remediation_reviews["count"],
        "privacy_security_audits": audits["privacy_security_audits"],
        "privacy_security_audit_reviews": audit_reviews["privacy_security_audit_reviews"],
        "secret_management_remediation_proposals": proposals["secret_management_remediation_proposals"],
        "secret_management_remediation_reviews": remediation_reviews["secret_management_remediation_reviews"],
        **_base(),
    }
    row["dashboard_digest"] = _digest(row)
    return row


def render_privacy_security_audit_dashboard_html(*, runtime_root=None) -> str:
    row = privacy_security_audit_dashboard_record(runtime_root=runtime_root)
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Privacy, Security, and Secret-Management Audit</title>"
        "<style>body{font-family:system-ui;background:#111827;color:#e5e7eb;margin:0;padding:28px}.card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:18px;max-width:980px;margin:auto}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{background:#111827;padding:14px;border-radius:8px}.muted{color:#9ca3af}</style></head><body><div class='card'>"
        "<h1>Privacy, Security, and Secret-Management Audit</h1><p class='muted'>GET-only redacted inspection. Secret values and matched text are never displayed. Review never rotates, deletes, quarantines, contacts providers, mutates packages, or grants authority.</p>"
        f"<div class='grid'><div class='metric'>Audits<br><b>{html.escape(str(row['audit_count']))}</b></div>"
        f"<div class='metric'>Audit reviews<br><b>{html.escape(str(row['audit_review_count']))}</b></div>"
        f"<div class='metric'>Remediation proposals<br><b>{html.escape(str(row['remediation_proposal_count']))}</b></div>"
        f"<div class='metric'>Remediation reviews<br><b>{html.escape(str(row['remediation_review_count']))}</b></div></div>"
        "<p>Findings distinguish confirmed and likely secrets, sensitive metadata, synthetic canaries, allowed public identifiers, false positives, unverified findings, and remediated findings.</p>"
        "</div></body></html>"
    )


def privacy_security_audit_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "")
    if not row.get("ok"):
        return f"Privacy and security control was blocked: {row.get('reason') or status}. No secret value was revealed and no remediation authority was created."
    if status.endswith("registry_ready"):
        return "The Privacy, Security, and Secret-Management Audit registry is ready for redacted read-only inspection."
    if status.endswith("audit_review_recorded"):
        return f"Recorded audit review {row.get('review_id')} as {row.get('disposition')}. No secret was revealed or remediated."
    if status.endswith("remediation_review_recorded"):
        return f"Recorded remediation review {row.get('review_id')} as {row.get('disposition')}. No credential was rotated and no file or package was modified."
    return "Redacted privacy and security evidence is ready for read-only inspection."


def process_privacy_security_audit_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    row: dict[str, Any] | None = None
    if _SHOW_REGISTRY.fullmatch(text):
        row = privacy_security_secret_management_registry()
    elif _SHOW_AUDITS.fullmatch(text):
        row = public_privacy_security_audits(runtime_root=runtime_root)
    elif _SHOW_AUDIT_REVIEWS.fullmatch(text):
        row = public_privacy_security_audit_reviews(runtime_root=runtime_root)
    elif _SHOW_REMEDIATIONS.fullmatch(text):
        row = public_secret_management_remediation_proposals(runtime_root=runtime_root)
    elif _SHOW_REMEDIATION_REVIEWS.fullmatch(text):
        row = public_secret_management_remediation_reviews(runtime_root=runtime_root)
    else:
        match = _REVIEW_AUDIT.fullmatch(text)
        if match:
            row = review_privacy_security_audit(match.group("audit"), expected_audit_digest=match.group("digest"), disposition=match.group("disposition").lower(), exact_phrase=text, runtime_root=runtime_root)
        else:
            match = _REVIEW_REMEDIATION.fullmatch(text)
            if match:
                row = review_secret_management_remediation(match.group("proposal"), expected_proposal_digest=match.group("digest"), disposition=match.group("disposition").lower(), exact_phrase=text, runtime_root=runtime_root)
    if row is None:
        return {"active": False}
    return {
        "active": True,
        "privacy_security_audit": row,
        "response": privacy_security_audit_response(row),
        "action_taken": False,
        "secret_value_revealed": False,
        "credential_rotated": False,
        "file_deleted": False,
        "package_modified": False,
        "execution_started": False,
    }


def build_privacy_security_secret_management_contract() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "privacy_security_secret_management_contract_ready",
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "threat_model_and_data_classification": True,
        "trust_boundaries_and_transmission_paths": True,
        "retention_rules_and_immutable_lineage": True,
        "redacted_secret_findings": True,
        "eight_finding_classifications": True,
        "source_and_archive_scanning": True,
        "secret_reference_and_rotation_proposals": True,
        "provider_credential_and_local_remote_routing_review": True,
        "ordinary_chat_review": True,
        "cli_and_get_only_inspection": True,
        "path_traversal_archive_log_backup_and_crash_hardening": True,
        "prompt_and_provider_output_injection_hardening": True,
        "cross_project_session_replay_and_tamper_hardening": True,
        "no_secret_value_disclosure": True,
        "no_automatic_remediation": True,
        "no_execution_authority": True,
        "runtime_records_external": True,
        **_base(),
    }
    row["contract_digest"] = _digest(row)
    return row
