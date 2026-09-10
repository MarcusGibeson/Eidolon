from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import socket
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from bounded_capability_evidence import bounded_float, digest, sealed, valid_seal

CONTRACT_VERSION="v1450.9"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_loopback_url(url:str) -> bool:
    try:
        p=urlparse(url); host=(p.hostname or "").lower()
        return (
            p.scheme in {"http","https"}
            and host in {"127.0.0.1","localhost","::1"}
            and p.port is not None
            and p.username is None
            and p.password is None
            and not p.query
            and not p.fragment
        )
    except Exception:return False


def native_desktop_shell_contract(config:Mapping[str,Any], *, version:str="1441.9") -> dict[str,Any]:
    dashboard=str(config.get("dashboard_url") or "http://127.0.0.1:8765"); api=str(config.get("api_url") or "http://127.0.0.1:8766")
    payload={"container":"windows_tkinter_localhost_shell","supported_platform":"windows","single_instance":True,"instance_lock_scope":"per_user","dashboard_url":dashboard,"api_url":api,"localhost_boundaries_valid":validate_loopback_url(dashboard) and validate_loopback_url(api),"remote_binding_denied":True,"browser_fallback":True}
    return sealed("native_desktop_shell",payload,version=version)


def _pid_alive(pid:int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def acquire_single_instance_lease(lock_path:Path, *, pid:int|None=None) -> dict[str,Any]:
    pid=int(pid or os.getpid()); lock_path=Path(lock_path); lock_path.parent.mkdir(parents=True,exist_ok=True)
    stale_reconciled=False
    for _attempt in range(2):
        try: existing=int(lock_path.read_text().strip())
        except FileNotFoundError: existing=0
        except Exception: existing=-1
        if existing == pid:
            return {"ok":True,"status":"lease_reused","pid":pid,"stale_reconciled":stale_reconciled}
        if existing>0 and _pid_alive(existing):
            return {"ok":False,"status":"instance_already_running","existing_pid":existing,"pid":pid,"stale_reconciled":False}
        if existing:
            stale_reconciled=True
            try: lock_path.unlink()
            except FileNotFoundError: pass
        try:
            descriptor=os.open(lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError:
            continue
        with os.fdopen(descriptor,"w",encoding="utf-8") as handle:
            handle.write(str(pid)); handle.flush(); os.fsync(handle.fileno())
        return {"ok":True,"status":"lease_acquired","pid":pid,"stale_reconciled":stale_reconciled}
    return {"ok":False,"status":"instance_lock_race","pid":pid,"stale_reconciled":stale_reconciled}


def desktop_lifecycle_transition(state:str,event:str, *, version:str="1442.9") -> dict[str,Any]:
    table={
      ("stopped","start"):"running",("running","minimize"):"hidden",("hidden","restore"):"running",("running","exit"):"stopped",("hidden","exit"):"stopped",("running","restart"):"restarting",("hidden","restart"):"restarting",("restarting","ready"):"running",("running","crash"):"recovering",("hidden","crash"):"recovering",("recovering","ready"):"running",("recovering","give_up"):"stopped"}
    nxt=table.get((state,event)); valid=nxt is not None
    return sealed("desktop_lifecycle",{"from":state,"event":event,"to":nxt or state,"valid":valid,"auto_start_operator_choice_required":True,"stale_process_reconciliation":True},version=version)


def conversation_workspace_contract(state:Mapping[str,Any], *, version:str="1443.9") -> dict[str,Any]:
    payload={"composer_visible":bool(state.get("composer_visible",True)),"enter_sends":True,"shift_enter_newline":True,"scroll_anchor_stable":bool(state.get("scroll_anchor_stable",True)),"draft_persisted":bool(state.get("draft_persisted",True)),"navigation_stable":bool(state.get("navigation_stable",True)),"tab_owner":str(state.get("tab_owner") or "single-writer"),"first_visible_token_ms":int(state.get("first_visible_token_ms",250)),"duplicate_send_count":int(state.get("duplicate_send_count",0))}
    payload["workspace_ready"]=all((payload["composer_visible"],payload["scroll_anchor_stable"],payload["draft_persisted"],payload["navigation_stable"],payload["duplicate_send_count"]==0))
    return sealed("conversation_workspace",payload,version=version)


def development_workspace_projection(work:Mapping[str,Any], *, version:str="1444.9") -> dict[str,Any]:
    keys=("goal","plan","changed_files","tests","logs","evidence","diffs","authority","status"); view={k:work.get(k) for k in keys}; controls={"pause":work.get("status")=="active","cancel":work.get("status") in {"active","paused","queued"},"rollback":work.get("status")=="completed" and bool(work.get("rollback_available"))}
    return sealed("development_workspace",{"view":view,"controls":controls,"authority_always_visible":True,"hidden_mutation_controls":False},version=version)


def provider_setup_assessment(config:Mapping[str,Any], capability:Mapping[str,Any], *, version:str="1445.9") -> dict[str,Any]:
    endpoint=str(config.get("endpoint") or ""); loopback=validate_loopback_url(endpoint); required=set(config.get("required_capabilities") or []); available=set(capability.get("capabilities") or []); missing=sorted(required-available); latency=capability.get("latency_ms")
    return sealed("provider_setup",{"provider":config.get("provider"),"model":config.get("model"),"description":config.get("description",""),"endpoint_loopback":loopback,"capability_match":not missing,"missing_capabilities":missing,"latency_ms":latency,"offline_guidance":not loopback or bool(missing),"model_installation_performed":False,"model_deletion_performed":False},version=version)


def notification_decision(event:Mapping[str,Any], policy:Mapping[str,Any], *, version:str="1446.9") -> dict[str,Any]:
    kind=str(event.get("kind") or "info"); actionable=kind in {"completion","clarification","failure","rollback","resource_limit"}; quiet=bool(policy.get("quiet_hours")); urgent=kind in {"failure","rollback","resource_limit"} and bool(event.get("urgent")); muted=kind in set(policy.get("muted_kinds") or []); show=actionable and not muted and (not quiet or urgent)
    return sealed("desktop_notification",{"kind":kind,"actionable":actionable,"decision":"show" if show else "suppress","quiet_hours":quiet,"urgent":urgent,"muted":muted,"actions":["open","dismiss"] if show else []},version=version)


def accessibility_assessment(checks:Mapping[str,Any], *, version:str="1447.9") -> dict[str,Any]:
    required=("keyboard_only","focus_order","screen_reader_labels","contrast","zoom_200","narrow_layout","reduced_motion","remote_mobile_input")
    rows={k:bool(checks.get(k)) for k in required}; return sealed("desktop_accessibility",{"checks":rows,"passed":sum(rows.values()),"total":len(rows),"ready":all(rows.values()),"manual_windows_validation_required":True},version=version)


class WindowsDpapiAdapter:
    """Windows-only encryption adapter. Native calls are intentionally deferred until used on Windows."""
    name="windows-dpapi-current-user"
    @staticmethod
    def available()->bool: return os.name=="nt"
    @staticmethod
    def encrypt(data:bytes)->bytes:
        if os.name!="nt": raise RuntimeError("windows_dpapi_unavailable")
        import ctypes
        from ctypes import wintypes
        class BLOB(ctypes.Structure): _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_byte))]
        def blob(b):
            buf=ctypes.create_string_buffer(b); return BLOB(len(b),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte))),buf
        inp,buf=blob(data); out=BLOB(); crypt32=ctypes.windll.crypt32; kernel32=ctypes.windll.kernel32
        if not crypt32.CryptProtectData(ctypes.byref(inp),"Eidolon",None,None,None,0,ctypes.byref(out)): raise ctypes.WinError()
        try:return ctypes.string_at(out.pbData,out.cbData)
        finally:kernel32.LocalFree(out.pbData)
    @staticmethod
    def decrypt(data:bytes)->bytes:
        if os.name!="nt": raise RuntimeError("windows_dpapi_unavailable")
        import ctypes
        from ctypes import wintypes
        class BLOB(ctypes.Structure): _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_byte))]
        def blob(b):
            buf=ctypes.create_string_buffer(b); return BLOB(len(b),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte))),buf
        inp,buf=blob(data); out=BLOB(); desc=ctypes.c_wchar_p(); crypt32=ctypes.windll.crypt32; kernel32=ctypes.windll.kernel32
        if not crypt32.CryptUnprotectData(ctypes.byref(inp),ctypes.byref(desc),None,None,None,0,ctypes.byref(out)): raise ctypes.WinError()
        try:return ctypes.string_at(out.pbData,out.cbData)
        finally:kernel32.LocalFree(out.pbData)


def _safe_backup_path(value:Any) -> str | None:
    name=str(value or "").replace("\\","/")
    path=PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
        return None
    normalized=path.as_posix()
    return normalized if normalized not in {".", ""} else None


def build_encrypted_backup(files:Mapping[str,bytes], encrypt:Callable[[bytes],bytes], *, selected:Sequence[str]|None=None, version:str="1448.9") -> dict[str,Any]:
    names=sorted(selected or files.keys()); payload={"schema":"eidolon-runtime-backup-v1","files":[]}
    for name in names:
        if name not in files: continue
        safe_name=_safe_backup_path(name)
        if safe_name is None: raise ValueError(f"unsafe_backup_path:{name}")
        data=files[name]; payload["files"].append({"path":safe_name,"sha256":hashlib.sha256(data).hexdigest(),"data_b64":base64.b64encode(data).decode("ascii")})
    raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode(); encrypted=encrypt(raw)
    return sealed("encrypted_backup",{"selected_paths":names,"file_count":len(payload["files"]),"plaintext_manifest_digest":hashlib.sha256(raw).hexdigest(),"encrypted_blob_b64":base64.b64encode(encrypted).decode("ascii"),"encrypted_blob_sha256":hashlib.sha256(encrypted).hexdigest(),"selective_restore_supported":True,"migration_preview_required":True,"operator_controlled":True},version=version,content_free=False)


def restore_encrypted_backup(record:Mapping[str,Any], decrypt:Callable[[bytes],bytes], *, selected:Sequence[str]|None=None, apply:bool=False) -> dict[str,Any]:
    if not valid_seal(record): return {"ok":False,"status":"backup_evidence_invalid","restored":{}}
    try: raw=decrypt(base64.b64decode(record["payload"]["encrypted_blob_b64"])); manifest=json.loads(raw.decode())
    except Exception:return {"ok":False,"status":"backup_decryption_failed","restored":{}}
    wanted=set(selected or [x["path"] for x in manifest.get("files",[]) ]); restored={}; bad=[]
    for row in manifest.get("files",[]):
        if row.get("path") not in wanted:continue
        safe_name=_safe_backup_path(row.get("path"))
        if safe_name is None: bad.append(row.get("path")); continue
        data=base64.b64decode(row["data_b64"])
        if hashlib.sha256(data).hexdigest()!=row.get("sha256"): bad.append(row.get("path")); continue
        restored[safe_name]=data
    return {"ok":not bad,"status":"restore_preview_ready" if not apply else "restore_materialization_requires_external_operator_boundary","restored":restored if not apply else {},"selected":sorted(wanted),"integrity_failures":bad,"apply_performed":False,"migration_preview":{"file_count":len(restored),"paths":sorted(restored)}}


def update_experience(candidate:Mapping[str,Any], *, version:str="1449.9") -> dict[str,Any]:
    candidate_version=str(candidate.get("version") or "").strip(); current_version=str(candidate.get("current_version") or "").strip()
    checks={"candidate_identified":bool(candidate_version) and candidate_version!=current_version,"download_staged":bool(_SHA256_RE.fullmatch(str(candidate.get("staged_path_digest") or ""))),"manifest_verified":bool(candidate.get("manifest_valid")),"hash_verified":bool(candidate.get("hash_valid")),"clean_extract_verified":bool(candidate.get("clean_extract_valid")),"isolated_verification_passed":bool(candidate.get("isolated_verification_passed")),"rollback_artifact_ready":bool(_SHA256_RE.fullmatch(str(candidate.get("rollback_artifact_digest") or "")))}
    ready=all(checks.values())
    return sealed("update_experience",{"candidate_version":candidate_version,"current_version":current_version,"checks":checks,"preview_ready":ready,"installation_authorized":False,"promotion_authorized":False,"rollback_separate":True,"clear_current_version_reporting":True},version=version)


def build_desktop_alpha_preflight(*, shell:Mapping[str,Any], lifecycle:Mapping[str,Any], conversation:Mapping[str,Any], development:Mapping[str,Any], provider:Mapping[str,Any], notification:Mapping[str,Any], accessibility:Mapping[str,Any], backup:Mapping[str,Any], update:Mapping[str,Any], version:str="1450.9") -> dict[str,Any]:
    inputs=[shell,lifecycle,conversation,development,provider,notification,accessibility,backup,update]
    checks={"all_inputs_sealed":all(valid_seal(x) for x in inputs),"native_shell_contract":shell.get("payload",{}).get("localhost_boundaries_valid") is True,"desktop_lifecycle":lifecycle.get("payload",{}).get("valid") is True,"conversation_workspace":conversation.get("payload",{}).get("workspace_ready") is True,"development_workspace":development.get("payload",{}).get("authority_always_visible") is True,"provider_setup":provider.get("payload",{}).get("model_installation_performed") is False,"notifications_bounded":notification.get("payload",{}).get("actionable") is True,"accessibility_preflight":accessibility.get("payload",{}).get("ready") is True,"backup_encrypted":bool(backup.get("payload",{}).get("encrypted_blob_sha256")),"update_preview":update.get("payload",{}).get("preview_ready") is True,"manual_windows_multi_day_review_required":True}
    # This is intentionally a preflight only; v1450 cannot pass without external Windows evidence.
    return sealed("desktop_alpha_preflight",{"checks":checks,"preflight_ready":all(checks.values()),"desktop_alpha_checkpoint_ready":False,"blocked_reason":"manual_multi_day_windows_daily_use_review_required"},version=version)
