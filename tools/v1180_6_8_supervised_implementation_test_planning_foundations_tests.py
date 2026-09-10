from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_project_inspection import inspect_project_source
from supervised_deficiency_specification import review_deficiency_candidates, build_specification_candidates
from supervised_implementation_test_planning import *
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 p=Path(td); (p/'pkg').mkdir(); (p/'data').mkdir()
 (p/'pkg'/'bad.py').write_text('def bad(:\n pass\n',encoding='utf-8')
 (p/'pkg'/'good.py').write_text('# TODO review\ndef ok(): return 1\n',encoding='utf-8')
 (p/'data'/'secret.json').write_text('{"secret":"NEVER_SHOW"}',encoding='utf-8')
 inspection=inspect_project_source(p)
 ids={r['category']:r['candidate_id'] for r in inspection['deficiency_candidates']}
 review=review_deficiency_candidates(inspection,{ids['python_syntax_error']:'confirm',ids['maintenance_marker']:'reject'})
 specs=build_specification_candidates(review)
 plans=build_implementation_and_test_plans(specs)
 req(plans['planning_status']=='candidate_ready' and plans['plan_count']==1)
 plan=plans['plans'][0]
 req(plan['category']=='python_syntax_error' and 'prepare_minimal_parseability_change' in plan['implementation_step_codes'])
 req('python_compile' in plan['test_plan_codes'] and 'source_privacy_scan' in plan['post_change_checks'])
 req(plan['rollback_plan_codes']==['restore_pre_change_snapshot','rerun_focused_regression'])
 req(not plan['patch_allowed'] and not plan['test_execution_allowed'] and not plan['implementation_authorized'])
 req(len(plan['implementation_plan_digest'])==64 and plan['implementation_plan_id'].startswith('impl-'))
 req(len(plan['test_plan_digest'])==64 and len(plans['planning_bundle_digest'])==64)
 req(not plans['source_read'] and not plans['source_modified'] and not plans['project_registry_discovered'])
 req(not plans['patch_created'] and not plans['tests_executed'] and not plans['execution_invoked'])
 req('NEVER_SHOW' not in json.dumps(plans) and not plans['raw_source_exposed'] and not plans['raw_evidence_exposed'])
 bad=dict(specs); bad['contract_version']='wrong'
 req(build_implementation_and_test_plans(bad)['block_reason']=='invalid_specification_bundle')
 tampered=json.loads(json.dumps(specs)); tampered['specifications'][0]['category']='maintenance_marker'
 t=build_implementation_and_test_plans(tampered)
 req(t['planning_status']=='no_valid_specification' and t['invalid_specification_count']==1)
 duplicate=json.loads(json.dumps(specs)); duplicate['specifications']*=4
 d=build_implementation_and_test_plans(duplicate)
 req(d['plan_count']==1 and d['invalid_specification_count']==3)
 empty=build_implementation_and_test_plans({**specs,'specifications':[]})
 req(empty['planning_status']=='no_valid_specification' and empty['plan_count']==0)
 prompt=implementation_test_planning_prompt(plans)
 req('not patches or executable test commands' in prompt and 'Do not claim implementation' in prompt)
 source=(ROOT/'conscious_agent'/'supervised_implementation_test_planning.py').read_text(encoding='utf-8')
 req('read_text(' not in source and 'read_bytes(' not in source and 'write_text(' not in source and 'subprocess' not in source)
 req('patch_created": False' in source and 'tests_executed": False' in source and 'shell_invoked": False' in source)
 req(len(json.dumps(plans,sort_keys=True,separators=(',',':')).encode())<=MAX_REPORT_BYTES)
 req(plans['content_free'] and plans['operator_review_required'])
print(json.dumps({'ok':True,'suite':'v1180.6-v1180.8-supervised-implementation-test-planning-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
