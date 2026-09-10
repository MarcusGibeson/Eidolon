from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090c-console-'); os.environ['PYTHONDONTWRITEBYTECODE']='1'
import api_server, dashboard, post_review_development_verify as verify
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_review as review
import repair_candidate_verification_evidence as evidence
import repair_candidate_lineage as lineage
import repair_candidate_console as console

def require(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.suffix not in {'.pyc','.pyo'} and not any(x in p.parts for x in {'__pycache__','.git','.venv','venv'}): h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def fixture():
    s=create_conversation_session('Candidate console fixture',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
    f=finding.create_evaluation_finding(finding_title='PRIVATE_CONSOLE_FINDING',finding_details='PRIVATE_CONSOLE_DETAILS',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
    r=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256='A'*64,source_manifest_sha256='B'*64,evidence_digest='C'*64,label='PRIVATE_CANDIDATE_LABEL',private_reference='PRIVATE_CANDIDATE_REFERENCE',expected_revision=f['revision'],operator_confirmed=True)
    c=r['candidates'][0]
    rv=review.record_repair_candidate_review(f['finding_id'],c['candidate_id'],review_area='artifact_integrity',review_outcome='reviewing',evidence_digest='D'*64,note='PRIVATE_REVIEW_NOTE',expected_revision=r['finding_revision'],operator_confirmed=True)
    ev=evidence.record_repair_candidate_verification_evidence(f['finding_id'],c['candidate_id'],evidence_kind='focused_suite',result='pass',evidence_digest='E'*64,passed_checks=3,total_checks=3,suite_count=1,source_tree_unchanged=True,note='PRIVATE_VERIFICATION_NOTE',expected_revision=rv['finding_revision'],operator_confirmed=True)
    return f,c,ev

def test_empty_console_is_read_only():
    before=tree_digest(); r=console.build_repair_candidate_console_state(); require(r['selection_status']=='none_selected','empty'); require(not r['writes_state'] and r['content_free'],'boundary'); require(before==tree_digest(),'source')
def test_selected_console_combines_redacted_evidence():
    f,c,_=fixture(); r=console.build_repair_candidate_console_state(finding_id=f['finding_id'],candidate_id=c['candidate_id'])
    require(r['selection_status']=='available','selection')
    for key in ('protocol','candidate_window','registrations','review','verification_evidence','lineage'): require(r[key] is not None,key)
    encoded=json.dumps(r,sort_keys=True)
    for secret in ('PRIVATE_CONSOLE_FINDING','PRIVATE_CONSOLE_DETAILS','PRIVATE_CANDIDATE_LABEL','PRIVATE_CANDIDATE_REFERENCE','PRIVATE_REVIEW_NOTE','PRIVATE_VERIFICATION_NOTE'): require(secret not in encoded,secret)
def test_console_comparison_is_optional_and_descriptive():
    f,c,ev=fixture(); r2=registration.register_repair_candidate(f['finding_id'],candidate_kind='patch_artifact',artifact_sha256='F'*64,source_manifest_sha256='1'*64,expected_revision=ev['finding_revision'],operator_confirmed=True); c2=r2['candidates'][-1]
    r=console.build_repair_candidate_console_state(finding_id=f['finding_id'],candidate_id=c['candidate_id'],comparison_candidate_ids=[c['candidate_id'],c2['candidate_id']])
    require(r['comparison'] and r['comparison']['candidate_count']==2,'comparison'); require(not r['comparison']['candidates_ranked'] and not r['comparison']['winner_selected'],'ranking')
def test_api_get_route_is_provider_free():
    f,c,_=fixture(); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-console',{'finding_id':[f['finding_id']],'candidate_id':[c['candidate_id']]}); d=payload['data']; require(status==200 and d['selection_status']=='available','route'); require(not d['provider_invoked'] and not d['generation_invoked'],'provider')
def test_dashboard_has_explicit_actions_export_and_narrow_layout():
    html=dashboard.render_repair_candidate_review_console()
    for token in ("data-repair-candidate-console-version='v1090.6'","data-repair-candidate-review-export-version='v1090.7'","data-long-session-candidates-version='v1090.8'",'/api/conversation/evaluation-finding','operator_confirmed:true','window.confirm','register_review_candidate','record_candidate_review','record_candidate_verification_evidence','link_candidate_lineage','/api/conversation/repair-candidate-review-export'): require(token in html,token)
    require('@media(max-width:820px)' in html and 'grid-template-columns:1fr' in html,'narrow')
def test_dashboard_javascript_has_valid_syntax():
    html=dashboard.render_repair_candidate_review_console(); m=re.search(r'<script>(.*?)</script>',html,re.S); require(m,'script'); p=Path(tempfile.mkdtemp())/'candidate-console.js'; p.write_text(m.group(1)); cp=subprocess.run(['node','--check',str(p)],text=True,capture_output=True,timeout=30); require(cp.returncode==0,cp.stderr)
def test_console_grants_no_authority():
    f,c,_=fixture(); r=console.build_repair_candidate_console_state(finding_id=f['finding_id'],candidate_id=c['candidate_id'])
    for key in ('automatic_test_execution','automatic_task_created','automatic_work_item_created','autonomous_prioritization','candidate_ranked','winner_selected','patch_generated','patch_reviewed_automatically','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[key] is False,key)
def test_missing_selection_is_bounded():
    r=console.build_repair_candidate_console_state(finding_id='eval_finding_20000101T000000_000000000000',candidate_id='repair_candidate_0000000000000000'); require(r['selection_status']=='not_found','missing'); require(r['registrations'] is None and r['review'] is None,'evidence')
def test_route_and_registration_are_exact():
    source=(ROOT/'conscious_agent/api_server.py').read_text(); require(source.count('parts == ["conversation", "repair-candidate-console"]')==1,'route'); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-console"]' not in post,'post'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.6-operator-candidate-review-console')==1,'registration'); require(names.index('v1090.6-operator-candidate-review-console')<names.index('v1090.5-candidate-supersession-lineage'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e: checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else: passed+=1; checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1090.6-operator-candidate-review-console','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
