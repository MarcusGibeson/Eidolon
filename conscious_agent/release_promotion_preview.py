from __future__ import annotations

"""Read-only promotion impact preview bound to exact installed evidence.

Promotion changes authority metadata only. It never copies, replaces, removes, or
rewrites installed source files and never implies certification.
"""

from collections import Counter
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import _target_inventory
    from release_installation_transaction import active_transaction_private, transaction_directory
    from release_installed_state import _receipt_digest, installed_state_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import _target_inventory
    from release_installation_transaction import active_transaction_private, transaction_directory
    from release_installed_state import _receipt_digest, installed_state_status

PROMOTION_PREVIEW_CONTRACT_VERSION = "1"
PROMOTION_DIRECTORY = "release_promotion"
PROMOTION_PREVIEW_SCHEMA = "eidolon-promotion-impact-preview-v1"
PROMOTION_STATE_SCHEMA = "eidolon-promotion-authority-state-v1"


def promotion_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / PROMOTION_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows or []:
        counts[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": counts[key]} for key in sorted(counts)]


def _record_digest(record: Mapping[str, Any], field: str) -> str:
    material = dict(record)
    material.pop(field, None)
    return digest_payload(material)


def current_promotion_state_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = promotion_directory(runtime_root)
    pointer = read_json(directory / "active_promotion_state.json")
    state_id = str(pointer.get("state_id") or "")
    record = read_json(directory / "states" / f"{state_id}.json") if state_id else {}
    return pointer, record


def _promotion_state_material(runtime_root: str | Path | None, installed: Mapping[str, Any]) -> dict[str, Any]:
    pointer, state = current_promotion_state_private(runtime_root)
    if state:
        material = dict(state)
        expected_state_sha256 = str(material.pop("state_sha256", ""))
        state_digest_valid = bool(expected_state_sha256 and expected_state_sha256 == digest_payload(material))
        return {
            "generation": int(state.get("generation") or 0),
            "state_id": str(state.get("state_id") or ""),
            "state": str(state.get("state") or ""),
            "state_sha256": str(state.get("state_sha256") or ""),
            "pointer_generation": int(pointer.get("generation") or 0),
            "pointer_state_sha256": str(pointer.get("state_sha256") or ""),
            "state_digest_valid": state_digest_valid,
        }
    return {
        "generation": 0,
        "state_id": "",
        "state": "installed_unpromoted",
        "state_sha256": digest_payload({
            "contract": "eidolon-initial-promotion-state-v1",
            "target_project_id": str(installed.get("target_project_id") or ""),
            "transaction_identity_sha256": str(installed.get("transaction_identity_sha256") or ""),
            "installed_receipt_sha256": str(installed.get("installed_receipt_sha256") or ""),
            "state": "installed_unpromoted",
            "generation": 0,
        }),
        "pointer_generation": 0,
        "pointer_state_sha256": "",
        "state_digest_valid": True,
    }


def _metadata_effects(installed: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"kind": "authority_metadata", "field": "promoted_version", "old": "", "new": str(installed.get("packaged_version") or "")},
        {"kind": "authority_metadata", "field": "promotion_state", "old": "installed_unpromoted", "new": "promoted_uncertified"},
        {"kind": "authority_metadata", "field": "promotion_evidence", "old": "absent", "new": "exact_external_receipt"},
    ]


def _preview_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-promotion-preview-binding-v1",
        "preview_id": str(record.get("preview_id") or ""),
        "generation": int(record.get("generation") or 0),
        "transaction_id": str(record.get("transaction_id") or ""),
        "transaction_generation": int(record.get("transaction_generation") or 0),
        "transaction_identity_sha256": str(record.get("transaction_identity_sha256") or ""),
        "transaction_state_sha256": str(record.get("transaction_state_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_identity_sha256": str(record.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "effects_sha256": str(record.get("effects_sha256") or ""),
        "previous_promotion_generation": int(record.get("previous_promotion_generation") or 0),
        "previous_promotion_state_sha256": str(record.get("previous_promotion_state_sha256") or ""),
        "previous_promotion_state": str(record.get("previous_promotion_state") or ""),
        "proposed_promotion_state": str(record.get("proposed_promotion_state") or ""),
        "metadata_effects_sha256": str(record.get("metadata_effects_sha256") or ""),
        "promotion_policy_sha256": str(record.get("promotion_policy_sha256") or ""),
    })


def _public(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_previewed"),
        "contract_version": PROMOTION_PREVIEW_CONTRACT_VERSION,
        "preview_present": bool(row),
        "preview_id": str(row.get("preview_id") or ""),
        "preview_binding_sha256": str(row.get("preview_binding_sha256") or ""),
        "generation": int(row.get("generation") or 0),
        "transaction_id": str(row.get("transaction_id") or ""),
        "transaction_identity_sha256": str(row.get("transaction_identity_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "packaged_version": str(row.get("packaged_version") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "source_manifest_sha256": str(row.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(row.get("archive_manifest_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "target_inventory_sha256": str(row.get("target_inventory_sha256") or ""),
        "effects_sha256": str(row.get("effects_sha256") or ""),
        "metadata_effect_count": len(row.get("metadata_effects") or []),
        "metadata_effects_sha256": str(row.get("metadata_effects_sha256") or ""),
        "previous_promotion_generation": int(row.get("previous_promotion_generation") or 0),
        "previous_promotion_state": str(row.get("previous_promotion_state") or ""),
        "proposed_promotion_state": str(row.get("proposed_promotion_state") or ""),
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "source_file_effect_count": 0,
        "source_files_mutated": False,
        "promotion_applied": False,
        "certified": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
        "provider_contacted": False,
    }


def _load_installed_evidence(runtime_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    installed = installed_state_status(runtime_root=runtime_root)
    _, transaction = active_transaction_private(runtime_root)
    tx_id = str(transaction.get("transaction_id") or "")
    receipt = read_json(transaction_directory(runtime_root) / "installed_receipts" / f"{tx_id}.json") if tx_id else {}
    if str(installed.get("status") or "") != "installed_unpromoted" or not installed.get("ok"):
        findings.append({"kind": "exact_installed_unpromoted_state_required"})
    if not transaction or str(transaction.get("state") or "") != "installed_unpromoted":
        findings.append({"kind": "installed_transaction_missing_or_not_complete"})
    if not receipt or str(receipt.get("receipt_sha256") or "") != _receipt_digest(receipt):
        findings.append({"kind": "installed_receipt_missing_or_invalid"})
    if transaction and receipt:
        for field in ("transaction_id", "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256", "target_project_id", "effects_sha256"):
            if str(transaction.get(field) or "") != str(receipt.get(field) or ""):
                findings.append({"kind": f"installed_receipt_{field}_mismatch"})
        root = Path(str(transaction.get("target_root_path") or ""))
        inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
        if not inventory.get("ok") or str(inventory.get("digest") or "") != str(receipt.get("target_inventory_sha256") or ""):
            findings.append({"kind": "installed_target_inventory_drift"})
    return installed, transaction, receipt, findings


def create_promotion_impact_preview(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    installed, transaction, receipt, findings = _load_installed_evidence(runtime_root)
    state = _promotion_state_material(runtime_root, installed)
    if state["state"] not in {"installed_unpromoted", "reversed_to_installed_unpromoted"}:
        findings.append({"kind": "conflicting_promotion_state"})
    if not state.get("state_digest_valid"):
        findings.append({"kind": "promotion_state_digest_mismatch"})
    if state["pointer_generation"] != state["generation"] or (state["pointer_state_sha256"] and state["pointer_state_sha256"] != state["state_sha256"]):
        findings.append({"kind": "promotion_state_pointer_mismatch"})
    directory = promotion_directory(runtime_root)
    if findings:
        failed = {"status": "promotion_preview_blocked", "ok": False, "contradictions": findings}
        atomic_json(directory / "last_failed_preview.json", failed)
        return _public(failed)
    pointer = read_json(directory / "active_preview.json")
    generation = int(pointer.get("generation") or 0) + 1
    effects = _metadata_effects(installed)
    record: dict[str, Any] = {
        "schema": PROMOTION_PREVIEW_SCHEMA,
        "preview_id": f"promotion-preview-{generation}-{secrets.token_hex(8)}",
        "generation": generation,
        "created_at": utc_now(),
        "status": "promotion_previewed",
        "ok": True,
        "transaction_id": str(transaction.get("transaction_id") or ""),
        "transaction_generation": int(transaction.get("generation") or 0),
        "transaction_identity_sha256": str(transaction.get("transaction_identity_sha256") or ""),
        "transaction_state_sha256": str(transaction.get("transaction_state_sha256") or ""),
        "installed_receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "candidate_id": str(receipt.get("candidate_id") or ""),
        "packaged_version": str(receipt.get("packaged_version") or ""),
        "archive_sha256": str(receipt.get("archive_sha256") or ""),
        "source_manifest_sha256": str(receipt.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(receipt.get("archive_manifest_sha256") or ""),
        "target_project_id": str(receipt.get("target_project_id") or ""),
        "target_identity_sha256": str(transaction.get("target_identity_sha256") or ""),
        "target_inventory_sha256": str(receipt.get("target_inventory_sha256") or ""),
        "effects_sha256": str(receipt.get("effects_sha256") or ""),
        "previous_promotion_generation": int(state["generation"]),
        "previous_promotion_state_sha256": str(state["state_sha256"]),
        "previous_promotion_state": str(state["state"]),
        "proposed_promotion_state": "promoted_uncertified",
        "metadata_effects": effects,
        "metadata_effects_sha256": digest_payload(effects),
        "promotion_policy_sha256": digest_payload({
            "contract": "eidolon-promotion-policy-v1",
            "source_mutation_allowed": False,
            "certification_allowed": False,
            "exact_installed_receipt_required": True,
        }),
        "contradictions": [],
    }
    record["preview_binding_sha256"] = _preview_binding(record)
    record["record_sha256"] = _record_digest(record, "record_sha256")
    atomic_json(directory / "previews" / f"{record['preview_id']}.json", record)
    atomic_json(directory / "active_preview.json", {
        "schema": PROMOTION_PREVIEW_SCHEMA,
        "preview_id": record["preview_id"],
        "generation": generation,
        "preview_binding_sha256": record["preview_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })
    return _public(record)


def active_promotion_preview_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = promotion_directory(runtime_root)
    pointer = read_json(directory / "active_preview.json")
    preview_id = str(pointer.get("preview_id") or "")
    return pointer, read_json(directory / "previews" / f"{preview_id}.json") if preview_id else {}


def promotion_preview_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_promotion_preview_private(runtime_root)
    if not record:
        return _public({})
    findings: list[dict[str, Any]] = []
    if str(record.get("record_sha256") or "") != _record_digest(record, "record_sha256"):
        findings.append({"kind": "promotion_preview_record_digest_mismatch"})
    if str(record.get("preview_binding_sha256") or "") != _preview_binding(record):
        findings.append({"kind": "promotion_preview_binding_mismatch"})
    for field in ("preview_id", "generation", "preview_binding_sha256", "record_sha256"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"promotion_preview_pointer_{field}_mismatch"})
    installed, transaction, receipt, evidence_findings = _load_installed_evidence(runtime_root)
    findings.extend(evidence_findings)
    comparisons = {
        "transaction_id": transaction.get("transaction_id"),
        "transaction_generation": transaction.get("generation"),
        "transaction_identity_sha256": transaction.get("transaction_identity_sha256"),
        "transaction_state_sha256": transaction.get("transaction_state_sha256"),
        "installed_receipt_sha256": receipt.get("receipt_sha256"),
        "candidate_id": receipt.get("candidate_id"),
        "archive_sha256": receipt.get("archive_sha256"),
        "source_manifest_sha256": receipt.get("source_manifest_sha256"),
        "archive_manifest_sha256": receipt.get("archive_manifest_sha256"),
        "target_project_id": receipt.get("target_project_id"),
        "target_identity_sha256": transaction.get("target_identity_sha256"),
        "target_inventory_sha256": receipt.get("target_inventory_sha256"),
        "effects_sha256": receipt.get("effects_sha256"),
    }
    for field, value in comparisons.items():
        if str(record.get(field) or "") != str(value or ""):
            findings.append({"kind": f"promotion_preview_{field}_drift"})
    state = _promotion_state_material(runtime_root, installed)
    if not state.get("state_digest_valid"):
        findings.append({"kind": "promotion_state_digest_mismatch"})
    if int(record.get("previous_promotion_generation") or 0) != int(state["generation"]) or str(record.get("previous_promotion_state_sha256") or "") != str(state["state_sha256"]):
        findings.append({"kind": "promotion_state_drift"})
    current = dict(record)
    current["contradictions"] = findings
    current["ok"] = not findings
    current["status"] = "promotion_previewed" if not findings else "promotion_preview_stale"
    return _public(current)
