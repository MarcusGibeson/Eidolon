from __future__ import annotations
"""v1338 bounded loopback service orchestration over v1336 process ownership."""
import hashlib
import http.client
import re
import socket
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions
from workspace_isolation import _record_path as _workspace_record_path
from typed_process_operations import start_candidate_process, monitor_candidate_process, stop_candidate_process

CONTRACT_VERSION = "v1338.8"
MAX_SERVICES = 16
MAX_DEPENDENCIES = 8
MAX_READINESS_SECONDS = 30.0
READINESS_KINDS = ("tcp", "http")
SERVICE_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
    "external_network_authorized": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_service_orchestration"


def _path(stack_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"services_[a-f0-9]{24}", str(stack_id or "")):
        raise ValueError("invalid_service_stack_id")
    return _root(runtime_root) / "records" / f"{stack_id}.json"


def _sealed(path: Path) -> dict[str, Any]:
    row = _read_json(path)
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None); row["record_digest"] = digest(row); _atomic_json(_path(str(row["service_stack_id"]), runtime_root), row); return row


def _workspace(workspace_id: str, runtime_root=None) -> dict[str, Any]:
    row = _sealed(_workspace_record_path(workspace_id, runtime_root))
    if not row or row.get("cleaned") or not row.get("workspace_created"):
        return {}
    return row


def _pre(record_id: str, tool: str, runtime_root=None) -> dict[str, Any]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    if not row or row.get("preconditions_satisfied") is not True or row.get("tool_code") != tool or row.get("tool_invoked") is not False:
        return {}
    return row


def _grant_ok(workspace: Mapping[str, Any], grant: Mapping[str, Any], now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(workspace.get("source_workspace_digest") or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, "command", now_unix=now_unix):
        return False, "active_command_grant_required"
    classes = set((grant.get("profile_snapshot") or {}).get("command_classes") or [])
    if "service" not in classes or not ({"shell", "process"} & classes):
        return False, "service_and_process_command_classes_required"
    return True, ""


def _service_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", text):
        raise ValueError("service_code_invalid")
    return text


def _definition(raw: Mapping[str, Any]) -> dict[str, Any]:
    code = _service_code(raw.get("service_code"))
    argv = raw.get("argv")
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence) or not argv:
        raise ValueError("service_argument_vector_required")
    args = [str(x) for x in argv]
    if len(args) > 128 or any(not x or "\x00" in x for x in args):
        raise ValueError("service_argument_vector_invalid")
    deps = [_service_code(x) for x in raw.get("dependencies") or ()]
    if len(deps) > MAX_DEPENDENCIES or code in deps or len(set(deps)) != len(deps):
        raise ValueError("service_dependencies_invalid")
    readiness = dict(raw.get("readiness") or {})
    kind = str(readiness.get("kind") or "tcp")
    if kind not in READINESS_KINDS:
        raise ValueError("service_readiness_kind_invalid")
    path = str(readiness.get("path") or "/")
    if kind == "http" and (not path.startswith("/") or len(path) > 1024):
        raise ValueError("service_readiness_path_invalid")
    expected = int(readiness.get("expected_status") or 200)
    if expected < 100 or expected > 599:
        raise ValueError("service_readiness_status_invalid")
    requested = int(raw.get("requested_port") or 0)
    if requested < 0 or requested > 65535:
        raise ValueError("service_port_invalid")
    readiness_seconds = max(0.25, min(MAX_READINESS_SECONDS, float(raw.get("readiness_timeout_seconds") or 8.0)))
    process_timeout = max(readiness_seconds + 1.0, min(3600.0, float(raw.get("process_timeout_seconds") or 300.0)))
    return {
        "service_code": code,
        "argv": args,
        "cwd_relative": str(raw.get("cwd_relative") or "."),
        "dependencies": deps,
        "readiness": {"kind": kind, "path": path, "expected_status": expected},
        "requested_port": requested,
        "readiness_timeout_seconds": readiness_seconds,
        "process_timeout_seconds": process_timeout,
    }


def _definition_digest(row: Mapping[str, Any]) -> str:
    public = {
        "service_code": row["service_code"], "arg_digests": [hashlib.sha256(x.encode()).hexdigest() for x in row["argv"]],
        "cwd_digest": hashlib.sha256(str(row["cwd_relative"]).encode()).hexdigest(), "dependencies": row["dependencies"],
        "readiness": row["readiness"], "requested_port": row["requested_port"],
        "readiness_timeout_seconds": row["readiness_timeout_seconds"], "process_timeout_seconds": row["process_timeout_seconds"],
    }
    return digest(public)


def _topological(defs: Sequence[Mapping[str, Any]]) -> list[str]:
    by = {str(x["service_code"]): x for x in defs}
    if len(by) != len(defs): raise ValueError("duplicate_service_code")
    for row in defs:
        if any(d not in by for d in row["dependencies"]): raise ValueError("service_dependency_missing")
    order: list[str] = []; visiting: set[str] = set(); done: set[str] = set()
    def visit(code: str):
        if code in done: return
        if code in visiting: raise ValueError("service_dependency_cycle")
        visiting.add(code)
        for dep in by[code]["dependencies"]: visit(dep)
        visiting.remove(code); done.add(code); order.append(code)
    for code in sorted(by): visit(code)
    return order


def _port_available(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0); s.bind(("127.0.0.1", port)); return True
    except OSError: return False
    finally: s.close()


def _choose_port(requested: int) -> int:
    if requested:
        if not _port_available(requested): raise ValueError("service_port_unavailable")
        return requested
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try: s.bind(("127.0.0.1", 0)); return int(s.getsockname()[1])
    finally: s.close()


def _args(row: Mapping[str, Any], port: int) -> list[str]:
    return [str(x).replace("{host}", "127.0.0.1").replace("{port}", str(port)) for x in row["argv"]]


def _ready(port: int, readiness: Mapping[str, Any]) -> bool:
    kind = str(readiness.get("kind"))
    if kind == "tcp":
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25): return True
        except OSError: return False
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.4)
    try:
        conn.request("GET", str(readiness.get("path") or "/"), headers={"Host": "127.0.0.1"})
        response = conn.getresponse(); response.read(1024)
        return response.status == int(readiness.get("expected_status") or 200)
    except OSError: return False
    finally:
        try: conn.close()
        except Exception: pass


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    services=[]
    for item in row.get("services") or []:
        services.append({k:item.get(k) for k in ("service_code","definition_digest","dependencies","port","readiness_kind","process_operation_id","process_state","readiness_state","restart_count","failure_code")})
    return {
        "contract_version": CONTRACT_VERSION, "service_stack_id": row.get("service_stack_id"), "workspace_id": row.get("workspace_id"),
        "source_workspace_digest": row.get("source_workspace_digest"), "service_precondition_record_id": row.get("service_precondition_record_id"),
        "process_precondition_record_id": row.get("process_precondition_record_id"), "grant_digest": row.get("grant_digest"),
        "service_count": len(services), "dependency_order": list(row.get("dependency_order") or []), "services": services,
        "stack_state": row.get("stack_state"), "ready_count": sum(1 for x in services if x.get("readiness_state")=="ready"),
        "cleanup_performed": row.get("cleanup_performed") is True, "orphaned_service_count": int(row.get("orphaned_service_count") or 0),
        "raw_command_exposed": False, "environment_values_exposed": False, "selected_source_modified": False,
        "loopback_declared_only": True, "os_network_sandbox_claimed": False, "content_free": True,
        "action_executed": row.get("action_executed") is True, **SERVICE_DENIED_AUTHORITY,
    }


def start_service_stack(
    workspace_id: str, definitions: Sequence[Mapping[str, Any]], *, active_grant: Mapping[str, Any],
    service_precondition_record_id: str, process_precondition_record_id: str, runtime_root=None, now_unix: int | None=None,
) -> dict[str, Any]:
    workspace=_workspace(str(workspace_id or ""),runtime_root); service_pre=_pre(service_precondition_record_id,"service",runtime_root); process_pre=_pre(process_precondition_record_id,"shell",runtime_root)
    if not workspace:return {"ok":False,"status":"candidate_workspace_required","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    if not service_pre:return {"ok":False,"status":"satisfied_service_precondition_required","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    if not process_pre:return {"ok":False,"status":"satisfied_shell_precondition_required","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    gok,reason=_grant_ok(workspace,active_grant,now_unix)
    if not gok:return {"ok":False,"status":reason,"action_executed":False,**SERVICE_DENIED_AUTHORITY}
    try:
        if not definitions or len(definitions)>MAX_SERVICES: raise ValueError("service_count_invalid")
        defs=[_definition(x) for x in definitions]; order=_topological(defs)
    except (TypeError,ValueError) as e:return {"ok":False,"status":str(e),"action_executed":False,**SERVICE_DENIED_AUTHORITY}
    by={x["service_code"]:x for x in defs}; material={"contract":CONTRACT_VERSION,"workspace":workspace_id,"defs":sorted((c,_definition_digest(x)) for c,x in by.items()),"order":order,"service_pre":service_pre.get("record_digest"),"process_pre":process_pre.get("record_digest"),"grant":active_grant.get("grant_digest")};stack_id="services_"+digest(material)[:24]
    existing=_sealed(_path(stack_id,runtime_root))
    if existing:return {"ok":existing.get("stack_state")=="ready","status":"service_stack_already_exists","service_stack":_public(existing),"action_executed":False,**SERVICE_DENIED_AUTHORITY}
    row={"contract_version":CONTRACT_VERSION,"service_stack_id":stack_id,"workspace_id":workspace_id,"source_workspace_digest":workspace.get("source_workspace_digest"),"service_precondition_record_id":service_precondition_record_id,"process_precondition_record_id":process_precondition_record_id,"grant_digest":active_grant.get("grant_digest"),"dependency_order":order,"services":[],"stack_state":"starting","cleanup_performed":False,"orphaned_service_count":0,"action_executed":False,**SERVICE_DENIED_AUTHORITY};_save(row,runtime_root)
    started=[]
    try:
        for code in order:
            spec=by[code];port=_choose_port(int(spec["requested_port"]));generation=0
            result=start_candidate_process(workspace_id,_args(spec,port),active_grant=active_grant,precondition_record_id=process_precondition_record_id,cwd_relative=spec["cwd_relative"],environment={"EIDOLON_SERVICE_HOST":"127.0.0.1","EIDOLON_SERVICE_PORT":str(port)},timeout_seconds=spec["process_timeout_seconds"],runtime_root=runtime_root,now_unix=now_unix,invocation_discriminator=f"service:{stack_id}:{code}:generation:{generation}")
            if not result.get("ok"): raise RuntimeError(f"service_process_start_failed:{code}")
            op=result["process_operation"]["process_operation_id"];entry={"service_code":code,"definition_digest":_definition_digest(spec),"dependencies":list(spec["dependencies"]),"port":port,"readiness_kind":spec["readiness"]["kind"],"process_operation_id":op,"process_state":result["process_operation"].get("process_state"),"readiness_state":"waiting","restart_count":0,"failure_code":""};row["services"].append(entry);row["action_executed"]=True;_save(row,runtime_root);started.append(entry)
            deadline=time.monotonic()+float(spec["readiness_timeout_seconds"]);ready=False
            while time.monotonic()<deadline:
                obs=monitor_candidate_process(op,runtime_root=runtime_root);state=(obs.get("process_operation") or {}).get("process_state");entry["process_state"]=state
                if _ready(port,spec["readiness"]):ready=True;break
                if state in {"completed","failed","cancelled","interrupted","uncertain"}:break
                time.sleep(.05)
            if not ready:
                entry["readiness_state"]="failed";entry["failure_code"]="readiness_not_reached";row["stack_state"]="failed";_save(row,runtime_root);raise RuntimeError(f"service_readiness_failed:{code}")
            entry["readiness_state"]="ready";row["stack_state"]="ready" if len(started)==len(order) else "starting";_save(row,runtime_root)
    except Exception as e:
        for entry in reversed(started):
            try:
                stop_candidate_process(str(entry["process_operation_id"]),active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
                obs=monitor_candidate_process(str(entry["process_operation_id"]),runtime_root=runtime_root);entry["process_state"]=(obs.get("process_operation") or {}).get("process_state")
            except Exception: entry["failure_code"] = entry.get("failure_code") or "cleanup_failed"
        row["cleanup_performed"]=bool(started);row["stack_state"]="failed";row["failure_code"]=str(e).split(':',1)[0];row["orphaned_service_count"]=sum(1 for x in started if x.get("process_state") not in {"completed","failed","cancelled","interrupted","uncertain"});_save(row,runtime_root)
        return {"ok":False,"status":"service_stack_start_failed","service_stack":_public(row),"action_executed":row["action_executed"],**SERVICE_DENIED_AUTHORITY}
    row["stack_state"]="ready";_save(row,runtime_root);return {"ok":True,"status":"service_stack_ready","service_stack":_public(row),"action_executed":True,**SERVICE_DENIED_AUTHORITY}


def inspect_service_stack(stack_id: str, *, runtime_root=None) -> dict[str, Any]:
    row=_sealed(_path(str(stack_id),runtime_root))
    if not row:return {"ok":False,"status":"service_stack_missing_or_invalid","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    for entry in row.get("services") or []:
        obs=monitor_candidate_process(str(entry.get("process_operation_id") or ""),runtime_root=runtime_root);entry["process_state"]=(obs.get("process_operation") or {}).get("process_state") or entry.get("process_state")
    _save(row,runtime_root);return {"ok":True,"status":"service_stack_observed","service_stack":_public(row),"action_executed":False,**SERVICE_DENIED_AUTHORITY}


def stop_service_stack(stack_id: str, *, active_grant: Mapping[str, Any], runtime_root=None, now_unix: int | None=None) -> dict[str, Any]:
    row=_sealed(_path(str(stack_id),runtime_root))
    if not row:return {"ok":False,"status":"service_stack_missing_or_invalid","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    workspace=_workspace(str(row.get("workspace_id") or ""),runtime_root);gok,reason=_grant_ok(workspace,active_grant,now_unix) if workspace else (False,"candidate_workspace_required")
    if not gok or str(active_grant.get("grant_digest") or "")!=str(row.get("grant_digest") or ""):return {"ok":False,"status":reason if not gok else "standing_grant_lineage_mismatch","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    for entry in reversed(row.get("services") or []):
        stop_candidate_process(str(entry.get("process_operation_id") or ""),active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
        obs=monitor_candidate_process(str(entry.get("process_operation_id") or ""),runtime_root=runtime_root);entry["process_state"]=(obs.get("process_operation") or {}).get("process_state")
        entry["readiness_state"]="stopped"
    row["cleanup_performed"]=True;row["stack_state"]="stopped";row["orphaned_service_count"]=sum(1 for x in row.get("services") or [] if x.get("process_state") not in {"completed","failed","cancelled","interrupted","uncertain"});_save(row,runtime_root)
    return {"ok":row["orphaned_service_count"]==0,"status":"service_stack_stopped","service_stack":_public(row),"action_executed":True,**SERVICE_DENIED_AUTHORITY}


def restart_service(stack_id: str, definition: Mapping[str, Any], *, active_grant: Mapping[str, Any], process_precondition_record_id: str, runtime_root=None, now_unix: int | None=None) -> dict[str, Any]:
    row=_sealed(_path(str(stack_id),runtime_root));spec=_definition(definition)
    if not row:return {"ok":False,"status":"service_stack_missing_or_invalid","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    entry=next((x for x in row.get("services") or [] if x.get("service_code")==spec["service_code"]),None)
    if not entry or entry.get("definition_digest")!=_definition_digest(spec):return {"ok":False,"status":"service_definition_lineage_mismatch","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    if not _pre(process_precondition_record_id,"shell",runtime_root) or process_precondition_record_id!=row.get("process_precondition_record_id"):return {"ok":False,"status":"satisfied_shell_precondition_required","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    workspace=_workspace(str(row.get("workspace_id") or ""),runtime_root);gok,reason=_grant_ok(workspace,active_grant,now_unix) if workspace else (False,"candidate_workspace_required")
    if not gok or active_grant.get("grant_digest")!=row.get("grant_digest"):return {"ok":False,"status":reason if not gok else "standing_grant_lineage_mismatch","action_executed":False,**SERVICE_DENIED_AUTHORITY}
    old=str(entry.get("process_operation_id") or "");stop_candidate_process(old,active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix);port=int(entry["port"]);count=int(entry.get("restart_count") or 0)+1
    started=start_candidate_process(str(row["workspace_id"]),_args(spec,port),active_grant=active_grant,precondition_record_id=process_precondition_record_id,cwd_relative=spec["cwd_relative"],environment={"EIDOLON_SERVICE_HOST":"127.0.0.1","EIDOLON_SERVICE_PORT":str(port)},timeout_seconds=spec["process_timeout_seconds"],runtime_root=runtime_root,now_unix=now_unix,invocation_discriminator=f"service:{stack_id}:{spec['service_code']}:generation:{count}")
    if not started.get("ok"):return {"ok":False,"status":"service_restart_start_failed","service_stack":_public(row),"action_executed":True,**SERVICE_DENIED_AUTHORITY}
    entry["process_operation_id"]=started["process_operation"]["process_operation_id"];entry["process_state"]=started["process_operation"].get("process_state");entry["restart_count"]=count;entry["readiness_state"]="waiting"
    deadline=time.monotonic()+float(spec["readiness_timeout_seconds"]);ready=False
    while time.monotonic()<deadline:
        obs=monitor_candidate_process(entry["process_operation_id"],runtime_root=runtime_root);entry["process_state"]=(obs.get("process_operation") or {}).get("process_state")
        if _ready(port,spec["readiness"]):ready=True;break
        if entry["process_state"] in {"completed","failed","cancelled","interrupted","uncertain"}:break
        time.sleep(.05)
    entry["readiness_state"]="ready" if ready else "failed";entry["failure_code"]="" if ready else "restart_readiness_not_reached";row["stack_state"]="ready" if ready else "failed";_save(row,runtime_root)
    if not ready:stop_candidate_process(entry["process_operation_id"],active_grant=active_grant,runtime_root=runtime_root,now_unix=now_unix)
    return {"ok":ready,"status":"service_restarted" if ready else "service_restart_failed","service_stack":_public(row),"action_executed":True,**SERVICE_DENIED_AUTHORITY}


def load_service_stack(stack_id: str, *, runtime_root=None) -> dict[str, Any]:
    row=_sealed(_path(str(stack_id),runtime_root));return _public(row) if row else {}


def process_service_orchestration_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show service stack","inspect service stack","show service orchestration"}:return {"active":False}
    sid=str((project_state or {}).get("service_stack_id") or "");row=load_service_stack(sid,runtime_root=runtime_root) if sid else {}
    return {"active":True,"ok":bool(row),"status":"service_stack_found" if row else "service_stack_missing","service_stack":row,"action_executed":False,**SERVICE_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","READINESS_KINDS","SERVICE_DENIED_AUTHORITY","start_service_stack","inspect_service_stack","restart_service","stop_service_stack","load_service_stack","process_service_orchestration_control"]
