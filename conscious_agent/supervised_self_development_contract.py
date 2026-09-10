from __future__ import annotations
"""Operator-governed self-development contract for v1489 Bundle 16."""
from pathlib import Path
from typing import Any,Iterable,Mapping
import hashlib,json,os,shutil

SOURCE_ONLY_IGNORED_PARTS=frozenset({
    'data','.git','.hg','.svn','.venv','venv','__pycache__','.pytest_cache',
    '.mypy_cache','.ruff_cache','reports','retired_evidence_quarantine',
    'install_backups',
})
SOURCE_ONLY_IGNORED_PATTERNS=tuple(sorted(SOURCE_ONLY_IGNORED_PARTS|{'*.pyc','*.pyo','*.log','*.zip'}))

def _digest_file(p:Path)->str:
    digest=hashlib.sha256()
    with p.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def read_only_inventory(root:Path|str,limit:int=500)->dict[str,Any]:
    r=Path(root).resolve(); rows=[]
    for p in sorted(r.rglob('*.py')):
        relative=p.relative_to(r)
        if any(x in relative.parts for x in ('data','__pycache__','.venv','.git')):continue
        rows.append({'path':relative.as_posix(),'size':p.stat().st_size,'digest':_digest_file(p)})
        if len(rows)>=limit:break
    return {'file_count':len(rows),'files':rows,'source_mutated':False,'content_free':True}

def improvement_opportunity(inventory:Mapping[str,Any])->dict[str,Any]:
    files=list(inventory.get('files') or [])
    target=next((r for r in files if str(r.get('path','')).endswith('_contract.py')),files[0] if files else {})
    return {'target_path':str(target.get('path') or ''),'evidence_digest':str(target.get('digest') or '')[:24],'opportunity_class':'bounded_testability_improvement' if target else 'none','evidence_backed':bool(target),'source_mutated':False,'content_free':True}

def propose_self_change(opportunity:Mapping[str,Any])->dict[str,Any]:
    return {'target_path':str(opportunity.get('target_path') or ''),'steps':['inspect target','apply one bounded change in isolated workspace','run focused verification','prepare review candidate'],'reversible':True,'modification_authorized':False,'installation_authorized':False,'promotion_authorized':False,'content_free':True}

def create_isolated_workspace(source_root:Path|str,workspace_root:Path|str,*,authorized:bool)->dict[str,Any]:
    src=Path(source_root).resolve(); dst=Path(workspace_root).resolve()
    if not authorized:return {'created':False,'reason':'operator_authorization_required','content_free':True}
    if dst.exists():shutil.rmtree(dst)
    shutil.copytree(src,dst,ignore=shutil.ignore_patterns(*SOURCE_ONLY_IGNORED_PATTERNS))
    return {'created':True,'workspace_digest':hashlib.sha256(str(dst).encode()).hexdigest()[:24],'authoritative_source_modified':False,'content_free':True}

def apply_bounded_text_change(workspace_root:Path|str,relative_path:str,old:str,new:str,*,authorized:bool)->dict[str,Any]:
    if not authorized:return {'changed':False,'reason':'operator_authorization_required','content_free':True}
    root=Path(workspace_root).resolve(); p=(root/relative_path).resolve()
    if root not in p.parents:raise ValueError('path escapes workspace')
    s=p.read_text(); count=s.count(old)
    if count!=1:return {'changed':False,'reason':'bounded_match_required','match_count':count,'content_free':True}
    p.write_text(s.replace(old,new,1));return {'changed':True,'changed_file':relative_path,'match_count':1,'content_free':True}

def critique_result(*,focused_pass:bool,regression_pass:bool,known_limitations:Iterable[str]=())->dict[str,Any]:
    limits=[str(x)[:120] for x in known_limitations]
    return {'acceptable_for_review':bool(focused_pass and regression_pass),'focused_pass':bool(focused_pass),'regression_pass':bool(regression_pass),'known_limitation_count':len(limits),'self_install_allowed':False,'content_free':True}

def candidate_evidence(*,changed_files:Iterable[str],rollback_available:bool)->dict[str,Any]:
    rows=sorted(set(str(x) for x in changed_files)); return {'changed_files':rows,'changed_file_count':len(rows),'rollback_available':bool(rollback_available),'self_install_allowed':False,'operator_review_required':True,'content_free':True}

def source_manifest(root:Path|str)->dict[str,str]:
    r=Path(root).resolve();out={}
    for current,dirs,files in os.walk(r,topdown=True,followlinks=False):
        dirs[:]=sorted(name for name in dirs if name.casefold() not in SOURCE_ONLY_IGNORED_PARTS)
        parent=Path(current)
        for name in sorted(files):
            p=parent/name
            if p.suffix.casefold() in {'.pyc','.pyo','.log','.zip'}:continue
            out[p.relative_to(r).as_posix()]=_digest_file(p)
    return out

def concurrent_operator_changes(baseline:Mapping[str,str],current:Mapping[str,str])->dict[str,Any]:
    changed=sorted(k for k in set(baseline)|set(current) if baseline.get(k)!=current.get(k))
    return {'concurrent_change_detected':bool(changed),'changed_file_count':len(changed),'overwrite_allowed':False,'must_reconcile_before_apply':bool(changed),'content_free':True}
