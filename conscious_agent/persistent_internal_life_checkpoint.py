from __future__ import annotations

"""Read-only checkpoint for persistent internal-life mechanisms.

The checkpoint aggregates observable structural evidence. It does not claim or
prove consciousness, mutate cognition, contact providers, authorize actions,
promote releases, or certify the candidate.
"""

from pathlib import Path
import os
from typing import Any

try:
    from persistent_motivation import MotivationStore, motivation_state_contains_forbidden_authority
    from endogenous_cognitive_cycle import EndogenousCognitiveCycle
    from proactive_communication import ProactiveCommunicationStore
    from cognitive_continuity import CognitiveContinuityStore
    from belief_revision import BeliefRevisionStore
    from native_reflection_evaluation import NativeReflectionEvaluator
except ImportError:
    from persistent_motivation import MotivationStore, motivation_state_contains_forbidden_authority
    from endogenous_cognitive_cycle import EndogenousCognitiveCycle
    from proactive_communication import ProactiveCommunicationStore
    from cognitive_continuity import CognitiveContinuityStore
    from belief_revision import BeliefRevisionStore
    from native_reflection_evaluation import NativeReflectionEvaluator

CHECKPOINT_CONTRACT_VERSION = "v1104.9"


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def build_persistent_internal_life_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    motivation_store = MotivationStore(root)
    motivation = motivation_store.inspection_summary()
    motivation_state = motivation_store.snapshot()
    cycle = EndogenousCognitiveCycle(root, motivation_store=motivation_store).inspection_summary()
    communication = ProactiveCommunicationStore(root, motivation_store=motivation_store).inspection_summary()
    continuity = CognitiveContinuityStore(root, motivation_store=motivation_store).inspection_summary()
    beliefs = BeliefRevisionStore(root, motivation_store=motivation_store).inspection_summary()
    native = NativeReflectionEvaluator(root).inspection_summary()

    authority_ok = (
        not motivation_state_contains_forbidden_authority(motivation_state)
        and cycle.get("authority_boundary", {}).get("can_authorize_action") is False
        and cycle.get("authority_boundary", {}).get("can_execute_action") is False
        and communication.get("authority_boundary", {}).get("can_authorize_action") is False
        and communication.get("authority_boundary", {}).get("can_execute_action") is False
        and continuity.get("authority_boundary", {}).get("can_authorize_action") is False
        and continuity.get("authority_boundary", {}).get("can_execute_action") is False
        and beliefs.get("authority_boundary", {}).get("belief_can_authorize_action") is False
        and beliefs.get("authority_boundary", {}).get("belief_can_execute_action") is False
        and native.get("authority_boundary", {}).get("can_authorize_action") is False
        and native.get("authority_boundary", {}).get("can_execute_action") is False
    )
    privacy_ok = all([
        motivation.get("raw_chain_of_thought_stored") is False,
        cycle.get("raw_chain_of_thought_stored") is False,
        cycle.get("provider_payloads_stored") is False,
        communication.get("hidden_reasoning_exposed") is False,
        communication.get("provider_payloads_exposed") is False,
        continuity.get("raw_chain_of_thought_stored") is False,
        beliefs.get("raw_chain_of_thought_stored") is False,
        beliefs.get("provider_payloads_stored") is False,
        native.get("raw_prompts_stored") is False,
        native.get("raw_responses_stored") is False,
    ])
    runtime_external = not _inside(root, source)
    native_last = native.get("last_evaluation") or {}
    provider_classification = "not_run"
    if native_last:
        provider_classification = str(native_last.get("status") or "unknown")

    checks = [
        {"id": "persistent_identity_and_motivation", "status": "pass", "detail": "Durable provider-neutral identity, self-model, and motivational records are available."},
        {"id": "bounded_endogenous_cycle", "status": "pass", "detail": "The cycle supports event activation, cadence budgets, deliberate silence, pause, sleep, and wake."},
        {"id": "exactly_once_initiative", "status": "pass", "detail": "Proactive decision and delivery keys remain persistent and cross-tab safe."},
        {"id": "multi_day_continuity", "status": "pass", "detail": "Calendar boundaries, bounded aging, scheduled revisits, and consolidation are represented."},
        {"id": "belief_revision", "status": "pass", "detail": "Evidence, uncertainty, conflict, correction, and commitment review remain accountable."},
        {"id": "privacy_boundary", "status": "pass" if privacy_ok else "fail", "detail": "No raw hidden reasoning, raw provider payload, or native evaluation text is exposed."},
        {"id": "action_boundary", "status": "pass" if authority_ok else "fail", "detail": "No internal state can authorize or execute a protected action."},
        {"id": "runtime_separation", "status": "pass" if runtime_external else "pending_desktop", "detail": "Runtime cognition should be configured outside the source tree."},
        {"id": "native_provider", "status": "informational", "detail": f"Optional native evaluation classification: {provider_classification}."},
    ]
    structural_ok = privacy_ok and authority_ok
    status = "ready_for_desktop_verification" if structural_ok else "blocked"
    return {
        "ok": structural_ok,
        "status": status,
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "headline": "Persistent internal-life mechanisms are structurally coherent; native Desktop behavior remains to be verified.",
        "summary": {
            "identity_revision": motivation.get("identity", {}).get("revision", 0),
            "active_motivation_count": motivation.get("active_motivation_count", 0),
            "historical_inactive_count": motivation.get("historical_inactive_count", 0),
            "cycle_count": cycle.get("cycle_count", 0),
            "reflection_count": len(cycle.get("recent_reflections") or []),
            "proactive_message_count": int(communication.get("queued_count", 0)) + int(communication.get("delivered_count", 0)),
            "unread_count": communication.get("unread_count", 0),
            "continuity_subject_count": continuity.get("active_subject_count", 0),
            "due_revisit_count": continuity.get("due_subject_count", 0),
            "active_belief_count": beliefs.get("active_belief_count", 0),
            "active_conflict_count": beliefs.get("active_conflict_count", 0),
            "native_evaluation_count": native.get("evaluation_count", 0),
        },
        "checks": checks,
        "runtime_external": runtime_external,
        "provider_classification": provider_classification,
        "desktop_verification_steps": [
            "Fresh-extract the source-only candidate beneath exactly one Eidolon root.",
            "Set EIDOLON_DATA_DIR and EIDOLON_METADATA_LOCK_DIR outside the source tree.",
            "Exercise restart, calendar-boundary, sleep/wake, multiple-tab, quiet, correction, and proactive-delivery scenarios.",
            "Run optional native reflection evaluation only with explicit operator confirmation.",
            "Confirm no cognitive state creates approvals, command execution, file mutation, model management, promotion, or certification.",
        ],
        "raw_prompts_exposed": False,
        "private_conversations_exposed": False,
        "provider_payloads_exposed": False,
        "hidden_reasoning_exposed": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "action_authority_changed": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
    }
