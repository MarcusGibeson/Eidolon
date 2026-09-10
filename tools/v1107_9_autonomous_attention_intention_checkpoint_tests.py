from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.autonomous_attention_intention_checkpoint import build_autonomous_attention_intention_checkpoint
from conscious_agent.api_server import dispatch_api

def req(x,m):
 if not x: raise AssertionError(m)
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','error':repr(e)})
 def checkpoint():
  q=build_autonomous_attention_intention_checkpoint(Path(tempfile.mkdtemp())/'runtime'/'cognition',source_root=ROOT);req(q['ok'] and q['check_count']==11 and q['runtime_external'],q)
 def api():
  status,p=dispatch_api('GET','/api/cognition/autonomous-attention-intention-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1107.9',p)
 def cli():
  env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(tempfile.mkdtemp())/'runtime');p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'autonomous-attention-intention-checkpoint','--json'],capture_output=True,text=True,env=env,timeout=60);req(p.returncode==0,p.stderr);req(json.loads(p.stdout)['contract_version']=='v1107.9',p.stdout)
 def dashboard():
  text=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();req('autonomous-attention-intention-checkpoint-panel' in text and '/api/cognition/autonomous-attention-intention-checkpoint' in text,text[-500:])
 def privacy():
  q=build_autonomous_attention_intention_checkpoint(Path(tempfile.mkdtemp())/'runtime'/'cognition',source_root=ROOT);req(all(q[k] is False for k in ('hidden_reasoning_exposed','private_subjects_exposed','action_authority_changed','external_action_executed','consciousness_claimed')),q)
 def metadata():
  from conscious_agent import release_metadata as m;req(tuple(map(int,m.WORKING_SOURCE_VERSION.split('.'))) >= (1107,9),m.RUNTIME_MILESTONE)
 for n,f in [('checkpoint',checkpoint),('api',api),('cli',cli),('dashboard',dashboard),('privacy',privacy),('metadata',metadata)]:run(n,f)
 return rows
if __name__=='__main__':
 rows=tests();out={'suite':'v1107.9-autonomous-attention-intention-checkpoint','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
