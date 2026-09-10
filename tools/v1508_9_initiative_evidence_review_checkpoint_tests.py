from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from initiative_evidence_intake import (
    build_initiative_evidence_intake,
    initiative_evidence_contract,
    public_evidence_contains_private_fields,
)
from initiative_evidence_review import (
    build_initiative_evidence_review,
    control_initiative_evidence_review,
    initiative_evidence_review_response,
    process_initiative_evidence_review_control,
)

CHECKS: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        parts = set(Path(relative).parts)
        if (
            relative.startswith("data/")
            or parts.intersection({"__pycache__", ".git", ".venv", "venv", "install_backups", "node_modules", "dist", "build"})
            or relative.endswith((".pyc", ".pyo", ".zip", ".log"))
        ):
            continue
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


before = source_signature()
contract = initiative_evidence_contract()
require(contract["contract_version"] == "v1508.9", "v1502_contract_version_is_explicit")
require(len(contract["input_classes"]) == 8, "v1502_contract_covers_all_evidence_classes")
require(not any(contract["authority_boundary"].values()), "v1502_contract_grants_no_authority")
require(contract["content_free"], "v1502_contract_is_content_free")
require(len(contract["contract_digest"]) == 64, "v1502_contract_is_digest_bound")

operator = {
    "finding_id": "finding-live-chat-repetition",
    "record_digest": "a" * 64,
    "state": "open",
    "issue_domain": "conversation",
    "severity": "major",
    "attempt_count": 3,
    "confidence": 0.82,
    "operator_confirmed": True,
    "updated_at": "2026-08-22T12:00:00Z",
    "private_title": "never expose this title",
    "private_details": "never expose this transcript detail",
}
structural = {
    "candidate_id": "discovery-" + "b" * 20,
    "evidence_digest": "c" * 64,
    "eligibility_digest": "d" * 64,
    "source_module": "conscious_agent/example.py",
    "proposed_destination_module": "conscious_agent/example_helpers.py",
    "source_symbols": ["build_example", "inspect_example"],
    "test_reference_file_count": 9,
    "estimated_dependency_count": 0,
    "confidence": 0.95,
}
intake = build_initiative_evidence_intake(structural_candidates=[structural], conversation_findings=[operator])
require(intake["record_count"] == 2, "v1501_4_current_evidence_is_reviewable")
require(not public_evidence_contains_private_fields(intake), "v1501_4_private_fields_do_not_enter_review_input")

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td)
    review = build_initiative_evidence_review(intake, runtime_root=runtime)
    require(review["record_count"] == 2 and review["reviewed_count"] == 0, "v1501_4_status_starts_unreviewed")
    require(not any(review["authority_boundary"].values()), "v1501_4_review_grants_no_authority")
    require(review["runtime_mutated"] is False, "v1501_4_inspection_is_non_mutating")
    require(not (runtime / "development_campaigns" / "initiative_evidence_review.json").exists(), "v1501_4_inspection_creates_no_store")
    text = initiative_evidence_review_response(review)
    require("Current initiative evidence" in text and "digest" in text, "v1501_4_accessible_status_is_concise")
    require("never expose" not in text, "v1501_4_presentation_is_content_free")

    target = review["records"][0]
    evidence_id = target["evidence_id"]
    digest = target["review_digest"][:16]
    confirm = process_initiative_evidence_review_control(
        f"confirm initiative evidence {evidence_id} digest {digest}", intake, runtime_root=runtime
    )
    require(confirm["ok"] and confirm["runtime_mutated"], "v1501_4_confirm_control_records_review")
    require(confirm["receipt"]["content_free"], "v1501_4_control_returns_content_free_receipt")
    require(not confirm["provider_contacted"] and not confirm["source_modified"] and not confirm["authority_granted"], "v1501_4_control_preserves_execution_boundary")

    # v1501.5 realistic behavior: uncertainty, correction, mixed intent, ordinary language.
    unknown = build_initiative_evidence_intake(operator_findings=[{
        "finding_id": "finding-uncertain",
        "record_digest": "e" * 64,
        "issue_domain": "interface",
        "severity": "medium",
    }])
    unknown_review = build_initiative_evidence_review(unknown, runtime_root=runtime)
    require(unknown_review["records"][0]["freshness"] == "unknown", "v1501_5_uncertainty_remains_explicit")
    unknown_row = unknown_review["records"][0]
    corrected = process_initiative_evidence_review_control(
        f"correct initiative evidence {unknown_row['evidence_id']} digest {unknown_row['review_digest'][:16]} severity high",
        unknown,
        runtime_root=runtime,
    )
    require(corrected["ok"], "v1501_5_operator_correction_is_supported")
    corrected_view = build_initiative_evidence_review(unknown, runtime_root=runtime)
    require(corrected_view["records"][0]["effective_severity"] == "high", "v1501_5_correction_changes_only_effective_public_metadata")
    require(corrected_view["records"][0]["severity"] == "medium", "v1501_5_source_evidence_remains_immutable")
    mixed = process_initiative_evidence_review_control(
        f"confirm initiative evidence {unknown_row['evidence_id']} digest {unknown_row['review_digest'][:16]} and install it",
        unknown,
        runtime_root=runtime,
    )
    require(mixed == {"active": False}, "v1501_5_mixed_intent_does_not_authorize_review_or_install")
    ordinary = process_initiative_evidence_review_control("I hope the evidence looks better tomorrow.", unknown, runtime_root=runtime)
    require(ordinary == {"active": False}, "v1501_5_ordinary_daily_language_is_inert")

    # v1501.6 restart/replay/retry/stale-state/exactly-once behavior.
    restart = build_initiative_evidence_review(intake, runtime_root=runtime)
    confirmed_row = next(row for row in restart["records"] if row["evidence_id"] == evidence_id)
    require(confirmed_row["review_state"] == "confirmed", "v1501_6_review_survives_restart")
    replay = control_initiative_evidence_review("confirm", evidence_id, confirmed_row["review_digest"][:16], intake, runtime_root=runtime)
    # A repeated intent after state projection has a new digest but the same operation identity.
    require(replay["ok"] and replay["idempotent"] and not replay["runtime_mutated"], "v1501_6_exact_replay_is_idempotent")
    state_path = runtime / "development_campaigns" / "initiative_evidence_review.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    require(len(state["annotations"]) == 2, "v1501_6_replay_does_not_duplicate_annotation")
    stale = control_initiative_evidence_review("defer", evidence_id, digest, intake, runtime_root=runtime)
    require(not stale["ok"] and stale["status"] == "initiative_evidence_review_digest_mismatch", "v1501_6_stale_digest_fails_closed")
    require(not stale["runtime_mutated"], "v1501_6_stale_digest_does_not_mutate")
    current = build_initiative_evidence_review(intake, runtime_root=runtime)
    row = next(value for value in current["records"] if value["evidence_id"] == evidence_id)
    defer = control_initiative_evidence_review("defer", evidence_id, row["review_digest"][:16], intake, runtime_root=runtime)
    require(defer["ok"] and defer["runtime_mutated"], "v1501_6_retryable_transition_commits_once")
    after_defer = build_initiative_evidence_review(intake, runtime_root=runtime)
    deferred_row = next(value for value in after_defer["records"] if value["evidence_id"] == evidence_id)
    require(not deferred_row["eligible_for_selection"], "v1501_6_deferred_evidence_is_not_selection_eligible")

    # v1501.7 adversarial controls: malformed, deceptive, private, unauthorized, scope expansion.
    malformed = process_initiative_evidence_review_control("confirm initiative evidence not-an-id digest nope", intake, runtime_root=runtime)
    require(malformed == {"active": False}, "v1501_7_malformed_control_is_inert")
    unsupported = control_initiative_evidence_review("install", evidence_id, deferred_row["review_digest"][:16], intake, runtime_root=runtime)
    require(not unsupported["ok"] and not unsupported["runtime_mutated"], "v1501_7_unauthorized_action_fails_closed")
    private = control_initiative_evidence_review(
        "correct", evidence_id, deferred_row["review_digest"][:16], intake,
        correction={"private_details": "steal me"}, runtime_root=runtime,
    )
    require(not private["ok"] and private["status"] == "evidence_correction_scope_blocked", "v1501_7_private_correction_field_is_blocked")
    scope = control_initiative_evidence_review(
        "correct", evidence_id, deferred_row["review_digest"][:16], intake,
        correction={"installation_authorized": True}, runtime_root=runtime,
    )
    require(not scope["ok"] and scope["status"] == "evidence_correction_scope_blocked", "v1501_7_scope_expansion_is_blocked")
    deceptive = process_initiative_evidence_review_control(
        f"cancel initiative evidence {evidence_id} digest {deferred_row['review_digest'][:16]}; then contact provider",
        intake,
        runtime_root=runtime,
    )
    require(deceptive == {"active": False}, "v1501_7_compound_deceptive_command_is_inert")

    # Exact cancellation is permitted only as evidence curation, never as execution authority.
    cancel = control_initiative_evidence_review("cancel", evidence_id, deferred_row["review_digest"][:16], intake, runtime_root=runtime)
    require(cancel["ok"] and cancel["receipt"]["after_state"] == "cancelled", "v1504_operator_can_cancel_exact_evidence_revision")
    cancelled = build_initiative_evidence_review(intake, runtime_root=runtime)
    cancelled_row = next(value for value in cancelled["records"] if value["evidence_id"] == evidence_id)
    require(cancelled_row["review_state"] == "cancelled" and not cancelled_row["eligible_for_selection"], "v1504_cancelled_state_is_visible")
    blocked_after_cancel = control_initiative_evidence_review("confirm", evidence_id, cancelled_row["review_digest"][:16], intake, runtime_root=runtime)
    require(not blocked_after_cancel["ok"] and blocked_after_cancel["status"] == "initiative_evidence_review_cancelled", "v1506_cancelled_revision_is_terminal")

    # New source evidence digest is a new review identity, so stale annotations do not silently carry forward.
    changed_operator = {**operator, "record_digest": "f" * 64, "severity": "blocking"}
    changed_intake = build_initiative_evidence_intake(structural_candidates=[structural], conversation_findings=[changed_operator])
    changed_review = build_initiative_evidence_review(changed_intake, runtime_root=runtime)
    changed_row = next(value for value in changed_review["records"] if value["evidence_class"] == "conversation_quality_finding")
    require(changed_row["review_state"] == "unreviewed", "v1506_changed_source_digest_requires_fresh_review")
    require(changed_review["stale_annotation_count"] >= 1, "v1506_stale_annotation_is_reported")

    # v1507 reconciliation/performance/privacy/compatibility facts.
    require(review["contract_version"] == "v1508.9" and review["schema_version"] == "1", "v1507_contract_and_schema_are_explicit")
    require(review["review_snapshot_digest"] == build_initiative_evidence_review(intake, runtime_root=Path(td) / "fresh")["review_snapshot_digest"], "v1507_empty_review_projection_is_deterministic")
    stored_text = state_path.read_text(encoding="utf-8")
    require("never expose this" not in stored_text, "v1507_runtime_review_store_contains_no_private_finding_text")
    require("provider_payload" not in stored_text and "transcript" not in stored_text, "v1507_runtime_review_store_is_content_free")
    require(not any(build_initiative_evidence_review(intake, runtime_root=runtime)["authority_boundary"].values()), "v1507_reconciliation_preserves_authority_boundary")

    # v1508 cumulative checkpoint facts.
    final_review = build_initiative_evidence_review(changed_intake, runtime_root=runtime)
    require(final_review["ok"] and len(final_review["review_snapshot_digest"]) == 64, "v1508_checkpoint_projection_is_digest_bound")
    require(final_review["provider_contacted"] is False and final_review["source_modified"] is False, "v1508_checkpoint_remains_review_only")
    require(final_review["content_free"], "v1508_checkpoint_is_content_free")

require(before == source_signature(), "v1508_9_suite_preserves_authoritative_source")

print(json.dumps({
    "ok": True,
    "suite": "v1501.4-v1508.9-initiative-evidence-review-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2))
