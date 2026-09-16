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


def install_package(name: str) -> None:
    pkg = adapter.package_area() / name
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
    require("experiment_review" in routing.bounded_action_explanation(projection),
            f"the_bounded_explanation_names_the_capability:{phrase[:40]}")

# An uninstalled package resolves to no capability rather than to a review that cannot run.
intent, grounding = project("Review G-NOT-INSTALLED independently.")
require(grounding.get("capability_id") != "experiment_review", "an_uninstalled_package_does_not_ground_a_review")
require(grounding.get("execution_state") == "not_executed", "an_uninstalled_package_executes_nothing")

# An unverified execution claim is still bounded back to the governed explanation.
projection = routing.build_natural_language_action_projection("Review G-INVAR independently.")
bounded = routing.bound_unverified_action_claim("I have completed the review of G-INVAR.", projection)
require(bounded != "I have completed the review of G-INVAR." and "experiment_review" in bounded,
        "an_unverified_completion_claim_is_replaced_by_the_governed_explanation")

# No review job exists anywhere after the whole suite: grounding never starts one.
require(not (RUNTIME / "research_jobs").exists(), "grounding_never_creates_a_review_job")

print(json.dumps({"suite": "v2731.10.0-conversation-path-review-routing", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
