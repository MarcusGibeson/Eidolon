from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
def req(v,m='failed'):
 if not v:raise AssertionError(m)
def snap():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
def main():
 base=Path(tempfile.mkdtemp());root=base/'runtime'/'cognition';before=snap();from conscious_agent.behavioral_evidence_continuity_checkpoint import build_behavioral_evidence_continuity_checkpoint
 c=build_behavioral_evidence_continuity_checkpoint(root,source_root=ROOT);req(before==snap());req(c['contract_version']=='v1112.2' and c['runtime_mutated'] is False);req(all(x['status']=='pass' for x in c['checks']));req(not c['hidden_reasoning_exposed'] and not c['authorization_granted'])
 from conscious_agent.api_server import dispatch_api;os.environ['EIDOLON_DATA_DIR']=str(base/'runtime');status,p=dispatch_api('GET','/api/cognition/behavioral-evidence-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1112.2');status2,_=dispatch_api('POST','/api/cognition/behavioral-evidence-checkpoint',body={});req(status2!=200)
 run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'behavioral-evidence-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1112.2');dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('behavioral-evidence-checkpoint-panel' in dash and '/api/cognition/behavioral-evidence-checkpoint' in dash);print('{"passed":10,"total":10,"suite":"v1112.2"}')
if __name__=='__main__':main()
