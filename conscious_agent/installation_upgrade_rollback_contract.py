from __future__ import annotations
"""Preview-only installation/upgrade/rollback contract for v1489 Bundle 19."""
from pathlib import Path
from typing import Any,Iterable,Mapping
import hashlib,json,shutil,zipfile,tempfile

PRIVATE_NAMES={'data','projects.json','.git','.venv','__pycache__'}

def tree_digest(root:Path|str)->str:
    r=Path(root).resolve();h=hashlib.sha256()
    for p in sorted(r.rglob('*')):
        if p.is_file():h.update(p.relative_to(r).as_posix().encode()+b'\0'+hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def upgrade_boundary(*,authoritative_digest:str,candidate_digest:str)->dict[str,Any]:
    return {'authoritative_digest':str(authoritative_digest),'candidate_digest':str(candidate_digest),'same_source':str(authoritative_digest)==str(candidate_digest),'candidate_authoritative':False,'operator_approval_required':True,'content_free':True}

def source_only_archive_audit(path:Path|str)->dict[str,Any]:
    findings=[]; roots=set()
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            parts=Path(name).parts
            if parts:roots.add(parts[0])
            low={p.lower() for p in parts}
            if any(n.lower() in low for n in PRIVATE_NAMES) or name.endswith(('.pyc','.pyo','.log')):findings.append(name)
    return {'ok':not findings and len(roots)==1,'root_count':len(roots),'forbidden_count':len(findings),'content_free':True}

def private_runtime_preservation(runtime_root:Path|str)->dict[str,Any]:
    r=Path(runtime_root).resolve(); classes={k:(r/k).exists() for k in ('settings','conversations','memories','projects','approvals')}
    return {'preservation_targets':classes,'target_count':sum(classes.values()),'source_upgrade_may_delete_private_data':False,'content_free':True}

def schema_compatibility(*,current:int,candidate_min:int,candidate_max:int)->dict[str,Any]:
    ok=int(candidate_min)<=int(current)<=int(candidate_max)
    return {'compatible':ok,'current_schema':int(current),'candidate_min':int(candidate_min),'candidate_max':int(candidate_max),'startup_allowed':ok,'migration_required':not ok,'content_free':True}

def migration_preview(*,current:int,target:int)->dict[str,Any]:
    return {'from_schema':int(current),'to_schema':int(target),'steps':abs(int(target)-int(current)),'preview_only':True,'applied':False,'operator_approval_required':True,'content_free':True}

def rollback_preview(*,source_backup_available:bool,private_data_compatible:bool)->dict[str,Any]:
    return {'rollback_possible':bool(source_backup_available),'restore_source':bool(source_backup_available),'preserve_private_data':bool(private_data_compatible),'apply_now':False,'operator_approval_required':True,'content_free':True}

def locate_entrypoints(root:Path|str)->dict[str,Any]:
    r=Path(root).resolve(); candidates=['Eidolon.bat','run_eidolon.bat','start_eidolon.py','conscious_agent/main.py','conscious_agent/desktop_shell.py']; found=[p for p in candidates if (r/p).exists()]
    return {'entrypoints':found,'count':len(found),'content_free':True}

def installation_coherence(*,expected_root_name:str,actual_root:Path|str,expected_manifest:str,actual_manifest:str)->dict[str,Any]:
    r=Path(actual_root).resolve(); wrong_root=r.name!=str(expected_root_name); mixed=str(expected_manifest)!=str(actual_manifest)
    return {'wrong_root':wrong_root,'mixed_or_partial_version':mixed,'coherent':not wrong_root and not mixed,'automatic_repair_allowed':False,'content_free':True}

def simulate_upgrade_rollback(authoritative:Path|str,candidate:Path|str,runtime:Path|str,workspace:Path|str)->dict[str,Any]:
    auth=Path(authoritative).resolve();cand=Path(candidate).resolve();run=Path(runtime).resolve();work=Path(workspace).resolve()
    before_private=tree_digest(run) if run.exists() else ''
    if work.exists():shutil.rmtree(work)
    shutil.copytree(cand,work)
    upgraded=tree_digest(work)==tree_digest(cand)
    shutil.rmtree(work);shutil.copytree(auth,work)
    rolled=tree_digest(work)==tree_digest(auth)
    after_private=tree_digest(run) if run.exists() else ''
    return {'fresh_install_simulated':True,'upgrade_candidate_matches':upgraded,'restart_source_available':work.exists(),'rollback_matches_authoritative':rolled,'private_runtime_unchanged':before_private==after_private,'live_install_modified':False,'content_free':True}
