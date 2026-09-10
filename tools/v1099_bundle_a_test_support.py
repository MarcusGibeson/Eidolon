from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from release_candidate_identity import atomic_json, digest_payload, read_json
from release_authority_consumer import _consumer_key, _consumer_root, _record_digest

IDENTITY = (
    "release-command-deck",
    "eidolon.consumer.command-deck",
    "1.0",
    "display exact release handoff status",
)
REQUIRED = ["general_release"]
UNSUPPORTED = ["installation", "model_specific", "native_windows", "promotion", "provider_ollama"]


def make_receipt(runtime_root: Path, identity=IDENTITY, *, policy_sha256: str = "policy-a"):
    root = _consumer_root(runtime_root, _consumer_key(*identity))
    receipt_id = "receipt-" + digest_payload({"identity": identity})[:16]
    receipt = {
        "schema": "eidolon-release-authority-consumer-receipt-v1",
        "consumer_receipt_id": receipt_id,
        "consumer_receipt_operation_id": "operation-" + digest_payload({"identity": identity})[:16],
        "consumer_id": identity[0],
        "consumer_schema": identity[1],
        "consumer_version": identity[2],
        "expected_use": identity[3],
        "consumer_key_sha256": _consumer_key(*identity),
        "validation_id": "validation-a",
        "validation_binding_sha256": "validation-binding-a",
        "acknowledgment_id": "ack-a",
        "acknowledgment_receipt_sha256": "ack-receipt-a",
        "acknowledgment_expires_at": "2099-01-01T00:00:00+00:00",
        "plan_id": "plan-a",
        "plan_binding_sha256": "plan-binding-a",
        "plan_record_sha256": "plan-record-a",
        "readiness_preview_id": "readiness-a",
        "readiness_generation": 7,
        "readiness_binding_sha256": "readiness-binding-a",
        "candidate_id": "candidate-a",
        "source_manifest_sha256": "source-a",
        "archive_manifest_sha256": "archive-manifest-a",
        "archive_sha256": "archive-a",
        "installation_transaction_id": "",
        "installation_transaction_identity_sha256": "",
        "installed_receipt_sha256": "",
        "target_project_id": "eidolon",
        "target_inventory_sha256": "target-a",
        "promotion_transaction_id": "",
        "promotion_transaction_identity_sha256": "",
        "promotion_receipt_sha256": "",
        "promotion_state_sha256": "promotion-state-a",
        "certification_transaction_id": "certification-a",
        "certification_receipt_sha256": "certification-receipt-a",
        "certification_state_sha256": "certification-state-a",
        "certification_generation": 4,
        "history_sha256": "history-a",
        "history_generation": 9,
        "authority_generation": 11,
        "authority_state_sha256": "authority-a",
        "policy_id": "policy-a",
        "policy_sha256": policy_sha256,
        "policy_generation": 2,
        "migration_preview_id": "migration-a",
        "migration_preview_sha256": "migration-preview-a",
        "scope_statuses_sha256": "scopes-a",
        "evidence_state_sha256": "evidence-a",
        "required_scopes": list(REQUIRED),
        "unsupported_scopes": list(UNSUPPORTED),
        "available_scopes": ["general_release"],
        "grants_authority": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "policy_migration_authorized": False,
        "provider_access_authorized": False,
        "model_access_authorized": False,
        "native_platform_certification_authorized": False,
        "content_free": True,
    }
    receipt["consumer_receipt_sha256"] = _record_digest(receipt, "consumer_receipt_sha256")
    atomic_json(root / "receipts" / f"{receipt_id}.json", receipt)
    atomic_json(root / "active_receipt.json", {
        "schema": receipt["schema"],
        "consumer_receipt_id": receipt_id,
        "consumer_receipt_sha256": receipt["consumer_receipt_sha256"],
        "validation_id": receipt["validation_id"],
        "validation_binding_sha256": receipt["validation_binding_sha256"],
        "content_free": True,
    })
    operation = {
        "schema": "eidolon-release-authority-consumer-receipt-operation-v1",
        "consumer_receipt_operation_id": receipt["consumer_receipt_operation_id"],
        "status": "completed",
        "content_free": True,
    }
    operation["operation_sha256"] = _record_digest(operation, "operation_sha256")
    atomic_json(root / "operations" / f"{operation['consumer_receipt_operation_id']}.json", operation)
    return root, receipt


def current_receipt(runtime_root: Path, identity=IDENTITY):
    root = _consumer_root(runtime_root, _consumer_key(*identity))
    pointer = read_json(root / "active_receipt.json")
    return read_json(root / "receipts" / f"{pointer.get('consumer_receipt_id', '')}.json")


def patch_daily(daily, runtime_root: Path, identity=IDENTITY):
    def receipt_status(*args, **kwargs):
        requested = tuple(args[:4])
        if requested != tuple(identity):
            return {"ok": False, "status": "wrong-consumer", "receipt_present": False}
        receipt = current_receipt(runtime_root, identity)
        return {
            **receipt,
            "ok": True,
            "status": "release_authority_consumer_receipt_current",
            "receipt_present": True,
            "receipt_stale": False,
        }

    def lifecycle_status(*args, **kwargs):
        requested = tuple(args[:4])
        receipt = current_receipt(runtime_root, identity)
        return {
            "ok": requested == tuple(identity),
            "status": "consumer_receipt_lifecycle_current" if requested == tuple(identity) else "wrong-consumer",
            "consumer_receipt_id": receipt.get("consumer_receipt_id", ""),
            "consumer_receipt_sha256": receipt.get("consumer_receipt_sha256", ""),
            "operation_status": "completed",
            "finding_count": 0,
        }

    daily.release_authority_consumer_receipt_status = receipt_status
    daily.consumer_receipt_lifecycle_status = lifecycle_status


def expire_selection(runtime_root: Path, daily, identity=IDENTITY):
    root, pointer, selection = daily._selection_private(runtime_root, identity)
    selection["selection_expires_at"] = "2000-01-01T00:00:00+00:00"
    selection["selection_sha256"] = _record_digest(selection, "selection_sha256")
    atomic_json(root / "selections" / f"{selection['selection_id']}.json", selection)
    pointer["selection_sha256"] = selection["selection_sha256"]
    atomic_json(root / "active_selection.json", pointer)
    return selection


def drift_policy(runtime_root: Path, identity=IDENTITY):
    root = _consumer_root(runtime_root, _consumer_key(*identity))
    pointer = read_json(root / "active_receipt.json")
    receipt = read_json(root / "receipts" / f"{pointer['consumer_receipt_id']}.json")
    receipt["policy_sha256"] = "policy-drifted"
    receipt["consumer_receipt_sha256"] = _record_digest(receipt, "consumer_receipt_sha256")
    atomic_json(root / "receipts" / f"{receipt['consumer_receipt_id']}.json", receipt)
    pointer["consumer_receipt_sha256"] = receipt["consumer_receipt_sha256"]
    atomic_json(root / "active_receipt.json", pointer)
    return receipt
