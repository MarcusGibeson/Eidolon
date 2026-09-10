from __future__ import annotations

"""Era 8 portable fault-tolerance and disaster-recovery contracts.

This layer prepares and simulates recovery over disposable copies.  It never
mutates the authoritative source or private runtime, and it preserves explicit
uncertainty when exact recovery cannot be proven.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2275.9"
SCHEMA_VERSION = "1"
RECOVERY_JOURNAL_FILE = "era8_recovery_journal.json"
MAX_JOURNAL = 512
RECOVERY_CLASSES = ("process_crash", "power_loss", "disk_pressure", "locked_file", "corrupt_json", "provider_outage", "source_drift")

_DENIED = {
    "authoritative_source_modified": False,
    "private_runtime_modified": False,
    "provider_contacted": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "destructive_operation_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_manifest(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): _file_digest(p) for p in sorted(root.rglob("*")) if p.is_file()}


def build_recovery_checkpoint(
    *, checkpoint_id: str, source_manifest_digest: str, runtime_state_digest: str = "",
    priority: int = 50, backup_digest: str = "", health_codes: Iterable[str] = (),
) -> dict[str, Any]:
    cid = str(checkpoint_id or "").strip()[:160]
    source = _hex64(source_manifest_digest)
    runtime_digest = _hex64(runtime_state_digest) if runtime_state_digest else ""
    backup = _hex64(backup_digest) if backup_digest else ""
    try:
        bounded_priority = max(0, min(100, int(priority)))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("invalid_recovery_checkpoint_priority") from None
    if not cid or not source or (runtime_state_digest and not runtime_digest) or (backup_digest and not backup):
        raise ValueError("checkpoint_id_and_source_manifest_digest_required")
    row = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": cid,
        "source_manifest_digest": source,
        "runtime_state_digest": runtime_digest,
        "backup_digest": backup,
        "priority": bounded_priority,
        "health_codes": sorted({str(code or "").strip().lower()[:120] for code in health_codes if str(code or "").strip()})[:64],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_is_installation_authority": False,
        "raw_private_content_recorded": False,
        **_DENIED,
    }
    row["checkpoint_digest"] = _digest({k: v for k, v in row.items() if k != "created_at"})
    return row


def classify_recovery_signal(signal: Mapping[str, Any]) -> dict[str, Any]:
    code = str(signal.get("class") or signal.get("code") or "").strip().lower()
    recognized = code in RECOVERY_CLASSES
    certainty = str(signal.get("certainty") or "observed").strip().lower()
    if certainty not in {"observed", "inferred", "unknown"}:
        certainty = "unknown"
    destructive = bool(signal.get("destructive_risk"))
    source_drift = bool(signal.get("source_drift")) or code == "source_drift"
    result = {
        "ok": True,
        "status": "recovery_signal_classified",
        "contract_version": CONTRACT_VERSION,
        "signal_class": code if recognized else "unknown",
        "recognized": recognized,
        "certainty": certainty,
        "destructive_risk": destructive,
        "source_drift": source_drift,
        "recommended_action": "freeze_and_escalate" if destructive or source_drift else ("prepare_recovery" if recognized and certainty == "observed" else "collect_evidence"),
        **_DENIED,
    }
    result["signal_digest"] = _digest(result)
    return result


def simulate_transactional_recovery(
    source_root: str | Path, *, signal: Mapping[str, Any], expected_manifest: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source = Path(source_root).expanduser().resolve(strict=True)
    classified = classify_recovery_signal(signal)
    if classified["recommended_action"] == "freeze_and_escalate":
        return {"ok": False, "status": "recovery_simulation_blocked_for_escalation", "signal": classified, **_DENIED}
    before = _tree_manifest(source)
    if expected_manifest is not None and dict(expected_manifest) != before:
        return {"ok": False, "status": "recovery_baseline_manifest_mismatch", "signal": classified, **_DENIED}
    with tempfile.TemporaryDirectory(prefix="eidolon-era8-recovery-") as tmp:
        tmp_root = Path(tmp)
        backup = tmp_root / "backup"
        candidate = tmp_root / "candidate"
        restored = tmp_root / "restored"
        shutil.copytree(source, backup)
        shutil.copytree(source, candidate)
        # Synthetic failure occurs only in the disposable candidate tree.
        marker = candidate / ".era8_failure_marker"
        marker.write_text(classified["signal_class"], encoding="utf-8")
        shutil.copytree(backup, restored)
        after = _tree_manifest(restored)
        backup_manifest = _tree_manifest(backup)
        source_after = _tree_manifest(source)
        exact = before == backup_manifest == after == source_after
        result = {
            "ok": exact,
            "status": "transactional_recovery_simulation_passed" if exact else "transactional_recovery_simulation_uncertain",
            "contract_version": CONTRACT_VERSION,
            "signal_class": classified["signal_class"],
            "source_manifest_digest": _digest(before),
            "backup_manifest_digest": _digest(backup_manifest),
            "restored_manifest_digest": _digest(after),
            "source_unchanged": source_after == before,
            "backup_verified": backup_manifest == before,
            "rollback_verified": after == before,
            "uncertain_result": not exact,
            "disposable_failure_injected": True,
            "failure_marker_persisted_to_source": False,
            **_DENIED,
        }
        result["recovery_digest"] = _digest(result)
        return result


def _journal_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "recovery" / RECOVERY_JOURNAL_FILE


def _default_journal() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "entries": [], "raw_private_content_recorded": False}


def _read_journal(runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, _ = _read_journal_checked(runtime_root)
    return state


def _read_journal_checked(runtime_root: str | Path | None = None) -> tuple[dict[str, Any], bool]:
    path = _journal_path(runtime_root)
    if not path.exists():
        return _default_journal(), True
    try:
        value = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _default_journal(), False
    if not isinstance(value, dict) or not isinstance(value.get("entries"), list):
        return _default_journal(), False
    state = deepcopy(value)
    integrity_ok = all(
        isinstance(row, Mapping)
        and bool(_hex64(row.get("event_digest")))
        and bool(_hex64(row.get("checkpoint_digest")))
        and bool(_hex64(row.get("signal_digest")))
        and (not row.get("result_digest") or bool(_hex64(row.get("result_digest"))))
        for row in state["entries"]
    )
    state["raw_private_content_recorded"] = False
    return state, integrity_ok


def append_recovery_journal(
    *, operation_id: str, checkpoint_digest: str, signal_digest: str, result_digest: str = "",
    state_code: str = "prepared", uncertain_result: bool = False, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    token = str(operation_id or "").strip()[:160]
    checkpoint = _hex64(checkpoint_digest)
    signal = _hex64(signal_digest)
    result = _hex64(result_digest) if result_digest else ""
    if not token or not checkpoint or not signal or (result_digest and not result):
        return {"ok": False, "status": "recovery_journal_identity_invalid", **_DENIED}
    state_name = str(state_code or "prepared").strip().lower()[:64]
    event_digest = _digest({"operation_id": token, "checkpoint_digest": checkpoint, "signal_digest": signal, "result_digest": result, "state_code": state_name, "uncertain_result": bool(uncertain_result)})
    path = _journal_path(runtime_root)
    try:
        with metadata_mutation_lock(path):
            journal, journal_integrity_ok = _read_journal_checked(runtime_root)
            if not journal_integrity_ok:
                return {"ok": False, "status": "recovery_journal_integrity_invalid", **_DENIED}
            for row in journal.get("entries", []):
                if isinstance(row, Mapping) and row.get("event_digest") == event_digest:
                    return {"ok": True, "status": "recovery_journal_replayed", "idempotent": True, "event_digest": event_digest, "revision": int(journal.get("revision") or 0), **_DENIED}
            entry = {
                "operation_digest": _digest(token), "checkpoint_digest": checkpoint, "signal_digest": signal,
                "result_digest": result, "state_code": state_name, "uncertain_result": bool(uncertain_result),
                "event_digest": event_digest, "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            journal["entries"] = (journal.get("entries", []) + [entry])[-MAX_JOURNAL:]
            journal["revision"] = int(journal.get("revision") or 0) + 1
            journal["contract_version"] = CONTRACT_VERSION
            write_json_atomic(path, journal, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "recovery_journal_appended", "idempotent": False, "event_digest": event_digest, "revision": journal["revision"], **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError):
        return {"ok": False, "status": "recovery_journal_write_blocked", **_DENIED}


def inspect_recovery_journal(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    journal, journal_integrity_ok = _read_journal_checked(runtime_root)
    counts: dict[str, int] = {}
    uncertain = 0
    for row in journal.get("entries", []):
        if isinstance(row, Mapping):
            code = str(row.get("state_code") or "unknown")
            counts[code] = counts.get(code, 0) + 1
            uncertain += int(bool(row.get("uncertain_result")))
    result = {
        "ok": journal_integrity_ok, "status": "recovery_journal_inspected" if journal_integrity_ok else "recovery_journal_integrity_invalid", "contract_version": CONTRACT_VERSION,
        "revision": int(journal.get("revision") or 0), "entry_count": len(journal.get("entries") or []),
        "state_counts": counts, "uncertain_count": uncertain, "raw_private_content_exposed": False, "fail_closed_required": not journal_integrity_ok, **_DENIED,
    }
    result["journal_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "RECOVERY_CLASSES", "build_recovery_checkpoint", "classify_recovery_signal", "simulate_transactional_recovery", "append_recovery_journal", "inspect_recovery_journal"]
