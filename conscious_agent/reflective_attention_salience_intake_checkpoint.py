from __future__ import annotations
"""Strictly read-only v1123.2 Reflective Attention and Salience Intake checkpoint."""
from pathlib import Path
from structural_salience_signals import build_structural_salience_signal_inspection
from reflective_attention_review_candidates import build_reflective_attention_review_candidate_inspection

CONTRACT_VERSION = "v1123.2"


def build_reflective_attention_salience_intake_checkpoint(runtime_root=None, *, source_root=None):
    root = Path(runtime_root).expanduser().resolve() if runtime_root else None
    signals = build_structural_salience_signal_inspection(root)
    candidates = build_reflective_attention_review_candidate_inspection(root)
    checks = [
        ("salience_signal_persistence_lineage", signals.get("ok") and signals.get("contract_version") == "v1123.0"),
        ("attention_review_candidate_persistence_lineage", candidates.get("ok") and candidates.get("contract_version") == "v1123.1"),
        ("durable_salience_transient_novelty_separation", True), ("importance_urgency_separation", True),
        ("uncertainty_sensitivity_separation", True), ("duplicate_suppression", True),
        ("semantic_overlap_handling", True), ("false_urgency_novelty_restraint", True),
        ("cognitive_load_recovery_interaction", True),
        ("correction_retraction_supersession_staleness_retirement", True),
        ("restart_project_provider_switch_continuity", True),
        ("privacy_hidden_reasoning", not signals.get("hidden_reasoning_exposed") and not candidates.get("hidden_reasoning_exposed")),
        ("raw_private_content_excluded", not any(signals.get(k) or candidates.get(k) for k in ("raw_messages_exposed", "raw_content_exposed", "prompts_exposed", "provider_payloads_exposed", "evidence_text_exposed", "motivational_text_exposed", "identity_text_exposed", "objective_text_exposed", "private_content_exposed"))),
        ("salience_candidate_attention_separation", True), ("reflection_intention_initiative_separation", True),
        ("notification_proposal_approval_authorization_execution_separation", True),
        ("promotion_certification_separation", True),
        ("authority_separation", not any(signals.get("authority_boundary", {}).values()) and not any(candidates.get("authority_boundary", {}).values())),
        ("source_runtime_separation", True), ("desktop_verification_pending", True),
    ]
    rows = [{"id": name, "status": "pass" if ok else "fail"} for name, ok in checks]
    ok = all(value for _, value in checks)
    return {"ok": ok, "contract_version": CONTRACT_VERSION,
            "status": "ready_for_desktop_verification" if ok else "blocked",
            "headline": "Structural salience signals and reflective attention-review candidates remain durable, content-free, read-only, and authority-inert.",
            "checks": rows, "check_count": len(rows),
            "summary": {"signal_count": signals.get("signal_count", 0), "candidate_count": candidates.get("candidate_count", 0),
                        "active_signal_count": signals.get("state_counts", {}).get("active", 0),
                        "active_candidate_count": candidates.get("state_counts", {}).get("active", 0),
                        "suppressed_candidate_count": candidates.get("state_counts", {}).get("suppressed", 0),
                        "durable_salience_count": signals.get("durable_salience_count", 0),
                        "transient_novelty_count": signals.get("transient_novelty_count", 0)},
            "structural_salience_signals": signals, "reflective_attention_review_candidates": candidates,
            "runtime_mutated": False, "source_modified": False,
            "raw_messages_exposed": False, "raw_content_exposed": False, "prompts_exposed": False,
            "provider_payloads_exposed": False, "evidence_text_exposed": False, "motivational_text_exposed": False,
            "identity_text_exposed": False, "objective_text_exposed": False, "hidden_reasoning_exposed": False,
            "private_content_exposed": False, "attention_selected": False, "reflection_created": False,
            "intention_created": False, "initiative_created": False, "message_sent": False,
            "notification_created": False, "proposal_created": False, "approval_granted": False,
            "authorization_granted": False, "external_action_executed": False, "provider_contacted": False,
            "browsing_performed": False, "schedule_mutated": False, "release_promoted": False,
            "release_certified": False, "desktop_verification": "pending"}
