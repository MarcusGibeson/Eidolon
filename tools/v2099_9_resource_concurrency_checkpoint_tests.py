from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2099-data-')
from resource_cooperative_governance_v2000 import configure_resource_budgets,assess_resource_pressure,apply_cooperative_suspension,read_resource_state,public_resource_state
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2099-runtime-'))
conf=configure_resource_budgets(budgets={'cpu_percent':30,'memory_percent':40,'thermal_percent':75,'background_concurrency':2,'provider_concurrency':1,'time_minutes':15},event_id='budget-1',runtime_root=runtime)
req(conf['ok'] and conf['state']['budgets']['cpu_percent']==30,'operator_budgets_persist')
req(conf['process_started'] is False and conf['provider_contacted'] is False,'budget_config_nonexecuting')
normal=assess_resource_pressure({'cpu_percent':10,'memory_percent':10,'thermal_percent':40,'background_concurrency':1,'provider_concurrency':0,'time_minutes':5},runtime_root=runtime)
req(normal['mode']=='permit' and normal['background_should_yield'] is False,'normal_pressure_permits')
elevated=assess_resource_pressure({'cpu_percent':31,'memory_percent':20,'thermal_percent':50,'background_concurrency':1,'provider_concurrency':0,'time_minutes':5},runtime_root=runtime)
req(elevated['mode']=='degrade','budget_exceedance_degrades')
heavy=assess_resource_pressure({'cpu_percent':25,'memory_percent':20,'thermal_percent':50,'foreground_high_load':True},runtime_root=runtime)
req(heavy['mode']=='suspend','heavy_foreground_suspends')
thermal=assess_resource_pressure({'cpu_percent':10,'memory_percent':10,'thermal_percent':90},runtime_root=runtime)
req(thermal['mode']=='suspend','thermal_pressure_suspends')
provider=assess_resource_pressure({'provider_outage':True},runtime_root=runtime)
req(provider['mode']=='degrade' and provider['provider_outage'] is True,'provider_outage_degrades')
missing=assess_resource_pressure({},runtime_root=runtime)
req(missing['mode']=='suspend' and missing['measurement_evidence_sufficient'] is False,'missing_measurements_suspend')
invalid=assess_resource_pressure({'cpu_percent':'not-a-number'},runtime_root=runtime)
req(invalid['mode']=='suspend' and invalid['invalid_dimensions']==['cpu_percent'],'invalid_measurements_suspend')
suspend=apply_cooperative_suspension(['bg_a','bg_b'],assessment=heavy,event_id='suspend-1',runtime_root=runtime)
req(suspend['ok'] and all(row['status']=='suspended' for row in suspend['state']['ticket_states']),'logical_ticket_suspension_persisted')
req(suspend['process_paused'] is False and suspend['process_killed'] is False,'logical_suspension_not_os_control')
replay=apply_cooperative_suspension(['bg_a','bg_b'],assessment=heavy,event_id='suspend-1',runtime_root=runtime)
req(replay['status']=='cooperative_suspension_replayed','suspension_exactly_once')
resume=apply_cooperative_suspension(['bg_a','bg_b'],assessment=normal,event_id='resume-1',runtime_root=runtime)
req(all(row['status']=='eligible' and row['resume_count']==1 for row in resume['state']['ticket_states']),'cooperative_resume_preserves_state')
state=public_resource_state(read_resource_state(runtime_root=runtime))
req(state['revision']>=3 and state['raw_content_persisted'] is False,'resource_state_restart_safe_content_free')
bad=dict(normal);bad['mode']='suspend'
req(apply_cooperative_suspension(['x'],assessment=bad,event_id='bad-digest',runtime_root=runtime)['status']=='resource_assessment_digest_invalid','tampered_assessment_rejected')
print(json.dumps({'suite':'v2099.9-resource-concurrency','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
