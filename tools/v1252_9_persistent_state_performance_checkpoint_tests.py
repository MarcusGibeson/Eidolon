from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1252-9-')
from checkpoint_registry import checkpoint_registry_manifest,lookup_checkpoint,validate_checkpoint_report
from release_authority import release_authority_record,validate_release_authority
from release_metadata_consolidation import validate_release_metadata_consolidation
from persistent_state_performance import benchmark_persistent_state_scaling,persistent_state_performance_contract
from persistent_state_performance_checkpoint import build_persistent_state_performance_checkpoint
checks=[]
def req(v): checks.append(bool(v)); assert v
contract=persistent_state_performance_contract(source_root=ROOT); req(contract['ok']); req(contract['passed']==contract['total']); req(len(contract['versions'])==9)
profile=os.environ.get('EIDOLON_V1252_BENCHMARK_PROFILE','full').strip().lower()
if profile=='medium':
    bench=benchmark_persistent_state_scaling(memory_count=5000,session_count=250,action_count=5000)
    req(bench['counts']=={'memories':5000,'sessions':250,'actions':5000})
    req(all(value for key,value in bench['checks'].items() if not key.endswith('_scale_reached')))
else:
    profile='full'; bench=benchmark_persistent_state_scaling(); req(bench['ok']); req(bench['counts']=={'memories':20000,'sessions':1000,'actions':20000}); req(all(bench['checks'].values()))
req(bench['measured_ms']['memory_recent_80_ms']<=bench['budgets_ms']['memory_recent_80_ms']); req(bench['measured_ms']['cross_session_select_ms']<=bench['budgets_ms']['cross_session_select_ms']); req(bench['measured_ms']['action_exact_lookup_ms']<=bench['budgets_ms']['action_exact_lookup_ms']); req(bench['measured_ms']['memory_append_ms']<=bench['budgets_ms']['memory_append_ms'])
cp=build_persistent_state_performance_checkpoint(source_root=ROOT); req(cp['ok']); req(cp['checkpoint_version']=='1252.9'); req(cp['status']=='persistent_state_performance_checkpoint_ready'); req(validate_checkpoint_report(cp,source_root=ROOT)['ok'])
reg=checkpoint_registry_manifest(source_root=ROOT); req(reg['ok']); req(reg['record_count']>=80); req(lookup_checkpoint('1252.9') is not None); req(lookup_checkpoint('1252.9').title=='Persistent-State Performance Checkpoint')
auth=release_authority_record(); req(any(row.get('version')=='1252.9' for row in auth['history'])); req(auth['history_count']>=80); req(auth['history'][-1]['version']==auth['working_source_version']); req(isinstance(auth['codex_review_state'],str) and bool(auth['codex_review_state'].strip())); req(validate_release_authority(source_root=ROOT)['ok']); req(validate_release_metadata_consolidation(source_root=ROOT)['ok'])
for k in ('installation_authorized','promotion_authorized','certification_authorized','release_authorized','provider_contact_authorized','tool_execution_authorized','project_mutation_authorized','source_mutation_authorized','approval_granted','independent_authority_granted'): req(auth[k] is False)
r={'suite':'v1252.9-persistent-state-performance-checkpoint','ok':all(checks),'passed':sum(checks),'total':len(checks),'benchmark_profile':profile,'benchmark_ms':bench['measured_ms'],'scale':bench['counts']}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
