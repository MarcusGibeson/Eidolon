from __future__ import annotations
import json,os,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.read_only_perception_governance_checkpoint import build_read_only_perception_governance_checkpoint
passed=0
def req(x):
 global passed
 if not x: raise AssertionError(f'check {passed+1} failed')
 passed+=1
with tempfile.TemporaryDirectory() as td:
 t=Path(td); r=build_read_only_perception_governance_checkpoint(t/'runtime'/'cognition',source_root=ROOT)
 req(r['contract_version']=='v1131.9'); req(r['ok'] and r['status']=='ready_for_desktop_verification'); req(r['passed']==r['total']==18); req(all(x['status']=='pass' for x in r['checks'])); req(not r['runtime_mutated'] and not r['source_modified']); req(r['intake']['contract_version']=='v1131.2'); req(r['deliberation']['contract_version']=='v1131.5'); req(r['integration']['contract_version']=='v1131.8')
 req(not any(r[k] for k in ('raw_file_content_exposed','raw_event_payload_exposed','message_text_exposed','prompt_exposed','provider_payload_exposed','hidden_reasoning_exposed')))
 req(not any(r[k] for k in ('filesystem_modified','browser_contacted','provider_contacted','message_sent','notification_created','approval_created','authorization_created','external_action_executed','promotion_performed','certification_performed','policy_applied','proposal_applied')))
 req(not r['consciousness_proven'] and not r['perception_signal_created_by_checkpoint'] and not r['perception_candidate_created_by_checkpoint'] and not r['perception_outcome_created_by_checkpoint'])
 env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(t/'cli'); p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'read-only-perception-governance-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60); req(p.returncode==0 and json.loads(p.stdout)['contract_version']=='v1131.9')
 os.environ['EIDOLON_DATA_DIR']=str(t/'api'); from conscious_agent.api_server import dispatch_api
 s,payload=dispatch_api('GET','/api/cognition/read-only-perception-governance-checkpoint'); req(s==200 and payload['data']['contract_version']=='v1131.9'); s,_=dispatch_api('POST','/api/cognition/read-only-perception-governance-checkpoint',body={}); req(s in (404,405))
 d=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(); req('read-only-perception-governance-checkpoint-panel' in d and '/api/cognition/read-only-perception-governance-checkpoint' in d and 'loadReadOnlyPerceptionGovernanceCheckpoint' in d)
 m=(ROOT/'conscious_agent/release_metadata.py').read_text(); q=re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"',m); req(bool(q) and tuple(map(int,q.groups())) >= (1131,9) and 'v1131.9 Read-Only Perception Governance Checkpoint' in (ROOT/'README_RELEASE_HISTORY.md').read_text())
 req(set(r['summary'])=={'perception_signal_count','candidate_count','deliberation_session_count','arbitration_outcome_count','perception_outcome_count','reliability_review_count','prioritized_failure_count','prioritized_change_count','deliberate_no_perception_count'}); req(r['desktop_verification_pending'])
print(json.dumps({'passed':passed,'total':18,'suite':'v1131.9'}))
