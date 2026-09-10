from __future__ import annotations
import argparse, concurrent.futures, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-1-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_reproducibility as repro
import repair_candidate_registration as registration
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make():
 s=create_conversation_session('Candidate registration',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title='PRIVATE_V1090_FINDING',finding_details='PRIVATE_DETAILS',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
def register(f,**kw):
 return registration.register_repair_candidate(f['finding_id'],candidate_kind=kw.get('candidate_kind','source_archive'),artifact_sha256=kw.get('artifact_sha256','a'*64),source_manifest_sha256=kw.get('source_manifest_sha256','b'*64),evidence_digest=kw.get('evidence_digest','c'*64),label=kw.get('label','PRIVATE_CANDIDATE_LABEL'),private_reference=kw.get('private_reference','PRIVATE_CANDIDATE_REFERENCE'),expected_revision=kw.get('expected_revision',f['revision']),operator_confirmed=kw.get('operator_confirmed',True))

def test_registration_requires_confirmation_and_exact_revision():
 f=make()
 for confirmed,rev in ((False,f['revision']),(True,None),(True,f['revision']-1)):
  try:register(f,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('unguarded registration')

def test_artifact_sha_and_kind_are_validated():
 f=make()
 for kind,sha in (('moon','a'*64),('source_archive','not-sha')):
  try:register(f,candidate_kind=kind,artifact_sha256=sha)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('invalid identity accepted')

def test_registration_binds_immutable_identity_and_finding():
 f=make(); r=register(f); c=r['candidates'][0]; require(c['finding_id']==f['finding_id'] and c['artifact_sha256']=='A'*64 and c['source_manifest_sha256']=='B'*64,'identity'); require(r['immutable_artifact_identity'],'immutability')

def test_private_label_and_reference_are_digest_only_publicly():
 f=make(); r=register(f); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_CANDIDATE_LABEL' not in encoded and 'PRIVATE_CANDIDATE_REFERENCE' not in encoded,'private leak'); require(r['candidates'][0]['private_label_digest'] and r['candidates'][0]['private_reference_digest'],'digests'); require(not registration.repair_candidate_registration_contains_private_fields(r),'private key')

def test_private_record_retains_operator_values():
 f=make(); r=register(f); private=finding.load_evaluation_finding_private(f['finding_id']); row=private['repair_candidate_review_records'][0]; require(row['private_label']=='PRIVATE_CANDIDATE_LABEL' and row['private_reference']=='PRIVATE_CANDIDATE_REFERENCE','private missing'); require(row['candidate_id']==r['candidates'][0]['candidate_id'],'id')

def test_registration_records_reproducibility_status():
 f=make(); rr=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='same_environment',expected_revision=f['revision'],operator_confirmed=True); current=finding.load_evaluation_finding(f['finding_id']); r=register(current,expected_revision=rr['finding_revision']); require(r['candidates'][0]['reproducibility_status_at_registration']=='confirmed','repro status')

def test_duplicate_registration_is_idempotent():
 f=make(); first=register(f); duplicate=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256='a'*64,source_manifest_sha256='b'*64,evidence_digest='c'*64,label='different',private_reference='different',expected_revision=first['finding_revision'],operator_confirmed=True); require(duplicate['duplicate_registration'] and duplicate['candidate_count']==1 and duplicate['finding_revision']==first['finding_revision'],'duplicate mutated')

def test_same_revision_race_allows_one_writer():
 f=make()
 def call(sha):
  try:return register(f,artifact_sha256=sha,expected_revision=f['revision'])['candidate_count']
  except finding.EvaluationFindingError:return 'stale'
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: results=list(ex.map(call,['1'*64,'2'*64]))
 require(results.count('stale')==1 and len([x for x in results if isinstance(x,int)])==1,'race')

def test_registration_is_readable_through_get_api():
 f=make(); r=register(f); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-registrations',{'finding_id':[f['finding_id']]}); require(status==200 and payload['data']['candidate_count']==1 and payload['data']['candidates'][0]['candidate_id']==r['candidates'][0]['candidate_id'],'GET')

def test_registration_is_explicit_through_existing_post_route():
 f=make(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'register_review_candidate','finding_id':f['finding_id'],'candidate_kind':'test_fixture','artifact_sha256':'d'*64,'expected_revision':f['revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['candidate_count']==1,'POST')

def test_no_candidate_generation_or_protected_authority():
 f=make(); r=register(f)
 for k in ('candidate_generated','automatic_task_created','automatic_work_item_created','autonomous_prioritization','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','provider_invoked','writes_state'): require(r[k] is False,k)

def test_source_only_and_registration_order():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.1-immutable-candidate-registration')==1 and names.index('v1090.1-immutable-candidate-registration')<names.index('v1090.0-repair-candidate-review-protocol'),'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.1-immutable-candidate-registration','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
