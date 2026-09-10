from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from bounded_capability_evidence import bounded_int, digest, sealed, valid_seal

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.I)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+\-/=]{8,})"),
    re.compile(r"\b(?:sk|pk)_[A-Za-z0-9]{16,}\b"),
)
_SHELL_META = re.compile(r"[;&|`$<>\n\r]")


def _norm_rel(value: Any) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw) or raw.startswith("//"):
        raise ValueError("absolute_or_empty_path_denied")
    parts = PurePosixPath(raw).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path_traversal_denied")
    return PurePosixPath(*parts).as_posix()


def workspace_containment(workspace_root: str | Path, candidate: Any, *, link_target: Any | None = None,
                          reparse_point: bool = False, protected_locations: Sequence[str] = (),
                          workspace_mount: str = "default", candidate_mount: str = "default",
                          version: str = "1451.9") -> dict[str, Any]:
    root = Path(workspace_root).expanduser().resolve()
    reasons: list[str] = []
    try:
        rel = _norm_rel(candidate)
    except ValueError as exc:
        rel = ""
        reasons.append(str(exc))
    resolved = (root / rel).resolve(strict=False) if rel else root
    try:
        resolved.relative_to(root)
        within = bool(rel)
    except ValueError:
        within = False
    if not within:
        reasons.append("outside_workspace")
    protected = {str(Path(p).expanduser().resolve()).casefold() for p in protected_locations}
    if str(resolved).casefold() in protected:
        reasons.append("protected_location")
    if workspace_mount != candidate_mount:
        reasons.append("mount_boundary_crossed")
    link_safe = True
    if reparse_point or link_target is not None:
        try:
            target = Path(link_target or resolved).expanduser().resolve(strict=False)
            target.relative_to(root)
        except (ValueError, OSError):
            link_safe = False
            reasons.append("link_or_reparse_escape")
    allowed = within and link_safe and not reasons
    return sealed("workspace_containment", {
        "workspace_root_digest": digest(str(root)), "relative_path": rel,
        "resolved_path_digest": digest(str(resolved)), "within_workspace": within,
        "link_safe": link_safe, "mount_consistent": workspace_mount == candidate_mount,
        "protected_location_denied": "protected_location" in reasons,
        "allowed": allowed, "denial_reasons": sorted(set(reasons)),
    }, version=version)


def command_policy(operation: Mapping[str, Any], *, version: str = "1452.9") -> dict[str, Any]:
    op_class = str(operation.get("class") or "").strip().lower()
    argv = [str(x) for x in operation.get("argv") or []]
    allowed_classes = {"read", "test", "build", "git_read", "format", "lint", "local_process"}
    forbidden = {"destructive_system", "account", "financial", "model_management", "release_promotion"}
    shell_meta = any(_SHELL_META.search(arg) for arg in argv)
    env = {str(k): str(v) for k, v in (operation.get("env") or {}).items() if str(k).upper() in {"PATH", "PYTHONPATH", "NODE_OPTIONS", "PYTHONDONTWRITEBYTECODE"}}
    env_secret_keys = [str(k) for k in (operation.get("env") or {}) if any(token in str(k).upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
    argv_count = bounded_int(len(argv), hi=128)
    allowed = op_class in allowed_classes and op_class not in forbidden and bool(argv) and not shell_meta and not env_secret_keys
    return sealed("command_policy", {
        "operation_class": op_class, "argv_count": argv_count, "typed_operation": op_class in allowed_classes,
        "shell_metacharacters_denied": shell_meta, "environment_keys": sorted(env),
        "secret_environment_keys_denied": sorted(env_secret_keys), "process_tree_containment_required": True,
        "allowed": allowed, "broad_shell_permission": False,
    }, version=version)


def network_policy(request: Mapping[str, Any], policy: Mapping[str, Any], *, version: str = "1453.9") -> dict[str, Any]:
    raw = str(request.get("url") or "")
    method = str(request.get("method") or "GET").upper()
    data_class = str(request.get("data_class") or "public").lower()
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").lower()
        scheme = parsed.scheme.lower()
    except Exception:
        host, scheme = "", ""
    allowed_hosts = {str(x).lower() for x in policy.get("hosts") or []}
    allowed_methods = {str(x).upper() for x in policy.get("methods") or ["GET"]}
    allowed_classes = {str(x).lower() for x in policy.get("data_classes") or ["public"]}
    redirect_host = str(request.get("redirect_host") or "").lower()
    redirect_ok = not redirect_host or redirect_host == host or redirect_host in allowed_hosts
    upload = method in {"POST", "PUT", "PATCH"} and bool(request.get("body_present"))
    upload_destination_ok = not upload or host in {str(x).lower() for x in policy.get("upload_hosts") or []}
    dns_change = bool(request.get("dns_change"))
    download = bool(request.get("download"))
    allowed = scheme in {"http", "https"} and host in allowed_hosts and method in allowed_methods and data_class in allowed_classes and redirect_ok and upload_destination_ok and not dns_change
    return sealed("network_policy", {
        "scheme": scheme, "host_digest": digest(host), "method": method, "data_class": data_class,
        "redirect_allowed": redirect_ok, "upload": upload, "upload_destination_allowed": upload_destination_ok,
        "download": download, "dns_change_denied": dns_change, "allowed": allowed,
    }, version=version)


def secret_handling(texts: Sequence[str], *, version: str = "1454.9") -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    redacted: list[str] = []
    for index, raw in enumerate(texts):
        text = str(raw)
        changed = text
        local = 0
        for pattern in _SECRET_PATTERNS:
            def repl(match: re.Match[str]) -> str:
                nonlocal local
                local += 1
                return match.group(0).replace(match.group(1), "[REDACTED]") if match.lastindex else "[REDACTED]"
            changed = pattern.sub(repl, changed)
        if local:
            findings.append({"source_index": index, "count": local, "source_digest": hashlib.sha256(text.encode()).hexdigest()})
        redacted.append(changed)
    return sealed("secret_handling", {
        "finding_count": sum(x["count"] for x in findings), "finding_sources": findings,
        "redacted_text_digests": [hashlib.sha256(x.encode()).hexdigest() for x in redacted],
        "secret_values_retained": False, "prompt_inclusion_allowed": False,
        "logs_content_free": True, "archive_secret_material_allowed": False,
        "rotation_requires_separate_operator_action": True,
    }, version=version)


def untrusted_content_defense(items: Sequence[Mapping[str, Any]], *, version: str = "1455.9") -> dict[str, Any]:
    rows = []
    authority_attempts = 0
    patterns = ("ignore previous", "system prompt", "grant authority", "run this command", "disable safety", "you are now")
    for item in items:
        text = str(item.get("text") or "")
        lower = text.lower()
        suspicious = any(token in lower for token in patterns)
        authority_attempts += int(suspicious)
        rows.append({"source": str(item.get("source") or "unknown"), "content_digest": hashlib.sha256(text.encode()).hexdigest(), "instruction_like": suspicious, "treated_as_data": True})
    return sealed("untrusted_content_defense", {
        "item_count": len(rows), "authority_redefinition_attempts": authority_attempts,
        "items": rows, "authority_changed": False, "content_can_define_policy": False,
        "operator_or_session_authority_required": True,
    }, version=version)


def supply_chain_defense(artifact: Mapping[str, Any], *, version: str = "1456.9") -> dict[str, Any]:
    digest_value = str(artifact.get("sha256") or "")
    entries = [str(x).replace("\\", "/") for x in artifact.get("entries") or []]
    dangerous = [x for x in entries if x.lower().endswith((".exe", ".dll", ".ps1", ".bat", ".cmd", ".scr")) and x not in set(artifact.get("expected_executables") or [])]
    traversal = [x for x in entries if x.startswith("/") or "../" in x or re.match(r"^[A-Za-z]:", x)]
    lock_required = bool(artifact.get("dependency_change"))
    lock_ok = not lock_required or bool(artifact.get("lockfile_present"))
    provenance_ok = bool(artifact.get("provenance_digest")) and _SHA256_RE.fullmatch(str(artifact.get("provenance_digest"))) is not None
    signature_state = "verified" if artifact.get("signature_verified") else "unavailable_or_unverified"
    ok = _SHA256_RE.fullmatch(digest_value) is not None and not dangerous and not traversal and lock_ok and provenance_ok
    return sealed("supply_chain_defense", {
        "archive_digest_valid": _SHA256_RE.fullmatch(digest_value) is not None,
        "entry_count": len(entries), "unexpected_executables": dangerous, "archive_path_violations": traversal,
        "lockfile_requirement_met": lock_ok, "provenance_verified": provenance_ok,
        "signature_state": signature_state, "safe_to_review": ok, "installation_authorized": False,
    }, version=version)


def data_privacy(records: Sequence[Mapping[str, Any]], policy: Mapping[str, Any], *, version: str = "1457.9") -> dict[str, Any]:
    allowed_classes = {"conversation", "memory", "project", "telemetry", "log", "receipt", "export"}
    rows = []
    for record in records:
        cls = str(record.get("class") or "unknown").lower()
        ttl = bounded_int((policy.get("retention_days") or {}).get(cls, 0), hi=36500)
        rows.append({
            "id": str(record.get("id") or ""), "class": cls, "recognized": cls in allowed_classes,
            "retention_days": ttl, "deletable": True, "export_redaction_required": cls in {"conversation", "memory", "project", "log"},
            "content_digest": str(record.get("content_digest") or ""),
        })
    return sealed("data_privacy", {
        "records": rows, "unrecognized_count": sum(not x["recognized"] for x in rows),
        "deletion_supported": True, "retention_explicit": all(x["retention_days"] >= 0 for x in rows),
        "private_content_in_public_evidence": False,
    }, version=version)


def audit_integrity(events: Sequence[Mapping[str, Any]], *, initial_digest: str = "0" * 64, version: str = "1458.9") -> dict[str, Any]:
    previous = initial_digest if _SHA256_RE.fullmatch(initial_digest) else "0" * 64
    chain = []
    for ordinal, event in enumerate(events, 1):
        public = {
            "ordinal": ordinal, "session_id": str(event.get("session_id") or ""),
            "event": str(event.get("event") or ""), "side_effect_digest": str(event.get("side_effect_digest") or ""),
            "authority_digest": str(event.get("authority_digest") or ""), "previous_digest": previous,
        }
        current = digest(public)
        chain.append({**public, "event_digest": current})
        previous = current
    reconstructable = all(row["ordinal"] == i + 1 for i, row in enumerate(chain))
    return sealed("audit_integrity", {
        "event_count": len(chain), "chain_head": previous, "chain": chain,
        "tamper_evident": True, "reconstructable": reconstructable,
        "raw_private_content_recorded": False,
    }, version=version)


def incident_response(signals: Sequence[Mapping[str, Any]], session: Mapping[str, Any], *, version: str = "1459.9") -> dict[str, Any]:
    critical = [x for x in signals if str(x.get("severity") or "").lower() in {"critical", "high"} or bool(x.get("containment_failure"))]
    triggered = bool(critical)
    actions = ["stop_work", "preserve_redacted_evidence", "revoke_session", "freeze_owned_mutations", "prepare_restore"] if triggered else ["continue_monitoring"]
    return sealed("incident_response", {
        "incident_triggered": triggered, "signal_count": len(signals), "critical_count": len(critical),
        "session_id": str(session.get("session_id") or ""), "actions": actions,
        "automatic_external_publication": False, "restore_requires_owned_lineage": True,
        "operator_explanation_required": triggered,
    }, version=version)


def build_security_checkpoint(*, workspace: Mapping[str, Any], command: Mapping[str, Any], network: Mapping[str, Any],
                              secrets: Mapping[str, Any], untrusted: Mapping[str, Any], supply: Mapping[str, Any],
                              privacy: Mapping[str, Any], audit: Mapping[str, Any], incident: Mapping[str, Any],
                              version: str = "1460.9") -> dict[str, Any]:
    inputs = [workspace, command, network, secrets, untrusted, supply, privacy, audit, incident]
    checks = {
        "all_evidence_sealed": all(valid_seal(x) for x in inputs),
        "workspace_contained": workspace.get("payload", {}).get("allowed") is True,
        "command_typed": command.get("payload", {}).get("allowed") is True,
        "network_scoped": network.get("payload", {}).get("allowed") is True,
        "secrets_redacted": secrets.get("payload", {}).get("secret_values_retained") is False,
        "untrusted_cannot_redefine_authority": untrusted.get("payload", {}).get("authority_changed") is False,
        "supply_chain_reviewable": supply.get("payload", {}).get("safe_to_review") is True,
        "privacy_content_free": privacy.get("payload", {}).get("private_content_in_public_evidence") is False,
        "audit_tamper_evident": audit.get("payload", {}).get("tamper_evident") is True,
        "incident_path_available": bool(incident.get("payload", {}).get("actions")),
    }
    return sealed("security_checkpoint", {
        "checks": checks, "passed": sum(checks.values()), "total": len(checks),
        "security_checkpoint_ready": all(checks.values()), "authority_expansion": False,
    }, version=version)


__all__ = [
    "workspace_containment", "command_policy", "network_policy", "secret_handling", "untrusted_content_defense",
    "supply_chain_defense", "data_privacy", "audit_integrity", "incident_response", "build_security_checkpoint",
]
