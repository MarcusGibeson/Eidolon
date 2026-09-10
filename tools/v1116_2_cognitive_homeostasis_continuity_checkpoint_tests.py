from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
passed=0
def check(n,c):
 global passed
 if not c:raise AssertionError(n)
 passed+=1
from conscious_agent.cognitive_homeostasis_continuity_checkpoint import build_cognitive_homeostasis_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
with tempfile.TemporaryDirectory() as td:
 root=Path(td);before=list(root.rglob('*'));r=build_cognitive_homeostasis_continuity_checkpoint(root,source_root=ROOT);check('contract',r['contract_version']=='v1116.2');check('ok',r['ok']);check('readonly',not r['runtime_mutated'] and before==list(root.rglob('*')));check('checks',len(r['checks'])==12 and all(x['status']=='pass' for x in r['checks']));check('privacy',not r['raw_messages_exposed'] and not r['hidden_reasoning_exposed']);check('authority',not any(r[k] for k in ('schedule_changed','work_paused','work_resumed','attention_selected','intention_formed','authorization_granted','external_action_executed')));env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'cognitive-homeostasis-continuity-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);check('cli',proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1116.2');os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/cognitive-homeostasis-continuity-checkpoint');check('api',status==200 and (payload.get('data') or {}).get('contract_version')=='v1116.2');post,_=dispatch_api('POST','/api/cognition/cognitive-homeostasis-continuity-checkpoint',body={});check('post_blocked',post in (404,405));source=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');check('dashboard','cognitive-homeostasis-continuity-checkpoint' in source)
print(json.dumps({'passed':passed,'total':10,'suite':'v1116.2'}))
