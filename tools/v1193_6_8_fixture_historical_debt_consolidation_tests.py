from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.fixture_historical_debt_consolidation import *
from conscious_agent.fixture_historical_debt_consolidation_checkpoint import build_fixture_historical_debt_consolidation_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[];req=lambda v:checks.append(bool(v))
r=build_fixture_historical_debt_consolidation_checkpoint(source_root=ROOT)
for k,v in {'ok':True,'contract_version':'v1193.8','checkpoint_id':'fixture-historical-debt-consolidation:v1193.8','read_only':True,'content_free':True,'source_unchanged':True,'runtime_mutated':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'execution_invoked':False,'authority_granted':False}.items():req(r.get(k)==v)
req(r['summary']['record_count']==4);req(r['summary']['alias_count']==1);req(r['summary']['deferred_count']==1);req(r['summary']['historical_truth_preserved'] is True)
base=[create_fixture_record(fixture_id='a',owner='platform',cleanup_owner='platform',fixture_group='g',suite_path='tools/a.py',source_version='v1',overlap_class='unique',disposition='retain_independent',expected_checks=1),create_fixture_record(fixture_id='b',owner='release',cleanup_owner='release',fixture_group='g',suite_path='tools/b.py',source_version='v1',overlap_class='exact_duplicate',canonical_fixture_id='a',disposition='retain_alias',historical_debt_id='d',debt_severity='medium',expected_checks=1)]
report=consolidate_fixture_records(base);req(report['status']=='consolidated');req(report['consolidation']['alias_map']=={'b':'a'});req(report['consolidation']['fixture_deleted'] is False);req(report['consolidation']['verifier_retired'] is False);req(public_consolidation_summary(report)['content_free'] is True)
mutations=[('empty',[]),('oversized',base*200)]
for _,rows in mutations:req(consolidate_fixture_records(rows)['status']=='blocked')
for field,value in [('owner','x'),('cleanup_owner','x'),('suite_path','bad'),('overlap_class','x'),('disposition','x'),('debt_severity','x'),('expected_checks',-1),('authority_state','granted'),('fixture_deleted',True),('verifier_retired',True),('historical_truth_preserved',False)]:
 rows=[dict(x) for x in base];rows[0][field]=value;req(consolidate_fixture_records(rows)['status']=='blocked')
for field in ['prompt','conversation','memory','secret','raw_source','patch','stdout','stderr','provider_payload','private_reasoning','content','text']:
 rows=[dict(x) for x in base];rows[0][field]='x';req(consolidate_fixture_records(rows)['status']=='blocked')
rows=[dict(x) for x in base];rows[1]['canonical_fixture_id']='missing';req(consolidate_fixture_records(rows)['status']=='blocked')
rows=[dict(x) for x in base];rows[1]['fixture_id']='a';req(consolidate_fixture_records(rows)['status']=='blocked')
rows=[dict(x) for x in base];rows[1]['suite_path']='tools/a.py';req(consolidate_fixture_records(rows)['status']=='blocked')
reg=inspect_checkpoint_registry(source_root=ROOT);entry=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='fixture-historical-debt-consolidation-checkpoint');req(entry['contract_version']=='v1193.8');req(entry['builder']=='build_fixture_historical_debt_consolidation_checkpoint')
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'fixture-historical-debt-consolidation-checkpoint'],cwd=ROOT,text=True,capture_output=True);req(p.returncode==0);req(json.loads(p.stdout)['ok'] is True)
status,payload=dispatch_api('GET','/api/cognition/fixture-historical-debt-consolidation-checkpoint');req(status==200);req(payload['data']['ok'] is True);status,_=dispatch_api('POST','/api/cognition/fixture-historical-debt-consolidation-checkpoint');req(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');req('fixture-historical-debt-consolidation-checkpoint-panel' in html);req('/api/cognition/fixture-historical-debt-consolidation-checkpoint' in html)
meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');req('v1193.8 Fixture and Historical-Debt Consolidation' in meta);req('v1193.9' in meta)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8');req(release.count('v1193.8-fixture-historical-debt-consolidation')==1)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
