from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from bounded_implementation_preparation import *
checks=[]
def req(v): checks.append(bool(v)); assert v

def d(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
plan={
 'specification_id':'spec-abc','implementation_plan_id':'impl-abc','implementation_plan_digest':'a'*64,
 'test_plan_digest':'b'*64,'implementation_step_codes':['prepare_minimal_parseability_change'],
 'pre_change_checks':['source_identity_match'],'acceptance_criteria_codes':['python_parses'],
 'post_change_checks':['python_compile','focused_regression'],'rollback_plan_codes':['restore_pre_change_snapshot'],
 'patch_allowed':False,'test_execution_allowed':False,
}
planning={'contract_version':'v1180.8','content_free':True,'source_modified':False,'patch_created':False,'tests_executed':False,'planning_bundle_digest':'c'*64,'plans':[plan]}
baseline={'content_free':True,'baseline_digest':'d'*64,'files':[{'path':'conscious_agent/example.py','file_digest':'e'*64}]}
bindings={'impl-abc':{'target_path':'conscious_agent/example.py','expected_file_digest':'e'*64}}
result=prepare_implementation_candidates(planning,baseline,bindings)
req(result['preparation_status']=='candidate_ready' and result['preparation_count']==1)
row=result['preparations'][0]
req(row['target_path']=='conscious_agent/example.py' and row['baseline_file_digest']=='e'*64)
req(row['sandbox_required'] and row['fresh_source_match_required'] and row['operator_review_required'])
req(not row['patch_creation_allowed'] and not row['implementation_authorized'] and not row['test_execution_allowed'])
req(row['preparation_id'].startswith('prep-') and len(row['preparation_digest'])==64)
req(row['change_step_codes']==['prepare_minimal_parseability_change'])
req(row['rollback_plan_codes']==['restore_pre_change_snapshot'])
req(not result['source_read'] and not result['source_modified'] and not result['patch_created'])
req(not result['tests_executed'] and not result['shell_invoked'] and not result['tool_invoked'])
req(result['content_free'] and result['operator_review_required'] and not result['project_registry_discovered'])
stale=prepare_implementation_candidates(planning,baseline,{'impl-abc':{'target_path':'conscious_agent/example.py','expected_file_digest':'f'*64}})
req(stale['preparation_status']=='stale_source' and stale['stale_binding_count']==1 and stale['preparation_count']==0)
for bad_path in ('../secret.py','/etc/passwd','C:/secret.py','data/secret.json','conscious_agent/no.exe'):
 blocked=prepare_implementation_candidates(planning,baseline,{'impl-abc':{'target_path':bad_path,'expected_file_digest':'e'*64}})
 req(blocked['preparation_count']==0)
req(prepare_implementation_candidates({**planning,'contract_version':'bad'},baseline,bindings)['block_reason']=='invalid_input_contract')
req(prepare_implementation_candidates(planning,{**baseline,'baseline_digest':'bad'},bindings)['block_reason']=='invalid_input_contract')
dup=prepare_implementation_candidates({**planning,'plans':[plan,plan]},baseline,bindings)
req(dup['preparation_count']==1 and dup['duplicate_plan_count']==1)
req('not patches or authority' in implementation_preparation_prompt(result))
source=(ROOT/'conscious_agent'/'bounded_implementation_preparation.py').read_text(encoding='utf-8')
req('read_text(' not in source and 'read_bytes(' not in source and 'write_text(' not in source and 'subprocess' not in source)
req('patch_created": False' in source and 'tests_executed": False' in source and 'shell_invoked": False' in source)
req(len(json.dumps(result,sort_keys=True,separators=(',',':')).encode())<=MAX_REPORT_BYTES)
print(json.dumps({'ok':True,'suite':'v1181.0-v1181.2-bounded-implementation-preparation-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
