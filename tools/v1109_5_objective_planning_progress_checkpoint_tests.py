from pathlib import Path
import tempfile,os,subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 root=Path(tempfile.mkdtemp())/'cognition';from conscious_agent.objective_planning_progress_checkpoint import build_objective_planning_progress_checkpoint;c=build_objective_planning_progress_checkpoint(root,source_root=ROOT);from conscious_agent.api_server import dispatch_api;os.environ['EIDOLON_DATA_DIR']=str(root.parent);status,p=dispatch_api('GET','/api/cognition/objective-planning-progress-checkpoint');env=dict(os.environ);q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'objective-planning-progress-checkpoint','--json'],capture_output=True,text=True,env=env,timeout=60);tests=[c['contract_version']=='v1109.5',c['runtime_mutated'] is False,c['action_authority_changed'] is False,status==200,(p.get('data') or {}).get('contract_version')=='v1109.5',q.returncode==0,json.loads(q.stdout)['contract_version']=='v1109.5','objective-planning-progress-checkpoint-panel' in (ROOT/'conscious_agent/dashboard_first_use.py').read_text(),c['consciousness_claimed'] is False]
 print(f"v1109.5 objective planning progress checkpoint: {sum(tests)}/{len(tests)} passed");return 0 if all(tests) else 1
if __name__=='__main__':raise SystemExit(main())
