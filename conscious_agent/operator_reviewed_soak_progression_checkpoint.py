from __future__ import annotations

"""Read-only v1195.5 Operator-Reviewed Soak Progression checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from long_session_multi_day_soak_checkpoint import build_long_session_multi_day_soak_checkpoint
from operator_reviewed_soak_progression import ACTION_TARGETS, ACTIONS, create_soak_progression_request, create_soak_progression_review, public_soak_progression_summary, review_soak_progression
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1195.5"
_CHECKPOINT_ID = "operator-reviewed-soak-progression-checkpoint"
_LIMITATIONS = (
    "Operator decisions are content-free presentation evidence and do not start, pause, resume, cancel, or recover a soak.",
    "No private conversation, cognition, campaign, queue, cancellation, interruption, restart, or recovery record is fetched.",
    "No approval is created or consumed, and no provider, model, process, thread, runtime mutation, or execution occurs.",
    "Adversarial restart storms, resource exhaustion, cancellation races, and long-duration drift remain for v1195.6-v1195.8.",
    "Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    excluded = {"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "reports"}
    for base, directories, files in os.walk(root):
        directories[:] = sorted(item for item in directories if item not in excluded)
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            body = path.read_bytes()
            count += 1
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(body).digest())
    return digest.hexdigest(), count


def _resign(row: dict[str, Any], digest_field: str) -> None:
    from operator_reviewed_soak_progression import _digest

    row.pop(digest_field, None)
    row[digest_field] = _digest(row)


def build_operator_reviewed_soak_progression_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    foundation = build_long_session_multi_day_soak_checkpoint(source_root=source, runtime_root=runtime_root)
    soak_summary = dict(foundation["summary"])
    snapshot = _h("v1195.5:snapshot")
    context = _h("v1195.5:context")
    soak_summary.update(
        {
            "soak_digest": _h("v1195.5:soak"),
            "plan_digest": _h("v1195.5:plan"),
            "terminal_interval_digest": _h("v1195.5:terminal"),
            "foreground_path_available": True,
            "global_profile_pass_claimed": False,
        }
    )

    def make_request(
        *,
        action: str,
        current_state: str,
        sequence: int,
        previous_digest: str,
        session_index: int = 0,
        day_index: int = 0,
    ) -> dict[str, Any]:
        purpose = {
            "pause_observation": "operator_pause_review",
            "resume_observation": "operator_resume_review",
            "review_interruption": "operator_interruption_review",
            "review_restart": "operator_restart_review",
        }.get(action, "operator_interval_disposition" if action.startswith("present_") else "operator_soak_progression")
        return create_soak_progression_request(
            progression_id=f"progression:v1195.5:{sequence}:{action}",
            soak_id="soak:v1195.5",
            soak_digest=soak_summary["soak_digest"],
            plan_digest=soak_summary["plan_digest"],
            terminal_interval_digest=soak_summary["terminal_interval_digest"],
            snapshot_digest=snapshot,
            context_digest=context,
            action=action,
            current_lifecycle_state=current_state,
            target_lifecycle_state=ACTION_TARGETS[action],
            purpose_code=purpose,
            session_index=session_index,
            day_index=day_index,
            transition_sequence=sequence,
            previous_transition_digest=previous_digest,
            artifact_digest=_h(f"artifact:{sequence}:{action}"),
            receipt_digest=_h(f"receipt:{sequence}:{action}"),
        )

    def make_review(request: Mapping[str, Any], decision: str = "approve") -> dict[str, Any]:
        return create_soak_progression_review(
            request_digest=str(request["request_digest"]),
            review_id=f"review:{request['progression_id']}:{decision}",
            decision=decision,
            operator_review_digest=_h(f"operator:{request['progression_id']}:{decision}"),
            reason_code=f"operator_{decision}",
        )

    decisions: dict[str, dict[str, Any]] = {}
    for decision in ("approve", "reject", "defer"):
        request = make_request(action="continue_observation", current_state="review_required", sequence=0, previous_digest="")
        decisions[decision] = review_soak_progression(
            soak_summary=soak_summary,
            request=request,
            review=make_review(request, decision),
            current_snapshot_digest=snapshot,
            current_context_digest=context,
        )
    require(decisions["approve"]["status"] == "progression_presented")
    require(decisions["reject"]["status"] == "progression_rejected")
    require(decisions["defer"]["status"] == "progression_deferred")

    action_states = {
        "continue_observation": "review_required",
        "pause_observation": "observation_only",
        "resume_observation": "paused_evidence_only",
        "review_interruption": "review_required",
        "review_restart": "review_required",
        "present_completion": "observation_only",
        "present_failure": "observation_only",
        "present_blocked": "review_required",
        "present_inconclusive": "review_required",
    }
    transitions: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for sequence, action in enumerate(ACTIONS):
        request = make_request(
            action=action,
            current_state=action_states[action],
            sequence=sequence,
            previous_digest=str(previous.get("transition_digest") if previous else ""),
            session_index=min(sequence, 8),
            day_index=min(sequence // 3, 2),
        )
        result = review_soak_progression(
            soak_summary=soak_summary,
            request=request,
            review=make_review(request),
            current_snapshot_digest=snapshot,
            current_context_digest=context,
            previous_transition=previous,
        )
        transitions.append(result)
        previous = result
        require(result["status"] == "progression_presented")
        require(result["action"] == action)
        require(result["transition_sequence"] == sequence)
        require(result["accountable_transition_presented"] is True)
        require(result["exact_lineage_verified"] is True)
        require(result["original_evidence_preserved"] is True)
        require(result["progression_started"] is False)
        require(result["execution_invoked"] is False)
        require(result["authority_granted"] is False)

    blocked: dict[str, dict[str, Any]] = {}

    def case(name: str, mutate: Any, *, action: str = "continue_observation") -> None:
        request = make_request(action=action, current_state=action_states[action], sequence=0, previous_digest="")
        review = make_review(request)
        summary = dict(soak_summary)
        previous_transition: dict[str, Any] | None = None
        mutate(request, review, summary)
        blocked[name] = review_soak_progression(
            soak_summary=summary,
            request=request,
            review=review,
            current_snapshot_digest=snapshot,
            current_context_digest=context,
            previous_transition=previous_transition,
        )

    case("stale-snapshot", lambda q, r, s: (q.__setitem__("snapshot_digest", _h("stale")), _resign(q, "request_digest")))
    case("stale-context", lambda q, r, s: (q.__setitem__("context_digest", _h("stale")), _resign(q, "request_digest")))
    case("stale-soak", lambda q, r, s: (q.__setitem__("soak_digest", _h("stale")), _resign(q, "request_digest")))
    case("stale-plan", lambda q, r, s: (q.__setitem__("plan_digest", _h("stale")), _resign(q, "request_digest")))
    case("stale-terminal", lambda q, r, s: (q.__setitem__("terminal_interval_digest", _h("stale")), _resign(q, "request_digest")))
    case("unsupported-action", lambda q, r, s: (q.__setitem__("action", "execute_soak"), _resign(q, "request_digest")))
    case("unsupported-decision", lambda q, r, s: (r.__setitem__("decision", "auto_approve"), _resign(r, "review_digest")))
    case("unsupported-purpose", lambda q, r, s: (q.__setitem__("purpose_code", "hidden"), _resign(q, "request_digest")))
    case("invalid-transition", lambda q, r, s: (q.__setitem__("current_lifecycle_state", "completed_evidence_only"), _resign(q, "request_digest")), action="pause_observation")
    case("target-mismatch", lambda q, r, s: (q.__setitem__("target_lifecycle_state", "completed_evidence_only"), _resign(q, "request_digest")))
    case("malformed-digest", lambda q, r, s: (q.__setitem__("artifact_digest", "bad"), _resign(q, "request_digest")))
    case("review-mismatch", lambda q, r, s: (r.__setitem__("request_digest", _h("other")), _resign(r, "review_digest")))
    case("private-field", lambda q, r, s: (q.__setitem__("prompt", "private"), _resign(q, "request_digest")))
    case("hidden-wait", lambda q, r, s: (q.__setitem__("actual_waiting_requested", True), _resign(q, "request_digest")))
    case("automatic-continuation", lambda q, r, s: (q.__setitem__("automatic_continuation_requested", True), _resign(q, "request_digest")))
    case("hidden-execution", lambda q, r, s: (q.__setitem__("execution_requested", True), _resign(q, "request_digest")))
    case("pause-execution", lambda q, r, s: (q.__setitem__("pause_execution_requested", True), _resign(q, "request_digest")))
    case("resume-execution", lambda q, r, s: (q.__setitem__("resume_execution_requested", True), _resign(q, "request_digest")))
    case("cancellation", lambda q, r, s: (q.__setitem__("cancellation_requested", True), _resign(q, "request_digest")))
    case("recovery", lambda q, r, s: (q.__setitem__("recovery_requested", True), _resign(q, "request_digest")))
    case("runtime-mutation", lambda q, r, s: (q.__setitem__("runtime_mutation_requested", True), _resign(q, "request_digest")))
    case("provider-contact", lambda q, r, s: (q.__setitem__("provider_contact_requested", True), _resign(q, "request_digest")))
    case("thread-start", lambda q, r, s: (q.__setitem__("thread_start_requested", True), _resign(q, "request_digest")))
    case("approval-consumption", lambda q, r, s: (r.__setitem__("approval_consumed", True), _resign(r, "review_digest")))
    case("authority", lambda q, r, s: (r.__setitem__("authority_granted", True), _resign(r, "review_digest")))
    case("foreground-block", lambda q, r, s: s.__setitem__("foreground_path_available", False))
    case("evidence-loss", lambda q, r, s: s.__setitem__("original_evidence_preserved", False))
    case("lineage-loss", lambda q, r, s: s.__setitem__("exact_lineage_verified", False))
    case("hidden-debt", lambda q, r, s: s.__setitem__("inherited_debt_visible", False))
    case("global-pass", lambda q, r, s: s.__setitem__("global_profile_pass_claimed", True))
    case("tamper", lambda q, r, s: q.__setitem__("purpose_code", "tampered"))

    for report in blocked.values():
        require(report["status"] == "blocked")
        require(report["error_count"] > 0)
        require(report["progression_started"] is False)
        require(report["pause_executed"] is False)
        require(report["resume_executed"] is False)
        require(report["execution_invoked"] is False)
        require(report["runtime_mutated"] is False)
        require(report["authority_granted"] is False)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == _CHECKPOINT_ID), None)
    require(descriptor is not None)
    require((descriptor or {}).get("builder") == "build_operator_reviewed_soak_progression_checkpoint")
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry["duplicate_checkpoint_ids"])
    require(not registry["duplicate_builder_targets"])
    require(package_privacy_summary_for_root(source).get("ok") is True)
    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    summary = public_soak_progression_summary(transitions[0])
    summary.update(
        {
            "decision_count": len(decisions),
            "action_count": len(transitions),
            "transition_count": len(transitions),
            "blocked_case_count": len(blocked),
            "approve_status": decisions["approve"]["status"],
            "reject_status": decisions["reject"]["status"],
            "defer_status": decisions["defer"]["status"],
            "all_actions_presented": all(item["accountable_transition_presented"] for item in transitions),
            "multi_session_lineage_verified": all(item["exact_lineage_verified"] for item in transitions),
            "terminal_disposition_count": sum(bool(item["terminal_disposition_presented"]) for item in transitions),
        }
    )
    return {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "operator-reviewed-soak-progression:v1195.5",
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "blocked_cases": {name: item["errors"] for name, item in blocked.items()},
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "runtime_mutated": False,
        "production_source_modified": False,
        "actual_waiting_started": False,
        "automatic_continuation": False,
        "progression_started": False,
        "pause_executed": False,
        "resume_executed": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "cancellation_executed": False,
        "recovery_executed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "global_profile_pass_claimed": False,
        "authority_granted": False,
    }
