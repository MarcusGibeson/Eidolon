from __future__ import annotations
"""Versioned, balanced dataset manifests. No training authority is granted."""
import hashlib,json,time
from collections import Counter
from typing import Any, Iterable, Mapping
from model_training.training_schema import normalize_training_record
from model_training.training_dedup import deduplicate_records
CONTRACT_VERSION="v2503.4.28.2"
# High ceilings, not target sizes. Defaults must not make the readiness threshold unreachable.
DEFAULT_CAPS={"coding":2500,"repair":2500,"research":2000,"planning":1500,"tool_use":1500,"governance":1500,"conversation":1500,"memory":1000,"abstention":1000,"other":1000}

def _record_binding(record: Mapping[str,Any]) -> dict[str,str]:
    n=normalize_training_record(record)
    digest=str(record.get("record_digest") or "")
    if len(digest)!=64: digest=str(n.get("normalized_digest") or "")
    return {"record_id":n["record_id"],"record_digest":digest}

def _manifest_digest(payload: Mapping[str,Any]) -> str:
    return hashlib.sha256(json.dumps(dict(payload),ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _hex64(value: Any) -> bool:
    text=str(value or "")
    return len(text)==64 and all(c in "0123456789abcdefABCDEF" for c in text)

def validate_dataset_manifest(manifest: Mapping[str,Any]) -> bool:
    if not isinstance(manifest,Mapping) or not _hex64(manifest.get("manifest_digest")):
        return False
    body={k:v for k,v in manifest.items() if k!="manifest_digest"}
    if str(manifest.get("manifest_digest"))!=_manifest_digest(body):
        return False
    version=str(manifest.get("dataset_version") or "").strip()
    record_ids=manifest.get("record_ids")
    bindings=manifest.get("record_bindings")
    counts=manifest.get("capability_counts")
    if not version or not isinstance(record_ids,list) or not isinstance(bindings,list) or not isinstance(counts,Mapping):
        return False
    try:
        record_count=int(manifest.get("record_count"))
        dedup_rejected=int(manifest.get("dedup_rejected_count") or 0)
    except (TypeError,ValueError):
        return False
    if record_count<0 or dedup_rejected<0 or record_count!=len(record_ids) or record_count!=len(bindings):
        return False
    if len(set(map(str,record_ids)))!=len(record_ids) or any(not str(rid).startswith("trn_") for rid in record_ids):
        return False
    binding_ids=[]
    for row in bindings:
        if not isinstance(row,Mapping):
            return False
        rid=str(row.get("record_id") or "")
        if not rid.startswith("trn_") or not _hex64(row.get("record_digest")):
            return False
        binding_ids.append(rid)
    if binding_ids!=list(map(str,record_ids)) or len(set(binding_ids))!=len(binding_ids):
        return False
    total=0
    for key,value in counts.items():
        if not str(key).strip(): return False
        try: n=int(value)
        except (TypeError,ValueError): return False
        if n<0: return False
        total+=n
    if total!=record_count:
        return False
    if manifest.get("runtime_only") is not True or manifest.get("model_training_authorized") is not False or manifest.get("model_promotion_authorized") is not False:
        return False
    return True

def build_dataset_manifest(records: Iterable[Mapping[str,Any]], *, dataset_version:str, per_capability_caps:Mapping[str,int]|None=None)->dict[str,Any]:
    dedup=deduplicate_records(records); caps=dict(DEFAULT_CAPS); caps.update(dict(per_capability_caps or {})); selected=[]; bindings=[]; counts=Counter()
    for r in dedup["kept_records"]:
        n=normalize_training_record(r); cap=n["capability"]
        if counts[cap] >= int(caps.get(cap,1000)): continue
        selected.append(n["record_id"]); bindings.append(_record_binding(r)); counts[cap]+=1
    payload={"contract_version":CONTRACT_VERSION,"dataset_version":str(dataset_version),"record_ids":selected,"record_bindings":bindings,"record_count":len(selected),"capability_counts":dict(sorted(counts.items())),"dedup_rejected_count":len(dedup["rejected"]),"created_at_ns":time.time_ns(),"runtime_only":True,"model_training_authorized":False,"model_promotion_authorized":False}
    payload["manifest_digest"]=_manifest_digest(payload)
    return payload

def materialize_dataset_manifest(*, runtime_root, dataset_version: str, operator_authorized: bool, per_capability_caps: Mapping[str,int] | None = None) -> dict[str,Any]:
    from model_training.training_record import _training_root, _atomic_json, load_training_record
    if operator_authorized is not True: return {"ok":False,"status":"dataset_manifest_operator_authorization_required","model_training_authorized":False}
    root=_training_root(runtime_root); approved=root/"approved"; records=[]
    for path in sorted(approved.glob("trn_*.json")) if approved.exists() else []:
        row=load_training_record(path.stem,runtime_root=runtime_root,stage="approved")
        if row and row.get("approved_for_training") is True and row.get("sanitized") is True: records.append(row)
    manifest=build_dataset_manifest(records,dataset_version=dataset_version,per_capability_caps=per_capability_caps); manifest["approved_store_provenance_required"]=True; manifest["manifest_digest"]=_manifest_digest({k:v for k,v in manifest.items() if k!="manifest_digest"})
    safe="".join(c if c.isalnum() or c in "._-" else "-" for c in str(dataset_version))[:96]; path=root/"datasets"/f"{safe}.manifest.json"
    if path.exists():
        try: existing=json.loads(path.read_text(encoding="utf-8"))
        except Exception: existing={}
        comparable=lambda row:{k:v for k,v in dict(row).items() if k not in {"created_at_ns","manifest_digest"}}
        if validate_dataset_manifest(existing) and comparable(existing)==comparable(manifest):
            return {"ok":True,"status":"dataset_manifest_restored","manifest":existing,"runtime_path":str(path),"model_training_authorized":False}
        return {"ok":False,"status":"dataset_manifest_version_conflict","runtime_path":str(path),"model_training_authorized":False}
    _atomic_json(path,manifest); return {"ok":True,"status":"dataset_manifest_materialized","manifest":manifest,"runtime_path":str(path),"model_training_authorized":False}
