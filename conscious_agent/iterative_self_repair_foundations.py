from __future__ import annotations

"""v1267.0-v1267.2 foundations for bounded iterative self-repair.

Consumes one fresh v1266 test-selection record for one sealed v1265 disposable
self-candidate. Preparation is authority-free: it binds candidate/test lineage,
defines a bounded repair campaign, and persists no raw test/provider output.
"""

import hashlib, json, os, re, tempfile
from pathlib import Path
from typing import Any, Mapping

from intelligent_test_selection_foundations import load_test_selection, validate_test_selection, _digest as _selection_digest
from intelligent_test_selection_reliability import validate_test_selection_freshness
from isolated_self_modification_foundations import _runtime_root as _self_runtime_root, load_self_modification, source_only_manifest
from ordinary_chat_development_campaign import _proposal_lock

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1267.2"
MAX_REPAIR_ATTEMPTS = 2
MAX_RUNTIME_RECORD_BYTES = 4 * 1024 * 1024

ITERATIVE_REPAIR_DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "active_source_mutation_authorized": False,
    "selected_project_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "self_update_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _runtime_root(runtime_root: str | Path | None) -> Path:
    if runtime_root is None:
        raise ValueError("iterative_self_repair_runtime_root_required")
    return Path(runtime_root).expanduser().resolve()


def _record_dir(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "iterative_self_repair" / "records"


def _record_path(repair_id: str, runtime_root: str | Path | None) -> Path:
    if not re.fullmatch(r"selfrepair_[a-f0-9]{24}", str(repair_id or "")):
        raise ValueError("invalid_iterative_self_repair_id")
    return _record_dir(runtime_root) / f"{repair_id}.json"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    data=(json.dumps(dict(value),indent=2,sort_keys=True,ensure_ascii=True)+"\n").encode()
    if len(data)>MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("iterative_self_repair_record_too_large")
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=None
    try:
        with tempfile.NamedTemporaryFile("wb",delete=False,dir=path.parent,suffix=".tmp") as h:
            h.write(data);h.flush();os.fsync(h.fileno());tmp=Path(h.name)
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None: tmp.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    if path.stat().st_size>MAX_RUNTIME_RECORD_BYTES: raise ValueError("iterative_self_repair_record_too_large")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("iterative_self_repair_record_invalid")
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()


def _record_digest(record: Mapping[str, Any]) -> str:
    transient={"record_digest","operation_status","provider_called_this_invocation","tests_executed_this_invocation"}
    return _digest({k:v for k,v in record.items() if k not in transient})


def validate_iterative_self_repair_foundation(record: Mapping[str, Any]) -> dict[str, Any]:
    digest_ok=bool(record.get("record_digest")) and record.get("record_digest")==_record_digest(record)
    authority_ok=all(record.get(k) is v for k,v in ITERATIVE_REPAIR_DENIED_AUTHORITY.items())
    semantic=(str(record.get("repair_id") or "").startswith("selfrepair_") and str(record.get("phase") or "") in {"prepared","running","passed","blocked","cancelled"}
              and bool(record.get("source_operation_id")) and bool(record.get("selection_id")) and bool(record.get("candidate_manifest_digest"))
              and int(record.get("max_repair_attempts") or 0)==MAX_REPAIR_ATTEMPTS and record.get("active_source_modified") is False
              and record.get("operator_review_required") is True and isinstance(record.get("attempts"),list))
    ok=digest_ok and authority_ok and semantic
    return {"ok":ok,"status":"iterative_self_repair_foundation_valid" if ok else "iterative_self_repair_foundation_invalid","record_digest_valid":digest_ok,"authority_contained":authority_ok,"semantic_valid":semantic}


def prepare_iterative_self_repair(
    selection_id: str,
    source_root: str | Path,
    *,
    self_modification_runtime_root: str | Path | None,
    test_selection_runtime_root: str | Path | None,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    source=Path(source_root).expanduser().resolve(strict=True)
    freshness=validate_test_selection_freshness(selection_id,source,self_modification_runtime_root=self_modification_runtime_root,runtime_root=test_selection_runtime_root)
    if not freshness.get("ok"): raise ValueError("fresh_v1266_test_selection_required")
    selection=load_test_selection(selection_id,runtime_root=test_selection_runtime_root)
    if not validate_test_selection(selection).get("ok"): raise ValueError("valid_v1266_test_selection_required")
    op_id=str(selection.get("source_operation_id") or "")
    self_record=load_self_modification(op_id,runtime_root=self_modification_runtime_root)
    if self_record.get("phase")!="sealed": raise ValueError("sealed_v1265_candidate_required")
    workspace=Path(str(self_record.get("workspace_path") or "")).expanduser().resolve(strict=True)
    manifest=source_only_manifest(workspace)
    if manifest["source_manifest_digest"]!=selection.get("candidate_manifest_digest"): raise ValueError("candidate_selection_manifest_mismatch")
    repair_id="selfrepair_"+hashlib.sha256(f"{selection_id}:{selection.get('selection_digest')}:{manifest['source_manifest_digest']}".encode()).hexdigest()[:24]
    path=_record_path(repair_id,runtime_root)
    lock="devc_"+repair_id.split("_",1)[1]
    with _proposal_lock(lock,_runtime_root(runtime_root)):
        existing=_read_json(path)
        if existing:
            if not validate_iterative_self_repair_foundation(existing).get("ok"): raise ValueError("stored_iterative_self_repair_invalid")
            return {**existing,"operation_status":"restored"}
        phrase=f"AUTHORIZE SELF REPAIR {repair_id[-12:].upper()}"
        record={
            "ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"iterative_self_repair_prepared","phase":"prepared",
            "repair_id":repair_id,"source_operation_id":op_id,"selection_id":selection_id,"selection_digest":selection.get("selection_digest",""),
            "source_manifest_digest":source_only_manifest(source)["source_manifest_digest"],"candidate_manifest_digest":manifest["source_manifest_digest"],
            "selected_test_count":int(selection.get("selected_test_count") or 0),"selected_test_digest":_digest(selection.get("selected_tests") or []),
            "affected_surfaces":list(selection.get("affected_surfaces") or []),"risk_band":selection.get("risk_band",""),
            "authorization_phrase":phrase,"authorization_consumed":False,"max_repair_attempts":MAX_REPAIR_ATTEMPTS,"attempts":[],
            "operator_review_required":True,"active_source_modified":False,"candidate_workspace_modified":False,"tests_executed":False,"provider_contacted":False,
            **ITERATIVE_REPAIR_DENIED_AUTHORITY,
        }
        record["record_digest"]=_record_digest(record);_write_json(path,record)
        return {**record,"operation_status":"created"}


def load_iterative_self_repair(repair_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read_json(_record_path(repair_id,runtime_root))


def public_iterative_self_repair(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok":record.get("ok") is True,"status":record.get("status",""),"phase":record.get("phase",""),"repair_id":record.get("repair_id",""),
        "source_operation_id":record.get("source_operation_id",""),"selection_id":record.get("selection_id",""),"risk_band":record.get("risk_band",""),
        "attempt_count":len(record.get("attempts") or []),"max_repair_attempts":record.get("max_repair_attempts",MAX_REPAIR_ATTEMPTS),
        "tests_executed":record.get("tests_executed") is True,"provider_contacted":record.get("provider_contacted") is True,
        "active_source_modified":False,"operator_review_required":True,"content_minimized":True,**ITERATIVE_REPAIR_DENIED_AUTHORITY,
    }

__all__=["CONTRACT_VERSION","MAX_REPAIR_ATTEMPTS","ITERATIVE_REPAIR_DENIED_AUTHORITY","prepare_iterative_self_repair","load_iterative_self_repair","public_iterative_self_repair","validate_iterative_self_repair_foundation","_digest","_record_digest","_record_path","_write_json","_runtime_root"]
