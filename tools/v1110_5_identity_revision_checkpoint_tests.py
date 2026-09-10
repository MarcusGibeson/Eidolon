from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def snap():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
def main():
 root=Path(tempfile.mkdtemp())/'cognition';before=snap();from conscious_agent.identity_revision_checkpoint import build_identity_revision_checkpoint;c=build_identity_revision_checkpoint(root,source_root=ROOT);after=snap();req(before==after);req(c['contract_version']=='v1110.5');req(c['runtime_mutated'] is False and c['action_authority_changed'] is False);req(c['consciousness_claimed'] is False)
 from conscious_agent.api_server import dispatch_api;os.environ['EIDOLON_DATA_DIR']=str(root.parent);status,p=dispatch_api('GET','/api/cognition/identity-revision-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1110.5');status2,_=dispatch_api('POST','/api/cognition/identity-revision-checkpoint',body={});req(status2!=200)
 q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'identity-revision-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(q.returncode==0 and json.loads(q.stdout)['contract_version']=='v1110.5');text=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('identity-revision-checkpoint-panel' in text and '/api/cognition/identity-revision-checkpoint' in text)
 print('{"passed":8,"total":8,"suite":"v1110.5"}')
if __name__=='__main__':main()
