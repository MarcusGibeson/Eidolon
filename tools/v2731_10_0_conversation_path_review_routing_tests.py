from __future__ import annotations

"""Grounding of the governed experiment review on the conversation path (spec 2.26).

Deterministic; no provider contact, no job and no detached process.  The conversational adapter (2.25) is reachable
from the command surface but was unreachable from ordinary conversation: question-shaped requests never consulted the
supervised router, and the three review intents resolved to no registered capability.  This proves the two
question-shaped phrasings now ground on the registered `experiment_review` capability, that an explicit review
command still grounds and still demands separate operator approval, that ordinary conversation about reviews and
experiments stays conversation, and that grounding remains a proposal: nothing executes, nothing mutates, and the
projection stays content free.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-10-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import experiment_review as er  # noqa: E402
import conversational_experiment_review as adapter  # noqa: E402
import natural_language_action_routing as routing  # noqa: E402

DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", "form=V1 item=A classification=unresolved\n")}


def install_package(name: str, root: Path | None = None) -> None:
    pkg = adapter.package_area(root) / name
    pkg.mkdir(parents=True, exist_ok=True)
    entries = []
    for n, (file_name, (role, text)) in enumerate(DOCS.items(), 1):
        (pkg / file_name).write_text(text, encoding="utf-8", newline="\n")
        entries.append({"doc_id": f"D{n}", "path": file_name, "role": role, "description": file_name,
                        "sha256": hashlib.sha256((pkg / file_name).read_bytes()).hexdigest()})
    (pkg / er.MANIFEST_NAME).write_text(json.dumps({"experiment_id": name, "title": f"{name} test experiment",
                                                    "task": "independent_review", "brief": "Review it.",
                                                    "documents": entries}), encoding="utf-8")


install_package("G-INVAR")
install_package("G-CAND2-refx")

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def project(text: str) -> tuple[dict, dict]:
    projection = routing.build_natural_language_action_projection(text)
    return dict(projection.get("intent") or {}), dict(projection.get("grounding") or {})


LIST_PHRASES = (
    "What experiments can you review?",
    "What experiments can you review? I'm looking for something like G-CAND2 and the like.",
    "Which experiment packages can you review?",
    "List the eligible experiment packages.",
)
STATUS_PHRASES = (
    "How is the review going?",
    "What is the status of the experiment review?",
    "Is the experiment review finished?",
)
START_PHRASES = (
    "Review G-INVAR independently.",
    "Please review G-CAND2-refx",
)
# Ordinary conversation that merely mentions reviewing or experiments must stay ordinary conversation.
CONVERSATION_PHRASES = (
    "What do you think about the experiment we ran?",
    "Tell me about your experiments in general.",
    "What can you do?",
    "Do you review your own work?",
)

intent, grounding = project("Confirm.")
require(intent.get("category") != "action_request", "a_confirmation_with_no_saved_proposal_is_not_an_action_request")
require(grounding.get("capability_id") != "experiment_review", "a_confirmation_with_no_saved_proposal_grounds_nothing")

for phrase in LIST_PHRASES + STATUS_PHRASES:
    intent, grounding = project(phrase)
    require(intent.get("category") == "action_request", f"question_shaped_review_request_reaches_the_router:{phrase[:40]}")
    require(grounding.get("grounding_status") == "matched", f"question_shaped_review_request_is_matched:{phrase[:40]}")
    require(grounding.get("capability_id") == "experiment_review", f"question_shaped_review_request_maps_to_the_capability:{phrase[:40]}")
    require(grounding.get("capability_registered") is True, f"the_capability_is_registered:{phrase[:40]}")

for phrase in START_PHRASES:
    intent, grounding = project(phrase)
    require(intent.get("category") == "action_request", f"an_explicit_review_command_is_an_action_request:{phrase[:40]}")
    require(grounding.get("capability_id") == "experiment_review", f"an_explicit_review_command_maps_to_the_capability:{phrase[:40]}")
    require(grounding.get("grounding_status") == "matched", f"an_explicit_review_command_is_matched:{phrase[:40]}")
    require(grounding.get("authority_required") is True
            and grounding.get("required_authority") == "separate_explicit_operator_approval",
            f"starting_a_review_still_requires_separate_operator_approval:{phrase[:40]}")

for phrase in CONVERSATION_PHRASES:
    intent, grounding = project(phrase)
    require(intent.get("category") != "action_request", f"ordinary_conversation_is_not_reclassified:{phrase[:40]}")
    require(grounding.get("capability_id") != "experiment_review", f"ordinary_conversation_does_not_ground_a_review:{phrase[:40]}")

# Ordinary sentences that merely use the verb "review" reach the router only as they already did before this change,
# and none of them grounds on the review capability.
for phrase in ("Can you review my thoughts on this?", "Please review what I just said", "Review the plan with me"):
    intent, grounding = project(phrase)
    require(grounding.get("capability_id") != "experiment_review", f"a_conversational_review_verb_does_not_ground_a_review:{phrase[:40]}")

# The narrower file-review capability keeps its own requests.
intent, grounding = project("review conscious_agent/memory.py")
require(grounding.get("capability_id") == "file_review", "a_file_review_request_still_grounds_on_file_review")

# Grounding is a proposal, never an execution, and carries no review content.
for phrase in LIST_PHRASES[:1] + STATUS_PHRASES[:1] + START_PHRASES[:1]:
    projection = routing.build_natural_language_action_projection(phrase)
    grounding = dict(projection.get("grounding") or {})
    public = routing.natural_language_action_public_projection(projection)
    require(grounding.get("execution_state") == "not_executed", f"nothing_executes_on_the_conversation_path:{phrase[:40]}")
    require(grounding.get("approval_state") == "not_created" and grounding.get("authorization_state") == "not_granted",
            f"no_approval_and_no_authorization_are_inferred:{phrase[:40]}")
    require(grounding.get("runtime_mutated") is False and grounding.get("source_modified") is False
            and grounding.get("provider_contacted") is False, f"grounding_mutates_nothing:{phrase[:40]}")
    require(grounding.get("authoritative_execution_receipt_present") is False, f"grounding_claims_no_receipt:{phrase[:40]}")
    require(routing.action_projection_contains_private_fields(public) is False, f"the_public_projection_stays_content_free:{phrase[:40]}")
    require(routing.bounded_action_explanation(projection).strip() != "",
            f"the_bounded_explanation_answers_the_request:{phrase[:40]}")

# The listing the conversation receives is the installed package ids, bounded and content free.
INSTALLED = ["G-CAND2-refx", "G-INVAR"]
for phrase in LIST_PHRASES[:1] + STATUS_PHRASES[:1] + START_PHRASES[:1]:
    projection = routing.build_natural_language_action_projection(phrase)
    grounding = dict(projection.get("grounding") or {})
    targets = list(grounding.get("available_review_targets") or [])
    require(targets == INSTALLED, f"the_conversation_receives_the_installed_package_ids:{phrase[:40]}")
    require(all(not set(name) & set("/\\") for name in targets), f"a_target_is_never_a_path:{phrase[:40]}")
    require(routing.action_projection_contains_private_fields(
        routing.natural_language_action_public_projection(projection)) is False,
        f"the_projection_with_targets_stays_content_free:{phrase[:40]}")
    explanation = routing.bounded_action_explanation(projection)
    if grounding.get("router_intent") == "experiment_review_list":
        require(all(name in explanation for name in INSTALLED), f"the_explanation_names_what_can_be_reviewed:{phrase[:40]}")

# Ordinary conversation is told nothing about what is installed.
for phrase in CONVERSATION_PHRASES:
    grounding = dict(routing.build_natural_language_action_projection(phrase).get("grounding") or {})
    require(not grounding.get("available_review_targets"), f"ordinary_conversation_receives_no_listing:{phrase[:40]}")

# The listing is bounded, whatever is installed.
OVERFULL = Path(tempfile.mkdtemp(prefix="eidolon-v2731-10-0-overfull-"))
for n in range(adapter.MAX_CONVERSATION_TARGETS + 3):
    install_package(f"G-BOUND-{n:02d}", OVERFULL)
require(len(adapter.eligible_target_ids(OVERFULL)) == adapter.MAX_CONVERSATION_TARGETS, "the_listing_is_bounded")
require(adapter.eligible_target_ids(Path(tempfile.mkdtemp(prefix="eidolon-v2731-10-0-empty-"))) == (),
        "an_empty_package_area_lists_nothing")

# An uninstalled package resolves to no capability rather than to a review that cannot run.
intent, grounding = project("Review G-NOT-INSTALLED independently.")
require(grounding.get("capability_id") != "experiment_review", "an_uninstalled_package_does_not_ground_a_review")
require(grounding.get("execution_state") == "not_executed", "an_uninstalled_package_executes_nothing")

# An unverified execution claim is still bounded back to the governed explanation.
projection = routing.build_natural_language_action_projection("Review G-INVAR independently.")
bounded = routing.bound_unverified_action_claim("I have completed the review of G-INVAR.", projection)
require(bounded != "I have completed the review of G-INVAR." and "Nothing has started" in bounded,
        "an_unverified_completion_claim_is_replaced_by_the_governed_explanation")

# Each review request gets its own answer. One paragraph reused across turns is squashed by the conversation's own
# repetition guard, which replaced Marcus's second request with "I repeated my previous response".
from conversation_target_continuity import _similarity  # noqa: E402

ANSWERS = {}
for phrase, label in (("What experiments can you review?", "list"), ("Review G-INVAR independently.", "start"),
                      ("How is the review going?", "status")):
    ANSWERS[label] = routing.bounded_action_explanation(routing.build_natural_language_action_projection(phrase))
require("G-INVAR" in ANSWERS["start"] and "Nothing has started" in ANSWERS["start"],
        "the_start_answer_names_the_requested_package_and_starts_nothing")
require(all(name in ANSWERS["list"] for name in INSTALLED), "the_list_answer_names_what_is_installed")
require("no job to report" in ANSWERS["status"], "the_status_answer_reports_no_job_when_none_has_run")
for left in ANSWERS:
    for right in ANSWERS:
        if left >= right:
            continue
        jaccard, ratio = _similarity(ANSWERS[left], ANSWERS[right])
        require(not (jaccard >= 0.72 and ratio >= 0.86), f"two_review_answers_are_not_one_repeated_paragraph:{left}_{right}")
for label, answer in ANSWERS.items():
    require(not routing._PAST_EXECUTION_CLAIM.search(answer), f"no_review_answer_claims_a_review_ran:{label}")

# The guard itself, on the path where it runs: asking to review one package after asking what is reviewable must not
# come back as "I repeated my previous response".
from conversation_target_continuity import enforce_conversation_target_output  # noqa: E402

history = [{"user_message": "What experiments can you review?", "assistant_response": ANSWERS["list"]}]
for label in ("start", "status"):
    out, diagnostics = enforce_conversation_target_output(ANSWERS[label], None, history, casual_fast_path=True)
    require(diagnostics.get("whole_response_replaced") is False, f"the_repetition_guard_does_not_squash_the_answer:{label}")
    require(out == ANSWERS[label], f"the_answer_reaches_the_operator_unchanged:{label}")

# No review job exists anywhere after the whole suite: grounding never starts one.
require(not (RUNTIME / "research_jobs").exists(), "grounding_never_creates_a_review_job")

# A review request becomes one saved proposal, and a confirmation resolves against that same saved action.
import chat_action_router as router  # noqa: E402

start_grounding = dict(routing.build_natural_language_action_projection("Review G-INVAR independently.").get("grounding") or {})
action_id = str(start_grounding.get("review_action_id") or "")
require(action_id != "", "a_review_request_is_saved_as_a_governed_proposal")
require(start_grounding.get("review_proposal_persisted") is True, "grounding_reports_that_it_saved_a_proposal")
require(dict(routing.build_natural_language_action_projection("What experiments can you review?").get("grounding") or {})
        .get("review_proposal_persisted") in (False, None), "listing_saves_no_proposal")
saved = router.load_chat_action(action_id) or {}
require(str(saved.get("intent") or "") == "experiment_review_start", "the_saved_proposal_is_the_review_start")
require(str(saved.get("status") or "") == "proposed", "the_saved_proposal_is_waiting_not_running")
require(str((saved.get("function_args") or {}).get("package_id") or "") == "G-INVAR", "the_saved_proposal_names_the_package")

again = dict(routing.build_natural_language_action_projection("Review G-INVAR independently.").get("grounding") or {})
require(str(again.get("review_action_id") or "") == action_id, "grounding_the_same_request_twice_saves_one_proposal")
proposals = [row for row in router.list_chat_actions(include_closed=True)
             if str(row.get("intent") or "") == "experiment_review_start"
             and str((row.get("function_args") or {}).get("package_id") or "") == "G-INVAR"]
require(len(proposals) == 1, "no_duplicate_review_proposal_is_created")

# A confirmation resolves against the most recent proposal still waiting, whichever package that is.
pending = router.pending_review_action() or {}
pending_id = str(pending.get("id") or "")
pending_package = str((pending.get("function_args") or {}).get("package_id") or "")
require(pending_id != "" and pending_package != "", "a_saved_proposal_is_waiting_to_run")

confirm_projection = routing.build_natural_language_action_projection("Confirm.")
confirm_grounding = dict(confirm_projection.get("grounding") or {})
require(dict(confirm_projection.get("intent") or {}).get("category") == "action_request", "a_confirmation_after_a_proposal_is_an_action_request")
require(confirm_grounding.get("capability_id") == "experiment_review", "a_confirmation_grounds_on_the_review_capability")
require(confirm_grounding.get("router_intent") == "experiment_review_confirm", "a_confirmation_routes_to_the_confirmation_control")
require(dict(confirm_grounding.get("pending_review_action") or {}).get("action_id") == pending_id,
        "the_confirmation_resolves_against_the_saved_proposal")
confirm_answer = routing.bounded_action_explanation(confirm_projection)
require(pending_id in confirm_answer and pending_package in confirm_answer,
        "the_confirmation_answer_names_the_proposal_and_package")
require("has not started" in confirm_answer, "the_confirmation_answer_says_nothing_has_started")
require(confirm_grounding.get("execution_state") == "not_executed", "confirming_executes_nothing")

# Confirming is still not an execution: no job exists anywhere after the whole confirmation flow.
require(not (RUNTIME / "research_jobs").exists(), "confirming_never_creates_a_review_job")

# A turn that is not an action request must not claim a review is running when none is.
ordinary_projection = routing.build_natural_language_action_projection("Thanks!")
fabricated = ("The read-only review of G-INVAR is now active. I am scanning the package structure and logic to "
              "identify any deviations or issues.")
bound_claim = routing.bound_unverified_action_claim(fabricated, ordinary_projection)
require(bound_claim != fabricated, "a_fabricated_review_execution_claim_is_replaced")
require("is running" not in bound_claim or "No independent review is running" in bound_claim,
        "the_replacement_reports_the_job_record")
for untouched in ("That sounds good, the invariance question is the interesting one.",
                  "I can review G-INVAR, G-CAND2-refx and G-REL-fixtures.",
                  "A review of a manuscript is usually slower than this."):
    require(routing.bound_unverified_action_claim(untouched, ordinary_projection) == untouched,
            f"ordinary_text_is_not_rewritten:{untouched[:36]}")

# The confirmation answer is its own answer, not a repeat of the proposal it confirms.
jaccard, ratio = _similarity(ANSWERS["start"], confirm_answer)
require(not (jaccard >= 0.72 and ratio >= 0.86), "the_confirmation_answer_is_not_a_repeat_of_the_proposal")

print(json.dumps({"suite": "v2731.10.0-conversation-path-review-routing", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
