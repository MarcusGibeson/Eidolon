from __future__ import annotations
"""v2676 content-minimized response-grounding observability.

Stores only structural grounding posture for the most recent turn. It never
stores prompt, response, memory, or provider text and grants no authority.
"""
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic

CONTRACT_VERSION = "v2676.0"

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def _path(runtime_root: str|Path|None=None) -> Path:
    if runtime_root is not None:
        root=Path(runtime_root).expanduser().resolve()
    else:
        root=Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
    return root/"response_grounding_observability_v2676.json"

def record_response_grounding_observability(policy: Mapping[str,Any], calibration: Mapping[str,Any], *, operation_id: str, runtime_root: str|Path|None=None) -> dict[str,Any]:
    if not str(operation_id or "").strip(): raise ValueError("operation_id_required")
    row={
        "operation_ref_digest": hashlib.sha256(str(operation_id).encode()).hexdigest(),
        "assertiveness": str(policy.get("assertiveness") or "cautious")[:32],
        "memory_state": str(policy.get("memory_state") or "no_useful_memory")[:48],
        "preserve_uncertainty": bool(policy.get("preserve_uncertainty")),
        "personal_memory_reference_permitted": bool(policy.get("personal_memory_reference_permitted")),
        "assertion_level": str(calibration.get("assertion_level") or "explicit_uncertainty")[:32],
        "policy_digest": str(policy.get("policy_digest") or "")[:64],
        "calibration_digest": str(calibration.get("calibration_digest") or "")[:64],
        "raw_prompt_stored": False,
        "raw_response_stored": False,
        "raw_memory_text_stored": False,
        "authority_granted": False,
    }
    row["observability_digest"]=_digest(row)
    path=_path(runtime_root); path.parent.mkdir(parents=True,exist_ok=True)
    payload={"contract_version":CONTRACT_VERSION,"present":True,"grounding":row,"observability_digest":row["observability_digest"],"authority_granted":False}
    write_json_atomic(path,payload,expected_type=dict,sort_keys=True)
    return payload

def load_response_grounding_observability(runtime_root: str|Path|None=None) -> dict[str,Any]:
    state=load_json_file(_path(runtime_root), {"contract_version":CONTRACT_VERSION,"present":False,"grounding":{},"authority_granted":False}, expected_type=dict)
    return {"contract_version":CONTRACT_VERSION,"present":bool(state.get("present")),"grounding":dict(state.get("grounding") or {}),"observability_digest":str(state.get("observability_digest") or ""),"authority_granted":False}

__all__=["CONTRACT_VERSION","record_response_grounding_observability","load_response_grounding_observability"]
