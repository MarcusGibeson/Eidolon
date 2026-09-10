from pathlib import Path
import tempfile, subprocess, sys, json, os
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.deliberative_decision_review_checkpoint import build_deliberative_decision_review_checkpoint
from conscious_agent.api_server import dispatch_api

def c(name,ok):
 print(('PASS' if ok else 'FAIL'),name)
 if not ok: raise SystemExit(1)
with tempfile.TemporaryDirectory() as td:
 runtime=Path(td)/'runtime';runtime.mkdir(); before={p.name:p.read_bytes() for p in runtime.glob('*.json')}; report=build_deliberative_decision_review_checkpoint(runtime,source_root=ROOT); after={p.name:p.read_bytes() for p in runtime.glob('*.json')}
 c('checkpoint_ready',report['ok'] and report['contract_version']=='v1114.8'); c('read_only',before==after and not report['runtime_mutated']); c('lineage_check',next(x for x in report['checks'] if x['id']=='decision_to_intention_lineage')['status']=='pass'); c('missing_feedback_check',next(x for x in report['checks'] if x['id']=='missing_feedback_unknown')['status']=='pass'); c('trigger_restraint',next(x for x in report['checks'] if x['id']=='reconsideration_trigger_restraint')['status']=='pass'); c('authority_separation',not any(report[k] for k in ('intention_formed','proposal_created','approval_granted','authorization_granted','external_action_executed'))); c('privacy_boundary',not report['raw_messages_exposed'] and not report['hidden_reasoning_exposed']); c('desktop_pending',report['desktop_verification_status']=='pending')
 env=dict(os.environ);env['EIDOLON_DATA_DIR']=str(Path(td)/'cli');proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'deliberative-decision-review-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True);c('cli_read_only_surface',proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1114.8')
 os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api');status,payload=dispatch_api('GET','/api/cognition/deliberative-decision-review-checkpoint');data=payload.get('data',payload);c('get_only_api_surface',status==200 and data.get('contract_version')=='v1114.8')
