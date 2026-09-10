from __future__ import annotations

"""Explicit external certification evidence intake and readiness preview.

Evidence is selected one artifact at a time by the operator. Detailed payloads and
paths remain under the external runtime root. Public status is content-free and
never certifies a release.
"""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import _target_inventory
    from release_promotion_preview import current_promotion_state_private
    from release_promotion_transaction import active_promotion_transaction_private, promotion_directory, promotion_transaction_status
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_installation_preview import _target_inventory
    from release_promotion_preview import current_promotion_state_private
    from release_promotion_transaction import active_promotion_transaction_private, promotion_directory, promotion_transaction_status

CERTIFICATION_EVIDENCE_CONTRACT_VERSION = "1"
EVIDENCE_SCHEMA = "eidolon-certification-evidence-v1"
AUTHORITATIVE_REPORT_SCHEMA = "eidolon-authoritative-verification-report-v1"
READINESS_SCHEMA = "eidolon-certification-readiness-preview-v1"
CERTIFICATION_DIRECTORY = "release_certification"

EVIDENCE_SCOPES = (
    "source_package_integrity",
    "startup_daily_use",
    "installation_recovery",
    "promotion_behavior",
    "native_windows_behavior",
    "provider_ollama_behavior",
    "model_specific_behavior",
)
CERTIFICATION_SCOPE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "general_release": (
        "source_package_integrity",
        "startup_daily_use",
        "installation_recovery",
        "promotion_behavior",
    ),
    "native_windows": ("native_windows_behavior",),
    "provider_ollama": ("provider_ollama_behavior",),
    "model_specific": ("model_specific_behavior",),
}
TRUSTED_PRODUCERS = {
    "eidolon-authoritative-verifier",
    "eidolon-native-windows-verifier",
    "eidolon-provider-verifier",
    "eidolon-model-verifier",
}


def certification_directory(runtime_root: str | Path | None = None) -> Path:
    return runtime_data_root(runtime_root) / CERTIFICATION_DIRECTORY


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _record_digest(record: Mapping[str, Any], field: str = "record_sha256") -> str:
    material = dict(record)
    material.pop(field, None)
    return digest_payload(material)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _path_leaks(value: Any, key: str = "") -> bool:
    lowered = key.lower()
    if isinstance(value, Mapping):
        return any(_path_leaks(item, str(name)) for name, item in value.items())
    if isinstance(value, list):
        return any(_path_leaks(item, key) for item in value)
    if not isinstance(value, str):
        return False
    text = value.strip()
    if any(token in lowered for token in ("path", "directory", "working_root", "source_root", "runtime_root")) and text:
        return True
    if text.startswith(("/", "\\\\")) or PureWindowsPath(text).is_absolute():
        return True
    return False


def _promotion_context(runtime_root: str | Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    status = promotion_transaction_status(runtime_root=runtime_root)
    _, transaction = active_promotion_transaction_private(runtime_root)
    pointer, state = current_promotion_state_private(runtime_root)
    txid = str(transaction.get("promotion_transaction_id") or "")
    receipt = read_json(promotion_directory(runtime_root) / "receipts" / f"{txid}.json") if txid else {}
    allowed_authority = {"promoted_uncertified", "certified", "partially_certified"}
    if not status.get("ok") or str(status.get("status") or "") not in allowed_authority:
        findings.append({"kind": "exact_promoted_release_authority_required"})
    if not transaction or not receipt:
        findings.append({"kind": "promotion_transaction_or_receipt_missing"})
    receipt_material = dict(receipt)
    expected_receipt = str(receipt_material.pop("receipt_sha256", ""))
    if receipt and (not expected_receipt or expected_receipt != digest_payload(receipt_material)):
        findings.append({"kind": "promotion_receipt_digest_mismatch"})
    state_material = dict(state)
    expected_state = str(state_material.pop("state_sha256", ""))
    if state and (not expected_state or expected_state != digest_payload(state_material)):
        findings.append({"kind": "promotion_state_digest_mismatch"})
    if state and str(pointer.get("state_sha256") or "") != str(state.get("state_sha256") or ""):
        findings.append({"kind": "promotion_state_pointer_mismatch"})
    if state and str(state.get("state") or "") not in allowed_authority:
        findings.append({"kind": "promoted_release_authority_required"})
    root = Path(str(transaction.get("target_root_path") or ""))
    inventory = _target_inventory(root) if root.is_dir() else {"ok": False, "digest": ""}
    if not inventory.get("ok") or str(inventory.get("digest") or "") != str(receipt.get("target_inventory_sha256") or ""):
        findings.append({"kind": "promoted_target_inventory_drift"})
    context = {
        "candidate_id": str(receipt.get("candidate_id") or ""),
        "packaged_version": str(receipt.get("packaged_version") or ""),
        "archive_sha256": str(receipt.get("archive_sha256") or ""),
        "source_manifest_sha256": str(receipt.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(receipt.get("archive_manifest_sha256") or ""),
        "installed_transaction_id": str(receipt.get("transaction_id") or ""),
        "installed_receipt_sha256": str(receipt.get("installed_receipt_sha256") or ""),
        "promotion_transaction_id": txid,
        "promotion_transaction_identity_sha256": str(transaction.get("promotion_transaction_identity_sha256") or ""),
        "promotion_receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "target_project_id": str(receipt.get("target_project_id") or ""),
        "target_inventory_sha256": str(receipt.get("target_inventory_sha256") or ""),
        "promotion_state_generation": int(state.get("generation") or 0),
        "promotion_state_sha256": str(state.get("state_sha256") or ""),
        "promoted_at": str(receipt.get("promoted_at") or ""),
    }
    return context, findings


def _public_evidence(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_selected"),
        "contract_version": CERTIFICATION_EVIDENCE_CONTRACT_VERSION,
        "evidence_id": str(row.get("evidence_id") or ""),
        "generation": int(row.get("generation") or 0),
        "scope": str(row.get("scope") or ""),
        "artifact_sha256": str(row.get("artifact_sha256") or ""),
        "schema": str(row.get("evidence_schema") or ""),
        "producer_tool": str(row.get("producer_tool") or ""),
        "producer_version": str(row.get("producer_version") or ""),
        "claimed_environment": str(row.get("claimed_environment_summary") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "verification_result": str(row.get("verification_result") or ""),
        "complete": bool(row.get("complete")),
        "sufficient": bool(row.get("sufficient")) and not contradictions,
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "certified": False,
        "certification_applied": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "provider_contacted": False,
        "native_check_run": False,
        "ordinary_conversation_affected": False,
    }


def select_certification_evidence(
    evidence_path: str | Path,
    *,
    runtime_root: str | Path | None = None,
    _activation_state: str = "active",
) -> dict[str, Any]:
    path = Path(evidence_path).expanduser().resolve()
    directory = certification_directory(runtime_root)
    active = read_json(directory / "evidence_index.json")
    generation = int(active.get("generation") or 0) + 1
    findings: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    artifact_sha = ""
    if not path.is_file() or path.is_symlink():
        findings.append({"kind": "selected_evidence_missing_or_not_regular"})
    else:
        try:
            artifact_sha = _sha256_file(path)
            loaded = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(loaded, dict):
                raise ValueError("evidence_not_object")
            payload = loaded
        except Exception:
            findings.append({"kind": "selected_evidence_malformed"})
    context, context_findings = _promotion_context(runtime_root)
    findings.extend(context_findings)
    schema = str(payload.get("schema") or "")
    scope = str(payload.get("scope") or "")
    producer = payload.get("producer") if isinstance(payload.get("producer"), Mapping) else {}
    environment = payload.get("environment") if isinstance(payload.get("environment"), Mapping) else {}
    result = str(payload.get("verification_result") or payload.get("result") or "").lower()
    complete = bool(payload.get("complete"))
    if payload:
        if schema not in {EVIDENCE_SCHEMA, AUTHORITATIVE_REPORT_SCHEMA}:
            findings.append({"kind": "unsupported_evidence_schema"})
        if scope not in EVIDENCE_SCOPES:
            findings.append({"kind": "unsupported_evidence_scope"})
        if str(producer.get("tool") or "") not in TRUSTED_PRODUCERS:
            findings.append({"kind": "self_asserted_or_untrusted_evidence"})
        if not str(producer.get("version") or ""):
            findings.append({"kind": "producing_tool_version_missing"})
        if result not in {"pass", "passed"}:
            findings.append({"kind": "verification_result_not_passing"})
        if not complete:
            findings.append({"kind": "authoritative_report_incomplete"})
        if _path_leaks(payload):
            findings.append({"kind": "evidence_payload_leaks_private_path"})
        for field in (
            "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256",
            "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id",
        ):
            if str(payload.get(field) or "") != str(context.get(field) or ""):
                findings.append({"kind": f"evidence_{field}_mismatch"})
        finished = _parse_time(payload.get("finished_at"))
        promoted = _parse_time(context.get("promoted_at"))
        if not finished:
            findings.append({"kind": "evidence_timestamp_missing_or_invalid"})
        elif promoted and finished < promoted:
            findings.append({"kind": "evidence_predates_exact_promotion"})
        if scope == "native_windows_behavior":
            if str(environment.get("os") or "").lower() != "windows" or not bool(environment.get("native")):
                findings.append({"kind": "native_windows_environment_not_proven"})
        if scope == "provider_ollama_behavior":
            if str(environment.get("provider") or "").lower() != "ollama" or not bool(environment.get("available")):
                findings.append({"kind": "native_ollama_environment_not_proven"})
        if scope == "model_specific_behavior" and not str(environment.get("model") or ""):
            findings.append({"kind": "model_identity_missing"})
    evidence_id = f"cert-evidence-{generation}-{secrets.token_hex(8)}"
    record = {
        "schema": "eidolon-certification-evidence-intake-record-v1",
        "evidence_id": evidence_id,
        "generation": generation,
        "selected_at": utc_now(),
        "selected_path": str(path),
        "artifact_sha256": artifact_sha,
        "evidence_schema": schema,
        "scope": scope,
        "producer_tool": str(producer.get("tool") or ""),
        "producer_version": str(producer.get("version") or ""),
        "claimed_environment": dict(environment),
        "claimed_environment_summary": str(environment.get("os") or environment.get("provider") or environment.get("model") or "unspecified"),
        "candidate_id": str(payload.get("candidate_id") or ""),
        "packaged_version": str(payload.get("packaged_version") or context.get("packaged_version") or ""),
        "archive_sha256": str(payload.get("archive_sha256") or ""),
        "source_manifest_sha256": str(payload.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(payload.get("archive_manifest_sha256") or ""),
        "installed_receipt_sha256": str(payload.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(payload.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(payload.get("target_project_id") or ""),
        "promotion_state_generation": int(context.get("promotion_state_generation") or 0),
        "promotion_state_sha256": str(context.get("promotion_state_sha256") or ""),
        "verification_result": result,
        "complete": complete,
        "payload": payload,
        "activation_state": _activation_state if _activation_state in {"active", "pending_replacement"} else "active",
        "sufficient": not findings,
        "status": "evidence_sufficient" if not findings else "evidence_insufficient",
        "ok": not findings,
        "contradictions": findings,
    }
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "evidence" / f"{evidence_id}.json", record)
    evidence_ids = list(active.get("evidence_ids") or [])
    evidence_ids.append(evidence_id)
    atomic_json(directory / "evidence_index.json", {
        "schema": "eidolon-certification-evidence-index-v1",
        "generation": generation,
        "evidence_ids": evidence_ids,
        "content_free": True,
    })
    atomic_json(directory / "last_evidence_intake.json", {
        "schema": "eidolon-certification-evidence-intake-pointer-v1",
        "generation": generation,
        "evidence_id": evidence_id,
        "artifact_sha256": artifact_sha,
        "scope": scope,
        "status": record["status"],
        "record_sha256": record["record_sha256"],
        "content_free": True,
    })
    return _public_evidence(record)



def _promotion_state_descends(runtime_root: str | Path | None, current_sha: str, ancestor_sha: str) -> bool:
    if not ancestor_sha or not current_sha:
        return False
    if current_sha == ancestor_sha:
        return True
    states: dict[str, dict[str, Any]] = {}
    for path in (promotion_directory(runtime_root) / "states").glob("*.json"):
        row = read_json(path)
        sha = str(row.get("state_sha256") or "")
        if sha:
            states[sha] = row
    seen: set[str] = set()
    cursor = current_sha
    while cursor and cursor not in seen:
        seen.add(cursor)
        row = states.get(cursor, {})
        previous = str(row.get("previous_state_sha256") or "")
        if previous == ancestor_sha:
            return True
        cursor = previous
    return False

def _current_evidence(runtime_root: str | Path | None, context: Mapping[str, Any]) -> list[dict[str, Any]]:
    directory = certification_directory(runtime_root)
    index = read_json(directory / "evidence_index.json")
    replacements = read_json(directory / "active_evidence_replacements.json")
    active_by_scope = dict(replacements.get("active_evidence_by_scope") or {})
    rows: list[dict[str, Any]] = []
    for evidence_id in list(index.get("evidence_ids") or []):
        record = read_json(directory / "evidence" / f"{evidence_id}.json")
        if not record:
            continue
        scope = str(record.get("scope") or "")
        mapped = str(active_by_scope.get(scope) or "")
        if mapped and evidence_id != mapped:
            continue
        if not mapped and str(record.get("activation_state") or "active") == "pending_replacement":
            continue
        valid = str(record.get("record_sha256") or "") == _record_digest(record)
        core_exact = all(str(record.get(field) or "") == str(context.get(field) or "") for field in (
            "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256",
            "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id",
        ))
        authority_exact = _promotion_state_descends(runtime_root, str(context.get("promotion_state_sha256") or ""), str(record.get("promotion_state_sha256") or ""))
        exact = core_exact and authority_exact
        current = dict(record)
        if not valid:
            current.setdefault("contradictions", []).append({"kind": "evidence_record_digest_mismatch"})
        if not exact:
            current.setdefault("contradictions", []).append({"kind": "evidence_stale_for_current_release_authority"})
        current["sufficient"] = bool(record.get("sufficient")) and valid and exact and not current.get("contradictions")
        rows.append(current)
    return rows


def _readiness_binding(record: Mapping[str, Any]) -> str:
    return digest_payload({
        "contract": "eidolon-certification-readiness-binding-v1",
        "preview_id": str(record.get("preview_id") or ""),
        "generation": int(record.get("generation") or 0),
        "certification_scope": str(record.get("certification_scope") or ""),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "source_manifest_sha256": str(record.get("source_manifest_sha256") or ""),
        "archive_manifest_sha256": str(record.get("archive_manifest_sha256") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "target_inventory_sha256": str(record.get("target_inventory_sha256") or ""),
        "promotion_state_generation": int(record.get("promotion_state_generation") or 0),
        "promotion_state_sha256": str(record.get("promotion_state_sha256") or ""),
        "required_scopes_sha256": str(record.get("required_scopes_sha256") or ""),
        "satisfied_evidence_sha256": str(record.get("satisfied_evidence_sha256") or ""),
        "missing_scopes_sha256": str(record.get("missing_scopes_sha256") or ""),
        "contradictory_scopes_sha256": str(record.get("contradictory_scopes_sha256") or ""),
        "decision_policy_sha256": str(record.get("decision_policy_sha256") or ""),
    })


def _public_readiness(record: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(record or {})
    contradictions = _counts(row.get("contradictions") if isinstance(row.get("contradictions"), list) else [])
    return {
        "ok": bool(row.get("ok")) and not contradictions,
        "status": str(row.get("status") or "not_previewed"),
        "contract_version": CERTIFICATION_EVIDENCE_CONTRACT_VERSION,
        "preview_id": str(row.get("preview_id") or ""),
        "preview_binding_sha256": str(row.get("preview_binding_sha256") or ""),
        "generation": int(row.get("generation") or 0),
        "certification_scope": str(row.get("certification_scope") or ""),
        "candidate_id": str(row.get("candidate_id") or ""),
        "archive_sha256": str(row.get("archive_sha256") or ""),
        "installed_receipt_sha256": str(row.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(row.get("promotion_receipt_sha256") or ""),
        "target_project_id": str(row.get("target_project_id") or ""),
        "required_scopes": list(row.get("required_scopes") or []),
        "satisfied_scopes": list(row.get("satisfied_scopes") or []),
        "missing_scopes": list(row.get("missing_scopes") or []),
        "contradictory_scopes": list(row.get("contradictory_scopes") or []),
        "not_applicable_scopes": list(row.get("not_applicable_scopes") or []),
        "satisfied_evidence_count": len(row.get("satisfied_evidence") or []),
        "ready": bool(row.get("ready")) and not contradictions,
        "contradictions": contradictions,
        "contradiction_count": sum(int(item["count"]) for item in contradictions),
        "certified": False,
        "certification_applied": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "provider_contacted": False,
        "native_check_run": False,
        "ordinary_conversation_affected": False,
    }


def create_certification_readiness_preview(
    certification_scope: str = "general_release",
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    context, findings = _promotion_context(runtime_root)
    if certification_scope not in CERTIFICATION_SCOPE_REQUIREMENTS:
        findings.append({"kind": "unsupported_certification_scope"})
    required = list(CERTIFICATION_SCOPE_REQUIREMENTS.get(certification_scope, ()))
    evidence = _current_evidence(runtime_root, context)
    sufficient_by_scope: dict[str, dict[str, Any]] = {}
    contradictory_scopes: set[str] = set()
    for row in evidence:
        scope = str(row.get("scope") or "")
        if row.get("sufficient") and scope in required:
            previous = sufficient_by_scope.get(scope)
            if previous is None or int(row.get("generation") or 0) > int(previous.get("generation") or 0):
                sufficient_by_scope[scope] = row
        elif scope in required and row.get("contradictions"):
            contradictory_scopes.add(scope)
    satisfied = sorted(sufficient_by_scope)
    missing = sorted(set(required) - set(satisfied))
    not_applicable = sorted(set(EVIDENCE_SCOPES) - set(required))
    directory = certification_directory(runtime_root)
    active = read_json(directory / "active_readiness.json")
    generation = int(active.get("generation") or 0) + 1
    satisfied_evidence = [
        {"scope": scope, "evidence_id": sufficient_by_scope[scope]["evidence_id"], "artifact_sha256": sufficient_by_scope[scope]["artifact_sha256"], "record_sha256": sufficient_by_scope[scope]["record_sha256"]}
        for scope in satisfied
    ]
    policy = {
        "contract": "eidolon-certification-decision-policy-v1",
        "certification_scope": certification_scope,
        "exact_promoted_receipt_required": True,
        "all_required_evidence_must_pass": True,
        "scope_implication_allowed": False,
        "native_scope_inference_allowed": False,
        "provider_scope_inference_allowed": False,
    }
    ready = not findings and not missing and not contradictory_scopes
    record = {
        "schema": READINESS_SCHEMA,
        "preview_id": f"cert-readiness-{generation}-{secrets.token_hex(8)}",
        "generation": generation,
        "created_at": utc_now(),
        "status": "certification_ready" if ready else "certification_not_ready",
        "ok": not findings,
        "ready": ready,
        "certification_scope": certification_scope,
        **context,
        "required_scopes": required,
        "required_scopes_sha256": digest_payload(required),
        "satisfied_scopes": satisfied,
        "satisfied_evidence": satisfied_evidence,
        "satisfied_evidence_sha256": digest_payload(satisfied_evidence),
        "missing_scopes": missing,
        "missing_scopes_sha256": digest_payload(missing),
        "contradictory_scopes": sorted(contradictory_scopes),
        "contradictory_scopes_sha256": digest_payload(sorted(contradictory_scopes)),
        "not_applicable_scopes": not_applicable,
        "decision_policy": policy,
        "decision_policy_sha256": digest_payload(policy),
        "contradictions": findings,
    }
    record["preview_binding_sha256"] = _readiness_binding(record)
    record["record_sha256"] = _record_digest(record)
    atomic_json(directory / "readiness" / f"{record['preview_id']}.json", record)
    atomic_json(directory / "active_readiness.json", {
        "schema": READINESS_SCHEMA,
        "preview_id": record["preview_id"],
        "generation": generation,
        "preview_binding_sha256": record["preview_binding_sha256"],
        "record_sha256": record["record_sha256"],
        "certification_scope": certification_scope,
        "content_free": True,
    })
    return _public_readiness(record)


def active_certification_readiness_private(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = certification_directory(runtime_root)
    pointer = read_json(directory / "active_readiness.json")
    preview_id = str(pointer.get("preview_id") or "")
    return pointer, read_json(directory / "readiness" / f"{preview_id}.json") if preview_id else {}


def certification_readiness_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    pointer, record = active_certification_readiness_private(runtime_root)
    if not record:
        return _public_readiness({})
    findings: list[dict[str, Any]] = []
    if str(record.get("record_sha256") or "") != _record_digest(record):
        findings.append({"kind": "certification_readiness_record_digest_mismatch"})
    if str(record.get("preview_binding_sha256") or "") != _readiness_binding(record):
        findings.append({"kind": "certification_readiness_binding_mismatch"})
    for field in ("preview_id", "generation", "preview_binding_sha256", "record_sha256", "certification_scope"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""):
            findings.append({"kind": f"certification_readiness_pointer_{field}_mismatch"})
    context, context_findings = _promotion_context(runtime_root)
    findings.extend(context_findings)
    for field in (
        "candidate_id", "archive_sha256", "source_manifest_sha256", "archive_manifest_sha256",
        "installed_receipt_sha256", "promotion_receipt_sha256", "target_project_id",
        "target_inventory_sha256", "promotion_state_sha256",
    ):
        if str(record.get(field) or "") != str(context.get(field) or ""):
            findings.append({"kind": f"certification_readiness_{field}_drift"})
    if int(record.get("promotion_state_generation") or 0) != int(context.get("promotion_state_generation") or 0):
        findings.append({"kind": "certification_readiness_promotion_generation_drift"})
    evidence = _current_evidence(runtime_root, context)
    current_map = {str(row.get("evidence_id") or ""): row for row in evidence}
    for selected in list(record.get("satisfied_evidence") or []):
        current = current_map.get(str(selected.get("evidence_id") or ""), {})
        if not current.get("sufficient") or str(current.get("artifact_sha256") or "") != str(selected.get("artifact_sha256") or ""):
            findings.append({"kind": "certification_readiness_evidence_drift"})
    current = dict(record)
    current["contradictions"] = findings
    current["ok"] = not findings
    current["ready"] = bool(record.get("ready")) and not findings
    current["status"] = "certification_ready" if current["ready"] else ("certification_readiness_stale" if findings else "certification_not_ready")
    return _public_readiness(current)
