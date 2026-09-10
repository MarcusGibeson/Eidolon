from __future__ import annotations

"""Runtime-only, tamper-evident model-interaction training records.

This subsystem records *evidence for possible future training*.  It does not
train, fine-tune, distill, promote, select, or contact any model.  Records are
stored only beneath an explicit runtime root or EIDOLON_DATA_DIR and therefore
remain outside source-only packages.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

TRAINING_RECORD_SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v2503.4.13"
_ALLOWED_TASK_TYPES = {
    "software_development",
    "software_repair",
    "research_synthesis",
    "tool_use",
    "planning",
    "conversation",
    "governance",
    "other",
}
_AUTHORITY = {
    "model_training_authorized": False,
    "model_fine_tuning_authorized": False,
    "model_distillation_authorized": False,
    "model_promotion_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "source_mutation_authorized": False,
    "independent_authority_granted": False,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _runtime_root(runtime_root: str | Path | None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    override = os.environ.get("EIDOLON_DATA_DIR", "").strip()
    if not override:
        raise ValueError("training_runtime_root_required")
    return Path(override).expanduser().resolve()


def _training_root(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "model_training"


def _safe_id(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip())[:96].strip("-.")
    return text


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(value), ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _seal(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["record_digest"] = _digest({k: v for k, v in result.items() if k != "record_digest"})
    return result


def validate_training_record(record: Mapping[str, Any]) -> bool:
    if str(record.get("schema_version") or "") != TRAINING_RECORD_SCHEMA_VERSION:
        return False
    digest = str(record.get("record_digest") or "")
    if len(digest) != 64:
        return False
    return digest == _digest({k: v for k, v in record.items() if k != "record_digest"})


def create_training_record(
    *,
    task_type: str,
    input_payload: Mapping[str, Any] | str,
    model_output: Mapping[str, Any] | str,
    validation: Mapping[str, Any],
    corrected_output: Mapping[str, Any] | str | None = None,
    source_system: str = "eidolon",
    provenance: Mapping[str, Any] | None = None,
    capture_authorized: bool = False,
    created_at_ns: int | None = None,
) -> dict[str, Any]:
    """Build a record in memory; recording still requires explicit capture authorization."""
    task = str(task_type or "other").strip().lower()
    if task not in _ALLOWED_TASK_TYPES:
        task = "other"
    passed = bool(validation.get("passed") is True or validation.get("ok") is True)
    failure_code = str(validation.get("failure_code") or validation.get("status") or "")[:120]
    created = int(created_at_ns if created_at_ns is not None else time.time_ns())
    identity_basis = {
        "task_type": task,
        "input_digest": _digest(input_payload),
        "output_digest": _digest(model_output),
        "validation_digest": _digest(dict(validation)),
        "created_at_ns": created,
    }
    record_id = "trn_" + _digest(identity_basis)[:24]
    row = {
        "schema_version": TRAINING_RECORD_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "record_id": record_id,
        "created_at_ns": created,
        "task_type": task,
        "source_system": _safe_id(source_system) or "eidolon",
        "input_payload": input_payload,
        "model_output": model_output,
        "validation": dict(validation),
        "corrected_output": corrected_output,
        "provenance": dict(provenance or {}),
        "validation_passed": passed,
        "failure_code": failure_code,
        "has_correction": corrected_output is not None,
        "capture_authorized": bool(capture_authorized),
        "runtime_only": True,
        "source_package_allowed": False,
        "sanitized": False,
        "approved_for_training": False,
        **_AUTHORITY,
    }
    return _seal(row)


def training_record_path(record_id: str, *, runtime_root: str | Path | None = None, stage: str = "raw") -> Path:
    safe = _safe_id(record_id)
    if not safe.startswith("trn_"):
        raise ValueError("invalid_training_record_id")
    if stage not in {"raw", "sanitized", "approved"}:
        raise ValueError("invalid_training_record_stage")
    return _training_root(runtime_root) / stage / f"{safe}.json"


def record_training_interaction(
    *,
    runtime_root: str | Path | None,
    capture_authorized: bool,
    task_type: str,
    input_payload: Mapping[str, Any] | str,
    model_output: Mapping[str, Any] | str,
    validation: Mapping[str, Any],
    corrected_output: Mapping[str, Any] | str | None = None,
    source_system: str = "eidolon",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if capture_authorized is not True:
        return {
            "ok": False,
            "status": "training_capture_authorization_required",
            "runtime_only": True,
            "source_modified": False,
            **_AUTHORITY,
        }
    record = create_training_record(
        task_type=task_type,
        input_payload=input_payload,
        model_output=model_output,
        validation=validation,
        corrected_output=corrected_output,
        source_system=source_system,
        provenance=provenance,
        capture_authorized=True,
    )
    path = training_record_path(record["record_id"], runtime_root=runtime_root, stage="raw")
    if path.exists():
        existing = load_training_record(record["record_id"], runtime_root=runtime_root, stage="raw")
        if existing and existing.get("record_digest") == record.get("record_digest"):
            return {"ok": True, "status": "training_record_restored", "record": existing, "runtime_path": str(path)}
        return {"ok": False, "status": "training_record_identity_conflict", "runtime_path": str(path), **_AUTHORITY}
    _atomic_json(path, record)
    return {"ok": True, "status": "training_record_created", "record": record, "runtime_path": str(path)}


def load_training_record(record_id: str, *, runtime_root: str | Path | None, stage: str = "raw") -> dict[str, Any]:
    path = training_record_path(record_id, runtime_root=runtime_root, stage=stage)
    if not path.exists():
        return {}
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(row, dict) or not validate_training_record(row):
        return {}
    return row
