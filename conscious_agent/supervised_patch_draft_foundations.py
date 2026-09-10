from __future__ import annotations

"""v1181.3-v1181.5 supervised patch draft foundations.

Consumes an exact v1181.2 preparation candidate and caller-supplied before/after
text for its single bound target. It may construct a bounded private unified-diff
draft in memory. It never reads or writes repository files, applies a patch,
runs tests, invokes a shell/tool/provider/model, or grants approval/authority.
"""

import difflib
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1181.5"
MAX_SOURCE_BYTES = 262_144
MAX_PATCH_BYTES = 262_144
MAX_PATCH_LINES = 4_096
_ALLOWED_SUFFIXES = frozenset({".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".toml", ".yaml", ".yml"})
_BLOCKED_PARTS = frozenset({"data", "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules", "conversations", "memories"})


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
        "draft_mode": "bounded_private_in_memory",
        "repository_read": False,
        "source_modified": False,
        "patch_written": False,
        "patch_applied": False,
        "tests_executed": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "authorization_created": False,
        "implementation_started": False,
        "operator_review_required": True,
        "separate_application_approval_required": True,
        "public_diagnostics_content_free": True,
    }


def draft_supervised_patch(
    preparation_bundle: Mapping[str, Any],
    preparation_id: str,
    before_text: str,
    after_text: str,
) -> dict[str, Any]:
    """Create one bounded in-memory unified diff without touching the repository."""
    base = _base()
    prep_bundle_digest = _text(preparation_bundle.get("preparation_bundle_digest"), 64)
    valid_bundle = (
        preparation_bundle.get("contract_version") == "v1181.2"
        and preparation_bundle.get("content_free") is True
        and preparation_bundle.get("source_modified") is False
        and preparation_bundle.get("patch_created") is False
        and preparation_bundle.get("tests_executed") is False
        and len(prep_bundle_digest) == 64
    )
    selected = None
    wanted = _text(preparation_id, 80)
    for row in list(preparation_bundle.get("preparations") or [])[:32]:
        if _text(row.get("preparation_id"), 80) == wanted:
            selected = row
            break
    if not valid_bundle or not isinstance(selected, Mapping):
        result = {**base, "draft_status": "blocked", "block_reason": "invalid_preparation_contract"}
        result["draft_receipt_digest"] = _digest(result)
        return result

    target = _safe_target(selected.get("target_path"))
    baseline_digest = _text(selected.get("baseline_file_digest"), 64)
    preparation_digest = _text(selected.get("preparation_digest"), 64)
    if not target or len(baseline_digest) != 64 or len(preparation_digest) != 64:
        result = {**base, "draft_status": "blocked", "block_reason": "invalid_target_binding"}
        result["draft_receipt_digest"] = _digest(result)
        return result
    if selected.get("patch_creation_allowed") is not False or selected.get("implementation_authorized") is not False:
        result = {**base, "draft_status": "blocked", "block_reason": "unsafe_preparation_authority"}
        result["draft_receipt_digest"] = _digest(result)
        return result

    if not isinstance(before_text, str) or not isinstance(after_text, str) or "\x00" in before_text or "\x00" in after_text:
        result = {**base, "draft_status": "blocked", "block_reason": "invalid_source_text"}
        result["draft_receipt_digest"] = _digest(result)
        return result
    before_bytes = before_text.encode("utf-8")
    after_bytes = after_text.encode("utf-8")
    if len(before_bytes) > MAX_SOURCE_BYTES or len(after_bytes) > MAX_SOURCE_BYTES:
        result = {**base, "draft_status": "blocked", "block_reason": "source_text_too_large"}
        result["draft_receipt_digest"] = _digest(result)
        return result
    actual_before_digest = _digest_bytes(before_bytes)
    if actual_before_digest != baseline_digest:
        result = {
            **base,
            "draft_status": "stale_source",
            "block_reason": "baseline_text_digest_mismatch",
            "target_path": target,
            "expected_baseline_digest": baseline_digest,
            "actual_baseline_digest": actual_before_digest,
        }
        result["draft_receipt_digest"] = _digest(result)
        return result
    if before_text == after_text:
        result = {**base, "draft_status": "blocked", "block_reason": "no_change", "target_path": target}
        result["draft_receipt_digest"] = _digest(result)
        return result

    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    patch_lines = list(difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{target}", tofile=f"b/{target}", lineterm=""))
    patch_text = "\n".join(patch_lines)
    patch_bytes = patch_text.encode("utf-8")
    if len(patch_lines) > MAX_PATCH_LINES or len(patch_bytes) > MAX_PATCH_BYTES:
        result = {**base, "draft_status": "blocked", "block_reason": "patch_too_large", "target_path": target}
        result["draft_receipt_digest"] = _digest(result)
        return result

    added = sum(1 for line in patch_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in patch_lines if line.startswith("-") and not line.startswith("---"))
    after_digest = _digest_bytes(after_bytes)
    structural = {
        "preparation_id": wanted,
        "preparation_digest": preparation_digest,
        "preparation_bundle_digest": prep_bundle_digest,
        "target_path": target,
        "before_digest": actual_before_digest,
        "after_digest": after_digest,
        "patch_digest": _digest_bytes(patch_bytes),
        "patch_line_count": len(patch_lines),
        "added_line_count": added,
        "removed_line_count": removed,
        "single_target": True,
        "reversible": True,
        "sandbox_required": True,
        "operator_review_required": True,
        "separate_application_approval_required": True,
        "application_authorized": False,
        "test_execution_authorized": False,
    }
    draft_digest = _digest(structural)
    result = {
        **base,
        "draft_status": "draft_ready",
        "draft_id": f"patch-draft-{draft_digest[:20]}",
        "draft_digest": draft_digest,
        **structural,
        "patch_text": patch_text,
        "contains_source_content": True,
        "private_artifact": True,
        "public_diagnostics_safe": False,
    }
    result["draft_receipt_digest"] = _digest({k: v for k, v in result.items() if k != "patch_text"})
    return result


def patch_draft_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return a content-free review summary; never copy patch/source text."""
    allowed = {
        "schema_version", "contract_version", "draft_status", "block_reason", "draft_id", "draft_digest",
        "draft_receipt_digest", "preparation_id", "preparation_digest", "preparation_bundle_digest", "target_path",
        "before_digest", "after_digest", "patch_digest", "patch_line_count", "added_line_count", "removed_line_count",
        "single_target", "reversible", "sandbox_required", "operator_review_required",
        "separate_application_approval_required", "application_authorized", "test_execution_authorized",
    }
    summary = {k: result[k] for k in allowed if k in result}
    summary.update({
        "content_free": True,
        "patch_text_included": False,
        "raw_source_included": False,
        "source_modified": False,
        "patch_applied": False,
        "tests_executed": False,
        "authority_granted": False,
    })
    summary["summary_digest"] = _digest(summary)
    return summary


def patch_draft_prompt(summary: Mapping[str, Any]) -> str:
    return (
        "Supervised patch draft:\n"
        f"- Status: {_text(summary.get('draft_status'), 40) or 'blocked'}.\n"
        f"- Target: {_text(summary.get('target_path'), 160) or 'none'}.\n"
        "- The private draft is not applied, tested, approved, or authorized for application."
    )
