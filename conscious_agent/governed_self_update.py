from __future__ import annotations
"""v1269.3-v1269.5 exact governed self-update, health verification and rollback."""
import base64, hashlib, os, tempfile, time, uuid
from pathlib import Path
from typing import Any, Callable, Mapping
from isolated_self_modification_foundations import source_only_manifest, _is_link_like
from ordinary_chat_development_campaign import _proposal_lock
from security_privacy_hardening import guard_governed_update_paths
from security_privacy_hardening_foundations import inspect_contained_path, validate_untrusted_relative_path
from governed_self_update_foundations import (DENIED_AUTHORITY, load_governed_self_update, validate_governed_self_update_packet, _runtime_root, _backup_path, _read_json, _write_json, _update_path, _record_digest, _digest, _rollback_path, _rollback_authorization_phrase)

CONTRACT_VERSION="v1269.5"; LEASE_SECONDS=90

def _file_digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def _capture_backup(update:Mapping[str,Any],source:Path,runtime_root=None)->dict[str,Any]:
    p=_backup_path(str(update["update_id"]),runtime_root);existing=_read_json(p)
    if existing:return existing
    entries=[];total=0
    for ch in update.get("changed_files") or []:
        rel=validate_untrusted_relative_path(str(ch["relative_path"]));inspect_contained_path(source,rel,require_exists=False);target=source/rel
        existed=target.is_file();data=target.read_bytes() if existed else b"";total+=len(data)
        entries.append({"relative_path":rel,"existed":existed,"content_digest":hashlib.sha256(data).hexdigest() if existed else "","content_b64":base64.b64encode(data).decode() if existed else ""})
    row={"schema_version":"1","update_id":update["update_id"],"source_manifest_digest":update["source_manifest_digest"],"entry_count":len(entries),"total_bytes":total,"entries":entries,"private_backup":True,"content_exposed":False};row["backup_digest"]=_digest({k:v for k,v in row.items() if k!="backup_digest"});_write_json(p,row);return row

def _restore_backup(source:Path,backup:Mapping[str,Any])->None:
    for e in backup.get("entries") or []:
        rel=validate_untrusted_relative_path(str(e["relative_path"]));inspect_contained_path(source,rel,require_exists=False);target=source/rel;target.parent.mkdir(parents=True,exist_ok=True);inspect_contained_path(source,rel,require_exists=False)
        if e.get("existed"):
            data=base64.b64decode(str(e.get("content_b64") or ""));
            if hashlib.sha256(data).hexdigest()!=e.get("content_digest"):raise ValueError("governed_self_update_backup_corrupt")
            fd,tmp=tempfile.mkstemp(prefix=".eidolon-restore-",dir=target.parent);os.close(fd);Path(tmp).write_bytes(data);os.replace(tmp,target)
        elif target.exists():
            if _is_link_like(target) or not target.is_file():raise ValueError("governed_self_update_restore_boundary_rejected")
            target.unlink()

def _current_state(source:Path,update:Mapping[str,Any])->str:
    d=source_only_manifest(source)["source_manifest_digest"]
    if d==update.get("source_manifest_digest"):return "baseline"
    if d==update.get("candidate_manifest_digest"):return "candidate"
    return "other"

def _affected_state(source:Path,update:Mapping[str,Any])->str:
    states=[]
    for ch in update.get("changed_files") or []:
        rel=validate_untrusted_relative_path(str(ch["relative_path"]));inspect_contained_path(source,rel,require_exists=False);target=source/rel
        digest=_file_digest(target) if target.is_file() else ""
        if digest==str(ch.get("before_digest") or ""): states.append("baseline")
        elif digest==str(ch.get("after_digest") or ""): states.append("candidate")
        else: states.append("conflict")
    if states and all(x=="baseline" for x in states):return "baseline"
    if states and all(x=="candidate" for x in states):return "candidate"
    if states and all(x in {"baseline","candidate"} for x in states):return "known_partial"
    return "conflict"

def _apply_reviewed_changes(source:Path,candidate:Path,update:Mapping[str,Any])->None:
    # Validate every reviewed path and every existing ancestor before the first
    # write, then re-run the containment guard immediately before each write.
    changes=list(update.get("changed_files") or [])
    guard_governed_update_paths(source,candidate,changes)
    for ch in changes:
        rel=validate_untrusted_relative_path(str(ch["relative_path"]));target=source/rel;src=candidate/rel
        inspect_contained_path(source,rel,require_exists=False)
        if ch.get("action")!="delete":inspect_contained_path(candidate,rel,require_exists=True,require_file=True)
        before=_file_digest(target) if target.is_file() else ""
        if before!=ch.get("before_digest"):raise ValueError("governed_self_update_affected_path_changed")
        if ch.get("action")!="delete" and (not src.is_file() or _file_digest(src)!=ch.get("after_digest")):raise ValueError("governed_self_update_candidate_path_changed")
    for ch in changes:
        rel=validate_untrusted_relative_path(str(ch["relative_path"]));inspect_contained_path(source,rel,require_exists=False);target=source/rel;src=candidate/rel
        if ch.get("action")!="delete":inspect_contained_path(candidate,rel,require_exists=True,require_file=True)
        if ch.get("action")=="delete":target.unlink(missing_ok=True);continue
        data=src.read_bytes();target.parent.mkdir(parents=True,exist_ok=True);inspect_contained_path(source,rel,require_exists=False);fd,tmp=tempfile.mkstemp(prefix=".eidolon-update-",dir=target.parent);os.close(fd);Path(tmp).write_bytes(data);os.replace(tmp,target)

def authorize_and_apply_governed_self_update(update_id:str,source_root:str|Path,*,runtime_root:str|Path|None,authorization_phrase:str,restart_health_verifier:Callable[[Path,str],Mapping[str,Any]])->dict[str,Any]:
    runtime=_runtime_root(runtime_root);source=Path(source_root).expanduser().resolve(strict=True)
    with _proposal_lock("devc_"+update_id.split("_",1)[1],runtime):
        rec=load_governed_self_update(update_id,runtime_root=runtime)
        if not rec or not validate_governed_self_update_packet(rec).get("ok"):raise ValueError("valid_governed_self_update_packet_required")
        if rec.get("phase")=="applied_verified":return {**rec.get("result",{}),"operation_status":"restored"}
        if rec.get("phase")=="rolled_back":return {**rec.get("result",{}),"operation_status":"restored"}
        if str(authorization_phrase or "")!=str(rec.get("authorization_phrase") or ""):return {"ok":False,"status":"governed_self_update_exact_authorization_required","update_id":update_id,"active_source_modified":False,**DENIED_AUTHORITY}
        state=_current_state(source,rec); affected=_affected_state(source,rec)
        if rec.get("phase")=="running" and affected in {"candidate","known_partial"}:
            backup=_read_json(_backup_path(update_id,runtime))
            if not backup:return {"ok":False,"status":"governed_self_update_recovery_backup_missing","update_id":update_id,"active_source_modified":affected!="baseline",**DENIED_AUTHORITY}
            _restore_backup(source,backup);state=_current_state(source,rec);affected=_affected_state(source,rec)
        if state!="baseline" or affected!="baseline":return {"ok":False,"status":"governed_self_update_active_source_stale","update_id":update_id,"active_source_modified":False,**DENIED_AUTHORITY}
        candidate=Path(str(rec.get("candidate_workspace_path") or "")).resolve(strict=True)
        if source_only_manifest(candidate)["source_manifest_digest"]!=rec.get("candidate_manifest_digest"):return {"ok":False,"status":"governed_self_update_candidate_stale","update_id":update_id,"active_source_modified":False,**DENIED_AUTHORITY}
        try:guard_governed_update_paths(source,candidate,rec.get("changed_files") or [])
        except ValueError:return {"ok":False,"status":"governed_self_update_path_security_blocked","update_id":update_id,"active_source_modified":False,**DENIED_AUTHORITY}
        backup=_capture_backup(rec,source,runtime_root=runtime)
        running=dict(rec);running.update({"contract_version":CONTRACT_VERSION,"phase":"running","status":"governed_self_update_running","authorization_consumed":True,"lease_token":uuid.uuid4().hex,"lease_expires_unix":time.time()+LEASE_SECONDS,"backup_digest":backup.get("backup_digest"),"write_started":False});running["record_digest"]=_record_digest(running);_write_json(_update_path(update_id,runtime),running)
        try:
            running["write_started"]=True;running["record_digest"]=_record_digest(running);_write_json(_update_path(update_id,runtime),running)
            _apply_reviewed_changes(source,candidate,rec)
            applied=source_only_manifest(source)
            if applied["source_manifest_digest"]!=rec.get("candidate_manifest_digest"):raise ValueError("governed_self_update_applied_manifest_mismatch")
            health=dict(restart_health_verifier(source,str(rec.get("candidate_manifest_digest"))))
            if health.get("ok") is not True:raise RuntimeError("governed_self_update_restart_health_failed")
            after_health=source_only_manifest(source)["source_manifest_digest"]
            if after_health!=rec.get("candidate_manifest_digest"):raise RuntimeError("governed_self_update_source_changed_during_health_verification")
            result={"ok":True,"status":"governed_self_update_applied_and_verified","update_id":update_id,"source_manifest_before":rec.get("source_manifest_digest"),"source_manifest_after":applied["source_manifest_digest"],"candidate_manifest_digest":rec.get("candidate_manifest_digest"),"changed_file_count":rec.get("changed_file_count"),"backup_prepared":True,"restart_attempted":True,"restart_health_passed":True,"health_digest":_digest(health),"monitor_signals_digest":_digest(health.get("signals") or []),"automatic_rollback_performed":False,"active_source_modified":True,"release_authorized":False,"promotion_authorized":False,"certification_authorized":False,"permanent_approval_granted":False,"independent_authority_granted":False}
            sealed=dict(running);sealed.update({"phase":"applied_verified","status":result["status"],"lease_token":"","lease_expires_unix":0.0,"result":result,"result_digest":_digest(result),"active_source_modified":True,**DENIED_AUTHORITY});sealed["record_digest"]=_record_digest(sealed);_write_json(_update_path(update_id,runtime),sealed);return result
        except Exception as exc:
            rollback_ok=False
            try:_restore_backup(source,backup);rollback_ok=_current_state(source,rec)=="baseline"
            except Exception:rollback_ok=False
            result={"ok":False,"status":"governed_self_update_rolled_back_after_failure" if rollback_ok else "governed_self_update_recovery_required","update_id":update_id,"failure_code":str(exc).split(":",1)[0][:120],"backup_prepared":True,"restart_attempted":True,"restart_health_passed":False,"automatic_rollback_performed":rollback_ok,"active_source_modified":not rollback_ok,"source_restored_to_baseline":rollback_ok}
            blocked=dict(running);blocked.update({"phase":"rolled_back" if rollback_ok else "blocked","status":result["status"],"lease_token":"","lease_expires_unix":0.0,"result":result,"result_digest":_digest(result),"active_source_modified":not rollback_ok,**DENIED_AUTHORITY});blocked["record_digest"]=_record_digest(blocked);_write_json(_update_path(update_id,runtime),blocked);return result

def prepare_successful_self_update_rollback(update_id:str,source_root:str|Path,*,runtime_root=None)->dict[str,Any]:
    runtime=_runtime_root(runtime_root);source=Path(source_root).resolve(strict=True);rec=load_governed_self_update(update_id,runtime_root=runtime)
    if not rec or rec.get("phase")!="applied_verified" or _current_state(source,rec)!="candidate":return {"ok":False,"status":"governed_self_update_rollback_not_available",**DENIED_AUTHORITY}
    rid=_digest({"update_id":update_id,"result_digest":rec.get("result_digest")});row={"ok":True,"contract_version":CONTRACT_VERSION,"status":"governed_self_update_rollback_prepared","update_id":update_id,"update_result_digest":rec.get("result_digest"),"rollback_digest":rid,"authorization_phrase":_rollback_authorization_phrase(update_id,rid),**DENIED_AUTHORITY};row["record_digest"]=_record_digest(row);_write_json(_rollback_path(update_id,runtime),row);return row

def authorize_and_rollback_successful_self_update(update_id:str,source_root:str|Path,*,runtime_root=None,authorization_phrase:str)->dict[str,Any]:
    runtime=_runtime_root(runtime_root);source=Path(source_root).resolve(strict=True)
    with _proposal_lock("devc_"+update_id.split("_",1)[1],runtime):
        rb=_read_json(_rollback_path(update_id,runtime));rec=load_governed_self_update(update_id,runtime_root=runtime)
        if not rb:return {"ok":False,"status":"governed_self_update_rollback_not_prepared",**DENIED_AUTHORITY}
        if str(authorization_phrase or "")!=str(rb.get("authorization_phrase") or ""):return {"ok":False,"status":"governed_self_update_rollback_exact_authorization_required",**DENIED_AUTHORITY}
        if rec.get("phase")=="rolled_back":return {**rec.get("result",{}),"operation_status":"restored"}
        if _current_state(source,rec)!="candidate":return {"ok":False,"status":"governed_self_update_rollback_source_conflict",**DENIED_AUTHORITY}
        backup=_read_json(_backup_path(update_id,runtime));_restore_backup(source,backup);ok=_current_state(source,rec)=="baseline"
        result={"ok":ok,"status":"governed_self_update_rollback_complete" if ok else "governed_self_update_rollback_failed","update_id":update_id,"active_source_modified":False if ok else True,"source_restored_to_baseline":ok}
        sealed=dict(rec);sealed.update({"phase":"rolled_back" if ok else "blocked","status":result["status"],"result":result,"result_digest":_digest(result),"active_source_modified":not ok,**DENIED_AUTHORITY});sealed["record_digest"]=_record_digest(sealed);_write_json(_update_path(update_id,runtime),sealed);return result

__all__=["CONTRACT_VERSION","authorize_and_apply_governed_self_update","prepare_successful_self_update_rollback","authorize_and_rollback_successful_self_update"]
