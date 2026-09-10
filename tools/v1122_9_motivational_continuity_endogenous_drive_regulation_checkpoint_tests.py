from __future__ import annotations
import json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.motivational_continuity_endogenous_drive_regulation_checkpoint import build_motivational_continuity_endogenous_drive_regulation_checkpoint
passed=0
def require(condition):
 global passed
 if not condition: raise AssertionError(f"check {passed+1} failed")
 passed+=1
with tempfile.TemporaryDirectory() as td:
 runtime=Path(td)/"runtime"
 before={p.relative_to(ROOT).as_posix():(p.stat().st_size,p.stat().st_mtime_ns) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 report=build_motivational_continuity_endogenous_drive_regulation_checkpoint(runtime,source_root=ROOT)
 after={p.relative_to(ROOT).as_posix():(p.stat().st_size,p.stat().st_mtime_ns) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 require(report['contract_version']=='v1122.9')
 require(report['ok'] and report['status']=='ready_for_desktop_verification')
 require(report['check_count']==18 and len(report['checks'])==18)
 require(all(x['status']=='pass' for x in report['checks']))
 require(report['runtime_external'] and not report['runtime_mutated'])
 require(before==after and not report['source_modified'])
 require(report['motivational_continuity_intake']['contract_version']=='v1122.2')
 require(report['motivational_drive_deliberation']['contract_version']=='v1122.5')
 require(report['motivational_continuity_review']['contract_version']=='v1122.8')
 require(not any(report[k] for k in ('raw_messages_exposed','raw_content_exposed','prompts_exposed','provider_payloads_exposed','motivation_text_exposed','hidden_reasoning_exposed','private_content_exposed')))
 require(not any(report[k] for k in ('attention_selected','initiative_created','message_sent','notification_created','provider_contacted','browsing_performed','policy_applied')))
 require(not any(report[k] for k in ('proposal_created','proposal_applied','approval_granted','authorization_granted','external_action_executed','release_approved','release_promoted','release_certified')))
 env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(Path(td)/'cli-runtime')
 cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'motivational-continuity-endogenous-drive-regulation-checkpoint','--json'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60)
 require(cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1122.9')
 os.environ['EIDOLON_DATA_DIR']=str(Path(td)/'api-runtime')
 from conscious_agent.api_server import dispatch_api
 status,payload=dispatch_api('GET','/api/cognition/motivational-continuity-endogenous-drive-regulation-checkpoint')
 require(status==200 and (payload.get('data') or {})['contract_version']=='v1122.9')
 post,_=dispatch_api('POST','/api/cognition/motivational-continuity-endogenous-drive-regulation-checkpoint',body={})
 require(post in (404,405))
 dashboard=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(encoding='utf-8')
 require('motivational-continuity-endogenous-drive-regulation-checkpoint-panel' in dashboard and '/api/cognition/motivational-continuity-endogenous-drive-regulation-checkpoint' in dashboard)
 metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding='utf-8')
 wm=re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"',metadata); pm=re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"',metadata)
 working=tuple(map(int,wm.groups())) if wm else (0,0); previous=tuple(map(int,pm.groups())) if pm else (0,0)
 require(working>=(1122,9) and previous>=(1122,8) and previous<=working and 'METADATA_SCHEMA_VERSION = "1"' in metadata)
 docs='\n'.join((ROOT/n).read_text(encoding='utf-8') for n in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md'))
 require('v1122.9' in docs and 'v1123' in docs)
print(json.dumps({'passed':passed,'total':18,'suite':'v1122.9'}))
