from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
from conscious_agent.deliberative_option_records import DeliberativeOptionStore
from conscious_agent.deliberative_option_arbitration import DeliberativeOptionArbitrator
from conscious_agent.deliberative_continuity_checkpoint import build_deliberative_continuity_checkpoint
ROOT=Path(__file__).resolve().parents[1]
def main():
 checks=[]
 def check(name,ok): checks.append((name,bool(ok))); print(('PASS' if ok else 'FAIL'),name)
 with tempfile.TemporaryDirectory() as td:
  runtime=Path(td)/'runtime'; runtime.mkdir(); clock=lambda:'2026-07-28T12:00:00.000Z'; store=DeliberativeOptionStore(runtime,clock=clock); arb=DeliberativeOptionArbitrator(runtime,clock=clock)
  r=store.register('r1',origin_type='unresolved_conflict',origin_id='conflict-1',intended_outcome_digest='z'*64,risk_score=.4,reversibility=.8); oid=r['result']['option_id']; arb.compare('c1',option_ids=[oid],missing_evidence=True)
  before={p.name:p.read_bytes() for p in runtime.glob('*.json')}; report=build_deliberative_continuity_checkpoint(runtime,source_root=ROOT); after={p.name:p.read_bytes() for p in runtime.glob('*.json')}
  check('checkpoint_ready',report['ok'] and report['contract_version']=='v1114.2')
  check('read_only',before==after and not report['runtime_mutated'])
  check('lineage_check',next(x for x in report['checks'] if x['id']=='option_persistence_lineage')['status']=='pass')
  check('missing_evidence_check',next(x for x in report['checks'] if x['id']=='missing_evidence_unknown')['status']=='pass')
  check('authority_separation',not any(report[k] for k in ('decision_committed','intention_formed','proposal_created','approval_granted','authorization_granted','external_action_executed')))
  check('privacy_boundary',not report['raw_messages_exposed'] and not report['hidden_reasoning_exposed'])
  check('desktop_pending',report['desktop_verification_status']=='pending')
  env=dict(__import__('os').environ); env['EIDOLON_DATA_DIR']=str(Path(td)/'cli-data'); proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'deliberative-continuity-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True); check('cli_read_only_surface',proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1114.2')
  from conscious_agent.api_server import dispatch_api
  status,payload=dispatch_api('GET','/api/cognition/deliberative-continuity-checkpoint')
  data=payload.get('data',payload); check('get_only_api_surface',status==200 and data.get('contract_version')=='v1114.2')
  source=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8'); check('dashboard_surface','deliberative-continuity-checkpoint' in source)
 print(f'{sum(x for _,x in checks)}/{len(checks)} passed'); return 0 if all(x for _,x in checks) else 1
if __name__=='__main__': raise SystemExit(main())
