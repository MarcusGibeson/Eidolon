from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
passed=0
def check(name,cond):
 global passed
 if not cond: raise AssertionError(name)
 passed+=1
import os,subprocess
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_load_continuity_checkpoint import build_cognitive_load_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
with tempfile.TemporaryDirectory() as td:
 runtime=Path(td)/'runtime';s=CognitiveDemandStore(runtime);did=s.register('e1',origin_type='objective',origin_id='o1')['result']['demand_id'];CognitiveLoadArbitrator(runtime).allocate('a1',demand_ids=[did]);before={p.name:p.read_bytes() for p in runtime.glob('*.json')};report=build_cognitive_load_continuity_checkpoint(runtime,source_root=ROOT);after={p.name:p.read_bytes() for p in runtime.glob('*.json')};check('contract',report['contract_version']=='v1115.2');check('ready',report['ok']);check('read_only',before==after and not report['runtime_mutated']);check('checks',len(report['checks'])==12 and all(x['status']=='pass' for x in report['checks']));check('separation',not any(report[k] for k in ('attention_selected','intention_formed','decision_committed','proposal_created','approval_granted','authorization_granted','external_action_executed')));check('privacy',not report['hidden_reasoning_exposed'] and not report['raw_messages_exposed']);check('summary',report['summary']['demand_count']==1 and report['summary']['allocation_count']==1)
 env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-load-continuity-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);check('cli',proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1115.2')
 os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/cognitive-load-continuity-checkpoint');check('api',status==200 and (payload.get('data') or {}).get('contract_version')=='v1115.2')
 source=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');check('dashboard','cognitive-load-continuity-checkpoint' in source)
print(json.dumps({'passed':passed,'total':10,'suite':'v1115.2'}))
