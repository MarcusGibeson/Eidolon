from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.intention_lifecycle_review import build_intention_lifecycle_review
from conscious_agent.api_server import dispatch_api

def req(x,m):
 if not x: raise AssertionError(m)
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','error':repr(e)})
 def checkpoint():
  q=build_intention_lifecycle_review(Path(tempfile.mkdtemp())/'runtime'/'cognition',source_root=ROOT);req(q['ok'] and q['check_count']==10 and q['runtime_external'],q)
 def api():
  status,p=dispatch_api('GET','/api/cognition/intention-lifecycle-review');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1107.8',p)
 def cli():
  env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(tempfile.mkdtemp())/'runtime');p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'intention-lifecycle-review','--json'],capture_output=True,text=True,env=env,timeout=60);req(p.returncode==0,p.stderr);req(json.loads(p.stdout)['contract_version']=='v1107.8',p.stdout)
 def dashboard():
  text=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();req('intention-lifecycle-review-panel' in text and '/api/cognition/intention-lifecycle-review' in text,text[-500:])
 def privacy():
  q=build_intention_lifecycle_review(Path(tempfile.mkdtemp())/'runtime'/'cognition',source_root=ROOT);b=json.dumps(q).lower();req(q['hidden_reasoning_exposed'] is False and q['private_subjects_exposed'] is False and q['action_authority_changed'] is False and q['consciousness_claimed'] is False,q)
 for n,f in [('checkpoint',checkpoint),('api',api),('cli',cli),('dashboard',dashboard),('privacy',privacy)]:run(n,f)
 return rows
if __name__=='__main__':
 rows=tests();out={'suite':'v1107.8-intention-lifecycle-review','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
