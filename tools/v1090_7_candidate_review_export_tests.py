from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090c-export-'); os.environ['PYTHONDONTWRITEBYTECODE']='1'
import api_server, post_review_development_verify as verify
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import repair_candidate_verification_evidence as evidence
import repair_candidate_lineage as lineage
import repair_candidate_review_export as export

def require(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.suffix not in {'.pyc','.pyo'} and not any(x in p.parts for x in {'__pycache__','.git','.venv','venv'}): h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def fixture():
    s=create_conversation_session('Candidate export fixture',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
    f=finding.create_evaluation_finding(finding_title='PRIVATE_EXPORT_FINDING',finding_details='PRIVATE_EXPORT_DETAILS',issue_domain='provider_transport',severity='blocking',evaluation_id=e['evaluation_id'],operator_confirmed=True)
    r=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256='A'*64,source_manifest_sha256='B'*64,evidence_digest='C'*64,label='PRIVATE_EXPORT_LABEL',private_reference='PRIVATE_EXPORT_REFERENCE',expected_revision=f['revision'],operator_confirmed=True); c=r['candidates'][0]
    rv=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='artifact_integrity',review_outcome='reviewing',evidence_digest='D'*64,note='PRIVATE_EXPORT_REVIEW_NOTE',expected_revision=r['finding_revision'],operator_confirmed=True)
    ev=evidence.record_repair_candidate_verification_evidence(f['finding_id'],c['candidate_id'],evidence_kind='focused_suite',result='pass',evidence_digest='E'*64,passed_checks=9,total_checks=9,suite_count=1,source_tree_unchanged=True,note='PRIVATE_EXPORT_VERIFY_NOTE',expected_revision=rv['finding_revision'],operator_confirmed=True)
    r2=registration.register_repair_candidate(f['finding_id'],candidate_kind='patch_artifact',artifact_sha256='F'*64,source_manifest_sha256='1'*64,label='PRIVATE_SUCCESSOR_LABEL',expected_revision=ev['finding_revision'],operator_confirmed=True); c2=r2['candidates'][-1]
    li=lineage.link_repair_candidate_lineage(f['finding_id'],predecessor_candidate_id=c['candidate_id'],successor_candidate_id=c2['candidate_id'],relation_kind='replaces',evidence_digest='2'*64,note='PRIVATE_LINEAGE_NOTE',expected_revision=r2['finding_revision'],operator_confirmed=True)
    return f,c,c2,li

def test_export_is_deterministic_and_hash_bound():
    f,c,_,_=fixture(); a=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id']); b=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id']); require(a==b,'deterministic'); require(hashlib.sha256(a['document'].encode()).hexdigest()==a['document_sha256'],'hash')
def test_export_contains_bounded_review_evidence_and_lineage():
    f,c,c2,_=fixture(); r=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id']); d=r['review']; require(d['review_event_count']==1 and d['verification_evidence_count']==1,'evidence'); require(d['related_lineage_edge_count']==1 and d['related_lineage_edges'][0]['successor_candidate_id']==c2['candidate_id'],'lineage')
def test_export_excludes_all_private_values():
    f,c,_,_=fixture(); r=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id']); encoded=json.dumps(r,sort_keys=True)
    for secret in ('PRIVATE_EXPORT_FINDING','PRIVATE_EXPORT_DETAILS','PRIVATE_EXPORT_LABEL','PRIVATE_EXPORT_REFERENCE','PRIVATE_EXPORT_REVIEW_NOTE','PRIVATE_EXPORT_VERIFY_NOTE','PRIVATE_SUCCESSOR_LABEL','PRIVATE_LINEAGE_NOTE'): require(secret not in encoded,secret)
    require(not export.repair_candidate_review_export_contains_private_fields(r['review']),'private fields')
def test_export_has_explicit_exclusion_flags():
    f,c,_,_=fixture(); d=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id'])['review']
    for key in ('candidate_ranking_included','winner_selected','priority_included','statistical_significance_claimed','automatic_test_execution','automatic_task_created','automatic_work_item_created','patch_generated','patch_reviewed_automatically','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','private_labels_included','private_references_included','private_review_notes_included','private_verification_notes_included','private_lineage_notes_included','transcript_included','prompt_included','memory_content_included','provider_payload_included','credentials_included','vectors_included','hidden_reasoning_included','provider_invoked','generation_invoked'): require(d[key] is False,key)
def test_get_route_is_client_download_and_source_immutable():
    f,c,_,_=fixture(); before=tree_digest(); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-review-export',{'finding_id':[f['finding_id']],'candidate_id':[c['candidate_id']]}); d=payload['data']; require(status==200 and d['client_download_ready'],'route'); require(not d['server_file_written'] and not d['writes_state'],'write'); require(before==tree_digest(),'source')
def test_export_cannot_approve_apply_or_release():
    f,c,_,_=fixture(); d=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id'])['review']; require(d['testing_decision']=='operator_only' and d['application_decision']=='operator_only' and d['release_decision']=='operator_only','decision'); require(not d['approval_granted'] and not d['patch_applied'] and not d['release_certified'],'authority')
def test_filename_is_bounded_and_content_free():
    f,c,_,_=fixture(); r=export.build_repair_candidate_review_export(f['finding_id'],c['candidate_id']); require(r['filename']==f"{c['candidate_id']}_privacy_safe_candidate_review.json",'filename'); require('/' not in r['filename'] and '\\' not in r['filename'],'path')
def test_no_post_route_and_registration_are_exact():
    source=(ROOT/'conscious_agent/api_server.py').read_text(); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-review-export"]' not in post,'post'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.7-candidate-review-export')==1,'registration'); require(names.index('v1090.7-candidate-review-export')<names.index('v1090.6-operator-candidate-review-console'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1090.7-candidate-review-export','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
