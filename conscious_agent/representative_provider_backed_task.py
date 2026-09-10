from __future__ import annotations

"""v1397 representative provider-backed task with local-only privacy and offline fallback."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

CONTRACT_VERSION = "v1397.8"
TASK_ID = re.compile(r"^gamma_[a-f0-9]{12,64}$")
DENIED = {
    "eidolon_source_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "remote_provider_contact_authorized": False,
    "independent_authority_granted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _safe_plan(value: Mapping[str, Any] | None) -> dict[str, str] | None:
    row = dict(value or {})
    prefix = str(row.get("label_prefix") or "").strip().lower()
    empty = str(row.get("empty_label") or "").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,15}", prefix):
        return None
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,15}", empty):
        return None
    return {"label_prefix": prefix, "empty_label": empty}


def _fallback_plan() -> dict[str, str]:
    return {"label_prefix": "release", "empty_label": "unlabeled"}


def _loopback_endpoint(config: Mapping[str, Any]) -> str:
    endpoint = str(config.get("endpoint") or "").strip()
    try:
        parsed = urlparse(endpoint)
        host = str(parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or host not in {"localhost", "127.0.0.1", "::1"}:
            return ""
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return ""
        return endpoint.rstrip("/")
    except Exception:
        return ""


def _files(plan: Mapping[str, str]) -> dict[str, str]:
    prefix = plan["label_prefix"]
    empty = plan["empty_label"]
    module = f'''from __future__ import annotations\n\nPREFIX = {prefix!r}\nEMPTY = {empty!r}\n\ndef release_label(title: str) -> str:\n    cleaned = "-".join(str(title or "").strip().lower().split())\n    return f"{{PREFIX}}:{{cleaned}}" if cleaned else EMPTY\n'''
    tests = '''from labeler import release_label\n\nassert release_label("Gamma Ready") == "''' + prefix + ''':gamma-ready"\nassert release_label("   ") == "''' + empty + '''"\nprint({"ok": True, "passed": 2, "total": 2})\n'''
    readme = "# Provider-backed release label helper\n\nGenerated in an isolated external workspace from a bounded local-provider plan with deterministic offline fallback.\n"
    return {"labeler.py": module, "test_labeler.py": tests, "README.md": readme}


def run_provider_backed_task(
    *,
    request: str,
    runtime_root: str | Path,
    task_id: str,
    provider_config: Mapping[str, Any] | None,
    provider_call: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    provider_use_authorized: bool,
) -> dict[str, Any]:
    text = str(request or "").strip()
    root = Path(runtime_root).expanduser().resolve()
    active = Path(__file__).resolve().parents[1]
    config = dict(provider_config or {})
    if not TASK_ID.fullmatch(str(task_id or "")) or "release" not in text.lower() or "label" not in text.lower():
        return {"ok": False, "status": "provider_backed_task_unsupported", "action_executed": False, **DENIED}
    try:
        root.relative_to(active)
        return {"ok": False, "status": "provider_backed_task_eidolon_source_blocked", "action_executed": False, **DENIED}
    except ValueError:
        pass
    workspace = root / task_id
    if workspace.exists():
        return {"ok": False, "status": "provider_backed_task_already_exists", "action_executed": False, **DENIED}

    endpoint = _loopback_endpoint(config)
    local_config = bool(config.get("configured")) and config.get("provider_class") == "local" and config.get("privacy_tier") == "local_only" and bool(endpoint)
    provider_id = str(config.get("provider_id") or "unconfigured")
    payload = {
        "schema": "eidolon.gamma-provider-task.v1",
        "task_kind": "release_label_helper",
        "constraints": ["python_stdlib_only", "two_behavior_tests", "external_workspace_only"],
        "request_digest": _digest(text),
        "requested_fields": ["label_prefix", "empty_label"],
        "private_project_content_included": False,
        "filesystem_path_included": False,
    }
    provider_called = False
    provider_failure = ""
    plan: dict[str, str] | None = None
    if local_config and provider_use_authorized and provider_call is not None:
        provider_called = True
        try:
            plan = _safe_plan(provider_call(dict(payload)))
            if plan is None:
                provider_failure = "invalid_provider_response"
        except Exception as exc:
            provider_failure = type(exc).__name__
    if plan is None:
        plan = _fallback_plan()
    fallback_used = not provider_called or bool(provider_failure)

    workspace.mkdir(parents=True, exist_ok=False)
    files = _files(plan)
    for rel, content in files.items():
        (workspace / rel).write_text(content, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "test_labeler.py"],
        cwd=workspace,
        text=True,
        capture_output=True,
        timeout=20,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    if proc.returncode != 0:
        shutil.rmtree(workspace, ignore_errors=True)
        return {"ok": False, "status": "provider_backed_task_verification_failed", "action_executed": True, **DENIED}

    artifact_rows = []
    for rel in sorted(files):
        data = (workspace / rel).read_bytes()
        artifact_rows.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    core = {
        "contract_version": CONTRACT_VERSION,
        "task_id": task_id,
        "request_digest": _digest(text),
        "provider_class": "local" if local_config else "offline",
        "provider_id_digest": _digest(provider_id),
        "provider_endpoint_digest": _digest(endpoint) if endpoint else None,
        "provider_endpoint_verified_loopback": bool(endpoint),
        "provider_configured_local": local_config,
        "provider_use_authorized_for_task": bool(local_config and provider_use_authorized),
        "provider_called": provider_called,
        "provider_response_accepted": bool(provider_called and not provider_failure),
        "provider_failure_class": provider_failure or None,
        "payload_digest": _digest(payload),
        "payload_content_free": True,
        "private_project_content_transmitted": False,
        "remote_provider_contacted": False if provider_called else None,
        "offline_fallback_available": True,
        "offline_fallback_used": fallback_used,
        "feature_behavior": {"label_prefix": plan["label_prefix"], "empty_label": plan["empty_label"]},
        "artifact_manifest": artifact_rows,
        "file_count": len(artifact_rows),
        "verification_exit_code": proc.returncode,
        "verification_stdout_digest": _digest(proc.stdout.strip()),
        "runnable_result_ready": proc.returncode == 0,
        "workspace_path_exposed_in_evidence": False,
        "action_executed": True,
        **DENIED,
    }
    core["task_digest"] = _digest(core)
    return {"ok": True, "status": "provider_backed_task_complete", "provider_backed_task": core, "action_executed": True, **DENIED}


def process_provider_backed_task_control(text: str, *, project_state: Mapping[str, Any] | None = None, **_: Any) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show provider backed task", "inspect provider backed task", "show gamma provider task"}:
        return {"active": False}
    record = dict((project_state or {}).get("provider_backed_task") or {})
    return {"active": True, "ok": bool(record), "status": "provider_backed_task_found" if record else "provider_backed_task_missing", "provider_backed_task": record, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "run_provider_backed_task", "process_provider_backed_task_control"]
