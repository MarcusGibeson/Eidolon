from __future__ import annotations

"""Content-free v1101 first-use coherence checkpoint.

The checkpoint consolidates the conversation-first startup contracts into one
read-only summary. It never sends a provider request, replays accepted work,
moves runtime data, modifies models, or grants release/certification authority.
"""

from typing import Any

from release_metadata import WORKING_SOURCE_VERSION

FIRST_USE_CHECKPOINT_SCHEMA_VERSION = "1"


def _phase_status(payload: dict[str, Any], name: str) -> str:
    progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
    rows = progress.get("phases") if isinstance(progress.get("phases"), list) else []
    for row in rows:
        if isinstance(row, dict) and str(row.get("name") or "") == name:
            return str(row.get("status") or "unknown")[:32]
    return "unknown"


def _check(name: str, status: str, *, required: bool, summary: str, recovery: str = "") -> dict[str, Any]:
    normalized = status if status in {"ready", "pending", "degraded", "blocked"} else "degraded"
    return {
        "name": name,
        "status": normalized,
        "required": bool(required),
        "summary": str(summary)[:240],
        "recovery": str(recovery)[:160],
    }


def build_first_use_coherence_checkpoint(
    bootstrap: dict[str, Any],
    *,
    native_windows_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a bounded public checkpoint from an existing bootstrap payload."""

    active_project = bootstrap.get("active_project") if isinstance(bootstrap.get("active_project"), dict) else {}
    runtime = bootstrap.get("runtime_guidance") if isinstance(bootstrap.get("runtime_guidance"), dict) else {}
    recovery = bootstrap.get("recovery") if isinstance(bootstrap.get("recovery"), dict) else {}
    provider = bootstrap.get("provider") if isinstance(bootstrap.get("provider"), dict) else {}
    windows = native_windows_evidence if isinstance(native_windows_evidence, dict) else {}

    checks: list[dict[str, Any]] = []

    shell_ok = bool(bootstrap.get("chat_interactive")) and not bool(bootstrap.get("administrative_services_loaded"))
    checks.append(_check(
        "conversation_shell",
        "ready" if shell_ok else "blocked",
        required=True,
        summary="Conversation input is interactive while administrative services remain deferred.",
        recovery="Restart the lightweight dashboard shell." if not shell_ok else "",
    ))

    project_truth = str(active_project.get("truth_status") or active_project.get("status") or "unknown")
    project_status = "ready" if project_truth == "ready" else "degraded"
    checks.append(_check(
        "active_project_truth",
        project_status,
        required=False,
        summary=f"Persisted project and working-source authority report {project_truth}.",
        recovery="Review active-project source binding." if project_status != "ready" else "",
    ))

    external_runtime = bool(runtime.get("runtime_external"))
    checks.append(_check(
        "source_runtime_boundary",
        "ready" if external_runtime else "degraded",
        required=False,
        summary="Runtime data is external to source." if external_runtime else "Runtime data is source-local and requires operator review.",
        recovery="Run the runtime guide before manually moving any data." if not external_runtime else "",
    ))

    conversation_phase = _phase_status(bootstrap, "conversation_restoration")
    ownership_phase = _phase_status(bootstrap, "conversation_ownership_restoration")
    continuity_ready = conversation_phase == "ready" and ownership_phase == "ready"
    continuity_pending = conversation_phase == "pending" or ownership_phase == "pending"
    checks.append(_check(
        "continuity_restoration",
        "ready" if continuity_ready else ("pending" if continuity_pending else "degraded"),
        required=False,
        summary="Conversation, draft, presentation, and tab ownership restoration remain independently visible.",
        recovery="Use bounded optional startup retry controls." if not continuity_ready else "",
    ))

    replay_safe = not any((
        bool(bootstrap.get("accepted_turn_replayed")),
        bool(bootstrap.get("provider_contacted")),
        bool(bootstrap.get("runtime_mutation_performed")),
        bool(recovery.get("accepted_message_replayed")),
        bool(recovery.get("provider_request_repeated")),
        bool(recovery.get("retry_is_automatic")),
        bool(recovery.get("false_ready_state")),
    ))
    checks.append(_check(
        "replay_and_mutation_safety",
        "ready" if replay_safe else "blocked",
        required=True,
        summary="Startup is read-only and does not replay accepted messages or provider requests.",
        recovery="Stop startup and inspect the violated exactly-once contract." if not replay_safe else "",
    ))

    provider_state = str(provider.get("status") or "unknown")[:48]
    provider_status = "ready" if bool(provider.get("recovery_proven")) else "pending"
    if provider.get("source") == "optional_service_failure":
        provider_status = "degraded"
    checks.append(_check(
        "provider_truth",
        provider_status,
        required=False,
        summary=f"Provider state is reported as {provider_state}; no generation request is made by the checkpoint.",
        recovery="Run one explicit bounded provider readiness check." if provider_status != "ready" else "",
    ))

    native_pass = bool(windows.get("native_windows") and windows.get("ok"))
    native_fail = bool(windows) and not native_pass
    checks.append(_check(
        "native_windows_evidence",
        "ready" if native_pass else ("degraded" if native_fail else "pending"),
        required=False,
        summary="Native Windows startup evidence passed." if native_pass else (
            "Supplied native Windows evidence did not pass." if native_fail else "Native Windows startup evidence remains operator-controlled and pending."
        ),
        recovery="Run the bounded startup soak on Windows with Python 3.11 or newer." if not native_pass else "",
    ))

    required_blocked = [row for row in checks if row["required"] and row["status"] == "blocked"]
    current_defects = [row for row in checks if row["status"] in {"blocked", "degraded"}]
    pending = [row for row in checks if row["status"] == "pending"]
    if required_blocked:
        status = "blocked"
        headline = "First-use coherence is blocked by a current product contract failure."
    elif current_defects:
        status = "degraded"
        headline = "First-use remains usable, but one or more coherence checks need attention."
    elif native_pass:
        status = "ready"
        headline = "First-use coherence and supplied native Windows evidence are ready for operator review."
    else:
        status = "ready_for_native_windows_review"
        headline = "First-use coherence is ready for native Windows review."

    return {
        "schema_version": FIRST_USE_CHECKPOINT_SCHEMA_VERSION,
        "working_source_version": str(WORKING_SOURCE_VERSION),
        "status": status,
        "ok": not bool(required_blocked),
        "headline": headline,
        "checks": checks,
        "current_product_defect_count": len(current_defects),
        "pending_evidence_count": len(pending),
        "chat_remains_usable": bool(bootstrap.get("chat_interactive")),
        "provider_contacted": False,
        "accepted_turn_replayed": False,
        "provider_request_repeated": False,
        "runtime_mutation_performed": False,
        "models_changed": False,
        "automatic_retry": False,
        "automatic_migration": False,
        "automatic_promotion": False,
        "automatic_certification": False,
        "operator_authority_required": True,
        "content_free": True,
        "private_values_included": False,
    }


def checkpoint_contains_private_fields(value: Any) -> bool:
    """Conservative key scan used by focused verification and packaging review."""

    forbidden = {
        "path", "root", "content", "draft", "message", "prompt", "response", "payload",
        "secret", "credential", "endpoint", "memory", "conversation_id", "session_id",
        "project_id", "model_name", "provider_payload",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token == lowered or lowered.endswith("_" + token) for token in forbidden):
                return True
            if checkpoint_contains_private_fields(item):
                return True
    elif isinstance(value, list):
        return any(checkpoint_contains_private_fields(item) for item in value)
    return False
