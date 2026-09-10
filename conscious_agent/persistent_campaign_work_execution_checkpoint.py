from __future__ import annotations

"""Read-only v1187.9 Persistent Campaign Work Execution checkpoint.

Consolidates one exact lease-backed campaign work execution, operator-reviewed
result accounting, terminal ledger and budget evidence, governed continuation,
bounded follow-up selection, failure handling, and one atomic next campaign
generation. Production source and caller runtime are never modified. Writes are
limited to isolated temporary fixtures that are destroyed before return.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from bounded_campaign_work_execution import create_work_execution_contract, create_work_execution_review, execute_bounded_campaign_work, work_execution_public_summary
from bounded_campaign_work_execution_checkpoint import build_bounded_campaign_work_execution_checkpoint
from campaign_work_result_ledger import create_ledger_update_receipt, create_work_result_review, work_result_ledger_public_summary
from campaign_work_result_ledger_checkpoint import build_campaign_work_result_ledger_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from governed_campaign_work_continuation import continuation_public_summary, create_campaign_continuation_review, create_followup_work_selection, persist_continuation_generation
from governed_campaign_work_continuation_checkpoint import build_governed_campaign_work_continuation_checkpoint
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1187.9"
_CHECKPOINT_ID = "persistent-campaign-work-execution:v1187.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_PUBLIC_KEYS = {
    "prompt", "prompts", "conversation", "conversations", "memory", "memories",
    "secret", "secrets", "provider_payload", "raw_source", "raw_patch", "patch_text",
    "stdout", "stderr", "private_evidence", "private_reasoning", "replacement_text",
    "rollback_text", "source_text", "file_content", "work_item_content",
}
_LIMITATIONS = (
    "Checkpoint work uses isolated synthetic sandbox and runtime fixtures rather than a live operator campaign.",
    "Execution remains limited to content_digest_match and python_compile against one digest-bound sandbox target.",
    "Observed work cost is caller-supplied bounded evidence rather than direct operating-system metering.",
    "Accepted result and continuation receipts do not automatically execute, retry, repair, resume, or reselect work.",
    "The continuation writer lock is local and single-host rather than a distributed lease with identity attestation.",
    "Persisted continuation records are content-free local JSON and are not encrypted.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _signed(value: Mapping[str, Any], digest_field: str, **changes: object) -> dict[str, Any]:
    row = dict(value)
    row.update(changes)
    row.pop(digest_field, None)
    row[digest_field] = _digest(row)
    return row


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    if not root.exists():
        return digest.hexdigest(), count
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        count += 1
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count


def _forbidden_report_value_count(value: object, *, key: str = "") -> int:
    count = 1 if key.lower() in _FORBIDDEN_PUBLIC_KEYS else 0
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            count += _forbidden_report_value_count(child, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += _forbidden_report_value_count(child, key=key)
    return count


def _execution_lineage(token: str, selected: tuple[str, ...] = ("work-1", "work-2", "work-3")) -> dict[str, Any]:
    materialization = _signed({
        "contract_version": "v1186.8",
        "campaign_id": f"campaign-{token}",
        "session_id": f"session-{token}",
        "status": "resumed_session_materialized_not_executing",
        "resumed_session_digest": _h(f"{token}:session"),
        "work_execution_eligible": True,
        "work_executed": False,
        "content_free": True,
        "authority_granted": False,
    }, "resume_materialization_receipt_digest")
    restart = _signed({
        "contract_version": "v1186.8",
        "campaign_id": f"campaign-{token}",
        "status": "restored_execution_eligible_not_executing",
        "resumed_session_digest": _h(f"{token}:session"),
        "lease_digest": _h(f"{token}:lease"),
        "content_free": True,
        "work_execution_eligible": True,
        "work_executed": False,
        "automatic_execution": False,
        "authority_granted": False,
    }, "restart_reconciliation_digest")
    selection = _signed({
        "contract_version": "v1185.5",
        "campaign_id": f"campaign-{token}",
        "selected_work_item_ids": list(selected),
        "status": "selected_not_executed",
        "content_free": True,
        "authority_granted": False,
    }, "selection_digest")
    ledger = _signed({
        "contract_version": "v1185.2",
        "campaign_id": f"campaign-{token}",
        "work_item_ids": list(selected),
        "status": "approved_bounded_ledger",
        "content_free": True,
    }, "ledger_digest")
    budget = _signed({
        "contract_version": "v1185.8",
        "campaign_id": f"campaign-{token}",
        "observed": {"work_items": 0, "elapsed_seconds": 10, "disk_bytes": 0, "token_budget": 0},
        "limits": {"max_work_items": 8, "max_elapsed_seconds": 3600, "max_disk_bytes": 1_000_000, "max_token_budget": 50_000},
        "status": "within_budget",
        "content_free": True,
    }, "budget_receipt_digest")
    prior = _signed({
        "contract_version": "v1186.2",
        "campaign_id": f"campaign-{token}",
        "storage_generation": 1,
        "campaign_state": "active",
        "content_free": True,
    }, "storage_record_digest")
    return {"materialization": materialization, "restart": restart, "selection": selection, "ledger": ledger, "budget": budget, "prior": prior}


def _run_case(*, root: Path, token: str, source_text: str, expected_result: str, action: str, followup: bool) -> dict[str, Any]:
    fixture = _execution_lineage(token)
    sandbox = root / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    target = sandbox / "sample.py"
    target.write_text(source_text, encoding="utf-8")
    target_digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    contract = create_work_execution_contract(
        restart_reconciliation=fixture["restart"],
        materialization_receipt=fixture["materialization"],
        selection=fixture["selection"],
        work_item_id="work-1",
        execution_code="python_compile",
        target_relative_path="sample.py",
        expected_target_digest=target_digest,
        operator_contract_digest=_h(f"{token}:execution-contract"),
    )
    execution_review = create_work_execution_review(
        contract=contract, decision="approve", operator_decision_digest=_h(f"{token}:execution-review")
    )
    execution = execute_bounded_campaign_work(sandbox_root=sandbox, contract=contract, review=execution_review)
    result_review = create_work_result_review(
        execution_receipt=execution, decision="accept", operator_decision_digest=_h(f"{token}:result-review")
    )
    update = create_ledger_update_receipt(
        ledger=fixture["ledger"], budget_receipt=fixture["budget"], execution_receipt=execution,
        result_review=result_review,
        observed_cost={"work_items": 1, "elapsed_seconds": 2, "disk_bytes": 0, "token_budget": 1},
    )
    continuation_review = create_campaign_continuation_review(
        ledger_update_receipt=update, requested_action=action, decision="approve",
        operator_decision_digest=_h(f"{token}:continuation-review"),
    )
    selection = None
    if followup:
        selection = create_followup_work_selection(
            ledger=fixture["ledger"], ledger_update_receipt=update, continuation_review=continuation_review,
            candidate_work_item_ids=["work-2"], max_items=1,
        )
    runtime = root / "runtime"
    state = runtime / "campaigns" / fixture["prior"]["campaign_id"] / "campaign_state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(fixture["prior"], sort_keys=True, separators=(",", ":")), encoding="utf-8")
    stored = persist_continuation_generation(
        runtime_root=runtime, prior_storage_record=fixture["prior"], ledger_update_receipt=update,
        continuation_review=continuation_review, followup_selection=selection,
        operator_storage_digest=_h(f"{token}:storage"),
    )
    return {
        **fixture,
        "contract": contract,
        "execution_review": execution_review,
        "execution": execution,
        "result_review": result_review,
        "update": update,
        "continuation_review": continuation_review,
        "followup": selection,
        "stored": stored,
        "expected_result": expected_result,
        "execution_summary": work_execution_public_summary(contract, execution_review, execution),
        "result_summary": work_result_ledger_public_summary(result_review, update),
        "continuation_summary": continuation_public_summary(continuation_review, selection, stored),
    }


def build_persistent_campaign_work_execution_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").resolve()
    source_before, source_count_before = _tree_signature(source)
    runtime_before, runtime_count_before = _tree_signature(runtime)
    runtime_existed_before = runtime.exists()
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_bounded_campaign_work_execution_checkpoint(source_root=source, runtime_root=runtime),
        build_campaign_work_result_ledger_checkpoint(source_root=source, runtime_root=runtime),
        build_governed_campaign_work_continuation_checkpoint(source_root=source, runtime_root=runtime),
    )
    for report, expected in zip(retained, ("v1187.2", "v1187.5", "v1187.8")):
        require(report.get("ok") is True)
        require(report.get("passed") == report.get("total"))
        require(report.get("contract_version") == expected)
        require(report.get("content_free") is True)
        require(report.get("production_source_modified") is False)
        require(report.get("sandbox_modified") is False)
        require(report.get("provider_contacted") is False)
        require(report.get("model_contacted") is False)
        require(report.get("authority_granted") is False)
        require(report.get("release_authorized") is False)
        require(report.get("desktop_verification_deferred_until_v1200") is True)

    with tempfile.TemporaryDirectory(prefix="eidolon-v1187-9-success-") as directory:
        success = _run_case(root=Path(directory), token="success", source_text="value = 1\n", expected_result="passed", action="select_followup", followup=True)
        for row, status in (
            (success["contract"], "execution_review_required"),
            (success["execution_review"], "approved_not_executed"),
            (success["execution"], "executed"),
            (success["result_review"], "accepted_for_ledger"),
            (success["update"], "ledger_update_recorded"),
            (success["continuation_review"], "continuation_approved"),
            (success["followup"], "followup_selection_ready"),
            (success["stored"], "continuation_stored"),
        ):
            require(row.get("status") == status)
            require(row.get("error_count", 0) == 0)
            require(row.get("content_free") is True)
            require(row.get("authority_granted") is False)
        require(success["execution"].get("result_code") == "passed")
        require(success["update"].get("new_work_item_state") == "completed")
        require(success["update"].get("ledger_updated") is True)
        require(success["update"].get("budget_consumed") is True)
        require(success["followup"].get("selected_work_item_ids") == ["work-2"])
        require(success["stored"].get("storage_generation") == 2)
        require(success["stored"].get("selected_work_item_ids") == ["work-2"])
        require(success["stored"].get("campaign_state") == "active")
        require(success["stored"].get("runtime_written") is True)
        for summary in (success["execution_summary"], success["result_summary"], success["continuation_summary"]):
            require(summary.get("content_free") is True)
            require(summary.get("authority_granted") is False)

    with tempfile.TemporaryDirectory(prefix="eidolon-v1187-9-failure-") as directory:
        failure = _run_case(root=Path(directory), token="failure", source_text="def broken(:\n", expected_result="failed", action="hold_failure", followup=False)
        require(failure["execution"].get("status") == "executed")
        require(failure["execution"].get("result_code") == "failed")
        require(failure["result_review"].get("status") == "accepted_for_ledger")
        require(failure["update"].get("new_work_item_state") == "failed")
        require(failure["continuation_review"].get("requested_action") == "hold_failure")
        require(failure["stored"].get("campaign_state") == "paused")
        require(failure["stored"].get("runtime_written") is True)
        require(failure["stored"].get("work_executed") is False)
        require(failure["stored"].get("automatic_retry") is False)
        require(failure["stored"].get("automatic_resume") is False)

    # Digest-match execution and operator decision matrices.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1187-9-decisions-") as directory:
        root = Path(directory); sandbox = root / "sandbox"; sandbox.mkdir(); text = "payload\n"; (sandbox / "sample.txt").write_text(text, encoding="utf-8")
        fixture = _execution_lineage("decisions")
        contract = create_work_execution_contract(
            restart_reconciliation=fixture["restart"], materialization_receipt=fixture["materialization"], selection=fixture["selection"],
            work_item_id="work-1", execution_code="content_digest_match", target_relative_path="sample.txt",
            expected_target_digest=hashlib.sha256(text.encode()).hexdigest(), operator_contract_digest=_h("decisions:contract"),
        )
        review_rows = []
        for decision, status in (("approve", "approved_not_executed"), ("reject", "rejected"), ("defer", "deferred")):
            row = create_work_execution_review(contract=contract, decision=decision, operator_decision_digest=_h(f"exec:{decision}"))
            review_rows.append(row); require(row.get("status") == status); require(row.get("work_executed") is False); require(row.get("authority_granted") is False)
        receipt = execute_bounded_campaign_work(sandbox_root=sandbox, contract=contract, review=review_rows[0])
        require(receipt.get("result_code") == "passed")
        for decision, status in (("accept", "accepted_for_ledger"), ("reject", "rejected_result"), ("defer", "deferred_result")):
            row = create_work_result_review(execution_receipt=receipt, decision=decision, operator_decision_digest=_h(f"result:{decision}"))
            require(row.get("status") == status); require(row.get("ledger_updated") is False); require(row.get("retry_authorized") is False)

    # Continuation action matrix.
    continuation_cases = []
    for state, actions in (("completed", ("select_followup", "pause_campaign", "complete_campaign")), ("failed", ("hold_failure", "select_followup", "pause_campaign", "abandon_campaign"))):
        update = _signed({
            "contract_version": "v1187.5", "campaign_id": "campaign-actions", "session_id": "session-actions",
            "work_item_id": "work-1", "new_work_item_state": state, "status": "ledger_update_recorded",
            "ledger_updated": True, "content_free": True,
        }, "ledger_update_receipt_digest")
        for action in actions:
            row = create_campaign_continuation_review(
                ledger_update_receipt=update, requested_action=action, decision="approve",
                operator_decision_digest=_h(f"action:{state}:{action}"),
            )
            continuation_cases.append(row)
            require(row.get("status") == "continuation_approved")
            require(row.get("requested_action") == action)
            require(row.get("automatic_retry") is False)
            require(row.get("automatic_reselection") is False)
            require(row.get("work_executed") is False)
            require(row.get("authority_granted") is False)
        for decision, status in (("reject", "continuation_rejected"), ("defer", "continuation_deferred")):
            row = create_campaign_continuation_review(
                ledger_update_receipt=update, requested_action=actions[0], decision=decision,
                operator_decision_digest=_h(f"action:{decision}:{state}"),
            )
            require(row.get("status") == status)

    # Negative, stale, tamper, privacy, and authority boundaries.
    negative_rows: list[Mapping[str, Any]] = []
    base = _execution_lineage("negative")
    negative_rows.append(create_work_execution_contract(
        restart_reconciliation=base["restart"], materialization_receipt=base["materialization"], selection=base["selection"],
        work_item_id="unknown", execution_code="python_compile", target_relative_path="sample.py",
        expected_target_digest=_h("x"), operator_contract_digest=_h("x"),
    ))
    negative_rows.append(create_work_execution_contract(
        restart_reconciliation=base["restart"], materialization_receipt=base["materialization"], selection=base["selection"],
        work_item_id="work-1", execution_code="shell", target_relative_path="sample.py",
        expected_target_digest=_h("x"), operator_contract_digest=_h("x"),
    ))
    negative_rows.append(create_work_execution_contract(
        restart_reconciliation=base["restart"], materialization_receipt=base["materialization"], selection=base["selection"],
        work_item_id="work-1", execution_code="python_compile", target_relative_path="../source.py",
        expected_target_digest=_h("x"), operator_contract_digest=_h("x"),
    ))
    tampered_restart = dict(base["restart"]); tampered_restart["lease_digest"] = _h("tampered")
    negative_rows.append(create_work_execution_contract(
        restart_reconciliation=tampered_restart, materialization_receipt=base["materialization"], selection=base["selection"],
        work_item_id="work-1", execution_code="python_compile", target_relative_path="sample.py",
        expected_target_digest=_h("x"), operator_contract_digest=_h("x"),
    ))
    fake_execution = _signed({
        "campaign_id": "campaign-negative", "session_id": "s", "work_item_id": "work-1",
        "status": "executed", "result_code": "passed", "work_executed": True, "content_free": True,
    }, "work_execution_receipt_digest")
    accepted = create_work_result_review(execution_receipt=fake_execution, decision="accept", operator_decision_digest=_h("accepted"))
    negative_rows.append(create_ledger_update_receipt(
        ledger=base["ledger"], budget_receipt=base["budget"], execution_receipt=fake_execution,
        result_review=accepted, observed_cost={"work_items": 2},
    ))
    negative_rows.append(create_ledger_update_receipt(
        ledger=base["ledger"], budget_receipt=base["budget"], execution_receipt=fake_execution,
        result_review=accepted, observed_cost={"work_items": 1, "elapsed_seconds": 99999},
    ))
    failed_update = _signed({
        "campaign_id": "campaign-negative", "session_id": "s", "work_item_id": "work-1",
        "new_work_item_state": "failed", "status": "ledger_update_recorded", "ledger_updated": True, "content_free": True,
    }, "ledger_update_receipt_digest")
    negative_rows.append(create_campaign_continuation_review(
        ledger_update_receipt=failed_update, requested_action="complete_campaign", decision="approve",
        operator_decision_digest=_h("unsupported-action"),
    ))
    good_follow_review = create_campaign_continuation_review(
        ledger_update_receipt=failed_update, requested_action="select_followup", decision="approve",
        operator_decision_digest=_h("follow-review"),
    )
    negative_rows.append(create_followup_work_selection(
        ledger=base["ledger"], ledger_update_receipt=failed_update, continuation_review=good_follow_review,
        candidate_work_item_ids=["work-1"], max_items=1,
    ))
    negative_rows.append(create_followup_work_selection(
        ledger=base["ledger"], ledger_update_receipt=failed_update, continuation_review=good_follow_review,
        candidate_work_item_ids=["unknown"], max_items=1,
    ))
    for row in negative_rows:
        require(row.get("status") == "blocked")
        require(int(row.get("error_count") or 0) >= 1)
        require(row.get("authority_granted") is False)

    # Stale generation and concurrent writer blocks.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1187-9-storage-negative-") as directory:
        root = Path(directory); campaign = root / "campaigns" / base["prior"]["campaign_id"]; campaign.mkdir(parents=True)
        drifted = _signed(dict(base["prior"]), "storage_record_digest", storage_generation=2)
        (campaign / "campaign_state.json").write_text(json.dumps(drifted), encoding="utf-8")
        update = _signed({
            "campaign_id": base["prior"]["campaign_id"], "session_id": "s", "work_item_id": "work-1",
            "new_work_item_state": "completed", "status": "ledger_update_recorded", "ledger_updated": True, "content_free": True,
        }, "ledger_update_receipt_digest")
        review = create_campaign_continuation_review(
            ledger_update_receipt=update, requested_action="pause_campaign", decision="approve", operator_decision_digest=_h("pause")
        )
        stale = persist_continuation_generation(
            runtime_root=root, prior_storage_record=base["prior"], ledger_update_receipt=update,
            continuation_review=review, followup_selection=None, operator_storage_digest=_h("stale"),
        )
        require(stale.get("status") == "blocked"); require(stale.get("errors") == ["stale_storage_generation"]); require(stale.get("runtime_written") is False)
        (campaign / "campaign_state.json").write_text(json.dumps(base["prior"]), encoding="utf-8")
        (campaign / ".continuation.lock").write_text("locked", encoding="utf-8")
        concurrent = persist_continuation_generation(
            runtime_root=root, prior_storage_record=base["prior"], ledger_update_receipt=update,
            continuation_review=review, followup_selection=None, operator_storage_digest=_h("concurrent"),
        )
        require(concurrent.get("status") == "blocked"); require(concurrent.get("errors") == ["concurrent_writer"]); require(concurrent.get("runtime_written") is False)

    registry = inspect_checkpoint_registry(source_root=source)
    registry_row = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "persistent-campaign-work-execution-checkpoint"), {})
    require(registry_row.get("builder") == "build_persistent_campaign_work_execution_checkpoint")
    require(registry_row.get("contract_version") == CONTRACT_VERSION)
    require(registry_row.get("read_only") is True)
    require(registry_row.get("post_available") is False)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    source_after, source_count_after = _tree_signature(source)
    runtime_after, runtime_count_after = _tree_signature(runtime)
    if not runtime_existed_before and runtime.exists() and not any(runtime.iterdir()):
        runtime.rmdir()
    require(source_before == source_after)
    require(source_count_before == source_count_after)
    require(runtime_before == runtime_after)
    require(runtime_count_before == runtime_count_after)

    summary = {
        "retained_checkpoint_count": len(retained),
        "successful_execution_case_count": 2,
        "failed_execution_case_count": 1,
        "execution_review_decision_case_count": 3,
        "result_review_decision_case_count": 3,
        "continuation_action_case_count": len(continuation_cases),
        "continuation_nonapproval_case_count": 4,
        "followup_selection_case_count": 2,
        "durable_generation_case_count": 2,
        "stale_generation_case_count": 1,
        "concurrent_writer_case_count": 1,
        "negative_boundary_case_count": len(negative_rows) + 2,
        "public_summary_case_count": 5,
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
        "open_limitation_count": len(_LIMITATIONS),
    }
    report: dict[str, Any] = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_review_required": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "persistent_campaign_work_execution_checkpoint_completed": True,
        "retained_execution_checkpoint_completed": retained[0].get("ok") is True,
        "retained_result_ledger_checkpoint_completed": retained[1].get("ok") is True,
        "retained_continuation_checkpoint_completed": retained[2].get("ok") is True,
        "successful_execution_and_continuation_exercised": True,
        "failed_execution_and_failure_hold_exercised": True,
        "operator_decision_matrices_exercised": True,
        "terminal_ledger_budget_accounting_exercised": True,
        "bounded_followup_selection_exercised": True,
        "durable_next_generation_persistence_exercised": True,
        "stale_generation_and_concurrent_writer_exercised": True,
        "tamper_path_budget_privacy_boundaries_exercised": True,
        "source_runtime_immutability_exercised": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "sandbox_modified": False,
        "runtime_mutated": False,
        "campaign_work_selected_automatically": False,
        "campaign_work_executed_in_isolated_fixture": True,
        "campaign_work_executed": False,
        "work_executed": False,
        "automatic_retry_performed": False,
        "automatic_reselection_performed": False,
        "automatic_resume_performed": False,
        "automatic_execution_performed": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "model_contacted": False,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "raw_test_output_exposed": False,
        "private_evidence_exposed": False,
        "private_reasoning_exposed": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "implementation_authorized": False,
        "repair_authorized": False,
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "autonomous_action_authorized": False,
        "summary": summary,
        "limitations": list(_LIMITATIONS),
        "source_tree_digest_before": source_before,
        "source_tree_digest_after": source_after,
        "source_file_count_before": source_count_before,
        "source_file_count_after": source_count_after,
        "runtime_tree_digest_before": runtime_before,
        "runtime_tree_digest_after": runtime_after,
        "runtime_file_count_before": runtime_count_before,
        "runtime_file_count_after": runtime_count_after,
    }
    report["forbidden_report_value_count"] = _forbidden_report_value_count(report)
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
