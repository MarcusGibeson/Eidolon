from __future__ import annotations

"""Installed-state reconciliation for exact installation transactions."""

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import digest_payload, read_json, runtime_data_root
    from release_installation_recovery import inspect_installation_transaction
    from release_installation_staging import installation_staging_status
    from release_installation_transaction import active_transaction_private, transaction_directory
    from release_installation_preview import _target_inventory
except ImportError:
    from release_candidate_identity import digest_payload, read_json, runtime_data_root
    from release_installation_recovery import inspect_installation_transaction
    from release_installation_staging import installation_staging_status
    from release_installation_transaction import active_transaction_private, transaction_directory
    from release_installation_preview import _target_inventory

INSTALLED_STATE_CONTRACT_VERSION = "1"
KNOWN_INSTALLATION_STATES = (
    "not_staged", "staged", "applying", "interrupted", "uncertain",
    "rollback_ready", "rolled_back", "installed_unpromoted", "promoted", "partially_certified", "certified",
)


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []: found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _receipt_digest(receipt: Mapping[str, Any]) -> str:
    material = dict(receipt); material.pop("receipt_sha256", None)
    return digest_payload(material)


def installed_state_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    stage = installation_staging_status(runtime_root=runtime_root)
    recovery = inspect_installation_transaction(runtime_root=runtime_root)
    _, transaction = active_transaction_private(runtime_root)
    findings: list[dict[str, Any]] = []
    receipt_pointer = read_json(transaction_directory(runtime_root) / "active_installed_receipt.json")
    transaction_id = str(transaction.get("transaction_id") or receipt_pointer.get("transaction_id") or "")
    receipt = read_json(transaction_directory(runtime_root) / "installed_receipts" / f"{transaction_id}.json") if transaction_id else {}
    receipt_valid = False
    target_inventory_sha = ""
    if receipt:
        receipt_valid = str(receipt.get("receipt_sha256") or "") == _receipt_digest(receipt)
        if not receipt_valid: findings.append({"kind": "installed_receipt_digest_mismatch"})
        if str(receipt_pointer.get("receipt_sha256") or "") != str(receipt.get("receipt_sha256") or ""): findings.append({"kind": "installed_receipt_pointer_mismatch"})
        for field in ("transaction_id", "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256", "target_project_id", "effects_sha256"):
            if transaction and str(receipt.get(field) or "") != str(transaction.get(field) or ""): findings.append({"kind": f"installed_receipt_{field}_mismatch"})
        root = Path(str(transaction.get("target_root_path") or ""))
        inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
        target_inventory_sha = str(inventory.get("digest") or "")
        expected_inventory = str(receipt.get("target_inventory_sha256") or "")
        if str(receipt.get("state") or "") == "installed_unpromoted" and target_inventory_sha != expected_inventory:
            findings.append({"kind": "installed_target_drift"})
    tx_state = str(transaction.get("state") or "")
    recovery_status = str(recovery.get("status") or "")
    promotion_state = {}
    promotion_pointer = {}
    if transaction and receipt_valid:
        promotion_root = runtime_data_root(runtime_root) / "release_promotion"
        promotion_pointer = read_json(promotion_root / "active_promotion_state.json")
        promotion_state_id = str(promotion_pointer.get("state_id") or "")
        promotion_state = read_json(promotion_root / "states" / f"{promotion_state_id}.json") if promotion_state_id else {}
        if promotion_state:
            material = dict(promotion_state); expected_state_sha = str(material.pop("state_sha256", ""))
            if expected_state_sha != digest_payload(material): findings.append({"kind": "promotion_state_digest_mismatch"})
            if str(promotion_pointer.get("state_sha256") or "") != expected_state_sha: findings.append({"kind": "promotion_state_pointer_mismatch"})
            for field in ("candidate_id", "target_project_id", "target_inventory_sha256"):
                source_value = receipt.get(field) if field != "target_inventory_sha256" else receipt.get("target_inventory_sha256")
                if str(promotion_state.get(field) or "") != str(source_value or ""): findings.append({"kind": f"promotion_state_{field}_mismatch"})
            if bool(promotion_state.get("certified")) and str(promotion_state.get("state") or "") != "certified": findings.append({"kind": "promotion_certification_evidence_mismatch"})
    if not transaction:
        state = "staged" if stage.get("ok") else "not_staged"
    elif findings or recovery_status == "uncertain": state = "uncertain"
    elif tx_state == "installed_unpromoted" and receipt_valid:
        authority_state = str(promotion_state.get("state") or "")
        if authority_state == "certified" and bool(promotion_state.get("certified")): state = "certified"
        elif authority_state == "partially_certified" and bool(promotion_state.get("certified")): state = "partially_certified"
        elif authority_state == "promoted_uncertified" and not bool(promotion_state.get("certified")): state = "promoted"
        else: state = "installed_unpromoted"
    elif tx_state == "rolled_back" or str(receipt.get("state") or "") == "rolled_back": state = "rolled_back"
    elif recovery_status == "rollback_ready": state = "rollback_ready"
    elif tx_state in {"applying", "rolling_back"}: state = "applying"
    elif tx_state in {"interrupted", "rollback_interrupted"}: state = "interrupted"
    else: state = "uncertain"
    contradictions = _counts(findings)
    installed = state in {"installed_unpromoted", "promoted", "partially_certified", "certified"}
    return {
        "ok": not contradictions and state != "uncertain",
        "status": state,
        "contract_version": INSTALLED_STATE_CONTRACT_VERSION,
        "known_states": list(KNOWN_INSTALLATION_STATES),
        "transaction_present": bool(transaction), "transaction_id": transaction_id,
        "transaction_identity_sha256": str(transaction.get("transaction_identity_sha256") or ""),
        "candidate_id": str(transaction.get("candidate_id") or receipt.get("candidate_id") or stage.get("candidate_id") or ""),
        "packaged_version": str(transaction.get("packaged_version") or receipt.get("packaged_version") or stage.get("packaged_version") or ""),
        "archive_sha256": str(transaction.get("archive_sha256") or receipt.get("archive_sha256") or stage.get("archive_sha256") or ""),
        "source_manifest_sha256": str(transaction.get("source_manifest_sha256") or receipt.get("source_manifest_sha256") or stage.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(transaction.get("archive_manifest_sha256") or receipt.get("archive_manifest_sha256") or stage.get("archive_manifest_sha256") or ""),
        "target_project_id": str(transaction.get("target_project_id") or receipt.get("target_project_id") or stage.get("target_project_id") or ""),
        "target_inventory_sha256": target_inventory_sha or str(receipt.get("target_inventory_sha256") or ""),
        "installed_receipt_present": bool(receipt), "installed_receipt_valid": receipt_valid, "installed_receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "staged": state == "staged", "applying": state == "applying", "interrupted": state == "interrupted",
        "uncertain": state == "uncertain", "rollback_ready": state == "rollback_ready", "rolled_back": state == "rolled_back",
        "installed": installed, "installed_unpromoted": state == "installed_unpromoted",
        "promoted": state in {"promoted", "partially_certified", "certified"}, "partially_certified": state == "partially_certified", "certified": state in {"partially_certified", "certified"},
        "promotion_actions_available": state == "installed_unpromoted", "certification_actions_available": state == "promoted",
        "promotion_state_generation": int(promotion_state.get("generation") or 0), "promotion_state_sha256": str(promotion_state.get("state_sha256") or ""),
        "installation_inferred_from_source_similarity": False, "installation_inferred_from_archive_filename": False,
        "installation_inferred_from_candidate_or_staging_record": False,
        "contradictions": contradictions, "contradiction_count": sum(int(x["count"]) for x in contradictions),
        "paths_suppressed": True, "records_external": True, "content_free": True,
        "ordinary_conversation_affected": False, "provider_contacted": False,
    }
