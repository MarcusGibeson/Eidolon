from __future__ import annotations

"""Strictly read-only v1145.2 Conversation-Cognition Unification Intake checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from unified_context_candidates import build_unified_context_candidate_inspection
from unified_conversational_context_eligibility import COGNITIVE_CONTEXT_CATEGORIES, CURRENT_ONLY_CATEGORIES, HISTORICAL_ALLOWED_CATEGORIES, REQUIRED_CONTEXT_CATEGORIES, SOURCE_CATEGORIES, build_unified_conversational_context_eligibility_inspection

CONTRACT_VERSION = "v1145.2"


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file()
            and candidate.suffix not in {".pyc", ".pyo"}
            and "__pycache__" not in candidate.parts
        ):
            stat = path.stat()
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return digest.hexdigest()


def _all_source_rows(eligibility_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        source
        for row in eligibility_rows
        for source in (row.get("source_lineage") or [])
        if isinstance(source, dict)
    ]


def build_conversation_cognition_unification_intake_checkpoint(
    runtime_root: Path | str | None = None,
    *,
    source_root: Path | str | None = None,
) -> dict[str, object]:
    runtime = Path(runtime_root).resolve() if runtime_root else _root()
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    eligibility = build_unified_conversational_context_eligibility_inspection(runtime)
    candidates = build_unified_context_candidate_inspection(runtime)
    eligibility_rows = eligibility.get("recent_records", [])
    candidate_rows = candidates.get("recent_records", [])
    source_rows = _all_source_rows(eligibility_rows)

    lifecycle_keys = {
        "correction_source_ids",
        "accepted_guidance_source_ids",
        "contradicted_source_ids",
        "retracted_source_ids",
        "superseded_source_ids",
        "expired_source_ids",
        "retired_source_ids",
    }
    required_affective_categories = {
        "mood_state",
        "goal",
        "motivation",
        "concern",
        "attention_target",
    }
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

    checks = [
        ("eligibility_contract", eligibility.get("contract_version") == "v1145.0"),
        ("candidate_contract", candidates.get("contract_version") == "v1145.1"),
        ("complete_source_taxonomy", set(eligibility.get("recognized_source_categories", [])) == SOURCE_CATEGORIES),
        ("required_constraint_taxonomy", set(eligibility.get("required_context_categories", [])) == REQUIRED_CONTEXT_CATEGORIES),
        (
            "exact_cognition_conversation_lineage",
            all(
                row.get("session_id")
                and row.get("conversation_id")
                and row.get("structural_digest")
                and row.get("context_set_digest")
                and all(
                    source_row.get("source_id")
                    and int(source_row.get("source_revision") or 0) > 0
                    and source_row.get("source_digest")
                    and source_row.get("lineage_digest")
                    for source_row in (row.get("source_lineage") or [])
                )
                for row in eligibility_rows
            )
            and all(
                row.get("eligibility_id")
                and row.get("eligibility_structural_digest")
                and row.get("eligibility_context_set_digest")
                for row in candidate_rows
            ),
        ),
        (
            "current_historical_separation",
            set(eligibility.get("current_only_categories", [])) == CURRENT_ONLY_CATEGORIES
            and set(eligibility.get("historical_allowed_categories", [])) == HISTORICAL_ALLOWED_CATEGORIES
            and all(
                source_row.get("temporal_status") in {"current", "historical"}
                and not (
                    source_row.get("source_category") in CURRENT_ONLY_CATEGORIES
                    and source_row.get("temporal_status") != "current"
                    and source_row.get("included")
                )
                for source_row in source_rows
            ),
        ),
        (
            "thought_memory_distinction",
            all(
                source_row.get("temporal_status") == "current"
                for source_row in source_rows
                if source_row.get("source_category") in {"active_thought", "reflection"}
                and source_row.get("included")
            )
            and all(
                source_row.get("temporal_status") in {"current", "historical"}
                for source_row in source_rows
                if source_row.get("source_category") == "memory_reference"
            ),
        ),
        (
            "memory_relevance_privacy",
            all(
                source_row.get("relevance_category")
                and source_row.get("privacy_class") in {"public", "internal"}
                for source_row in source_rows
                if source_row.get("source_category") == "memory_reference"
                and source_row.get("included")
            ),
        ),
        (
            "relationship_identity_boundary",
            all(
                source_row.get("relationship_boundary") == "relationship_only"
                for source_row in source_rows
                if source_row.get("source_category") == "relationship_context"
                and source_row.get("included")
            ),
        ),
        (
            "mood_goal_motivation_concern_attention_lineage",
            required_affective_categories <= SOURCE_CATEGORIES
            and all(
                source_row.get("source_id") and source_row.get("source_digest")
                for source_row in source_rows
                if source_row.get("source_category") in required_affective_categories
            ),
        ),
        (
            "correction_acceptance_guidance_lineage",
            {"operator_correction", "accepted_guidance"} <= SOURCE_CATEGORIES
            and all(
                lifecycle_keys <= set((row.get("lifecycle_lineage") or {}).keys())
                for row in candidate_rows
            ),
        ),
        (
            "session_conversation_continuity",
            all(row.get("session_id") and row.get("conversation_id") for row in eligibility_rows + candidate_rows),
        ),
        (
            "workload_latency_token_budgets",
            all(
                all(int((row.get("budget_limits") or {}).get(key) or 0) > 0 for key in ("cpu_budget_ms", "memory_budget_mb", "latency_budget_ms", "token_budget"))
                for row in eligibility_rows
                if row.get("state") in {"eligible", "requires_operator_review"}
            )
            and all(
                all(int((row.get("budget_limits") or {}).get(key) or 0) > 0 for key in ("cpu_budget_ms", "memory_budget_mb", "latency_budget_ms", "token_budget"))
                for row in candidate_rows
                if row.get("state") in {"candidate_ready", "silence_only", "requires_operator_review"}
            ),
        ),
        (
            "provider_availability_lineage",
            "provider_state" in SOURCE_CATEGORIES
            and all(
                row.get("provider_profile_id")
                and "provider_state" in (row.get("included_categories") or [])
                for row in candidate_rows
                if row.get("state") in {"candidate_ready", "silence_only", "requires_operator_review"}
            ),
        ),
        (
            "included_excluded_context_categories",
            all(row.get("included_categories") is not None and row.get("excluded_categories") is not None for row in eligibility_rows + candidate_rows),
        ),
        (
            "relevance_permission_separation",
            all(
                "relevant" in source_row
                and "communication_eligible" in source_row
                and "included" in source_row
                for source_row in source_rows
            ),
        ),
        (
            "candidate_subset_determinism",
            candidates.get("deterministic_construction")
            and not candidates.get("eligible_set_broadening_allowed")
            and all(
                row.get("relevance_order") == row.get("included_source_ids")
                for row in candidate_rows
            ),
        ),
        (
            "silence_eligibility",
            candidates.get("silence_is_valid_outcome")
            and all(row.get("silence_eligible") for row in candidate_rows if row.get("state") in {"candidate_ready", "silence_only", "requires_operator_review"}),
        ),
        (
            "contradiction_retraction_supersession_expiry_retirement",
            all(
                source_row.get("lifecycle_state") in set(eligibility.get("recognized_lifecycle_states", []))
                for source_row in source_rows
            )
            and all(lifecycle_keys <= set((row.get("lifecycle_lineage") or {}).keys()) for row in candidate_rows),
        ),
        (
            "duplicate_stale_retry_cross_tab_suppression",
            all((eligibility.get("suppression_controls") or {}).values()),
        ),
        (
            "privacy_hidden_reasoning_boundary",
            not any(bool(eligibility.get(key)) for key in privacy_flags)
            and not any(bool(candidates.get(key)) for key in privacy_flags),
        ),
        (
            "authority_separation",
            not any((eligibility.get("authority_boundary") or {}).values())
            and not any((candidates.get("authority_boundary") or {}).values()),
        ),
        (
            "no_generation_message_or_mutation",
            not eligibility.get("provider_contacted")
            and not eligibility.get("conversation_generated")
            and not eligibility.get("message_sent")
            and not eligibility.get("cognition_mutated")
            and not eligibility.get("conversation_mutated")
            and not candidates.get("provider_contacted")
            and not candidates.get("provider_context_assembled")
            and not candidates.get("conversation_generated")
            and not candidates.get("message_sent")
            and not candidates.get("cognition_mutated")
            and not candidates.get("conversation_mutated"),
        ),
        ("source_runtime_separation", runtime != source),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "eligibility": eligibility,
        "candidates": candidates,
        "summary": {
            "eligibility_record_count": int(eligibility.get("record_count") or 0),
            "context_candidate_count": int(candidates.get("record_count") or 0),
            "recognized_source_category_count": len(SOURCE_CATEGORIES),
            "required_constraint_category_count": len(REQUIRED_CONTEXT_CATEGORIES),
            "cognitive_context_category_count": len(COGNITIVE_CONTEXT_CATEGORIES),
        },
        "runtime_mutated": runtime_before != _tree_signature(runtime),
        "source_modified": source_before != _tree_signature(source),
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
        "communication_arbitration_performed": False,
        "provider_context_assembled": False,
        "provider_contacted": False,
        "conversation_generated": False,
        "message_sent": False,
        "notification_created": False,
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
        "eligibility_created_by_checkpoint": False,
        "candidate_created_by_checkpoint": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
