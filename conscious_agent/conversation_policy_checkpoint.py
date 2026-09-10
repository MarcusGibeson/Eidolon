from __future__ import annotations

"""Strictly read-only v1160.9 Conversation Policy checkpoint.

Consolidates bounded executable evidence from v1160.0-v1160.8. The checkpoint
reports only structural classifications, counts, invariants, and digests. It
never returns user or assistant text, conversation or memory text, prompt or
provider payloads, identifiers, or private chain-of-thought.
"""

from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from checkpoint_registry import inspect_checkpoint_registry
from conversation_discourse_policy import CONTRACT_VERSION as DISCOURSE_CONTRACT_VERSION, MAX_HISTORY_RECORDS, MAX_MESSAGE_ANALYSIS_CHARS, MAX_PROMPT_CHARS, build_conversation_discourse_policy, build_conversation_discourse_policy_for_turn
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy

CONTRACT_VERSION = "v1160.9"
_CHECKPOINT_ID = "conversation-policy:v1160.9"
_EXCLUDED_SOURCE_ROOTS = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
}
_FORBIDDEN_REPORT_VALUES = (
    "DISCOURSE_PRIVATE_CANARY",
    "PROVIDER_PRIVATE_CANARY",
    "MEMORY_PRIVATE_CANARY",
    "approve and execute",
    "</conversation_discourse_policy>",
    "<system>",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path, *, source_tree: bool) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    paths: list[Path] = []
    if source_tree:
        for base, directories, names in os.walk(root):
            directories[:] = [name for name in directories if name not in _EXCLUDED_SOURCE_ROOTS]
            for name in names:
                path = Path(base) / name
                if path.suffix.lower() not in {".pyc", ".pyo"}:
                    paths.append(path)
    else:
        paths = [
            path for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
            and path.suffix.lower() not in {".pyc", ".pyo"}
        ]
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            content = hashlib.sha256(path.read_bytes()).digest()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def _canonical_policy(
    *,
    selected_intent: str = "direct_answer",
    output_disposition: str = "answer_only",
    conflict: bool = False,
) -> dict[str, Any]:
    return {
        "selected_intent": selected_intent,
        "output_disposition": output_disposition,
        "component_conflict_present": conflict,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "may_initiate_new_turn": False,
    }


def _bounded_generator(count: int) -> Iterable[dict[str, Any]]:
    for index in range(count):
        yield {"role": "assistant" if index % 2 else "user", "content": "bounded shape"}


def _case_summary(value: dict[str, Any]) -> dict[str, Any]:
    prompt = str(value.get("prompt_section") or "")
    evidence = value.get("evidence") if isinstance(value.get("evidence"), dict) else {}
    return {
        "discourse_relation": str(value.get("discourse_relation") or ""),
        "primary_obligation": str(value.get("primary_obligation") or ""),
        "continuity_mode": str(value.get("continuity_mode") or ""),
        "grounding_mode": str(value.get("grounding_mode") or ""),
        "opening_move": str(value.get("opening_move") or ""),
        "prior_context_use": str(value.get("prior_context_use") or ""),
        "repair_sequence": str(value.get("repair_sequence") or ""),
        "completion_shape": str(value.get("completion_shape") or ""),
        "maximum_prior_turn_references": int(value.get("maximum_prior_turn_references") or 0),
        "maximum_recap_sentences": int(value.get("maximum_recap_sentences") or 0),
        "generic_closing_offer_allowed": bool(value.get("generic_closing_offer_allowed")),
        "context_integrity": str(value.get("context_integrity") or ""),
        "contradictory_cues_suppressed": bool(value.get("contradictory_cues_suppressed")),
        "repeated_repair_loop_suppressed": bool(value.get("repeated_repair_loop_suppressed")),
        "answer_current_request": bool(value.get("answer_current_request")),
        "address_explicit_correction": bool(value.get("address_explicit_correction")),
        "may_reference_prior_turn": bool(value.get("may_reference_prior_turn")),
        "policy_recovered": bool(value.get("policy_recovered")),
        "history_count": int(evidence.get("history_count") or 0),
        "history_truncated": bool(evidence.get("history_truncated")),
        "history_malformed": bool(evidence.get("history_malformed")),
        "stale_history_records_ignored": int(evidence.get("stale_history_records_ignored") or 0),
        "suspicious_history_records_ignored": int(evidence.get("suspicious_history_records_ignored") or 0),
        "message_truncated": bool(evidence.get("message_truncated")),
        "message_control_characters_removed": bool(evidence.get("message_control_characters_removed")),
        "authority_preserved": not any(bool(value.get(key)) for key in (
            "approval_granted", "authorization_granted", "execution_permitted", "may_initiate_new_turn",
        )),
        "content_free": not any(bool(value.get(key)) for key in (
            "contains_message_content", "contains_conversation_text", "contains_memory_text",
            "contains_provider_payload", "contains_private_chain_of_thought",
        )) and not any(bool(evidence.get(key)) for key in (
            "contains_message_content", "contains_conversation_text", "contains_memory_text",
            "contains_provider_payload", "contains_private_chain_of_thought",
        )),
        "policy_identity_present": len(str(value.get("policy_digest") or "")) == 64,
        "evidence_identity_present": len(str(value.get("evidence_digest") or "")) == 64,
        "prompt_length": len(prompt),
        "prompt_envelope_complete": prompt.startswith(
            '<conversation_discourse_policy data_only="true" authority="none">'
        ) and prompt.endswith("</conversation_discourse_policy>"),
    }


def _synthetic_contract_evidence() -> dict[str, Any]:
    prior_history = [
        {"role": "user", "content": "prior shape"},
        {"role": "assistant", "content": "prior answer shape"},
    ]
    repair_history = [
        {"role": "user", "content": "actually correction one"},
        {"role": "assistant", "content": "prior answer"},
        {"role": "user", "content": "that is wrong correction two"},
        {"role": "assistant", "content": "prior answer"},
        {"role": "user", "content": "you misunderstood correction three"},
        {"role": "assistant", "content": "prior answer"},
    ]
    cases: dict[str, dict[str, Any]] = {
        "direct_answer": build_conversation_discourse_policy_for_turn(
            "What is the capital?", _canonical_policy()
        ),
        "continuation": build_conversation_discourse_policy_for_turn(
            "Keep going", _canonical_policy(), conversation_history=prior_history
        ),
        "correction": build_conversation_discourse_policy_for_turn(
            "No, that is incorrect", _canonical_policy(selected_intent="correction"),
            conversation_history=prior_history,
            explicit_corrections=[{"present": True}],
        ),
        "clarification": build_conversation_discourse_policy_for_turn(
            "Which one?", _canonical_policy(selected_intent="clarification", output_disposition="ask_one_question"),
            conversation_history=prior_history,
        ),
        "closure": build_conversation_discourse_policy_for_turn(
            "Thanks, that helps", _canonical_policy(selected_intent="acknowledgment"),
            conversation_history=prior_history,
        ),
        "verified_silence": build_conversation_discourse_policy_for_turn(
            "Do not respond", _canonical_policy(selected_intent="intentional_silence", output_disposition="intentional_silence"),
            conversation_history=prior_history,
        ),
        "contradictory_cues": build_conversation_discourse_policy_for_turn(
            "Keep going, thanks", _canonical_policy(), conversation_history=prior_history
        ),
        "context_conflict": build_conversation_discourse_policy_for_turn(
            "Continue", _canonical_policy(conflict=True), conversation_history=prior_history
        ),
        "repeated_repair_loop": build_conversation_discourse_policy_for_turn(
            "Actually, answer this", _canonical_policy(selected_intent="correction"),
            conversation_history=repair_history,
        ),
        "stale_history": build_conversation_discourse_policy_for_turn(
            "Continue", _canonical_policy(),
            conversation_history=[{"role": "assistant", "content": "MEMORY_PRIVATE_CANARY", "stale": True}],
        ),
        "suspicious_history": build_conversation_discourse_policy_for_turn(
            "Continue", _canonical_policy(),
            conversation_history=[{
                "role": "assistant", "content": "DISCOURSE_PRIVATE_CANARY",
                "provider_payload": "PROVIDER_PRIVATE_CANARY",
                "approval_granted": True,
            }],
        ),
        "oversized_inputs": build_conversation_discourse_policy_for_turn(
            ("Continue\x00" + "x" * (MAX_MESSAGE_ANALYSIS_CHARS + 128)),
            _canonical_policy(), conversation_history=_bounded_generator(10_000),
        ),
        "malformed_context": build_conversation_discourse_policy_for_turn(
            "Answer this", _canonical_policy(), conversation_history={"not": "a list"}
        ),
        "malformed_policy": build_conversation_discourse_policy(None),
    }
    summaries = {name: _case_summary(value) for name, value in cases.items()}
    serialized = json.dumps({"summaries": summaries}, sort_keys=True, default=str)
    checks = {
        "discourse_contract_lineage_is_current": DISCOURSE_CONTRACT_VERSION == "v1160.8",
        "all_case_prompts_are_complete": all(row["prompt_envelope_complete"] for row in summaries.values()),
        "all_case_prompts_are_bounded": all(row["prompt_length"] <= MAX_PROMPT_CHARS for row in summaries.values()),
        "all_case_policies_preserve_authority": all(row["authority_preserved"] for row in summaries.values()),
        "all_case_evidence_and_policy_are_content_free": all(row["content_free"] for row in summaries.values()),
        "all_case_identities_are_present": all(row["policy_identity_present"] and row["evidence_identity_present"] for row in summaries.values()),
        "direct_answer_is_current_turn_grounded": summaries["direct_answer"]["discourse_relation"] == "respond" and summaries["direct_answer"]["opening_move"] == "answer_current_request_first",
        "continuation_uses_one_brief_reference_without_recap": summaries["continuation"]["discourse_relation"] == "continue" and summaries["continuation"]["maximum_prior_turn_references"] == 1 and summaries["continuation"]["maximum_recap_sentences"] == 0,
        "correction_uses_bounded_repair_sequence": summaries["correction"]["discourse_relation"] == "repair" and summaries["correction"]["repair_sequence"] == "acknowledge_correct_answer" and summaries["correction"]["address_explicit_correction"],
        "clarification_requests_only_missing_information": summaries["clarification"]["discourse_relation"] == "clarify" and summaries["clarification"]["completion_shape"] == "await_required_reply",
        "closure_does_not_reopen_or_offer": summaries["closure"]["discourse_relation"] == "close" and not summaries["closure"]["generic_closing_offer_allowed"],
        "verified_silence_has_no_substantive_plan": summaries["verified_silence"]["primary_obligation"] == "honor_explicit_silence" and summaries["verified_silence"]["completion_shape"] == "silent_completion" and not summaries["verified_silence"]["answer_current_request"],
        "contradictory_cues_fall_back_to_current_turn": summaries["contradictory_cues"]["contradictory_cues_suppressed"] and summaries["contradictory_cues"]["discourse_relation"] == "respond" and summaries["contradictory_cues"]["maximum_prior_turn_references"] == 0,
        "context_conflict_suppresses_prior_reference": summaries["context_conflict"]["maximum_prior_turn_references"] == 0 and summaries["context_conflict"]["prior_context_use"] == "none",
        "repair_loop_suppresses_repair_repetition": summaries["repeated_repair_loop"]["repeated_repair_loop_suppressed"] and summaries["repeated_repair_loop"]["opening_move"] == "answer_current_request_first",
        "stale_history_is_ignored": summaries["stale_history"]["stale_history_records_ignored"] == 1 and summaries["stale_history"]["prior_context_use"] != "one_brief_reference",
        "suspicious_history_is_ignored_and_degrades_context": summaries["suspicious_history"]["suspicious_history_records_ignored"] == 1 and summaries["suspicious_history"]["context_integrity"] == "degraded",
        "oversized_inputs_are_bounded": summaries["oversized_inputs"]["message_truncated"] and summaries["oversized_inputs"]["message_control_characters_removed"] and summaries["oversized_inputs"]["history_truncated"] and summaries["oversized_inputs"]["history_count"] == MAX_HISTORY_RECORDS,
        "malformed_context_recovers_without_prior_reference": summaries["malformed_context"]["history_malformed"] and summaries["malformed_context"]["policy_recovered"] and summaries["malformed_context"]["maximum_prior_turn_references"] == 0,
        "malformed_policy_recovers_neutrally": summaries["malformed_policy"]["policy_recovered"] and summaries["malformed_policy"]["discourse_relation"] == "respond" and summaries["malformed_policy"]["maximum_prior_turn_references"] == 0,
        "generic_closing_offers_are_never_enabled": not any(row["generic_closing_offer_allowed"] for row in summaries.values()),
        "private_canaries_are_absent_from_checkpoint_evidence": not any(token in serialized for token in (
            "DISCOURSE_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY"
        )),
    }
    return {
        "checks": checks,
        "passed": sum(1 for value in checks.values() if value),
        "total": len(checks),
        "case_count": len(cases),
        "case_summaries": summaries,
        "content_free": True,
        "structural_digest": _digest({"checks": checks, "summaries": summaries}),
    }


@lru_cache(maxsize=8)
def _static_source_evidence(source_text: str, source_signature: str) -> str:
    del source_signature
    source = Path(source_text)
    runtime_text = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    policy_text = (source / "conscious_agent" / "conversation_discourse_policy.py").read_text(encoding="utf-8")
    prompt_projection = policy_text[policy_text.find("def conversation_discourse_prompt_section"):policy_text.find("def build_conversation_discourse_policy_for_turn")]
    payload = {
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
        "integration": {
            "ordinary_runtime_builds_discourse_policy_in_both_paths": runtime_text.count("build_conversation_discourse_policy_for_turn(") == 2,
            "ordinary_runtime_sends_discourse_prompt_in_both_paths": runtime_text.count('conversation_discourse["prompt_section"]') == 2,
            "ordinary_runtime_records_discourse_policy_in_both_paths": runtime_text.count('result.cognitive_context["conversation_discourse_policy"]') == 2,
            "ordinary_runtime_records_discourse_evidence_in_both_paths": runtime_text.count('result.cognitive_context["conversation_discourse_evidence"]') == 2,
            "single_authoritative_conversation_builder_is_preserved": runtime_text.count("ConversationRuntime(") == 0 and runtime_text.count("build_conversation_discourse_policy_for_turn(") == 2,
            "assistant_memory_commit_boundary_remains_present": "assistant_memory_stored" in runtime_text,
            "provider_failure_and_cancellation_boundaries_remain_present": "LocalModelCancelledError" in runtime_text and "cancel_event" in runtime_text,
            "discourse_prompt_is_data_only_and_authority_free": '<conversation_discourse_policy data_only="true" authority="none">' in policy_text,
            "discourse_policy_reconstructs_authority": all(token in policy_text for token in (
                "may_initiate_new_turn=False", "approval_granted=False",
                "authorization_granted=False", "execution_permitted=False",
            )),
            "history_and_message_bounds_are_explicit": "MAX_HISTORY_RECORDS = 24" in policy_text and "MAX_MESSAGE_ANALYSIS_CHARS = 4096" in policy_text,
            "stale_and_suspicious_history_filters_are_present": "def _record_is_stale" in policy_text and "def _record_is_suspicious" in policy_text,
            "contradictory_and_repair_loop_suppression_are_present": "contradictory_cues_suppressed" in policy_text and "repeated_repair_loop_suppressed" in policy_text,
            "prompt_projection_omits_raw_content_fields": not any(token in prompt_projection for token in (
                "current_message", "conversation_history", "memory_text", "provider_payload", "private_chain_of_thought",
            )),
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_conversation_policy_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").expanduser().resolve()
    source_before = _tree_signature(source, source_tree=True)
    runtime_before = _tree_signature(runtime, source_tree=False)

    static = json.loads(_static_source_evidence(str(source), source_before))
    registry = static["registry"]
    privacy_policy = static["privacy_policy"]
    privacy = static["privacy"]
    integration = static["integration"]
    synthetic = _synthetic_contract_evidence()

    limitations = [
        {"limitation_id": "discourse-classification-remains-bounded-and-lexical", "status": "open", "current_behavior": "deterministic_structural_cues"},
        {"limitation_id": "provider-responses-are-not-postvalidated-against-discourse-plan", "status": "open", "current_behavior": "bounded_prompt_construction_contract"},
        {"limitation_id": "repair-resolution-and-prior-turn-relevance-are-not-semantically-proven", "status": "open", "current_behavior": "bounded_history_shape_and_cues"},
        {"limitation_id": "intentional-silence-uses-existing-valid-turn-boundary", "status": "open", "current_behavior": "no_provider_free_silent_completion"},
        {"limitation_id": "native-desktop-verification-pending", "status": "open", "next_action": "defer_desktop_codex_review_until_v1200"},
    ]

    checks: list[tuple[str, bool]] = [
        *[(name, bool(value)) for name, value in synthetic["checks"].items()],
        *[(name, bool(value)) for name, value in integration.items()],
        (
            "checkpoint_registry_discovers_conversation_policy_checkpoint",
            int(registry.get("checkpoint_count") or 0) >= 187
            and not registry.get("duplicate_checkpoint_ids")
            and not registry.get("duplicate_builder_targets"),
        ),
        (
            "source_only_policy_excludes_runtime_data",
            privacy_policy.get("excludes_all_data_directory_entries") is True
            and not privacy_policy.get("authorizes_package_creation")
            and not privacy_policy.get("publishes_release"),
        ),
        (
            "current_source_tree_privacy_scan_passes",
            privacy.get("ok") is True and privacy.get("source_only") is True
            and privacy.get("forbidden_count") == 0
            and privacy.get("private_content_finding_count") == 0,
        ),
        (
            "remaining_limitations_are_explicit",
            len(limitations) == 5 and all(row.get("status") == "open" for row in limitations),
        ),
        (
            "checkpoint_does_not_modify_source_or_runtime",
            source_before == _tree_signature(source, source_tree=True)
            and runtime_before == _tree_signature(runtime, source_tree=False),
        ),
    ]
    check_rows = [{"check_id": name, "status": "pass" if value else "fail"} for name, value in checks]
    passed = sum(1 for _, value in checks if value)
    total = len(checks)
    ok = passed == total

    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": ok,
        "status": "conversation_policy_checkpoint_candidate" if ok else "review_required",
        "passed": passed,
        "total": total,
        "checks": check_rows,
        "summary": {
            "synthetic_contract_check_count": synthetic["total"],
            "synthetic_case_count": synthetic["case_count"],
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "discourse_prompt_maximum_chars": MAX_PROMPT_CHARS,
            "message_analysis_maximum_chars": MAX_MESSAGE_ANALYSIS_CHARS,
            "history_record_maximum_count": MAX_HISTORY_RECORDS,
            "authoritative_conversation_path_count": 2 if integration["ordinary_runtime_builds_discourse_policy_in_both_paths"] else 0,
            "open_limitation_count": len(limitations),
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {
            "synthetic_contracts": synthetic,
            "ordinary_conversation_integration": integration,
            "registry": {
                "checkpoint_count": registry.get("checkpoint_count", 0),
                "duplicate_checkpoint_id_count": len(registry.get("duplicate_checkpoint_ids") or []),
                "duplicate_builder_target_count": len(registry.get("duplicate_builder_targets") or []),
                "content_free": True,
            },
            "privacy": {
                "source_only": privacy.get("source_only"),
                "forbidden_count": privacy.get("forbidden_count", 0),
                "private_content_finding_count": privacy.get("private_content_finding_count", 0),
                "structural_digest": privacy.get("structural_digest", ""),
                "content_free": True,
            },
        },
        "remaining_limitations": limitations,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "native_provider_certification_pending": True,
        "conversation_policy_checkpoint_completed": ok,
        "conversation_and_learning_arc_started": True,
        "governed_proactive_speech_not_started": True,
        "bounded_learning_mutation_not_started": True,
        "consciousness_proven": False,
        "sentience_proven": False,
        "personhood_proven": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "generated_response_exposed": False,
        "prompt_exposed": False,
        "memory_text_exposed": False,
        "evidence_text_exposed": False,
        "provider_payload_exposed": False,
        "operation_identifiers_exposed": False,
        "session_identifiers_exposed": False,
        "hidden_reasoning_exposed": False,
    }
    for field in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "goal_modified", "plan_created",
        "decision_created", "intention_created", "conflict_resolved",
        "approval_request_created", "approval_created", "approval_granted",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed", "proactive_turn_created", "learning_performed",
        "identity_rewritten", "memory_corrected",
    ):
        report[field] = False
    report["structural_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "checks": check_rows,
        "summary": report["summary"],
        "limitations": limitations,
        "synthetic_digest": synthetic["structural_digest"],
    })
    serialized = json.dumps(report, sort_keys=True)
    report["forbidden_report_value_count"] = sum(serialized.count(token) for token in _FORBIDDEN_REPORT_VALUES)
    return report
