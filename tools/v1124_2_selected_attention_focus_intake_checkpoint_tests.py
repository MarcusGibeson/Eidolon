from pathlib import Path
import tempfile, subprocess, sys
from conscious_agent.selected_attention_records import SelectedAttentionStore
from conscious_agent.reflective_focus_state import ReflectiveFocusStateStore
from conscious_agent.selected_attention_focus_intake_checkpoint import build_selected_attention_focus_intake_checkpoint

def main():
 checks=[]
 def ck(n,o): checks.append((n,bool(o)))
 root=Path(__file__).resolve().parents[1]
 with tempfile.TemporaryDirectory() as td:
  runtime=Path(td)/'cognition'; a=SelectedAttentionStore(runtime); r=a.select('e1',outcome_id='o1',candidate_id='c1',session_id='s1',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,uncertainty=.2); ReflectiveFocusStateStore(runtime).record('e2',attention_id=r['attention_id'])
  report=build_selected_attention_focus_intake_checkpoint(runtime,source_root=root)
  ck('checkpoint 18/18',report['passed']==18 and report['total']==18)
  ck('read only',not report['runtime_mutated'] and not report['source_modified'])
  ck('selected attention visible',report['summary']['attention_count']==1)
  ck('focus visible',report['summary']['focus_count']==1)
  ck('reflection boundary',not report['reflection_created'])
  ck('intention boundary',not report['intention_created'])
  ck('initiative boundary',not report['initiative_created'])
  ck('communication boundary',not report['message_sent'] and not report['notification_created'])
  ck('provider browsing boundary',not report['provider_contacted'] and not report['browsing_performed'])
  ck('execution boundary',not report['external_action_executed'])
  ck('privacy boundary',not report['hidden_reasoning_exposed'] and not report['private_content_exposed'])
  env=dict(__import__('os').environ); env['EIDOLON_DATA_DIR']=str(Path(td))
  p=subprocess.run([sys.executable,str(root/'eidolon.py'),'selected-attention-focus-intake-checkpoint','--json'],cwd=root,env=env,capture_output=True,text=True)
  ck('cli read only',p.returncode==0 and 'v1124.2' in p.stdout)
  from conscious_agent.api_server import dispatch_api
  status,payload=dispatch_api('GET','/api/cognition/selected-attention-focus-intake-checkpoint')
  ck('get api',status==200 and payload.get('data',{}).get('contract_version')=='v1124.2')
  status,_=dispatch_api('POST','/api/cognition/selected-attention-focus-intake-checkpoint',body={})
  ck('post rejected',status in {404,405})
  dash=(root/'conscious_agent/dashboard_first_use.py').read_text(encoding='utf-8')
  ck('dashboard exposed','selected-attention-focus-intake-checkpoint-panel' in dash)
  ck('no raw content fields',not report['raw_messages_exposed'] and not report['prompts_exposed'] and not report['provider_payloads_exposed'])
  ck('desktop pending',report['desktop_verification_pending'])
  ck('status ready',report['status']=='ready_for_desktop_verification')
 for n,o in checks: print(('PASS' if o else 'FAIL')+': '+n)
 print(f'{sum(o for _,o in checks)}/{len(checks)}'); return 0 if all(o for _,o in checks) else 1
if __name__=='__main__': raise SystemExit(main())
