from pathlib import Path
import tempfile,json,os,subprocess,sys
from conscious_agent.belief_revision_deliberation_checkpoint import build_belief_revision_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1]; passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob('*')); r=build_belief_revision_deliberation_checkpoint(root,source_root=ROOT); req(r['contract_version']=='v1118.5'); req(r['ok']); req(r['runtime_mutated'] is False and before==list(root.rglob('*'))); req(len(r['checks'])==13 and all(x['status']=='pass' for x in r['checks'])); req(not r['hidden_reasoning_exposed'] and not r['evidence_text_exposed']); req(not any(r[k] for k in ('belief_revised','attention_selected','intention_formed','decision_committed','proposal_created','approval_granted','authorization_granted','external_action_executed'))); env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(root/'cli'); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'belief-revision-deliberation-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True); req(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1118.5'); os.environ['EIDOLON_DATA_DIR']=str(root/'api'); status,payload=dispatch_api('GET','/api/cognition/belief-revision-deliberation-checkpoint'); req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1118.5'); post,_=dispatch_api('POST','/api/cognition/belief-revision-deliberation-checkpoint',body={}); req(post in (404,405)); dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); req('belief-revision-deliberation-checkpoint-panel' in dash)
print(json.dumps({'passed':passed,'total':10,'suite':'v1118.5'}))
