from __future__ import annotations
"""v1335 typed, candidate-workspace Git operations.

No generic Git command surface exists here. The module inspects bounded history,
stages only changes proven owned by sealed v1334 file-operation receipts, and
creates a commit only from an exact sealed staging receipt. Hooks, signing,
fsmonitor, external filters, shell evaluation, network operations, reset, clean,
restore, checkout, rebase, merge, push, and other destructive/expansive Git
behaviors are intentionally outside this contract.
"""
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions
from workspace_isolation import _record_path as _isolation_record_path
from structured_file_operations import _operation_path as _file_operation_path

CONTRACT_VERSION = "v1335.8"
TYPED_GIT_OPERATIONS = ("status", "history", "stage_owned", "commit_owned")
MAX_HISTORY = 64
GIT_TIMEOUT_SECONDS = 20
GIT_OPERATION_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "tool_execution_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
    "network_authorized": False,
}


def _git_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_git_operations"


def _operation_path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"gitop_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_git_operation_id")
    return _git_root(runtime_root) / "records" / f"{operation_id}.json"


def _load_sealed(path: Path) -> dict[str, Any]:
    row = _read_json(path)
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _load_workspace(workspace_id: str, runtime_root=None) -> dict[str, Any]:
    row = _load_sealed(_isolation_record_path(workspace_id, runtime_root))
    if not row or row.get("cleaned") or not row.get("workspace_created"):
        return {}
    if row.get("mode") not in {"git_worktree", "git_branch_worktree"}:
        return {}
    root = Path(str(row.get("candidate_private_path") or ""))
    if not root.is_dir():
        return {}
    return row


def _load_file_operation(operation_id: str, runtime_root=None) -> dict[str, Any]:
    return _load_sealed(_file_operation_path(operation_id, runtime_root))


def _load_git_operation(operation_id: str, runtime_root=None) -> dict[str, Any]:
    return _load_sealed(_operation_path(operation_id, runtime_root))


def _validate_grant(workspace: Mapping[str, Any], grant: Mapping[str, Any], action_class: str, now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(workspace.get("source_workspace_digest") or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, action_class, now_unix=now_unix):
        return False, f"active_{action_class}_grant_required"
    classes = set((grant.get("profile_snapshot") or {}).get("command_classes") or [])
    if not ({"git", "git_worktree"} & classes):
        return False, "typed_git_command_class_required"
    return True, ""


def _validate_precondition(record_id: str, runtime_root=None) -> tuple[bool, dict[str, Any]]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    return bool(row and row.get("preconditions_satisfied") is True and row.get("tool_code") == "git" and row.get("tool_invoked") is False), row


def _git_binary(git_executable: str | None) -> str:
    git = git_executable or shutil.which("git")
    if not git:
        raise RuntimeError("git_unavailable")
    return str(git)


def _safe_git_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PAGER": "cat",
        "GIT_EDITOR": "true",
        "GIT_SEQUENCE_EDITOR": "true",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    })
    return env


def _git_run(git: str, candidate: Path, args: Sequence[str], *, mutating: bool = False, runtime_root=None) -> subprocess.CompletedProcess[bytes]:
    empty_hooks = _git_root(runtime_root) / "empty_hooks"
    empty_hooks.mkdir(parents=True, exist_ok=True)
    prefix = [git, "-c", f"core.hooksPath={empty_hooks}", "-c", "core.fsmonitor=false", "-c", "commit.gpgSign=false", "-c", "tag.gpgSign=false", "-C", str(candidate)]
    return subprocess.run(
        [*prefix, *args], cwd=str(candidate), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        timeout=GIT_TIMEOUT_SECONDS, env=_safe_git_env(),
    )


def _external_filters_configured(git: str, candidate: Path, runtime_root=None) -> bool:
    result = _git_run(git, candidate, ["config", "--local", "--get-regexp", r"^filter\..*\.(clean|process|smudge)$"], runtime_root=runtime_root)
    # git config returns 1 when no keys matched.
    return result.returncode == 0 and bool(result.stdout.strip())


def _head(git: str, candidate: Path, runtime_root=None) -> str:
    result = _git_run(git, candidate, ["rev-parse", "HEAD"], runtime_root=runtime_root)
    if result.returncode:
        raise RuntimeError("git_head_unavailable")
    value = result.stdout.decode("ascii", errors="strict").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise RuntimeError("git_head_invalid")
    return value


def _status_rows(git: str, candidate: Path, runtime_root=None) -> list[dict[str, Any]]:
    result = _git_run(git, candidate, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], runtime_root=runtime_root)
    if result.returncode:
        raise RuntimeError("git_status_failed")
    chunks = result.stdout.split(b"\0")
    rows: list[dict[str, Any]] = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        i += 1
        if not chunk:
            continue
        if len(chunk) < 4 or chunk[2:3] != b" ":
            raise RuntimeError("git_status_format_unexpected")
        x = chr(chunk[0]); y = chr(chunk[1])
        try:
            path = chunk[3:].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise RuntimeError("git_status_path_encoding_unsupported") from exc
        paths = [path]
        if x in {"R", "C"} or y in {"R", "C"}:
            if i >= len(chunks) or not chunks[i]:
                raise RuntimeError("git_status_rename_format_unexpected")
            try:
                paths.append(chunks[i].decode("utf-8", errors="strict"))
            except UnicodeDecodeError as exc:
                raise RuntimeError("git_status_path_encoding_unsupported") from exc
            i += 1
        for rel in paths:
            rows.append({
                "x": x, "y": y, "relative_path": rel,
                "relative_path_digest": hashlib.sha256(rel.replace("\\", "/").encode("utf-8")).hexdigest(),
                "staged": x not in {" ", "?"},
                "unstaged": y != " " or (x == "?" and y == "?"),
            })
    return rows


def _public_status(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    digests = sorted({str(row.get("relative_path_digest") or "") for row in rows if row.get("relative_path_digest")})
    staged = sorted({str(row.get("relative_path_digest") or "") for row in rows if row.get("staged")})
    unstaged = sorted({str(row.get("relative_path_digest") or "") for row in rows if row.get("unstaged")})
    return {
        "changed_path_digests": digests,
        "changed_path_count": len(digests),
        "staged_path_digests": staged,
        "staged_path_count": len(staged),
        "unstaged_path_digests": unstaged,
        "unstaged_path_count": len(unstaged),
        "status_digest": digest([(row.get("x"), row.get("y"), row.get("relative_path_digest")) for row in rows]),
    }


def _operation_base(kind: str, workspace: Mapping[str, Any], pre: Mapping[str, Any], grant: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation_kind": kind,
        "workspace_id": workspace.get("workspace_id"),
        "source_workspace_digest": workspace.get("source_workspace_digest"),
        "grant_digest": grant.get("grant_digest"),
        "precondition_record_id": pre.get("precondition_record_id"),
        "precondition_digest": pre.get("record_digest"),
        "repository_metadata_modified": kind in {"stage_owned", "commit_owned"},
        "selected_source_content_modified": False,
        "candidate_content_modified": False,
        "network_contacted": False,
        "shell_used": False,
        "hooks_enabled": False,
        "signing_enabled": False,
        "workspace_operation_authorized": True,
        **GIT_OPERATION_DENIED_AUTHORITY,
    }


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row["record_digest"] = digest(row)
    _atomic_json(_operation_path(str(row["operation_id"]), runtime_root), row)
    return row


def inspect_git_status(
    workspace_id: str, *, active_grant: Mapping[str, Any], precondition_record_id: str,
    runtime_root=None, now_unix: int | None = None, git_executable: str | None = None,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "git_candidate_workspace_required", **GIT_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "command", now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, **GIT_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_precondition(precondition_record_id, runtime_root)
    if not pre_ok:
        return {"ok": False, "status": "sealed_satisfied_git_preconditions_required", **GIT_OPERATION_DENIED_AUTHORITY}
    try:
        git = _git_binary(git_executable);head = _head(git, Path(workspace["candidate_private_path"]), runtime_root);rows = _status_rows(git, Path(workspace["candidate_private_path"]), runtime_root)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "status": str(exc), **GIT_OPERATION_DENIED_AUTHORITY}
    summary = _public_status(rows)
    operation_id = "gitop_" + digest({"kind":"status","workspace":workspace_id,"head":head,"status":summary["status_digest"]})[:24]
    existing = _load_git_operation(operation_id, runtime_root)
    if existing:
        return {"ok": True, "status": "git_status_restored", "git_operation": public_git_operation(existing), "operation_executed_this_request": False, **GIT_OPERATION_DENIED_AUTHORITY}
    row = _operation_base("status", workspace, pre, active_grant);row.update({"operation_id":operation_id,"status":"git_status_inspected","head_commit":head,"head_commit_digest":hashlib.sha256(head.encode()).hexdigest(),**summary,"action_executed":True})
    _save(row,runtime_root)
    return {"ok":True,"status":"git_status_inspected","git_operation":public_git_operation(row),"operation_executed_this_request":True,**GIT_OPERATION_DENIED_AUTHORITY}


def inspect_git_history(
    workspace_id: str, *, active_grant: Mapping[str, Any], precondition_record_id: str,
    limit: int = 12, runtime_root=None, now_unix: int | None = None,
    git_executable: str | None = None, include_subjects: bool = False,
) -> dict[str, Any]:
    workspace = _load_workspace(workspace_id, runtime_root)
    if not workspace:
        return {"ok": False, "status": "git_candidate_workspace_required", **GIT_OPERATION_DENIED_AUTHORITY}
    grant_ok, reason = _validate_grant(workspace, active_grant, "command", now_unix)
    if not grant_ok:return {"ok":False,"status":reason,**GIT_OPERATION_DENIED_AUTHORITY}
    pre_ok, pre = _validate_precondition(precondition_record_id, runtime_root)
    if not pre_ok:return {"ok":False,"status":"sealed_satisfied_git_preconditions_required",**GIT_OPERATION_DENIED_AUTHORITY}
    count=max(1,min(MAX_HISTORY,int(limit)))
    try:
        git=_git_binary(git_executable);candidate=Path(workspace["candidate_private_path"]);head=_head(git,candidate,runtime_root)
        result=_git_run(git,candidate,["log",f"-{count}","--format=%H%x1f%P%x1f%ct%x1f%s%x1e"],runtime_root=runtime_root)
        if result.returncode:raise RuntimeError("git_history_failed")
        history=[];subjects=[]
        for raw in result.stdout.split(b"\x1e"):
            raw=raw.strip(b"\r\n")
            if not raw:continue
            parts=raw.decode("utf-8",errors="replace").split("\x1f",3)
            if len(parts)!=4:raise RuntimeError("git_history_format_unexpected")
            commit,parents,ts,subject=parts
            history.append({"commit_id_digest":hashlib.sha256(commit.encode()).hexdigest(),"parent_count":len([x for x in parents.split() if x]),"timestamp_unix":int(ts),"subject_digest":hashlib.sha256(subject.encode()).hexdigest()})
            subjects.append(subject)
    except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as exc:return {"ok":False,"status":str(exc),**GIT_OPERATION_DENIED_AUTHORITY}
    operation_id="gitop_"+digest({"kind":"history","workspace":workspace_id,"head":head,"limit":count,"history":history})[:24]
    existing=_load_git_operation(operation_id,runtime_root)
    if not existing:
        row=_operation_base("history",workspace,pre,active_grant);row.update({"operation_id":operation_id,"status":"git_history_inspected","head_commit":head,"head_commit_digest":hashlib.sha256(head.encode()).hexdigest(),"history":history,"history_count":len(history),"raw_subjects_persisted":False,"action_executed":True});_save(row,runtime_root)
    else:row=existing
    out={"ok":True,"status":"git_history_inspected","git_operation":public_git_operation(row),"operation_executed_this_request":not bool(existing),**GIT_OPERATION_DENIED_AUTHORITY}
    if include_subjects:out["history_subjects"]=subjects;out["subjects_exposed_to_internal_caller"]=True
    else:out["subjects_exposed_to_internal_caller"]=False
    return out


def _owned_changes(operation_ids: Sequence[str], workspace_id: str, runtime_root=None) -> tuple[bool, dict[str, Any]]:
    if not operation_ids or len(operation_ids)>128:return False,{"status":"owned_file_operation_ids_required"}
    allowed:set[str]=set();expected_after:dict[str,str]={};expected_absent:set[str]=set();loaded=[]
    for operation_id in sorted({str(x) for x in operation_ids if str(x)}):
        row=_load_file_operation(operation_id,runtime_root)
        if not row or row.get("workspace_id")!=workspace_id or row.get("operation_kind") not in {"patch","move","generated_update"}:
            return False,{"status":"owned_file_operation_missing_invalid_or_wrong_workspace"}
        rel=str(row.get("relative_path_digest") or "");dst=str(row.get("destination_path_digest") or "")
        if rel:allowed.add(rel)
        if row.get("operation_kind")=="move":
            expected_absent.add(rel)
            if dst:allowed.add(dst);expected_after[dst]=str(row.get("after_digest") or "")
        else:expected_after[rel]=str(row.get("after_digest") or "")
        loaded.append(row)
    return True,{"operation_ids":[row["operation_id"] for row in loaded],"allowed_path_digests":allowed,"expected_after":expected_after,"expected_absent":expected_absent}


def _verify_owned_status(candidate: Path, rows: Sequence[Mapping[str, Any]], owned: Mapping[str, Any]) -> tuple[bool,str,list[str],list[str]]:
    allowed=set(owned["allowed_path_digests"]);expected_after=dict(owned["expected_after"]);expected_absent=set(owned["expected_absent"])
    owned_changed=[];unowned_staged=[]
    for row in rows:
        dg=str(row.get("relative_path_digest") or "");rel=str(row.get("relative_path") or "")
        if row.get("staged") and dg not in allowed:unowned_staged.append(dg)
        if dg not in allowed:continue
        owned_changed.append(rel)
        path=candidate/Path(*rel.replace("\\","/").split("/"))
        if dg in expected_absent:
            if path.exists():return False,"owned_deleted_path_reappeared",[],unowned_staged
        elif dg in expected_after:
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected_after[dg]:return False,"owned_change_drift_detected",[],unowned_staged
    if unowned_staged:return False,"unowned_staged_changes_present",owned_changed,unowned_staged
    return True,"",sorted(set(owned_changed)),[]


def stage_owned_changes(
    workspace_id: str, *, owned_file_operation_ids: Sequence[str], active_grant: Mapping[str, Any],
    precondition_record_id: str, runtime_root=None, now_unix: int | None = None,
    git_executable: str | None = None,
) -> dict[str, Any]:
    workspace=_load_workspace(workspace_id,runtime_root)
    if not workspace:return {"ok":False,"status":"git_candidate_workspace_required",**GIT_OPERATION_DENIED_AUTHORITY}
    grant_ok,reason=_validate_grant(workspace,active_grant,"command",now_unix)
    if not grant_ok:return {"ok":False,"status":reason,**GIT_OPERATION_DENIED_AUTHORITY}
    pre_ok,pre=_validate_precondition(precondition_record_id,runtime_root)
    if not pre_ok:return {"ok":False,"status":"sealed_satisfied_git_preconditions_required",**GIT_OPERATION_DENIED_AUTHORITY}
    owned_ok,owned=_owned_changes(owned_file_operation_ids,workspace_id,runtime_root)
    if not owned_ok:return {"ok":False,"status":owned["status"],**GIT_OPERATION_DENIED_AUTHORITY}
    candidate=Path(workspace["candidate_private_path"])
    try:
        git=_git_binary(git_executable);head=_head(git,candidate,runtime_root)
        operation_id="gitop_"+digest({"kind":"stage_owned","workspace":workspace_id,"head":head,"owned":owned["operation_ids"]})[:24]
        existing=_load_git_operation(operation_id,runtime_root)
        if existing:
            current=_public_status(_status_rows(git,candidate,runtime_root))
            if sorted(current["staged_path_digests"])==sorted(existing.get("staged_path_digests") or []):
                return {"ok":True,"status":"owned_git_stage_restored","git_operation":public_git_operation(existing),"operation_executed_this_request":False,**GIT_OPERATION_DENIED_AUTHORITY}
            return {"ok":False,"status":"prior_git_stage_conflicts_with_index",**GIT_OPERATION_DENIED_AUTHORITY}
        if _external_filters_configured(git,candidate,runtime_root):raise RuntimeError("external_git_filters_block_staging")
        before_rows=_status_rows(git,candidate,runtime_root);valid,reason,owned_paths,_=_verify_owned_status(candidate,before_rows,owned)
        if not valid:raise RuntimeError(reason)
        if not owned_paths:raise RuntimeError("no_owned_changes_to_stage")
        result=_git_run(git,candidate,["add","-A","--",*owned_paths],mutating=True,runtime_root=runtime_root)
        if result.returncode:raise RuntimeError("git_stage_owned_failed")
        after_rows=_status_rows(git,candidate,runtime_root);valid,reason,_,_=_verify_owned_status(candidate,after_rows,owned)
        if not valid:raise RuntimeError(reason)
        after=_public_status(after_rows);allowed=set(owned["allowed_path_digests"])
        if not after["staged_path_digests"] or any(x not in allowed for x in after["staged_path_digests"]):raise RuntimeError("git_staged_scope_mismatch")
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:return {"ok":False,"status":str(exc),**GIT_OPERATION_DENIED_AUTHORITY}
    row=_operation_base("stage_owned",workspace,pre,active_grant);row.update({"operation_id":operation_id,"status":"owned_changes_staged","head_commit":head,"head_commit_digest":hashlib.sha256(head.encode()).hexdigest(),"owned_file_operation_ids":owned["operation_ids"],"owned_file_operation_digest":digest(owned["operation_ids"]),"staged_path_digests":after["staged_path_digests"],"staged_path_count":after["staged_path_count"],"unstaged_path_digests":after["unstaged_path_digests"],"unstaged_path_count":after["unstaged_path_count"],"action_executed":True});_save(row,runtime_root)
    return {"ok":True,"status":"owned_changes_staged","git_operation":public_git_operation(row),"operation_executed_this_request":True,**GIT_OPERATION_DENIED_AUTHORITY}


def _validate_commit_message(message: str) -> str:
    value=str(message or "").strip()
    if len(value)<3 or len(value)>120 or "\n" in value or "\r" in value or "\x00" in value or any(ord(c)<32 and c not in "\t" for c in value):
        raise ValueError("coherent_single_subject_commit_message_required")
    return value


def commit_owned_changes(
    workspace_id: str, *, stage_operation_id: str, commit_message: str,
    active_grant: Mapping[str, Any], precondition_record_id: str,
    runtime_root=None, now_unix: int | None = None, git_executable: str | None = None,
) -> dict[str, Any]:
    workspace=_load_workspace(workspace_id,runtime_root)
    if not workspace:return {"ok":False,"status":"git_candidate_workspace_required",**GIT_OPERATION_DENIED_AUTHORITY}
    if workspace.get("mode")!="git_branch_worktree":return {"ok":False,"status":"owned_branch_worktree_required_for_commit",**GIT_OPERATION_DENIED_AUTHORITY}
    grant_ok,reason=_validate_grant(workspace,active_grant,"git_commit",now_unix)
    if not grant_ok:return {"ok":False,"status":reason,**GIT_OPERATION_DENIED_AUTHORITY}
    pre_ok,pre=_validate_precondition(precondition_record_id,runtime_root)
    if not pre_ok:return {"ok":False,"status":"sealed_satisfied_git_preconditions_required",**GIT_OPERATION_DENIED_AUTHORITY}
    stage=_load_git_operation(stage_operation_id,runtime_root)
    if not stage or stage.get("operation_kind")!="stage_owned" or stage.get("workspace_id")!=workspace_id:return {"ok":False,"status":"sealed_owned_stage_receipt_required",**GIT_OPERATION_DENIED_AUTHORITY}
    try:message=_validate_commit_message(commit_message)
    except ValueError as exc:return {"ok":False,"status":str(exc),**GIT_OPERATION_DENIED_AUTHORITY}
    message_digest=hashlib.sha256(message.encode()).hexdigest();operation_id="gitop_"+digest({"kind":"commit_owned","workspace":workspace_id,"stage":stage_operation_id,"message":message_digest})[:24]
    candidate=Path(workspace["candidate_private_path"])
    try:
        git=_git_binary(git_executable);existing=_load_git_operation(operation_id,runtime_root)
        if existing:
            if _head(git,candidate,runtime_root)==existing.get("after_head_commit"):
                return {"ok":True,"status":"owned_git_commit_restored","git_operation":public_git_operation(existing),"operation_executed_this_request":False,**GIT_OPERATION_DENIED_AUTHORITY}
            return {"ok":False,"status":"prior_git_commit_conflicts_with_head",**GIT_OPERATION_DENIED_AUTHORITY}
        before_head=_head(git,candidate,runtime_root)
        if before_head!=stage.get("head_commit"):raise RuntimeError("git_head_changed_since_stage")
        status=_public_status(_status_rows(git,candidate,runtime_root));expected=sorted(stage.get("staged_path_digests") or [])
        if not expected or sorted(status["staged_path_digests"])!=expected:raise RuntimeError("git_index_changed_since_stage")
        if _external_filters_configured(git,candidate,runtime_root):raise RuntimeError("external_git_filters_block_commit")
        result=_git_run(git,candidate,["commit","--no-verify","--no-gpg-sign","-m",message],mutating=True,runtime_root=runtime_root)
        if result.returncode:raise RuntimeError("git_commit_owned_failed")
        after_head=_head(git,candidate,runtime_root)
        if after_head==before_head:raise RuntimeError("git_commit_did_not_advance_head")
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:return {"ok":False,"status":str(exc),**GIT_OPERATION_DENIED_AUTHORITY}
    row=_operation_base("commit_owned",workspace,pre,active_grant);row.update({"operation_id":operation_id,"status":"owned_changes_committed","stage_operation_id":stage_operation_id,"owned_file_operation_digest":stage.get("owned_file_operation_digest"),"commit_message_digest":message_digest,"before_head_commit":before_head,"before_head_commit_digest":hashlib.sha256(before_head.encode()).hexdigest(),"after_head_commit":after_head,"after_head_commit_digest":hashlib.sha256(after_head.encode()).hexdigest(),"staged_path_digests":expected,"staged_path_count":len(expected),"raw_commit_message_persisted":False,"action_executed":True});_save(row,runtime_root)
    return {"ok":True,"status":"owned_changes_committed","git_operation":public_git_operation(row),"operation_executed_this_request":True,**GIT_OPERATION_DENIED_AUTHORITY}


def public_git_operation(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version":CONTRACT_VERSION,"operation_id":row.get("operation_id"),"operation_kind":row.get("operation_kind"),"status":row.get("status"),"workspace_id":row.get("workspace_id"),
        "head_commit_digest":row.get("head_commit_digest"),"before_head_commit_digest":row.get("before_head_commit_digest"),"after_head_commit_digest":row.get("after_head_commit_digest"),
        "changed_path_count":int(row.get("changed_path_count") or 0),"changed_path_digests":list(row.get("changed_path_digests") or []),"staged_path_count":int(row.get("staged_path_count") or 0),"staged_path_digests":list(row.get("staged_path_digests") or []),"unstaged_path_count":int(row.get("unstaged_path_count") or 0),"unstaged_path_digests":list(row.get("unstaged_path_digests") or []),
        "history_count":int(row.get("history_count") or 0),"history":[dict(x) for x in row.get("history") or []],"owned_file_operation_digest":row.get("owned_file_operation_digest"),"stage_operation_id":row.get("stage_operation_id"),"commit_message_digest":row.get("commit_message_digest"),
        "repository_metadata_modified":bool(row.get("repository_metadata_modified")),"selected_source_content_modified":False,"candidate_content_modified":False,"network_contacted":False,"shell_used":False,"hooks_enabled":False,"signing_enabled":False,"raw_paths_exposed":False,"raw_commit_message_exposed":False,"raw_commit_message_persisted":False,"workspace_operation_authorized":bool(row.get("workspace_operation_authorized")),"action_executed":bool(row.get("action_executed")),**GIT_OPERATION_DENIED_AUTHORITY,
    }


def inspect_git_operation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row=_load_git_operation(operation_id,runtime_root)
    if not row:return {"ok":False,"status":"git_operation_missing_or_invalid",**GIT_OPERATION_DENIED_AUTHORITY}
    return {"ok":True,"status":"git_operation_inspected","git_operation":public_git_operation(row),"operation_executed_this_request":False,**GIT_OPERATION_DENIED_AUTHORITY}


def process_git_operations_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show git operation","inspect git operation","show candidate git operation"}:return {"active":False}
    operation_id=str((project_state or {}).get("git_operation_id") or "")
    if not operation_id:return {"active":True,"ok":False,"status":"git_operation_id_required","operation_executed_this_request":False,**GIT_OPERATION_DENIED_AUTHORITY}
    return {"active":True,**inspect_git_operation(operation_id,runtime_root=runtime_root)}


__all__=["CONTRACT_VERSION","TYPED_GIT_OPERATIONS","GIT_OPERATION_DENIED_AUTHORITY","inspect_git_status","inspect_git_history","stage_owned_changes","commit_owned_changes","public_git_operation","inspect_git_operation","process_git_operations_control"]
