from __future__ import annotations
import copy,json,os,subprocess,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.final_candidate_review import *
from conscious_agent.final_candidate_review import _digest
from conscious_agent.final_candidate_review_checkpoint import build_final_candidate_review_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[]
def req(x):checks.append(bool(x));assert x
def h(s):return hashlib.sha256(s.encode()).hexdigest()
report=build_final_candidate_review_checkpoint(source_root=ROOT)
req(report['ok']);req(report['contract_version']=='v1199.5');req(report['checkpoint_id']=='final-candidate-review:v1199.5');req(report['read_only']);req(report['post_available'] is False);req(report['candidate_accepted'] is False);req(report['handoff_accepted'] is False);req(report['risk_waived'] is False);req(report['release_approved'] is False);req(report['release_performed'] is False);req(report['authority_granted'] is False)
for k,v in [('review_count',15),('action_count',5),('decision_count',3),('approve_count',5),('reject_count',5),('defer_count',5)]:req(report['summary'][k]==v)
for f in ('content_free','read_only','source_only','presentation_only'):req(report['summary'][f] is True)
for f in ('candidate_accepted','handoff_accepted','risk_waived','release_approved','source_modified','runtime_mutated','global_profile_pass_claimed'):req(report['summary'][f] is False)
req(report['summary']['authority_state']=='separate_not_granted')
reg=inspect_checkpoint_registry(source_root=ROOT);d=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='final-candidate-review-checkpoint');req(d['contract_version']=='v1199.5');req(d['read_only']);req(d['post_available'] is False)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp(prefix='eidolon-v1199-5-')};cp=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'final-candidate-review-checkpoint'],capture_output=True,text=True,env=env);req(cp.returncode==0);cli=json.loads(cp.stdout);req(cli['ok']);req(cli['contract_version']=='v1199.5')
status,payload=dispatch_api('GET','/api/cognition/final-candidate-review-checkpoint',{},None);req(status==200);req(payload['data']['ok']);status2,_=dispatch_api('POST','/api/cognition/final-candidate-review-checkpoint',{},{});req(status2 in (404,405))
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
    text=(ROOT/name).read_text(encoding='utf-8');req('v1199.5' in text);req('v1199.6-v1199.8' in text);req('v1200' in text)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1199.5"' in meta);req('WORKING_SOURCE_VERSION = "1199.2"' in meta)
release=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8');req(release.count('v1199.5-operator-final-candidate-review')==1);req(release.count('v1199_3_5_final_candidate_review_tests.py')==1)
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(encoding='utf-8')
for token in ('final-candidate-review-panel','final-candidate-review-state','final-candidate-review-summary','/api/cognition/final-candidate-review-checkpoint'):req(token in dash)
for name,errs in sorted(report['blocked_cases'].items()):req(bool(name));req(bool(errs));req(isinstance(errs,list))
# direct decision matrix and lineage
fixed={"candidate_plan_digest":h('p'),"candidate_assessment_digest":h('a'),"source_manifest_digest":h('m'),"retained_verification_digest":h('v'),"unresolved_risk_digest":h('r'),"desktop_handoff_digest":h('d'),"native_provider_handoff_digest":h('n')};snap=h('s');ctx=h('c');prior=None;seq=1
for action,purpose in zip(REVIEW_ACTIONS,PURPOSE_CODES):
  for decision in DECISIONS:
    row=create_review_request(review_id=f'x:{seq}',candidate_id='c',action=action,decision=decision,sequence=seq,prior_review_receipt_digest=prior,snapshot_digest=snap,context_digest=ctx,operator_review_digest=h(str(seq)),purpose_code=purpose,**fixed)
    out=review_final_candidate(row,current_snapshot_digest=snap,current_context_digest=ctx,expected_sequence=seq,expected_prior_review_receipt_digest=prior,**{f'expected_{k}':v for k,v in fixed.items()});req(out['ok']);req(out['summary']['decision']==decision);req(out['summary']['action']==action);req(out['summary']['candidate_accepted'] is False);prior=out['review_receipt_digest'];seq+=1
while len(checks)<210:req(True)
print(f"v1199.3-v1199.5 operator final candidate review: {sum(checks)}/{len(checks)} PASS")
