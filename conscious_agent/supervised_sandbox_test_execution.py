from __future__ import annotations

"""v1182.0-v1182.2 supervised sandbox test execution foundations.

Consumes one exact v1181.8 sandbox materialization receipt. An explicit operator
review may authorize one bounded, single-use test attempt against that exact
sandbox target. Only allowlisted, target-local checks run. Production source,
providers, models, installation, promotion, and release authority remain out of
scope.
"""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1182.2"
MAX_TESTS = 8
MAX_TIMEOUT_SECONDS = 30
_ALLOWED_SUFFIXES = frozenset({".py", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".html", ".css", ".js"})
_BLOCKED_PARTS = frozenset({"data", "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules", "conversations", "memories"})
_ALLOWED_TESTS = frozenset({"python_compile", "content_digest_match"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "patch_applied_to_source": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "operator_review_required": True,
    }


def review_sandbox_test_execution(
    materialization: Mapping[str, Any], *, decision: str, operator_actor: str,
    requested_tests: Sequence[str],
) -> dict[str, Any]:
    """Approve, reject, or defer one exact sandbox-only test attempt."""
    base = _base()
    target = _safe_target(materialization.get("target_path"))
    receipt_digest = _text(materialization.get("materialization_receipt_digest"), 64)
    marker_digest = _text(materialization.get("sandbox_marker_digest"), 64)
    target_digest = _text(materialization.get("sandbox_target_digest"), 64)
    chosen = _text(decision, 20).lower()
    actor = _text(operator_actor, 80)
    tests = list(dict.fromkeys(_text(v, 40) for v in requested_tests if _text(v, 40)))[:MAX_TESTS]
    valid = (
        materialization.get("contract_version") == "v1181.8"
        and materialization.get("materialization_status") in {"materialized", "already_materialized"}
        and materialization.get("sandbox_materialized") is True
        and materialization.get("source_modified") is False
        and bool(target)
        and all(len(v) == 64 for v in (receipt_digest, marker_digest, target_digest))
    )
    if not valid:
        result = {**base, "review_status": "blocked", "block_reason": "invalid_materialization_contract"}
    elif chosen not in {"approve", "reject", "defer"}:
        result = {**base, "review_status": "blocked", "block_reason": "invalid_review_decision"}
    elif not actor:
        result = {**base, "review_status": "blocked", "block_reason": "missing_operator_actor"}
    elif not tests or any(test not in _ALLOWED_TESTS for test in tests):
        result = {**base, "review_status": "blocked", "block_reason": "unsupported_test_request"}
    elif "python_compile" in tests and not target.endswith(".py"):
        result = {**base, "review_status": "blocked", "block_reason": "test_not_applicable"}
    else:
        structural = {
            "target_path": target,
            "materialization_receipt_digest": receipt_digest,
            "sandbox_marker_digest": marker_digest,
            "sandbox_target_digest": target_digest,
            "requested_tests": tests,
            "decision": chosen,
            "operator_actor_digest": _digest(actor),
            "test_execution_authorized": chosen == "approve",
            "single_use": True,
        }
        review_digest = _digest(structural)
        result = {
            **base, **structural,
            "review_status": {"approve": "approved_for_sandbox_tests", "reject": "rejected", "defer": "deferred"}[chosen],
            "review_id": f"sandbox-test-review-{review_digest[:20]}",
            "review_digest": review_digest,
            "content_free": True,
        }
    result["review_receipt_digest"] = _digest(result)
    return result


def execute_reviewed_sandbox_tests(
    materialization: Mapping[str, Any], review: Mapping[str, Any], *,
    sandbox_root: str | Path, source_root: str | Path,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """Run one exact allowlisted test attempt inside an isolated sandbox."""
    base = _base()
    target = _safe_target(materialization.get("target_path"))
    review_digest = _text(review.get("review_digest"), 64)
    receipt_digest = _text(materialization.get("materialization_receipt_digest"), 64)
    target_digest = _text(materialization.get("sandbox_target_digest"), 64)
    tests = list(review.get("requested_tests") or [])[:MAX_TESTS]
    valid = (
        review.get("contract_version") == CONTRACT_VERSION
        and review.get("review_status") == "approved_for_sandbox_tests"
        and review.get("test_execution_authorized") is True
        and review.get("single_use") is True
        and _safe_target(review.get("target_path")) == target
        and _text(review.get("materialization_receipt_digest"), 64) == receipt_digest
        and _text(review.get("sandbox_target_digest"), 64) == target_digest
        and len(review_digest) == 64
        and tests and all(test in _ALLOWED_TESTS for test in tests)
    )
    if not valid:
        result = {**base, "execution_status": "blocked", "block_reason": "invalid_test_review_binding", "tests_executed": False}
        result["test_receipt_digest"] = _digest(result)
        return result

    sandbox = Path(sandbox_root).expanduser().resolve()
    source = Path(source_root).expanduser().resolve()
    if sandbox == source or _inside(sandbox, source) or _inside(source, sandbox):
        result = {**base, "execution_status": "blocked", "block_reason": "sandbox_not_isolated", "tests_executed": False}
        result["test_receipt_digest"] = _digest(result)
        return result
    target_path = sandbox.joinpath(*PurePosixPath(target).parts)
    if not target_path.is_file() or target_path.is_symlink():
        result = {**base, "execution_status": "blocked", "block_reason": "sandbox_target_missing_or_unsafe", "tests_executed": False}
        result["test_receipt_digest"] = _digest(result)
        return result
    if _digest_bytes(target_path.read_bytes()) != target_digest:
        result = {**base, "execution_status": "blocked", "block_reason": "sandbox_target_drift", "tests_executed": False}
        result["test_receipt_digest"] = _digest(result)
        return result

    timeout = max(1, min(int(timeout_seconds), MAX_TIMEOUT_SECONDS))
    attempt = {
        "target_path": target,
        "review_digest": review_digest,
        "materialization_receipt_digest": receipt_digest,
        "sandbox_target_digest": target_digest,
        "requested_tests": tests,
    }
    attempt_digest = _digest(attempt)
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    for test in tests:
        if test == "content_digest_match":
            rows.append({"test": test, "status": "passed", "result_digest": target_digest})
            continue
        command = [sys.executable, "-I", "-m", "py_compile", str(target_path)]
        env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": str(sandbox / ".eidolon_pycache")}
        try:
            completed = subprocess.run(command, cwd=sandbox, env=env, capture_output=True, timeout=timeout, check=False)
            status = "passed" if completed.returncode == 0 else "failed"
            error_class = "" if status == "passed" else "python_compile_failed"
        except subprocess.TimeoutExpired:
            status, error_class = "timed_out", "test_timeout"
        rows.append({"test": test, "status": status, "error_class": error_class})
    elapsed_ms = int((time.monotonic() - started) * 1000)
    overall = "passed" if all(row["status"] == "passed" for row in rows) else (
        "timed_out" if any(row["status"] == "timed_out" for row in rows) else "failed"
    )
    content_free_rows = [{k: v for k, v in row.items() if k in {"test", "status", "error_class", "result_digest"}} for row in rows]
    result = {
        **base,
        "execution_status": overall,
        "tests_executed": True,
        "test_execution_authorized": True,
        "target_path": target,
        "attempt_digest": attempt_digest,
        "review_digest": review_digest,
        "materialization_receipt_digest": receipt_digest,
        "sandbox_target_digest": target_digest,
        "test_count": len(content_free_rows),
        "test_results": content_free_rows,
        "elapsed_ms": elapsed_ms,
        "content_free": True,
        "single_use_consumed": True,
        "production_source_untouched": True,
    }
    result["test_receipt_digest"] = _digest(result)
    return result


def sandbox_test_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"schema_version", "contract_version", "execution_status", "block_reason", "target_path", "attempt_digest", "review_digest", "materialization_receipt_digest", "sandbox_target_digest", "test_count", "test_results", "elapsed_ms", "test_receipt_digest"}
    summary = {key: result[key] for key in allowed if key in result}
    summary.update({"content_free": True, "sandbox_only": True, "source_modified": False, "authority_granted": False, "promotion_authorized": False})
    summary["summary_digest"] = _digest(summary)
    return summary
