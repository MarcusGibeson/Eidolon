from __future__ import annotations

"""Strictly read-only v1159.9 Cognitive Integration Alpha checkpoint.

Consolidates bounded executable evidence from v1156.0-v1159.8. The checkpoint
reports only structural classifications, counts, invariants, and digests. It
never returns user or assistant text, memory text, prompt payloads, provider
payloads, operation or session identifiers, or private chain-of-thought.
"""

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from contextual_conversation_behavior import CONTRACT_VERSION as BEHAVIOR_CONTRACT_VERSION, build_contextual_conversation_behavior
from conversation_policy_state import CONTRACT_VERSION as POLICY_STATE_CONTRACT_VERSION, MAX_PROMPT_CHARS as POLICY_STATE_MAX_PROMPT_CHARS, _load_verified_completed, _load_verified_pending, build_conversation_policy_state, complete_conversation_policy_state, stage_conversation_policy_state
from follow_up_silence_policy import CONTRACT_VERSION as FOLLOW_UP_CONTRACT_VERSION, build_follow_up_silence_policy
from package_integrity import package_privacy_summary_for_root, source_only_entry_policy
from response_intent_selection import CONTRACT_VERSION as INTENT_CONTRACT_VERSION, build_response_intent_selection

CONTRACT_VERSION = "v1159.9"
_CHECKPOINT_ID = "cognitive-integration-alpha:v1159.9"
_MAX_RUNTIME_RECORDS_INSPECTED = 512
_EXCLUDED_SOURCE_ROOTS = {
    "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
}
_FORBIDDEN_REPORT_VALUES = (
    "COGNITIVE_PRIVATE_CANARY",
    "PROVIDER_PRIVATE_CANARY",
    "MEMORY_PRIVATE_CANARY",
    "approve and execute",
    "</conversation_policy_state>",
    "<system>",
)
_FORBIDDEN_PERSISTED_KEYS = {
    "user_message", "assistant_response", "conversation_text", "memory_text",
    "prompt_section", "provider_payload", "private_chain_of_thought",
    "hidden_reasoning", "raw_evidence", "candidate_rationale",
}


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


def _public_state_summary(value: dict[str, Any]) -> dict[str, Any]:
    prompt = str(value.get("prompt_section") or "")
    return {
        "selected_intent": str(value.get("selected_intent") or ""),
        "intent_confidence": str(value.get("intent_confidence") or ""),
        "context_application": str(value.get("context_application") or ""),
        "warmth": str(value.get("warmth") or ""),
        "output_disposition": str(value.get("output_disposition") or ""),
        "question_scope": str(value.get("question_scope") or ""),
        "max_follow_up_questions": int(value.get("max_follow_up_questions") or 0),
        "explicit_silence_verified": bool(value.get("explicit_silence_verified")),
        "emit_no_substantive_content": bool(value.get("emit_no_substantive_content")),
        "component_recovery_present": bool(value.get("component_recovery_present")),
        "component_conflict_present": bool(value.get("component_conflict_present")),
        "authority_preserved": not any(bool(value.get(key)) for key in (
            "approval_granted", "authorization_granted", "execution_permitted",
            "may_initiate_new_turn", "provider_contacted_for_policy",
        )),
        "precedence_preserved": all(bool(value.get(key)) for key in (
            "literal_request_precedence", "selected_intent_precedence",
            "protected_constraints_precedence",
        )),
        "prompt_length": len(prompt),
        "prompt_envelope_complete": prompt.startswith(
            '<conversation_policy_state data_only="true" authority="none">'
        ) and prompt.endswith("</conversation_policy_state>"),
        "component_digests_present": all(
            len(str(value.get(key) or "")) == 64 for key in (
                "response_intent_digest", "contextual_behavior_digest",
                "follow_up_silence_digest", "policy_state_digest",
            )
        ),
        "content_free": True,
    }


def _actual_policy(message: str, *, self_model: dict[str, Any] | None = None,
                   memories: list[dict[str, Any]] | None = None,
                   history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    intent = build_response_intent_selection(
        message,
        reasoning_state={"reasoning_quality": "bounded_candidate", "uncertainty_score": 0.2},
        conversation_history=history or [],
        explicit_corrections=[],
        protected_operator_constraints=["No action authority", "Current message controls"],
        self_model=self_model or {},
        desires={},
        contextual_memories=memories or [],
    )
    behavior = build_contextual_conversation_behavior(
        intent,
        self_model=self_model or {},
        contextual_memories=memories or [],
        conversation_history=history or [],
    )
    follow = build_follow_up_silence_policy(message, intent, behavior)
    return build_conversation_policy_state(intent, behavior, follow)


def _manual_policy(*, intent: str = "direct_answer", disposition: str = "answer_only",
                   explicit_silence: bool = False, conflict: bool = False,
                   authority_tamper: bool = False) -> dict[str, Any]:
    intent_value = {
        "selected_intent": intent,
        "confidence": "high",
        "ambiguous": False,
        "selection_digest": "a" * 64,
    }
    behavior_value = {
        "context_application": "bounded_explicit" if not conflict else "bounded_explicit",
        "warmth": "warm",
        "familiarity": "continuity_aware",
        "directness": "balanced",
        "continuity_reference": "brief_explicit",
        "emotional_calibration": "gentle",
        "conflicting_context_suppressed": conflict,
        "policy_digest": "b" * 64,
    }
    follow_value = {
        "output_disposition": disposition,
        "question_scope": "missing_information_only" if "question" in disposition else "none",
        "max_follow_up_questions": 1 if "question" in disposition else 0,
        "explicit_silence_verified": explicit_silence,
        "policy_digest": "c" * 64,
    }
    if authority_tamper:
        for value in (intent_value, behavior_value, follow_value):
            value.update({
                "approval_granted": True,
                "authorization_granted": True,
                "execution_permitted": True,
                "may_initiate_new_turn": True,
                "provider_payload": "PROVIDER_PRIVATE_CANARY",
                "private_chain_of_thought": "COGNITIVE_PRIVATE_CANARY",
            })
    return build_conversation_policy_state(intent_value, behavior_value, follow_value)


def _persistence_contract_evidence() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    old = os.environ.get("EIDOLON_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1159-checkpoint-") as td:
            runtime = Path(td) / "runtime"
            os.environ["EIDOLON_DATA_DIR"] = str(runtime)
            base = _manual_policy()
            changed = _manual_policy(intent="explanation")

            staged = stage_conversation_policy_state(base, operation_id="synthetic-op-1", session_id="synthetic-session")
            checks["pending_state_is_content_free_and_non_authorizing"] = bool(
                staged.get("pending_persisted") and not staged.get("completed")
                and not staged.get("contains_content")
                and not staged.get("approval_granted")
                and not staged.get("authorization_granted")
                and not staged.get("execution_permitted")
            )
            first = complete_conversation_policy_state(operation_id="synthetic-op-1", session_id="synthetic-session")
            checks["first_completion_is_initial_and_post_stage"] = bool(
                first.get("completed") and first.get("transition_kind") == "initial"
                and not first.get("duplicate_completion")
            )

            stage_conversation_policy_state(base, operation_id="synthetic-op-2", session_id="synthetic-session")
            stable = complete_conversation_policy_state(operation_id="synthetic-op-2", session_id="synthetic-session")
            checks["unchanged_policy_records_stable_transition"] = bool(
                stable.get("completed") and stable.get("transition_kind") == "stable"
                and not stable.get("changed_fields")
            )

            stage_conversation_policy_state(changed, operation_id="synthetic-op-3", session_id="synthetic-session")
            changed_result = complete_conversation_policy_state(operation_id="synthetic-op-3", session_id="synthetic-session")
            checks["changed_policy_records_bounded_transition"] = bool(
                changed_result.get("completed") and changed_result.get("transition_kind") == "changed"
                and 0 < int(changed_result.get("changed_field_count") or 0) <= 16
            )
            duplicate = complete_conversation_policy_state(operation_id="synthetic-op-3", session_id="synthetic-session")
            checks["duplicate_completion_is_idempotent"] = bool(
                duplicate.get("completed") and duplicate.get("duplicate_completion")
                and duplicate.get("record_identity") == changed_result.get("record_identity")
            )
            mismatch = complete_conversation_policy_state(operation_id="synthetic-op-3", session_id="other-session")
            checks["cross_session_duplicate_fails_closed"] = bool(
                not mismatch.get("completed") and mismatch.get("completion_failure") == "operation_session_mismatch"
            )

            stage_conversation_policy_state(base, operation_id="synthetic-stale", session_id="stale-session")
            pending_path = runtime / "conversation_policy_state" / "pending" / "synthetic-stale.json"
            stale_record = json.loads(pending_path.read_text(encoding="utf-8"))
            stale_record["staged_at_epoch"] = 1
            pending_path.write_text(json.dumps(stale_record, sort_keys=True, indent=2), encoding="utf-8")
            stale_before = pending_path.read_bytes()
            stale = complete_conversation_policy_state(
                operation_id="synthetic-stale", session_id="stale-session", now_epoch=90002
            )
            checks["stale_pending_fails_closed_without_rewrite"] = bool(
                not stale.get("completed") and stale.get("completion_failure") == "stale_pending"
                and pending_path.read_bytes() == stale_before
            )

            completed_path = runtime / "conversation_policy_state" / "completed" / "synthetic-session.json"
            tampered = json.loads(completed_path.read_text(encoding="utf-8"))
            tampered["transition_digest"] = "0" * 64
            completed_path.write_text(json.dumps(tampered, sort_keys=True, indent=2), encoding="utf-8")
            stage_conversation_policy_state(base, operation_id="synthetic-op-4", session_id="synthetic-session")
            invalid_prior = complete_conversation_policy_state(operation_id="synthetic-op-4", session_id="synthetic-session")
            checks["tampered_completed_transition_blocks_promotion"] = bool(
                not invalid_prior.get("completed")
                and invalid_prior.get("completion_failure") == "invalid_previous_completed"
            )

            serialized_files = "".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in runtime.rglob("*.json")
            )
            checks["persisted_records_omit_private_content_canaries"] = not any(
                token in serialized_files for token in (
                    "COGNITIVE_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY"
                )
            )
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old
    return {
        "checks": checks,
        "passed": sum(1 for value in checks.values() if value),
        "total": len(checks),
        "content_free": True,
        "structural_digest": _digest(checks),
    }


def _synthetic_contract_evidence() -> dict[str, Any]:
    cases = {
        "direct_answer": _actual_policy("What is the capital of France?"),
        "explanation": _actual_policy("Explain why the sky appears blue."),
        "clarification": _actual_policy("Which one?"),
        "correction": _actual_policy("No, that is incorrect."),
        "explicit_silence": _actual_policy("Do not respond"),
        "relationship_context": _actual_policy(
            "Continue our discussion.",
            self_model={"style": "warm"},
            memories=[{"relationship_relevant": True, "active": True}],
            history=[{"role": "user"}, {"role": "assistant"}],
        ),
        "forged_silence": _manual_policy(intent="intentional_silence", disposition="intentional_silence"),
        "context_conflict": _manual_policy(intent="follow_up", disposition="answer_then_one_question", conflict=True),
        "authority_tamper": _manual_policy(authority_tamper=True),
        "malformed_components": build_conversation_policy_state(None, object(), []),
    }
    summaries = {name: _public_state_summary(value) for name, value in cases.items()}
    serialized = json.dumps(cases, sort_keys=True, default=str)
    checks = {
        "intent_contract_lineage_is_current": INTENT_CONTRACT_VERSION == "v1156.8",
        "behavior_contract_lineage_is_current": BEHAVIOR_CONTRACT_VERSION == "v1157.8",
        "follow_up_contract_lineage_is_current": FOLLOW_UP_CONTRACT_VERSION == "v1158.8",
        "canonical_policy_contract_lineage_is_current": POLICY_STATE_CONTRACT_VERSION == "v1159.8",
        "all_case_prompts_are_complete": all(row["prompt_envelope_complete"] for row in summaries.values()),
        "all_case_prompts_are_bounded": all(row["prompt_length"] <= POLICY_STATE_MAX_PROMPT_CHARS for row in summaries.values()),
        "all_case_states_preserve_authority": all(row["authority_preserved"] for row in summaries.values()),
        "all_case_states_preserve_precedence": all(row["precedence_preserved"] for row in summaries.values()),
        "all_case_states_have_component_identities": all(row["component_digests_present"] for row in summaries.values()),
        "direct_answer_remains_substantive": summaries["direct_answer"]["output_disposition"] != "intentional_silence",
        "explanation_remains_non_authorizing": summaries["explanation"]["authority_preserved"],
        "clarification_question_budget_is_bounded": summaries["clarification"]["max_follow_up_questions"] <= 1,
        "correction_does_not_create_authority": summaries["correction"]["authority_preserved"],
        "literal_silence_is_verified": summaries["explicit_silence"]["explicit_silence_verified"] and summaries["explicit_silence"]["emit_no_substantive_content"],
        "forged_silence_recovers_to_answer": not summaries["forged_silence"]["explicit_silence_verified"] and summaries["forged_silence"]["output_disposition"] == "answer_only",
        "conflicting_context_suppresses_question": summaries["context_conflict"]["component_conflict_present"] and summaries["context_conflict"]["max_follow_up_questions"] == 0,
        "malformed_components_recover_neutrally": summaries["malformed_components"]["component_recovery_present"] and summaries["malformed_components"]["output_disposition"] == "answer_only",
        "authority_tampering_is_reconstructed_false": summaries["authority_tamper"]["authority_preserved"],
        "private_canaries_are_absent_from_policy_outputs": not any(token in serialized for token in (
            "COGNITIVE_PRIVATE_CANARY", "PROVIDER_PRIVATE_CANARY", "MEMORY_PRIVATE_CANARY"
        )),
        "provider_is_not_contacted_for_policy": all(row["authority_preserved"] for row in summaries.values()),
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


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _contains_forbidden_persisted_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key) in _FORBIDDEN_PERSISTED_KEYS for key in value):
            return True
        return any(_contains_forbidden_persisted_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_persisted_key(item) for item in value)
    return False


def _runtime_policy_summary(runtime: Path) -> dict[str, Any]:
    root = runtime / "conversation_policy_state"
    pending_paths = sorted((root / "pending").glob("*.json"))[:_MAX_RUNTIME_RECORDS_INSPECTED] if root.exists() else []
    completed_paths = sorted((root / "completed").glob("*.json"))[:_MAX_RUNTIME_RECORDS_INSPECTED] if root.exists() else []
    operation_paths = sorted((root / "operations").glob("*.json"))[:_MAX_RUNTIME_RECORDS_INSPECTED] if root.exists() else []
    invalid_pending = 0
    stale_pending = 0
    invalid_completed = 0
    invalid_operations = 0
    forbidden_key_count = 0
    content_flag_count = 0

    now_epoch = int(time.time())
    for path in pending_paths:
        raw = _safe_json(path)
        verified, failure = _load_verified_pending(path, now_epoch=now_epoch)
        invalid_pending += int(verified is None and failure != "stale_pending")
        stale_pending += int(failure == "stale_pending")
        forbidden_key_count += int(_contains_forbidden_persisted_key(raw))
        content_flag_count += int(bool((raw or {}).get("contains_content")))
    for path in completed_paths:
        raw = _safe_json(path)
        invalid_completed += int(_load_verified_completed(path) is None)
        forbidden_key_count += int(_contains_forbidden_persisted_key(raw))
        content_flag_count += int(bool((raw or {}).get("contains_content")))
    for path in operation_paths:
        raw = _safe_json(path)
        invalid_operations += int(_load_verified_completed(path) is None)
        forbidden_key_count += int(_contains_forbidden_persisted_key(raw))
        content_flag_count += int(bool((raw or {}).get("contains_content")))

    truncated = any(len(list(directory.glob("*.json"))) > _MAX_RUNTIME_RECORDS_INSPECTED for directory in (
        root / "pending", root / "completed", root / "operations"
    ) if directory.exists())
    summary = {
        "pending_record_count": len(pending_paths),
        "completed_session_record_count": len(completed_paths),
        "operation_archive_record_count": len(operation_paths),
        "invalid_pending_count": invalid_pending,
        "stale_pending_count": stale_pending,
        "invalid_completed_count": invalid_completed,
        "invalid_operation_archive_count": invalid_operations,
        "forbidden_content_key_count": forbidden_key_count,
        "content_flag_violation_count": content_flag_count,
        "scan_truncated": truncated,
        "record_scan_bound": _MAX_RUNTIME_RECORDS_INSPECTED,
        "all_integrity_checks_pass": all(value == 0 for value in (
            invalid_pending, invalid_completed, invalid_operations,
            forbidden_key_count, content_flag_count,
        )),
        "raw_identifiers_exposed": False,
        "raw_content_exposed": False,
        "content_free": True,
    }
    summary["review_required"] = not summary["all_integrity_checks_pass"] or truncated
    summary["structural_digest"] = _digest(summary)
    return summary


@lru_cache(maxsize=8)
def _static_source_evidence(source_text: str, source_signature: str) -> str:
    del source_signature
    source = Path(source_text)
    runtime_text = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    executable_runtime = "\n".join(
        line for line in runtime_text.splitlines() if not line.lstrip().startswith("#")
    )
    policy_text = (source / "conscious_agent" / "conversation_policy_state.py").read_text(encoding="utf-8")
    payload = {
        "registry": inspect_checkpoint_registry(source_root=source),
        "privacy_policy": source_only_entry_policy(),
        "privacy": package_privacy_summary_for_root(source),
        "integration": {
            "ordinary_runtime_builds_intent_in_both_paths": runtime_text.count("build_response_intent_selection(") == 2,
            "ordinary_runtime_builds_behavior_in_both_paths": runtime_text.count("build_contextual_conversation_behavior(") == 2,
            "ordinary_runtime_builds_follow_up_policy_in_both_paths": runtime_text.count("build_follow_up_silence_policy(") == 2,
            "ordinary_runtime_builds_canonical_policy_in_both_paths": runtime_text.count("build_conversation_policy_state(") == 2,
            "ordinary_runtime_sends_single_canonical_policy_envelope": runtime_text.count('conversation_policy["prompt_section"]') == 2,
            "retired_component_prompt_envelopes_are_not_executable": not any(token in executable_runtime for token in (
                'response_intent["prompt_section"]', 'contextual_behavior["prompt_section"]',
                'follow_up_silence["prompt_section"]',
            )),
            "ordinary_runtime_stages_policy_in_both_paths": runtime_text.count("stage_conversation_policy_state(") == 2,
            "ordinary_runtime_completes_policy_in_both_paths": runtime_text.count("complete_conversation_policy_state(") == 2,
            "ordinary_runtime_records_all_component_diagnostics": all(runtime_text.count(token) == 2 for token in (
                'result.cognitive_context["response_intent"]',
                'result.cognitive_context["contextual_conversation_behavior"]',
                'result.cognitive_context["follow_up_silence_policy"]',
                'result.cognitive_context["conversation_policy_state"]',
            )),
            "ordinary_runtime_records_policy_continuity": runtime_text.count('result.cognitive_context["conversation_policy_continuity"]') == 4,
            "assistant_memory_commit_boundary_remains_present": "assistant_memory_stored" in runtime_text,
            "provider_failure_and_cancellation_boundaries_remain_present": "LocalModelCancelledError" in runtime_text and "cancel_event" in runtime_text,
            "canonical_prompt_is_data_only_and_authority_free": '<conversation_policy_state data_only="true" authority="none">' in policy_text,
            "canonical_projection_reconstructs_authority": all(token in policy_text for token in (
                '"approval_granted": False', '"authorization_granted": False',
                '"execution_permitted": False', '"may_initiate_new_turn": False',
                '"provider_contacted_for_policy": False',
            )),
            "pending_integrity_validation_is_present": "def _load_verified_pending" in policy_text and "stale_pending" in policy_text,
            "completed_transition_integrity_validation_is_present": "def _load_verified_completed" in policy_text and "transition_digest" in policy_text,
            "duplicate_completion_is_idempotent": "duplicate_completion" in policy_text and "operation_session_mismatch" in policy_text,
            "invalid_previous_state_fails_closed": "invalid_previous_completed" in policy_text,
            "persistence_omits_prompt_projection": '"prompt_section"' not in policy_text[policy_text.find("def _canonical_projection"):policy_text.find("def _record_identity")],
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_cognitive_integration_alpha_checkpoint(
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
    persistence = _persistence_contract_evidence()
    runtime_summary = _runtime_policy_summary(runtime)

    limitations = [
        {"limitation_id": "generated-responses-are-not-postvalidated-against-canonical-policy", "status": "open", "current_behavior": "bounded_prompt_construction_contract"},
        {"limitation_id": "intentional-silence-uses-existing-valid-turn-boundary", "status": "open", "current_behavior": "no_provider_free_silent_completion"},
        {"limitation_id": "context-conflict-and-relevance-remain-structural", "status": "open", "current_behavior": "bounded_deterministic_arbitration"},
        {"limitation_id": "policy-continuity-has-no-explicit-cross-process-claim-lock", "status": "open", "current_behavior": "atomic_replace_and_integrity_checks"},
        {"limitation_id": "native-desktop-verification-pending", "status": "open", "next_action": "defer_desktop_codex_review_until_v1200"},
    ]

    checks: list[tuple[str, bool]] = [
        *[(name, bool(value)) for name, value in synthetic["checks"].items()],
        *[(name, bool(value)) for name, value in persistence["checks"].items()],
        *[(name, bool(value)) for name, value in integration.items()],
        ("checkpoint_registry_discovers_cognitive_integration_alpha", int(registry.get("checkpoint_count") or 0) >= 186 and not registry.get("duplicate_checkpoint_ids") and not registry.get("duplicate_builder_targets")),
        ("source_only_policy_excludes_runtime_data", privacy_policy.get("excludes_all_data_directory_entries") is True and not privacy_policy.get("authorizes_package_creation") and not privacy_policy.get("publishes_release")),
        ("current_source_tree_privacy_scan_passes", privacy.get("ok") is True and privacy.get("source_only") is True and privacy.get("forbidden_count") == 0 and privacy.get("private_content_finding_count") == 0),
        ("runtime_policy_state_is_structurally_valid", not runtime_summary.get("review_required")),
        ("remaining_limitations_are_explicit", len(limitations) == 5 and all(row.get("status") == "open" for row in limitations)),
        ("checkpoint_does_not_modify_source_or_runtime", source_before == _tree_signature(source, source_tree=True) and runtime_before == _tree_signature(runtime, source_tree=False)),
    ]
    check_rows = [{"check_id": name, "status": "pass" if value else "fail"} for name, value in checks]
    passed = sum(1 for _, value in checks if value)
    total = len(checks)
    ok = passed == total

    report: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "ok": ok,
        "status": "cognitive_integration_alpha_checkpoint_candidate" if ok else "review_required",
        "passed": passed,
        "total": total,
        "checks": check_rows,
        "summary": {
            "synthetic_contract_check_count": synthetic["total"],
            "synthetic_case_count": synthetic["case_count"],
            "persistence_contract_check_count": persistence["total"],
            "registered_checkpoint_count": registry.get("checkpoint_count", 0),
            "canonical_policy_prompt_maximum_chars": POLICY_STATE_MAX_PROMPT_CHARS,
            "authoritative_conversation_path_count": 2 if integration["ordinary_runtime_builds_canonical_policy_in_both_paths"] else 0,
            "runtime_pending_record_count": runtime_summary["pending_record_count"],
            "runtime_completed_session_record_count": runtime_summary["completed_session_record_count"],
            "runtime_operation_archive_record_count": runtime_summary["operation_archive_record_count"],
            "runtime_integrity_mismatch_count": sum(int(runtime_summary[key]) for key in (
                "invalid_pending_count", "invalid_completed_count", "invalid_operation_archive_count",
                "forbidden_content_key_count", "content_flag_violation_count",
            )),
            "open_limitation_count": len(limitations),
            "privacy_forbidden_entry_count": privacy.get("forbidden_count", 0),
            "privacy_content_finding_count": privacy.get("private_content_finding_count", 0),
        },
        "evidence": {
            "synthetic_contracts": synthetic,
            "persistence_contracts": persistence,
            "ordinary_conversation_integration": integration,
            "runtime_policy_continuity": runtime_summary,
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
        "cognitive_integration_alpha_completed": ok,
        "conversation_and_learning_not_started": True,
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
    ):
        report[field] = False
    report["structural_digest"] = _digest({
        "contract_version": CONTRACT_VERSION,
        "checks": check_rows,
        "summary": report["summary"],
        "limitations": limitations,
        "synthetic_digest": synthetic["structural_digest"],
        "persistence_digest": persistence["structural_digest"],
        "runtime_digest": runtime_summary["structural_digest"],
    })
    serialized = json.dumps(report, sort_keys=True)
    report["forbidden_report_value_count"] = sum(serialized.count(token) for token in _FORBIDDEN_REPORT_VALUES)
    return report
