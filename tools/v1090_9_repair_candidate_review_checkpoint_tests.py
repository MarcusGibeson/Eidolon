from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-9-runtime-')
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server, dashboard, release_metadata, post_review_development_verify as verify
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import repair_candidate_verification_evidence as evidence
import repair_candidate_lineage as lineage
import repair_candidate_review_checkpoint as checkpoint

PRIVATE_FINDING='PRIVATE_FINDING_1090_9'; PRIVATE_LABEL='PRIVATE_LABEL_1090_9'; PRIVATE_REF='PRIVATE_REFERENCE_1090_9'; PRIVATE_REVIEW='PRIVATE_REVIEW_NOTE_1090_9'; PRIVATE_VERIFY='PRIVATE_VERIFY_NOTE_1090_9'; PRIVATE_LINEAGE='PRIVATE_LINEAGE_NOTE_1090_9'
def require(v,m):
 if not v: raise AssertionError(m)
def area(r,n): return next(x for x in r['areas'] if x['name']==n)
def source_digest():
 h=hashlib.sha256()
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
   h.update(p.relative_to(ROOT).as_posix().encode()); h.update(b'\0'); h.update(p.read_bytes()); h.update(b'\0')
 return h.hexdigest()
def fixture(two=False):
 s=create_conversation_session('Candidate checkpoint fixture',select_session=False)
 e=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
 f=finding.create_evaluation_finding(finding_title=PRIVATE_FINDING,finding_details='PRIVATE_DETAILS_1090_9',issue_domain='session_continuity',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
 r=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256='A'*64,source_manifest_sha256='B'*64,evidence_digest='C'*64,label=PRIVATE_LABEL,private_reference=PRIVATE_REF,expected_revision=f['revision'],operator_confirmed=True); c=r['candidates'][0]
 rv=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='artifact_integrity',review_outcome='reviewing',evidence_digest='D'*64,note=PRIVATE_REVIEW,expected_revision=r['finding_revision'],operator_confirmed=True)
 ev=evidence.record_repair_candidate_verification_evidence(f['finding_id'],c['candidate_id'],evidence_kind='focused_suite',result='pass',evidence_digest='E'*64,passed_checks=5,total_checks=5,suite_count=1,source_tree_unchanged=True,note=PRIVATE_VERIFY,expected_revision=rv['finding_revision'],operator_confirmed=True)
 c2=None; latest=ev['finding_revision']
 if two:
  r2=registration.register_repair_candidate(f['finding_id'],candidate_kind='patch_artifact',artifact_sha256='F'*64,source_manifest_sha256='1'*64,evidence_digest='2'*64,label='PRIVATE_SECOND_LABEL',private_reference='PRIVATE_SECOND_REFERENCE',expected_revision=latest,operator_confirmed=True); c2=r2['candidates'][-1]; latest=r2['finding_revision']
  ln=lineage.link_repair_candidate_lineage(f['finding_id'],predecessor_candidate_id=c['candidate_id'],successor_candidate_id=c2['candidate_id'],relation_kind='supersedes',evidence_digest='3'*64,note=PRIVATE_LINEAGE,expected_revision=latest,operator_confirmed=True); latest=ln['finding_revision']
 return f,c,c2,latest

def test_checkpoint_contract_and_areas():
 r=checkpoint.build_repair_candidate_review_checkpoint(); require(r['checkpoint_status']=='ready_for_operator_candidate_review','status'); require(r['area_count']==checkpoint.CHECKPOINT_AREA_COUNT==15,'areas'); require(len(r['contract_digest'])==64 and len(r['areas_digest'])==64,'digests')
def test_findings_checkpoint_foundation():
 r=checkpoint.build_repair_candidate_review_checkpoint(); m=area(r,'evaluation_findings_foundation')['metrics']; require(m['checkpoint_status']=='ready_for_operator_finding_review' and m['area_count']==15,'foundation')
def test_protocol_stops_at_testing():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'repair_candidate_review_protocol')['metrics']; require(m['most_favorable_review_state']=='acceptable_for_testing' and not m['application_approval_state_exists'],'protocol')
def test_selected_candidate_is_redacted():
 f,c,_,_=fixture(); r=checkpoint.build_repair_candidate_review_checkpoint(finding_id=f['finding_id'],candidate_id=c['candidate_id']); enc=json.dumps(r,sort_keys=True); require(r['selected_candidate_status']=='available','selection')
 for secret in (PRIVATE_FINDING,PRIVATE_LABEL,PRIVATE_REF,PRIVATE_REVIEW,PRIVATE_VERIFY): require(secret not in enc,secret)
 require(not checkpoint.repair_candidate_review_checkpoint_contains_private_fields(r),'private fields')
def test_missing_and_incomplete_selection_are_bounded():
 a=checkpoint.build_repair_candidate_review_checkpoint(finding_id='eval_finding_20000101T000000_000000000000',candidate_id='repair_candidate_0000000000000000'); require(a['selected_candidate_status']=='not_found','missing')
 b=checkpoint.build_repair_candidate_review_checkpoint(finding_id='eval_finding_20000101T000000_000000000000'); require(b['selected_candidate_status']=='incomplete_selection','incomplete')
def test_registration_is_immutable_and_operator_supplied():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'immutable_candidate_registration')['metrics']; require(m['artifact_sha256_required'] and m['immutable_artifact_identity'],'identity'); require(not m['automatic_registration'] and not m['candidate_generation'],'automation')
def test_review_has_no_apply_state():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'explicit_candidate_review_findings')['metrics']; require(m['most_favorable_review_state']=='acceptable_for_testing' and not m['application_approval_state_exists'],'review'); require(not m['automatic_review'],'auto')
def test_verification_evidence_never_executes_tests():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'deterministic_verification_evidence')['metrics']; require(m['maximum_evidence']==32 and not m['automatic_test_execution'] and m['source_tree_immutability_recorded'],'evidence')
def test_comparison_declares_no_winner():
 f,a,b,_=fixture(two=True); r=checkpoint.build_repair_candidate_review_checkpoint(finding_id=f['finding_id'],comparison_candidate_ids=[a['candidate_id'],b['candidate_id']]); m=area(r,'bounded_candidate_comparison')['metrics']; require(m['comparison_status']=='available' and m['compared_candidate_count']==2,'comparison')
 for k in ('candidates_ranked','winner_selected','priority_assigned','statistical_significance_claimed','release_recommendation_produced'): require(m[k] is False,k)
def test_lineage_preserves_history_without_selection():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'immutable_supersession_lineage')['metrics']; require(m['cycle_prevention'] and m['ambiguous_successor_prevention'] and m['predecessor_history_preserved'],'lineage'); require(not m['successor_auto_selected'],'selection')
def test_console_javascript_and_narrow_layout():
 r=checkpoint.build_repair_candidate_review_checkpoint(); require(area(r,'operator_candidate_review_console')['metrics']['read_routes_only_for_evidence'],'console'); html=dashboard.render_repair_candidate_review_console(); require('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow'); match=re.search(r'<script>(.*?)</script>',html,re.S); require(match,'script'); p=Path(tempfile.mkdtemp())/'candidate.js'; p.write_text(match.group(1)); cp=subprocess.run(['node','--check',str(p)],capture_output=True,text=True,timeout=30); require(cp.returncode==0,cp.stderr)
def test_export_is_client_side_and_content_free():
 f,c,_,_=fixture(); r=checkpoint.build_repair_candidate_review_checkpoint(finding_id=f['finding_id'],candidate_id=c['candidate_id']); m=area(r,'privacy_safe_candidate_review_export')['metrics']; require(m['selected_export_status']=='available' and len(m['selected_document_sha256'])==64 and not m['server_file_written'],'export')
def test_long_session_window_contract():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'long_session_candidate_windows')['metrics']; require(m['initial_window_limit']==80 and m['earlier_window_limit']==120 and m['maximum_candidates']==512 and m['complete_candidate_rows_only'],'window')
def test_existing_mutations_require_confirmation_and_revision():
 f,c,_,rev=fixture()
 try: review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='source_scope',review_outcome='needs_changes',expected_revision=rev,operator_confirmed=False)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('unconfirmed')
 updated=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='source_scope',review_outcome='needs_changes',expected_revision=rev,operator_confirmed=True)
 try: review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='privacy_boundary',review_outcome='rejected',expected_revision=rev,operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('stale')
 require(updated['finding_revision']==rev+1,'revision')
def test_checkpoint_is_provider_free_and_no_execution():
 r=checkpoint.build_repair_candidate_review_checkpoint()
 for k in ('provider_invoked','generation_invoked','automatic_provider_request','automatic_test_execution','automatic_replay','automatic_resend'): require(r[k] is False,k)
 source=(AGENT/'repair_candidate_review_checkpoint.py').read_text(); require('local_model' not in source and 'provider_readiness' not in source,'provider dependency')
def test_operator_authority_is_explicit():
 m=area(checkpoint.build_repair_candidate_review_checkpoint(),'operator_authority_and_checkpoint_boundary')['metrics']; require(m['testing_decision']=='operator_only' and m['application_decision']=='operator_only' and m['release_decision']=='operator_only','decisions')
 for k in ('automatic_test_execution','automatic_task_created','automatic_work_item_created','candidate_ranked','winner_selected','patch_generated','patch_reviewed_automatically','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','model_management','provider_switching','generation_settings_changed','checkpoint_writes_state'): require(m[k] is False,k)
def test_api_get_route():
 f,c,_,_=fixture(); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-review-checkpoint',{'finding_id':[f['finding_id']],'candidate_id':[c['candidate_id']]}); require(status==200 and payload['data']['type']=='desktop_alpha_repair_candidate_review_checkpoint','GET')
def test_no_post_route():
 source=(AGENT/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-review-checkpoint"]' not in post,'POST'); require('GET /api/conversation/repair-candidate-review-checkpoint' in source,'index')
def test_private_detector():
 require(checkpoint.repair_candidate_review_checkpoint_contains_private_fields({'private_note':'secret'}),'note'); require(checkpoint.repair_candidate_review_checkpoint_contains_private_fields({'document':'secret'}),'document'); require(not checkpoint.repair_candidate_review_checkpoint_contains_private_fields(checkpoint.build_repair_candidate_review_checkpoint()),'false positive')
def test_deterministic_and_immutable():
 before=source_digest(); a=checkpoint.build_repair_candidate_review_checkpoint(); b=checkpoint.build_repair_candidate_review_checkpoint(); after=source_digest(); require(a['contract_digest']==b['contract_digest'] and a['areas_digest']==b['areas_digest'],'determinism'); require(before==after,'source mutation')
def test_release_metadata_and_guides():
 require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.'))>=(1090,9),'version'); require(release_metadata.RUNTIME_VERSION_TAG==f"v{release_metadata.RUNTIME_VERSION}",'tag')
 for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
  text=(ROOT/name).read_text(); require('v1090.9' in text,f'{name} checkpoint'); require('v1089.9' in text,f'{name} finding checkpoint')
def test_registration_is_exact_and_bounded():
 names=[s.name for s in verify.SUITES]; name='v1090.9-desktop-alpha-repair-candidate-review-checkpoint'; require(names.count(name)==1,'registration'); require(names.index(name)<names.index('v1090.8-long-session-candidate-review'),'order'); historical=verify.SUITES[names.index(name):]; core=[s for s in historical if 'core' in s.profiles]; full=[s for s in historical if 'full' in s.profiles]; require(len(core)==102,f'historical core {len(core)}'); require(len(full)==119,f'historical full {len(full)}')
def test_source_only_privacy():
 forbidden={'data/projects.json','data/tasks.json','data/memories.json','data/conversations.json','data/conversation_evaluation_findings','.git','.venv','venv'}; relative={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')}; require(not(forbidden&relative),str(forbidden&relative))
 for p in ROOT.rglob('*'):
  rel=p.relative_to(ROOT); require('__pycache__' not in rel.parts,'cache'); require(p.suffix not in {'.pyc','.pyo','.zip'},f'artifact {rel}')
def test_top_level_boundaries():
 r=checkpoint.build_repair_candidate_review_checkpoint(); require(r['read_only'] and r['content_free'] and r['redacted'] and not r['writes_state'],'boundary')
 for k in ('automatic_test_execution','automatic_task_created','automatic_work_item_created','candidate_ranked','winner_selected','patch_generated','patch_reviewed_automatically','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified'): require(r[k] is False,k)

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.9-desktop-alpha-repair-candidate-review-checkpoint','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
