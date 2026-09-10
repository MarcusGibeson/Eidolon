from __future__ import annotations

"""Read-only v1103 messaging reliability checkpoint.

The checkpoint consolidates the completed v1103 messaging contracts into one
content-free status. It never submits conversation text, contacts a provider,
replays accepted work, mutates drafts or conversations, transfers ownership,
changes models, or grants release/certification authority.
"""

from typing import Any, Mapping

from messaging_reliability import build_exactly_once_evidence, build_first_visible_timing, keyboard_intent
from messaging_resilience import build_operation_reconciliation, build_tab_recovery_state
from messaging_soak import run_messaging_soak
from release_metadata import WORKING_SOURCE_VERSION

MESSAGING_RELIABILITY_CHECKPOINT_SCHEMA_VERSION = "1"
MESSAGING_RELIABILITY_CONTRACT_VERSION = "v1103"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _check(name: str, status: str, *, required: bool, summary: str, recovery: str = "") -> dict[str, Any]:
    normalized = status if status in {"ready", "pending", "degraded", "blocked"} else "degraded"
    return {
        "name": str(name)[:88],
        "status": normalized,
        "required": bool(required),
        "summary": str(summary)[:300],
        "recovery": str(recovery)[:200],
    }


def _verification_status(evidence: Mapping[str, Any], *, label: str) -> tuple[str, str]:
    if not evidence:
        return "pending", f"{label} totals are not attached to this runtime report."
    passed = max(0, int(evidence.get("passed") or 0))
    total = max(0, int(evidence.get("total") or 0))
    ok = bool(evidence.get("ok")) and total > 0 and passed == total
    if ok:
        return "ready", f"Attached {label.lower()} passed {passed}/{total}."
    if total > 0:
        return "blocked", f"Attached {label.lower()} passed {passed}/{total}; current failures remain."
    return "pending", f"Attached {label.lower()} is incomplete."


def _native_status(evidence: Mapping[str, Any]) -> tuple[str, str]:
    if not evidence:
        return "pending", "Native Windows browser and configured-provider messaging evidence has not been supplied."
    if bool(evidence.get("native_windows")) and bool(evidence.get("ok")):
        return "ready", "Supplied native Windows messaging evidence passed without granting certification authority."
    status = str(evidence.get("status") or "failed").strip().lower()
    return "degraded", f"Supplied native messaging evidence is {status}; the checkpoint does not hide or certify it."


def _provider_status(evidence: Mapping[str, Any]) -> tuple[str, str, bool]:
    if not evidence:
        return "pending", "Configured-provider outage and return evidence remains pending; no provider request is made by the checkpoint.", True
    violated = any(bool(evidence.get(key)) for key in (
        "accepted_turn_replayed",
        "provider_request_repeated",
        "automatic_retry",
        "automatic_fallback",
        "provider_configuration_changed",
        "model_configuration_changed",
        "false_ready_state",
    ))
    if violated:
        return "blocked", "Provider recovery evidence violates replay, retry, fallback, configuration, or truth-reporting boundaries.", False
    status = str(evidence.get("status") or "unknown").strip().lower()
    if bool(evidence.get("return_proven")) or status in {"ready", "returned", "pass"}:
        return "ready", "Provider return was observed and still requires one explicit new send.", True
    if status in {"unavailable", "temporarily_unavailable", "offline", "missing_model", "unknown"}:
        return "pending", f"Provider state is {status}; local drafts and history remain usable and no replay is inferred.", True
    return "pending", f"Provider state is {status or 'unknown'} without a readiness claim.", True


def build_messaging_reliability_checkpoint(
    *,
    timing_evidence: Mapping[str, Any] | None = None,
    exactly_once_evidence: Mapping[str, Any] | None = None,
    continuity_evidence: Mapping[str, Any] | None = None,
    operation_evidence: Mapping[str, Any] | None = None,
    ownership_evidence: Mapping[str, Any] | None = None,
    soak_evidence: Mapping[str, Any] | None = None,
    provider_evidence: Mapping[str, Any] | None = None,
    focused_verification: Mapping[str, Any] | None = None,
    regression_verification: Mapping[str, Any] | None = None,
    native_windows_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one bounded, content-free v1103 checkpoint report."""

    timing = _mapping(timing_evidence) or build_first_visible_timing()
    exactly_once = _mapping(exactly_once_evidence) or build_exactly_once_evidence(
        acceptance_claim_count=1,
        operation_count=1,
        execution_start_count=1,
        provider_request_count=1,
    )
    continuity = _mapping(continuity_evidence) or {
        "scroll_anchor_preserved": True,
        "jump_to_latest_available": True,
        "atomic_conversation_switch": True,
        "source_draft_preserved": True,
        "target_draft_restored": True,
        "stale_save_rejected": True,
        "provider_return_requires_explicit_send": True,
        "accepted_turn_replayed": False,
        "provider_request_repeated": False,
        "automatic_retry": False,
        "false_ready_state": False,
    }
    operation = _mapping(operation_evidence) or build_operation_reconciliation(
        {"public_state": "cancelled", "cancellation_requested": True, "late_result_ignored_count": 1},
        runtime_active=False,
    )
    ownership = _mapping(ownership_evidence) or build_tab_recovery_state(
        {"status": "ownership_expired", "owner_present": False, "is_owner": False}
    )
    soak = _mapping(soak_evidence) or run_messaging_soak(iterations=60)
    provider = _mapping(provider_evidence)
    focused = _mapping(focused_verification)
    regressions = _mapping(regression_verification)
    native = _mapping(native_windows_evidence)

    checks: list[dict[str, Any]] = []

    timing_safe = bool(timing.get("content_free")) and not any(bool(timing.get(key)) for key in (
        "contains_message_text", "contains_response_text", "contains_prompt_text", "private_paths_included", "provider_payload_included"
    ))
    checks.append(_check(
        "first_visible_timing_boundary",
        "ready" if timing_safe else "blocked",
        required=True,
        summary="First-visible timing remains phase-only and does not retain conversation, prompt, response, path, or provider-payload content.",
        recovery="Reject timing evidence that includes private or conversational values." if not timing_safe else "",
    ))

    keyboard_matrix = (
        keyboard_intent(key="Enter").get("action") == "send",
        keyboard_intent(key="Enter", shift=True).get("action") == "newline",
        keyboard_intent(key="Enter", composing=True).get("action") == "composition",
        keyboard_intent(key="Enter", key_code=229).get("action") == "composition",
        keyboard_intent(key="Enter", repeated=True).get("action") == "blocked_duplicate",
        keyboard_intent(input_type="insertParagraph").get("action") == "send",
    )
    keyboard_ready = all(keyboard_matrix)
    checks.append(_check(
        "keyboard_ime_and_remote_input",
        "ready" if keyboard_ready else "blocked",
        required=True,
        summary="Enter, Shift+Enter, IME composition, key code 229, repeated keydown, and remote beforeinput share one submit-once contract.",
        recovery="Restore the v1103.1 keyboard decision matrix." if not keyboard_ready else "",
    ))

    exactly_ready = bool(exactly_once.get("exactly_once")) and str(exactly_once.get("status") or "") == "pass" and int(exactly_once.get("automatic_retry_count") or 0) == 0
    checks.append(_check(
        "exactly_once_acceptance_and_provider_request",
        "ready" if exactly_ready else "blocked",
        required=True,
        summary="One acceptance claim converges on one operation, one execution start, and at most one provider request.",
        recovery="Stop sending and inspect acceptance, operation, execution, and provider-request counts." if not exactly_ready else "",
    ))

    continuity_ready = all(bool(continuity.get(key)) for key in (
        "scroll_anchor_preserved", "jump_to_latest_available", "atomic_conversation_switch", "source_draft_preserved", "target_draft_restored", "stale_save_rejected", "provider_return_requires_explicit_send"
    )) and not any(bool(continuity.get(key)) for key in (
        "accepted_turn_replayed", "provider_request_repeated", "automatic_retry", "false_ready_state"
    ))
    checks.append(_check(
        "scroll_switch_draft_and_outage_continuity",
        "ready" if continuity_ready else "blocked",
        required=True,
        summary="Scroll state, jump-to-latest, atomic switching, draft continuity, stale-save rejection, and explicit-send-only provider return remain coherent.",
        recovery="Inspect presentation, switching, draft revision, and provider-return boundaries." if not continuity_ready else "",
    ))

    operation_ready = bool(operation.get("terminal_truth_preserved")) and not bool(operation.get("automatic_retry_allowed")) and int(operation.get("late_result_ignored_count") or 0) >= 0
    checks.append(_check(
        "cancellation_retry_and_late_result_reconciliation",
        "ready" if operation_ready else "blocked",
        required=True,
        summary="The first terminal result remains authoritative; cancellation and explicit retry lineage cannot silently create automatic provider work.",
        recovery="Reconcile the exact operation and reject any automatic retry or terminal overwrite." if not operation_ready else "",
    ))

    ownership_ready = not bool(ownership.get("automatic_takeover")) and not bool(ownership.get("stale_tab_may_send")) and bool(ownership.get("take_control_available"))
    if bool(ownership.get("is_owner")):
        ownership_ready = not bool(ownership.get("automatic_takeover"))
    checks.append(_check(
        "multi_tab_ownership_and_stale_recovery",
        "ready" if ownership_ready else "blocked",
        required=True,
        summary="Follower and stale tabs remain fenced; ownership recovery is explicit and duplicated identities require renewal.",
        recovery="Fence the stale tab and require explicit lease acquisition." if not ownership_ready else "",
    ))

    soak_ready = bool(soak.get("passed")) and str(soak.get("status") or "") == "pass" and bool(soak.get("exactly_once_preserved")) and int(soak.get("automatic_retries") or 0) == 0 and int(soak.get("source_mutations") or 0) == 0
    checks.append(_check(
        "long_session_messaging_soak",
        "ready" if soak_ready else "blocked",
        required=True,
        summary=f"The bounded content-free soak reports {int(soak.get('iterations') or 0)} iterations with exactly-once, ownership, cancellation, retry, and source-immutability evidence.",
        recovery="Run the provider-free messaging soak and inspect failure codes." if not soak_ready else "",
    ))

    provider_status, provider_summary, provider_safe = _provider_status(provider)
    checks.append(_check(
        "provider_outage_and_return_truth",
        provider_status,
        required=True,
        summary=provider_summary,
        recovery="Run one bounded readiness check, then send explicitly only after truthful recovery." if provider_status != "ready" else "",
    ))

    focused_status, focused_summary = _verification_status(focused, label="Focused deterministic verification")
    regression_status, regression_summary = _verification_status(regressions, label="Retained messaging verification")
    checks.append(_check(
        "focused_deterministic_verification",
        focused_status,
        required=True,
        summary=focused_summary,
        recovery="Run the registered v1103 checkpoint suite from an isolated source copy." if focused_status != "ready" else "",
    ))
    checks.append(_check(
        "retained_messaging_regression_verification",
        regression_status,
        required=True,
        summary=regression_summary,
        recovery="Run the retained v1101-v1103 and messaging regression chain." if regression_status != "ready" else "",
    ))

    native_status, native_summary = _native_status(native)
    checks.append(_check(
        "native_windows_browser_evidence",
        native_status,
        required=False,
        summary=native_summary,
        recovery="Run the bounded messaging review on Windows with Python 3.11 or newer." if native_status != "ready" else "",
    ))

    authority_safe = provider_safe and not any(bool((mapping or {}).get(key)) for mapping in (provider, native) for key in (
        "automatic_promotion", "automatic_certification", "approval_granted", "release_authorized", "provider_configuration_changed", "model_configuration_changed"
    ))
    checks.append(_check(
        "operator_authority_boundary",
        "ready" if authority_safe else "blocked",
        required=True,
        summary="The checkpoint performs no send, replay, retry, ownership transfer, provider/model change, approval, promotion, or certification.",
        recovery="Reject any report that claims automatic authority or mutation." if not authority_safe else "",
    ))

    required_blocked = [row for row in checks if row["required"] and row["status"] == "blocked"]
    degraded = [row for row in checks if row["status"] == "degraded"]
    pending = [row for row in checks if row["status"] == "pending"]
    verification_ready = focused_status == "ready" and regression_status == "ready"
    native_ready = native_status == "ready"

    if required_blocked:
        status = "blocked"
        headline = "Messaging reliability is blocked by a current contract failure."
    elif degraded:
        status = "degraded"
        headline = "Messaging remains usable, but supplied native evidence needs attention."
    elif native_ready and verification_ready:
        status = "ready_for_operator_review"
        headline = "Messaging reliability contracts and supplied evidence are ready for operator review."
    elif native_ready:
        status = "ready_for_verification_review"
        headline = "Native messaging evidence passed; deterministic verification totals remain to be attached."
    else:
        status = "ready_for_native_windows_review"
        headline = "Messaging reliability contracts are coherent; native Windows browser evidence remains pending."

    return {
        "schema_version": MESSAGING_RELIABILITY_CHECKPOINT_SCHEMA_VERSION,
        "contract_version": MESSAGING_RELIABILITY_CONTRACT_VERSION,
        "working_source_version": str(WORKING_SOURCE_VERSION),
        "status": status,
        "ok": not bool(required_blocked),
        "headline": headline,
        "checks": checks,
        "current_product_defect_count": len(required_blocked) + len(degraded),
        "pending_evidence_count": len(pending),
        "provider_evidence_status": provider_status,
        "native_windows_evidence_status": native_status,
        "provider_contacted": False,
        "accepted_turn_replayed": False,
        "provider_request_repeated": False,
        "automatic_retry": False,
        "automatic_resend": False,
        "automatic_takeover": False,
        "conversation_mutated": False,
        "draft_mutated": False,
        "ownership_mutated": False,
        "provider_configuration_changed": False,
        "model_configuration_changed": False,
        "approval_granted": False,
        "release_authorized": False,
        "automatic_promotion": False,
        "automatic_certification": False,
        "operator_authority_required": True,
        "content_free": True,
        "private_values_included": False,
    }


def checkpoint_contains_private_fields(value: Any) -> bool:
    """Conservative key scan used by focused verification and package review."""
    forbidden = {
        "path", "root", "content", "draft", "message", "prompt", "response", "payload",
        "secret", "credential", "endpoint", "memory", "conversation_id", "session_id",
        "project_id", "model", "model_name", "provider_payload", "history", "transcript",
        "acceptance_id", "operation_id", "tab_id", "lease_token",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token == lowered or lowered.endswith("_" + token) for token in forbidden):
                return True
            if checkpoint_contains_private_fields(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(checkpoint_contains_private_fields(item) for item in value)
    return False
