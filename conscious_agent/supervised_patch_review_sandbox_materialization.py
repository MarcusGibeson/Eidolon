from __future__ import annotations

"""v1181.6-v1181.8 supervised patch review and sandbox materialization.

Consumes one exact v1181.5 private patch draft. An explicit operator decision may
approve that draft for materialization into one caller-selected isolated sandbox
root. Materialization writes only the reviewed replacement text to the draft's
single target beneath that sandbox. It never reads or modifies the production
source tree, applies to source, runs tests, invokes a shell/tool/provider/model,
or grants release or promotion authority.
"""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1181.8"
MAX_SOURCE_BYTES = 262_144
_ALLOWED_SUFFIXES = frozenset({".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".toml", ".yaml", ".yml"})
_BLOCKED_PARTS = frozenset({"data", "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules", "conversations", "memories"})
_DECISIONS = frozenset({"approve", "reject", "defer"})


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def _text(value: Any, limit: int = 260) -> str:
    return " ".join(str(value or "").split())[:limit]


def _safe_target(value: Any) -> str:
    raw = _text(value, 260).replace("\\", "/")
    if not raw or raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        return ""
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} or part.lower() in _BLOCKED_PARTS for part in path.parts):
        return ""
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        return ""
    return path.as_posix()


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "source_read": False,
        "source_modified": False,
        "patch_applied_to_source": False,
        "tests_executed": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "source_application_authorized": False,
        "test_execution_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "sandbox_only": True,
        "operator_review_required": True,
    }


def review_patch_draft(
    draft: Mapping[str, Any],
    *,
    decision: str,
    operator_actor: str,
) -> dict[str, Any]:
    """Record one bounded operator review decision over an exact private draft."""
    base = _base()
    chosen = _text(decision, 20).lower()
    actor = _text(operator_actor, 80)
    target = _safe_target(draft.get("target_path"))
    draft_digest = _text(draft.get("draft_digest"), 64)
    patch_digest = _text(draft.get("patch_digest"), 64)
    preparation_digest = _text(draft.get("preparation_digest"), 64)
    valid = (
        draft.get("contract_version") == "v1181.5"
        and draft.get("draft_status") == "draft_ready"
        and draft.get("private_artifact") is True
        and draft.get("contains_source_content") is True
        and draft.get("patch_applied") is False
        and draft.get("application_authorized") is False
        and draft.get("test_execution_authorized") is False
        and bool(target)
        and all(len(value) == 64 for value in (draft_digest, patch_digest, preparation_digest))
        and isinstance(draft.get("patch_text"), str)
    )
    if not valid:
        result = {**base, "review_status": "blocked", "block_reason": "invalid_patch_draft_contract"}
    elif chosen not in _DECISIONS:
        result = {**base, "review_status": "blocked", "block_reason": "invalid_review_decision"}
    elif not actor:
        result = {**base, "review_status": "blocked", "block_reason": "missing_operator_actor"}
    else:
        structural = {
            "draft_id": _text(draft.get("draft_id"), 80),
            "draft_digest": draft_digest,
            "patch_digest": patch_digest,
            "preparation_digest": preparation_digest,
            "target_path": target,
            "decision": chosen,
            "operator_actor_digest": _digest(actor),
            "sandbox_materialization_authorized": chosen == "approve",
            "source_application_authorized": False,
            "test_execution_authorized": False,
            "operator_review_complete": chosen in {"approve", "reject"},
        }
        review_digest = _digest(structural)
        result = {
            **base,
            **structural,
            "review_status": {"approve": "approved_for_sandbox", "reject": "rejected", "defer": "deferred"}[chosen],
            "review_id": f"patch-review-{review_digest[:20]}",
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


def materialize_reviewed_patch(
    draft: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    sandbox_root: str | Path,
    source_root: str | Path,
    before_text: str,
    after_text: str,
) -> dict[str, Any]:
    """Materialize one exact reviewed replacement file into an isolated sandbox."""
    base = _base()
    target = _safe_target(draft.get("target_path"))
    before_digest = _text(draft.get("before_digest"), 64)
    after_digest = _text(draft.get("after_digest"), 64)
    draft_digest = _text(draft.get("draft_digest"), 64)
    patch_digest = _text(draft.get("patch_digest"), 64)
    review_digest = _text(review.get("review_digest"), 64)
    valid_review = (
        review.get("contract_version") == CONTRACT_VERSION
        and review.get("review_status") == "approved_for_sandbox"
        and review.get("sandbox_materialization_authorized") is True
        and review.get("source_application_authorized") is False
        and review.get("test_execution_authorized") is False
        and _text(review.get("draft_digest"), 64) == draft_digest
        and _text(review.get("patch_digest"), 64) == patch_digest
        and _safe_target(review.get("target_path")) == target
        and len(review_digest) == 64
    )
    valid_draft = (
        draft.get("contract_version") == "v1181.5"
        and draft.get("draft_status") == "draft_ready"
        and draft.get("private_artifact") is True
        and draft.get("patch_applied") is False
        and bool(target)
        and all(len(value) == 64 for value in (before_digest, after_digest, draft_digest, patch_digest))
    )
    if not valid_draft or not valid_review:
        result = {**base, "materialization_status": "blocked", "block_reason": "invalid_review_binding"}
        result["materialization_receipt_digest"] = _digest(result)
        return result
    if not isinstance(before_text, str) or not isinstance(after_text, str) or "\x00" in before_text or "\x00" in after_text:
        result = {**base, "materialization_status": "blocked", "block_reason": "invalid_source_text"}
        result["materialization_receipt_digest"] = _digest(result)
        return result
    before_bytes, after_bytes = before_text.encode(), after_text.encode()
    if len(before_bytes) > MAX_SOURCE_BYTES or len(after_bytes) > MAX_SOURCE_BYTES:
        result = {**base, "materialization_status": "blocked", "block_reason": "source_text_too_large"}
        result["materialization_receipt_digest"] = _digest(result)
        return result
    if _digest_bytes(before_bytes) != before_digest or _digest_bytes(after_bytes) != after_digest:
        result = {**base, "materialization_status": "blocked", "block_reason": "source_text_digest_mismatch"}
        result["materialization_receipt_digest"] = _digest(result)
        return result

    sandbox = Path(sandbox_root).expanduser().resolve()
    source = Path(source_root).expanduser().resolve()
    if sandbox == source or _inside(sandbox, source) or _inside(source, sandbox):
        result = {**base, "materialization_status": "blocked", "block_reason": "sandbox_not_isolated"}
        result["materialization_receipt_digest"] = _digest(result)
        return result
    destination = sandbox.joinpath(*PurePosixPath(target).parts)
    if _has_symlink_component(sandbox, destination):
        result = {**base, "materialization_status": "blocked", "block_reason": "sandbox_symlink_boundary"}
        result["materialization_receipt_digest"] = _digest(result)
        return result

    sandbox.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _has_symlink_component(sandbox, destination):
        result = {**base, "materialization_status": "blocked", "block_reason": "sandbox_symlink_boundary"}
        result["materialization_receipt_digest"] = _digest(result)
        return result
    if destination.exists():
        existing = destination.read_bytes()
        existing_digest = _digest_bytes(existing)
        if existing_digest == after_digest:
            status = "already_materialized"
        elif existing_digest != before_digest:
            result = {**base, "materialization_status": "blocked", "block_reason": "sandbox_target_drift", "target_path": target}
            result["materialization_receipt_digest"] = _digest(result)
            return result
        else:
            status = "materialized"
    else:
        status = "materialized"

    if status == "materialized":
        temp = destination.with_name(destination.name + ".eidolon-tmp")
        temp.write_bytes(after_bytes)
        os.replace(temp, destination)

    marker = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "sandbox_only": True,
        "target_path": target,
        "draft_digest": draft_digest,
        "review_digest": review_digest,
        "before_digest": before_digest,
        "after_digest": after_digest,
        "patch_digest": patch_digest,
    }
    marker_digest = _digest(marker)
    marker_path = sandbox / ".eidolon_sandbox_materialization.json"
    marker_path.write_text(json.dumps({**marker, "marker_digest": marker_digest}, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    result = {
        **base,
        "materialization_status": status,
        "target_path": target,
        "draft_digest": draft_digest,
        "review_digest": review_digest,
        "patch_digest": patch_digest,
        "before_digest": before_digest,
        "after_digest": after_digest,
        "sandbox_target_digest": _digest_bytes(destination.read_bytes()),
        "sandbox_marker_digest": marker_digest,
        "sandbox_file_written": status == "materialized",
        "sandbox_materialized": True,
        "content_free": True,
    }
    result["materialization_receipt_digest"] = _digest(result)
    return result


def sandbox_materialization_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version", "contract_version", "materialization_status", "block_reason", "target_path",
        "draft_digest", "review_digest", "patch_digest", "before_digest", "after_digest",
        "sandbox_target_digest", "sandbox_marker_digest", "sandbox_file_written", "sandbox_materialized",
        "materialization_receipt_digest",
    }
    summary = {key: result[key] for key in allowed if key in result}
    summary.update({
        "content_free": True,
        "source_modified": False,
        "patch_applied_to_source": False,
        "tests_executed": False,
        "authority_granted": False,
        "sandbox_only": True,
    })
    summary["summary_digest"] = _digest(summary)
    return summary
