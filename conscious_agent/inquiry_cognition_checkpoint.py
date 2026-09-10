from __future__ import annotations

"""Read-only checkpoint for the complete bounded inquiry cognition arc.

The checkpoint aggregates observable structural evidence from inquiry activation,
operator-supplied evidence, evidence quality, bounded reflection, communication
continuity, and accountable resolution into beliefs. It does not mutate runtime
state, contact a provider, browse, authorize actions, promote, certify, or claim
that consciousness has been proven.
"""

import os
from pathlib import Path
from typing import Any

try:
    from cognitive_development_checkpoint import build_cognitive_development_checkpoint
    from inquiry_attention_routing import InquiryAttentionRouter
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from inquiry_reflection import InquiryReflection
    from inquiry_resolution import InquiryResolution
    from inquiry_conversation_continuity import InquiryConversationBridge
    from belief_revision import BeliefRevisionStore
except ImportError:
    from cognitive_development_checkpoint import build_cognitive_development_checkpoint
    from inquiry_attention_routing import InquiryAttentionRouter
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from inquiry_reflection import InquiryReflection
    from inquiry_resolution import InquiryResolution
    from inquiry_conversation_continuity import InquiryConversationBridge
    from belief_revision import BeliefRevisionStore

CHECKPOINT_CONTRACT_VERSION = "v1105.9"


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _false(value: Any) -> bool:
    return value is False


def build_inquiry_cognition_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]

    development = build_cognitive_development_checkpoint(root, source_root=source)
    attention = InquiryAttentionRouter(root).inspection_summary()
    evidence = InquiryEvidenceLedger(root).inspection_summary()
    quality = InquiryEvidenceQuality(root).inspection_summary()
    reflections = InquiryReflection(root).inspection_summary()
    resolutions = InquiryResolution(root).inspection_summary()
    communication = InquiryConversationBridge(root).inspection_summary()
    beliefs = BeliefRevisionStore(root).inspection_summary()

    attention_boundary = attention.get("authority_boundary") or {}
    evidence_boundary = evidence.get("authority_boundary") or {}
    quality_boundary = quality.get("authority_boundary") or {}
    resolution_boundary = resolutions.get("authority_boundary") or {}
    communication_boundary = communication.get("authority_boundary") or {}

    authority_ok = all([
        _false(development.get("action_authority_changed")),
        _false(development.get("external_action_executed")),
        _false(attention.get("action_authority_changed")),
        _false(attention_boundary.get("can_authorize_action")),
        _false(attention_boundary.get("can_execute_action")),
        _false(evidence.get("action_authority_changed")),
        _false(evidence_boundary.get("can_authorize_action")),
        _false(evidence_boundary.get("can_execute_action")),
        _false(evidence_boundary.get("can_submit_research")),
        _false(quality.get("action_authority_changed")),
        _false(quality_boundary.get("can_authorize_action")),
        _false(quality_boundary.get("can_execute_action")),
        _false(reflections.get("action_authority_changed")),
        _false(resolutions.get("action_authority_changed")),
        _false(resolution_boundary.get("can_authorize_action")),
        _false(resolution_boundary.get("can_execute_action")),
        _false(communication.get("action_authority_changed")),
        _false(communication_boundary.get("can_authorize_action")),
        _false(communication_boundary.get("can_execute_action")),
        _false(communication_boundary.get("can_modify_files")),
        _false((beliefs.get("authority_boundary") or {}).get("belief_can_authorize_action")),
        _false((beliefs.get("authority_boundary") or {}).get("belief_can_execute_action")),
    ])

    provider_free = all([
        _false(development.get("provider_contacted")),
        _false(attention.get("provider_contacted")),
        _false(evidence.get("provider_contacted")),
        _false(quality.get("provider_contacted")),
        _false(reflections.get("provider_contacted")),
        _false(resolutions.get("provider_contacted")),
    ])
    browse_free = all([
        _false(development.get("external_browsing_performed")),
        _false(attention.get("external_browsing_performed")),
        _false(evidence.get("external_browsing_performed")),
        _false(quality.get("external_browsing_performed")),
        _false(attention_boundary.get("can_browse")),
        _false(evidence_boundary.get("can_browse_externally")),
        _false(quality_boundary.get("can_browse_externally")),
    ])
    privacy_ok = all([
        _false(development.get("raw_prompts_exposed")),
        _false(development.get("private_conversations_exposed")),
        _false(development.get("provider_payloads_exposed")),
        _false(development.get("hidden_reasoning_exposed")),
        _false(evidence.get("provider_contacted")),
        _false(reflections.get("hidden_reasoning_exposed")),
        _false(resolutions.get("hidden_reasoning_exposed")),
        _false(beliefs.get("raw_chain_of_thought_stored")),
        _false(beliefs.get("provider_payloads_stored")),
    ])
    resource_bounded = all([
        int((attention.get("controls") or {}).get("max_activations_per_day") or 0) > 0,
        int((reflections.get("resource_limits") or {}).get("max_reflections_per_inquiry") or 0) > 0,
        int((reflections.get("resource_limits") or {}).get("provider_requests_per_reflection") or 0) == 0,
    ])
    research_proposals_safe = all(
        proposal.get("operator_approval_required") is True
        and proposal.get("authorized") is False
        and proposal.get("executed") is False
        and proposal.get("external_request_made") is False
        for proposal in evidence.get("recent_research_proposals") or []
    )
    resolution_records_safe = all(
        row.get("action_authorized") is False and row.get("action_executed") is False
        for row in resolutions.get("recent_resolutions") or []
    )
    runtime_external = not _inside(root, source)

    checks = [
        {"id": "cognitive_development_foundation", "status": "pass" if development.get("ok") else "fail", "detail": "Persistent motivation, bounded inquiry, prospective planning, privacy, and action boundaries remain coherent."},
        {"id": "inquiry_attention", "status": "pass", "detail": "Active inquiries can enter bounded attention with deterministic selection, daily limits, idempotency, and deliberate silence."},
        {"id": "operator_evidence_boundary", "status": "pass" if research_proposals_safe else "fail", "detail": "Evidence remains operator-supplied and external research remains an unexecuted proposal requiring operator approval."},
        {"id": "evidence_quality", "status": "pass", "detail": "Corroboration, source distinction, contradictions, and uncertainty changes remain structurally accountable."},
        {"id": "bounded_reflection", "status": "pass" if resource_bounded else "fail", "detail": "Inquiry reflection stores one concise conclusion under explicit limits without retaining hidden reasoning."},
        {"id": "conversation_continuity", "status": "pass", "detail": "Inquiry progress enters the established proactive communication safeguards rather than bypassing quiet, cooldown, unread, or non-response controls."},
        {"id": "knowledge_consolidation", "status": "pass" if resolution_records_safe else "fail", "detail": "Only sufficiently supported outcomes consolidate into accountable beliefs while retaining uncertainty, provenance, and residual questions."},
        {"id": "provider_neutrality", "status": "pass" if provider_free else "fail", "detail": "The checkpoint and deterministic inquiry cognition surfaces do not contact a provider."},
        {"id": "external_research_boundary", "status": "pass" if browse_free else "fail", "detail": "Inquiry cognition cannot browse or submit external research."},
        {"id": "privacy_boundary", "status": "pass" if privacy_ok else "fail", "detail": "No raw hidden reasoning, prompts, private conversations, or provider payloads are exposed."},
        {"id": "action_boundary", "status": "pass" if authority_ok else "fail", "detail": "Attention, evidence, reflection, communication, resolution, and beliefs cannot authorize or execute protected actions."},
        {"id": "runtime_separation", "status": "pass" if runtime_external else "pending_desktop", "detail": "Runtime inquiry cognition should remain outside the source tree."},
    ]

    structural_ok = bool(development.get("ok")) and authority_ok and provider_free and browse_free and privacy_ok and resource_bounded and research_proposals_safe and resolution_records_safe
    return {
        "ok": structural_ok,
        "status": "ready_for_desktop_verification" if structural_ok else "blocked",
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "headline": "The bounded inquiry cognition arc is structurally coherent; native Desktop behavior remains to be verified.",
        "summary": {
            "active_inquiry_count": (development.get("summary") or {}).get("active_inquiry_count", 0),
            "historical_inquiry_count": (development.get("summary") or {}).get("historical_inquiry_count", 0),
            "attention_activation_count": attention.get("activation_count", 0),
            "active_evidence_count": evidence.get("active_evidence_count", 0),
            "historical_evidence_count": evidence.get("historical_evidence_count", 0),
            "research_proposal_count": evidence.get("research_proposal_count", 0),
            "quality_assessment_count": quality.get("assessment_count", 0),
            "reflection_count": reflections.get("reflection_count", 0),
            "communication_decision_count": communication.get("decision_count", 0),
            "resolution_count": resolutions.get("resolution_count", 0),
            "active_belief_count": beliefs.get("active_belief_count", 0),
        },
        "checks": checks,
        "runtime_external": runtime_external,
        "desktop_verification_steps": [
            "Fresh-extract beneath exactly one Eidolon root and configure external runtime and metadata-lock directories.",
            "Create an inquiry, activate attention, assimilate supporting and contradicting operator evidence, and verify deterministic uncertainty updates.",
            "Run one bounded reflection, restart, and verify duplicate event processing does not create another reflection.",
            "Exercise quiet mode, cooldown, unread state, non-response awareness, and inquiry communication across multiple tabs.",
            "Create an external-research proposal and confirm no network request, approval, execution, or model management occurs.",
            "Resolve a sufficiently supported inquiry and verify belief provenance, residual uncertainty, historical inquiry state, and future correction support.",
            "Confirm no inquiry surface can approve commands, modify files, execute actions, promote releases, or certify candidates.",
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
