from __future__ import annotations
"""v1269.0-v1269.2 governed self-update foundations.

Preparation consumes an explicitly approved v1268 review handoff, rechecks the
active source and disposable self-candidate, and seals one exact update packet.
Preparation is read-only.  No update, rollback, installation, promotion,
certification, release, or standing authority is created here.
"""
import base64, hashlib, json, os, re, tempfile
from pathlib import Path
from typing import Any, Mapping
from isolated_self_modification_foundations import load_self_modification, source_only_manifest, _is_link_like
from operator_review_handoff_foundations import load_operator_review_packet, validate_operator_review_packet, _decision_path as _review_decision_path, _read_json as _review_read_json, _record_digest as _review_record_digest
from operator_review_handoff import build_v1269_review_handoff
from operator_review_handoff_reliability import validate_operator_review_freshness
from ordinary_chat_development_campaign import _proposal_lock

SCHEMA_VERSION="1"; CONTRACT_VERSION="v1269.2"; MAX_RECORD_BYTES=16*1024*1024; MAX_UPDATE_FILES=64; MAX_UPDATE_BYTES=8*1024*1024
DENIED_AUTHORITY={
 "provider_contact_authorized":False,"command_execution_authorized":False,"test_execution_authorized":False,
 "repair_authorized":False,"active_source_mutation_authorized":False,"source_application_authorized":False,
 "installation_authorized":False,"promotion_authorized":False,"certification_authorized":False,
 "release_authorized":False,"self_update_authorized":False,"rollback_authorized":False,
 "permanent_approval_granted":False,"independent_authority_granted":False,
}

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _runtime_root(v:str|Path|None)->Path:
    if v is None: raise ValueError("governed_self_update_runtime_root_required")
    return Path(v).expanduser().resolve()
def _update_path(update_id:str,runtime_root=None)->Path:
    if not re.fullmatch(r"selfupdate_[a-f0-9]{24}",str(update_id or "")):raise ValueError("invalid_governed_self_update_id")
    return _runtime_root(runtime_root)/"governed_self_update"/"updates"/f"{update_id}.json"
def _backup_path(update_id:str,runtime_root=None)->Path:return _runtime_root(runtime_root)/"governed_self_update"/"backups"/f"{update_id}.json"
def _rollback_path(update_id:str,runtime_root=None)->Path:return _runtime_root(runtime_root)/"governed_self_update"/"rollbacks"/f"{update_id}.json"
def _write_json(path:Path,value:Mapping[str,Any])->None:
    data=(json.dumps(dict(value),indent=2,sort_keys=True,ensure_ascii=True)+"\n").encode()
    if len(data)>MAX_RECORD_BYTES:raise ValueError("governed_self_update_record_too_large")
    path.parent.mkdir(parents=True,exist_ok=True);tmp=None
    try:
        with tempfile.NamedTemporaryFile("wb",delete=False,dir=path.parent,suffix=".tmp") as h:h.write(data);h.flush();os.fsync(h.fileno());tmp=Path(h.name)
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)
def _read_json(path:Path)->dict[str,Any]:
    if not path.exists():return {}
    if path.stat().st_size>MAX_RECORD_BYTES:raise ValueError("governed_self_update_record_too_large")
    v=json.loads(path.read_text(encoding="utf-8"));
    if not isinstance(v,dict):raise ValueError("governed_self_update_record_invalid")
    return v
def _record_digest(r:Mapping[str,Any])->str:return _digest({k:v for k,v in r.items() if k not in {"record_digest","operation_status"}})
def _valid_record(r:Mapping[str,Any])->bool:return bool(r.get("record_digest")) and r.get("record_digest")==_record_digest(r)
def _manifest_map(m:Mapping[str,Any])->dict[str,dict[str,Any]]:return {str(x.get("relative_path") or ""):dict(x) for x in m.get("files") or []}
def _changed(active:Mapping[str,Any],candidate:Mapping[str,Any])->list[dict[str,Any]]:
    a=_manifest_map(active);b=_manifest_map(candidate);rows=[];total=0
    for rel in sorted(set(a)|set(b),key=str.casefold):
        before=a.get(rel);after=b.get(rel)
        if (before or {}).get("content_digest")== (after or {}).get("content_digest"):continue
        if len(rows)>=MAX_UPDATE_FILES:raise ValueError("governed_self_update_file_limit_exceeded")
        size=int((after or {}).get("size_bytes") or 0);total+=size
        if total>MAX_UPDATE_BYTES:raise ValueError("governed_self_update_byte_limit_exceeded")
        reserved={"con","prn","aux","nul",*(f"com{i}" for i in range(1,10)),*(f"lpt{i}" for i in range(1,10))}
        for part in Path(rel).parts:
            stem=part.split(".",1)[0].casefold()
            if stem in reserved or part.endswith(("."," ")): raise ValueError("governed_self_update_windows_path_ambiguous")
        rows.append({"relative_path":rel,"action":"create" if before is None else "delete" if after is None else "modify","before_digest":(before or {}).get("content_digest",""),"after_digest":(after or {}).get("content_digest",""),"before_size_bytes":int((before or {}).get("size_bytes") or 0),"after_size_bytes":size,"content_exposed":False})
    if not rows:raise ValueError("governed_self_update_candidate_has_no_changes")
    if len({x["relative_path"].casefold() for x in rows})!=len(rows):raise ValueError("governed_self_update_casefold_collision")
    return rows

def _authorization_phrase(update_id:str,packet_digest:str)->str:return f"AUTHORIZE EIDOLON SELF UPDATE {update_id} {packet_digest[:16]}"
def _rollback_authorization_phrase(update_id:str,result_digest:str)->str:return f"AUTHORIZE EIDOLON SELF UPDATE ROLLBACK {update_id} {result_digest[:16]}"

def validate_governed_self_update_packet(r:Mapping[str,Any])->dict[str,Any]:
    digest_ok=_valid_record(r);authority_ok=all(r.get(k) is v for k,v in DENIED_AUTHORITY.items());semantic=(r.get("phase") in {"prepared","running","applied_verified","rolled_back","blocked"} and bool(r.get("update_id")) and bool(r.get("source_manifest_digest")) and bool(r.get("candidate_manifest_digest")) and isinstance(r.get("changed_files"),list))
    ok=digest_ok and authority_ok and semantic
    return {"ok":ok,"status":"governed_self_update_packet_valid" if ok else "governed_self_update_packet_invalid","digest_valid":digest_ok,"authority_contained":authority_ok,"semantic_valid":semantic}

def prepare_governed_self_update(review_id:str,source_root:str|Path,*,self_modification_runtime_root:str|Path|None,review_runtime_root:str|Path|None,runtime_root:str|Path|None)->dict[str,Any]:
    source=Path(source_root).expanduser().resolve(strict=True);handoff=build_v1269_review_handoff(review_id,runtime_root=review_runtime_root)
    if not handoff.get("ok"):raise ValueError("approved_v1268_handoff_required")
    freshness=validate_operator_review_freshness(review_id,source,self_modification_runtime_root=self_modification_runtime_root,runtime_root=review_runtime_root)
    if not freshness.get("ok"):raise ValueError("v1268_handoff_not_fresh")
    packet=load_operator_review_packet(review_id,runtime_root=review_runtime_root)
    if not packet or not validate_operator_review_packet(packet).get("ok"):raise ValueError("valid_v1268_review_packet_required")
    decision=_review_read_json(_review_decision_path(review_id,review_runtime_root))
    if not decision or decision.get("record_digest")!=_review_record_digest(decision) or decision.get("decision")!="approve_for_v1269_consideration" or decision.get("packet_digest")!=packet.get("record_digest"):
        raise ValueError("valid_v1268_approval_decision_required")
    selfrec=load_self_modification(str(packet.get("source_operation_id") or ""),runtime_root=self_modification_runtime_root)
    workspace=Path(str((selfrec or {}).get("workspace_path") or "")).expanduser().resolve(strict=True)
    if _is_link_like(workspace):raise ValueError("governed_self_update_candidate_link_rejected")
    active=source_only_manifest(source);candidate=source_only_manifest(workspace)
    if active["source_manifest_digest"]!=packet.get("source_manifest_digest"):raise ValueError("governed_self_update_active_source_stale")
    if candidate["source_manifest_digest"]!=packet.get("candidate_manifest_digest"):raise ValueError("governed_self_update_candidate_stale")
    changed=_changed(active,candidate)
    if _digest(changed)!=packet.get("changed_files_digest"):raise ValueError("governed_self_update_review_diff_mismatch")
    seed=f"{review_id}:{handoff.get('decision_digest')}:{active['source_manifest_digest']}:{candidate['source_manifest_digest']}";update_id="selfupdate_"+hashlib.sha256(seed.encode()).hexdigest()[:24]
    path=_update_path(update_id,runtime_root)
    with _proposal_lock("devc_"+update_id.split("_",1)[1],_runtime_root(runtime_root)):
        existing=_read_json(path)
        if existing:
            if not validate_governed_self_update_packet(existing).get("ok"):raise ValueError("stored_governed_self_update_packet_invalid")
            return {**existing,"operation_status":"restored"}
        row={"ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"governed_self_update_prepared","phase":"prepared","update_id":update_id,"review_id":review_id,"review_packet_digest":handoff.get("review_packet_digest"),"decision_digest":handoff.get("decision_digest"),"source_operation_id":packet.get("source_operation_id",""),"source_manifest_digest":active["source_manifest_digest"],"candidate_manifest_digest":candidate["source_manifest_digest"],"candidate_workspace_path":str(workspace),"changed_files":changed,"changed_file_count":len(changed),"changed_files_digest":_digest(changed),"fresh_preflight_passed":True,"backup_required_before_first_write":True,"restart_health_verification_required":True,"automatic_rollback_on_failure_required":True,"authorization_consumed":False,"active_source_modified":False,"content_minimized":True,**DENIED_AUTHORITY}
        row["record_digest"]=_record_digest(row);row["authorization_phrase"]=_authorization_phrase(update_id,row["record_digest"]);row["record_digest"]=_record_digest(row);_write_json(path,row);return {**row,"operation_status":"created"}

def load_governed_self_update(update_id:str,*,runtime_root=None)->dict[str,Any]:return _read_json(_update_path(update_id,runtime_root))

def public_governed_self_update(r:Mapping[str,Any])->dict[str,Any]:
    keys=("ok","status","phase","update_id","review_id","source_manifest_digest","candidate_manifest_digest","changed_files","changed_file_count","fresh_preflight_passed","backup_required_before_first_write","restart_health_verification_required","automatic_rollback_on_failure_required","authorization_consumed","active_source_modified","content_minimized")
    return {k:r.get(k) for k in keys}|DENIED_AUTHORITY

__all__=["CONTRACT_VERSION","DENIED_AUTHORITY","prepare_governed_self_update","load_governed_self_update","public_governed_self_update","validate_governed_self_update_packet","_digest","_record_digest","_read_json","_write_json","_update_path","_backup_path","_rollback_path","_authorization_phrase","_rollback_authorization_phrase","_changed"]
