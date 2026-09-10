from __future__ import annotations

"""Focused v1500.9 daily-use routing and reflection regression checks."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from chat_action_router import propose_chat_action
from conversation_quality import classify_conversation_quality
from conversational_action_portal_v1104 import classify_conversation_action
from conversational_capability_boundary import (
    capability_boundary_receipt,
    is_supervised_capability_catalog_request,
)
from active_conversation_facts import resolve_active_conversation_facts
from conversation_target_continuity import build_conversation_target_projection, enforce_conversation_target_output
from mixed_intent_action_presentation import present_mixed_intent_action_response
from natural_conversation_quality_runtime import build_natural_conversation_quality_runtime_profile

passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


reflection = (
    "Be specific. What can you do now that you couldn't do before, "
    "and what still frustrates you about your limitations?"
)
reflection_variants = (
    reflection,
    "What can you do now that you could not do before?",
    "How do you feel about your own progress and what can you do better now?",
    "What have you learned, what can you do now, and what do you still struggle with?",
    "What can you do compared to before, and what do you wish you could do?",
)
for index, message in enumerate(reflection_variants, start=1):
    check(f"reflective capability wording stays conversational {index}", not is_supervised_capability_catalog_request(message))
    quality = classify_conversation_quality(message)
    check(f"reflection is not explicit operator work {index}", quality.explicit_operator_request is False, quality.receipt_metrics())
    portal = classify_conversation_action(message)
    check(f"portal does not create action candidate {index}", portal["classification"] == "conversation", portal)
    action = propose_chat_action(message, save=False)
    check(f"router returns conversation-only result {index}", action["intent"] == "conversation_only", action)

grounded = resolve_active_conversation_facts(reflection, ())
check("self-capability reflection receives grounded project answer", grounded.state == "direct_self_reflection", grounded)
check("grounded answer names supervised development cycle", "supervised development cycle" in grounded.response, grounded.response)
check("grounded answer names real remaining limitations", "conversation and memory continuity" in grounded.response, grounded.response)
check("grounded answer avoids generic training biography", all(term not in grounded.response.lower() for term in ("knowledge base", "trained on", "latest developments")), grounded.response)

milestone_variants = (
    "What specifically became possible at v1500 that makes it different from our earlier milestones?",
    "What makes reaching v1500 meaningful for us?",
    "What did v1500 enable?",
    "Why is v1500 different?",
)
for index, message in enumerate(milestone_variants, start=1):
    milestone = resolve_active_conversation_facts(message, ())
    check(f"v1500 milestone wording is grounded {index}", milestone.state == "grounded_project_milestone", milestone)
    check(f"v1500 milestone names isolated implementation {index}", "implement it in an isolated workspace" in milestone.response, milestone.response)
    check(f"v1500 milestone preserves operator authority {index}", "retain installation and promotion authority" in milestone.response, milestone.response)
    check(f"v1500 milestone avoids generic marketing claims {index}", all(term not in milestone.response.lower() for term in ("knowledge base", "personalized and nuanced", "wider range of topics")), milestone.response)

responsibility_prompt = (
    "Don't give me a general reassurance or make this a shared responsibility. "
    "Answer personally: why does it matter to you when your mistake makes me feel unheard?"
)
responsibility_projection = build_conversation_target_projection(responsibility_prompt, ())
check("negative relational constraint is classified as correction", responsibility_projection["policy"]["correction"] is True, responsibility_projection)
check("shared-responsibility rejection is explicit", responsibility_projection["policy"]["reject_shared_responsibility"] is True, responsibility_projection)
constrained, constrained_diag = enforce_conversation_target_output(
    "It matters because I want our conversations to be meaningful and for you to feel heard. Let's find a way to make this work better together.",
    responsibility_projection,
    ({"user_message": "Why?", "assistant_response": "A different prior answer."},),
    casual_fast_path=True,
)
check("contradictory collaborative closing is removed", "together" not in constrained.lower() and "let's" not in constrained.lower(), constrained)
check("personal substantive answer is preserved", constrained.startswith("It matters because"), constrained)
check("constraint enforcement adds no provider request", constrained_diag["provider_request_added"] is False, constrained_diag)

repair_history = (
    {
        "user_message": "How do you feel about your progress?",
        "assistant_response": (
            "What still frustrates me is losing the conversational target or repeating a polished "
            "answer instead of responding to you."
        ),
    },
    {
        "user_message": "Why does that matter?",
        "assistant_response": "I want you to feel heard when we talk.",
    },
)
specific_prompt = "Be precise: what did you do that caused me to feel unheard?"
specific_projection = build_conversation_target_projection(specific_prompt, repair_history)
check("specific prior-mistake question is recognized", specific_projection["policy"]["specific_mistake_query"] is True, specific_projection)
check("repair subject retains lost target", "lost_target" in specific_projection["repair_subjects"], specific_projection)
check("repair subject retains repeated answer", "repeated_answer" in specific_projection["repair_subjects"], specific_projection)
generic_mistake, generic_diag = enforce_conversation_target_output(
    (
        "During our conversation, if my response didn't fully address or acknowledge your feelings, "
        "it might have felt like I wasn't listening closely enough."
    ),
    specific_projection,
    repair_history,
    casual_fast_path=True,
)
check("generic hypothetical mistake answer is grounded", "losing track of your current question" in generic_mistake, generic_mistake)
check("grounded mistake answer names repeated answers", "repeated answers" in generic_mistake, generic_mistake)
check("grounding reports bounded enforcement", generic_diag["grounded_repair_applied"] is True, generic_diag)
check("repair diagnostics contain no transcript text", all(term not in json.dumps(generic_diag) for term in ("feel unheard", "losing track", "repeated answers")), generic_diag)
check("repair grounding adds no provider request", generic_diag["provider_request_added"] is False, generic_diag)

present_stakes = build_natural_conversation_quality_runtime_profile(
    "Be specific to what is happening between us today, not general advice. Why does it matter to me right now?",
    repair_history,
    emotional=True,
)
present_stakes_guidance = " ".join(present_stakes.prompt_lines()).lower()
check("present-stakes follow-up requires attributable grounding", present_stakes.present_stakes_grounding_required, present_stakes.public_summary())
check("present-stakes guidance requires a current circumstance", "attributable current circumstance" in present_stakes_guidance, present_stakes_guidance)
check("present-stakes guidance rejects generic emotional advice", "do not substitute generic advice" in present_stakes_guidance, present_stakes_guidance)
ordinary_why = build_natural_conversation_quality_runtime_profile(
    "Why does sleep matter for memory?",
    repair_history,
)
check("ordinary why question does not trigger present-stakes contract", ordinary_why.present_stakes_grounding_required is False, ordinary_why.public_summary())

present_stakes_history = (
    {
        "user_message": (
            "Earlier I said I was worn out but proud of reaching a milestone. "
            "We got distracted by repeated coding failures. What do you think I was feeling?"
        ),
        "assistant_response": "You sounded accomplished and frustrated.",
    },
)
present_stakes_projection = build_conversation_target_projection(
    "Be specific to what is happening between us today. Why does that matter to me right now?",
    present_stakes_history,
)
generic_present_stakes, generic_present_stakes_diag = enforce_conversation_target_output(
    (
        "It matters because we're discussing your feelings about the milestone and coding challenges. "
        "Reflecting on these experiences can help you understand how you're handling success and setbacks. "
        "This awareness might help you celebrate achievements and approach future issues with a clearer mindset."
    ),
    present_stakes_projection,
    present_stakes_history,
    casual_fast_path=True,
)
check("generic present-stakes advice is replaced", generic_present_stakes_diag["present_stakes_grounding_applied"] is True, generic_present_stakes_diag)
check("replacement cites attributable current circumstances", "worn out but proud" in generic_present_stakes and "coding failures" in generic_present_stakes, generic_present_stakes)
check("replacement shifts evidence into companion voice", "you were worn out but proud" in generic_present_stakes.lower() and "we got distracted" in generic_present_stakes.lower(), generic_present_stakes)
check("replacement explains the conversational stake", "what you needed from this conversation" in generic_present_stakes, generic_present_stakes)
check("replacement removes generic self-help language", all(term not in generic_present_stakes.lower() for term in ("reflecting on", "this awareness", "clearer mindset")), generic_present_stakes)
check("replacement avoids evidence-receipt phrasing", all(term not in generic_present_stakes.lower() for term in ("you told me", "those are the circumstances", '"')), generic_present_stakes)
check("present-stakes diagnostics remain content-free", all(term not in json.dumps(generic_present_stakes_diag).lower() for term in ("worn out", "coding failures", "milestone")), generic_present_stakes_diag)

work_history = (
    {
        "user_message": "I felt relieved after my interview. Then your reply changed the subject.",
        "assistant_response": "That sounds important.",
    },
)
work_projection = build_conversation_target_projection(
    "Why does that matter to me right now?",
    work_history,
)
work_grounded, work_diag = enforce_conversation_target_output(
    "Reflecting on your feelings can help you understand the experience and find a clearer mindset.",
    work_projection,
    work_history,
    casual_fast_path=True,
)
check("unrelated work scenario is grounded", work_diag["present_stakes_grounding_applied"] is True and "you felt relieved" in work_grounded.lower(), work_grounded)
check("references to Eidolon shift into first person", "my reply changed the subject" in work_grounded.lower(), work_grounded)

specific_present_answer = "It matters because today you wanted me to recognize how much finishing the move cost you, and changing subjects made you feel dismissed."
specific_unchanged, specific_diag = enforce_conversation_target_output(
    specific_present_answer,
    present_stakes_projection,
    present_stakes_history,
    casual_fast_path=True,
)
check("naturally grounded provider answer remains unchanged", specific_unchanged == specific_present_answer and specific_diag["present_stakes_grounding_applied"] is False, specific_diag)

receipt_text = (
    "I ran the requested supervised read-only action and its receipt confirms successful completion. "
    "Action ID: action-test. The verified diagnostic status was WARN."
)
mixed_action_response, mixed_action_diag = present_mixed_intent_action_response(
    "I'm still pretty tired, but while we talk, please run a read-only system health check and tell me what you actually find.",
    receipt_text,
)
check("mixed action retains fatigue acknowledgement", mixed_action_response.startswith("I hear that you're tired."), mixed_action_response)
check("mixed action preserves receipt-derived result", receipt_text in mixed_action_response, mixed_action_response)
check("mixed action acknowledgement adds no provider request", mixed_action_diag["provider_request_added"] is False, mixed_action_diag)
check("mixed action acknowledgement grants no authority", mixed_action_diag["authority_granted"] is False, mixed_action_diag)
check("mixed action diagnostics remain content-free", "tired" not in json.dumps(mixed_action_diag), mixed_action_diag)
action_only_response, action_only_diag = present_mixed_intent_action_response(
    "Run a read-only system health check.", receipt_text,
)
check("action-only receipt response remains unchanged", action_only_response == receipt_text, action_only_response)
check("action-only turn adds no acknowledgement", action_only_diag["acknowledgement_added"] is False, action_only_diag)

dashboard_runtime = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
check("mixed-intent presentation integrated in both dashboard paths", dashboard_runtime.count("present_mixed_intent_action_response(message, response)") == 2)

repeated_diagnostic_requests = (
    "I'm worn out from testing. Please run one more read-only diagnostic check and report only what its receipt verifies.",
    "Please run another diagnostic check.",
    "Run a fresh system health check.",
    "Run a new diagnostic check.",
)
for index, message in enumerate(repeated_diagnostic_requests, start=1):
    repeat_quality = classify_conversation_quality(message)
    check(f"quantified diagnostic command remains explicit {index}", repeat_quality.explicit_operator_request is True, repeat_quality.receipt_metrics())
    repeat_action = propose_chat_action(message, save=False)
    check(f"quantified diagnostic command maps to diagnostics {index}", repeat_action["intent"] == "run_diagnostics", repeat_action)
    check(f"quantified diagnostic command remains direct low risk {index}", repeat_action["execution_mode"] == "direct_command" and repeat_action["risk_level"] == "low", repeat_action)

action_boundary_history = (
    {
        "user_message": "What part of that process should you handle, and what part should remain mine?",
        "assistant_response": "My role is to propose improvements, test them in isolation, and present the results for your review. You retain final approval.",
        "continuity_lane": "ordinary",
    },
    {
        "user_message": "Please run a read-only system health check.",
        "assistant_response": "The verified diagnostic status was WARN.",
        "continuity_lane": "operator",
        "action_status_summary": "Run diagnostics completed.",
    },
    {
        "user_message": "It would be convenient if diagnostics ran automatically, but do not do that now.",
        "assistant_response": "That could be convenient as an operator-controlled option.",
        "continuity_lane": "ordinary",
    },
)
boundary_return = resolve_active_conversation_facts(
    "Before we started running diagnostics, what were we discussing?",
    action_boundary_history,
)
check("pre-action topic uses governed lane boundary", boundary_return.state == "grounded_action_boundary_return", boundary_return)
check("pre-action topic restores development roles", "propose and verify changes in isolation" in boundary_return.response, boundary_return.response)
check("pre-action topic preserves operator final approval", "retain final approval" in boundary_return.response, boundary_return.response)
check("pre-action topic ignores later diagnostics wish", "automatically" not in boundary_return.response.lower(), boundary_return.response)

catalog_requests = (
    "What can you do?",
    "What can you do through chat?",
    "Which capabilities do you have?",
    "What supervised actions can you do?",
    "Which supervised actions are available?",
)
for index, message in enumerate(catalog_requests, start=1):
    check(f"explicit tool catalog remains recognized {index}", is_supervised_capability_catalog_request(message))
    quality = classify_conversation_quality(message)
    check(f"catalog remains explicit operator request {index}", quality.explicit_operator_request is True, quality.receipt_metrics())
    action = propose_chat_action(message, save=False)
    check(f"catalog still returns supervised capabilities {index}", action["intent"] == "supervised_capabilities", action)

diagnostics = classify_conversation_quality("Run a system health check.")
check("unrelated explicit diagnostics routing is preserved", diagnostics.explicit_operator_request is True, diagnostics.receipt_metrics())

receipt = capability_boundary_receipt(reflection)
serialized = json.dumps(receipt, sort_keys=True)
check("boundary receipt records reflection structurally", receipt["reflective_context"] is True and receipt["catalog_request"] is False, receipt)
check("boundary receipt remains content-free", all(value not in serialized for value in ("frustrates", "limitations", "before")), serialized)
check("boundary grants no authority or provider contact", receipt["authority_granted"] is False and receipt["provider_contacted"] is False, receipt)

verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
check("v1500.9 suite registered exactly once", verifier.count("v1500_9_integrated_daily_use_conversation_tests.py") == 1)
check("full verifier has an explicit bounded stage set", "FULL_STAGE_NAME_MARKERS =" in verifier)
check("full verifier uses profile stage selection", "stage_selected_for_profile(profile, name)" in verifier)
check("segmented verifier remains the broad history boundary", "segmented_release_verify.py" in verifier)

from release_verify import stage_selected_for_profile

check("current corrective suite remains in full", stage_selected_for_profile("full", "corrective-suite"))
check("current native conversation integration remains in full", stage_selected_for_profile("full", "native-conversation-validation-fixtures"))
check("old direct stage is excluded from monolithic full", not stage_selected_for_profile("full", "v1182.9-supervised-sandbox-testing-repair-checkpoint"))
check("quick Windows budget reflects measured host variance", 'performance_budget_seconds = 540 if profile == "quick"' in verifier)

import tempfile
from pathlib import Path
import runtime_data_migration
from launch_environment import prepare_ordinary_launch_environment

with tempfile.TemporaryDirectory(prefix="eidolon-v1500-9-launch-") as temporary:
    temporary_root = Path(temporary)
    source_root = temporary_root / "source"
    (source_root / "data").mkdir(parents=True)
    (source_root / "data" / "legacy.json").write_text("{}", encoding="utf-8")
    local_app_data = temporary_root / "local"
    external_runtime = local_app_data / "Eidolon" / "runtime"
    external_runtime.mkdir(parents=True)
    (external_runtime / "existing.json").write_text("{}", encoding="utf-8")
    original_preview = runtime_data_migration.preview_runtime_data_migration
    runtime_data_migration.preview_runtime_data_migration = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy scan should be skipped"))
    try:
        launch = prepare_ordinary_launch_environment(
            source_root,
            environment={"LOCALAPPDATA": str(local_app_data), "USERPROFILE": str(temporary_root)},
            platform_name="windows",
        )
    finally:
        runtime_data_migration.preview_runtime_data_migration = original_preview
    check("populated external runtime skips legacy inventory scan", launch["status"] == "existing_external_runtime_preserved", launch)
    check("fast launch path does not migrate or overwrite runtime", launch["automatic_migration"] is False and launch["external_runtime_overwritten"] is False, launch)

print({
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.9-integrated-daily-use-conversation",
    "provider_contacted": False,
    "runtime_mutated": False,
    "authority_granted": False,
})
if failed:
    raise SystemExit(1)
