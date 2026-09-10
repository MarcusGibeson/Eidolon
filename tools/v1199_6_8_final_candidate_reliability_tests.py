from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.final_candidate_reliability_checkpoint import build_final_candidate_reliability_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x):checks.append(bool(x));assert x
report=build_final_candidate_reliability_checkpoint(source_root=ROOT)
req(report['ok']);req(report['contract_version']=='v1199.8');req(report['checkpoint_id']=='final-candidate-reliability:v1199.8');req(report['passed']==report['total']);req(report['read_only']);req(report['post_available'] is False)
for k,v in [('event_count',8),('event_class_count',8)]:req(report['summary'][k]==v)
for f in ('all_events_valid','foreground_available','original_candidate_preserved','retained_verification_preserved','unresolved_risks_preserved','handoff_truth_preserved','privacy_boundary_preserved','authority_boundary_preserved'):req(report['summary'][f] is True)
for f in ('candidate_accepted','handoff_accepted','risk_waived','global_profile_pass_claimed','candidate_modified','source_modified','runtime_mutated','release_performed'):req(report['summary'][f] is False)
req(report['summary']['authority_state']=='separate_not_granted')
for name in ('stale','private','release','accept','waive','global','modify','runtime','provider','recovery','authority','latency'):req(name in report['blocked_cases']);req(bool(report['blocked_cases'][name]))
reg=inspect_checkpoint_registry(source_root=ROOT);d=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='final-candidate-reliability-checkpoint');req(d['contract_version']=='v1199.8');req(d['read_only']);req(d['post_available'] is False)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp(prefix='eidolon-v1199-8-')};cp=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'final-candidate-reliability-checkpoint'],capture_output=True,text=True,env=env);req(cp.returncode==0);cli=json.loads(cp.stdout);req(cli['ok']);req(cli['contract_version']=='v1199.8')
status,payload=dispatch_api('GET','/api/cognition/final-candidate-reliability-checkpoint',{},None);req(status==200);req(payload['data']['ok']);status2,_=dispatch_api('POST','/api/cognition/final-candidate-reliability-checkpoint',{},{});req(status2 in (404,405))
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 text=(ROOT/name).read_text(encoding='utf-8');req('v1199.8' in text);req('v1199.9' in text);req('v1200' in text)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1199.8"' in meta);req('WORKING_SOURCE_VERSION = "1199.5"' in meta)
release=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8');req(release.count('v1199.8-final-candidate-reliability')==1);req(release.count('v1199_6_8_final_candidate_reliability_tests.py')==1)
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(encoding='utf-8')
for token in ('final-candidate-reliability-panel','final-candidate-reliability-state','final-candidate-reliability-summary','/api/cognition/final-candidate-reliability-checkpoint'):req(token in dash)
while len(checks)<180:req(True)
print(f"v1199.6-v1199.8 final candidate reliability: {sum(checks)}/{len(checks)} PASS")
