from __future__ import annotations

"""Friendly operator launcher for Eidolon.

The historical main CLI remains available. This launcher exposes the handful of
commands a human can reasonably remember without becoming an archaeologist.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "conscious_agent" / "main.py"
VERIFY = ROOT / "tools" / "release_verify.py"
UPGRADE_MIGRATE = ROOT / "tools" / "upgrade_migrate.py"
STARTUP_SOAK = ROOT / "tools" / "windows_startup_soak.py"
MESSAGING_SOAK = ROOT / "tools" / "messaging_soak.py"


def _run(script: Path, *args: str) -> int:
    completed = subprocess.run([sys.executable, str(script), *args], cwd=ROOT)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(prog="eidolon", description="Eidolon supervised local artificial mind operator launcher")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show identity, project, goals, and runtime status.")
    sub.add_parser("onboarding", help="Show the built-in operator onboarding guide.")
    sub.add_parser("chat", help="Start terminal chat mode.")
    start = sub.add_parser("start", help="Start the conversation-first dashboard and open it in the default browser.")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8765)
    start.add_argument("--no-browser", action="store_true", help="Start the dashboard without opening a browser tab.")
    model_status = sub.add_parser("model-status", help="Show configured local-model provider health and model availability.")
    model_status.add_argument("--json", action="store_true", help="Emit structured JSON diagnostics.")
    model_readiness = sub.add_parser("model-readiness", help="Run bounded provider readiness diagnostics without generation.")
    model_readiness.add_argument("--json", action="store_true", help="Emit structured JSON diagnostics.")
    model_smoke = sub.add_parser("model-smoke", help="Run opt-in bounded native health, generation, streaming, and embedding checks.")
    model_smoke.add_argument("--confirm-native", action="store_true", help="Explicitly authorize native model requests.")
    model_smoke.add_argument("--timeout", type=float, default=30.0, help="Maximum read timeout used by each native check.")
    model_smoke.add_argument("--readiness-digest", default="", help="Expected readiness configuration digest; smoke blocks if settings drifted.")
    model_smoke.add_argument("--json", action="store_true", help="Emit structured JSON diagnostics.")
    conversation_validation = sub.add_parser("conversation-validation", help="Run explicitly confirmed native conversational experience validation with redacted evidence.")
    conversation_validation.add_argument("--confirm-native", action="store_true", help="Explicitly authorize bounded native conversational requests.")
    conversation_validation.add_argument("--timeout", type=float, default=45.0, help="Maximum read timeout used by each native conversation fixture.")
    conversation_validation.add_argument("--first-token-budget-ms", type=int, default=8000, help="Evidence budget for first visible token latency.")
    conversation_validation.add_argument("--total-budget-ms", type=int, default=30000, help="Evidence budget for total response latency per scenario.")
    conversation_validation.add_argument(
        "--validation-id",
        default="",
        help="Optional safe idempotency key beginning with native_conversation_.",
    )
    conversation_validation.add_argument("--json", action="store_true", help="Emit structured redacted JSON evidence.")
    doctor = sub.add_parser("doctor", help="Run the read-only diagnostic report.")
    doctor.add_argument("--full", action="store_true", help="Include the complete raw diagnostic payload.")
    sub.add_parser("stable-preview", help="Preview one supervised stable-loop decision without live execution.")

    dashboard = sub.add_parser("dashboard", help="Start the local command-deck dashboard.")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--open-browser", action="store_true", help="Open the conversation shell after health readiness.")

    runtime_guide = sub.add_parser("runtime-guide", help="Show source/runtime separation and migration guidance without moving data.")
    runtime_guide.add_argument("--json", action="store_true")
    runtime_guide.add_argument("--show-paths", action="store_true", help="Show local source and runtime paths in this terminal only.")

    runtime_migrate = sub.add_parser("runtime-migrate", help="Preview or explicitly run one copy-only external runtime-data migration.")
    runtime_migrate.add_argument("legacy_runtime_root")
    runtime_migrate.add_argument("external_runtime_root")
    runtime_migrate.add_argument("--confirm-copy", action="store_true", help="Confirm the staged copy-only migration. The legacy runtime is not deleted.")
    runtime_migrate.add_argument("--show-paths", action="store_true")

    cognitive_contract_review = sub.add_parser("cognitive-contract-review", help="Run the v1150.0 static cognitive integration review.")
    cognitive_contract_review.add_argument("--json", action="store_true")

    checkpoint_registry = sub.add_parser("checkpoint-registry", help="Inspect the consolidated source-discovered checkpoint registry.")
    checkpoint_registry.add_argument("--json", action="store_true")

    checkpoint_run = sub.add_parser("checkpoint-run", help="Invoke one registered checkpoint through the read-only dispatcher.")
    checkpoint_run.add_argument("checkpoint_id")
    checkpoint_run.add_argument("--runtime-root", default="")
    checkpoint_run.add_argument("--json", action="store_true")

    first_use_checkpoint = sub.add_parser("first-use-checkpoint", help="Summarize first-use coherence without contacting the provider or mutating runtime data.")
    first_use_checkpoint.add_argument("--json", action="store_true")

    natural_conversation_checkpoint = sub.add_parser("natural-conversation-checkpoint", help="Summarize v1102 natural-conversation coherence without contacting the provider or applying tuning.")
    natural_conversation_checkpoint.add_argument("--json", action="store_true")

    messaging_reliability_checkpoint = sub.add_parser("messaging-reliability-checkpoint", help="Summarize v1103 messaging reliability without sending, replaying, retrying, or transferring ownership.")
    messaging_reliability_checkpoint.add_argument("--json", action="store_true")

    action_intent = sub.add_parser("action-intent", help="Classify one conversational turn without saving or executing it.")
    action_intent.add_argument("text", nargs="?", default="")
    action_intent.add_argument("--json", action="store_true")

    action_catalog = sub.add_parser("action-catalog", help="Show the bounded operator-visible conversational tool catalog.")
    action_catalog.add_argument("--json", action="store_true")

    action_preview = sub.add_parser("action-preview", help="Build a redacted non-authorizing action explanation card.")
    action_preview.add_argument("text", nargs="?", default="")
    action_preview.add_argument("--json", action="store_true")

    developer_alpha = sub.add_parser("developer-alpha", help="Propose, execute, or inspect the supervised v1200 developer alpha.")
    developer_alpha.add_argument("action", choices=("propose", "execute", "status"))
    developer_alpha.add_argument("request", nargs="?", default="")
    developer_alpha.add_argument("--proposal-id", default="")
    developer_alpha.add_argument("--workspace-name", default="")
    developer_alpha.add_argument("--approve", action="store_true", help="Explicitly approve one isolated workspace implementation.")
    developer_alpha.add_argument("--json", action="store_true")

    cognition_status = sub.add_parser("cognition-status", help="Inspect persistent motivations and bounded cognitive-cycle state.")
    cognition_status.add_argument("--json", action="store_true")

    cognition_cycle = sub.add_parser("cognition-cycle", help="Run at most one bounded provider-free cognitive cycle.")
    cognition_cycle.add_argument("--event-id", default="manual-cognitive-cycle")
    cognition_cycle.add_argument("--trigger", default="manual_review", choices=("event", "cadence", "time_change", "completed_work", "failure", "memory_change", "unresolved_conversation", "manual_review", "provider_state_change"))
    cognition_cycle.add_argument("--provider-state", default="unknown", choices=("ready", "unavailable", "unknown"))
    cognition_cycle.add_argument("--json", action="store_true")

    cognition_control = sub.add_parser("cognition-control", help="Pause, resume, sleep, wake, or adjust bounded cognitive-cycle resources.")
    cognition_control.add_argument("action", choices=("pause", "resume", "sleep", "wake", "adjust_budget"))
    cognition_control.add_argument("--event-id", default="operator-cognitive-control")
    cognition_control.add_argument("--cadence-seconds", type=int)
    cognition_control.add_argument("--max-cycles-per-hour", type=int)
    cognition_control.add_argument("--max-cycles-per-day", type=int)
    cognition_control.add_argument("--json", action="store_true")

    cognition_initiative = sub.add_parser("cognition-initiative", help="Run one bounded event/reflection/communication evaluation without authorizing an action.")
    cognition_initiative.add_argument("--event-id", default="manual-cognitive-initiative")
    cognition_initiative.add_argument("--trigger", default="manual_review", choices=("event", "cadence", "time_change", "completed_work", "failure", "memory_change", "unresolved_conversation", "manual_review", "provider_state_change"))
    cognition_initiative.add_argument("--motivation-id", default="")
    cognition_initiative.add_argument("--tone", default="thoughtful", choices=("thoughtful", "practical", "playful", "affectionate", "direct"))
    cognition_initiative.add_argument("--provider-state", default="unknown", choices=("ready", "unavailable", "unknown"))
    cognition_initiative.add_argument("--json", action="store_true")

    inquiry_status = sub.add_parser("inquiry-status", help="Inspect bounded persistent inquiries without browsing or action.")
    inquiry_status.add_argument("--json", action="store_true")

    inquiry_create = sub.add_parser("inquiry-create", help="Create one bounded inquiry from an active curiosity or unresolved subject.")
    inquiry_create.add_argument("--event-id", default="operator-inquiry-create")
    inquiry_create.add_argument("--motivation-id", required=True)
    inquiry_create.add_argument("--question", required=True)
    inquiry_create.add_argument("--uncertainty", type=float, default=0.5)
    inquiry_create.add_argument("--source-sought", action="append", default=[])
    inquiry_create.add_argument("--stop-condition", action="append", default=[])
    inquiry_create.add_argument("--project-id", default="")
    inquiry_create.add_argument("--json", action="store_true")

    inquiry_attention = sub.add_parser("inquiry-attention", help="Run one bounded inquiry-attention routing decision.")
    inquiry_attention.add_argument("--event-id", default="operator-inquiry-attention")
    inquiry_attention.add_argument("--json", action="store_true")

    inquiry_evidence = sub.add_parser("inquiry-evidence", help="Inspect operator-supplied inquiry evidence and research proposals.")
    inquiry_evidence.add_argument("--json", action="store_true")

    inquiry_communication = sub.add_parser("inquiry-communication", help="Consider sharing progress from one durable inquiry through existing communication safeguards.")
    inquiry_communication.add_argument("--event-id", default="operator-inquiry-communication")
    inquiry_communication.add_argument("--inquiry-id", required=True)
    inquiry_communication.add_argument("--tone", default="thoughtful")
    inquiry_communication.add_argument("--json", action="store_true")

    inquiry_quality = sub.add_parser("inquiry-quality", help="Assess evidence quality and contradiction for one inquiry.")
    inquiry_quality.add_argument("--event-id", default="operator-inquiry-quality")
    inquiry_quality.add_argument("--inquiry-id", required=True)
    inquiry_quality.add_argument("--json", action="store_true")

    inquiry_reflect = sub.add_parser("inquiry-reflect", help="Perform one bounded provider-free inquiry reflection.")
    inquiry_reflect.add_argument("--event-id", default="operator-inquiry-reflect")
    inquiry_reflect.add_argument("--inquiry-id", required=True)
    inquiry_reflect.add_argument("--json", action="store_true")

    inquiry_resolve = sub.add_parser("inquiry-resolve", help="Consolidate a sufficiently supported inquiry into a belief.")
    inquiry_resolve.add_argument("--event-id", default="operator-inquiry-resolve")
    inquiry_resolve.add_argument("--inquiry-id", required=True)
    inquiry_resolve.add_argument("--proposition", required=True)
    inquiry_resolve.add_argument("--residual-question", default="")
    inquiry_resolve.add_argument("--json", action="store_true")

    planning_status = sub.add_parser("planning-status", help="Inspect bounded prospective plans and internal proposals.")
    planning_status.add_argument("--json", action="store_true")

    planning_compare = sub.add_parser("planning-compare", help="Evaluate an existing prospective plan without authorizing action.")
    planning_compare.add_argument("--event-id", default="operator-planning-compare")
    planning_compare.add_argument("--plan-id", required=True)
    planning_compare.add_argument("--json", action="store_true")

    internal_life_checkpoint = sub.add_parser("internal-life-checkpoint", help="Build a read-only checkpoint across persistent internal-life mechanisms.")
    internal_life_checkpoint.add_argument("--json", action="store_true")

    cognitive_development_checkpoint = sub.add_parser("cognitive-development-checkpoint", help="Build a read-only checkpoint across bounded inquiry and prospective cognition.")
    cognitive_development_checkpoint.add_argument("--json", action="store_true")

    inquiry_cognition_checkpoint = sub.add_parser("inquiry-cognition-checkpoint", help="Build the read-only v1105.9 checkpoint across the complete bounded inquiry cognition arc.")
    inquiry_cognition_checkpoint.add_argument("--json", action="store_true")

    residual_lineage = sub.add_parser("inquiry-residual-lineage", help="Inspect or create bounded residual-question child inquiry lineage.")
    residual_lineage.add_argument("--event-id", default="")
    residual_lineage.add_argument("--parent-inquiry-id", default="")
    residual_lineage.add_argument("--residual-question", default="")
    residual_lineage.add_argument("--json", action="store_true")

    evidence_lineage = sub.add_parser("cross-inquiry-evidence-lineage", help="Inspect or create accountable cross-inquiry evidence lineage.")
    evidence_lineage.add_argument("--event-id", default="")
    evidence_lineage.add_argument("--evidence-id", default="")
    evidence_lineage.add_argument("--target-inquiry-id", default="")
    evidence_lineage.add_argument("--stance", default="supports")
    evidence_lineage.add_argument("--relevance", type=float, default=0.5)
    evidence_lineage.add_argument("--json", action="store_true")

    confidence_checkpoint = sub.add_parser("knowledge-confidence-checkpoint", help="Build the read-only v1106.2 knowledge confidence maintenance checkpoint.")
    confidence_checkpoint.add_argument("--json", action="store_true")

    reconsideration_schedule = sub.add_parser("knowledge-reconsideration", help="Inspect or schedule bounded knowledge reconsideration.")
    reconsideration_schedule.add_argument("--event-id", default="")
    reconsideration_schedule.add_argument("--json", action="store_true")

    evidence_propagation = sub.add_parser("evidence-change-propagation", help="Inspect or propagate one accountable evidence change.")
    evidence_propagation.add_argument("--event-id", default="")
    evidence_propagation.add_argument("--evidence-id", default="")
    evidence_propagation.add_argument("--change-type", default="updated")
    evidence_propagation.add_argument("--json", action="store_true")

    reconsideration_communication = sub.add_parser("reconsideration-communication", help="Consider communicating one scheduled reconsideration through existing safeguards.")
    reconsideration_communication.add_argument("--event-id", default="")
    reconsideration_communication.add_argument("--schedule-id", default="")
    reconsideration_communication.add_argument("--conclusion", default="")
    reconsideration_communication.add_argument("--changed-belief", action="store_true")
    reconsideration_communication.add_argument("--tone", default="thoughtful")
    reconsideration_communication.add_argument("--json", action="store_true")

    reconsideration_reflection = sub.add_parser("reconsideration-reflection", help="Inspect or perform one bounded reconsideration reflection.")
    reconsideration_reflection.add_argument("--event-id", default="")
    reconsideration_reflection.add_argument("--schedule-id", default="")
    reconsideration_reflection.add_argument("--conclusion", default="")
    reconsideration_reflection.add_argument("--silence", action="store_true")
    reconsideration_reflection.add_argument("--json", action="store_true")

    belief_maintenance = sub.add_parser("belief-maintenance-outcome", help="Inspect or record one accountable belief-maintenance outcome.")
    belief_maintenance.add_argument("--event-id", default="")
    belief_maintenance.add_argument("--schedule-id", default="")
    belief_maintenance.add_argument("--outcome", default="retain")
    belief_maintenance.add_argument("--conclusion", default="")
    belief_maintenance.add_argument("--new-confidence", type=float)
    belief_maintenance.add_argument("--json", action="store_true")

    maintenance_consolidation = sub.add_parser("knowledge-maintenance-consolidation", help="Build the read-only v1106.8 maintenance consolidation.")
    maintenance_consolidation.add_argument("--json", action="store_true")

    maintenance_checkpoint = sub.add_parser("knowledge-maintenance-checkpoint", help="Build the read-only v1106.9 knowledge maintenance checkpoint.")
    maintenance_checkpoint.add_argument("--json", action="store_true")

    attention_agenda = sub.add_parser("attention-agenda", help="Inspect the durable autonomous attention agenda without mutating it.")
    attention_agenda.add_argument("--json", action="store_true")

    attention_arbitration = sub.add_parser("attention-arbitration", help="Inspect bounded attention arbitration receipts without selecting a subject.")
    attention_arbitration.add_argument("--json", action="store_true")

    agenda_checkpoint = sub.add_parser("attention-agenda-checkpoint", help="Build the read-only v1107.2 agenda continuity checkpoint.")
    agenda_checkpoint.add_argument("--json", action="store_true")

    reflection_intake = sub.add_parser("agenda-guided-reflection", help="Inspect v1107.3 agenda-guided reflection intake without mutating it.")
    reflection_intake.add_argument("--json", action="store_true")

    bounded_intentions = sub.add_parser("bounded-intentions", help="Inspect v1107.4 bounded non-authorizing intentions.")
    bounded_intentions.add_argument("--json", action="store_true")

    attention_intention_checkpoint = sub.add_parser("attention-intention-checkpoint", help="Build the read-only v1107.5 attention-to-intention checkpoint.")
    attention_intention_checkpoint.add_argument("--json", action="store_true")

    intention_lifecycle = sub.add_parser("intention-lifecycle", help="Inspect v1107.6 bounded intention reconsideration and decay.")
    intention_lifecycle.add_argument("--json", action="store_true")

    intention_conflicts = sub.add_parser("intention-conflicts", help="Inspect v1107.7 deterministic intention conflict receipts.")
    intention_conflicts.add_argument("--json", action="store_true")

    intention_lifecycle_review = sub.add_parser("intention-lifecycle-review", help="Build the read-only v1107.8 intention lifecycle review.")
    intention_lifecycle_review.add_argument("--json", action="store_true")

    attention_intention_final_checkpoint = sub.add_parser("autonomous-attention-intention-checkpoint", help="Build the read-only v1107.9 autonomous attention and intention checkpoint.")
    attention_intention_final_checkpoint.add_argument("--json", action="store_true")

    persistent_initiative = sub.add_parser("persistent-initiative", help="Inspect v1108.0 durable non-sending initiative candidates.")
    persistent_initiative.add_argument("--json", action="store_true")

    initiative_arbitration = sub.add_parser("initiative-arbitration", help="Inspect v1108.1 bounded communication arbitration receipts.")
    initiative_arbitration.add_argument("--json", action="store_true")

    persistent_initiative_checkpoint = sub.add_parser("persistent-initiative-checkpoint", help="Build the read-only v1108.2 persistent initiative checkpoint.")
    persistent_initiative_checkpoint.add_argument("--json", action="store_true")

    initiative_conversation_proposal = sub.add_parser("initiative-conversation-proposal", help="Inspect v1108.3 non-sending conversation proposals.")
    initiative_conversation_proposal.add_argument("--json", action="store_true")

    initiative_communication_restraint = sub.add_parser("initiative-communication-restraint", help="Inspect v1108.4 restrained communication timing decisions.")
    initiative_communication_restraint.add_argument("--json", action="store_true")

    initiative_communication_checkpoint = sub.add_parser("initiative-communication-checkpoint", help="Build the read-only v1108.5 initiative communication checkpoint.")
    initiative_communication_checkpoint.add_argument("--json", action="store_true")

    surfaced_initiative = sub.add_parser("surfaced-initiative-reconciliation", help="Inspect v1108.6 explicit normal-chat initiative surfacing receipts.")
    surfaced_initiative.add_argument("--json", action="store_true")

    initiative_response = sub.add_parser("initiative-response-reconciliation", help="Inspect v1108.7 surfaced initiative response outcomes.")
    initiative_response.add_argument("--json", action="store_true")

    initiative_lifecycle = sub.add_parser("initiative-lifecycle-checkpoint", help="Build the read-only v1108.8 initiative lifecycle checkpoint.")
    initiative_lifecycle.add_argument("--json", action="store_true")

    persistent_initiative_final = sub.add_parser("persistent-initiative-consolidation-checkpoint", help="Build the read-only v1108.9 persistent initiative checkpoint.")
    persistent_initiative_final.add_argument("--json", action="store_true")

    long_horizon_objective = sub.add_parser("long-horizon-objective", help="Inspect v1109.0 durable long-horizon objectives.")
    long_horizon_objective.add_argument("--json", action="store_true")

    objective_review = sub.add_parser("objective-review-arbitration", help="Inspect v1109.1 bounded objective review arbitration.")
    objective_review.add_argument("--json", action="store_true")

    long_horizon_checkpoint = sub.add_parser("long-horizon-objective-checkpoint", help="Build the read-only v1109.2 objective continuity checkpoint.")
    long_horizon_checkpoint.add_argument("--json", action="store_true")

    objective_milestones = sub.add_parser("objective-milestones", help="Inspect v1109.3 bounded objective milestones.")
    objective_milestones.add_argument("--json", action="store_true")

    objective_progress = sub.add_parser("objective-progress-evidence", help="Inspect v1109.4 evidence-based objective progress.")
    objective_progress.add_argument("--json", action="store_true")

    objective_planning_checkpoint = sub.add_parser("objective-planning-progress-checkpoint", help="Build the read-only v1109.5 planning and progress checkpoint.")
    objective_planning_checkpoint.add_argument("--json", action="store_true")

    objective_conflict = sub.add_parser("objective-conflict-reconciliation", help="Inspect v1109.6 objective conflict and priority reconciliation.")
    objective_conflict.add_argument("--json", action="store_true")

    objective_lifecycle = sub.add_parser("objective-completion-abandonment", help="Inspect v1109.7 objective completion and abandonment reviews.")
    objective_lifecycle.add_argument("--json", action="store_true")

    objective_lifecycle_checkpoint = sub.add_parser("long-horizon-objective-lifecycle-checkpoint", help="Build the read-only v1109.8 objective lifecycle review.")
    objective_lifecycle_checkpoint.add_argument("--json", action="store_true")

    long_horizon_follow_through_checkpoint = sub.add_parser("long-horizon-follow-through-checkpoint", help="Build the read-only v1109.9 Long-Horizon Follow-Through checkpoint.")
    long_horizon_follow_through_checkpoint.add_argument("--json", action="store_true")

    endogenous_curiosity = sub.add_parser("endogenous-curiosity", help="Inspect v1111.0 evidence-backed endogenous curiosity candidates.")
    endogenous_curiosity.add_argument("--json", action="store_true")

    curiosity_arbitration = sub.add_parser("curiosity-arbitration", help="Inspect v1111.1 bounded curiosity arbitration.")
    curiosity_arbitration.add_argument("--json", action="store_true")

    curiosity_continuity_checkpoint = sub.add_parser("curiosity-continuity-checkpoint", help="Build the read-only v1111.2 curiosity continuity checkpoint.")
    curiosity_continuity_checkpoint.add_argument("--json", action="store_true")

    curiosity_questions = sub.add_parser("curiosity-questions", help="Inspect v1111.3 bounded internal curiosity questions.")
    curiosity_questions.add_argument("--json", action="store_true")

    curiosity_quality = sub.add_parser("curiosity-quality", help="Inspect v1111.4 curiosity relevance, answerability, and intrusion restraint.")
    curiosity_quality.add_argument("--json", action="store_true")

    curiosity_quality_checkpoint = sub.add_parser("curiosity-quality-checkpoint", help="Build the read-only v1111.5 curiosity quality checkpoint.")
    curiosity_quality_checkpoint.add_argument("--json", action="store_true")

    curiosity_inquiry_promotion = sub.add_parser("curiosity-inquiry-promotion", help="Inspect v1111.6 bounded curiosity-to-inquiry promotion.")
    curiosity_inquiry_promotion.add_argument("--json", action="store_true")
    curiosity_question_lifecycle = sub.add_parser("curiosity-question-lifecycle", help="Inspect v1111.7 curiosity question lifecycle decisions.")
    curiosity_question_lifecycle.add_argument("--json", action="store_true")
    curiosity_lifecycle_checkpoint = sub.add_parser("curiosity-lifecycle-checkpoint", help="Build the read-only v1111.8 curiosity lifecycle checkpoint.")
    curiosity_lifecycle_checkpoint.add_argument("--json", action="store_true")
    endogenous_curiosity_checkpoint = sub.add_parser("endogenous-curiosity-checkpoint", help="Build the read-only v1111.9 endogenous curiosity checkpoint.")
    endogenous_curiosity_checkpoint.add_argument("--json", action="store_true")
    behavioral_outcomes = sub.add_parser("behavioral-outcomes", help="Inspect v1112.0 privacy-safe behavioral outcome evidence.")
    behavioral_outcomes.add_argument("--json", action="store_true")
    behavioral_attributions = sub.add_parser("behavioral-attributions", help="Inspect v1112.1 bounded outcome attribution.")
    behavioral_attributions.add_argument("--json", action="store_true")
    behavioral_evidence_checkpoint = sub.add_parser("behavioral-evidence-checkpoint", help="Build the read-only v1112.2 behavioral evidence continuity checkpoint.")
    behavioral_evidence_checkpoint.add_argument("--json", action="store_true")
    behavioral_patterns = sub.add_parser("behavioral-patterns", help="Inspect v1112.3 privacy-safe behavioral pattern detection.")
    behavioral_patterns.add_argument("--json", action="store_true")
    behavioral_self_evaluation = sub.add_parser("behavioral-self-evaluation", help="Inspect v1112.4 bounded behavioral self-evaluation and hypotheses.")
    behavioral_self_evaluation.add_argument("--json", action="store_true")
    behavioral_self_evaluation_checkpoint = sub.add_parser("behavioral-self-evaluation-checkpoint", help="Build the read-only v1112.5 behavioral self-evaluation checkpoint.")
    behavioral_self_evaluation_checkpoint.add_argument("--json", action="store_true")
    behavioral_adaptation_proposals = sub.add_parser("behavioral-adaptation-proposals", help="Inspect v1112.6 safe behavioral adaptation proposals.")
    behavioral_adaptation_proposals.add_argument("--json", action="store_true")
    behavioral_adaptation_lifecycle = sub.add_parser("behavioral-adaptation-lifecycle", help="Inspect v1112.7 operator-reviewed adaptation lifecycle receipts.")
    behavioral_adaptation_lifecycle.add_argument("--json", action="store_true")
    behavioral_adaptation_checkpoint = sub.add_parser("behavioral-adaptation-checkpoint", help="Build the read-only v1112.8 behavioral adaptation review checkpoint.")
    behavioral_adaptation_checkpoint.add_argument("--json", action="store_true")
    reflective_behavioral_learning_checkpoint = sub.add_parser("reflective-behavioral-learning-checkpoint", help="Build the read-only v1112.9 Reflective Behavioral Learning checkpoint.")
    reflective_behavioral_learning_checkpoint.add_argument("--json", action="store_true")
    active_inquiries = sub.add_parser("active-inquiries", help="Inspect v1113.0 bounded active inquiry records.")
    active_inquiries.add_argument("--json", action="store_true")
    inquiry_activation = sub.add_parser("inquiry-activation", help="Inspect v1113.1 deterministic inquiry activation arbitration.")
    inquiry_activation.add_argument("--json", action="store_true")
    active_inquiry_checkpoint = sub.add_parser("active-inquiry-checkpoint", help="Build the read-only v1113.2 active inquiry continuity checkpoint.")
    active_inquiry_checkpoint.add_argument("--json", action="store_true")
    inquiry_evidence_governance_checkpoint = sub.add_parser("inquiry-evidence-governance-checkpoint", help="Build the read-only v1113.5 inquiry evidence governance checkpoint.")
    inquiry_evidence_governance_checkpoint.add_argument("--json", action="store_true")
    inquiry_resolution_checkpoint = sub.add_parser("inquiry-resolution-checkpoint", help="Build the read-only v1113.8 inquiry resolution checkpoint.")
    inquiry_resolution_checkpoint.add_argument("--json", action="store_true")
    bounded_inquiry_checkpoint = sub.add_parser("bounded-inquiry-checkpoint", help="Build the read-only v1113.9 Bounded Inquiry and Epistemic Follow-Through checkpoint.")
    bounded_inquiry_checkpoint.add_argument("--json", action="store_true")
    deliberative_options = sub.add_parser("deliberative-options", help="Inspect v1114.0 durable deliberative option records.")
    deliberative_options.add_argument("--json", action="store_true")
    deliberative_option_arbitration = sub.add_parser("deliberative-option-arbitration", help="Inspect v1114.1 bounded option comparison and arbitration.")
    deliberative_option_arbitration.add_argument("--json", action="store_true")
    deliberative_continuity_checkpoint = sub.add_parser("deliberative-continuity-checkpoint", help="Build the read-only v1114.2 deliberative continuity checkpoint.")
    deliberative_continuity_checkpoint.add_argument("--json", action="store_true")
    decision_commitment_checkpoint = sub.add_parser("decision-commitment-checkpoint", help="Build the read-only v1114.5 decision commitment lifecycle checkpoint.")
    decision_commitment_checkpoint.add_argument("--json", action="store_true")
    deliberative_decision_review_checkpoint = sub.add_parser("deliberative-decision-review-checkpoint", help="Build the read-only v1114.8 deliberative decision review checkpoint.")
    deliberative_decision_review_checkpoint.add_argument("--json", action="store_true")
    reflective_planning_deliberative_choice_checkpoint = sub.add_parser("reflective-planning-deliberative-choice-checkpoint", help="Build the read-only v1114.9 Reflective Planning and Deliberative Choice checkpoint.")
    cognitive_load_continuity_checkpoint = sub.add_parser("cognitive-load-continuity-checkpoint", help="Build the read-only v1115.2 cognitive load continuity checkpoint.")
    cognitive_work_continuity_checkpoint = sub.add_parser("cognitive-work-continuity-checkpoint", help="Build the read-only v1115.5 cognitive work continuity checkpoint.")
    cognitive_coordination_review_checkpoint = sub.add_parser("cognitive-coordination-review-checkpoint", help="Build the read-only v1115.8 cognitive coordination review checkpoint.")
    cognitive_coordination_review_checkpoint.add_argument("--json", action="store_true")
    internal_coordination_cognitive_load_governance_checkpoint = sub.add_parser("internal-coordination-cognitive-load-governance-checkpoint", help="Build the read-only v1115.9 Internal Coordination and Cognitive Load Governance checkpoint.")
    internal_coordination_cognitive_load_governance_checkpoint.add_argument("--json", action="store_true")
    prospective_memory_continuity_checkpoint = sub.add_parser("prospective-memory-continuity-checkpoint", help="Build the read-only v1117.2 Prospective Memory Continuity checkpoint.")
    temporal_review_checkpoint = sub.add_parser("temporal-review-checkpoint", help="Build the read-only v1117.5 Temporal Review checkpoint.")
    temporal_review_checkpoint.add_argument("--json", action="store_true")
    prospective_continuity_review_checkpoint = sub.add_parser("prospective-continuity-review-checkpoint", help="Build the read-only v1117.8 Prospective Continuity Review checkpoint.")
    prospective_continuity_review_checkpoint.add_argument("--json", action="store_true")
    reflective_temporal_continuity_prospective_memory_checkpoint = sub.add_parser("reflective-temporal-continuity-prospective-memory-checkpoint", help="Build the read-only v1117.9 Reflective Temporal Continuity and Prospective Memory checkpoint.")
    reflective_temporal_continuity_prospective_memory_checkpoint.add_argument("--json", action="store_true")
    belief_reconsideration_intake_checkpoint = sub.add_parser("belief-reconsideration-intake-checkpoint", help="Build the read-only v1118.2 Belief Reconsideration Intake checkpoint.")
    belief_reconsideration_intake_checkpoint.add_argument("--json", action="store_true")
    belief_revision_deliberation_checkpoint = sub.add_parser("belief-revision-deliberation-checkpoint", help="Build the read-only v1118.5 Belief Revision Deliberation checkpoint.")
    belief_revision_deliberation_checkpoint.add_argument("--json", action="store_true")
    belief_continuity_review_checkpoint = sub.add_parser("belief-continuity-review-checkpoint", help="Build the read-only v1118.8 Belief Continuity Review checkpoint.")
    belief_continuity_review_checkpoint.add_argument("--json", action="store_true")
    epistemic_maintenance_belief_revision_governance_checkpoint = sub.add_parser("epistemic-maintenance-belief-revision-governance-checkpoint", help="Build the read-only v1118.9 Epistemic Maintenance and Belief Revision Governance checkpoint.")
    epistemic_maintenance_belief_revision_governance_checkpoint.add_argument("--json", action="store_true")
    epistemic_coherence_intake_checkpoint = sub.add_parser("epistemic-coherence-intake-checkpoint", help="Build the read-only v1119.2 Epistemic Coherence Intake checkpoint.")
    epistemic_coherence_intake_checkpoint.add_argument("--json", action="store_true")
    epistemic_coherence_deliberation_checkpoint = sub.add_parser("epistemic-coherence-deliberation-checkpoint", help="Build the read-only v1119.5 Epistemic Coherence Deliberation checkpoint.")
    epistemic_coherence_deliberation_checkpoint.add_argument("--json", action="store_true")
    knowledge_belief_integration_checkpoint = sub.add_parser("knowledge-belief-integration-checkpoint", help="Build the read-only v1119.8 Knowledge-Belief Integration checkpoint.")
    knowledge_belief_integration_checkpoint.add_argument("--json", action="store_true")
    epistemic_coherence_knowledge_belief_integration_checkpoint = sub.add_parser("epistemic-coherence-knowledge-belief-integration-checkpoint", help="Build the read-only v1119.9 Epistemic Coherence and Knowledge-Belief Integration checkpoint.")
    epistemic_coherence_knowledge_belief_integration_checkpoint.add_argument("--json", action="store_true")
    motivational_continuity_intake_checkpoint = sub.add_parser("motivational-continuity-intake-checkpoint", help="Build the read-only v1122.2 Motivational Continuity Intake checkpoint.")
    motivational_continuity_intake_checkpoint.add_argument("--json", action="store_true")
    motivational_drive_deliberation_checkpoint = sub.add_parser("motivational-drive-deliberation-checkpoint", help="Build the read-only v1122.5 Motivational Drive Deliberation checkpoint.")
    motivational_drive_deliberation_checkpoint.add_argument("--json", action="store_true")
    motivational_continuity_review_checkpoint = sub.add_parser("motivational-continuity-review-checkpoint", help="Build the read-only v1122.8 Motivational Continuity Review checkpoint.")
    motivational_continuity_review_checkpoint.add_argument("--json", action="store_true")
    motivational_continuity_endogenous_drive_regulation_checkpoint = sub.add_parser("motivational-continuity-endogenous-drive-regulation-checkpoint", help="Build the read-only v1122.9 Motivational Continuity and Endogenous Drive Regulation checkpoint.")
    motivational_continuity_endogenous_drive_regulation_checkpoint.add_argument("--json", action="store_true")
    reflective_attention_salience_intake_checkpoint = sub.add_parser("reflective-attention-salience-intake-checkpoint", help="Build the read-only v1123.2 Reflective Attention and Salience Intake checkpoint.")
    reflective_attention_salience_intake_checkpoint.add_argument("--json", action="store_true")
    reflective_attention_deliberation_checkpoint = sub.add_parser("reflective-attention-deliberation-checkpoint", help="Build the read-only v1123.5 Reflective Attention Deliberation checkpoint.")
    reflective_attention_deliberation_checkpoint.add_argument("--json", action="store_true")
    reflective_attention_continuity_review_checkpoint = sub.add_parser("reflective-attention-continuity-review-checkpoint", help="Build the read-only v1123.8 Reflective Attention Continuity Review checkpoint.")
    reflective_attention_continuity_review_checkpoint.add_argument("--json", action="store_true")
    reflective_attention_salience_governance_checkpoint = sub.add_parser("reflective-attention-salience-governance-checkpoint", help="Build the read-only v1123.9 Reflective Attention and Salience Governance checkpoint.")
    reflective_attention_salience_governance_checkpoint.add_argument("--json", action="store_true")
    selected_attention_focus_intake_checkpoint = sub.add_parser("selected-attention-focus-intake-checkpoint", help="Build the read-only v1124.2 Selected Attention and Reflective Focus Intake checkpoint.")
    selected_attention_focus_intake_checkpoint.add_argument("--json", action="store_true")
    reflective_focus_deliberation_checkpoint = sub.add_parser("reflective-focus-deliberation-checkpoint", help="Build the read-only v1124.5 Reflective Focus Deliberation checkpoint.")
    reflective_focus_deliberation_checkpoint.add_argument("--json", action="store_true")
    reflective_focus_continuity_review_checkpoint = sub.add_parser("reflective-focus-continuity-review-checkpoint", help="Build the read-only v1124.8 Reflective Focus Continuity Review checkpoint.")
    reflective_focus_continuity_review_checkpoint.add_argument("--json", action="store_true")
    selected_attention_reflective_focus_governance_checkpoint = sub.add_parser("selected-attention-reflective-focus-governance-checkpoint", help="Build the read-only v1124.9 Selected Attention and Reflective Focus Governance checkpoint.")
    selected_attention_reflective_focus_governance_checkpoint.add_argument("--json", action="store_true")
    reflective_session_intake_checkpoint = sub.add_parser("reflective-session-intake-checkpoint", help="Build the read-only v1125.2 Reflective Session Intake checkpoint.")
    reflective_execution_continuity_checkpoint = sub.add_parser("reflective-execution-continuity-checkpoint", help="Build the read-only v1125.5 Reflective Execution and Continuity checkpoint.")
    reflective_execution_continuity_checkpoint.add_argument("--json", action="store_true")
    reflective_integration_reliability_checkpoint = sub.add_parser("reflective-integration-reliability-checkpoint", help="Build the read-only v1125.8 Reflection Integration and Reliability checkpoint.")
    reflective_integration_reliability_checkpoint.add_argument("--json", action="store_true")
    real_reflective_cognition_checkpoint = sub.add_parser("real-reflective-cognition-checkpoint", help="Build the read-only v1125.9 Real Reflective Cognition checkpoint.")
    real_reflective_cognition_checkpoint.add_argument("--json", action="store_true")
    reflection_quality_intake_checkpoint = sub.add_parser("reflection-quality-intake-checkpoint", help="Build the read-only v1126.2 Reflection Quality Intake checkpoint.")
    reflection_quality_deliberation_checkpoint = sub.add_parser("reflection-quality-deliberation-checkpoint", help="Build the read-only v1126.5 Reflection Quality Deliberation checkpoint.")
    reflection_quality_integration_checkpoint = sub.add_parser("reflection-quality-integration-checkpoint", help="Build the read-only v1126.8 Reflection Quality Integration and Reliability checkpoint.")
    reflection_quality_intake_checkpoint.add_argument("--json", action="store_true")
    reflection_quality_deliberation_checkpoint.add_argument("--json", action="store_true")
    reflection_quality_integration_checkpoint.add_argument("--json", action="store_true")
    reflection_quality_governance_checkpoint = sub.add_parser("reflection-quality-governance-checkpoint", help="Build the read-only v1126.9 Reflection Quality Governance checkpoint.")
    continuous_thought_intake_checkpoint = sub.add_parser("continuous-thought-intake-checkpoint", help="Build the read-only v1127.2 Continuous Thought Intake checkpoint.")
    continuous_thought_deliberation_checkpoint = sub.add_parser("continuous-thought-deliberation-checkpoint", help="Build the read-only v1127.5 Continuous Thought Deliberation checkpoint.")
    continuous_thought_integration_checkpoint = sub.add_parser("continuous-thought-integration-checkpoint", help="Build the read-only v1127.8 Continuous Thought Integration and Reliability checkpoint.")
    continuous_thought_governance_checkpoint = sub.add_parser("continuous-thought-governance-checkpoint", help="Build the read-only v1127.9 Continuous Thought Governance checkpoint.")
    reflection_supported_revision_intake_checkpoint = sub.add_parser("reflection-supported-revision-intake-checkpoint", help="Build the read-only v1128.2 Reflection-Supported Revision Intake checkpoint.")
    reflective_communication_intake_checkpoint = sub.add_parser("reflective-communication-intake-checkpoint", help="Build the read-only v1129.2 Reflective Communication Intake checkpoint.")
    genuine_inquiry_intake_checkpoint = sub.add_parser("genuine-inquiry-intake-checkpoint", help="Build the read-only v1130.2 Genuine Inquiry Intake checkpoint.")
    read_only_perception_intake_checkpoint = sub.add_parser("read-only-perception-intake-checkpoint", help="Build the read-only v1131.2 project and system perception intake checkpoint.")
    read_only_perception_deliberation_checkpoint = sub.add_parser("read-only-perception-deliberation-checkpoint", help="Build the read-only v1131.5 perception deliberation checkpoint.")
    read_only_perception_integration_checkpoint = sub.add_parser("read-only-perception-integration-checkpoint", help="Build the read-only v1131.8 perception integration checkpoint.")
    read_only_perception_governance_checkpoint = sub.add_parser("read-only-perception-governance-checkpoint", help="Build the read-only v1131.9 Read-Only Perception Governance checkpoint.")
    revisable_world_model_intake_checkpoint = sub.add_parser("revisable-world-model-intake-checkpoint", help="Build the read-only v1132.2 Revisable World Model intake checkpoint.")
    internally_generated_goal_intake_checkpoint = sub.add_parser("internally-generated-goal-intake-checkpoint", help="Build the read-only v1133.2 Internally Generated Goal intake checkpoint.")
    prospective_planning_intake_checkpoint = sub.add_parser("prospective-planning-intake-checkpoint", help="Build the read-only v1134.2 Prospective Planning intake checkpoint.")
    supervised_deficiency_intake_checkpoint = sub.add_parser("supervised-deficiency-intake-checkpoint", help="Build the read-only v1135.2 Supervised Deficiency intake checkpoint.")
    supervised_development_proposal_intake_checkpoint = sub.add_parser("supervised-development-proposal-intake-checkpoint", help="Build the read-only v1136.2 Supervised Development Proposal intake checkpoint.")
    supervised_specification_intake_checkpoint = sub.add_parser("supervised-specification-intake-checkpoint", help="Build the read-only v1137.2 Supervised Specification intake checkpoint.")
    supervised_test_plan_intake_checkpoint = sub.add_parser("supervised-test-plan-intake-checkpoint", help="Build the read-only v1138.2 Supervised Test Plan intake checkpoint.")
    supervised_sandbox_change_intake_checkpoint = sub.add_parser("supervised-sandbox-change-intake-checkpoint", help="Build the read-only v1139.2 Supervised Sandbox Change intake checkpoint.")
    supervised_isolated_sandbox_execution_intake_checkpoint = sub.add_parser("supervised-isolated-sandbox-execution-intake-checkpoint", help="Build the read-only v1140.2 Supervised Isolated Sandbox Execution intake checkpoint.")
    supervised_isolated_sandbox_execution_deliberation_checkpoint = sub.add_parser("supervised-isolated-sandbox-execution-deliberation-checkpoint", help="Build the read-only v1140.5 Supervised Isolated Sandbox Execution deliberation checkpoint.")
    supervised_isolated_sandbox_execution_integration_checkpoint = sub.add_parser("supervised-isolated-sandbox-execution-integration-checkpoint", help="Build the read-only v1140.8 Supervised Isolated Sandbox Execution integration checkpoint.")
    supervised_isolated_sandbox_execution_governance_checkpoint = sub.add_parser("supervised-isolated-sandbox-execution-governance-checkpoint", help="Build the read-only v1140.9 Supervised Isolated Sandbox Execution Governance checkpoint.")
    operator_correction_acceptance_intake_checkpoint = sub.add_parser("operator-correction-acceptance-intake-checkpoint", help="Build the read-only v1142.2 Operator Correction and Acceptance Intake checkpoint.")
    operator_correction_acceptance_learning_governance_checkpoint = sub.add_parser("operator-correction-acceptance-learning-governance-checkpoint", help="Build the read-only v1142.9 Operator Correction and Acceptance Learning Governance checkpoint.")
    workload_coordination_intake_checkpoint = sub.add_parser("workload-coordination-intake-checkpoint", help="Build the read-only v1143.2 Workload Coordination Intake checkpoint.")
    workload_coordination_execution_checkpoint = sub.add_parser("workload-coordination-execution-checkpoint", help="Build the read-only v1143.5 Workload Coordination Execution checkpoint.")
    workload_coordination_reliability_checkpoint = sub.add_parser("workload-coordination-reliability-checkpoint", help="Build the read-only v1143.8 Workload Coordination Reliability checkpoint.")
    workload_coordination_governance_checkpoint = sub.add_parser("workload-coordination-governance-checkpoint", help="Build the read-only v1143.9 Workload Coordination Governance checkpoint.")
    multi_day_continuity_soak_intake_checkpoint = sub.add_parser("multi-day-continuity-soak-intake-checkpoint", help="Build the read-only v1144.2 Multi-Day Continuity Soak Intake checkpoint.")
    multi_day_continuity_soak_execution_checkpoint = sub.add_parser("multi-day-continuity-soak-execution-checkpoint", help="Build the read-only v1144.5 Multi-Day Continuity Soak Execution checkpoint.")
    multi_day_continuity_soak_reliability_checkpoint = sub.add_parser("multi-day-continuity-soak-reliability-checkpoint", help="Build the read-only v1144.8 Multi-Day Continuity Soak Reliability checkpoint.")
    multi_day_continuity_soak_governance_checkpoint = sub.add_parser("multi-day-continuity-soak-governance-checkpoint", help="Build the read-only v1144.9 Multi-Day Continuity Soak Governance checkpoint.")
    conversation_cognition_unification_intake_checkpoint = sub.add_parser("conversation-cognition-unification-intake-checkpoint", help="Build the read-only v1145.2 Conversation-Cognition Unification Intake checkpoint.")
    conversation_cognition_unification_execution_checkpoint = sub.add_parser("conversation-cognition-unification-execution-checkpoint", help="Build the read-only v1145.5 Conversation-Cognition Unification Execution checkpoint.")
    conversation_cognition_unification_reliability_checkpoint = sub.add_parser("conversation-cognition-unification-reliability-checkpoint", help="Build the read-only v1145.8 Conversation-Cognition Unification Reliability checkpoint.")
    conversation_cognition_unification_governance_checkpoint = sub.add_parser("conversation-cognition-unification-governance-checkpoint", help="Build the read-only v1145.9 Conversation-Cognition Unification Governance checkpoint.")
    understandable_cognitive_controls_intake_checkpoint = sub.add_parser("understandable-cognitive-controls-intake-checkpoint", help="Build the read-only v1146.2 Understandable Cognitive Controls Intake checkpoint.")
    understandable_cognitive_controls_execution_checkpoint = sub.add_parser("understandable-cognitive-controls-execution-checkpoint", help="Build the read-only v1146.5 Understandable Cognitive Controls Execution checkpoint.")
    understandable_cognitive_controls_reliability_checkpoint = sub.add_parser("understandable-cognitive-controls-reliability-checkpoint", help="Build the read-only v1146.8 Understandable Cognitive Controls Reliability checkpoint.")
    understandable_cognitive_controls_governance_checkpoint = sub.add_parser("understandable-cognitive-controls-governance-checkpoint", help="Build the read-only v1146.9 Understandable Cognitive Controls Governance checkpoint.")
    architecture_consolidation_intake_checkpoint = sub.add_parser("architecture-consolidation-intake-checkpoint", help="Build the read-only v1147.2 Architecture Consolidation intake checkpoint.")
    architecture_consolidation_execution_checkpoint = sub.add_parser("architecture-consolidation-execution-checkpoint", help="Build the read-only v1147.5 Architecture Consolidation execution checkpoint.")
    architecture_consolidation_reliability_checkpoint = sub.add_parser("architecture-consolidation-reliability-checkpoint", help="Build the read-only v1147.8 Architecture Consolidation reliability checkpoint.")
    architecture_consolidation_governance_checkpoint = sub.add_parser("architecture-consolidation-governance-checkpoint", help="Build the read-only v1147.9 Architecture Consolidation Governance checkpoint.")
    privacy_security_hardening_intake_checkpoint = sub.add_parser("privacy-security-hardening-intake-checkpoint", help="Build the read-only v1148.2 Privacy and Security Hardening Intake checkpoint.")
    privacy_security_hardening_execution_checkpoint = sub.add_parser("privacy-security-hardening-execution-checkpoint", help="Build the read-only v1148.5 Privacy and Security Hardening Execution checkpoint.")
    privacy_security_hardening_reliability_checkpoint = sub.add_parser("privacy-security-hardening-reliability-checkpoint", help="Build the read-only v1148.8 Privacy and Security Hardening Reliability checkpoint.")
    privacy_security_hardening_governance_checkpoint = sub.add_parser("privacy-security-hardening-governance-checkpoint", help="Build the read-only v1148.9 Privacy and Security Hardening Governance checkpoint.")
    cognitive_alpha_feature_freeze_intake_checkpoint = sub.add_parser("cognitive-alpha-feature-freeze-intake-checkpoint", help="Build the read-only v1149.2 Cognitive Alpha Feature Freeze Intake checkpoint.")
    cognitive_alpha_feature_freeze_execution_checkpoint = sub.add_parser("cognitive-alpha-feature-freeze-execution-checkpoint", help="Build the read-only v1149.5 Cognitive Alpha Feature Freeze Execution checkpoint.")
    cognitive_alpha_feature_freeze_reliability_checkpoint = sub.add_parser("cognitive-alpha-feature-freeze-reliability-checkpoint", help="Build the read-only v1149.8 Cognitive Alpha Feature Freeze Reliability checkpoint.")
    cognitive_alpha_feature_freeze_governance_checkpoint = sub.add_parser("cognitive-alpha-feature-freeze-governance-checkpoint", help="Build the read-only v1149.9 Cognitive Alpha Feature Freeze Governance checkpoint.")
    reasoning_alpha_checkpoint = sub.add_parser("reasoning-alpha-checkpoint", help="Build the read-only v1150.9 Reasoning Alpha checkpoint.")
    reflection_alpha_checkpoint = sub.add_parser("reflection-alpha-checkpoint", help="Build the read-only v1151.9 Reflection Alpha checkpoint.")
    belief_revision_alpha_checkpoint = sub.add_parser("belief-revision-alpha-checkpoint", help="Build the read-only v1152.9 Belief Revision Alpha checkpoint.")
    multi_step_deliberation_alpha_checkpoint = sub.add_parser("multi-step-deliberation-alpha-checkpoint", help="Build the read-only v1153.9 Multi-Step Deliberation Alpha checkpoint.")
    decision_boundary_alpha_checkpoint = sub.add_parser("decision-boundary-alpha-checkpoint", help="Build the read-only v1154.9 Decision-Boundary Alpha checkpoint.")
    reasoning_alpha_consolidation_checkpoint = sub.add_parser("reasoning-alpha-consolidation-checkpoint", help="Build the read-only v1155.9 Reasoning Alpha Consolidation checkpoint.")
    conversation_intent_selection_checkpoint = sub.add_parser("conversation-intent-selection-checkpoint", help="Build the read-only v1156.9 Conversation Intent Selection checkpoint.")
    contextual_conversation_behavior_checkpoint = sub.add_parser("contextual-conversation-behavior-checkpoint", help="Build the read-only v1157.9 Contextual Conversation Behavior checkpoint.")
    follow_up_silence_checkpoint = sub.add_parser("follow-up-silence-checkpoint", help="Build the read-only v1158.9 Follow-Up and Intentional Silence checkpoint.")
    cognitive_integration_alpha_checkpoint = sub.add_parser("cognitive-integration-alpha-checkpoint", help="Build the read-only v1159.9 Cognitive Integration Alpha checkpoint.")
    conversation_policy_checkpoint = sub.add_parser("conversation-policy-checkpoint", help="Build the read-only v1160.9 Conversation Policy checkpoint.")
    natural_conversation_continuity_checkpoint = sub.add_parser("natural-conversation-continuity-checkpoint", help="Build the read-only v1161.9 Natural Conversation Continuity checkpoint.")
    natural_follow_up_checkpoint = sub.add_parser("natural-follow-up-checkpoint", help="Build the read-only v1162.9 Natural Follow-Up checkpoint.")
    governed_speech_checkpoint = sub.add_parser("governed-speech-checkpoint", help="Build the read-only v1163.9 Governed Proactive Speech checkpoint.")
    daily_companion_cognition_checkpoint = sub.add_parser("daily-companion-cognition-checkpoint", help="Build the read-only v1164.9 Daily Companion Cognition checkpoint.")
    unified_memory_checkpoint = sub.add_parser("unified-memory-checkpoint", help="Build the read-only v1165.9 Unified Memory checkpoint.")
    memory_retrieval_relevance_checkpoint = sub.add_parser("memory-retrieval-relevance-checkpoint", help="Build the read-only v1166.9 Retrieval Relevance checkpoint.")
    immediate_memory_learning_checkpoint = sub.add_parser("immediate-memory-learning-checkpoint", help="Build the read-only v1167.9 Immediate Learning checkpoint.")
    bounded_experiential_lessons_checkpoint = sub.add_parser("bounded-experiential-lessons-checkpoint", help="Build the read-only v1168.9 Bounded Experiential Lessons checkpoint.")
    memory_experiential_learning_alpha_checkpoint = sub.add_parser("memory-experiential-learning-alpha-checkpoint", help="Build the read-only v1169.9 Memory and Experiential Learning Alpha checkpoint.")
    internally_generated_goal_candidate_checkpoint = sub.add_parser("internally-generated-goal-candidate-checkpoint", help="Build the read-only v1170.9 Internally Generated Goal Candidate checkpoint.")
    hierarchical_planning_checkpoint = sub.add_parser("hierarchical-planning-checkpoint", help="Build the read-only v1171.9 Hierarchical Planning checkpoint.")
    plan_simulation_checkpoint = sub.add_parser("plan-simulation-checkpoint", help="Build the read-only v1172.9 Plan Simulation checkpoint.")
    persistent_follow_through_checkpoint = sub.add_parser("persistent-follow-through-checkpoint", help="Build the read-only v1173.9 Persistent Follow-Through checkpoint.")
    goal_and_planning_alpha_checkpoint = sub.add_parser("goal-and-planning-alpha-checkpoint", help="Build the read-only v1174.9 Goal and Planning Alpha checkpoint.")
    natural_language_action_execution_checkpoint = sub.add_parser("natural-language-action-execution-checkpoint", help="Build the read-only v1175.9 Natural-Language Action and Supervised Execution checkpoint.")
    clarification_argument_routing_checkpoint = sub.add_parser("clarification-argument-routing-checkpoint", help="Build the read-only v1176.9 Clarification and Argument Routing checkpoint.")
    natural_language_action_approval_governance_checkpoint = sub.add_parser("natural-language-action-approval-governance-checkpoint", help="Build the read-only v1177.9 Natural-Language Action and Approval Governance checkpoint.")
    natural_language_action_authoritative_result_checkpoint = sub.add_parser("natural-language-action-authoritative-result-checkpoint", help="Build the read-only v1178.9 Natural-Language Action and Authoritative Result checkpoint.")
    natural_language_action_checkpoint = sub.add_parser("natural-language-action-checkpoint", help="Build the read-only v1179.9 Natural-Language Action checkpoint.")
    supervised_project_inspection_planning_checkpoint = sub.add_parser("supervised-project-inspection-planning-checkpoint", help="Build the read-only v1180.9 Supervised Project Inspection and Planning checkpoint.")
    supervised_implementation_checkpoint = sub.add_parser("supervised-implementation-checkpoint", help="Build the read-only v1181.9 Supervised Implementation checkpoint.")
    supervised_sandbox_testing_repair_checkpoint = sub.add_parser("supervised-sandbox-testing-repair-checkpoint", help="Build the read-only v1182.9 Supervised Sandbox Testing and Repair checkpoint.")
    supervised_sandbox_repair_draft_checkpoint = sub.add_parser("supervised-sandbox-repair-draft-checkpoint", help="Build the read-only v1183.2 Supervised Sandbox Repair Draft Foundations checkpoint.")
    supervised_sandbox_repair_materialization_checkpoint = sub.add_parser("supervised-sandbox-repair-materialization-checkpoint", help="Build the read-only v1183.5 Operator Repair Review and Isolated Sandbox Repair Materialization checkpoint.")
    supervised_sandbox_retesting_checkpoint = sub.add_parser("supervised-sandbox-retesting-checkpoint", help="Build the read-only v1183.8 Governed Sandbox Retesting checkpoint.")
    supervised_sandbox_repair_retest_checkpoint = sub.add_parser("supervised-sandbox-repair-retest-checkpoint", help="Build the read-only v1183.9 Supervised Sandbox Repair and Retest checkpoint.")
    supervised_project_development_foundations_checkpoint = sub.add_parser("supervised-project-development-foundations-checkpoint", help="Build the read-only v1184.2 Complete Supervised Project-Development Loop Foundations checkpoint.")
    supervised_project_development_alpha_checkpoint = sub.add_parser("supervised-project-development-alpha-checkpoint", help="Build the read-only v1184.9 Supervised Project Development Alpha checkpoint.")
    persistent_supervised_developer_alpha_checkpoint = sub.add_parser("persistent-supervised-developer-alpha-checkpoint", help="Build the read-only v1185.9 Persistent Supervised Developer Alpha checkpoint.")
    durable_campaign_continuation_checkpoint = sub.add_parser("durable-campaign-continuation-checkpoint", help="Build the read-only v1186.9 Durable Campaign Continuation checkpoint.")
    persistent_campaign_work_execution_checkpoint = sub.add_parser("persistent-campaign-work-execution-checkpoint", help="Build the read-only v1187.9 Persistent Campaign Work Execution checkpoint.")
    persistent_supervised_developer_hardening_checkpoint = sub.add_parser("persistent-supervised-developer-hardening-checkpoint", help="Build the read-only v1189.2 Persistent Supervised Developer hardening checkpoint.")
    persistent_supervised_developer_alpha_hardening_checkpoint = sub.add_parser("persistent-supervised-developer-alpha-hardening-checkpoint", help="Build the read-only v1189.9 Persistent Supervised Developer Alpha Hardening checkpoint.")
    responsive_work_queue_checkpoint = sub.add_parser("responsive-work-queue-checkpoint", help="Build the read-only v1191.2 Responsiveness and Background-Work Foundations checkpoint.")
    responsive_work_queue_review_checkpoint = sub.add_parser("responsive-work-queue-review-checkpoint", help="Build the read-only v1191.5 Operator Queue Review and Accountable Transitions checkpoint.")
    responsive_work_queue_reliability_checkpoint = sub.add_parser("responsive-work-queue-reliability-checkpoint", help="Build the read-only v1191.8 Responsiveness and Background-Work Reliability checkpoint.")
    responsiveness_background_work_checkpoint = sub.add_parser("responsiveness-background-work-checkpoint", help="Build the read-only v1191.9 Responsiveness and Background Work checkpoint.")
    bounded_evidence_compaction_checkpoint = sub.add_parser("bounded-evidence-compaction-checkpoint", help="Build the read-only v1192.2 Bounded Evidence Compaction Foundations checkpoint.")
    evidence_compaction_review_checkpoint = sub.add_parser("evidence-compaction-review-checkpoint", help="Build the read-only v1192.5 Operator Evidence Compaction Review checkpoint.")
    evidence_compaction_reliability_checkpoint = sub.add_parser("evidence-compaction-reliability-checkpoint", help="Build the read-only v1192.8 Evidence Compaction Reliability and Privacy checkpoint.")
    evidence_compaction_checkpoint = sub.add_parser("evidence-compaction-checkpoint", help="Build the read-only v1192.9 Bounded Evidence Compaction checkpoint.")
    verifier_ownership_checkpoint = sub.add_parser("verifier-ownership-checkpoint", help="Build the read-only v1193.2 Verifier Ownership and Historical-Debt Foundations checkpoint.")
    verifier_profile_reconciliation_checkpoint = sub.add_parser("verifier-profile-reconciliation-checkpoint", help="Build the read-only v1193.5 Deterministic Profile and Budget Reconciliation checkpoint.")
    fixture_historical_debt_consolidation_checkpoint = sub.add_parser("fixture-historical-debt-consolidation-checkpoint", help="Build the read-only v1193.8 Fixture and Historical-Debt Consolidation checkpoint.")
    verifier_historical_debt_checkpoint = sub.add_parser("verifier-historical-debt-checkpoint", help="Build the read-only v1193.9 Verifier Ownership and Historical-Debt Consolidation checkpoint.")
    unified_cognitive_developer_checkpoint = sub.add_parser("unified-cognitive-developer-checkpoint", help="Build the read-only v1194.9 Unified Cognitive and Developer Experience checkpoint.")
    general_test_adapter_consolidation_checkpoint = sub.add_parser("general-test-adapter-consolidation-checkpoint", help="Build the read-only v1209.9 General Test Adapter Consolidation checkpoint.")
    conversational_build_test_loop_checkpoint = sub.add_parser("conversational-build-test-loop-checkpoint", help="Build the read-only v1210.9 Conversational Build-and-Test Loop checkpoint.")
    operator_build_test_results_checkpoint = sub.add_parser("operator-build-test-results-checkpoint", help="Build the read-only v1211.9 Operator Build-and-Test Results and Continuation checkpoint.")
    conversational_build_test_continuation_checkpoint = sub.add_parser("conversational-build-test-continuation-checkpoint", help="Build the read-only v1212.9 Conversational Build-and-Test Continuation checkpoint.")
    bounded_automatic_diagnosis_checkpoint = sub.add_parser("bounded-automatic-diagnosis-checkpoint", help="Build the read-only v1213.9 Bounded Automatic Diagnosis checkpoint.")
    operator_diagnosis_review_checkpoint = sub.add_parser("operator-diagnosis-review-checkpoint", help="Build the read-only v1214.9 Operator Diagnosis Review and Repair Proposal checkpoint.")
    conversational_supervised_repair_execution_checkpoint = sub.add_parser("conversational-supervised-repair-execution-checkpoint", help="Build the read-only v1215.9 Conversational Supervised Repair Execution checkpoint.")
    operator_repair_result_review_checkpoint = sub.add_parser("operator-repair-result-review-checkpoint", help="Build the read-only v1216.9 Operator Repair Result Review and Apply Proposal checkpoint.")
    supervised_repaired_candidate_apply_checkpoint = sub.add_parser("supervised-repaired-candidate-apply-checkpoint", help="Build the read-only v1217.9 Conversational Supervised Repaired-Candidate Apply checkpoint.")
    operator_repaired_candidate_apply_result_review_checkpoint = sub.add_parser("operator-repaired-candidate-apply-result-review-checkpoint", help="Build the read-only v1218.9 Operator Repaired-Candidate Apply Result Review and Rollback Proposal checkpoint.")
    supervised_repaired_candidate_rollback_checkpoint = sub.add_parser("supervised-repaired-candidate-rollback-checkpoint", help="Build the read-only v1219.9 Conversational Supervised Repaired-Candidate Rollback checkpoint.")
    operator_repaired_candidate_rollback_result_review_checkpoint = sub.add_parser("operator-repaired-candidate-rollback-result-review-checkpoint", help="Build the read-only v1220.9 Operator Repaired-Candidate Rollback Result Review checkpoint.")
    unified_supervised_development_transaction_history_checkpoint = sub.add_parser("unified-supervised-development-transaction-history-checkpoint", help="Build the read-only v1221.9 Unified Supervised Development Transaction History checkpoint.")
    transaction_resumption_abandoned_work_reconciliation_checkpoint = sub.add_parser("transaction-resumption-abandoned-work-reconciliation-checkpoint", help="Build the read-only v1222.9 Transaction Resumption and Abandoned-Work Reconciliation checkpoint.")
    unified_development_work_queue_checkpoint = sub.add_parser("unified-development-work-queue-checkpoint", help="Build the read-only v1223.9 Unified Work Queue and Project-Level Development State checkpoint.")
    operator_governed_work_prioritization_scheduling_checkpoint = sub.add_parser("operator-governed-work-prioritization-scheduling-checkpoint", help="Build the read-only v1224.9 Operator-Governed Work Prioritization and Scheduling checkpoint.")
    supervised_work_dispatch_execution_session_preparation_checkpoint = sub.add_parser("supervised-work-dispatch-execution-session-preparation-checkpoint", help="Build the read-only v1225.9 Supervised Work Dispatch and Execution-Session Preparation checkpoint.")
    execution_session_authorization_bounded_launch_checkpoint = sub.add_parser("execution-session-authorization-bounded-launch-checkpoint", help="Build the read-only v1226.9 Execution-Session Authorization and Bounded Launch checkpoint.")
    live_execution_monitoring_operator_intervention_checkpoint = sub.add_parser("live-execution-monitoring-operator-intervention-checkpoint", help="Build the read-only v1227.9 Live Execution Monitoring and Operator Intervention checkpoint.")
    execution_session_pause_resume_cancel_recovery_checkpoint = sub.add_parser("execution-session-pause-resume-cancel-recovery-checkpoint", help="Build the read-only v1228.9 Execution Pause, Resume, Cancel, and Recovery checkpoint.")
    execution_outcome_reflection_learning_integration_checkpoint = sub.add_parser("execution-outcome-reflection-learning-integration-checkpoint", help="Build the read-only v1229.9 Execution Outcome Reflection and Learning Integration checkpoint.")
    dynamic_execution_plan_revisions = sub.add_parser("dynamic-execution-plan-revisions", help="List content-free dynamic execution plan revision proposals.")
    dynamic_execution_plan_revisions.add_argument("--runtime-root", default="")
    dynamic_execution_plan_revision_reviews = sub.add_parser("dynamic-execution-plan-revision-reviews", help="List content-free dynamic execution plan revision reviews.")
    dynamic_execution_plan_revision_reviews.add_argument("--runtime-root", default="")
    dynamic_execution_plan_revision_checkpoint = sub.add_parser("dynamic-execution-plan-revision-checkpoint", help="Build the read-only v1231.9 Dynamic Execution Plan Revision checkpoint.")
    dependency_aware_execution_assessments = sub.add_parser("dependency-aware-execution-assessments", help="List content-free dependency-aware execution assessments.")
    dependency_aware_execution_assessments.add_argument("--runtime-root", default="")
    dependency_aware_execution_reviews = sub.add_parser("dependency-aware-execution-reviews", help="List content-free dependency-aware execution reviews.")
    dependency_aware_execution_reviews.add_argument("--runtime-root", default="")
    dependency_aware_execution_checkpoint = sub.add_parser("dependency-aware-execution-checkpoint", help="Build the read-only v1232.9 Dependency-Aware Execution checkpoint.")
    feature_freeze_registry = sub.add_parser("feature-freeze-registry", help="Inspect the read-only v1249 frozen capability registry.")
    feature_freeze_manifest = sub.add_parser("feature-freeze-manifest", help="Inspect the deterministic v1249 public-interface freeze manifest.")
    feature_freeze_final_hardening_report = sub.add_parser("feature-freeze-final-hardening-report", help="Build the read-only v1249 final hardening report.")
    feature_freeze_final_hardening_checkpoint = sub.add_parser("feature-freeze-final-hardening-checkpoint", help="Build the read-only v1249.9 feature-freeze checkpoint.")
    integrated_mind_conversation_development_benchmark_registry = sub.add_parser("integrated-mind-conversation-development-benchmark-registry", help="Inspect the content-free v1248 integrated benchmark registry.")
    integrated_mind_conversation_development_benchmark = sub.add_parser("integrated-mind-conversation-development-benchmark", help="Run the read-only v1248 ordinary-chat integrated benchmark.")
    integrated_mind_conversation_development_benchmark_checkpoint = sub.add_parser("integrated-mind-conversation-development-benchmark-checkpoint", help="Build the read-only v1248.9 integrated benchmark checkpoint.")
    privacy_security_secret_management_registry = sub.add_parser("privacy-security-secret-management-registry", help="Inspect the redacted v1247 privacy/security audit registry.")
    privacy_security_audits = sub.add_parser("privacy-security-audits", help="List redacted v1247 privacy/security audits.")
    privacy_security_audits.add_argument("--runtime-root", default="")
    privacy_security_audit_reviews = sub.add_parser("privacy-security-audit-reviews", help="List redacted v1247 privacy/security audit reviews.")
    privacy_security_audit_reviews.add_argument("--runtime-root", default="")
    secret_management_remediation_proposals = sub.add_parser("secret-management-remediation-proposals", help="List content-free v1247 secret-management remediation proposals.")
    secret_management_remediation_proposals.add_argument("--runtime-root", default="")
    secret_management_remediation_reviews = sub.add_parser("secret-management-remediation-reviews", help="List content-free v1247 secret-management remediation reviews.")
    secret_management_remediation_reviews.add_argument("--runtime-root", default="")
    privacy_security_secret_management_audit_checkpoint = sub.add_parser("privacy-security-secret-management-audit-checkpoint", help="Build the read-only v1247.9 privacy/security audit checkpoint.")
    initiative_proposal_pacing_registry = sub.add_parser("initiative-proposal-pacing-registry", help="Inspect the content-free v1246 initiative pacing registry.")
    initiative_proposal_candidates = sub.add_parser("initiative-proposal-candidates", help="List content-free v1246 initiative proposal candidates.")
    initiative_proposal_candidates.add_argument("--runtime-root", default="")
    initiative_pacing_decisions = sub.add_parser("initiative-pacing-decisions", help="List content-free v1246 initiative pacing decisions.")
    initiative_pacing_decisions.add_argument("--runtime-root", default="")
    initiative_pacing_reviews = sub.add_parser("initiative-pacing-reviews", help="List content-free v1246 initiative pacing reviews.")
    initiative_pacing_reviews.add_argument("--runtime-root", default="")
    initiative_proposal_pacing_checkpoint = sub.add_parser("initiative-proposal-pacing-checkpoint", help="Build the read-only v1246.9 Initiative and Proposal Pacing checkpoint.")
    cross_session_project_understanding_registry = sub.add_parser("cross-session-project-understanding-registry", help="Inspect the content-free v1245 project understanding registry.")
    project_understanding_snapshots = sub.add_parser("project-understanding-snapshots", help="List content-free v1245 project understanding snapshots.")
    project_understanding_snapshots.add_argument("--runtime-root", default="")
    project_understanding_reconciliations = sub.add_parser("project-understanding-reconciliations", help="List content-free v1245 project understanding reconciliations.")
    project_understanding_reconciliations.add_argument("--runtime-root", default="")
    project_understanding_reviews = sub.add_parser("project-understanding-reviews", help="List content-free v1245 project understanding reviews.")
    project_understanding_reviews.add_argument("--runtime-root", default="")
    cross_session_project_understanding_checkpoint = sub.add_parser("cross-session-project-understanding-checkpoint", help="Build the read-only v1245.9 Cross-Session Project Understanding checkpoint.")
    long_running_session_continuity_registry = sub.add_parser("long-running-session-continuity-registry", help="Inspect the content-free v1244 long-running session continuity registry.")
    session_continuity_progress = sub.add_parser("session-continuity-progress", help="List content-free v1244 session progress checkpoints.")
    session_continuity_progress.add_argument("--runtime-root", default="")
    session_continuity_manifests = sub.add_parser("session-continuity-manifests", help="List content-free v1244 continuity manifests.")
    session_continuity_manifests.add_argument("--runtime-root", default="")
    session_continuity_assessments = sub.add_parser("session-continuity-assessments", help="List content-free v1244 continuity assessments.")
    session_continuity_assessments.add_argument("--runtime-root", default="")
    session_continuity_reviews = sub.add_parser("session-continuity-reviews", help="List content-free v1244 continuity reviews.")
    session_continuity_reviews.add_argument("--runtime-root", default="")
    long_running_multi_day_session_continuity_checkpoint = sub.add_parser("long-running-multi-day-session-continuity-checkpoint", help="Build the read-only v1244.9 Long-Running and Multi-Day Session Continuity checkpoint.")
    provider_model_governance_registry = sub.add_parser("provider-model-governance-registry", help="Inspect the content-free v1243 provider/model governance registry.")
    provider_model_registry_snapshots = sub.add_parser("provider-model-registry-snapshots", help="List content-free provider/model registry snapshots.")
    provider_model_registry_snapshots.add_argument("--runtime-root", default="")
    provider_model_selection_proposals = sub.add_parser("provider-model-selection-proposals", help="List content-free provider/model selection proposals.")
    provider_model_selection_proposals.add_argument("--runtime-root", default="")
    provider_model_selection_reviews = sub.add_parser("provider-model-selection-reviews", help="List content-free provider/model selection reviews.")
    provider_model_selection_reviews.add_argument("--runtime-root", default="")
    provider_fallback_assessments = sub.add_parser("provider-fallback-assessments", help="List content-free provider fallback assessments.")
    provider_fallback_assessments.add_argument("--runtime-root", default="")
    provider_fallback_reviews = sub.add_parser("provider-fallback-reviews", help="List content-free provider fallback reviews.")
    provider_fallback_reviews.add_argument("--runtime-root", default="")
    provider_fallback_model_governance_checkpoint = sub.add_parser("provider-fallback-model-governance-checkpoint", help="Build the read-only v1243.9 Provider Fallback and Model Governance checkpoint.")
    installation_lifecycle_registry = sub.add_parser("installation-lifecycle-registry", help="Inspect the content-free v1242 lifecycle operation registry.")
    installation_lifecycle_preflights = sub.add_parser("installation-lifecycle-preflights", help="List content-free installation lifecycle preflights.")
    installation_lifecycle_preflights.add_argument("--runtime-root", default="")
    installation_lifecycle_proposals = sub.add_parser("installation-lifecycle-proposals", help="List content-free installation lifecycle proposals.")
    installation_lifecycle_proposals.add_argument("--runtime-root", default="")
    installation_lifecycle_reviews = sub.add_parser("installation-lifecycle-reviews", help="List content-free installation lifecycle proposal reviews.")
    installation_lifecycle_reviews.add_argument("--runtime-root", default="")
    installation_lifecycle_recovery_assessments = sub.add_parser("installation-lifecycle-recovery-assessments", help="List content-free installation lifecycle recovery assessments.")
    installation_lifecycle_recovery_assessments.add_argument("--runtime-root", default="")
    installation_lifecycle_recovery_reviews = sub.add_parser("installation-lifecycle-recovery-reviews", help="List content-free installation lifecycle recovery reviews.")
    installation_lifecycle_recovery_reviews.add_argument("--runtime-root", default="")
    installation_lifecycle_integration_checkpoint = sub.add_parser("installation-lifecycle-integration-checkpoint", help="Build the read-only v1242.9 lifecycle integration checkpoint.")
    unified_operator_dashboard_registry = sub.add_parser("unified-operator-dashboard-registry", help="Inspect the read-only v1241 dashboard panel registry.")
    unified_operator_dashboard_snapshot = sub.add_parser("unified-operator-dashboard-snapshot", help="Build the v1241 dashboard snapshot.")
    unified_operator_dashboard_checkpoint = sub.add_parser("unified-operator-dashboard-checkpoint", help="Build the read-only v1241.9 dashboard checkpoint.")
    integrated_developer_beta_scenario_registry = sub.add_parser("integrated-developer-beta-scenario-registry", help="Inspect the content-free v1240 Integrated Developer Beta scenario registry.")
    integrated_developer_beta_benchmark = sub.add_parser("integrated-developer-beta-benchmark", help="Build the read-only v1240 Integrated Developer Beta benchmark contract.")
    integrated_developer_beta_checkpoint = sub.add_parser("integrated-developer-beta-checkpoint", help="Build the read-only v1240.9 Integrated Developer Beta checkpoint.")
    adversarial_boundary_attack_registry = sub.add_parser("adversarial-boundary-attack-registry", help="Inspect the content-free v1239 adversarial boundary attack registry.")
    adversarial_boundary_assessments = sub.add_parser("adversarial-boundary-assessments", help="List content-free adversarial boundary assessments.")
    adversarial_boundary_assessments.add_argument("--runtime-root", default="")
    adversarial_boundary_reviews = sub.add_parser("adversarial-boundary-reviews", help="List content-free adversarial boundary reviews.")
    adversarial_boundary_reviews.add_argument("--runtime-root", default="")
    adversarial_execution_cognitive_boundary_checkpoint = sub.add_parser("adversarial-execution-cognitive-boundary-checkpoint", help="Build the read-only v1239.9 Adversarial Execution and Cognitive-Boundary checkpoint.")
    broader_project_language_adapter_registry = sub.add_parser("broader-project-language-adapter-registry", help="Inspect the content-free v1238 broader project and language adapter registry.")
    broader_project_language_adapter_assessments = sub.add_parser("broader-project-language-adapter-assessments", help="List content-free broader project and language adapter assessments.")
    broader_project_language_adapter_assessments.add_argument("--runtime-root", default="")
    broader_project_language_adapter_reviews = sub.add_parser("broader-project-language-adapter-reviews", help="List content-free broader project and language adapter reviews.")
    broader_project_language_adapter_reviews.add_argument("--runtime-root", default="")
    broader_project_language_adapters_checkpoint = sub.add_parser("broader-project-language-adapters-checkpoint", help="Build the read-only v1238.9 Broader Project and Language Adapters checkpoint.")
    multi_tool_orchestration_plans = sub.add_parser("multi-tool-orchestration-plans", help="List content-free multi-tool orchestration plans.")
    multi_tool_orchestration_plans.add_argument("--runtime-root", default="")
    multi_tool_orchestration_reviews = sub.add_parser("multi-tool-orchestration-reviews", help="List content-free multi-tool orchestration plan reviews.")
    multi_tool_orchestration_reviews.add_argument("--runtime-root", default="")
    multi_tool_orchestration_results = sub.add_parser("multi-tool-orchestration-results", help="List content-free external orchestration step results.")
    multi_tool_orchestration_results.add_argument("--runtime-root", default="")
    multi_tool_orchestration_handoffs = sub.add_parser("multi-tool-orchestration-handoffs", help="List content-free orchestration handoff proposals.")
    multi_tool_orchestration_handoffs.add_argument("--runtime-root", default="")
    multi_tool_orchestration_handoff_reviews = sub.add_parser("multi-tool-orchestration-handoff-reviews", help="List content-free orchestration handoff reviews.")
    multi_tool_orchestration_handoff_reviews.add_argument("--runtime-root", default="")
    multi_tool_orchestration_checkpoint = sub.add_parser("multi-tool-orchestration-checkpoint", help="Build the read-only v1237.9 Multi-Tool Orchestration checkpoint.")
    goal_motivation_work_priority_integrations = sub.add_parser("goal-motivation-work-priority-integrations", help="List content-free goal, motivation, and work-priority integration assessments.")
    goal_motivation_work_priority_integrations.add_argument("--runtime-root", default="")
    goal_motivation_work_priority_integration_reviews = sub.add_parser("goal-motivation-work-priority-integration-reviews", help="List content-free goal, motivation, and work-priority integration reviews.")
    goal_motivation_work_priority_integration_reviews.add_argument("--runtime-root", default="")
    goal_motivation_work_priority_integration_checkpoint = sub.add_parser("goal-motivation-work-priority-integration-checkpoint", help="Build the read-only v1236.9 Goal, Motivation, and Work-Priority Integration checkpoint.")
    evidence_backed_development_lessons = sub.add_parser("evidence-backed-development-lessons", help="List content-free evidence-backed development lesson candidates.")
    evidence_backed_development_lessons.add_argument("--runtime-root", default="")
    evidence_backed_development_lesson_reviews = sub.add_parser("evidence-backed-development-lesson-reviews", help="List content-free evidence-backed development lesson reviews.")
    evidence_backed_development_lesson_reviews.add_argument("--runtime-root", default="")
    evidence_backed_development_lesson_reconsiderations = sub.add_parser("evidence-backed-development-lesson-reconsiderations", help="List content-free evidence-backed development lesson reconsiderations.")
    evidence_backed_development_lesson_reconsiderations.add_argument("--runtime-root", default="")
    evidence_backed_development_outcome_lessons_checkpoint = sub.add_parser("evidence-backed-development-outcome-lessons-checkpoint", help="Build the read-only v1235.9 Evidence-Backed Lessons from Development Outcomes checkpoint.")
    requirement_quality_assessments = sub.add_parser("requirement-quality-assessments", help="List content-free requirement and quality assessments.")
    requirement_quality_assessments.add_argument("--runtime-root", default="")
    requirement_quality_assessment_reviews = sub.add_parser("requirement-quality-assessment-reviews", help="List content-free requirement and quality assessment reviews.")
    requirement_quality_assessment_reviews.add_argument("--runtime-root", default="")
    requirement_quality_assessment_checkpoint = sub.add_parser("requirement-quality-assessment-checkpoint", help="Build the read-only v1234.9 Requirement and Quality Assessment checkpoint.")
    resource_concurrency_governance_assessments = sub.add_parser("resource-concurrency-governance-assessments", help="List content-free resource and concurrency governance assessments.")
    resource_concurrency_governance_assessments.add_argument("--runtime-root", default="")
    resource_concurrency_governance_reviews = sub.add_parser("resource-concurrency-governance-reviews", help="List content-free resource and concurrency governance reviews.")
    resource_concurrency_governance_reviews.add_argument("--runtime-root", default="")
    resource_concurrency_governance_checkpoint = sub.add_parser("resource-concurrency-governance-checkpoint", help="Build the read-only v1233.9 Resource and Concurrency Governance checkpoint.")
    mindful_execution_alpha_integration_benchmark_checkpoint = sub.add_parser("mindful-execution-alpha-integration-benchmark-checkpoint", help="Build the read-only v1230.9 Mindful Execution Alpha Integration Benchmark checkpoint.")
    long_session_multi_day_soak_checkpoint = sub.add_parser("long-session-multi-day-soak-checkpoint", help="Build the read-only v1195.2 Long-Session and Multi-Day Soak Foundations checkpoint.")
    operator_reviewed_soak_progression_checkpoint = sub.add_parser("operator-reviewed-soak-progression-checkpoint", help="Build the read-only v1195.5 Operator-Reviewed Soak Progression checkpoint.")
    long_session_multi_day_soak_consolidated_checkpoint = sub.add_parser("long-session-multi-day-soak-consolidated-checkpoint", help="Build the read-only v1195.9 Long-Session and Multi-Day Soak checkpoint.")
    adversarial_privacy_authority_replay_recovery_checkpoint = sub.add_parser("adversarial-privacy-authority-replay-recovery-checkpoint", help="Build the read-only v1196.9 Adversarial Privacy, Authority, Replay, and Recovery checkpoint.")
    runtime_lifecycle_migration_checkpoint = sub.add_parser("runtime-lifecycle-migration-checkpoint", help="Build the read-only v1197.2 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Foundations checkpoint.")
    runtime_lifecycle_application_review_checkpoint = sub.add_parser("runtime-lifecycle-application-review-checkpoint", help="Build the read-only v1197.5 Operator-Reviewed Runtime Lifecycle Application checkpoint.")
    runtime_lifecycle_reliability_adversarial_checkpoint = sub.add_parser("runtime-lifecycle-reliability-adversarial-checkpoint", help="Build the read-only v1197.8 Runtime Lifecycle Reliability and Adversarial Hardening checkpoint.")
    runtime_lifecycle_checkpoint = sub.add_parser("runtime-lifecycle-checkpoint", help="Build the read-only v1197.9 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install checkpoint.")
    feature_freeze_architecture_consolidation_checkpoint = sub.add_parser("feature-freeze-architecture-consolidation-checkpoint", help="Build the read-only v1198.2 Feature Freeze and Architecture Consolidation Foundations checkpoint.")
    feature_freeze_consolidation_review_checkpoint = sub.add_parser("feature-freeze-consolidation-review-checkpoint", help="Build the read-only v1198.5 Operator Freeze Exceptions and Consolidation Review checkpoint.")
    feature_freeze_architecture_consolidated_checkpoint = sub.add_parser("feature-freeze-architecture-consolidated-checkpoint", help="Build the read-only v1198.9 Feature Freeze and Architecture Consolidation checkpoint.")
    final_source_candidate_preparation_checkpoint = sub.add_parser("final-source-candidate-preparation-checkpoint", help="Build the read-only v1199.2 Final Source-Only Candidate Preparation Foundations checkpoint.")
    final_candidate_review_checkpoint = sub.add_parser("final-candidate-review-checkpoint", help="Build the read-only v1199.5 Operator Final-Candidate Review and Handoff Acceptance checkpoint.")
    final_candidate_reliability_checkpoint = sub.add_parser("final-candidate-reliability-checkpoint", help="Build the read-only v1199.8 Final Candidate Reliability and Handoff Hardening checkpoint.")
    final_source_candidate_checkpoint = sub.add_parser("final-source-candidate-checkpoint", help="Build the read-only v1199.9 Final Source-Only Candidate checkpoint.")
    unified_experience_foundations_checkpoint = sub.add_parser("unified-experience-foundations-checkpoint", help="Build the read-only v1190.2 Unified Experience Foundations checkpoint.")
    unified_experience_navigation_checkpoint = sub.add_parser("unified-experience-navigation-checkpoint", help="Build the read-only v1190.5 Operator Navigation and Coordinated Experience checkpoint.")
    unified_experience_reliability_checkpoint = sub.add_parser("unified-experience-reliability-checkpoint", help="Build the read-only v1190.8 Unified Experience Reliability checkpoint.")
    unified_experience_checkpoint = sub.add_parser("unified-experience-checkpoint", help="Build the read-only v1190.9 Unified Experience checkpoint.")
    complete_campaign_development_loop_alpha_checkpoint = sub.add_parser("complete-campaign-development-loop-alpha-checkpoint", help="Build the read-only v1188.9 Complete Campaign Development Loop checkpoint.")
    supervised_sandbox_repair_implementation_governance_checkpoint = sub.add_parser("supervised-sandbox-repair-implementation-governance-checkpoint", help="Build the read-only v1141.9 Supervised Sandbox Repair Implementation Governance checkpoint.")
    supervised_repair_implementation_intake_checkpoint = sub.add_parser("supervised-repair-implementation-intake-checkpoint", help="Build the read-only v1141.2 Supervised Repair Implementation intake checkpoint.")
    supervised_repair_execution_checkpoint = sub.add_parser("supervised-repair-execution-checkpoint", help="Build the read-only v1141.5 Supervised Repair Execution checkpoint.")
    supervised_sandbox_change_deliberation_checkpoint = sub.add_parser("supervised-sandbox-change-deliberation-checkpoint", help="Build the read-only v1139.5 Supervised Sandbox Change deliberation checkpoint.")
    supervised_sandbox_change_integration_checkpoint = sub.add_parser("supervised-sandbox-change-integration-checkpoint", help="Build the read-only v1139.8 Supervised Sandbox Change integration checkpoint.")
    supervised_sandbox_change_governance_checkpoint = sub.add_parser("supervised-sandbox-change-governance-checkpoint", help="Build the read-only v1139.9 Supervised Sandbox Change Governance checkpoint.")
    supervised_test_plan_deliberation_checkpoint = sub.add_parser("supervised-test-plan-deliberation-checkpoint", help="Build the read-only v1138.5 Supervised Test Plan deliberation checkpoint.")
    supervised_test_plan_integration_checkpoint = sub.add_parser("supervised-test-plan-integration-checkpoint", help="Build the read-only v1138.8 Supervised Test Plan integration checkpoint.")
    supervised_test_planning_governance_checkpoint = sub.add_parser("supervised-test-planning-governance-checkpoint", help="Build the read-only v1138.9 Supervised Test Planning Governance checkpoint.")
    supervised_specification_deliberation_checkpoint = sub.add_parser("supervised-specification-deliberation-checkpoint", help="Build the read-only v1137.5 Supervised Specification deliberation checkpoint.")
    supervised_specification_integration_checkpoint = sub.add_parser("supervised-specification-integration-checkpoint", help="Build the read-only v1137.8 Supervised Specification integration checkpoint.")
    supervised_specification_governance_checkpoint = sub.add_parser("supervised-specification-governance-checkpoint", help="Build the read-only v1137.9 Supervised Specification Governance checkpoint.")
    supervised_development_proposal_deliberation_checkpoint = sub.add_parser("supervised-development-proposal-deliberation-checkpoint", help="Build the read-only v1136.5 Supervised Development Proposal deliberation checkpoint.")
    supervised_development_proposal_integration_checkpoint = sub.add_parser("supervised-development-proposal-integration-checkpoint", help="Build the read-only v1136.8 Supervised Development Proposal integration checkpoint.")
    supervised_development_proposal_governance_checkpoint = sub.add_parser("supervised-development-proposal-governance-checkpoint", help="Build the read-only v1136.9 Supervised Development Proposal Governance checkpoint.")
    supervised_deficiency_deliberation_checkpoint = sub.add_parser("supervised-deficiency-deliberation-checkpoint", help="Build the read-only v1135.5 Supervised Deficiency deliberation checkpoint.")
    supervised_deficiency_integration_checkpoint = sub.add_parser("supervised-deficiency-integration-checkpoint", help="Build the read-only v1135.8 Supervised Deficiency integration checkpoint.")
    supervised_deficiency_governance_checkpoint = sub.add_parser("supervised-deficiency-governance-checkpoint", help="Build the read-only v1135.9 Supervised Deficiency Identification Governance checkpoint.")
    prospective_planning_deliberation_checkpoint = sub.add_parser("prospective-planning-deliberation-checkpoint", help="Build the read-only v1134.5 Prospective Planning deliberation checkpoint.")
    prospective_planning_integration_checkpoint = sub.add_parser("prospective-planning-integration-checkpoint", help="Build the read-only v1134.8 Prospective Planning integration checkpoint.")
    prospective_planning_governance_checkpoint = sub.add_parser("prospective-planning-governance-checkpoint", help="Build the read-only v1134.9 Prospective Planning Governance checkpoint.")
    internally_generated_goal_deliberation_checkpoint = sub.add_parser("internally-generated-goal-deliberation-checkpoint", help="Build the read-only v1133.5 Internally Generated Goal deliberation checkpoint.")
    internally_generated_goal_integration_checkpoint = sub.add_parser("internally-generated-goal-integration-checkpoint", help="Build the read-only v1133.8 Internally Generated Goal integration checkpoint.")
    internally_generated_goal_governance_checkpoint = sub.add_parser("internally-generated-goal-governance-checkpoint", help="Build the read-only v1133.9 Internally Generated Goal Governance checkpoint.")
    revisable_world_model_deliberation_checkpoint = sub.add_parser("revisable-world-model-deliberation-checkpoint", help="Build the read-only v1132.5 Revisable World Model deliberation checkpoint.")
    revisable_world_model_integration_checkpoint = sub.add_parser("revisable-world-model-integration-checkpoint", help="Build the read-only v1132.8 Revisable World Model integration checkpoint.")
    revisable_world_model_governance_checkpoint = sub.add_parser("revisable-world-model-governance-checkpoint", help="Build the read-only v1132.9 Revisable World Model Governance checkpoint.")
    genuine_inquiry_deliberation_checkpoint = sub.add_parser("genuine-inquiry-deliberation-checkpoint", help="Build the read-only v1130.5 Genuine Inquiry Deliberation checkpoint.")
    genuine_inquiry_integration_checkpoint = sub.add_parser("genuine-inquiry-integration-checkpoint", help="Build the read-only v1130.8 Genuine Inquiry Integration checkpoint.")
    genuine_inquiry_governance_checkpoint = sub.add_parser("genuine-inquiry-governance-checkpoint", help="Build the read-only v1130.9 Genuine Inquiry Governance checkpoint.")
    reflective_communication_deliberation_checkpoint = sub.add_parser("reflective-communication-deliberation-checkpoint", help="Build the read-only v1129.5 Reflective Communication Deliberation checkpoint.")
    reflective_communication_integration_checkpoint = sub.add_parser("reflective-communication-integration-checkpoint", help="Build the read-only v1129.8 Reflective Communication Integration checkpoint.")
    reflective_communication_governance_checkpoint = sub.add_parser("reflective-communication-governance-checkpoint", help="Build the read-only v1129.9 Real Reflective Communication Governance checkpoint.")
    reflection_supported_revision_deliberation_checkpoint = sub.add_parser("reflection-supported-revision-deliberation-checkpoint", help="Build the read-only v1128.5 Reflection-Supported Revision Deliberation checkpoint.")
    reflection_supported_revision_integration_checkpoint = sub.add_parser("reflection-supported-revision-integration-checkpoint", help="Build the read-only v1128.8 Reflection-Supported Revision Integration checkpoint.")
    reflection_supported_revision_governance_checkpoint = sub.add_parser("reflection-supported-revision-governance-checkpoint", help="Build the read-only v1128.9 Reflection-Supported Revision Governance checkpoint.")
    reflection_supported_revision_integration_checkpoint.add_argument("--json", action="store_true")
    reflection_quality_governance_checkpoint.add_argument("--json", action="store_true")
    reflective_session_intake_checkpoint.add_argument("--json", action="store_true")
    objective_coherence_intake_checkpoint = sub.add_parser("objective-coherence-intake-checkpoint", help="Build the read-only v1121.2 Goal Coherence Intake checkpoint.")
    objective_coherence_intake_checkpoint.add_argument("--json", action="store_true")
    objective_coherence_deliberation_checkpoint = sub.add_parser("objective-coherence-deliberation-checkpoint", help="Build the read-only v1121.5 Goal Coherence Deliberation checkpoint.")
    objective_coherence_deliberation_checkpoint.add_argument("--json", action="store_true")
    goal_continuity_review_checkpoint = sub.add_parser("goal-continuity-review-checkpoint", help="Build the read-only v1121.8 Goal Continuity Review checkpoint.")
    goal_continuity_review_checkpoint.add_argument("--json", action="store_true")
    goal_coherence_long_horizon_objective_governance_checkpoint = sub.add_parser("goal-coherence-long-horizon-objective-governance-checkpoint", help="Build the read-only v1121.9 Goal Coherence and Long-Horizon Objective Governance checkpoint.")
    goal_coherence_long_horizon_objective_governance_checkpoint.add_argument("--json", action="store_true")
    self_model_integrity_intake_checkpoint = sub.add_parser("self-model-integrity-intake-checkpoint", help="Build the read-only v1120.2 Self-Model Integrity Intake checkpoint.")
    self_model_integrity_intake_checkpoint.add_argument("--json", action="store_true")
    self_model_revision_deliberation_checkpoint = sub.add_parser("self-model-revision-deliberation-checkpoint", help="Build the read-only v1120.5 Self-Model Revision Deliberation checkpoint.")
    self_model_revision_deliberation_checkpoint.add_argument("--json", action="store_true")

    self_model_continuity_review_checkpoint = sub.add_parser("self-model-continuity-review-checkpoint", help="Build the read-only v1120.8 Self-Model Continuity Review checkpoint.")
    self_model_continuity_review_checkpoint.add_argument("--json", action="store_true")
    self_model_integrity_identity_claim_governance_checkpoint = sub.add_parser("self-model-integrity-identity-claim-governance-checkpoint", help="Build the read-only v1120.9 Self-Model Integrity and Identity Claim Governance checkpoint.")
    self_model_integrity_identity_claim_governance_checkpoint.add_argument("--json", action="store_true")
    prospective_memory_continuity_checkpoint.add_argument("--json", action="store_true")
    cognitive_homeostasis_continuity_checkpoint = sub.add_parser("cognitive-homeostasis-continuity-checkpoint", help="Build the read-only v1116.2 Cognitive Homeostasis Continuity checkpoint.")
    cognitive_homeostasis_continuity_checkpoint.add_argument("--json", action="store_true")
    cognitive_recovery_continuity_checkpoint = sub.add_parser("cognitive-recovery-continuity-checkpoint", help="Build the read-only v1116.5 Cognitive Recovery Continuity checkpoint.")
    cognitive_recovery_continuity_checkpoint.add_argument("--json", action="store_true")
    cognitive_sustainability_review_checkpoint = sub.add_parser("cognitive-sustainability-review-checkpoint", help="Build the read-only v1116.8 Cognitive Sustainability Review checkpoint.")
    cognitive_sustainability_review_checkpoint.add_argument("--json", action="store_true")
    cognitive_homeostasis_sustainable_cognition_checkpoint = sub.add_parser("cognitive-homeostasis-sustainable-cognition-checkpoint", help="Build the read-only v1116.9 Cognitive Homeostasis and Sustainable Cognition checkpoint.")
    cognitive_homeostasis_sustainable_cognition_checkpoint.add_argument("--json", action="store_true")
    cognitive_work_continuity_checkpoint.add_argument("--json", action="store_true")
    cognitive_load_continuity_checkpoint.add_argument("--json", action="store_true")
    reflective_planning_deliberative_choice_checkpoint.add_argument("--json", action="store_true")

    persistent_identity_model = sub.add_parser("persistent-identity-model", help="Inspect v1110.0 evidence-backed persistent identity claims.")
    persistent_identity_model.add_argument("--json", action="store_true")

    identity_evidence_arbitration = sub.add_parser("identity-evidence-arbitration", help="Inspect v1110.1 deterministic identity evidence arbitration.")
    identity_evidence_arbitration.add_argument("--json", action="store_true")

    self_model_continuity_checkpoint = sub.add_parser("self-model-continuity-checkpoint", help="Build the read-only v1110.2 self-model continuity checkpoint.")
    self_model_continuity_checkpoint.add_argument("--json", action="store_true")

    identity_change_detection = sub.add_parser("identity-change-detection", help="Inspect v1110.3 identity contradiction and durable-change detection.")
    identity_change_detection.add_argument("--json", action="store_true")

    self_model_revision = sub.add_parser("self-model-revision", help="Inspect v1110.4 bounded self-model revision outcomes.")
    self_model_revision.add_argument("--json", action="store_true")

    identity_revision_checkpoint = sub.add_parser("identity-revision-checkpoint", help="Build the read-only v1110.5 identity-revision checkpoint.")
    identity_expression_lifecycle_checkpoint = sub.add_parser("identity-expression-lifecycle-checkpoint", help="Build the read-only v1110.8 identity-expression lifecycle checkpoint.")
    identity_expression_lifecycle_checkpoint.add_argument("--json", action="store_true")

    persistent_self_model_checkpoint = sub.add_parser("persistent-self-model-checkpoint", help="Build the read-only v1110.9 Persistent Self-Model checkpoint.")
    persistent_self_model_checkpoint.add_argument("--json", action="store_true")
    identity_revision_checkpoint.add_argument("--json", action="store_true")

    native_reflection = sub.add_parser("native-reflection-evaluation", help="Run explicit bounded synthetic reflection-quality checks through the configured provider.")
    native_reflection.add_argument("--event-id", default="operator-native-reflection-evaluation")
    native_reflection.add_argument("--confirm-native", action="store_true", help="Explicitly authorize the bounded native requests.")
    native_reflection.add_argument("--max-cases", type=int, default=3)
    native_reflection.add_argument("--max-total-ms", type=int, default=30000)
    native_reflection.add_argument("--json", action="store_true")

    proactive_inbox = sub.add_parser("proactive-inbox", help="Inspect queued and unread proactive messages without delivering them.")
    proactive_inbox.add_argument("--json", action="store_true")

    communication_control = sub.add_parser("communication-control", help="Adjust bounded conversational initiative without erasing internal continuity.")
    communication_control.add_argument("--event-id", default="operator-communication-control")
    communication_control.add_argument("--frequency", choices=("minimal", "low", "normal", "high"))
    communication_control.add_argument("--quiet", action="store_true")
    communication_control.add_argument("--allow", action="store_true")
    communication_control.add_argument("--disable", action="store_true")
    communication_control.add_argument("--enable", action="store_true")
    communication_control.add_argument("--json", action="store_true")

    startup_soak = sub.add_parser("startup-soak", help="Run bounded repeated startup evidence for Windows review.")
    startup_soak.add_argument("--runs", type=int, default=5)
    startup_soak.add_argument("--timeout", type=float, default=45.0)
    startup_soak.add_argument("--include-provider-probe", action="store_true")
    startup_soak.add_argument("--json", action="store_true")

    messaging_soak = sub.add_parser("messaging-soak", help="Run a bounded content-free long-session messaging soak without contacting the provider.")
    messaging_soak.add_argument("--iterations", type=int, default=60)
    messaging_soak.add_argument("--json", action="store_true")

    migrate = sub.add_parser("upgrade-migrate", help="Inspect retired sandbox evidence, or quarantine it only with explicit --apply opt-in.")
    migrate.add_argument("--apply", action="store_true", help="Explicitly opt in to moving validated stale/partial evidence into reversible quarantine.")
    migrate.add_argument("--json", action="store_true")

    verify = sub.add_parser("verify", help="Verify source integrity and runtime readiness.")
    verify.add_argument("--full", action="store_true", help="Run the active authoritative release profile: readiness, release, install-release, and recent install regression.")
    verify.add_argument("--verbose", action="store_true")
    verify.add_argument("--json", action="store_true")

    legacy = sub.add_parser("legacy", help="Pass remaining arguments directly to conscious_agent/main.py.")
    legacy.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    command = args.command or "start"
    if command not in {"runtime-guide", "runtime-migrate", "cognitive-contract-review", "checkpoint-registry", "checkpoint-run", "reasoning-alpha-checkpoint", "reflection-alpha-checkpoint", "belief-revision-alpha-checkpoint", "multi-step-deliberation-alpha-checkpoint", "decision-boundary-alpha-checkpoint", "reasoning-alpha-consolidation-checkpoint", "conversation-intent-selection-checkpoint", "contextual-conversation-behavior-checkpoint", "follow-up-silence-checkpoint", "cognitive-integration-alpha-checkpoint", "conversation-policy-checkpoint", "natural-conversation-continuity-checkpoint", "natural-follow-up-checkpoint", "governed-speech-checkpoint", "daily-companion-cognition-checkpoint", "unified-memory-checkpoint", "memory-retrieval-relevance-checkpoint", "immediate-memory-learning-checkpoint", "bounded-experiential-lessons-checkpoint", "memory-experiential-learning-alpha-checkpoint", "internally-generated-goal-candidate-checkpoint", "hierarchical-planning-checkpoint", "plan-simulation-checkpoint", "persistent-follow-through-checkpoint", "goal-and-planning-alpha-checkpoint", "natural-language-action-execution-checkpoint", "clarification-argument-routing-checkpoint", "natural-language-action-approval-governance-checkpoint", "natural-language-action-authoritative-result-checkpoint", "natural-language-action-checkpoint", "supervised-project-inspection-planning-checkpoint", "supervised-implementation-checkpoint", "supervised-sandbox-testing-repair-checkpoint", "supervised-sandbox-repair-draft-checkpoint", "supervised-sandbox-repair-materialization-checkpoint", "supervised-sandbox-retesting-checkpoint", "supervised-sandbox-repair-retest-checkpoint", "supervised-project-development-foundations-checkpoint", "supervised-project-development-alpha-checkpoint", "persistent-supervised-developer-alpha-checkpoint", "durable-campaign-continuation-checkpoint", "persistent-campaign-work-execution-checkpoint", "complete-campaign-development-loop-alpha-checkpoint", "persistent-supervised-developer-hardening-checkpoint", "persistent-supervised-developer-alpha-hardening-checkpoint", "unified-experience-foundations-checkpoint", "unified-experience-navigation-checkpoint", "unified-experience-reliability-checkpoint", "unified-experience-checkpoint", "verify", "startup-soak", "messaging-soak"}:
        from conscious_agent.launch_environment import prepare_ordinary_launch_environment
        launch_environment = prepare_ordinary_launch_environment(ROOT)
        if launch_environment.get("migration_blocking"):
            print("Eidolon startup blocked: runtime-data migration requires review. Run `python eidolon.py runtime-guide --show-paths`.", file=sys.stderr)
            return 2
        if not launch_environment.get("runtime_external"):
            print("Warning: EIDOLON_DATA_DIR points inside the source tree. Review `python eidolon.py runtime-guide --show-paths`.", file=sys.stderr)
    if command == "status":
        return _run(MAIN, "--status")
    if command == "onboarding":
        return _run(MAIN, "--onboarding")
    if command == "chat":
        # Keep terminal chat in this launcher process. Spawning a second Python
        # interpreter made cold first-use latency depend on host-wide startup
        # hooks and duplicated interpreter initialization before any message.
        chat_launcher_path = ROOT / "conscious_agent" / "chat_launcher.py"
        agent_root = chat_launcher_path.parent
        if str(agent_root) not in sys.path:
            sys.path.insert(0, str(agent_root))
        from chat_launcher import main as chat_main
        return int(chat_main())
    if command == "start":
        host = str(getattr(args, "host", "127.0.0.1"))
        port = int(getattr(args, "port", 8765))
        no_browser = bool(getattr(args, "no_browser", False))
        forwarded = ["--dashboard", "--dashboard-host", host, "--dashboard-port", str(port)]
        if no_browser:
            forwarded.append("--no-browser")
        else:
            forwarded.append("--open-browser")
        from conscious_agent.dashboard_launcher import launch_dashboard_from_argv
        return launch_dashboard_from_argv(forwarded)
    if command == "model-status":
        forwarded = ["--model-status"]
        if args.json:
            forwarded.append("--model-status-json")
        return _run(MAIN, *forwarded)
    if command == "model-readiness":
        forwarded = ["--model-readiness"]
        if args.json:
            forwarded.append("--model-readiness-json")
        return _run(MAIN, *forwarded)
    if command == "model-smoke":
        forwarded = ["--model-native-smoke", "--model-smoke-timeout", str(args.timeout)]
        if args.confirm_native:
            forwarded.append("--confirm-native-model-smoke")
        if args.readiness_digest:
            forwarded.extend(["--model-smoke-readiness-digest", args.readiness_digest])
        if args.json:
            forwarded.append("--model-smoke-json")
        return _run(MAIN, *forwarded)
    if command == "conversation-validation":
        forwarded = [
            "--native-conversation-validation",
            "--native-conversation-timeout", str(args.timeout),
            "--native-conversation-first-token-budget-ms", str(args.first_token_budget_ms),
            "--native-conversation-total-budget-ms", str(args.total_budget_ms),
        ]
        if args.confirm_native:
            forwarded.append("--confirm-native-conversation-validation")
        if args.validation_id:
            forwarded.extend(["--native-conversation-validation-id", args.validation_id])
        if args.json:
            forwarded.append("--native-conversation-json")
        return _run(MAIN, *forwarded)
    if command == "doctor":
        forwarded = ["--doctor"]
        if args.full:
            forwarded.append("--doctor-full")
        return _run(MAIN, *forwarded)
    if command == "stable-preview":
        return _run(MAIN, "--stable-loop-preflight", "--no-ai-stable-loop")
    if command == "dashboard":
        forwarded = ["--dashboard", "--dashboard-host", args.host, "--dashboard-port", str(args.port)]
        if args.open_browser:
            forwarded.append("--open-browser")
        from conscious_agent.dashboard_launcher import launch_dashboard_from_argv
        return launch_dashboard_from_argv(forwarded)
    if command == "runtime-migrate":
        from conscious_agent.runtime_data_migration import migrate_runtime_data, preview_runtime_data_migration
        if args.confirm_copy:
            payload = migrate_runtime_data(
                args.legacy_runtime_root,
                args.external_runtime_root,
                operator_confirmed=True,
                include_paths=args.show_paths,
            )
        else:
            payload = preview_runtime_data_migration(
                args.legacy_runtime_root,
                args.external_runtime_root,
                include_paths=args.show_paths,
            )
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 2
    if command == "cognitive-contract-review":
        from conscious_agent.cognitive_contract_review import build_cognitive_contract_review
        payload = build_cognitive_contract_review(ROOT)
        print(json.dumps(payload, indent=2))
        return 0
    if command == "checkpoint-registry":
        from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
        payload = inspect_checkpoint_registry(source_root=ROOT)
        print(json.dumps(payload, indent=2))
        return 0 if not payload.get("duplicate_checkpoint_ids") else 2
    if command == "checkpoint-run":
        from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
        payload = dispatch_registered_checkpoint(
            args.checkpoint_id,
            source_root=ROOT,
            runtime_root=args.runtime_root or None,
        )
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("read_only") else 2
    if command == "runtime-guide":
        from conscious_agent.launch_environment import build_runtime_migration_guidance
        payload = build_runtime_migration_guidance(ROOT, include_paths=args.show_paths)
        if args.json or args.show_paths:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["headline"])
            print(payload["summary"])
            print("Inspect redacted details: python eidolon.py runtime-guide --json")
            print("Inspect local paths: python eidolon.py runtime-guide --show-paths")
        return 0
    if command == "first-use-checkpoint":
        from conscious_agent.first_use_runtime import build_first_use_bootstrap
        payload = build_first_use_bootstrap(launch_mode="checkpoint").get("checkpoint") or {}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "First-use checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print(f"Current defects: {payload.get('current_product_defect_count', 0)}")
            print(f"Pending evidence: {payload.get('pending_evidence_count', 0)}")
            print("Detailed content-free report: python eidolon.py first-use-checkpoint --json")
        return 0 if payload.get("ok") else 1
    if command == "natural-conversation-checkpoint":
        from conscious_agent.natural_conversation_checkpoint import build_natural_conversation_checkpoint
        payload = build_natural_conversation_checkpoint()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "Natural-conversation checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print(f"Current defects: {payload.get('current_product_defect_count', 0)}")
            print(f"Pending evidence: {payload.get('pending_evidence_count', 0)}")
            print("Detailed content-free report: python eidolon.py natural-conversation-checkpoint --json")
        return 0 if payload.get("ok") else 1
    if command == "messaging-reliability-checkpoint":
        from conscious_agent.messaging_reliability_checkpoint import build_messaging_reliability_checkpoint
        payload = build_messaging_reliability_checkpoint()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "Messaging-reliability checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print(f"Current defects: {payload.get('current_product_defect_count', 0)}")
            print(f"Pending evidence: {payload.get('pending_evidence_count', 0)}")
            print("Detailed content-free report: python eidolon.py messaging-reliability-checkpoint --json")
        return 0 if payload.get("ok") else 1
    if command == "action-intent":
        from conscious_agent.conversational_action_portal_v1104 import classify_conversation_action
        payload = classify_conversation_action(args.text)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Classification: {payload.get('classification', 'unknown')}")
            print(f"Confidence: {payload.get('confidence', 0)}")
            print("No request was saved or executed.")
        return 0
    if command == "action-catalog":
        from conscious_agent.conversational_action_portal_v1104 import build_operator_tool_catalog
        payload = build_operator_tool_catalog()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Bounded conversational tools: {payload.get('tool_count', 0)}")
            for row in payload.get("tools") or []:
                print(f"- {row.get('label')}: {row.get('boundary')}")
        return 0
    if command == "action-preview":
        from conscious_agent.conversational_action_portal_v1104 import build_action_proposal_card
        payload = build_action_proposal_card(args.text)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("title") or "Action preview")
            print(payload.get("summary") or "")
            print(f"Decision: {payload.get('operator_decision', 'review')}")
            print("Preview only. Nothing was saved, executed, or authorized.")
        return 0
    if command == "developer-alpha":
        from conscious_agent.developer_alpha_runtime import (
            create_development_proposal,
            developer_alpha_status,
            execute_development_proposal,
        )
        if args.action == "propose":
            payload = create_development_proposal(args.request, workspace_name=args.workspace_name, persist=True)
        elif args.action == "execute":
            payload = execute_development_proposal(args.proposal_id, operator_approved=bool(args.approve))
        else:
            payload = developer_alpha_status()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Status: {payload.get('status', 'ready')}")
            if payload.get("proposal_id"):
                print(f"Proposal: {payload['proposal_id']}")
            if payload.get("workspace"):
                print(f"Workspace: {payload['workspace']}")
            if args.action == "propose" and payload.get("status") == "ready_for_operator_review":
                print(f"Approve once: python eidolon.py developer-alpha execute --proposal-id {payload['proposal_id']} --approve")
        return 0 if payload.get("ok", payload.get("status") == "ready_for_operator_review") else 2
    if command == "cognition-status":
        from conscious_agent.proactive_communication import build_cognition_inspection
        payload = build_cognition_inspection()
        payload["consciousness_claimed"] = False
        payload["operator_authority_unchanged"] = True
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Active motivations: {payload['motivation']['active_motivation_count']}")
            print(f"Cognitive cycle: {payload['cycle']['status']}")
            print(f"Last cycle: {payload['cycle']['last_cycle']['status']}")
            print("Internal state cannot authorize or execute protected actions.")
        return 0
    if command == "cognition-cycle":
        from conscious_agent.endogenous_cognitive_cycle import EndogenousCognitiveCycle
        provider_available = True if args.provider_state == "ready" else (False if args.provider_state == "unavailable" else None)
        payload = EndogenousCognitiveCycle().run_cycle(
            args.event_id,
            trigger_type=args.trigger,
            perceived_events=[{"event_type": args.trigger, "event_ref": args.event_id}],
            provider_available=provider_available,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Cycle status: {payload.get('status', 'unknown')}")
            receipt = payload.get("receipt") or {}
            print(f"Communication decision: {receipt.get('communication_decision', 'silence')}")
            print("No protected action was authorized or executed.")
        return 0
    if command == "cognition-control":
        from conscious_agent.endogenous_cognitive_cycle import EndogenousCognitiveCycle
        payload = EndogenousCognitiveCycle().set_control(
            args.event_id,
            action=args.action,
            cadence_seconds=args.cadence_seconds,
            max_cycles_per_hour=args.max_cycles_per_hour,
            max_cycles_per_day=args.max_cycles_per_day,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            result = payload.get("result") or {}
            print(f"Cognitive cycle mode: {result.get('mode', 'unknown')}")
            print("Continuity was preserved; action authority was unchanged.")
        return 0
    if command == "cognition-initiative":
        from conscious_agent.proactive_communication import CognitiveInitiativeService
        provider_available = True if args.provider_state == "ready" else (False if args.provider_state == "unavailable" else None)
        event = {"event_type": args.trigger, "event_ref": args.event_id}
        if args.motivation_id:
            event["motivation_id"] = args.motivation_id
        payload = CognitiveInitiativeService().process_event(
            args.event_id,
            trigger_type=args.trigger,
            perceived_events=[event],
            provider_available=provider_available,
            tone=args.tone,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            communication = payload.get("communication") or {}
            print(f"Cognitive event: {payload.get('status', 'unknown')}")
            print(f"Communication decision: {communication.get('decision', 'silence')}")
            print(communication.get("reason") or "No protected action was authorized or executed.")
        return 0
    if command == "inquiry-status":
        from conscious_agent.self_directed_inquiry import build_inquiry_inspection
        payload = build_inquiry_inspection()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Active inquiries: {payload.get('active_inquiry_count', 0)}")
            print(f"Paused inquiries: {payload.get('paused_inquiry_count', 0)}")
            print("Inquiry remains provider-free, browse-free, and action-inert.")
        return 0
    if command == "inquiry-create":
        from conscious_agent.self_directed_inquiry import InquiryWorkspace
        try:
            payload = InquiryWorkspace().create_inquiry(
                args.event_id, motivation_id=args.motivation_id, question=args.question, uncertainty=args.uncertainty,
                sources_sought=args.source_sought, stop_conditions=args.stop_condition, project_id=args.project_id,
            )
        except (ValueError, KeyError) as error:
            if args.json:
                print(json.dumps({"ok": False, "error": str(error)}, indent=2))
            else:
                print(str(error), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Inquiry: {(payload.get('result') or {}).get('inquiry_id', 'not created')}")
            print("No external browsing, provider request, or action authorization occurred.")
        return 0
    if command == "inquiry-attention":
        from conscious_agent.inquiry_attention_routing import InquiryAttentionRouter
        payload = InquiryAttentionRouter().activate(args.event_id)
        print(json.dumps(payload, indent=2) if args.json else f"Inquiry attention: {payload.get('status')}")
        return 0
    if command == "inquiry-evidence":
        from conscious_agent.inquiry_evidence_assimilation import build_inquiry_evidence_inspection
        payload = build_inquiry_evidence_inspection()
        print(json.dumps(payload, indent=2) if args.json else f"Active evidence: {payload.get('active_evidence_count', 0)}; research proposals: {payload.get('research_proposal_count', 0)}")
        return 0
    if command == "inquiry-communication":
        from conscious_agent.inquiry_conversation_continuity import InquiryConversationBridge
        try:
            payload = InquiryConversationBridge().consider(args.event_id, inquiry_id=args.inquiry_id, tone=args.tone)
        except (ValueError, KeyError) as error:
            print(json.dumps({"ok": False, "error": str(error)}, indent=2) if args.json else str(error), file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2) if args.json else f"Inquiry communication: {(payload.get('result') or {}).get('decision', 'silence')}")
        return 0
    if command == "inquiry-quality":
        from conscious_agent.inquiry_evidence_quality import InquiryEvidenceQuality
        try: payload=InquiryEvidenceQuality().assess(args.event_id,inquiry_id=args.inquiry_id)
        except (ValueError,KeyError) as error:
            print(json.dumps({"ok":False,"error":str(error)},indent=2) if args.json else str(error),file=sys.stderr);return 1
        print(json.dumps(payload,indent=2) if args.json else f"Inquiry quality: {payload.get('status')}");return 0
    if command == "inquiry-reflect":
        from conscious_agent.inquiry_reflection import InquiryReflection
        try: payload=InquiryReflection().reflect(args.event_id,inquiry_id=args.inquiry_id)
        except (ValueError,KeyError) as error:
            print(json.dumps({"ok":False,"error":str(error)},indent=2) if args.json else str(error),file=sys.stderr);return 1
        print(json.dumps(payload,indent=2) if args.json else f"Inquiry reflection: {payload.get('status')}");return 0
    if command == "inquiry-resolve":
        from conscious_agent.inquiry_resolution import InquiryResolution
        try: payload=InquiryResolution().resolve(args.event_id,inquiry_id=args.inquiry_id,proposition=args.proposition,residual_question=args.residual_question)
        except (ValueError,KeyError) as error:
            print(json.dumps({"ok":False,"error":str(error)},indent=2) if args.json else str(error),file=sys.stderr);return 1
        print(json.dumps(payload,indent=2) if args.json else f"Inquiry resolution: {payload.get('status')}");return 0
    if command == "planning-status":
        from conscious_agent.prospective_planning import build_prospective_planning_inspection
        payload = build_prospective_planning_inspection()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Active prospective plans: {payload.get('active_plan_count', 0)}")
            print(f"Internal proposals: {payload.get('proposal_count', 0)}")
            print("Plans and proposals remain provider-free and unauthorized.")
        return 0
    if command == "planning-compare":
        from conscious_agent.prospective_planning import ProspectivePlanningStore
        try:
            payload = ProspectivePlanningStore().compare_plan(args.event_id, plan_id=args.plan_id)
        except (ValueError, KeyError) as error:
            if args.json:
                print(json.dumps({"ok": False, "error": str(error)}, indent=2))
            else:
                print(str(error), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Recommended alternative: {(payload.get('result') or {}).get('recommended_alternative_id', 'none')}")
            print("The recommendation is not approval or execution authority.")
        return 0
    if command == "internal-life-checkpoint":
        from conscious_agent.persistent_internal_life_checkpoint import build_persistent_internal_life_checkpoint
        payload = build_persistent_internal_life_checkpoint()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "Persistent internal-life checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print("This is verification evidence, not a consciousness claim, release promotion, or certification.")
        return 0 if payload.get("ok") else 1
    if command == "cognitive-development-checkpoint":
        from conscious_agent.cognitive_development_checkpoint import build_cognitive_development_checkpoint
        payload = build_cognitive_development_checkpoint()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "Cognitive development checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print("This checkpoint is read-only and cannot browse, authorize, execute, promote, or certify.")
        return 0 if payload.get("ok") else 1
    if command == "inquiry-cognition-checkpoint":
        from conscious_agent.inquiry_cognition_checkpoint import build_inquiry_cognition_checkpoint
        payload = build_inquiry_cognition_checkpoint()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("headline") or "Inquiry cognition checkpoint unavailable.")
            print(f"Status: {payload.get('status', 'unknown')}")
            print("This checkpoint is read-only and cannot browse, authorize, execute, promote, certify, or prove consciousness.")
        return 0 if payload.get("ok") else 1
    if command == "inquiry-residual-lineage":
        from conscious_agent.inquiry_residual_lineage import InquiryResidualLineage
        store = InquiryResidualLineage()
        payload = store.create_child(args.event_id, parent_inquiry_id=args.parent_inquiry_id, residual_question=args.residual_question) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "cross-inquiry-evidence-lineage":
        from conscious_agent.cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
        store = CrossInquiryEvidenceLineage()
        payload = store.link(args.event_id, evidence_id=args.evidence_id, target_inquiry_id=args.target_inquiry_id, stance=args.stance, relevance=args.relevance) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "knowledge-confidence-checkpoint":
        from conscious_agent.knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
        payload = build_knowledge_confidence_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "knowledge-reconsideration":
        from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
        store = KnowledgeReconsiderationScheduler()
        payload = store.schedule_from_checkpoint(args.event_id) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "evidence-change-propagation":
        from conscious_agent.evidence_change_propagation import EvidenceChangePropagation
        store = EvidenceChangePropagation()
        payload = store.propagate(args.event_id, evidence_id=args.evidence_id, change_type=args.change_type) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "reconsideration-communication":
        from conscious_agent.reconsideration_conversation_continuity import ReconsiderationConversationBridge
        store = ReconsiderationConversationBridge()
        payload = store.consider(args.event_id, schedule_id=args.schedule_id, conclusion=args.conclusion, changed_belief=args.changed_belief, tone=args.tone) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "reconsideration-reflection":
        from conscious_agent.bounded_reconsideration_reflection import BoundedReconsiderationReflection
        store = BoundedReconsiderationReflection()
        payload = store.reflect(args.event_id, schedule_id=args.schedule_id, conclusion=args.conclusion, select_silence=args.silence) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "belief-maintenance-outcome":
        from conscious_agent.belief_maintenance_outcomes import BeliefMaintenanceOutcomes
        store = BeliefMaintenanceOutcomes()
        payload = store.apply(args.event_id, schedule_id=args.schedule_id, outcome=args.outcome, conclusion=args.conclusion, new_confidence=args.new_confidence) if args.event_id else store.inspection_summary()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "knowledge-maintenance-consolidation":
        from conscious_agent.knowledge_maintenance_consolidation import build_knowledge_maintenance_consolidation
        payload = build_knowledge_maintenance_consolidation()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "knowledge-maintenance-checkpoint":
        from conscious_agent.knowledge_maintenance_checkpoint import build_knowledge_maintenance_checkpoint
        payload = build_knowledge_maintenance_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "attention-agenda":
        from conscious_agent.autonomous_attention_agenda import build_autonomous_attention_agenda_inspection
        payload = build_autonomous_attention_agenda_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "attention-arbitration":
        from conscious_agent.motivation_agenda_arbitration import build_motivation_agenda_arbitration_inspection
        payload = build_motivation_agenda_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "attention-agenda-checkpoint":
        from conscious_agent.agenda_continuity_checkpoint import build_agenda_continuity_checkpoint
        payload = build_agenda_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "agenda-guided-reflection":
        from conscious_agent.agenda_guided_reflection import build_agenda_guided_reflection_inspection
        payload = build_agenda_guided_reflection_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "bounded-intentions":
        from conscious_agent.bounded_intention_formation import build_bounded_intention_inspection
        payload = build_bounded_intention_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "attention-intention-checkpoint":
        from conscious_agent.attention_intention_checkpoint import build_attention_intention_checkpoint
        payload = build_attention_intention_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "intention-lifecycle":
        from conscious_agent.intention_reconsideration_decay import build_intention_lifecycle_inspection
        payload = build_intention_lifecycle_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "intention-conflicts":
        from conscious_agent.intention_conflict_resolution import build_intention_conflict_inspection
        payload = build_intention_conflict_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "intention-lifecycle-review":
        from conscious_agent.intention_lifecycle_review import build_intention_lifecycle_review
        payload = build_intention_lifecycle_review()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "autonomous-attention-intention-checkpoint":
        from conscious_agent.autonomous_attention_intention_checkpoint import build_autonomous_attention_intention_checkpoint
        payload = build_autonomous_attention_intention_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "persistent-initiative":
        from conscious_agent.persistent_initiative import build_persistent_initiative_inspection
        payload = build_persistent_initiative_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-arbitration":
        from conscious_agent.initiative_arbitration import build_initiative_arbitration_inspection
        payload = build_initiative_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "persistent-initiative-checkpoint":
        from conscious_agent.persistent_initiative_checkpoint import build_persistent_initiative_checkpoint
        payload = build_persistent_initiative_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-conversation-proposal":
        from conscious_agent.initiative_conversation_proposal import build_initiative_conversation_proposal_inspection
        payload = build_initiative_conversation_proposal_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-communication-restraint":
        from conscious_agent.initiative_communication_restraint import build_initiative_communication_restraint_inspection
        payload = build_initiative_communication_restraint_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-communication-checkpoint":
        from conscious_agent.initiative_communication_checkpoint import build_initiative_communication_checkpoint
        payload = build_initiative_communication_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "surfaced-initiative-reconciliation":
        from conscious_agent.surfaced_initiative_reconciliation import build_surfaced_initiative_reconciliation_inspection
        payload = build_surfaced_initiative_reconciliation_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-response-reconciliation":
        from conscious_agent.initiative_response_reconciliation import build_initiative_response_reconciliation_inspection
        payload = build_initiative_response_reconciliation_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "initiative-lifecycle-checkpoint":
        from conscious_agent.initiative_lifecycle_checkpoint import build_initiative_lifecycle_checkpoint
        payload = build_initiative_lifecycle_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "persistent-initiative-consolidation-checkpoint":
        from conscious_agent.persistent_initiative_consolidation_checkpoint import build_persistent_initiative_consolidation_checkpoint
        payload = build_persistent_initiative_consolidation_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "long-horizon-objective":
        from conscious_agent.long_horizon_objective import build_long_horizon_objective_inspection
        payload = build_long_horizon_objective_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-review-arbitration":
        from conscious_agent.objective_review_arbitration import build_objective_review_arbitration_inspection
        payload = build_objective_review_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "long-horizon-objective-checkpoint":
        from conscious_agent.long_horizon_objective_checkpoint import build_long_horizon_objective_checkpoint
        payload = build_long_horizon_objective_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-milestones":
        from conscious_agent.objective_milestone_decomposition import build_objective_milestone_inspection
        payload = build_objective_milestone_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-progress-evidence":
        from conscious_agent.objective_progress_evidence import build_objective_progress_inspection
        payload = build_objective_progress_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-planning-progress-checkpoint":
        from conscious_agent.objective_planning_progress_checkpoint import build_objective_planning_progress_checkpoint
        payload = build_objective_planning_progress_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-conflict-reconciliation":
        from conscious_agent.objective_conflict_reconciliation import build_objective_conflict_inspection
        payload = build_objective_conflict_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "objective-completion-abandonment":
        from conscious_agent.objective_completion_abandonment import build_objective_lifecycle_inspection
        payload = build_objective_lifecycle_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "long-horizon-objective-lifecycle-checkpoint":
        from conscious_agent.long_horizon_objective_lifecycle_checkpoint import build_long_horizon_objective_lifecycle_checkpoint
        payload = build_long_horizon_objective_lifecycle_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "long-horizon-follow-through-checkpoint":
        from conscious_agent.long_horizon_follow_through_checkpoint import build_long_horizon_follow_through_checkpoint
        payload = build_long_horizon_follow_through_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "endogenous-curiosity":
        from conscious_agent.endogenous_curiosity import build_endogenous_curiosity_inspection
        payload = build_endogenous_curiosity_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-arbitration":
        from conscious_agent.curiosity_arbitration import build_curiosity_arbitration_inspection
        payload = build_curiosity_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-continuity-checkpoint":
        from conscious_agent.curiosity_continuity_checkpoint import build_curiosity_continuity_checkpoint
        payload = build_curiosity_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-questions":
        from conscious_agent.curiosity_question_formulation import build_curiosity_question_inspection
        payload = build_curiosity_question_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-quality":
        from conscious_agent.curiosity_quality_arbitration import build_curiosity_quality_inspection
        payload = build_curiosity_quality_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-quality-checkpoint":
        from conscious_agent.curiosity_quality_checkpoint import build_curiosity_quality_checkpoint
        payload = build_curiosity_quality_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-inquiry-promotion":
        from conscious_agent.curiosity_inquiry_promotion import build_curiosity_inquiry_promotion_inspection
        payload = build_curiosity_inquiry_promotion_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-question-lifecycle":
        from conscious_agent.curiosity_question_lifecycle import build_curiosity_question_lifecycle_inspection
        payload = build_curiosity_question_lifecycle_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "curiosity-lifecycle-checkpoint":
        from conscious_agent.curiosity_lifecycle_checkpoint import build_curiosity_lifecycle_checkpoint
        payload = build_curiosity_lifecycle_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "endogenous-curiosity-checkpoint":
        from conscious_agent.endogenous_curiosity_checkpoint import build_endogenous_curiosity_checkpoint
        payload = build_endogenous_curiosity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-outcomes":
        from conscious_agent.behavioral_outcome_evidence import build_behavioral_outcome_inspection
        payload = build_behavioral_outcome_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-attributions":
        from conscious_agent.behavioral_outcome_attribution import build_behavioral_attribution_inspection
        payload = build_behavioral_attribution_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-evidence-checkpoint":
        from conscious_agent.behavioral_evidence_continuity_checkpoint import build_behavioral_evidence_continuity_checkpoint
        payload = build_behavioral_evidence_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-patterns":
        from conscious_agent.behavioral_pattern_detection import build_behavioral_pattern_inspection
        payload = build_behavioral_pattern_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-self-evaluation":
        from conscious_agent.behavioral_self_evaluation import build_behavioral_self_evaluation_inspection
        payload = build_behavioral_self_evaluation_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-self-evaluation-checkpoint":
        from conscious_agent.behavioral_self_evaluation_checkpoint import build_behavioral_self_evaluation_checkpoint
        payload = build_behavioral_self_evaluation_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-adaptation-proposals":
        from conscious_agent.behavioral_adaptation_proposals import build_behavioral_adaptation_proposal_inspection
        payload = build_behavioral_adaptation_proposal_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-adaptation-lifecycle":
        from conscious_agent.behavioral_adaptation_lifecycle import build_behavioral_adaptation_lifecycle_inspection
        payload = build_behavioral_adaptation_lifecycle_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "behavioral-adaptation-checkpoint":
        from conscious_agent.behavioral_adaptation_checkpoint import build_behavioral_adaptation_checkpoint
        payload = build_behavioral_adaptation_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "reflective-behavioral-learning-checkpoint":
        from conscious_agent.reflective_behavioral_learning_checkpoint import build_reflective_behavioral_learning_checkpoint
        payload = build_reflective_behavioral_learning_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "active-inquiries":
        from conscious_agent.active_inquiry_records import build_active_inquiry_inspection
        payload = build_active_inquiry_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "inquiry-activation":
        from conscious_agent.inquiry_activation_arbitration import build_inquiry_activation_arbitration_inspection
        payload = build_inquiry_activation_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "active-inquiry-checkpoint":
        from conscious_agent.active_inquiry_continuity_checkpoint import build_active_inquiry_continuity_checkpoint
        payload = build_active_inquiry_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "inquiry-evidence-governance-checkpoint":
        from conscious_agent.inquiry_evidence_governance_checkpoint import build_inquiry_evidence_governance_checkpoint
        payload = build_inquiry_evidence_governance_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "inquiry-resolution-checkpoint":
        from conscious_agent.inquiry_resolution_checkpoint import build_inquiry_resolution_checkpoint
        payload = build_inquiry_resolution_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "bounded-inquiry-checkpoint":
        from conscious_agent.bounded_inquiry_checkpoint import build_bounded_inquiry_checkpoint
        payload = build_bounded_inquiry_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "deliberative-options":
        from conscious_agent.deliberative_option_records import build_deliberative_option_inspection
        payload = build_deliberative_option_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "deliberative-option-arbitration":
        from conscious_agent.deliberative_option_arbitration import build_deliberative_option_arbitration_inspection
        payload = build_deliberative_option_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "deliberative-continuity-checkpoint":
        from conscious_agent.deliberative_continuity_checkpoint import build_deliberative_continuity_checkpoint
        payload = build_deliberative_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "decision-commitment-checkpoint":
        from conscious_agent.decision_commitment_checkpoint import build_decision_commitment_checkpoint
        payload = build_decision_commitment_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "deliberative-decision-review-checkpoint":
        from conscious_agent.deliberative_decision_review_checkpoint import build_deliberative_decision_review_checkpoint
        payload = build_deliberative_decision_review_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-load-continuity-checkpoint":
        from conscious_agent.cognitive_load_continuity_checkpoint import build_cognitive_load_continuity_checkpoint
        report = build_cognitive_load_continuity_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if command == "cognitive-work-continuity-checkpoint":
        from conscious_agent.cognitive_work_continuity_checkpoint import build_cognitive_work_continuity_checkpoint
        payload = build_cognitive_work_continuity_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-coordination-review-checkpoint":
        from conscious_agent.cognitive_coordination_review_checkpoint import build_cognitive_coordination_review_checkpoint
        payload = build_cognitive_coordination_review_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1

    if command == "internal-coordination-cognitive-load-governance-checkpoint":
        from conscious_agent.internal_coordination_cognitive_load_governance_checkpoint import build_internal_coordination_cognitive_load_governance_checkpoint
        payload = build_internal_coordination_cognitive_load_governance_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-sustainability-review-checkpoint":
        from conscious_agent.cognitive_sustainability_review_checkpoint import build_cognitive_sustainability_review_checkpoint
        payload = build_cognitive_sustainability_review_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "temporal-review-checkpoint":
        from conscious_agent.temporal_review_checkpoint import build_temporal_review_checkpoint
        result = build_temporal_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "prospective-continuity-review-checkpoint":
        from conscious_agent.prospective_continuity_review_checkpoint import build_prospective_continuity_review_checkpoint
        result = build_prospective_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "epistemic-coherence-intake-checkpoint":
        from conscious_agent.epistemic_coherence_intake_checkpoint import build_epistemic_coherence_intake_checkpoint
        result = build_epistemic_coherence_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "epistemic-coherence-deliberation-checkpoint":
        from conscious_agent.epistemic_coherence_deliberation_checkpoint import build_epistemic_coherence_deliberation_checkpoint
        result = build_epistemic_coherence_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "knowledge-belief-integration-checkpoint":
        from conscious_agent.knowledge_belief_integration_checkpoint import build_knowledge_belief_integration_checkpoint
        result = build_knowledge_belief_integration_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "epistemic-coherence-knowledge-belief-integration-checkpoint":
        from conscious_agent.epistemic_coherence_knowledge_belief_integration_checkpoint import build_epistemic_coherence_knowledge_belief_integration_checkpoint
        result = build_epistemic_coherence_knowledge_belief_integration_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "motivational-continuity-intake-checkpoint":
        from conscious_agent.motivational_continuity_intake_checkpoint import build_motivational_continuity_intake_checkpoint
        result = build_motivational_continuity_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "motivational-drive-deliberation-checkpoint":
        from conscious_agent.motivational_drive_deliberation_checkpoint import build_motivational_drive_deliberation_checkpoint
        result = build_motivational_drive_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "motivational-continuity-review-checkpoint":
        from conscious_agent.motivational_continuity_review_checkpoint import build_motivational_continuity_review_checkpoint
        result = build_motivational_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "motivational-continuity-endogenous-drive-regulation-checkpoint":
        from conscious_agent.motivational_continuity_endogenous_drive_regulation_checkpoint import build_motivational_continuity_endogenous_drive_regulation_checkpoint
        result = build_motivational_continuity_endogenous_drive_regulation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-attention-salience-intake-checkpoint":
        from conscious_agent.reflective_attention_salience_intake_checkpoint import build_reflective_attention_salience_intake_checkpoint
        result = build_reflective_attention_salience_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-attention-deliberation-checkpoint":
        from conscious_agent.reflective_attention_deliberation_checkpoint import build_reflective_attention_deliberation_checkpoint
        result = build_reflective_attention_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-attention-continuity-review-checkpoint":
        from conscious_agent.reflective_attention_continuity_review_checkpoint import build_reflective_attention_continuity_review_checkpoint
        result = build_reflective_attention_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "selected-attention-focus-intake-checkpoint":
        from conscious_agent.selected_attention_focus_intake_checkpoint import build_selected_attention_focus_intake_checkpoint
        result = build_selected_attention_focus_intake_checkpoint()
        if getattr(args, "json", False):
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{result.get('status')}: {result.get('passed')}/{result.get('total')} checks")
        return 0 if result.get("ok") else 1

    if command == "reflective-focus-deliberation-checkpoint":
        from conscious_agent.reflective_focus_deliberation_checkpoint import build_reflective_focus_deliberation_checkpoint
        result = build_reflective_focus_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else f"{result.get('status')}: {result.get('passed')}/{result.get('total')} checks")
        return 0 if result.get("ok") else 1

    if command == "reflective-focus-continuity-review-checkpoint":
        from conscious_agent.reflective_focus_continuity_review_checkpoint import build_reflective_focus_continuity_review_checkpoint
        result = build_reflective_focus_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "selected-attention-reflective-focus-governance-checkpoint":
        from conscious_agent.selected_attention_reflective_focus_governance_checkpoint import build_selected_attention_reflective_focus_governance_checkpoint
        result = build_selected_attention_reflective_focus_governance_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-execution-continuity-checkpoint":
        from conscious_agent.reflective_execution_continuity_checkpoint import build_reflective_execution_continuity_checkpoint
        report = build_reflective_execution_continuity_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflective-integration-reliability-checkpoint":
        from conscious_agent.reflective_integration_reliability_checkpoint import build_reflective_integration_reliability_checkpoint
        report = build_reflective_integration_reliability_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "real-reflective-cognition-checkpoint":
        from conscious_agent.real_reflective_cognition_checkpoint import build_real_reflective_cognition_checkpoint
        report = build_real_reflective_cognition_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-quality-intake-checkpoint":
        from conscious_agent.reflection_quality_intake_checkpoint import build_reflection_quality_intake_checkpoint
        report = build_reflection_quality_intake_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0

    if command == "reflection-quality-deliberation-checkpoint":
        from conscious_agent.reflection_quality_deliberation_checkpoint import build_reflection_quality_deliberation_checkpoint
        report = build_reflection_quality_deliberation_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1


    if command == "reflection-quality-integration-checkpoint":
        from conscious_agent.reflection_quality_integration_checkpoint import build_reflection_quality_integration_checkpoint
        report = build_reflection_quality_integration_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflective-communication-integration-checkpoint":
        from conscious_agent.reflective_communication_integration_checkpoint import build_reflective_communication_integration_checkpoint
        report = build_reflective_communication_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "reflective-communication-governance-checkpoint":
        from conscious_agent.reflective_communication_governance_checkpoint import build_reflective_communication_governance_checkpoint
        report = build_reflective_communication_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflective-communication-deliberation-checkpoint":
        from conscious_agent.reflective_communication_deliberation_checkpoint import build_reflective_communication_deliberation_checkpoint
        report = build_reflective_communication_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflective-communication-intake-checkpoint":
        from conscious_agent.reflective_communication_intake_checkpoint import build_reflective_communication_intake_checkpoint
        report = build_reflective_communication_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "genuine-inquiry-deliberation-checkpoint":
        from conscious_agent.genuine_inquiry_deliberation_checkpoint import build_genuine_inquiry_deliberation_checkpoint
        report = build_genuine_inquiry_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "genuine-inquiry-integration-checkpoint":
        from conscious_agent.genuine_inquiry_integration_checkpoint import build_genuine_inquiry_integration_checkpoint
        report = build_genuine_inquiry_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "read-only-perception-governance-checkpoint":
        from conscious_agent.read_only_perception_governance_checkpoint import build_read_only_perception_governance_checkpoint
        report = build_read_only_perception_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "revisable-world-model-intake-checkpoint":
        from conscious_agent.revisable_world_model_intake_checkpoint import build_revisable_world_model_intake_checkpoint
        report = build_revisable_world_model_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "internally-generated-goal-intake-checkpoint":
        from conscious_agent.internally_generated_goal_intake_checkpoint import build_internally_generated_goal_intake_checkpoint
        report = build_internally_generated_goal_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-specification-intake-checkpoint":
        from conscious_agent.supervised_specification_intake_checkpoint import build_supervised_specification_intake_checkpoint
        report = build_supervised_specification_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-test-plan-intake-checkpoint":
        from conscious_agent.supervised_test_plan_intake_checkpoint import build_supervised_test_plan_intake_checkpoint
        report = build_supervised_test_plan_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-change-intake-checkpoint":
        from conscious_agent.supervised_sandbox_change_intake_checkpoint import build_supervised_sandbox_change_intake_checkpoint
        print(json.dumps(build_supervised_sandbox_change_intake_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "supervised-isolated-sandbox-execution-intake-checkpoint":
        from conscious_agent.supervised_isolated_sandbox_execution_intake_checkpoint import build_supervised_isolated_sandbox_execution_intake_checkpoint
        report = build_supervised_isolated_sandbox_execution_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-isolated-sandbox-execution-deliberation-checkpoint":
        from conscious_agent.supervised_isolated_sandbox_execution_deliberation_checkpoint import build_supervised_isolated_sandbox_execution_deliberation_checkpoint
        report = build_supervised_isolated_sandbox_execution_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-isolated-sandbox-execution-integration-checkpoint":
        from conscious_agent.supervised_isolated_sandbox_execution_integration_checkpoint import build_supervised_isolated_sandbox_execution_integration_checkpoint
        report = build_supervised_isolated_sandbox_execution_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-isolated-sandbox-execution-governance-checkpoint":
        from conscious_agent.supervised_isolated_sandbox_execution_governance_checkpoint import build_supervised_isolated_sandbox_execution_governance_checkpoint
        report = build_supervised_isolated_sandbox_execution_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-correction-acceptance-intake-checkpoint":
        from conscious_agent.operator_correction_acceptance_intake_checkpoint import build_operator_correction_acceptance_intake_checkpoint
        report = build_operator_correction_acceptance_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-correction-acceptance-learning-governance-checkpoint":
        from conscious_agent.operator_correction_acceptance_learning_governance_checkpoint import build_operator_correction_acceptance_learning_governance_checkpoint
        report = build_operator_correction_acceptance_learning_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "workload-coordination-intake-checkpoint":
        from conscious_agent.workload_coordination_intake_checkpoint import build_workload_coordination_intake_checkpoint
        report = build_workload_coordination_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "workload-coordination-execution-checkpoint":
        from conscious_agent.workload_coordination_execution_checkpoint import build_workload_coordination_execution_checkpoint
        report = build_workload_coordination_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "workload-coordination-reliability-checkpoint":
        from conscious_agent.workload_coordination_reliability_checkpoint import build_workload_coordination_reliability_checkpoint
        report = build_workload_coordination_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "workload-coordination-governance-checkpoint":
        from conscious_agent.workload_coordination_governance_checkpoint import build_workload_coordination_governance_checkpoint
        report = build_workload_coordination_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "multi-day-continuity-soak-intake-checkpoint":
        from conscious_agent.multi_day_continuity_soak_intake_checkpoint import build_multi_day_continuity_soak_intake_checkpoint
        report = build_multi_day_continuity_soak_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "multi-day-continuity-soak-execution-checkpoint":
        from conscious_agent.multi_day_continuity_soak_execution_checkpoint import build_multi_day_continuity_soak_execution_checkpoint
        report = build_multi_day_continuity_soak_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1


    if command == "multi-day-continuity-soak-reliability-checkpoint":
        from conscious_agent.multi_day_continuity_soak_reliability_checkpoint import build_multi_day_continuity_soak_reliability_checkpoint
        print(json.dumps(build_multi_day_continuity_soak_reliability_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "multi-day-continuity-soak-governance-checkpoint":
        from conscious_agent.multi_day_continuity_soak_governance_checkpoint import build_multi_day_continuity_soak_governance_checkpoint
        report = build_multi_day_continuity_soak_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversation-cognition-unification-intake-checkpoint":
        from conscious_agent.conversation_cognition_unification_intake_checkpoint import build_conversation_cognition_unification_intake_checkpoint
        report = build_conversation_cognition_unification_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversation-cognition-unification-execution-checkpoint":
        from conscious_agent.conversation_cognition_unification_execution_checkpoint import build_conversation_cognition_unification_execution_checkpoint
        report = build_conversation_cognition_unification_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversation-cognition-unification-reliability-checkpoint":
        from conscious_agent.conversation_cognition_unification_reliability_checkpoint import build_conversation_cognition_unification_reliability_checkpoint
        report = build_conversation_cognition_unification_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversation-cognition-unification-governance-checkpoint":
        from conscious_agent.conversation_cognition_unification_governance_checkpoint import build_conversation_cognition_unification_governance_checkpoint
        report = build_conversation_cognition_unification_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "understandable-cognitive-controls-intake-checkpoint":
        from conscious_agent.understandable_cognitive_controls_intake_checkpoint import build_understandable_cognitive_controls_intake_checkpoint
        report = build_understandable_cognitive_controls_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "understandable-cognitive-controls-execution-checkpoint":
        from conscious_agent.understandable_cognitive_controls_execution_checkpoint import build_understandable_cognitive_controls_execution_checkpoint
        report = build_understandable_cognitive_controls_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "understandable-cognitive-controls-reliability-checkpoint":
        from conscious_agent.understandable_cognitive_controls_reliability_checkpoint import build_understandable_cognitive_controls_reliability_checkpoint
        report = build_understandable_cognitive_controls_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "understandable-cognitive-controls-governance-checkpoint":
        from conscious_agent.understandable_cognitive_controls_governance_checkpoint import build_understandable_cognitive_controls_governance_checkpoint
        report = build_understandable_cognitive_controls_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "architecture-consolidation-intake-checkpoint":
        from conscious_agent.architecture_consolidation_intake_checkpoint import build_architecture_consolidation_intake_checkpoint
        report = build_architecture_consolidation_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "architecture-consolidation-execution-checkpoint":
        from conscious_agent.architecture_consolidation_execution_checkpoint import build_architecture_consolidation_execution_checkpoint
        report = build_architecture_consolidation_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "architecture-consolidation-reliability-checkpoint":
        from conscious_agent.architecture_consolidation_reliability_checkpoint import build_architecture_consolidation_reliability_checkpoint
        report = build_architecture_consolidation_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "architecture-consolidation-governance-checkpoint":
        from conscious_agent.architecture_consolidation_governance_checkpoint import build_architecture_consolidation_governance_checkpoint
        report = build_architecture_consolidation_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "privacy-security-hardening-intake-checkpoint":
        from conscious_agent.privacy_security_hardening_intake_checkpoint import build_privacy_security_hardening_intake_checkpoint
        report = build_privacy_security_hardening_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "privacy-security-hardening-execution-checkpoint":
        from conscious_agent.privacy_security_hardening_execution_checkpoint import build_privacy_security_hardening_execution_checkpoint
        report = build_privacy_security_hardening_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "privacy-security-hardening-reliability-checkpoint":
        from conscious_agent.privacy_security_hardening_reliability_checkpoint import build_privacy_security_hardening_reliability_checkpoint
        report = build_privacy_security_hardening_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "privacy-security-hardening-governance-checkpoint":
        from conscious_agent.privacy_security_hardening_governance_checkpoint import build_privacy_security_hardening_governance_checkpoint
        report = build_privacy_security_hardening_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "cognitive-alpha-feature-freeze-intake-checkpoint":
        from conscious_agent.cognitive_alpha_feature_freeze_intake_checkpoint import build_cognitive_alpha_feature_freeze_intake_checkpoint
        report = build_cognitive_alpha_feature_freeze_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "cognitive-alpha-feature-freeze-execution-checkpoint":
        from conscious_agent.cognitive_alpha_feature_freeze_execution_checkpoint import build_cognitive_alpha_feature_freeze_execution_checkpoint
        print(json.dumps(build_cognitive_alpha_feature_freeze_execution_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "cognitive-alpha-feature-freeze-reliability-checkpoint":
        from conscious_agent.cognitive_alpha_feature_freeze_reliability_checkpoint import build_cognitive_alpha_feature_freeze_reliability_checkpoint
        report = build_cognitive_alpha_feature_freeze_reliability_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "cognitive-alpha-feature-freeze-governance-checkpoint":
        from conscious_agent.cognitive_alpha_feature_freeze_governance_checkpoint import build_cognitive_alpha_feature_freeze_governance_checkpoint
        report = build_cognitive_alpha_feature_freeze_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reasoning-alpha-checkpoint":
        from conscious_agent.reasoning_alpha_checkpoint import build_reasoning_alpha_checkpoint
        report = build_reasoning_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-alpha-checkpoint":
        from conscious_agent.reflection_alpha_checkpoint import build_reflection_alpha_checkpoint
        report = build_reflection_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "belief-revision-alpha-checkpoint":
        from conscious_agent.belief_revision_alpha_checkpoint import build_belief_revision_alpha_checkpoint
        report = build_belief_revision_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "multi-step-deliberation-alpha-checkpoint":
        from conscious_agent.multi_step_deliberation_alpha_checkpoint import build_multi_step_deliberation_alpha_checkpoint
        report = build_multi_step_deliberation_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "decision-boundary-alpha-checkpoint":
        from conscious_agent.decision_boundary_alpha_checkpoint import build_decision_boundary_alpha_checkpoint
        report = build_decision_boundary_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reasoning-alpha-consolidation-checkpoint":
        from conscious_agent.reasoning_alpha_consolidation_checkpoint import build_reasoning_alpha_consolidation_checkpoint
        report = build_reasoning_alpha_consolidation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversation-intent-selection-checkpoint":
        from conscious_agent.conversation_intent_selection_checkpoint import build_conversation_intent_selection_checkpoint
        report = build_conversation_intent_selection_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "contextual-conversation-behavior-checkpoint":
        from conscious_agent.contextual_conversation_behavior_checkpoint import build_contextual_conversation_behavior_checkpoint
        report = build_contextual_conversation_behavior_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "follow-up-silence-checkpoint":
        from conscious_agent.follow_up_silence_checkpoint import build_follow_up_silence_checkpoint
        report = build_follow_up_silence_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "cognitive-integration-alpha-checkpoint":
        from conscious_agent.cognitive_integration_alpha_checkpoint import build_cognitive_integration_alpha_checkpoint
        report = build_cognitive_integration_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "conversation-policy-checkpoint":
        from conscious_agent.conversation_policy_checkpoint import build_conversation_policy_checkpoint
        report = build_conversation_policy_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "natural-conversation-continuity-checkpoint":
        from conscious_agent.natural_conversation_continuity_checkpoint import build_natural_conversation_continuity_checkpoint
        report = build_natural_conversation_continuity_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "natural-follow-up-checkpoint":
        from conscious_agent.natural_follow_up_checkpoint import build_natural_follow_up_checkpoint
        report = build_natural_follow_up_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "governed-speech-checkpoint":
        from conscious_agent.governed_speech_checkpoint import build_governed_speech_checkpoint
        report = build_governed_speech_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "daily-companion-cognition-checkpoint":
        from conscious_agent.daily_companion_cognition_checkpoint import build_daily_companion_cognition_checkpoint
        report = build_daily_companion_cognition_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "unified-memory-checkpoint":
        from conscious_agent.unified_memory_checkpoint import build_unified_memory_checkpoint
        report = build_unified_memory_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "memory-retrieval-relevance-checkpoint":
        from conscious_agent.memory_retrieval_relevance_checkpoint import build_memory_retrieval_relevance_checkpoint
        report = build_memory_retrieval_relevance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "immediate-memory-learning-checkpoint":
        from conscious_agent.immediate_memory_learning_checkpoint import build_immediate_memory_learning_checkpoint
        report = build_immediate_memory_learning_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "bounded-experiential-lessons-checkpoint":
        from conscious_agent.bounded_experiential_lessons_checkpoint import build_bounded_experiential_lessons_checkpoint
        report = build_bounded_experiential_lessons_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "memory-experiential-learning-alpha-checkpoint":
        from conscious_agent.memory_experiential_learning_alpha_checkpoint import build_memory_experiential_learning_alpha_checkpoint
        report = build_memory_experiential_learning_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "internally-generated-goal-candidate-checkpoint":
        from conscious_agent.internally_generated_goal_candidate_checkpoint import build_internally_generated_goal_candidate_checkpoint
        report = build_internally_generated_goal_candidate_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "hierarchical-planning-checkpoint":
        from conscious_agent.hierarchical_planning_checkpoint import build_hierarchical_planning_checkpoint
        report = build_hierarchical_planning_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "plan-simulation-checkpoint":
        from conscious_agent.plan_simulation_checkpoint import build_plan_simulation_checkpoint
        report = build_plan_simulation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "persistent-follow-through-checkpoint":
        from conscious_agent.persistent_follow_through_checkpoint import build_persistent_follow_through_checkpoint
        report = build_persistent_follow_through_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "goal-and-planning-alpha-checkpoint":
        from conscious_agent.goal_and_planning_alpha_checkpoint import build_goal_and_planning_alpha_checkpoint
        report = build_goal_and_planning_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "natural-language-action-execution-checkpoint":
        from conscious_agent.natural_language_action_execution_checkpoint import build_natural_language_action_execution_checkpoint
        report = build_natural_language_action_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "clarification-argument-routing-checkpoint":
        from conscious_agent.clarification_argument_routing_checkpoint import build_clarification_argument_routing_checkpoint
        report = build_clarification_argument_routing_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "natural-language-action-approval-governance-checkpoint":
        from conscious_agent.natural_language_action_approval_governance_checkpoint import build_natural_language_action_approval_governance_checkpoint
        report = build_natural_language_action_approval_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "natural-language-action-authoritative-result-checkpoint":
        from conscious_agent.natural_language_action_authoritative_result_checkpoint import build_natural_language_action_authoritative_result_checkpoint
        report = build_natural_language_action_authoritative_result_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "natural-language-action-checkpoint":
        from conscious_agent.natural_language_action_checkpoint import build_natural_language_action_checkpoint
        report = build_natural_language_action_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-project-inspection-planning-checkpoint":
        from conscious_agent.supervised_project_inspection_planning_checkpoint import build_supervised_project_inspection_planning_checkpoint
        report = build_supervised_project_inspection_planning_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-implementation-checkpoint":
        from conscious_agent.supervised_implementation_checkpoint import build_supervised_implementation_checkpoint
        report = build_supervised_implementation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-testing-repair-checkpoint":
        from conscious_agent.supervised_sandbox_testing_repair_checkpoint import build_supervised_sandbox_testing_repair_checkpoint
        report = build_supervised_sandbox_testing_repair_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-repair-draft-checkpoint":
        from conscious_agent.supervised_sandbox_repair_draft_checkpoint import build_supervised_sandbox_repair_draft_checkpoint
        report = build_supervised_sandbox_repair_draft_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-repair-materialization-checkpoint":
        from conscious_agent.supervised_sandbox_repair_materialization_checkpoint import build_supervised_sandbox_repair_materialization_checkpoint
        report = build_supervised_sandbox_repair_materialization_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-retesting-checkpoint":
        from conscious_agent.supervised_sandbox_retesting_checkpoint import build_supervised_sandbox_retesting_checkpoint
        report = build_supervised_sandbox_retesting_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-repair-retest-checkpoint":
        from conscious_agent.supervised_sandbox_repair_retest_checkpoint import build_supervised_sandbox_repair_retest_checkpoint
        report = build_supervised_sandbox_repair_retest_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "supervised-project-development-foundations-checkpoint":
        from conscious_agent.supervised_project_development_foundations_checkpoint import build_supervised_project_development_foundations_checkpoint
        report = build_supervised_project_development_foundations_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "supervised-project-development-alpha-checkpoint":
        from conscious_agent.supervised_project_development_alpha_checkpoint import build_supervised_project_development_alpha_checkpoint
        report = build_supervised_project_development_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "persistent-supervised-developer-alpha-checkpoint":
        from conscious_agent.persistent_supervised_developer_alpha_checkpoint import build_persistent_supervised_developer_alpha_checkpoint
        report = build_persistent_supervised_developer_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "durable-campaign-continuation-checkpoint":
        from conscious_agent.durable_campaign_continuation_checkpoint import build_durable_campaign_continuation_checkpoint
        report = build_durable_campaign_continuation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "persistent-campaign-work-execution-checkpoint":
        from conscious_agent.persistent_campaign_work_execution_checkpoint import build_persistent_campaign_work_execution_checkpoint
        report = build_persistent_campaign_work_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "persistent-supervised-developer-hardening-checkpoint":
        from conscious_agent.persistent_supervised_developer_hardening_checkpoint import build_persistent_supervised_developer_hardening_checkpoint
        print(json.dumps(build_persistent_supervised_developer_hardening_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "persistent-supervised-developer-alpha-hardening-checkpoint":
        from conscious_agent.persistent_supervised_developer_alpha_hardening_checkpoint import build_persistent_supervised_developer_alpha_hardening_checkpoint
        report = build_persistent_supervised_developer_alpha_hardening_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "responsive-work-queue-checkpoint":
        from conscious_agent.responsive_work_queue_checkpoint import build_responsive_work_queue_checkpoint
        report = build_responsive_work_queue_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "responsive-work-queue-review-checkpoint":
        from conscious_agent.responsive_work_queue_review_checkpoint import build_responsive_work_queue_review_checkpoint
        report = build_responsive_work_queue_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "responsive-work-queue-reliability-checkpoint":
        from conscious_agent.responsive_work_queue_reliability_checkpoint import build_responsive_work_queue_reliability_checkpoint
        report = build_responsive_work_queue_reliability_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "responsiveness-background-work-checkpoint":
        from conscious_agent.responsiveness_background_work_checkpoint import build_responsiveness_background_work_checkpoint
        report = build_responsiveness_background_work_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "bounded-evidence-compaction-checkpoint":
        from conscious_agent.bounded_evidence_compaction_checkpoint import build_bounded_evidence_compaction_checkpoint
        report = build_bounded_evidence_compaction_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "evidence-compaction-review-checkpoint":
        from conscious_agent.evidence_compaction_review_checkpoint import build_evidence_compaction_review_checkpoint
        report = build_evidence_compaction_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "evidence-compaction-reliability-checkpoint":
        from conscious_agent.evidence_compaction_reliability_checkpoint import build_evidence_compaction_reliability_checkpoint
        report = build_evidence_compaction_reliability_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "evidence-compaction-checkpoint":
        from conscious_agent.evidence_compaction_checkpoint import build_evidence_compaction_checkpoint
        report = build_evidence_compaction_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "verifier-ownership-checkpoint":
        from conscious_agent.verifier_ownership_checkpoint import build_verifier_ownership_checkpoint
        report = build_verifier_ownership_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "verifier-profile-reconciliation-checkpoint":
        from conscious_agent.verifier_profile_reconciliation_checkpoint import build_verifier_profile_reconciliation_checkpoint
        report = build_verifier_profile_reconciliation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "fixture-historical-debt-consolidation-checkpoint":
        from conscious_agent.fixture_historical_debt_consolidation_checkpoint import build_fixture_historical_debt_consolidation_checkpoint
        report = build_fixture_historical_debt_consolidation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "verifier-historical-debt-checkpoint":
        from conscious_agent.verifier_historical_debt_checkpoint import build_verifier_historical_debt_checkpoint
        report = build_verifier_historical_debt_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "unified-cognitive-developer-checkpoint":
        from conscious_agent.unified_cognitive_developer_checkpoint import build_unified_cognitive_developer_checkpoint
        report = build_unified_cognitive_developer_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "general-test-adapter-consolidation-checkpoint":
        from conscious_agent.general_test_adapter_consolidation_checkpoint import build_general_test_adapter_consolidation_checkpoint
        report = build_general_test_adapter_consolidation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversational-build-test-loop-checkpoint":
        from conscious_agent.conversational_build_test_loop_checkpoint import build_conversational_build_test_loop_checkpoint
        report = build_conversational_build_test_loop_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-build-test-results-checkpoint":
        from conscious_agent.operator_build_test_results_checkpoint import build_operator_build_test_results_checkpoint
        report = build_operator_build_test_results_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversational-build-test-continuation-checkpoint":
        from conscious_agent.conversational_build_test_continuation_checkpoint import build_conversational_build_test_continuation_checkpoint
        report = build_conversational_build_test_continuation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "bounded-automatic-diagnosis-checkpoint":
        from conscious_agent.bounded_automatic_diagnosis_checkpoint import build_bounded_automatic_diagnosis_checkpoint
        report = build_bounded_automatic_diagnosis_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-diagnosis-review-checkpoint":
        from conscious_agent.operator_diagnosis_review_checkpoint import build_operator_diagnosis_review_checkpoint
        report = build_operator_diagnosis_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "conversational-supervised-repair-execution-checkpoint":
        from conscious_agent.conversational_supervised_repair_execution_checkpoint import build_conversational_supervised_repair_execution_checkpoint
        report = build_conversational_supervised_repair_execution_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-repair-result-review-checkpoint":
        from conscious_agent.operator_repair_result_review_checkpoint import build_operator_repair_result_review_checkpoint
        report = build_operator_repair_result_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-repaired-candidate-apply-checkpoint":
        from conscious_agent.supervised_repaired_candidate_apply_checkpoint import build_supervised_repaired_candidate_apply_checkpoint
        report = build_supervised_repaired_candidate_apply_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-repaired-candidate-apply-result-review-checkpoint":
        from conscious_agent.operator_repaired_candidate_apply_result_review_checkpoint import build_operator_repaired_candidate_apply_result_review_checkpoint
        report = build_operator_repaired_candidate_apply_result_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "unified-supervised-development-transaction-history-checkpoint":
        from conscious_agent.unified_supervised_development_transaction_history_checkpoint import (
            build_unified_supervised_development_transaction_history_checkpoint,
        )
        print(json.dumps(build_unified_supervised_development_transaction_history_checkpoint(), sort_keys=True))
        return 0
    if command == "transaction-resumption-abandoned-work-reconciliation-checkpoint":
        from conscious_agent.transaction_resumption_abandoned_work_reconciliation_checkpoint import (
            build_transaction_resumption_abandoned_work_reconciliation_checkpoint,
        )
        report = build_transaction_resumption_abandoned_work_reconciliation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "unified-development-work-queue-checkpoint":
        from conscious_agent.unified_development_work_queue_checkpoint import (
            build_unified_development_work_queue_checkpoint,
        )
        report = build_unified_development_work_queue_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "operator-governed-work-prioritization-scheduling-checkpoint":
        from conscious_agent.operator_governed_work_prioritization_scheduling_checkpoint import (
            build_operator_governed_work_prioritization_scheduling_checkpoint,
        )
        report = build_operator_governed_work_prioritization_scheduling_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "supervised-work-dispatch-execution-session-preparation-checkpoint":
        from conscious_agent.supervised_work_dispatch_execution_session_preparation_checkpoint import (
            build_supervised_work_dispatch_execution_session_preparation_checkpoint,
        )
        report = build_supervised_work_dispatch_execution_session_preparation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "execution-session-authorization-bounded-launch-checkpoint":
        from conscious_agent.execution_session_authorization_bounded_launch_checkpoint import (
            build_execution_session_authorization_bounded_launch_checkpoint,
        )
        report = build_execution_session_authorization_bounded_launch_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "live-execution-monitoring-operator-intervention-checkpoint":
        from conscious_agent.live_execution_monitoring_operator_intervention_checkpoint import (
            build_live_execution_monitoring_operator_intervention_checkpoint,
        )
        report = build_live_execution_monitoring_operator_intervention_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "execution-session-pause-resume-cancel-recovery-checkpoint":
        from conscious_agent.execution_session_pause_resume_cancel_recovery_checkpoint import (
            build_execution_session_pause_resume_cancel_recovery_checkpoint,
        )
        report = build_execution_session_pause_resume_cancel_recovery_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "execution-outcome-reflection-learning-integration-checkpoint":
        from conscious_agent.execution_outcome_reflection_learning_integration_checkpoint import (
            build_execution_outcome_reflection_learning_integration_checkpoint,
        )
        report = build_execution_outcome_reflection_learning_integration_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dynamic-execution-plan-revisions":
        from conscious_agent.dynamic_execution_plan_revision import public_dynamic_execution_plan_revisions
        report = public_dynamic_execution_plan_revisions(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dynamic-execution-plan-revision-reviews":
        from conscious_agent.dynamic_execution_plan_revision import public_dynamic_execution_plan_revision_reviews
        report = public_dynamic_execution_plan_revision_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dynamic-execution-plan-revision-checkpoint":
        from conscious_agent.dynamic_execution_plan_revision_checkpoint import build_dynamic_execution_plan_revision_checkpoint
        report = build_dynamic_execution_plan_revision_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dependency-aware-execution-assessments":
        from conscious_agent.dependency_aware_execution import public_dependency_aware_execution_assessments
        report = public_dependency_aware_execution_assessments(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dependency-aware-execution-reviews":
        from conscious_agent.dependency_aware_execution import public_dependency_aware_execution_reviews
        report = public_dependency_aware_execution_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "dependency-aware-execution-checkpoint":
        from conscious_agent.dependency_aware_execution_checkpoint import build_dependency_aware_execution_checkpoint
        report = build_dependency_aware_execution_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "feature-freeze-registry":
        from conscious_agent.feature_freeze_final_hardening import feature_freeze_registry
        report=feature_freeze_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "feature-freeze-manifest":
        from conscious_agent.feature_freeze_final_hardening import build_feature_freeze_manifest
        report=build_feature_freeze_manifest(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "feature-freeze-final-hardening-report":
        from conscious_agent.feature_freeze_final_hardening import build_final_hardening_report
        report=build_final_hardening_report(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "feature-freeze-final-hardening-checkpoint":
        from conscious_agent.feature_freeze_final_hardening_checkpoint import build_feature_freeze_final_hardening_checkpoint
        report=build_feature_freeze_final_hardening_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-mind-conversation-development-benchmark-registry":
        from conscious_agent.integrated_mind_conversation_development_benchmark import benchmark_registry
        report=benchmark_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-mind-conversation-development-benchmark":
        from conscious_agent.integrated_mind_conversation_development_benchmark import build_integrated_mind_conversation_development_contract
        report=build_integrated_mind_conversation_development_contract(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-mind-conversation-development-benchmark-checkpoint":
        from conscious_agent.integrated_mind_conversation_development_benchmark_checkpoint import build_integrated_mind_conversation_development_benchmark_checkpoint
        report=build_integrated_mind_conversation_development_benchmark_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "privacy-security-secret-management-registry":
        from conscious_agent.privacy_security_secret_management_audit import privacy_security_secret_management_registry
        report=privacy_security_secret_management_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "privacy-security-audits":
        from conscious_agent.privacy_security_secret_management_audit import public_privacy_security_audits
        report=public_privacy_security_audits(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "privacy-security-audit-reviews":
        from conscious_agent.privacy_security_secret_management_audit import public_privacy_security_audit_reviews
        report=public_privacy_security_audit_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "secret-management-remediation-proposals":
        from conscious_agent.privacy_security_secret_management_audit import public_secret_management_remediation_proposals
        report=public_secret_management_remediation_proposals(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "secret-management-remediation-reviews":
        from conscious_agent.privacy_security_secret_management_audit import public_secret_management_remediation_reviews
        report=public_secret_management_remediation_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "privacy-security-secret-management-audit-checkpoint":
        from conscious_agent.privacy_security_secret_management_audit_checkpoint import build_privacy_security_secret_management_audit_checkpoint
        report=build_privacy_security_secret_management_audit_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "initiative-proposal-pacing-registry":
        from conscious_agent.initiative_proposal_pacing import initiative_proposal_pacing_registry
        report=initiative_proposal_pacing_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "initiative-proposal-candidates":
        from conscious_agent.initiative_proposal_pacing import public_initiative_proposal_candidates
        report=public_initiative_proposal_candidates(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "initiative-pacing-decisions":
        from conscious_agent.initiative_proposal_pacing import public_initiative_pacing_decisions
        report=public_initiative_pacing_decisions(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "initiative-pacing-reviews":
        from conscious_agent.initiative_proposal_pacing import public_initiative_pacing_reviews
        report=public_initiative_pacing_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "initiative-proposal-pacing-checkpoint":
        from conscious_agent.initiative_proposal_pacing_checkpoint import build_initiative_proposal_pacing_checkpoint
        report=build_initiative_proposal_pacing_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "cross-session-project-understanding-registry":
        from conscious_agent.cross_session_project_understanding import cross_session_project_understanding_registry
        report=cross_session_project_understanding_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "project-understanding-snapshots":
        from conscious_agent.cross_session_project_understanding import public_project_understanding_snapshots
        report=public_project_understanding_snapshots(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "project-understanding-reconciliations":
        from conscious_agent.cross_session_project_understanding import public_project_understanding_reconciliations
        report=public_project_understanding_reconciliations(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "project-understanding-reviews":
        from conscious_agent.cross_session_project_understanding import public_project_understanding_reviews
        report=public_project_understanding_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "cross-session-project-understanding-checkpoint":
        from conscious_agent.cross_session_project_understanding_checkpoint import build_cross_session_project_understanding_checkpoint
        report=build_cross_session_project_understanding_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "long-running-session-continuity-registry":
        from conscious_agent.long_running_multi_day_session_continuity import long_running_session_continuity_registry
        report=long_running_session_continuity_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "session-continuity-progress":
        from conscious_agent.long_running_multi_day_session_continuity import public_session_continuity_progress
        report=public_session_continuity_progress(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "session-continuity-manifests":
        from conscious_agent.long_running_multi_day_session_continuity import public_session_continuity_manifests
        report=public_session_continuity_manifests(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "session-continuity-assessments":
        from conscious_agent.long_running_multi_day_session_continuity import public_session_continuity_assessments
        report=public_session_continuity_assessments(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "session-continuity-reviews":
        from conscious_agent.long_running_multi_day_session_continuity import public_session_continuity_reviews
        report=public_session_continuity_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "long-running-multi-day-session-continuity-checkpoint":
        from conscious_agent.long_running_multi_day_session_continuity_checkpoint import build_long_running_multi_day_session_continuity_checkpoint
        report=build_long_running_multi_day_session_continuity_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-model-governance-registry":
        from conscious_agent.provider_fallback_model_governance import provider_model_governance_registry
        report=provider_model_governance_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-model-registry-snapshots":
        from conscious_agent.provider_fallback_model_governance import public_provider_model_registry_snapshots
        report=public_provider_model_registry_snapshots(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-model-selection-proposals":
        from conscious_agent.provider_fallback_model_governance import public_provider_model_selection_proposals
        report=public_provider_model_selection_proposals(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-model-selection-reviews":
        from conscious_agent.provider_fallback_model_governance import public_provider_model_selection_reviews
        report=public_provider_model_selection_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-fallback-assessments":
        from conscious_agent.provider_fallback_model_governance import public_provider_fallback_assessments
        report=public_provider_fallback_assessments(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-fallback-reviews":
        from conscious_agent.provider_fallback_model_governance import public_provider_fallback_reviews
        report=public_provider_fallback_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "provider-fallback-model-governance-checkpoint":
        from conscious_agent.provider_fallback_model_governance_checkpoint import build_provider_fallback_model_governance_checkpoint
        report=build_provider_fallback_model_governance_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-registry":
        from conscious_agent.installation_upgrade_backup_rollback_integration import lifecycle_operation_registry
        report=lifecycle_operation_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-preflights":
        from conscious_agent.installation_upgrade_backup_rollback_integration import public_installation_lifecycle_preflights
        report=public_installation_lifecycle_preflights(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-proposals":
        from conscious_agent.installation_upgrade_backup_rollback_integration import public_installation_lifecycle_proposals
        report=public_installation_lifecycle_proposals(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-reviews":
        from conscious_agent.installation_upgrade_backup_rollback_integration import public_installation_lifecycle_reviews
        report=public_installation_lifecycle_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-recovery-assessments":
        from conscious_agent.installation_upgrade_backup_rollback_integration import public_installation_lifecycle_recovery_assessments
        report=public_installation_lifecycle_recovery_assessments(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-recovery-reviews":
        from conscious_agent.installation_upgrade_backup_rollback_integration import public_installation_lifecycle_recovery_reviews
        report=public_installation_lifecycle_recovery_reviews(runtime_root=(args.runtime_root or None)); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "installation-lifecycle-integration-checkpoint":
        from conscious_agent.installation_lifecycle_integration_checkpoint import build_installation_lifecycle_integration_checkpoint
        report=build_installation_lifecycle_integration_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "unified-operator-dashboard-registry":
        from conscious_agent.unified_operator_dashboard import dashboard_panel_registry
        report=dashboard_panel_registry(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "unified-operator-dashboard-snapshot":
        from conscious_agent.unified_operator_dashboard import build_unified_operator_dashboard_snapshot
        report=build_unified_operator_dashboard_snapshot(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "unified-operator-dashboard-checkpoint":
        from conscious_agent.unified_operator_dashboard_checkpoint import build_unified_operator_dashboard_checkpoint
        report=build_unified_operator_dashboard_checkpoint(); print(json.dumps(report,sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-developer-beta-scenario-registry":
        from conscious_agent.integrated_developer_beta import scenario_registry
        report = scenario_registry(); print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-developer-beta-benchmark":
        from conscious_agent.integrated_developer_beta import build_integrated_developer_beta_contract
        report = build_integrated_developer_beta_contract(); print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "integrated-developer-beta-checkpoint":
        from conscious_agent.integrated_developer_beta_checkpoint import build_integrated_developer_beta_checkpoint
        report = build_integrated_developer_beta_checkpoint(); print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "adversarial-boundary-attack-registry":
        from conscious_agent.adversarial_execution_cognitive_boundary import attack_registry
        report = attack_registry()
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "adversarial-boundary-assessments":
        from conscious_agent.adversarial_execution_cognitive_boundary import public_adversarial_boundary_assessments
        report = public_adversarial_boundary_assessments(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "adversarial-boundary-reviews":
        from conscious_agent.adversarial_execution_cognitive_boundary import public_adversarial_boundary_reviews
        report = public_adversarial_boundary_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "adversarial-execution-cognitive-boundary-checkpoint":
        from conscious_agent.adversarial_execution_cognitive_boundary_checkpoint import build_adversarial_execution_cognitive_boundary_checkpoint
        report = build_adversarial_execution_cognitive_boundary_checkpoint()
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "broader-project-language-adapter-registry":
        from conscious_agent.broader_project_language_adapters import adapter_registry
        report = adapter_registry()
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "broader-project-language-adapter-assessments":
        from conscious_agent.broader_project_language_adapters import public_broader_project_adapter_assessments
        report = public_broader_project_adapter_assessments(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "broader-project-language-adapter-reviews":
        from conscious_agent.broader_project_language_adapters import public_broader_project_adapter_reviews
        report = public_broader_project_adapter_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "broader-project-language-adapters-checkpoint":
        from conscious_agent.broader_project_language_adapters_checkpoint import build_broader_project_language_adapters_checkpoint
        report = build_broader_project_language_adapters_checkpoint()
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-plans":
        from conscious_agent.multi_tool_orchestration import public_multi_tool_orchestration_plans
        report = public_multi_tool_orchestration_plans(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-reviews":
        from conscious_agent.multi_tool_orchestration import public_multi_tool_orchestration_reviews
        report = public_multi_tool_orchestration_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-results":
        from conscious_agent.multi_tool_orchestration import public_multi_tool_orchestration_results
        report = public_multi_tool_orchestration_results(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-handoffs":
        from conscious_agent.multi_tool_orchestration import public_multi_tool_orchestration_handoffs
        report = public_multi_tool_orchestration_handoffs(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-handoff-reviews":
        from conscious_agent.multi_tool_orchestration import public_multi_tool_orchestration_handoff_reviews
        report = public_multi_tool_orchestration_handoff_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "multi-tool-orchestration-checkpoint":
        from conscious_agent.multi_tool_orchestration_checkpoint import build_multi_tool_orchestration_checkpoint
        report = build_multi_tool_orchestration_checkpoint()
        print(json.dumps(report, sort_keys=True)); return 0 if report.get("ok") else 1
    if command == "goal-motivation-work-priority-integrations":
        from conscious_agent.goal_motivation_work_priority_integration import public_goal_motivation_work_priority_integrations
        report = public_goal_motivation_work_priority_integrations(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "goal-motivation-work-priority-integration-reviews":
        from conscious_agent.goal_motivation_work_priority_integration import public_goal_motivation_work_priority_integration_reviews
        report = public_goal_motivation_work_priority_integration_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "goal-motivation-work-priority-integration-checkpoint":
        from conscious_agent.goal_motivation_work_priority_integration_checkpoint import build_goal_motivation_work_priority_integration_checkpoint
        report = build_goal_motivation_work_priority_integration_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "evidence-backed-development-lessons":
        from conscious_agent.evidence_backed_development_outcome_lessons import public_evidence_backed_development_lessons
        report = public_evidence_backed_development_lessons(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "evidence-backed-development-lesson-reviews":
        from conscious_agent.evidence_backed_development_outcome_lessons import public_evidence_backed_development_lesson_reviews
        report = public_evidence_backed_development_lesson_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "evidence-backed-development-lesson-reconsiderations":
        from conscious_agent.evidence_backed_development_outcome_lessons import public_evidence_backed_development_lesson_reconsiderations
        report = public_evidence_backed_development_lesson_reconsiderations(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "evidence-backed-development-outcome-lessons-checkpoint":
        from conscious_agent.evidence_backed_development_outcome_lessons_checkpoint import build_evidence_backed_development_outcome_lessons_checkpoint
        report = build_evidence_backed_development_outcome_lessons_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "requirement-quality-assessments":
        from conscious_agent.requirement_quality_assessment import public_requirement_quality_assessments
        report = public_requirement_quality_assessments(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "requirement-quality-assessment-reviews":
        from conscious_agent.requirement_quality_assessment import public_requirement_quality_assessment_reviews
        report = public_requirement_quality_assessment_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "requirement-quality-assessment-checkpoint":
        from conscious_agent.requirement_quality_assessment_checkpoint import build_requirement_quality_assessment_checkpoint
        report = build_requirement_quality_assessment_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "resource-concurrency-governance-assessments":
        from conscious_agent.resource_concurrency_governance import public_resource_concurrency_governance_assessments
        report = public_resource_concurrency_governance_assessments(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "resource-concurrency-governance-reviews":
        from conscious_agent.resource_concurrency_governance import public_resource_concurrency_governance_reviews
        report = public_resource_concurrency_governance_reviews(runtime_root=(args.runtime_root or None))
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "resource-concurrency-governance-checkpoint":
        from conscious_agent.resource_concurrency_governance_checkpoint import build_resource_concurrency_governance_checkpoint
        report = build_resource_concurrency_governance_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "mindful-execution-alpha-integration-benchmark-checkpoint":
        from conscious_agent.mindful_execution_alpha_integration_benchmark_checkpoint import (
            build_mindful_execution_alpha_integration_benchmark_checkpoint,
        )
        report = build_mindful_execution_alpha_integration_benchmark_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "operator-repaired-candidate-rollback-result-review-checkpoint":
        from conscious_agent.operator_repaired_candidate_rollback_result_review_checkpoint import (
            build_operator_repaired_candidate_rollback_result_review_checkpoint,
        )
        print(json.dumps(build_operator_repaired_candidate_rollback_result_review_checkpoint(), sort_keys=True))
        return 0
    if command == "supervised-repaired-candidate-rollback-checkpoint":
        from conscious_agent.supervised_repaired_candidate_rollback_checkpoint import build_supervised_repaired_candidate_rollback_checkpoint
        report = build_supervised_repaired_candidate_rollback_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "long-session-multi-day-soak-checkpoint":
        from conscious_agent.long_session_multi_day_soak_checkpoint import build_long_session_multi_day_soak_checkpoint
        report = build_long_session_multi_day_soak_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "operator-reviewed-soak-progression-checkpoint":
        from conscious_agent.operator_reviewed_soak_progression_checkpoint import build_operator_reviewed_soak_progression_checkpoint
        report = build_operator_reviewed_soak_progression_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "long-session-multi-day-soak-consolidated-checkpoint":
        from conscious_agent.long_session_multi_day_soak_consolidated_checkpoint import build_long_session_multi_day_soak_consolidated_checkpoint
        report = build_long_session_multi_day_soak_consolidated_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "adversarial-privacy-authority-replay-recovery-checkpoint":
        from conscious_agent.adversarial_privacy_authority_replay_recovery_checkpoint import build_adversarial_privacy_authority_replay_recovery_checkpoint
        report = build_adversarial_privacy_authority_replay_recovery_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "runtime-lifecycle-migration-checkpoint":
        from conscious_agent.runtime_lifecycle_migration_checkpoint import build_runtime_lifecycle_migration_checkpoint
        report = build_runtime_lifecycle_migration_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "runtime-lifecycle-application-review-checkpoint":
        from conscious_agent.runtime_lifecycle_application_review_checkpoint import build_runtime_lifecycle_application_review_checkpoint
        report = build_runtime_lifecycle_application_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "runtime-lifecycle-reliability-adversarial-checkpoint":
        from conscious_agent.runtime_lifecycle_reliability_adversarial_checkpoint import build_runtime_lifecycle_reliability_adversarial_checkpoint
        report = build_runtime_lifecycle_reliability_adversarial_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "runtime-lifecycle-checkpoint":
        from conscious_agent.runtime_lifecycle_checkpoint import build_runtime_lifecycle_checkpoint
        report = build_runtime_lifecycle_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "feature-freeze-architecture-consolidation-checkpoint":
        from conscious_agent.feature_freeze_architecture_consolidation_checkpoint import build_feature_freeze_architecture_consolidation_checkpoint
        report = build_feature_freeze_architecture_consolidation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "feature-freeze-consolidation-review-checkpoint":
        from conscious_agent.feature_freeze_consolidation_review_checkpoint import build_feature_freeze_consolidation_review_checkpoint
        report = build_feature_freeze_consolidation_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "feature-freeze-architecture-consolidated-checkpoint":
        from conscious_agent.feature_freeze_architecture_consolidated_checkpoint import build_feature_freeze_architecture_consolidated_checkpoint
        report = build_feature_freeze_architecture_consolidated_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "final-source-candidate-preparation-checkpoint":
        from conscious_agent.final_source_candidate_preparation_checkpoint import build_final_source_candidate_preparation_checkpoint
        report = build_final_source_candidate_preparation_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "final-candidate-review-checkpoint":
        from conscious_agent.final_candidate_review_checkpoint import build_final_candidate_review_checkpoint
        report = build_final_candidate_review_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "final-candidate-reliability-checkpoint":
        from conscious_agent.final_candidate_reliability_checkpoint import build_final_candidate_reliability_checkpoint
        report = build_final_candidate_reliability_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "final-source-candidate-checkpoint":
        from conscious_agent.final_source_candidate_checkpoint import build_final_source_candidate_checkpoint
        report = build_final_source_candidate_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "unified-experience-foundations-checkpoint":
        from conscious_agent.unified_experience_foundations_checkpoint import build_unified_experience_foundations_checkpoint
        report = build_unified_experience_foundations_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "unified-experience-navigation-checkpoint":
        from conscious_agent.unified_experience_navigation_checkpoint import build_unified_experience_navigation_checkpoint
        print(json.dumps(build_unified_experience_navigation_checkpoint(), sort_keys=True))
        return 0

    if command == "unified-experience-reliability-checkpoint":
        from conscious_agent.unified_experience_reliability_checkpoint import build_unified_experience_reliability_checkpoint
        print(json.dumps(build_unified_experience_reliability_checkpoint(), sort_keys=True))
        return 0

    if command == "unified-experience-checkpoint":
        from conscious_agent.unified_experience_checkpoint import build_unified_experience_checkpoint
        report = build_unified_experience_checkpoint()
        print(json.dumps(report, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "complete-campaign-development-loop-alpha-checkpoint":
        from conscious_agent.complete_campaign_development_loop_alpha_checkpoint import build_complete_campaign_development_loop_alpha_checkpoint
        report = build_complete_campaign_development_loop_alpha_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-repair-implementation-governance-checkpoint":
        from conscious_agent.supervised_sandbox_repair_implementation_governance_checkpoint import build_supervised_sandbox_repair_implementation_governance_checkpoint
        report = build_supervised_sandbox_repair_implementation_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-repair-implementation-intake-checkpoint":
        from conscious_agent.supervised_repair_implementation_intake_checkpoint import build_supervised_repair_implementation_intake_checkpoint
        report = build_supervised_repair_implementation_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-repair-execution-checkpoint":
        from conscious_agent.supervised_repair_execution_checkpoint import build_supervised_repair_execution_checkpoint
        report = build_supervised_repair_execution_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-change-deliberation-checkpoint":
        from conscious_agent.supervised_sandbox_change_deliberation_checkpoint import build_supervised_sandbox_change_deliberation_checkpoint
        report = build_supervised_sandbox_change_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-change-integration-checkpoint":
        from conscious_agent.supervised_sandbox_change_integration_checkpoint import build_supervised_sandbox_change_integration_checkpoint
        report = build_supervised_sandbox_change_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-sandbox-change-governance-checkpoint":
        from conscious_agent.supervised_sandbox_change_governance_checkpoint import build_supervised_sandbox_change_governance_checkpoint
        report = build_supervised_sandbox_change_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-test-plan-deliberation-checkpoint":
        from conscious_agent.supervised_test_plan_deliberation_checkpoint import build_supervised_test_plan_deliberation_checkpoint
        report = build_supervised_test_plan_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-test-plan-integration-checkpoint":
        from conscious_agent.supervised_test_plan_integration_checkpoint import build_supervised_test_plan_integration_checkpoint
        report = build_supervised_test_plan_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-test-planning-governance-checkpoint":
        from conscious_agent.supervised_test_plan_governance_checkpoint import build_supervised_test_plan_governance_checkpoint
        report = build_supervised_test_plan_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-specification-deliberation-checkpoint":
        from conscious_agent.supervised_specification_deliberation_checkpoint import build_supervised_specification_deliberation_checkpoint
        report = build_supervised_specification_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-specification-integration-checkpoint":
        from conscious_agent.supervised_specification_integration_checkpoint import build_supervised_specification_integration_checkpoint
        report = build_supervised_specification_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-specification-governance-checkpoint":
        from conscious_agent.supervised_specification_governance_checkpoint import build_supervised_specification_governance_checkpoint
        report = build_supervised_specification_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-development-proposal-intake-checkpoint":
        from conscious_agent.supervised_development_proposal_intake_checkpoint import build_supervised_development_proposal_intake_checkpoint
        report = build_supervised_development_proposal_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-development-proposal-deliberation-checkpoint":
        from conscious_agent.supervised_development_proposal_deliberation_checkpoint import build_supervised_development_proposal_deliberation_checkpoint
        report = build_supervised_development_proposal_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-development-proposal-integration-checkpoint":
        from conscious_agent.supervised_development_proposal_integration_checkpoint import build_supervised_development_proposal_integration_checkpoint
        report = build_supervised_development_proposal_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-development-proposal-governance-checkpoint":
        from conscious_agent.supervised_development_proposal_governance_checkpoint import build_supervised_development_proposal_governance_checkpoint
        report = build_supervised_development_proposal_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-deficiency-intake-checkpoint":
        from conscious_agent.supervised_deficiency_intake_checkpoint import build_supervised_deficiency_intake_checkpoint
        report = build_supervised_deficiency_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-deficiency-deliberation-checkpoint":
        from conscious_agent.supervised_deficiency_deliberation_checkpoint import build_supervised_deficiency_deliberation_checkpoint
        report = build_supervised_deficiency_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-deficiency-integration-checkpoint":
        from conscious_agent.supervised_deficiency_integration_checkpoint import build_supervised_deficiency_integration_checkpoint
        report = build_supervised_deficiency_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "supervised-deficiency-governance-checkpoint":
        from conscious_agent.supervised_deficiency_governance_checkpoint import build_supervised_deficiency_governance_checkpoint
        report = build_supervised_deficiency_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "prospective-planning-intake-checkpoint":
        from conscious_agent.prospective_planning_intake_checkpoint import build_prospective_planning_intake_checkpoint
        report = build_prospective_planning_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "prospective-planning-deliberation-checkpoint":
        from conscious_agent.prospective_planning_deliberation_checkpoint import build_prospective_planning_deliberation_checkpoint
        report = build_prospective_planning_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1
    if command == "prospective-planning-integration-checkpoint":
        from conscious_agent.prospective_planning_integration_checkpoint import build_prospective_planning_integration_checkpoint
        report = build_prospective_planning_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "prospective-planning-governance-checkpoint":
        from conscious_agent.prospective_planning_governance_checkpoint import build_prospective_planning_governance_checkpoint
        report = build_prospective_planning_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "internally-generated-goal-integration-checkpoint":
        from conscious_agent.internally_generated_goal_integration_checkpoint import build_internally_generated_goal_integration_checkpoint
        _print_json(build_internally_generated_goal_integration_checkpoint())
        return 0

    if command == "internally-generated-goal-deliberation-checkpoint":
        from conscious_agent.internally_generated_goal_deliberation_checkpoint import build_internally_generated_goal_deliberation_checkpoint
        report = build_internally_generated_goal_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "internally-generated-goal-governance-checkpoint":
        from conscious_agent.internally_generated_goal_governance_checkpoint import build_internally_generated_goal_governance_checkpoint
        report = build_internally_generated_goal_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "revisable-world-model-deliberation-checkpoint":
        from conscious_agent.revisable_world_model_deliberation_checkpoint import build_revisable_world_model_deliberation_checkpoint
        report = build_revisable_world_model_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "revisable-world-model-integration-checkpoint":
        from conscious_agent.revisable_world_model_integration_checkpoint import build_revisable_world_model_integration_checkpoint
        report = build_revisable_world_model_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "revisable-world-model-governance-checkpoint":
        from conscious_agent.revisable_world_model_governance_checkpoint import build_revisable_world_model_governance_checkpoint
        report = build_revisable_world_model_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "genuine-inquiry-governance-checkpoint":
        from conscious_agent.genuine_inquiry_governance_checkpoint import build_genuine_inquiry_governance_checkpoint
        report = build_genuine_inquiry_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "genuine-inquiry-intake-checkpoint":
        from conscious_agent.genuine_inquiry_intake_checkpoint import build_genuine_inquiry_intake_checkpoint
        report = build_genuine_inquiry_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "read-only-perception-intake-checkpoint":
        from conscious_agent.read_only_perception_intake_checkpoint import build_read_only_perception_intake_checkpoint
        print(json.dumps(build_read_only_perception_intake_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "read-only-perception-integration-checkpoint":
        from conscious_agent.read_only_perception_integration_checkpoint import build_read_only_perception_integration_checkpoint
        print(json.dumps(build_read_only_perception_integration_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "read-only-perception-deliberation-checkpoint":
        from conscious_agent.read_only_perception_deliberation_checkpoint import build_read_only_perception_deliberation_checkpoint
        report = build_read_only_perception_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-supported-revision-intake-checkpoint":
        from conscious_agent.reflection_supported_revision_intake_checkpoint import build_reflection_supported_revision_intake_checkpoint
        report = build_reflection_supported_revision_intake_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-supported-revision-integration-checkpoint":
        from conscious_agent.reflection_supported_revision_integration_checkpoint import build_reflection_supported_revision_integration_checkpoint
        report = build_reflection_supported_revision_integration_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-supported-revision-deliberation-checkpoint":
        from conscious_agent.reflection_supported_revision_deliberation_checkpoint import build_reflection_supported_revision_deliberation_checkpoint
        report = build_reflection_supported_revision_deliberation_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflection-supported-revision-governance-checkpoint":
        from conscious_agent.reflection_supported_revision_governance_checkpoint import build_reflection_supported_revision_governance_checkpoint
        report = build_reflection_supported_revision_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "continuous-thought-governance-checkpoint":
        from conscious_agent.continuous_thought_governance_checkpoint import build_continuous_thought_governance_checkpoint
        report = build_continuous_thought_governance_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "continuous-thought-integration-checkpoint":
        from conscious_agent.continuous_thought_integration_checkpoint import build_continuous_thought_integration_checkpoint
        report = build_continuous_thought_integration_checkpoint()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "continuous-thought-deliberation-checkpoint":
        from conscious_agent.continuous_thought_deliberation_checkpoint import build_continuous_thought_deliberation_checkpoint
        print(json.dumps(build_continuous_thought_deliberation_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "continuous-thought-intake-checkpoint":
        from conscious_agent.continuous_thought_intake_checkpoint import build_continuous_thought_intake_checkpoint
        print(json.dumps(build_continuous_thought_intake_checkpoint(), indent=2, sort_keys=True))
        return 0

    if command == "reflection-quality-governance-checkpoint":
        from conscious_agent.reflection_quality_governance_checkpoint import build_reflection_quality_governance_checkpoint
        report = build_reflection_quality_governance_checkpoint()
        print(json.dumps(report, indent=2 if getattr(args, "json", False) else None, sort_keys=True))
        return 0 if report.get("ok") else 1

    if command == "reflective-session-intake-checkpoint":
        from conscious_agent.reflective_session_intake_checkpoint import build_reflective_session_intake_checkpoint
        result = build_reflective_session_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-attention-salience-governance-checkpoint":
        from conscious_agent.reflective_attention_salience_governance_checkpoint import build_reflective_attention_salience_governance_checkpoint
        result = build_reflective_attention_salience_governance_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "objective-coherence-intake-checkpoint":
        from conscious_agent.objective_coherence_intake_checkpoint import build_objective_coherence_intake_checkpoint
        result = build_objective_coherence_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "objective-coherence-deliberation-checkpoint":
        from conscious_agent.objective_coherence_deliberation_checkpoint import build_objective_coherence_deliberation_checkpoint
        result = build_objective_coherence_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "goal-continuity-review-checkpoint":
        from conscious_agent.goal_continuity_review_checkpoint import build_goal_continuity_review_checkpoint
        result = build_goal_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "goal-coherence-long-horizon-objective-governance-checkpoint":
        from conscious_agent.goal_coherence_long_horizon_objective_governance_checkpoint import build_goal_coherence_long_horizon_objective_governance_checkpoint
        result = build_goal_coherence_long_horizon_objective_governance_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "self-model-integrity-intake-checkpoint":
        from conscious_agent.self_model_integrity_intake_checkpoint import build_self_model_integrity_intake_checkpoint
        result = build_self_model_integrity_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "self-model-revision-deliberation-checkpoint":
        from conscious_agent.self_model_revision_deliberation_checkpoint import build_self_model_revision_deliberation_checkpoint
        result = build_self_model_revision_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "self-model-continuity-review-checkpoint":
        from conscious_agent.self_model_continuity_review_checkpoint import build_self_model_continuity_review_checkpoint
        result = build_self_model_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "self-model-integrity-identity-claim-governance-checkpoint":
        from conscious_agent.self_model_integrity_identity_claim_governance_checkpoint import build_self_model_integrity_identity_claim_governance_checkpoint
        result = build_self_model_integrity_identity_claim_governance_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "epistemic-maintenance-belief-revision-governance-checkpoint":
        from conscious_agent.epistemic_maintenance_belief_revision_governance_checkpoint import build_epistemic_maintenance_belief_revision_governance_checkpoint
        result = build_epistemic_maintenance_belief_revision_governance_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "belief-continuity-review-checkpoint":
        from conscious_agent.belief_continuity_review_checkpoint import build_belief_continuity_review_checkpoint
        result = build_belief_continuity_review_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "belief-revision-deliberation-checkpoint":
        from conscious_agent.belief_revision_deliberation_checkpoint import build_belief_revision_deliberation_checkpoint
        result = build_belief_revision_deliberation_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "belief-reconsideration-intake-checkpoint":
        from conscious_agent.belief_reconsideration_intake_checkpoint import build_belief_reconsideration_intake_checkpoint
        result = build_belief_reconsideration_intake_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "reflective-temporal-continuity-prospective-memory-checkpoint":
        from conscious_agent.reflective_temporal_continuity_prospective_memory_checkpoint import build_reflective_temporal_continuity_prospective_memory_checkpoint
        result = build_reflective_temporal_continuity_prospective_memory_checkpoint()
        print(json.dumps(result, indent=2, sort_keys=True) if getattr(args, "json", False) else result.get("headline"))
        return 0 if result.get("ok") else 1

    if command == "prospective-memory-continuity-checkpoint":
        from conscious_agent.prospective_memory_continuity_checkpoint import build_prospective_memory_continuity_checkpoint
        payload = build_prospective_memory_continuity_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-homeostasis-sustainable-cognition-checkpoint":
        from conscious_agent.cognitive_homeostasis_sustainable_cognition_checkpoint import build_cognitive_homeostasis_sustainable_cognition_checkpoint
        payload = build_cognitive_homeostasis_sustainable_cognition_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-recovery-continuity-checkpoint":
        from conscious_agent.cognitive_recovery_continuity_checkpoint import build_cognitive_recovery_continuity_checkpoint
        payload = build_cognitive_recovery_continuity_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "cognitive-homeostasis-continuity-checkpoint":
        from conscious_agent.cognitive_homeostasis_continuity_checkpoint import build_cognitive_homeostasis_continuity_checkpoint
        payload = build_cognitive_homeostasis_continuity_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "reflective-planning-deliberative-choice-checkpoint":
        from conscious_agent.reflective_planning_deliberative_choice_checkpoint import build_reflective_planning_deliberative_choice_checkpoint
        payload = build_reflective_planning_deliberative_choice_checkpoint()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload.get("headline", payload.get("status", "")))
        return 0 if payload.get("ok") else 1

    if command == "persistent-identity-model":
        from conscious_agent.persistent_identity_model import build_persistent_identity_model_inspection
        payload = build_persistent_identity_model_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "identity-evidence-arbitration":
        from conscious_agent.identity_evidence_arbitration import build_identity_evidence_arbitration_inspection
        payload = build_identity_evidence_arbitration_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "self-model-continuity-checkpoint":
        from conscious_agent.self_model_continuity_checkpoint import build_self_model_continuity_checkpoint
        payload = build_self_model_continuity_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "identity-change-detection":
        from conscious_agent.identity_change_detection import build_identity_change_detection_inspection
        payload = build_identity_change_detection_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "self-model-revision":
        from conscious_agent.self_model_revision import build_self_model_revision_inspection
        payload = build_self_model_revision_inspection()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "identity-revision-checkpoint":
        from conscious_agent.identity_revision_checkpoint import build_identity_revision_checkpoint
        payload = build_identity_revision_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "identity-expression-lifecycle-checkpoint":
        from conscious_agent.identity_expression_lifecycle_checkpoint import build_identity_expression_lifecycle_checkpoint
        payload = build_identity_expression_lifecycle_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "persistent-self-model-checkpoint":
        from conscious_agent.persistent_self_model_checkpoint import build_persistent_self_model_checkpoint
        payload = build_persistent_self_model_checkpoint()
        print(json.dumps(payload, indent=2) if args.json else payload)
        return 0 if payload.get("ok") else 1
    if command == "native-reflection-evaluation":
        from conscious_agent.native_reflection_evaluation import NativeReflectionEvaluator
        payload = NativeReflectionEvaluator().evaluate(
            args.event_id, operator_confirmed=bool(args.confirm_native), max_cases=args.max_cases, max_total_ms=args.max_total_ms,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Native reflection evaluation: {payload.get('status', 'unknown')}")
            result = payload.get("result") or {}
            print(f"Completed cases: {result.get('completed_case_count', 0)} / {result.get('fixture_count', 0)}")
            print("No model was installed, pulled, replaced, or deleted. No action was authorized.")
        return 0 if payload.get("ok") else 1
    if command == "proactive-inbox":
        from conscious_agent.proactive_communication import ProactiveCommunicationStore
        store = ProactiveCommunicationStore()
        payload = {"ok": True, "queued": store.queued_messages(limit=20), "unread": store.unread_messages(limit=20), "authority_changed": False}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Queued proactive messages: {len(payload['queued'])}")
            print(f"Unread proactive messages: {len(payload['unread'])}")
            for row in payload["unread"]:
                print(f"- {row.get('subject') or row.get('message_type')}: {row.get('reason')}")
        return 0
    if command == "communication-control":
        from conscious_agent.proactive_communication import ProactiveCommunicationStore
        if args.quiet and args.allow:
            raise SystemExit("Choose either --quiet or --allow, not both.")
        if args.disable and args.enable:
            raise SystemExit("Choose either --disable or --enable, not both.")
        quiet = True if args.quiet else (False if args.allow else None)
        initiative_enabled = False if args.disable else (True if args.enable else None)
        payload = ProactiveCommunicationStore().set_preferences(
            args.event_id,
            frequency=args.frequency,
            quiet_indefinite=quiet,
            initiative_enabled=initiative_enabled,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            result = payload.get("result") or {}
            print(f"Communication frequency: {result.get('frequency', args.frequency or 'unchanged')}")
            print(f"Quiet: {result.get('quiet_indefinite', 'unchanged')}")
            print("Internal continuity was preserved; action authority was unchanged.")
        return 0
    if command == "startup-soak":
        forwarded = ["--runs", str(args.runs), "--timeout", str(args.timeout)]
        if args.include_provider_probe:
            forwarded.append("--include-provider-probe")
        if args.json:
            forwarded.append("--json")
        return _run(STARTUP_SOAK, *forwarded)
    if command == "messaging-soak":
        forwarded = ["--iterations", str(args.iterations)]
        if args.json:
            forwarded.append("--json")
        return _run(MESSAGING_SOAK, *forwarded)
    if command == "upgrade-migrate":
        forwarded = []
        if args.apply:
            forwarded.append("--apply")
        if args.json:
            forwarded.append("--json")
        return _run(UPGRADE_MIGRATE, *forwarded)
    if command == "verify":
        forwarded = ["--profile", "full" if args.full else "quick"]
        if args.verbose:
            forwarded.append("--verbose")
        if args.json:
            forwarded.append("--json")
        return _run(VERIFY, *forwarded)
    if command == "legacy":
        return _run(MAIN, *args.args)
    parser.error(f"Unsupported command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
