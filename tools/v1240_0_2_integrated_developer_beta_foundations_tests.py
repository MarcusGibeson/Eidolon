from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from integrated_developer_beta import AUTHORITY_FLAGS,RETAINED_CHECKPOINTS,build_integrated_developer_beta_contract,scenario_registry
checks=[]
def check(v): checks.append(bool(v))
r=scenario_registry(); c=build_integrated_developer_beta_contract(source_root=ROOT)
for v in (r.get('ok'),r.get('scenario_count')==10,r.get('stage_count')==10,r.get('content_free') is True,r.get('read_only') is True,len(r.get('scenarios',[]))==10,c.get('ok'),c.get('status')=='integrated_developer_beta_contract_ready',c.get('contract_version')=='v1240.8',c.get('milestone_name')=='Integrated Developer Beta',c.get('roadmap_path')=='Balanced Mind-and-Action Path 3',c.get('retained_stage_count')==10,c.get('scenario_count')==10,c.get('complete_stage_order') is True,c.get('retained_versions_match') is True,c.get('retained_checkpoints_pass') is True,c.get('historical_receipts_remain_immutable') is True,c.get('missing_timeout_or_incomplete_evidence_never_passes') is True,c.get('adversarial_fail_closed') is True,c.get('os_level_sandbox_not_claimed') is True,c.get('runtime_data_read') is False,c.get('runtime_data_written') is False,c.get('source_modified') is False): check(v)
for key,expected in AUTHORITY_FLAGS.items(): check(c.get(key) is expected)
for row,expected in zip(c.get('stages',[]),RETAINED_CHECKPOINTS):
    for v in (row.get('stage_id')==expected[0],row.get('expected_contract_version')==expected[1],row.get('checkpoint_id')==expected[2],row.get('reported_contract_version')==expected[1],row.get('ok') is True,row.get('read_only') is True,row.get('content_free') is True,row.get('runtime_data_read') is False,row.get('runtime_data_written') is False,row.get('source_modified') is False,row.get('authority_granted') is False,row.get('provider_contacted') is False,row.get('commands_executed') is False,row.get('tests_executed') is False,row.get('project_modified') is False,row.get('cognition_written') is False,int(row.get('passed_checks') or 0)>0): check(v)
for s in r.get('scenarios',[]):
    for v in (bool(s.get('scenario_id')),bool(s.get('scenario_digest')),s.get('content_free') is True,s.get('operator_authority_required_at_each_mutation') is True,s.get('automatic_continuation_allowed') is False,s.get('missing_evidence_is_pass') is False,len(s.get('required_stages',[]))>=2): check(v)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
