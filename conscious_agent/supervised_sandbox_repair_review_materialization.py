from __future__ import annotations

"""v1183.3-v1183.5 operator repair review and isolated sandbox materialization.

Records an explicit operator decision over one exact v1183.2 private repair draft.
Only an approved exact draft may replace its single target inside a caller-selected
isolated sandbox. The original bytes are retained as private rollback material and
content-free rollback evidence is emitted. This module never touches production
source, runs tests, invokes providers/models/tools/shells, or grants retest,
source-application, promotion, installation, certification, or release authority.
"""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1183.5"
MAX_SOURCE_BYTES = 262_144
_DECISIONS = frozenset({"approve", "reject", "defer"})
_ALLOWED_SUFFIXES = frozenset({".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".toml", ".yaml", ".yml"})
_BLOCKED_PARTS = frozenset({"data", "runtime", "private", "secrets", "credentials", "tokens", "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules", "conversations", "memories", "providers"})
_PRIVATE_FIELDS = frozenset({"replacement_text", "rollback_text", "patch_text"})


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_newline_bytes(value: bytes) -> bytes | None:
    """Return UTF-8 bytes with CRLF/CR normalized to LF for reviewed-text comparison."""
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return _digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def _text(value: Any, limit: int = 260) -> str:
    return " ".join(str(value or "").split())[:limit]


def _hex64(value: Any) -> str:
    token = _text(value, 64).lower()
    return token if len(token) == 64 and all(c in "0123456789abcdef" for c in token) else ""


def _safe_target(value: Any) -> str:
    raw = _text(value, 260).replace("\\", "/")
    if not raw or raw.startswith(("/", "//")) or (len(raw) > 1 and raw[1] == ":"):
        return ""
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} or part.lower() in _BLOCKED_PARTS for part in path.parts):
        return ""
    return path.as_posix() if path.suffix.lower() in _ALLOWED_SUFFIXES else ""


def _receipt_valid(value: Mapping[str, Any], field: str, *, omitted: frozenset[str] = frozenset()) -> bool:
    supplied = _hex64(value.get(field))
    if not supplied:
        return False
    basis = {k: v for k, v in value.items() if k != field and k not in omitted}
    try:
        return _digest(basis) == supplied
    except (TypeError, ValueError, OverflowError):
        return False


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "tests_rerun": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "automatic_approval_created": False,
        "automatic_authorization_created": False,
        "retest_authorized": False,
        "source_application_authorized": False,
        "promotion_authorized": False,
        "installation_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "public_diagnostics_content_free": True,
    }


def _blocked(reason: str, *, phase: str, **details: Any) -> dict[str, Any]:
    status_field = "review_status" if phase == "review" else "materialization_status"
    result = {**_base(), status_field: "blocked", "block_reason": reason, **details}
    result[f"{phase}_receipt_digest"] = _digest(result)
    return result


def _valid_draft(draft: Mapping[str, Any]) -> bool:
    target = _safe_target(draft.get("target_path"))
    return bool(
        draft.get("contract_version") == "v1183.2"
        and draft.get("draft_status") == "private_draft_ready"
        and draft.get("private_artifact") is True
        and draft.get("contains_private_source_content") is True
        and draft.get("repair_materialized") is False
        and draft.get("tests_rerun") is False
        and draft.get("repair_materialization_authorized") is False
        and draft.get("retest_authorized") is False
        and target
        and all(_hex64(draft.get(k)) for k in (
            "draft_digest", "draft_receipt_digest", "plan_digest", "diagnosis_digest",
            "evidence_digest", "materialization_receipt_digest", "baseline_target_digest",
            "replacement_digest", "rollback_digest", "patch_digest",
        ))
        and draft.get("baseline_target_digest") == draft.get("rollback_digest")
        and isinstance(draft.get("replacement_text"), str)
        and isinstance(draft.get("rollback_text"), str)
        and isinstance(draft.get("patch_text"), str)
        and _receipt_valid(draft, "draft_receipt_digest", omitted=_PRIVATE_FIELDS)
    )


def review_repair_draft(draft: Mapping[str, Any], *, decision: str, operator_actor: str) -> dict[str, Any]:
    """Record one explicit content-free operator decision over an exact private draft."""
    if not _valid_draft(draft):
        return _blocked("invalid_or_tampered_repair_draft", phase="review")
    chosen = _text(decision, 20).lower()
    actor = _text(operator_actor, 100)
    if chosen not in _DECISIONS:
        return _blocked("invalid_review_decision", phase="review")
    if not actor:
        return _blocked("missing_operator_actor", phase="review")
    structural = {
        "draft_id": _text(draft.get("draft_id"), 100),
        "draft_digest": _hex64(draft.get("draft_digest")),
        "draft_receipt_digest": _hex64(draft.get("draft_receipt_digest")),
        "plan_digest": _hex64(draft.get("plan_digest")),
        "target_path": _safe_target(draft.get("target_path")),
        "baseline_target_digest": _hex64(draft.get("baseline_target_digest")),
        "replacement_digest": _hex64(draft.get("replacement_digest")),
        "rollback_digest": _hex64(draft.get("rollback_digest")),
        "patch_digest": _hex64(draft.get("patch_digest")),
        "failure_code": _text(draft.get("failure_code"), 80),
        "decision": chosen,
        "operator_actor_digest": _digest(actor),
        "operator_review_complete": chosen in {"approve", "reject"},
        "sandbox_repair_materialization_authorized": chosen == "approve",
        "rollback_evidence_required": chosen == "approve",
        "retest_authorized": False,
        "source_application_authorized": False,
    }
    review_digest = _digest(structural)
    result = {
        **_base(), **structural,
        "review_status": {"approve": "approved_for_sandbox_repair", "reject": "rejected", "defer": "deferred"}[chosen],
        "review_id": f"sandbox-repair-review-{review_digest[:20]}",
        "review_digest": review_digest,
        "content_free": True,
    }
    result["review_receipt_digest"] = _digest(result)
    return result


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _has_symlink_component(root: Path, target: Path) -> bool:
    current = root
    if current.exists() and current.is_symlink():
        return True
    for part in target.relative_to(root).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False


def materialize_reviewed_sandbox_repair(
    draft: Mapping[str, Any], review: Mapping[str, Any], *, sandbox_root: str | Path,
    source_root: str | Path, current_target_text: str, replacement_text: str,
) -> dict[str, Any]:
    """Apply one exact approved replacement only inside an isolated sandbox."""
    if not _valid_draft(draft):
        return _blocked("invalid_or_tampered_repair_draft", phase="materialization")
    target = _safe_target(draft.get("target_path"))
    valid_review = (
        review.get("contract_version") == CONTRACT_VERSION
        and review.get("review_status") == "approved_for_sandbox_repair"
        and review.get("sandbox_repair_materialization_authorized") is True
        and review.get("rollback_evidence_required") is True
        and review.get("retest_authorized") is False
        and review.get("source_application_authorized") is False
        and _hex64(review.get("draft_digest")) == _hex64(draft.get("draft_digest"))
        and _hex64(review.get("draft_receipt_digest")) == _hex64(draft.get("draft_receipt_digest"))
        and _safe_target(review.get("target_path")) == target
        and _hex64(review.get("baseline_target_digest")) == _hex64(draft.get("baseline_target_digest"))
        and _hex64(review.get("replacement_digest")) == _hex64(draft.get("replacement_digest"))
        and _receipt_valid(review, "review_receipt_digest")
    )
    if not valid_review:
        return _blocked("invalid_or_tampered_repair_review_binding", phase="materialization")
    if not isinstance(current_target_text, str) or not isinstance(replacement_text, str) or "\x00" in current_target_text or "\x00" in replacement_text:
        return _blocked("invalid_private_source_content", phase="materialization", target_path=target)
    before, after = current_target_text.encode(), replacement_text.encode()
    if len(before) > MAX_SOURCE_BYTES or len(after) > MAX_SOURCE_BYTES:
        return _blocked("oversized_private_source_content", phase="materialization", target_path=target)
    if (
        _digest_bytes(before) != _hex64(draft.get("baseline_target_digest"))
        or _digest_bytes(before) != _hex64(draft.get("rollback_digest"))
        or _digest_bytes(after) != _hex64(draft.get("replacement_digest"))
        or current_target_text != draft.get("rollback_text")
        or replacement_text != draft.get("replacement_text")
    ):
        return _blocked("private_content_digest_or_binding_mismatch", phase="materialization", target_path=target)

    sandbox = Path(sandbox_root).expanduser().resolve()
    source = Path(source_root).expanduser().resolve()
    if sandbox == source or _inside(sandbox, source) or _inside(source, sandbox):
        return _blocked("sandbox_not_isolated", phase="materialization", target_path=target)
    destination = sandbox.joinpath(*PurePosixPath(target).parts)
    rollback_dir = sandbox / ".eidolon_repair_rollback"
    marker_path = sandbox / ".eidolon_sandbox_repair_materialization.json"
    rollback_path = rollback_dir / f"{_hex64(draft.get('draft_digest'))}.rollback"
    if any(_has_symlink_component(sandbox, p) for p in (destination, rollback_path, marker_path)):
        return _blocked("sandbox_symlink_boundary", phase="materialization", target_path=target)

    sandbox.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rollback_dir.mkdir(parents=True, exist_ok=True)
    if any(_has_symlink_component(sandbox, p) for p in (destination, rollback_path, marker_path)):
        return _blocked("sandbox_symlink_boundary", phase="materialization", target_path=target)
    if not destination.exists():
        return _blocked("sandbox_target_missing", phase="materialization", target_path=target)
    observed = destination.read_bytes()
    observed_digest = _digest_bytes(observed)
    observed_canonical = _canonical_newline_bytes(observed)
    observed_canonical_digest = _digest_bytes(observed_canonical) if observed_canonical is not None else ""
    before_digest = _digest_bytes(before)
    after_digest = _digest_bytes(after)
    newline_normalization_applied = bool(observed_digest != before_digest and observed_canonical_digest == before_digest)
    rollback_bytes = observed
    rollback_artifact_digest = _digest_bytes(rollback_bytes)
    existing_rollback = rollback_path.read_bytes() if rollback_path.exists() else b""
    existing_rollback_canonical = _canonical_newline_bytes(existing_rollback) if existing_rollback else None
    existing_rollback_matches = bool(
        existing_rollback
        and (
            _digest_bytes(existing_rollback) == before_digest
            or (existing_rollback_canonical is not None and _digest_bytes(existing_rollback_canonical) == before_digest)
        )
    )
    if existing_rollback_matches and _digest_bytes(existing_rollback) != before_digest:
        newline_normalization_applied = True
    if observed_digest == after_digest and existing_rollback_matches:
        status = "already_materialized"
        rollback_bytes = existing_rollback
        rollback_artifact_digest = _digest_bytes(existing_rollback)
    elif observed_digest != before_digest and observed_canonical_digest != before_digest:
        return _blocked("stale_sandbox_target_or_drift", phase="materialization", target_path=target, expected_target_digest=before_digest, observed_target_digest=observed_digest)
    else:
        status = "materialized"
        rollback_temp = rollback_path.with_suffix(".tmp")
        rollback_temp.write_bytes(rollback_bytes)
        os.replace(rollback_temp, rollback_path)
        target_temp = destination.with_name(destination.name + ".eidolon-repair-tmp")
        target_temp.write_bytes(after)
        os.replace(target_temp, destination)

    rollback_evidence = {
        "target_path": target,
        "draft_digest": _hex64(draft.get("draft_digest")),
        "review_digest": _hex64(review.get("review_digest")),
        "rollback_digest": before_digest,
        "rollback_artifact_digest": rollback_artifact_digest,
        "replacement_digest": after_digest,
        "newline_normalization_applied": newline_normalization_applied,
        "rollback_artifact_present": rollback_path.exists(),
        "rollback_artifact_digest_verified": rollback_path.exists() and _digest_bytes(rollback_path.read_bytes()) == rollback_artifact_digest,
        "rollback_not_executed": True,
    }
    rollback_evidence_digest = _digest(rollback_evidence)
    marker = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "sandbox_only": True,
        "target_path": target, "draft_digest": _hex64(draft.get("draft_digest")),
        "review_digest": _hex64(review.get("review_digest")), "baseline_target_digest": before_digest,
        "physical_baseline_target_digest": rollback_artifact_digest,
        "newline_normalization_applied": newline_normalization_applied,
        "replacement_digest": after_digest, "rollback_evidence_digest": rollback_evidence_digest,
        "tests_rerun": False, "retest_authorized": False,
    }
    marker_digest = _digest(marker)
    marker_path.write_text(json.dumps({**marker, "marker_digest": marker_digest}, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    result = {
        **_base(),
        "materialization_status": status,
        "target_path": target,
        "draft_digest": _hex64(draft.get("draft_digest")),
        "draft_receipt_digest": _hex64(draft.get("draft_receipt_digest")),
        "review_digest": _hex64(review.get("review_digest")),
        "review_receipt_digest": _hex64(review.get("review_receipt_digest")),
        "baseline_target_digest": before_digest,
        "physical_baseline_target_digest": rollback_artifact_digest,
        "newline_normalization_applied": newline_normalization_applied,
        "sandbox_target_digest": _digest_bytes(destination.read_bytes()),
        "replacement_digest": after_digest,
        "rollback_digest": before_digest,
        "rollback_artifact_digest": rollback_artifact_digest,
        "rollback_evidence_digest": rollback_evidence_digest,
        "sandbox_marker_digest": marker_digest,
        "sandbox_repair_materialized": True,
        "sandbox_file_written": status == "materialized",
        "rollback_artifact_written": status == "materialized",
        "rollback_artifact_present": rollback_evidence["rollback_artifact_present"],
        "rollback_artifact_digest_verified": rollback_evidence["rollback_artifact_digest_verified"],
        "rollback_executed": False,
        "content_free": True,
        "operator_review_required_for_retest": True,
    }
    result["materialization_receipt_digest"] = _digest(result)
    return result


def sandbox_repair_materialization_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version", "contract_version", "materialization_status", "block_reason", "target_path",
        "draft_digest", "draft_receipt_digest", "review_digest", "review_receipt_digest",
        "baseline_target_digest", "physical_baseline_target_digest", "newline_normalization_applied",
        "sandbox_target_digest", "replacement_digest", "rollback_digest", "rollback_artifact_digest",
        "rollback_evidence_digest", "sandbox_marker_digest", "sandbox_repair_materialized",
        "sandbox_file_written", "rollback_artifact_written", "rollback_artifact_present",
        "rollback_artifact_digest_verified", "rollback_executed", "materialization_receipt_digest",
        "expected_target_digest", "observed_target_digest",
    }
    summary = {k: result[k] for k in allowed if k in result}
    summary.update({
        "content_free": True, "private_source_content_included": False, "patch_text_included": False,
        "rollback_text_included": False, "replacement_text_included": False,
        "production_source_modified": False, "source_modified": False, "tests_rerun": False,
        "retest_authorized": False, "source_application_authorized": False, "authority_granted": False,
        "operator_review_required_for_retest": True,
    })
    summary["summary_digest"] = _digest(summary)
    return summary
