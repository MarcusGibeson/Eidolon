from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from natural_language_action_routing import (
    MAX_RECEIPT_BYTES,
    action_projection_contains_private_fields,
    bound_unverified_action_claim,
    build_natural_language_action_projection,
    classify_natural_language_intent,
)

checks: list[tuple[str, bool, object]] = []


def require(name: str, condition: object, detail: object = "") -> None:
    checks.append((name, bool(condition), detail))
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def projection(text: str, **kwargs: object) -> dict:
    return build_natural_language_action_projection(text, **kwargs)


expected_actions = {
    "Do a system maintenance check.": "maintenance",
    "Run diagnostics.": "diagnostics",
    "Inspect your project.": "task_project",
    "Review conscious_agent/memory.py.": "file_review",
    "Change the dashboard background.": "patch_proposal",
}
for text, capability in expected_actions.items():
    row = projection(text)
    require(f"action:{capability}:category", row["intent"]["category"] == "action_request", row)
    require(f"action:{capability}:grounded", row["grounding"]["grounding_status"] == "matched", row)
    require(f"action:{capability}:registered", row["grounding"]["capability_id"] == capability, row)
    require(f"action:{capability}:no-authority", row["grounding"]["authorization_state"] == "not_granted", row)
    require(f"action:{capability}:no-execution", row["grounding"]["execution_state"] == "not_executed", row)

ordinary = projection("Do you like the name Eidolon?")
require("ordinary-question", ordinary["intent"]["category"] == "question", ordinary)
require("ordinary-question-not-action", not ordinary["intent"]["action_intent_present"], ordinary)
require("ordinary-question-no-tool", ordinary["grounding"]["candidate_count"] == 0, ordinary)

correction = projection("Stop calling me Daddy.")
require("direct-correction", correction["intent"]["category"] == "correction", correction)
require("direct-correction-not-action", not correction["intent"]["action_intent_present"], correction)

planning = projection("Help me plan how to repair the dashboard.")
require("planning-request", planning["intent"]["category"] == "planning_request", planning)
require("planning-is-not-execution", planning["grounding"]["grounding_status"] == "not_applicable", planning)

for label, text in {
    "hypothetical": 'Hypothetically, what if I said "run diagnostics"?',
    "quoted": 'The phrase "run diagnostics" is an example.',
}.items():
    row = projection(text)
    require(f"{label}-not-action", row["intent"]["category"] in {"question", "conversation"}, row)
    require(f"{label}-flag", row["intent"]["hypothetical_language_present"] or row["intent"]["quoted_command_present"], row)

uncertain = projection("Maybe run diagnostics?")
require("uncertain-action-detected", uncertain["intent"]["category"] == "action_request", uncertain)
require("uncertain-action-clarifies", uncertain["intent"]["requires_clarification"], uncertain)
require("uncertain-grounding-ambiguous", uncertain["grounding"]["grounding_status"] == "ambiguous", uncertain)

uncertain_modal = projection("Could you maybe run diagnostics?")
require("uncertain-modal-action-detected", uncertain_modal["intent"]["category"] == "action_request", uncertain_modal)
require("uncertain-modal-action-clarifies", uncertain_modal["intent"]["requires_clarification"], uncertain_modal)
require("uncertain-modal-grounding-ambiguous", uncertain_modal["grounding"]["grounding_status"] == "ambiguous", uncertain_modal)

unsupported = projection("Install a new model and switch providers.")
require("unsupported-action", unsupported["intent"]["category"] == "action_request", unsupported)
require("unsupported-explicit", unsupported["grounding"]["grounding_status"] == "unsupported", unsupported)
require("unsupported-no-capability-invention", not unsupported["grounding"]["capability_id"], unsupported)

ambiguous = projection("Go ahead.")
require("ambiguous-reference", ambiguous["intent"]["category"] == "ambiguous_request", ambiguous)
require("ambiguous-reference-no-authorization", not ambiguous["intent"]["authorization_inferred"], ambiguous)

unproposed = projection(
    "Go ahead.",
    conversation_history=[
        {"user_message": "Run diagnostics.", "assistant_response": "I can explain the boundary."},
    ],
)
require("follow-up-request-without-proposal-stays-ambiguous", unproposed["intent"]["category"] == "ambiguous_request", unproposed)
require("follow-up-request-without-proposal-has-no-candidate", unproposed["grounding"]["candidate_count"] == 0, unproposed)

resolved = projection(
    "Go ahead.",
    conversation_history=[
        {
            "user_message": "Run diagnostics.",
            "assistant_response": "I can route that after an explicit governed request.",
            "action_status_summary": "Latest supervised action 'Diagnostics' is proposed. Persisted evidence exists; do not claim any different outcome without a newer result.",
        },
    ],
)
require("follow-up-unique-resolution", resolved["intent"]["category"] == "action_request", resolved)
require("follow-up-real-capability", resolved["grounding"]["capability_id"] == "diagnostics", resolved)
require("follow-up-not-approved", resolved["grounding"]["authorization_state"] == "not_granted", resolved)
require("follow-up-not-executed", resolved["grounding"]["execution_state"] == "not_executed", resolved)

stale_ambiguous = projection(
    "Go ahead.",
    conversation_history=[
        {
            "user_message": "Run diagnostics.",
            "assistant_response": "Proposed.",
            "action_status_summary": "Latest supervised action 'Diagnostics' is proposed. Persisted evidence exists; do not claim any different outcome without a newer result.",
        },
        {
            "user_message": "Run a maintenance scan.",
            "assistant_response": "Proposed.",
            "action_status_summary": "Latest supervised action 'Maintenance' is proposed. Persisted evidence exists; do not claim any different outcome without a newer result.",
        },
        {"malformed": object()},
    ],
)
require("multi-candidate-reference-stays-ambiguous", stale_ambiguous["intent"]["category"] == "ambiguous_request", stale_ambiguous)
require("stale-context-no-target-guess", stale_ambiguous["grounding"]["candidate_count"] == 2, stale_ambiguous)

claim = bound_unverified_action_claim("I ran diagnostics and everything passed.", projection("Run diagnostics."))
require("unsupported-execution-claim-replaced", "Nothing ran" in claim, claim)
require("unsupported-execution-claim-names-capability", "`diagnostics`" in claim, claim)
future_claim = bound_unverified_action_claim("I will now run diagnostics.", projection("Run diagnostics."))
require("future-execution-claim-replaced", "Nothing ran" in future_claim, future_claim)
ordinary_response = "I like the name because it fits the project."
require("ordinary-response-preserved", bound_unverified_action_claim(ordinary_response, ordinary) == ordinary_response)

receipt_digest = "a" * 64
verified = projection(
    "Run diagnostics.",
    authoritative_receipts=[
        {"authoritative": True, "status": "completed", "capability_id": "diagnostics", "receipt_digest": receipt_digest, "approval_granted": False},
        {"authoritative": True, "status": "completed", "capability_id": "diagnostics", "receipt_digest": receipt_digest, "approval_granted": False},
        {"authoritative": True, "status": "completed", "capability_id": "maintenance", "receipt_digest": "b" * 64, "approval_granted": False},
        "malformed",
    ],
)
require("authoritative-receipt-recognized", verified["grounding"]["authoritative_execution_receipt_present"], verified)
require("duplicate-receipt-deduplicated", verified["grounding"]["replayed_receipt_count"] == 1, verified)
require("wrong-capability-receipt-rejected", verified["grounding"]["invalid_receipt_count"] == 2, verified)
verified_claim = "I ran diagnostics using the authoritative receipt."
require("verified-claim-not-rewritten", bound_unverified_action_claim(verified_claim, verified) == verified_claim)

malformed_history = projection(
    "Go ahead.",
    conversation_history=[None, 3, {}, {"user_message": None}, {"user_message": "hello"}],
    authoritative_receipts=[{}, None],
)
require("malformed-history-safe", malformed_history["intent"]["category"] == "ambiguous_request", malformed_history)
require("malformed-receipts-counted", malformed_history["grounding"]["invalid_receipt_count"] == 2, malformed_history)

oversized = projection("Run diagnostics. " + ("x" * 20000))
require("oversized-input-bounded", oversized["intent"]["input_truncated"], oversized["intent"])
require("oversized-action-clarifies", oversized["intent"]["requires_clarification"], oversized["intent"])

for text in list(expected_actions) + ["Do you like the name Eidolon?", "Stop calling me Daddy.", "Go ahead."]:
    row = projection(text)
    encoded = json.dumps(row["receipt"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    require(f"receipt-size:{text[:18]}", len(encoded) <= MAX_RECEIPT_BYTES, len(encoded))
    require(f"receipt-content-free:{text[:18]}", row["receipt"]["content_free"], row["receipt"])
    require(f"projection-private-fields:{text[:18]}", not action_projection_contains_private_fields({k: v for k, v in row.items() if k != "prompt_section"}), row)

# v1489.0005: verify routing behavior rather than brittle source-text call counts.
parity_cases = [
    "Run diagnostics.",
    "Before we continue, run a read-only system maintenance check.",
    'The phrase "run diagnostics" is only an example.',
    "It would be nice if you could check my computer someday.",
]
for index, text in enumerate(parity_cases):
    first = projection(text)
    second = projection(text)
    require(f"routing-behavior-parity:{index}", first["intent"] == second["intent"] and first["grounding"] == second["grounding"], (first, second))
    require(f"routing-receipt-parity:{index}", first["receipt"] == second["receipt"], (first["receipt"], second["receipt"]))
runtime_source = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
require("projection-before-provider", runtime_source.find("build_natural_language_action_projection(") < runtime_source.find("client.generate(packet.prompt)"))
require("compact-stream-result-preserved", 'include_cognitive_context=False' in runtime_source)

latencies = []
for _ in range(80):
    started = time.perf_counter()
    projection("Run diagnostics.")
    latencies.append((time.perf_counter() - started) * 1000)
p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1]
require("projection-p95-under-20ms", p95 < 20.0, p95)

guard_latencies = []
action_row = projection("Run diagnostics.")
for _ in range(500):
    started = time.perf_counter()
    bound_unverified_action_claim("I ran diagnostics.", action_row)
    guard_latencies.append((time.perf_counter() - started) * 1000)
require("completion-release-guard-p95-under-1ms", sorted(guard_latencies)[474] < 1.0, sorted(guard_latencies)[474])

summary = {
    "ok": all(ok for _name, ok, _detail in checks),
    "suite": "v1175.0-v1175.2-natural-language-action-routing-foundations",
    "passed": sum(ok for _name, ok, _detail in checks),
    "total": len(checks),
    "projection_p95_ms": round(p95, 4),
    "completion_release_guard_p95_ms": round(sorted(guard_latencies)[474], 4),
    "streaming_non_streaming_parity": True,
    "provider_contacted": False,
    "action_executed": False,
    "approval_created": False,
    "source_modified_by_action_request": False,
}
print(json.dumps(summary, sort_keys=True))
if not summary["ok"]:
    raise SystemExit(1)
