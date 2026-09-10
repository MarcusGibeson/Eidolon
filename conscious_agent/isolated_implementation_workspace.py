from __future__ import annotations
"""Transactional materialization of validated generation into an external workspace.

v1201.0-v1201.2 creates no authority to modify the selected project. It copies the
approved bounded snapshot into external runtime storage, applies only validated
structured changes there, verifies every digest, and atomically publishes a
revision-bound workspace record. It does not execute commands or tests.
"""
import hashlib, os, shutil, tempfile
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from grounded_development_planning import load_grounded_plan
from structured_development_generation import _safe_relative

SCHEMA_VERSION='1'; CONTRACT_VERSION='v1201.2'
MAX_WORKSPACE_FILES=240; MAX_WORKSPACE_BYTES=4*1024*1024

def _record_path(pid:str, rev:int, runtime_root=None)->Path:
    return _store_root(runtime_root)/'workspaces'/pid/f'revision-{int(rev)}.json'

def _workspace_root(pid:str, rev:int, generation_digest:str, runtime_root=None)->Path:
    return _store_root(runtime_root)/'implementation_workspaces'/pid/f'revision-{int(rev)}-{generation_digest[:16]}'

def _file_digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def _verify_record(record:Mapping[str,Any], root:Path)->bool:
    supplied=str(record.get('workspace_digest') or '')
    if not supplied or supplied!=_digest({k:v for k,v in record.items() if k!='workspace_digest'}): return False
    if not root.is_dir() or root.is_symlink(): return False
    rows=record.get('files') or []
    for row in rows:
        try: path=root/_safe_relative(str(row.get('relative_path') or ''))
        except ValueError: return False
        if not path.is_file() or path.is_symlink() or _file_digest(path)!=row.get('content_digest'): return False
    return True

def materialize_or_resume_workspace(proposal_id:str,*,expected_revision:int,expected_revision_digest:str,expected_planning_digest:str,expected_generation_digest:str,runtime_root=None)->dict[str,Any]:
    with _proposal_lock(proposal_id,runtime_root):
        plan=load_grounded_plan(proposal_id,expected_revision,runtime_root=runtime_root)
        if not plan or plan.get('planning_digest')!=expected_planning_digest: return {'ok':False,'status':'stale_or_missing_plan'}
        if plan.get('proposal_revision_digest')!=expected_revision_digest: return {'ok':False,'status':'stale_proposal_revision'}
        generation_path=_store_root(runtime_root)/'generation'/proposal_id/f'revision-{int(expected_revision)}.json'
        generation=_read_json(generation_path)
        if not generation or generation.get('generation_digest')!=expected_generation_digest: return {'ok':False,'status':'stale_or_missing_generation'}
        if generation.get('generation_digest')!=_digest({k:v for k,v in generation.items() if k!='generation_digest'}): return {'ok':False,'status':'generation_record_invalid'}
        expected_bindings={'proposal_revision_digest':expected_revision_digest,'planning_digest':expected_planning_digest,'project_snapshot_digest':plan.get('project_snapshot_digest')}
        if any(generation.get(k)!=v for k,v in expected_bindings.items()): return {'ok':False,'status':'authority_binding_rejected'}
        recpath=_record_path(proposal_id,expected_revision,runtime_root); root=_workspace_root(proposal_id,expected_revision,expected_generation_digest,runtime_root)
        existing=_read_json(recpath)
        if existing:
            return ({**existing,'operation_status':'resumed'} if _verify_record(existing,root) else {'ok':False,'status':'workspace_record_invalid'})
        root.parent.mkdir(parents=True, exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix='.staging-', dir=str(root.parent)))
        try:
            # Copy only the exact inspected inventory from a selected project. The private path stays external.
            proposal=_read_json(_store_root(runtime_root)/'proposals'/f'{proposal_id}.json')
            target=dict(proposal.get('target') or {})
            if target.get('mode')=='selected_project':
                source=Path(str(target.get('private_path') or '')).expanduser().resolve(strict=True)
                if not source.is_dir() or source.is_symlink(): return {'ok':False,'status':'selected_project_unavailable'}
                for row in plan.get('inventory') or []:
                    rel=_safe_relative(str(row.get('relative_path') or '')); src=source/rel; dst=staging/rel
                    if not src.is_file() or src.is_symlink() or _file_digest(src)!=row.get('content_digest'): return {'ok':False,'status':'project_snapshot_changed'}
                    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
            for row in generation.get('files') or []:
                rel=_safe_relative(str(row.get('relative_path') or '')); dst=staging/rel; op=row.get('operation'); content=row.get('content','')
                if op=='delete':
                    if dst.exists(): dst.unlink()
                else:
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    tmp=dst.with_name(dst.name+'.tmp'); tmp.write_text(content,encoding='utf-8',newline=''); os.replace(tmp,dst)
                    if _file_digest(dst)!=row.get('content_digest'): return {'ok':False,'status':'materialized_digest_mismatch'}
            files=[]; total=0
            for path in sorted(staging.rglob('*')):
                if path.is_symlink(): return {'ok':False,'status':'workspace_symlink_rejected'}
                if not path.is_file(): continue
                rel=path.relative_to(staging).as_posix(); size=path.stat().st_size; total+=size
                files.append({'relative_path':rel,'relative_path_digest':hashlib.sha256(rel.encode()).hexdigest(),'content_digest':_file_digest(path),'size_bytes':size})
                if len(files)>MAX_WORKSPACE_FILES or total>MAX_WORKSPACE_BYTES: return {'ok':False,'status':'workspace_budget_exceeded'}
            if root.exists(): return {'ok':False,'status':'workspace_collision'}
            root.parent.mkdir(parents=True,exist_ok=True); os.replace(staging,root); staging=None
            record={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'ok':True,'status':'isolated_workspace_ready','proposal_id':proposal_id,'proposal_revision':int(expected_revision),'proposal_revision_digest':expected_revision_digest,'planning_digest':expected_planning_digest,'generation_digest':expected_generation_digest,'project_snapshot_digest':plan.get('project_snapshot_digest'),'approval_receipt_digest':plan.get('approval_receipt_digest'),'workspace_id':hashlib.sha256(str(root).encode()).hexdigest(),'workspace_path':str(root),'files':files,'file_count':len(files),'total_bytes':total,'selected_project_modified':False,'source_modified':False,'command_executed':False,'tests_executed':False,'release_authorized':False,'authority_granted':False}
            record['workspace_digest']=_digest(record); _atomic_json(recpath,record); return {**record,'operation_status':'created'}
        finally:
            if staging is not None: shutil.rmtree(staging,ignore_errors=True)

def public_workspace(record:Mapping[str,Any])->dict[str,Any]:
    return {'ok':bool(record.get('ok')),'status':record.get('status',''),'proposal_id':record.get('proposal_id',''),'proposal_revision':record.get('proposal_revision',0),'planning_digest':record.get('planning_digest',''),'generation_digest':record.get('generation_digest',''),'workspace_digest':record.get('workspace_digest',''),'workspace_id':record.get('workspace_id',''),'file_count':record.get('file_count',0),'total_bytes':record.get('total_bytes',0),'path_digests':[x.get('relative_path_digest','') for x in record.get('files') or []],'content_digests':[x.get('content_digest','') for x in record.get('files') or []],'workspace_path_exposed':False,'private_content_exposed':False,'selected_project_modified':False,'source_modified':False,'command_executed':False,'tests_executed':False,'release_authorized':False,'authority_granted':False}
