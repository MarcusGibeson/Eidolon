from __future__ import annotations
"""v2656 read-only observability for latest project lifecycle rehearsal evidence."""
from pathlib import Path
from typing import Any,Mapping
import json,os,tempfile
CONTRACT_VERSION='v2656.0'

def _root(runtime_root=None)->Path:
    if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
    return (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'development')
def _load(path:Path)->dict[str,Any]:
    try:
        v=json.loads(path.read_text(encoding='utf-8'));return v if isinstance(v,dict) else {}
    except (OSError,ValueError,TypeError):return {}
def persist_project_simulation_observability(*,health:Mapping[str,Any],evidence:Mapping[str,Any],readiness:Mapping[str,Any],runtime_root=None)->dict[str,Any]:
    root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);payload={'health':dict(health),'evidence':dict(evidence),'readiness':dict(readiness)}
    path=root/'developer_project_simulation_observability.json';fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=str(root))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(payload,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass
    return {'ok':True,'contract_version':CONTRACT_VERSION,'runtime_only':True,'project_content_stored':False,'source_mutated':False,'authority_granted':False}
def build_project_simulation_observability(runtime_root=None)->dict[str,Any]:
    raw=_load(_root(runtime_root)/'developer_project_simulation_observability.json');health=raw.get('health') if isinstance(raw.get('health'),Mapping) else {};evidence=raw.get('evidence') if isinstance(raw.get('evidence'),Mapping) else {};readiness=raw.get('readiness') if isinstance(raw.get('readiness'),Mapping) else {}
    state=str(health.get('state') or ('no_data' if not raw else 'insufficient'))
    return {'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'scenario_count':int(health.get('scenario_count') or 0),'failure_mode_count':int(health.get('failure_mode_count') or len(evidence.get('failure_modes') or [])),'simulation_confidence':str(evidence.get('simulation_confidence') or 'insufficient'),'eligible_for_operator_start_trial_review':bool(readiness.get('eligible_for_operator_start_trial_review')),'real_verification_still_required':bool(readiness.get('real_verification_still_required',True)),'synthetic_evidence_only':True,'project_content_stored':False,'automatic_project_start_permitted':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','persist_project_simulation_observability','build_project_simulation_observability']
