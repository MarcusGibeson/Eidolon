from __future__ import annotations

"""Operator-approved training record promotion and local dataset export."""

import json
from pathlib import Path
from typing import Any, Mapping

from model_training.training_quality import assess_training_record_quality
from model_training.training_record import _atomic_json, _seal, load_training_record, training_record_path, _training_root

CONTRACT_VERSION = "v2503.4.23"


def approve_training_record(record_id: str, *, runtime_root: str | Path | None, operator_approved: bool) -> dict[str, Any]:
    if operator_approved is not True:
        return {"ok": False, "status": "training_record_operator_approval_required", "model_training_authorized": False}
    record = load_training_record(record_id, runtime_root=runtime_root, stage="sanitized")
    if not record:
        return {"ok": False, "status": "training_sanitized_record_missing_or_invalid", "model_training_authorized": False}
    assessment = assess_training_record_quality(record)
    if assessment.get("eligible_for_operator_approval") is not True:
        return {"ok": False, "status": "training_record_quality_gate_failed", "assessment": assessment, "model_training_authorized": False}
    approved = dict(record)
    approved.pop("record_digest", None)
    approved["contract_version"] = CONTRACT_VERSION
    approved["approved_for_training"] = True
    approved["operator_approval_recorded"] = True
    approved["quality_assessment"] = assessment
    approved["model_training_authorized"] = False
    approved["model_promotion_authorized"] = False
    approved = _seal(approved)
    path = training_record_path(record_id, runtime_root=runtime_root, stage="approved")
    if path.exists():
        existing = load_training_record(record_id, runtime_root=runtime_root, stage="approved")
        if existing and existing.get("record_digest") == approved.get("record_digest"):
            return {"ok": True, "status": "training_record_approval_restored", "record": existing, "runtime_path": str(path), "model_training_authorized": False}
        return {"ok": False, "status": "training_record_approval_identity_conflict", "runtime_path": str(path), "model_training_authorized": False}
    _atomic_json(path, approved)
    return {"ok": True, "status": "training_record_approved_for_dataset", "record": approved, "runtime_path": str(path), "model_training_authorized": False}


def _messages(record: Mapping[str, Any]) -> list[dict[str, str]]:
    input_payload = record.get("input_payload")
    output = record.get("corrected_output") if record.get("corrected_output") is not None else record.get("model_output")
    user = input_payload if isinstance(input_payload, str) else json.dumps(input_payload, ensure_ascii=True, sort_keys=True)
    assistant = output if isinstance(output, str) else json.dumps(output, ensure_ascii=True, sort_keys=True)
    return [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]


def export_approved_sft_jsonl(*, runtime_root: str | Path | None, export_name: str = "eidolon_sft.jsonl", operator_authorized: bool) -> dict[str, Any]:
    if operator_authorized is not True:
        return {"ok": False, "status": "training_export_operator_authorization_required", "model_training_authorized": False}
    root = _training_root(runtime_root)
    approved_root = root / "approved"
    export_root = root / "exports"
    export_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(export_name).name
    if not safe_name.endswith(".jsonl"):
        safe_name += ".jsonl"
    rows: list[str] = []
    record_ids: list[str] = []
    for path in sorted(approved_root.glob("trn_*.json")) if approved_root.exists() else []:
        record = load_training_record(path.stem, runtime_root=runtime_root, stage="approved")
        if not record or record.get("approved_for_training") is not True or record.get("sanitized") is not True:
            continue
        rows.append(json.dumps({"messages": _messages(record), "metadata": {"record_id": path.stem, "task_type": record.get("task_type"), "quality_score": (record.get("quality_assessment") or {}).get("quality_score")}}, ensure_ascii=True, sort_keys=True))
        record_ids.append(path.stem)
    output = export_root / safe_name
    output.write_text(("\n".join(rows) + ("\n" if rows else "")), encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "status": "training_sft_dataset_exported",
        "record_count": len(record_ids),
        "record_ids": record_ids,
        "runtime_path": str(output),
        "runtime_only": True,
        "source_modified": False,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
    }


def export_approved_preference_jsonl(*, runtime_root: str | Path | None, export_name: str = "eidolon_preferences.jsonl", operator_authorized: bool) -> dict[str, Any]:
    from model_training.training_preferences import build_preference_pair
    if operator_authorized is not True:
        return {"ok": False, "status": "training_export_operator_authorization_required", "model_training_authorized": False}
    root=_training_root(runtime_root); approved_root=root/"approved"; export_root=root/"exports"; export_root.mkdir(parents=True,exist_ok=True); rows=[]; ids=[]
    for path in sorted(approved_root.glob("trn_*.json")) if approved_root.exists() else []:
        rec=load_training_record(path.stem,runtime_root=runtime_root,stage="approved"); pair=build_preference_pair(rec) if rec else {"ok":False}
        if pair.get("ok") is True:
            rows.append(json.dumps({k:pair[k] for k in ("prompt","chosen","rejected","capability","record_id")},ensure_ascii=True,sort_keys=True)); ids.append(path.stem)
    safe=Path(export_name).name; safe += "" if safe.endswith(".jsonl") else ".jsonl"; out=export_root/safe; out.write_text("\n".join(rows)+( "\n" if rows else ""),encoding="utf-8",newline="\n")
    return {"ok":True,"status":"training_preference_dataset_exported","record_count":len(ids),"record_ids":ids,"runtime_path":str(out),"runtime_only":True,"model_training_authorized":False,"model_promotion_authorized":False}


def _immutable_text(path: Path, text: str, *, conflict_status: str) -> tuple[bool, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except Exception:
            existing = None
        if existing == text:
            return True, "restored"
        return False, conflict_status
    path.write_text(text, encoding="utf-8", newline="\n")
    return True, "created"


def _load_manifest_bound_records(*, runtime_root: str | Path | None, dataset_manifest: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    from model_training.training_dataset import validate_dataset_manifest
    if not validate_dataset_manifest(dataset_manifest):
        return [], "training_dataset_manifest_invalid"
    rows: list[dict[str, Any]] = []
    for binding in dataset_manifest.get("record_bindings") or []:
        rid = str(binding.get("record_id") or "")
        expected_digest = str(binding.get("record_digest") or "")
        record = load_training_record(rid, runtime_root=runtime_root, stage="approved")
        if not record:
            return [], "training_dataset_record_missing_or_invalid"
        if record.get("approved_for_training") is not True or record.get("sanitized") is not True:
            return [], "training_dataset_record_not_approved"
        if str(record.get("record_digest") or "") != expected_digest:
            return [], "training_dataset_record_digest_mismatch"
        rows.append(record)
    return rows, None


def export_manifest_sft_jsonl(*, runtime_root: str | Path | None, dataset_manifest: Mapping[str, Any], export_name: str | None = None, operator_authorized: bool) -> dict[str, Any]:
    if operator_authorized is not True:
        return {"ok": False, "status": "training_export_operator_authorization_required", "model_training_authorized": False}
    records, error = _load_manifest_bound_records(runtime_root=runtime_root, dataset_manifest=dataset_manifest)
    if error:
        return {"ok": False, "status": error, "model_training_authorized": False}
    manifest_digest = str(dataset_manifest.get("manifest_digest") or "")
    version = str(dataset_manifest.get("dataset_version") or "dataset")
    safe_version = "".join(c if c.isalnum() or c in "._-" else "-" for c in version)[:72].strip(".-") or "dataset"
    safe_name = Path(export_name or f"{safe_version}.{manifest_digest[:12]}.sft.jsonl").name
    if not safe_name.endswith(".jsonl"):
        safe_name += ".jsonl"
    rows = []
    ids = []
    for record in records:
        rid = str(record.get("record_id") or "")
        rows.append(json.dumps({"messages": _messages(record), "metadata": {"record_id": rid, "task_type": record.get("task_type"), "quality_score": (record.get("quality_assessment") or {}).get("quality_score"), "dataset_manifest_digest": manifest_digest}}, ensure_ascii=True, sort_keys=True))
        ids.append(rid)
    text = "\n".join(rows) + ("\n" if rows else "")
    output = _training_root(runtime_root) / "exports" / safe_name
    ok, state = _immutable_text(output, text, conflict_status="training_dataset_export_identity_conflict")
    return {"ok": ok, "status": "training_manifest_sft_dataset_exported" if ok else state, "record_count": len(ids) if ok else 0, "record_ids": ids if ok else [], "dataset_manifest_digest": manifest_digest, "runtime_path": str(output), "runtime_only": True, "model_training_authorized": False, "model_promotion_authorized": False}


def export_manifest_preference_jsonl(*, runtime_root: str | Path | None, dataset_manifest: Mapping[str, Any], export_name: str | None = None, operator_authorized: bool) -> dict[str, Any]:
    from model_training.training_preferences import build_preference_pair
    if operator_authorized is not True:
        return {"ok": False, "status": "training_export_operator_authorization_required", "model_training_authorized": False}
    records, error = _load_manifest_bound_records(runtime_root=runtime_root, dataset_manifest=dataset_manifest)
    if error:
        return {"ok": False, "status": error, "model_training_authorized": False}
    manifest_digest = str(dataset_manifest.get("manifest_digest") or "")
    version = str(dataset_manifest.get("dataset_version") or "dataset")
    safe_version = "".join(c if c.isalnum() or c in "._-" else "-" for c in version)[:72].strip(".-") or "dataset"
    safe_name = Path(export_name or f"{safe_version}.{manifest_digest[:12]}.preferences.jsonl").name
    if not safe_name.endswith(".jsonl"):
        safe_name += ".jsonl"
    rows = []
    ids = []
    for record in records:
        pair = build_preference_pair(record)
        if pair.get("ok") is True:
            rows.append(json.dumps({**{k: pair[k] for k in ("prompt", "chosen", "rejected", "capability", "record_id")}, "dataset_manifest_digest": manifest_digest}, ensure_ascii=True, sort_keys=True))
            ids.append(str(record.get("record_id") or ""))
    text = "\n".join(rows) + ("\n" if rows else "")
    output = _training_root(runtime_root) / "exports" / safe_name
    ok, state = _immutable_text(output, text, conflict_status="training_dataset_export_identity_conflict")
    return {"ok": ok, "status": "training_manifest_preference_dataset_exported" if ok else state, "record_count": len(ids) if ok else 0, "record_ids": ids if ok else [], "dataset_manifest_digest": manifest_digest, "runtime_path": str(output), "runtime_only": True, "model_training_authorized": False, "model_promotion_authorized": False}
