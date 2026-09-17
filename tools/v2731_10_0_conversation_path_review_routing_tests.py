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

# Two proposals are waiting by now, so a bare confirmation must not guess between them.
waiting = router.pending_confirmable_actions()
require(len(waiting) >= 2, "more_than_one_proposal_is_waiting")
ambiguous_projection = routing.build_natural_language_action_projection("Confirm.")
ambiguous_grounding = dict(ambiguous_projection.get("grounding") or {})
require(ambiguous_grounding.get("router_intent") == "experiment_review_confirm_ambiguous",
        "a_bare_confirmation_with_several_waiting_is_ambiguous")
ambiguous_answer = routing.bounded_action_explanation(ambiguous_projection)
require("G-INVAR" in ambiguous_answer and "G-CAND2-refx" in ambiguous_answer,
        "the_ambiguous_answer_names_every_waiting_proposal")
require(routing.apply_confirmed_execution(ambiguous_projection)["grounding"].get("execution_state") == "not_executed",
        "an_ambiguous_confirmation_runs_nothing")
require(not (RUNTIME / "research_jobs").exists(), "an_ambiguous_confirmation_creates_no_job")

# Naming the package resolves it, and a name that matches nothing runs nothing.
unknown_projection = routing.build_natural_language_action_projection("Confirm G-NOTHING")
require(dict(unknown_projection.get("grounding") or {}).get("router_intent") == "experiment_review_confirm_ambiguous",
        "a_confirmation_naming_nothing_waiting_resolves_nothing")
require(routing.apply_confirmed_execution(unknown_projection)["grounding"].get("execution_state") == "not_executed",
        "a_confirmation_naming_nothing_waiting_runs_nothing")

confirm_projection = routing.build_natural_language_action_projection("Confirm G-INVAR")
confirm_grounding = dict(confirm_projection.get("grounding") or {})
require(dict(confirm_projection.get("intent") or {}).get("category") == "action_request",
        "a_named_confirmation_is_an_action_request")
require(confirm_grounding.get("capability_id") == "experiment_review", "a_confirmation_grounds_on_the_review_capability")
require(confirm_grounding.get("router_intent") == "experiment_review_confirm", "a_named_confirmation_resolves_to_one_proposal")
require(dict(confirm_grounding.get("pending_review_action") or {}).get("action_id") == action_id,
        "the_confirmation_resolves_to_the_named_package")
require(confirm_grounding.get("execution_state") == "not_executed", "grounding_a_confirmation_still_executes_nothing")
require(not (RUNTIME / "research_jobs").exists(), "grounding_a_confirmation_creates_no_job")

# Asking for the same package again, phrased differently, is the same proposal rather than a second one.
# A trailing period was enough to stack a duplicate and make both resolution branches contradict themselves.
for phrasing in ("Review G-INVAR independently", "review G-INVAR", "Please review G-INVAR."):
    repeat = dict(routing.build_natural_language_action_projection(phrasing).get("grounding") or {})
    require(str(repeat.get("review_action_id") or "") == action_id,
            f"a_rephrased_request_reuses_the_saved_proposal:{phrasing[:34]}")
g_invar_records = [row for row in router.pending_confirmable_actions()
                   if str((row.get("function_args") or {}).get("package_id") or "") == "G-INVAR"]
require(len(g_invar_records) == 1, "rephrasing_never_stacks_a_second_proposal")

# Records that already stacked up for one target still resolve: they are one intent, and the newest wins.
duplicate = router.propose_chat_action("Review G-INVAR independently", save=True, save_unknown=False,
                                       deduplication_key="v2731-10-0-forced-duplicate")
duplicate_id = str(duplicate.get("id") or "")
require(duplicate_id != "" and duplicate_id != action_id, "a_duplicate_record_exists_for_the_test")
state, resolved, _ = router.resolve_confirmation("confirm G-INVAR")
require(state == "one" and str((resolved or {}).get("id") or "") == duplicate_id,
        "a_named_confirmation_with_duplicates_resolves_to_the_newest")
require(router.resolve_confirmation("confirm G-INVAR.")[0] == "one", "trailing_punctuation_resolves_the_same_way")

# Genuine ambiguity is still two different targets, and it names them both.
require(router.resolve_confirmation("confirm")[0] == "ambiguous", "two_different_targets_are_still_ambiguous")
ambiguous_again = routing.bounded_action_explanation(routing.build_natural_language_action_projection("Confirm."))
require("G-INVAR" in ambiguous_again and "G-CAND2-refx" in ambiguous_again,
        "the_ambiguous_answer_still_names_both_targets")

# Only the live turn runs it, and it runs exactly once.
adapter.SPAWN = lambda argv, cwd, env: 4242
adapter.ALIVE = lambda pid: pid == 4242
executed = routing.apply_confirmed_execution(routing.build_natural_language_action_projection("Confirm G-INVAR"))
executed_grounding = dict(executed.get("grounding") or {})
receipt = dict(executed_grounding.get("confirmed_execution") or {})
require(receipt.get("ok") is True, "the_confirmed_proposal_runs_on_the_live_turn")
require(executed_grounding.get("execution_state") == "started", "the_projection_records_that_it_started")
require(str(receipt.get("job_id") or "") != "", "the_receipt_carries_the_job_id")
job_files = sorted((RUNTIME / "research_jobs").glob("job_*.json"))
require(len(job_files) == 1, "confirming_starts_exactly_one_job")
started_answer = routing.bounded_action_explanation(executed)
require("G-INVAR" in started_answer and str(receipt.get("job_id")) in started_answer,
        "the_answer_reports_the_started_job")

# Two started reviews in one conversation must read as two statements, not as one repeated paragraph. A templated
# receipt differing only by package and job id scored 0.85 jaccard against the previous one, above the conversation's
# duplicate threshold, so a real start was replaced by "I repeated my previous response".
# Only one review runs at a time, so the first job must finish before a second can start. Its process is gone, which
# the adapter records as a failure rather than leaving a stuck job.
adapter.ALIVE = lambda pid: False
require((adapter.job_status(str(receipt.get("job_id"))) or {}).get("status") == "failed",
        "a_job_whose_process_ended_without_a_result_is_recorded_as_failed")
require(adapter.active_job() is None, "the_review_slot_is_free_again")
second = routing.apply_confirmed_execution(routing.build_natural_language_action_projection("Confirm G-CAND2-refx"))
second_receipt = dict(dict(second.get("grounding") or {}).get("confirmed_execution") or {})
require(second_receipt.get("ok") is True, "a_second_package_can_also_be_confirmed")
second_answer = routing.bounded_action_explanation(second)
require("G-CAND2-refx" in second_answer and str(second_receipt.get("job_id")) in second_answer,
        "the_second_answer_reports_its_own_package_and_job")
jaccard, ratio = _similarity(started_answer, second_answer)
require(not (jaccard >= 0.72 and ratio >= 0.86), "two_started_reviews_are_not_one_repeated_receipt")
out, diagnostics = enforce_conversation_target_output(
    second_answer, None, [{"user_message": "Confirm G-INVAR", "assistant_response": started_answer}],
    casual_fast_path=True)
require(diagnostics.get("whole_response_replaced") is False and out == second_answer,
        "the_guard_lets_a_second_started_review_through")
# Two reviews have now run, so the replay check below measures against the current set of jobs.
job_files = sorted((RUNTIME / "research_jobs").glob("job_*.json"))
require(len(job_files) == 2, "each_confirmed_review_started_exactly_one_job")

# A proposal that has run cannot run again: it is no longer waiting, and the runner refuses it before any executor.
# This is the guarantee, rather than the incidental one that a review was already occupying the single review slot.
executed_id = str(receipt.get("action_id") or "")
before_replay = sorted((RUNTIME / "research_jobs").glob("job_*.json"))
replayed = router.run_confirmed_action(executed_id)
require(replayed.get("ok") is False and replayed.get("refused") == "already_resolved",
        "an_executed_proposal_is_refused_when_it_is_confirmed_again")
require(sorted((RUNTIME / "research_jobs").glob("job_*.json")) == before_replay,
        "a_replayed_confirmation_starts_no_second_job")
require(str((router.load_chat_action(executed_id) or {}).get("status") or "") != "proposed",
        "an_executed_proposal_is_no_longer_waiting")

# The allowlist is the only route from a conversation turn to an executor.
require("experiment_review_start" in router.CONVERSATION_CONFIRMABLE_FUNCTIONS, "the_review_is_confirmable")
require(all(name.isidentifier() for name in router.CONVERSATION_CONFIRMABLE_FUNCTIONS), "the_allowlist_holds_function_names_only")
refused = router.run_confirmed_action("chat_action_does_not_exist")
require(refused.get("ok") is False and refused.get("refused") == "not_confirmable_from_conversation",
        "an_action_outside_the_allowlist_is_refused")
runtime_source = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
require(runtime_source.count("_apply_confirmed_execution(action_projection)") == 2,
        "the_live_turn_applies_the_confirmation_at_both_projection_sites")
require(runtime_source.count("execute_supervised_action(") == 0, "conversation_still_calls_no_supervised_executor")

# A turn that is not an action request must not claim a review is running when none is.
ordinary_projection = routing.build_natural_language_action_projection("Thanks!")
fabricated = ("The read-only review of G-INVAR is now active. I am scanning the package structure and logic to "
              "identify any deviations or issues.")
bound_claim = routing.bound_unverified_action_claim(fabricated, ordinary_projection)
require(bound_claim != fabricated, "a_fabricated_review_execution_claim_is_replaced")
known_jobs = {json.loads(f.read_text(encoding="utf-8")).get("job_id", "")
              for f in (RUNTIME / "research_jobs").glob("job_*.json")}
require(any(job_id and job_id in bound_claim for job_id in known_jobs)
        or "No independent review is running" in bound_claim,
        "the_replacement_reports_the_job_record")
for untouched in ("That sounds good, the invariance question is the interesting one.",
                  "I can review G-INVAR, G-CAND2-refx and G-REL-fixtures.",
                  "A review of a manuscript is usually slower than this."):
    require(routing.bound_unverified_action_claim(untouched, ordinary_projection) == untouched,
            f"ordinary_text_is_not_rewritten:{untouched[:36]}")

# The confirmation answer is its own answer, not a repeat of the proposal it confirms.
jaccard, ratio = _similarity(ANSWERS["start"], started_answer)
require(not (jaccard >= 0.72 and ratio >= 0.86), "the_confirmation_answer_is_not_a_repeat_of_the_proposal")

print(json.dumps({"suite": "v2731.10.0-conversation-path-review-routing", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
