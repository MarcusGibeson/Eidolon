from pathlib import Path
import json,subprocess,sys,tempfile
from conscious_agent.conversation_cognition_unification_reliability_checkpoint import build_conversation_cognition_unification_reliability_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=[]
 def req(v,n):
  if not v: raise AssertionError(n)
  p.append(n)
 with tempfile.TemporaryDirectory() as d:
  q=build_conversation_cognition_unification_reliability_checkpoint(Path(d),source_root=ROOT); req(q['ok'],'ok'); req(q['passed']==q['total']==21,'checks'); req(q['contract_version']=='v1145.8','contract'); req(not q['runtime_mutated'],'runtime'); req(not q['source_modified'],'source'); req(not q['message_sent'],'send'); req(not q['provider_contacted_by_checkpoint'],'provider'); req(not q['hidden_reasoning_exposed'],'privacy'); req(q['desktop_verification_pending'],'desktop')
 out=subprocess.check_output([sys.executable,str(ROOT/'eidolon.py'),'conversation-cognition-unification-reliability-checkpoint'],text=True); req(json.loads(out)['contract_version']=='v1145.8','cli')
 status,payload=dispatch_api('GET','/api/cognition/conversation-cognition-unification-reliability-checkpoint'); req(status==200 and payload['data']['contract_version']=='v1145.8','api_get')
 status,_=dispatch_api('POST','/api/cognition/conversation-cognition-unification-reliability-checkpoint',body={'confirm':True}); req(status!=200,'api_post')
 dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(); req('conversation-cognition-unification-reliability-checkpoint-panel' in dash,'panel'); req('/api/cognition/conversation-cognition-unification-reliability-checkpoint' in dash,'dashboard_api')
 print(f'v1145.8 checks: {len(p)}/{len(p)}')
if __name__=='__main__': main()
