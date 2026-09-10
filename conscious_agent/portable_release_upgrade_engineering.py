from __future__ import annotations
"""Era 2 / Arc 8 portable release and upgrade engineering.

This module validates source-only candidate coherence and exercises upgrades only
inside explicitly supplied disposable simulation roots.  It never targets an
installed Eidolon tree and grants no installation, promotion, or certification
authority.
"""
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
import hashlib
import json
import os
import shutil
import tempfile

from project_evidence_store import DENIED_AUTHORITY, atomic_json, digest, evidence_root, read_json, seal, valid, iter_source_files

CONTRACT_VERSION = "v1699.9"
FORBIDDEN_PARTS = {"data", "runtime", "logs", "cache", "caches", "__pycache__", ".git", ".venv", "venv", "node_modules", "install_backups", "proposal_workspaces", "provider_payloads"}
FORBIDDEN_NAMES = {"projects.json", ".env", "credentials.json", "secrets.json"}


def _candidate_path(cid: str, runtime_root=None) -> Path:
    return evidence_root("portable_release_upgrade_engineering", runtime_root) / "candidates" / f"{cid}.json"


def _simulation_path(sid: str, runtime_root=None) -> Path:
    return evidence_root("portable_release_upgrade_engineering", runtime_root) / "simulations" / f"{sid}.json"


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _source_manifest(root: Path) -> list[dict[str, Any]]:
    rows=[]
    for p in sorted((x for x in root.rglob('*') if x.is_file()), key=lambda x:x.relative_to(root).as_posix()):
        rel=p.relative_to(root).as_posix()
        rows.append({"relative_path":rel,"sha256":_sha(p),"size_bytes":p.stat().st_size})
    return rows


def _source_only_paths(root: Path) -> list[Path]:
    return [
        p for p in sorted((x for x in root.rglob('*') if x.is_file()), key=lambda x:x.relative_to(root).as_posix())
        if not any(part.lower() in FORBIDDEN_PARTS for part in p.relative_to(root).parts)
        and p.name.lower() not in FORBIDDEN_NAMES
    ]


def _source_only_manifest(root: Path) -> list[dict[str, Any]]:
    rows=[]
    for p in _source_only_paths(root):
        rel=p.relative_to(root)
        rows.append({"relative_path":rel.as_posix(),"sha256":_sha(p),"size_bytes":p.stat().st_size})
    return rows


def _manifest_digest(rows: Iterable[Mapping[str, Any]]) -> str:
    return digest([(x.get("relative_path"),x.get("sha256"),int(x.get("size_bytes") or 0)) for x in rows])


def _privacy_findings(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    for row in rows:
        rel=str(row.get('relative_path') or '')
        p=PurePosixPath(rel); low=rel.lower()
        if any(part.lower() in FORBIDDEN_PARTS for part in p.parts) or p.name.lower() in FORBIDDEN_NAMES:
            out.append({"kind":"forbidden_source_path","path_digest":digest(rel),"content_exposed":False})
        if p.suffix.lower() in {'.zip','.7z','.rar'}:
            out.append({"kind":"nested_archive","path_digest":digest(rel),"content_exposed":False})
    return out


def build_candidate_coherence(source_root: str|Path, *, candidate_version: str, changed_paths: Iterable[str]=(), migration_declarations: Iterable[Mapping[str,Any]]=(), known_limitations: Iterable[str]=(), runtime_root=None) -> dict[str,Any]:
    root=Path(source_root).resolve()
    if not root.exists() or not root.is_dir():return {"ok":False,"status":"source_root_missing","action_executed":False,**DENIED_AUTHORITY}
    rows=_source_manifest(root);manifest=_manifest_digest(rows);findings=_privacy_findings(rows)
    changed=[];unknown=[]
    available={x['relative_path'] for x in rows}
    for raw in changed_paths or []:
        rel=str(raw or '').replace('\\','/').lstrip('/')
        if not rel or '..' in PurePosixPath(rel).parts:unknown.append(digest(str(raw)));continue
        if rel not in available:unknown.append(digest(rel));continue
        if rel not in changed:changed.append(rel)
    migrations=[]
    for m in migration_declarations or []:
        migrations.append({
            "migration_id":str(m.get('migration_id') or ''),
            "kind":str(m.get('kind') or 'runtime_schema'),
            "required":bool(m.get('required')),
            "backward_compatible":bool(m.get('backward_compatible')),
            "rollback_supported":bool(m.get('rollback_supported')),
            "evidence_digest":str(m.get('evidence_digest') or digest(m)),
        })
    cid='release-candidate-'+digest({'version':candidate_version,'manifest':manifest,'changed':[digest(x) for x in changed],'migrations':migrations})[:24]
    row=seal({
        "contract_version":CONTRACT_VERSION,"candidate_id":cid,"candidate_version":str(candidate_version),
        "source_manifest_digest":manifest,"source_file_count":len(rows),"changed_paths":changed,"changed_path_digests":[digest(x) for x in changed],
        "unknown_changed_path_digests":unknown,"migration_declarations":migrations,"known_limitation_digests":[digest(x) for x in known_limitations][:64],
        "privacy_findings":findings,"source_only":not findings,"candidate_coherent":not findings and not unknown,
        "release_summary_digest":digest({'version':candidate_version,'changed':[digest(x) for x in changed],'migrations':migrations,'limitations':[digest(x) for x in known_limitations]}),
        "installation_performed":False,"promotion_performed":False,"certification_performed":False,"provider_contacted":False,
        "source_modified":False,"action_executed":False,**DENIED_AUTHORITY,
    })
    atomic_json(_candidate_path(cid,runtime_root),row)
    return {"ok":bool(row['candidate_coherent']),"status":"candidate_coherence_ready" if row['candidate_coherent'] else "candidate_coherence_blocked","candidate":public_candidate_coherence(row),"action_executed":False,**DENIED_AUTHORITY}


def public_candidate_coherence(row:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"candidate_id":row.get('candidate_id'),"candidate_version":row.get('candidate_version'),"source_manifest_digest":row.get('source_manifest_digest'),"source_file_count":int(row.get('source_file_count') or 0),"changed_path_count":len(row.get('changed_paths') or []),"unknown_changed_path_count":len(row.get('unknown_changed_path_digests') or []),"migration_count":len(row.get('migration_declarations') or []),"required_migration_count":sum(1 for x in row.get('migration_declarations') or [] if x.get('required')),"known_limitation_count":len(row.get('known_limitation_digests') or []),"privacy_finding_count":len(row.get('privacy_findings') or []),"source_only":bool(row.get('source_only')),"candidate_coherent":bool(row.get('candidate_coherent')),"release_summary_digest":row.get('release_summary_digest'),"source_paths_exposed":False,"raw_source_content_exposed":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"read_only":True,"action_executed":False,**DENIED_AUTHORITY}


def load_candidate_coherence(cid:str,*,runtime_root=None,include_private=False)->dict[str,Any]:
    row=read_json(_candidate_path(str(cid),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_candidate_coherence(row)


def _copy_tree_source_only(src:Path,dst:Path)->None:
    if dst.exists():shutil.rmtree(dst)
    dst.mkdir(parents=True,exist_ok=True)
    for p in _source_only_paths(src):
        rel=p.relative_to(src)
        target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)


def simulate_upgrade_lifecycle(*,baseline_root:str|Path,target_root:str|Path,simulation_root:str|Path,interrupt_after_files:int|None=None,runtime_root=None)->dict[str,Any]:
    """Exercise install/upgrade/backup/rollback only in a disposable root.

    Refuses simulation roots equal to or nested inside either source root.
    """
    base=Path(baseline_root).resolve();target=Path(target_root).resolve();sim=Path(simulation_root).resolve()
    if not base.is_dir() or not target.is_dir():return {"ok":False,"status":"simulation_source_missing","action_executed":False,**DENIED_AUTHORITY}
    for src in (base,target):
        try:sim.relative_to(src);return {"ok":False,"status":"simulation_root_inside_source_rejected","action_executed":False,**DENIED_AUTHORITY}
        except ValueError:pass
        try:src.relative_to(sim);return {"ok":False,"status":"source_inside_simulation_root_rejected","action_executed":False,**DENIED_AUTHORITY}
        except ValueError:pass
    base_before=_manifest_digest(_source_only_manifest(base));target_before=_manifest_digest(_source_only_manifest(target))
    sim.mkdir(parents=True,exist_ok=True);install=sim/'installed';backup=sim/'backup';staging=sim/'staging'
    for p in (install,backup,staging):
        if p.exists():shutil.rmtree(p)
    _copy_tree_source_only(base,install);installed_baseline=_manifest_digest(_source_manifest(install));_copy_tree_source_only(install,backup)
    backup_digest=_manifest_digest(_source_manifest(backup))
    interrupted=False;copied=0
    staging.mkdir(parents=True,exist_ok=True)
    for p in sorted((x for x in target.rglob('*') if x.is_file()),key=lambda x:x.relative_to(target).as_posix()):
        rel=p.relative_to(target)
        if any(part.lower() in FORBIDDEN_PARTS for part in rel.parts) or rel.name.lower() in FORBIDDEN_NAMES:continue
        dest=staging/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);copied+=1
        if interrupt_after_files is not None and copied>=max(0,int(interrupt_after_files)):
            interrupted=True;break
    target_source_only_rows=_source_only_manifest(target)
    expected_target=_manifest_digest(target_source_only_rows)
    staged_digest=_manifest_digest(_source_manifest(staging))
    upgraded=False
    if not interrupted and staged_digest==expected_target:
        if install.exists():shutil.rmtree(install)
        os.replace(staging,install);upgraded=True
    if interrupted:
        shutil.rmtree(staging,ignore_errors=True)
    # Roll back every simulation, proving the backup independently of upgrade success.
    if install.exists():shutil.rmtree(install)
    _copy_tree_source_only(backup,install)
    rollback_digest=_manifest_digest(_source_manifest(install))
    base_after=_manifest_digest(_source_only_manifest(base));target_after=_manifest_digest(_source_only_manifest(target))
    sid='upgrade-sim-'+digest({'base':base_before,'target':target_before,'interrupt':interrupt_after_files})[:24]
    row=seal({
        "contract_version":CONTRACT_VERSION,"simulation_id":sid,"baseline_manifest_digest":base_before,"target_manifest_digest":target_before,
        "installed_baseline_digest":installed_baseline,"backup_digest":backup_digest,"expected_target_source_only_digest":expected_target,"staged_digest":staged_digest,
        "interrupted":interrupted,"upgraded_before_rollback":upgraded,"rollback_digest":rollback_digest,"rollback_restored_baseline":rollback_digest==installed_baseline==backup_digest,
        "baseline_source_unchanged":base_before==base_after,"target_source_unchanged":target_before==target_after,"live_installation_touched":False,
        "simulation_root_external":True,"migration_executed":False,"provider_contacted":False,"installation_authority_granted":False,"promotion_authority_granted":False,
        "action_executed":True,**DENIED_AUTHORITY,
    })
    atomic_json(_simulation_path(sid,runtime_root),row)
    ok=bool(row['rollback_restored_baseline'] and row['baseline_source_unchanged'] and row['target_source_unchanged'] and (interrupted or upgraded))
    return {"ok":ok,"status":"upgrade_simulation_interrupted_and_recovered" if interrupted and ok else "upgrade_simulation_completed_and_rolled_back" if ok else "upgrade_simulation_failed","simulation":public_upgrade_simulation(row),"action_executed":True,**DENIED_AUTHORITY}


def public_upgrade_simulation(row:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"simulation_id":row.get('simulation_id'),"interrupted":bool(row.get('interrupted')),"upgraded_before_rollback":bool(row.get('upgraded_before_rollback')),"rollback_restored_baseline":bool(row.get('rollback_restored_baseline')),"baseline_source_unchanged":bool(row.get('baseline_source_unchanged')),"target_source_unchanged":bool(row.get('target_source_unchanged')),"live_installation_touched":False,"simulation_root_external":True,"migration_executed":False,"provider_contacted":False,"installation_authority_granted":False,"promotion_authority_granted":False,"raw_source_content_exposed":False,"source_paths_exposed":False,"action_executed":True,**DENIED_AUTHORITY}


def build_engineering_gate_preparation(*,candidate:Mapping[str,Any],simulations:Iterable[Mapping[str,Any]],runtime_root=None)->dict[str,Any]:
    sims=list(simulations or [])
    candidate_ok=bool(candidate.get('candidate_coherent') and candidate.get('source_only'))
    rollback_ok=bool(sims) and all(bool(x.get('rollback_restored_baseline')) for x in sims)
    source_ok=bool(sims) and all(bool(x.get('baseline_source_unchanged')) and bool(x.get('target_source_unchanged')) for x in sims)
    result={"contract_version":CONTRACT_VERSION,"candidate_coherent":candidate_ok,"simulation_count":len(sims),"rollback_simulation_passed":rollback_ok,"source_immutability_passed":source_ok,"native_windows_verified":False,"native_providers_verified":False,"desktop_packaging_verified":False,"live_upgrade_verified":False,"operator_trial_completed":False,"promotion_performed":False,"installation_performed":False,"ready_for_desktop_gate":candidate_ok and rollback_ok and source_ok,"action_executed":False,**DENIED_AUTHORITY}
    result['preparation_digest']=digest(result)
    return {"ok":bool(result['ready_for_desktop_gate']),"status":"v1700_desktop_gate_preparation_ready" if result['ready_for_desktop_gate'] else "v1700_desktop_gate_preparation_incomplete","gate_preparation":result,"action_executed":False,**DENIED_AUTHORITY}


__all__=['CONTRACT_VERSION','build_candidate_coherence','public_candidate_coherence','load_candidate_coherence','simulate_upgrade_lifecycle','public_upgrade_simulation','build_engineering_gate_preparation']
