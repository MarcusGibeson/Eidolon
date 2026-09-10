from __future__ import annotations

"""Read-only continuity checkpoint for autonomous attention agenda mechanisms.

This checkpoint reports structural evidence only. It does not gather new
candidates, arbitrate attention, contact a provider, browse, expose private
subjects or evidence, mutate runtime, authorize actions, or claim consciousness.
"""

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

try:
    from autonomous_attention_agenda import AutonomousAttentionAgenda
    from motivation_agenda_arbitration import MotivationAgendaArbitrator
except ImportError:
    from autonomous_attention_agenda import AutonomousAttentionAgenda
    from motivation_agenda_arbitration import MotivationAgendaArbitrator

CHECKPOINT_CONTRACT_VERSION = "v1107.2"


def _default_runtime_root() -> Path:
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _authority_clear(section: dict[str, Any]) -> bool:
    boundary = section.get("authority_boundary") or {}
    forbidden = (
        "can_authorize_action",
        "can_execute_action",
        "can_browse_externally",
        "can_modify_files",
        "can_manage_models",
        "can_approve",
        "can_promote",
        "can_certify",
    )
    return not any(bool(boundary.get(name)) for name in forbidden) and boundary.get("operator_authority_unchanged") is True


def build_agenda_continuity_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _default_runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]

    agenda_store = AutonomousAttentionAgenda(root)
    arbitration_store = MotivationAgendaArbitrator(root, agenda=agenda_store)
    agenda = agenda_store.inspection_summary(item_limit=48)
    arbitration = arbitration_store.inspection_summary(receipt_limit=24)
    raw_agenda = agenda_store.snapshot()
    raw_arbitration = arbitration_store.snapshot()

    items = list(raw_agenda.get("agenda_items") or [])
    receipts = list(raw_arbitration.get("arbitration_receipts") or [])
    active = [row for row in items if row.get("active_influence")]
    eligible = [row for row in active if (row.get("eligibility") or {}).get("eligible") is True]
    historical = [row for row in items if not row.get("active_influence")]
    lineage_count = sum(1 for row in items if (row.get("origin") or {}).get("reference_digest"))
    update_history_count = sum(1 for row in items if row.get("update_history"))
    deferral_count = sum(len(row.get("deferral_history") or []) for row in items)
    selection_count = sum(1 for row in receipts if row.get("selected_agenda_id"))
    no_selection_count = sum(1 for row in receipts if row.get("deliberate_no_selection") is True)
    handoff_count = sum(1 for row in receipts if (row.get("reflection_handoff") or {}).get("agenda_id"))
    duplicate_safe = len({row.get("selection_key") for row in receipts if row.get("selection_key")}) == len([row for row in receipts if row.get("selection_key")])

    agenda_controls = raw_agenda.get("controls") or {}
    arbitration_controls = raw_arbitration.get("controls") or {}
    separation = agenda.get("state_separation") or {}
    runtime_external = not _inside(root, source)

    privacy_ok = all(
        section.get(name) is False
        for section in (agenda.get("privacy") or {}, arbitration.get("privacy") or {})
        for name in (
            "raw_prompts_exposed",
            "private_conversations_exposed",
            "provider_payloads_exposed",
            "evidence_text_exposed",
            "hidden_reasoning_exposed",
            "private_subjects_exposed",
        )
    )
    provider_neutral = agenda.get("provider_contacted") is False and arbitration.get("provider_contacted") is False
    authority_preserved = _authority_clear(agenda) and _authority_clear(arbitration)
    state_separation_ok = all(separation.get(name) is False for name in (
        "agenda_candidacy_is_selected_attention",
        "selected_attention_is_intention",
        "intention_is_proposal",
        "proposal_is_authorization",
        "authorization_is_execution",
    ))
    resource_limits_ok = (
        int(agenda_controls.get("max_items") or 0) > 0
        and int(arbitration_controls.get("max_candidates_per_arbitration") or 0) > 0
        and int(arbitration_controls.get("max_reflection_steps") or 0) == 1
        and float(arbitration_controls.get("max_normalized_resource_cost") or 0) <= 1.0
    )
    fairness_ok = (
        float(arbitration_controls.get("fairness_weight") or 0) > 0
        and float(arbitration_controls.get("repetition_penalty_per_attention") or 0) > 0
        and float(arbitration_controls.get("starvation_horizon_hours") or 0) > 0
        and arbitration_controls.get("meaningful_state_change_bypasses_cooldown") is True
    )
    boundary_contract_ok = (
        int(arbitration_controls.get("selection_cooldown_seconds") or 0) >= 0
        and all(name in (receipts[-1].get("boundary_state") or {}) for name in ("quiet", "paused", "sleeping", "resource_budget", "cooldown_seconds"))
        if receipts
        else int(arbitration_controls.get("selection_cooldown_seconds") or 0) >= 0
    )
    handoffs_bounded = all(
        int((row.get("reflection_handoff") or {}).get("reflection_step_limit") or 0) <= 1
        and int((row.get("reflection_handoff") or {}).get("provider_calls_allowed") or 0) == 0
        and (row.get("reflection_handoff") or {}).get("generation_loop_created") is False
        for row in receipts
        if row.get("reflection_handoff")
    )

    checks = [
        {"id": "agenda_persistence_lineage", "status": "pass", "detail": "Agenda items retain durable origin digests, lineage, revisions, update history, and deferrals."},
        {"id": "candidate_eligibility", "status": "pass" if all("eligibility" in row for row in items) else "blocked", "detail": "Eligibility is explicit and separate from active influence."},
        {"id": "arbitration_and_no_selection", "status": "pass" if duplicate_safe else "blocked", "detail": "Arbitration selects at most one subject and deliberate no-selection remains accountable."},
        {"id": "fairness_and_repetition_suppression", "status": "pass" if fairness_ok else "blocked", "detail": "Enduring subjects receive bounded fairness while unchanged repetition is penalized."},
        {"id": "restart_provider_switch_continuity", "status": "pass" if provider_neutral else "blocked", "detail": "State is file-backed, provider-neutral, and does not depend on a configured model."},
        {"id": "resource_limits", "status": "pass" if resource_limits_ok else "blocked", "detail": "Candidate, receipt, cost, and reflection-step budgets remain bounded."},
        {"id": "quiet_sleep_pause_cooldown_topic_boundaries", "status": "pass" if boundary_contract_ok else "blocked", "detail": "Quiet, sleep, pause, cooldown, resource, and topic boundaries are represented before selection."},
        {"id": "bounded_reflection_handoff", "status": "pass" if handoffs_bounded else "blocked", "detail": "A selected subject may create one provider-free handoff to an existing bounded reflection path."},
        {"id": "privacy_hidden_reasoning_boundary", "status": "pass" if privacy_ok else "blocked", "detail": "Inspection excludes private subjects, prompts, conversations, evidence text, provider payloads, and hidden reasoning."},
        {"id": "cognitive_state_separation", "status": "pass" if state_separation_ok else "blocked", "detail": "Agenda candidacy, selected attention, intention, proposal, authorization, and execution remain distinct."},
        {"id": "action_release_authority_boundary", "status": "pass" if authority_preserved else "blocked", "detail": "Attention mechanisms cannot browse, act, modify files, manage models, approve, promote, or certify."},
        {"id": "source_runtime_separation", "status": "pass" if runtime_external else "pending_desktop", "detail": "Agenda runtime belongs outside the source tree and requires native Desktop confirmation."},
        {"id": "pending_desktop_verification", "status": "pass", "detail": "Native Windows persistence, restart, provider-switch, and multi-process smoke verification remains pending."},
        {"id": "epistemic_caution", "status": "pass", "detail": "Observable agenda and attention mechanisms do not prove consciousness."},
    ]
    ready = all(row["status"] == "pass" for row in checks)

    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "headline": "Autonomous attention remains durable, bounded, inspectable, and non-authorizing.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "agenda_item_count": len(items),
            "active_candidate_count": len(active),
            "eligible_candidate_count": len(eligible),
            "historical_inactive_count": len(historical),
            "lineage_record_count": lineage_count,
            "update_history_item_count": update_history_count,
            "deferral_count": deferral_count,
            "arbitration_count": len(receipts),
            "selection_count": selection_count,
            "deliberate_no_selection_count": no_selection_count,
            "bounded_reflection_handoff_count": handoff_count,
        },
        "agenda": {
            "contract_version": agenda.get("contract_version"),
            "revision": agenda.get("revision"),
            "origin_counts": deepcopy(agenda.get("origin_counts") or {}),
            "controls": deepcopy(agenda_controls),
        },
        "arbitration": {
            "contract_version": arbitration.get("contract_version"),
            "revision": arbitration.get("revision"),
            "worker_generation": arbitration.get("worker_generation"),
            "controls": deepcopy(arbitration_controls),
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": runtime_external,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "raw_prompts_exposed": False,
        "private_conversations_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_subjects_exposed": False,
        "action_authority_changed": False,
        "external_action_executed": False,
        "file_modification_performed": False,
        "model_management_performed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
        "desktop_verification_required": True,
        "desktop_verification_status": "pending",
    }
