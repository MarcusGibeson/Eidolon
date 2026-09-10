from __future__ import annotations
"""v2580 bounded runtime history for retrieval outcomes."""
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime, timezone
import os, hashlib, json
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic

CONTRACT_VERSION = "v2580.0"
MAX_ROWS = 96

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _root(runtime_root: str|Path|None=None) -> Path:
    if runtime_root is not None: return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"

def append_memory_retrieval_outcome(outcome: Mapping[str, Any], *, operation_id: str = "", operation_ref_digest: str = "", runtime_root: str|Path|None=None) -> dict[str, Any]:
    if not str(operation_id or "").strip() and len(str(operation_ref_digest or "")) != 64: raise ValueError("operation_reference_required")
    if str(outcome.get("outcome_digest") or "").strip() == "": raise ValueError("outcome_digest_required")
    root = _root(runtime_root); root.mkdir(parents=True, exist_ok=True)
    path = root/"memory_retrieval_outcome_history_v2580.json"
    state = load_json_file(path, {"rows": []}, expected_type=dict)
    rows = list(state.get("rows") or [])
    op_digest = str(operation_ref_digest or "").strip() or hashlib.sha256(str(operation_id).encode()).hexdigest()
    row = {
        "operation_ref_digest": op_digest,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "retrieval_state": str(outcome.get("retrieval_state") or "unknown")[:48],
        "outcome_disposition": str(outcome.get("outcome_disposition") or "neutral_evidence")[:48],
        "selected_count": max(0, int(outcome.get("selected_count") or 0)),
        "correction_detected": bool(outcome.get("correction_detected")),
        "contradiction_detected": bool(outcome.get("contradiction_detected")),
        "uncertainty_preserved": bool(outcome.get("uncertainty_preserved")),
        "outcome_digest": str(outcome.get("outcome_digest")),
    }
    row["row_digest"] = _digest(row)
    if not any(r.get("row_digest") == row["row_digest"] for r in rows if isinstance(r, Mapping)):
        rows.append(row)
    rows = rows[-MAX_ROWS:]
    payload = {"contract_version": CONTRACT_VERSION, "rows": rows, "raw_memory_text_stored": False, "raw_prompt_stored": False, "raw_response_stored": False}
    payload["history_digest"] = _digest(payload)
    write_json_atomic(path, payload, expected_type=dict, sort_keys=True)
    return {"ok": True, "contract_version": CONTRACT_VERSION, "row_count": len(rows), "row_digest": row["row_digest"], "history_digest": payload["history_digest"], "memory_mutated": False, "policy_mutated": False, "authority_granted": False}

def load_memory_retrieval_outcome_history(runtime_root: str|Path|None=None) -> dict[str, Any]:
    state = load_json_file(_root(runtime_root)/"memory_retrieval_outcome_history_v2580.json", {"rows": []}, expected_type=dict)
    return {"ok": True, "contract_version": CONTRACT_VERSION, "rows": list(state.get("rows") or [])[-MAX_ROWS:], "raw_memory_text_stored": False}

__all__=["CONTRACT_VERSION","append_memory_retrieval_outcome","load_memory_retrieval_outcome_history"]
