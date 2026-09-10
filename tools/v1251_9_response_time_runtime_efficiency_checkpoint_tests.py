from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1251-9-'))
from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint, validate_checkpoint_report
from release_authority import release_authority_record, validate_release_authority
from release_metadata_consolidation import validate_release_metadata_consolidation
from response_time_efficiency import response_time_contract
from response_time_runtime_efficiency_checkpoint import build_response_time_runtime_efficiency_checkpoint
checks=[]
def req(v): checks.append(bool(v)); assert v
contract=response_time_contract(source_root=ROOT); cp=build_response_time_runtime_efficiency_checkpoint(source_root=ROOT); val=validate_checkpoint_report(cp,source_root=ROOT); reg=checkpoint_registry_manifest(source_root=ROOT); auth=release_authority_record(); authv=validate_release_authority(source_root=ROOT); meta=validate_release_metadata_consolidation(source_root=ROOT)
req(contract['ok']); req(contract['passed']==contract['total']); req(cp['ok']); req(cp['passed']==cp['total']==6); req(cp['checkpoint_version']=='1251.9'); req(cp['status']=='response_time_runtime_efficiency_alpha_checkpoint_ready'); req(val['ok']); req(reg['ok']); req(reg['record_count']>=70); req(lookup_checkpoint('1251.9') is not None); req(lookup_checkpoint('1251.9').title=='Response-Time and Runtime Efficiency Alpha Checkpoint'); req(any(row.get('version')=='1251.9' for row in auth['history'])); req(auth['history_count']>=70); req(auth['history'][-1]['version']==auth['working_source_version']); req(isinstance(auth['codex_review_state'],str) and bool(auth['codex_review_state'].strip())); req(authv['ok']); req(meta['ok']); req(contract['ordinary_projection_estimated_tokens']<=800); req(contract['social_projection_estimated_tokens']<=600)
for k in ('installation_authorized','promotion_authorized','certification_authorized','release_authorized','provider_contact_authorized','tool_execution_authorized','project_mutation_authorized','source_mutation_authorized','approval_granted','independent_authority_granted'): req(auth[k] is False)
r={'suite':'v1251.9-response-time-runtime-efficiency-checkpoint','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
