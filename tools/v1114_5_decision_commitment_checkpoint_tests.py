from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
from conscious_agent.decision_commitment_checkpoint import build_decision_commitment_checkpoint
ROOT=Path(__file__).resolve().parents[1]
def main():
 checks=[]
 def c(n,v):checks.append((n,bool(v)));print(('PASS' if v else 'FAIL'),n)
 with tempfile.TemporaryDirectory() as td:
  runtime=Path(td)/'runtime';runtime.mkdir(); before={p.name:p.read_bytes() for p in runtime.glob('*.json')}; report=build_decision_commitment_checkpoint(runtime,source_root=ROOT); after={p.name:p.read_bytes() for p in runtime.glob('*.json')}
  c('checkpoint_ready',report['ok'] and report['contract_version']=='v1114.5'); c('read_only',before==after and not report['runtime_mutated']); c('lineage_check',next(x for x in report['checks'] if x['id']=='commitment_persistence_lineage')['status']=='pass'); c('missing_feedback_check',next(x for x in report['checks'] if x['id']=='missing_feedback_unknown')['status']=='pass'); c('authority_separation',not any(report[k] for k in ('intention_formed','proposal_created','approval_granted','authorization_granted','external_action_executed'))); c('privacy_boundary',not report['raw_messages_exposed'] and not report['hidden_reasoning_exposed']); c('desktop_pending',report['desktop_verification_status']=='pending')
  env=dict(__import__('os').environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'decision-commitment-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);c('cli_read_only_surface',proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1114.5')
  from conscious_agent.api_server import dispatch_api
  status,payload=dispatch_api('GET','/api/cognition/decision-commitment-checkpoint');data=payload.get('data',payload);c('get_only_api_surface',status==200 and data.get('contract_version')=='v1114.5'); source=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();c('dashboard_surface','decision-commitment-checkpoint' in source)
 print(f'{sum(v for _,v in checks)}/{len(checks)} passed');return 0 if all(v for _,v in checks) else 1
if __name__=='__main__':raise SystemExit(main())
