from __future__ import annotations

"""Strictly read-only v1145.5 Conversation-Cognition Unification Execution checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from conversation_cognition_bounded_generation import STATES as GENERATION_STATES, build_conversation_cognition_bounded_generation_inspection
from conversation_cognition_communication_arbitration import OUTCOMES, build_conversation_cognition_communication_arbitration_inspection
from conversation_cognition_unification_intake_checkpoint import build_conversation_cognition_unification_intake_checkpoint
from workload_coordination_continuity import build_workload_coordination_continuity_inspection

CONTRACT_VERSION = "v1145.5"


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and "__pycache__" not in item.parts and item.suffix not in {".pyc", ".pyo"}
    ):
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest()


def build_conversation_cognition_unification_execution_checkpoint(
    runtime_root: Path | str | None = None,
    *,
    source_root: Path | str | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).resolve() if runtime_root else _root()
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_conversation_cognition_unification_intake_checkpoint(runtime, source_root=source)
    arbitration = build_conversation_cognition_communication_arbitration_inspection(runtime)
    generation = build_conversation_cognition_bounded_generation_inspection(runtime)
    workload_continuity = build_workload_coordination_continuity_inspection(runtime)
    arbitration_rows = arbitration.get("recent_records", [])
    generation_rows = generation.get("recent_records", [])

    privacy_flags = (
        "raw_conversation_exposed",
        "raw_message_exposed",
        "prompt_exposed",
        "reflection_text_exposed",
        "memory_text_exposed",
        "relationship_text_exposed",
        "mood_text_exposed",
        "goal_text_exposed",
        "motivation_text_exposed",
        "provider_payload_exposed",
        "generated_response_exposed",
        "hidden_reasoning_exposed",
    )
    generation_active = {"running", "cancellation_requested", "completed"}
    checks = [
        ("intake_contract", intake.get("contract_version") == "v1145.2"),
        ("arbitration_contract", arbitration.get("contract_version") == "v1145.3"),
        ("generation_contract", generation.get("contract_version") == "v1145.4"),
        ("exact_candidate_lineage", all(row.get("candidate_id") and row.get("candidate_structural_digest") and row.get("eligibility_id") for row in arbitration_rows + generation_rows)),
        ("exact_session_conversation_lineage", all(row.get("session_id") and row.get("conversation_id") for row in arbitration_rows + generation_rows)),
        ("deterministic_arbitration", arbitration.get("deterministic_arbitration") and set(arbitration.get("recognized_outcomes", [])) == OUTCOMES),
        ("deliberate_silence", arbitration.get("silence_is_valid_outcome") and "deliberate_silence" in OUTCOMES),
        ("relevance_permission_separation", any(check.get("id") == "relevance_permission_separation" and check.get("status") == "pass" for check in intake.get("checks", []))),
        ("generation_requires_exact_arbitration", all(row.get("arbitration_id") and row.get("arbitration_structural_digest") for row in generation_rows)),
        ("generation_only_after_eligibility", all(row.get("state") not in generation_active or row.get("arbitration_id") for row in generation_rows)),
        ("provider_profile_binding", all(row.get("state") in {"stale_worker", "stale_arbitration", "context_rejected"} or (row.get("provider_profile_id") and row.get("provider_profile_digest")) for row in generation_rows)),
        ("exact_context_assembly", generation.get("exact_provider_context_assembly") and all(not row.get("context_assembled") or (row.get("context_set_digest") and row.get("source_lineage_digest") and row.get("prompt_digest") and int(row.get("source_count") or 0) > 0) for row in generation_rows)),
        ("bounded_tokens", all(row.get("state") == "budget_exhausted" or int(row.get("input_token_estimate") or 0) + int(row.get("output_token_estimate") or 0) <= int((row.get("budget_limits") or {}).get("token_budget") or 0) for row in generation_rows if row.get("context_assembled"))),
        ("bounded_resources", all(row.get("state") == "budget_exhausted" or (int(row.get("cpu_used_ms") or 0) <= int((row.get("budget_limits") or {}).get("cpu_budget_ms") or 0) and int(row.get("latency_used_ms") or 0) <= int((row.get("budget_limits") or {}).get("latency_budget_ms") or 0) and int(row.get("memory_estimate_mb") or 0) <= int((row.get("budget_limits") or {}).get("memory_budget_mb") or 0)) for row in generation_rows if row.get("provider_contacted"))),
        ("cancellation_support", generation.get("cancellation_supported") and "cancelled" in GENERATION_STATES and "cancellation_requested" in GENERATION_STATES),
        ("timeout_support", generation.get("timeout_supported") and "timed_out" in GENERATION_STATES),
        ("workload_admission_lineage", all(row.get("outcome") != "generation_eligible" or (row.get("workload_admitted") and row.get("workload_arbitration_id") and row.get("workload_arbitration_digest")) for row in arbitration_rows)),
        ("workload_continuity", generation.get("workload_continuity_integrated") and workload_continuity.get("contract_version") == "v1143.4" and all(not row.get("provider_contacted") or row.get("workload_continuity_id") for row in generation_rows if row.get("state") in GENERATION_STATES - {"running", "cancellation_requested"})),
        ("stale_worker_fail_closed", "stale_worker" in GENERATION_STATES and all(row.get("state") != "stale_worker" or not row.get("provider_contacted") for row in generation_rows)),
        ("stale_arbitration_fail_closed", "stale_arbitration" in GENERATION_STATES and all(row.get("state") != "stale_arbitration" or not row.get("provider_contacted") for row in generation_rows)),
        ("duplicate_suppression", "duplicate_suppressed" in GENERATION_STATES and all(row.get("state") != "duplicate_suppressed" or not row.get("generation_completed") for row in generation_rows)),
        ("structural_receipts_only", generation.get("receipts_are_structural_only") and all(row.get("structural_digest") for row in generation_rows)),
        ("privacy_hidden_reasoning", not any(bool(arbitration.get(key)) or bool(generation.get(key)) for key in privacy_flags)),
        ("output_commit_separation", generation.get("generated_output_requires_separate_commit") and not generation.get("generated_output_committed")),
        ("message_delivery_separation", generation.get("message_delivery_requires_separate_authority") and not arbitration.get("message_sent") and not generation.get("message_sent") and not generation.get("notification_created")),
        ("cognition_conversation_mutation_separation", not arbitration.get("cognition_mutated") and not arbitration.get("conversation_mutated") and not generation.get("cognition_mutated") and not generation.get("conversation_mutated")),
        ("authority_separation", not any((arbitration.get("authority_boundary") or {}).values()) and not any((generation.get("authority_boundary") or {}).values())),
        ("checkpoint_read_only", runtime_before == _tree_signature(runtime) and source_before == _tree_signature(source)),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    source_modified = source_before != _tree_signature(source)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_name": "Conversation-Cognition Unification Execution",
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "intake": intake,
        "arbitration": arbitration,
        "generation": generation,
        "workload_continuity": workload_continuity,
        "summary": {
            "eligibility_record_count": (intake.get("summary") or {}).get("eligibility_record_count", 0),
            "context_candidate_count": (intake.get("summary") or {}).get("context_candidate_count", 0),
            "communication_arbitration_count": arbitration.get("record_count", 0),
            "generation_receipt_count": generation.get("record_count", 0),
            "deliberate_silence_count": (arbitration.get("outcome_counts") or {}).get("deliberate_silence", 0),
            "completed_generation_count": (generation.get("state_counts") or {}).get("completed", 0),
            "cancelled_generation_count": (generation.get("state_counts") or {}).get("cancelled", 0),
            "timed_out_generation_count": (generation.get("state_counts") or {}).get("timed_out", 0),
        },
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "goal_text_exposed": False,
        "motivation_text_exposed": False,
        "provider_payload_exposed": False,
        "generated_response_exposed": False,
        "hidden_reasoning_exposed": False,
        "communication_arbitration_performed_by_checkpoint": False,
        "provider_context_assembled_by_checkpoint": False,
        "provider_contacted_by_checkpoint": False,
        "conversation_generated_by_checkpoint": False,
        "message_sent": False,
        "notification_created": False,
        "generated_output_committed": False,
        "cognition_mutated": False,
        "memory_mutated": False,
        "relationship_mutated": False,
        "mood_mutated": False,
        "goal_mutated": False,
        "motivation_mutated": False,
        "attention_mutated": False,
        "conversation_mutated": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "consciousness_proven": False,
        "desktop_verification_pending": True,
        "desktop_verification": "pending",
    }
