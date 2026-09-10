from __future__ import annotations
import argparse,json,tempfile,sys,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.attention_intention_checkpoint import build_attention_intention_checkpoint
from conscious_agent.api_server import dispatch_api
def req(v,d='failed'):
 if not v:raise AssertionError(d)
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','detail':repr(e)})
 def report():
  root=Path(tempfile.mkdtemp())/'runtime'/'cognition';q=build_attention_intention_checkpoint(root,source_root=ROOT);req(q['ok'] and q['runtime_external'] and q['check_count']==10,q);req(q['action_authority_changed'] is False and q['consciousness_claimed'] is False,q)
 def api():
  root=Path(tempfile.mkdtemp())/'runtime';old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(root)
  try:status,p=dispatch_api('GET','/api/cognition/attention-intention-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1107.5',p)
  finally:
   if old is None:os.environ.pop('EIDOLON_DATA_DIR',None)
   else:os.environ['EIDOLON_DATA_DIR']=old
 def cli():
  env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(tempfile.mkdtemp())/'runtime');p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'attention-intention-checkpoint','--json'],capture_output=True,text=True,env=env,timeout=60);req(p.returncode==0,p.stderr);req(json.loads(p.stdout)['contract_version']=='v1107.5',p.stdout)
 def dashboard():
  text=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();req("id='attention-intention-checkpoint-panel'" in text and '/api/cognition/attention-intention-checkpoint' in text,text[:100])
 def privacy():
  q=build_attention_intention_checkpoint(Path(tempfile.mkdtemp())/'runtime'/'cognition',source_root=ROOT);blob=json.dumps(q).lower();req('private subject' not in blob and q['hidden_reasoning_exposed'] is False,q)
 for n,f in [('read_only_checkpoint',report),('read_only_api',api),('cli_surface',cli),('dashboard_surface',dashboard),('privacy_boundary',privacy)]:run(n,f)
 return rows
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();out={'suite':'v1107.5-attention-intention-checkpoint','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
