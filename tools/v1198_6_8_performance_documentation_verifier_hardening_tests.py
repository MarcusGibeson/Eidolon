from pathlib import Path
import copy
from conscious_agent.performance_documentation_verifier_hardening import *
from conscious_agent.performance_documentation_verifier_hardening import _digest
from conscious_agent.performance_documentation_verifier_hardening_checkpoint import build_performance_documentation_verifier_hardening_checkpoint
ROOT=Path(__file__).resolve().parents[1];passed=0
def req(x):
 global passed
 assert x;passed+=1
d=lambda s:_digest(s);snap=d('s');ctx=d('c');arch=d('a');docs=d('d');reg=d('r');freeze=d('f')
p=create_hardening_plan(plan_id='p',snapshot_digest=snap,context_digest=ctx,architecture_digest=arch,documentation_digest=docs,verifier_registry_digest=reg,freeze_review_digest=freeze)
rows=[];prior=''
for i,c in enumerate(EVIDENCE_CLASSES,1):
 o='inherited_debt' if c=='fixture_overlap' else 'pass';r=create_evidence(evidence_id=f'e{i}',evidence_class=c,outcome=o,owner='owner',sequence=i,observed_ms=i,budget_ms=100,artifact_digest=d(c),receipt_digest=d(c+'r'),prior_receipt_digest=prior,debt_id='debt' if o=='inherited_debt' else '');rows.append(r);prior=r['receipt_digest']
a=assess_hardening(p,rows,current_snapshot_digest=snap,current_context_digest=ctx,current_architecture_digest=arch,current_documentation_digest=docs,current_verifier_registry_digest=reg,current_freeze_review_digest=freeze)
for x in [a['status']=='ready',a['evidence_count']==8,a['evidence_class_count']==8,a['inherited_debt_count']==1,a['global_profile_pass_claimed'] is False,a['current_health_pass'] is True,a['profiling_executed'] is False,a['verifier_executed'] is False,a['files_moved'] is False,a['files_deleted'] is False,a['modules_merged'] is False,a['imports_rewritten'] is False,a['source_modified'] is False,a['runtime_mutated'] is False,a['authority_state']=='separate_not_granted']:req(x)
def blocked(modp=None,modrows=None):
 pp=copy.deepcopy(p);rr=copy.deepcopy(rows)
 if modp:modp(pp)
 if modrows:modrows(rr)
 return assess_hardening(pp,rr,current_snapshot_digest=snap,current_context_digest=ctx,current_architecture_digest=arch,current_documentation_digest=docs,current_verifier_registry_digest=reg,current_freeze_review_digest=freeze)['status']=='blocked'
cases=[lambda x:x.update(snapshot_digest=d('x')),lambda x:x.update(context_digest=d('x')),lambda x:x.update(architecture_digest=d('x')),lambda x:x.update(documentation_digest=d('x')),lambda x:x.update(verifier_registry_digest=d('x')),lambda x:x.update(freeze_review_digest=d('x')),lambda x:x.update(global_profile_pass_claimed=True),lambda x:x.update(profiling_executed=True),lambda x:x.update(verifier_executed=True),lambda x:x.update(source_modified=True),lambda x:x.update(runtime_mutated=True),lambda x:x.update(authority_state='granted')]
for f in cases:req(blocked(modp=f))
rowcases=[lambda r:r[0].update(evidence_class='bad'),lambda r:r[0].update(outcome='bad'),lambda r:r[0].update(owner=''),lambda r:r[0].update(observed_ms=200,budget_ms=100),lambda r:r[1].update(prior_receipt_digest=''),lambda r:r.append(copy.deepcopy(r[0])),lambda r:r[0].update(global_profile_pass_claimed=True),lambda r:r[0].update(files_deleted=True),lambda r:r[0].update(authority_state='granted'),lambda r:r[0].update(prompt='x')]
for f in rowcases:req(blocked(modrows=f))
cp=build_performance_documentation_verifier_hardening_checkpoint(source_root=ROOT)
for x in [cp['ok'],cp['contract_version']=='v1198.8',cp['read_only'],cp['post_available'] is False,cp['evidence_class_count']==8,cp['global_profile_pass_claimed'] is False,cp['source_unchanged'],cp['runtime_mutated'] is False,cp['authority_granted'] is False]:req(x)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text(encoding='utf-8');req('v1198.8' in t);req('v1198.9' in t)
rel=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8');req(rel.count('v1198_6_8_performance_documentation_verifier_hardening_tests.py')==1);req(rel.count('v1198.8-performance-documentation-verifier-hardening')==1)
print(f'v1198.6-v1198.8: {passed}/{passed} PASS')
