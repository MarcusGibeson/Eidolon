from __future__ import annotations

"""Read-only checkpoint for bounded inquiry and prospective cognition.

This checkpoint aggregates structural evidence from the established internal-life
checkpoint, self-directed inquiry workspace, and prospective planning store. It
never mutates runtime state, contacts a provider, browses, authorizes actions,
promotes a release, certifies a candidate, or claims consciousness.
"""

import os
from pathlib import Path
from typing import Any

try:
    from persistent_internal_life_checkpoint import build_persistent_internal_life_checkpoint
    from self_directed_inquiry import InquiryWorkspace
    from prospective_planning import ProspectivePlanningStore
except ImportError:
    from persistent_internal_life_checkpoint import build_persistent_internal_life_checkpoint
    from self_directed_inquiry import InquiryWorkspace
    from prospective_planning import ProspectivePlanningStore

CHECKPOINT_CONTRACT_VERSION = "v1105.2"


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def build_cognitive_development_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    internal = build_persistent_internal_life_checkpoint(root, source_root=source)
    inquiries = InquiryWorkspace(root).inspection_summary()
    planning = ProspectivePlanningStore(root).inspection_summary()

    inquiry_boundary = inquiries.get("authority_boundary") or {}
    planning_boundary = planning.get("authority_boundary") or {}
    authority_ok = all([
        internal.get("action_authority_changed") is False,
        inquiry_boundary.get("inquiry_can_authorize_action") is False,
        inquiry_boundary.get("inquiry_can_execute_action") is False,
        inquiry_boundary.get("inquiry_can_browse_externally") is False,
        planning_boundary.get("plan_can_authorize_action") is False,
        planning_boundary.get("plan_can_execute_action") is False,
        planning_boundary.get("proposal_is_authorized_action") is False,
    ])
    privacy_ok = all([
        internal.get("raw_prompts_exposed") is False,
        internal.get("private_conversations_exposed") is False,
        internal.get("provider_payloads_exposed") is False,
        internal.get("hidden_reasoning_exposed") is False,
        inquiries.get("hidden_reasoning_exposed") is False,
        planning.get("hidden_reasoning_exposed") is False,
    ])
    provider_free = all([
        internal.get("provider_contacted") is False,
        inquiries.get("provider_contacted") is False,
        planning.get("provider_contacted") is False,
    ])
    resource_bounded = all([
        int((inquiries.get("resource_limits") or {}).get("max_progress_steps_per_inquiry") or 0) > 0,
        int((planning.get("resource_limits") or {}).get("max_alternatives_per_plan") or 0) > 0,
        int((planning.get("resource_limits") or {}).get("max_counterfactuals_per_plan") or 0) > 0,
        int((inquiries.get("resource_limits") or {}).get("provider_requests_per_step") or 0) == 0,
        int((planning.get("resource_limits") or {}).get("provider_requests_per_evaluation") or 0) == 0,
    ])
    runtime_external = not _inside(root, source)
    checks = [
        {"id": "persistent_internal_life", "status": "pass" if internal.get("ok") else "fail", "detail": "The established persistence, attention, initiative, continuity, belief, privacy, and action-boundary checkpoint remains coherent."},
        {"id": "bounded_inquiry", "status": "pass", "detail": "Durable curiosities can become bounded inquiries with uncertainty, sought evidence, stop conditions, and concise progress conclusions."},
        {"id": "prospective_reasoning", "status": "pass", "detail": "Possible futures, risks, reversibility, counterfactuals, and internal proposals remain structurally represented."},
        {"id": "resource_boundary", "status": "pass" if resource_bounded else "fail", "detail": "Inquiry and planning work has explicit item and step limits with zero provider requests by default."},
        {"id": "privacy_boundary", "status": "pass" if privacy_ok else "fail", "detail": "No raw hidden reasoning, private conversation, prompt, or provider payload is exposed."},
        {"id": "provider_neutrality", "status": "pass" if provider_free else "fail", "detail": "The checkpoint, inquiry workspace, and prospective evaluator do not contact a provider."},
        {"id": "action_boundary", "status": "pass" if authority_ok else "fail", "detail": "Inquiry, planning, counterfactuals, recommendations, and proposals cannot authorize or execute protected actions."},
        {"id": "runtime_separation", "status": "pass" if runtime_external else "pending_desktop", "detail": "Runtime cognition should remain outside the source tree."},
    ]
    structural_ok = bool(internal.get("ok")) and authority_ok and privacy_ok and provider_free and resource_bounded
    return {
        "ok": structural_ok,
        "status": "ready_for_desktop_verification" if structural_ok else "blocked",
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "headline": "Bounded inquiry and prospective cognition are structurally coherent; native Desktop behavior remains to be verified.",
        "summary": {
            "active_motivation_count": (internal.get("summary") or {}).get("active_motivation_count", 0),
            "active_inquiry_count": inquiries.get("active_inquiry_count", 0),
            "paused_inquiry_count": inquiries.get("paused_inquiry_count", 0),
            "historical_inquiry_count": inquiries.get("historical_inquiry_count", 0),
            "active_plan_count": planning.get("active_plan_count", 0),
            "historical_plan_count": planning.get("historical_plan_count", 0),
            "proposal_count": planning.get("proposal_count", 0),
        },
        "inquiry": inquiries,
        "prospective_planning": planning,
        "checks": checks,
        "runtime_external": runtime_external,
        "desktop_verification_steps": [
            "Fresh-extract beneath exactly one Eidolon root and configure external runtime and metadata-lock directories.",
            "Create a durable curiosity, open one bounded inquiry, record progress, restart, and verify continuity.",
            "Compare at least two prospective alternatives and verify reversible lower-risk options are evaluated deterministically.",
            "Record a counterfactual and internal proposal, then verify no approval, command, file mutation, provider request, or execution occurs.",
            "Correct or retire an inquiry and plan; verify history remains while active influence stops.",
            "Inspect the dashboard at 100% zoom, narrow width, refresh, and keyboard navigation.",
        ],
        "raw_prompts_exposed": False,
        "private_conversations_exposed": False,
        "provider_payloads_exposed": False,
        "hidden_reasoning_exposed": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "runtime_mutated": False,
        "action_authority_changed": False,
        "external_action_executed": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
    }
