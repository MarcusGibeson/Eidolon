from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1088c-export-')
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_followups as followups
import conversation_evaluation_campaign_review as review
import conversation_evaluation_campaign_review_export as export
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc': h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def fixture():
    session=create_conversation_session('Campaign export fixture',select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    item=daily.record_operator_observation(item['evaluation_id'],ratings={'recovery':4},issue_domain='provider_transport',severity='major',reproducible=True,note='PRIVATE_EVALUATION_EXPORT_NOTE',signals=['provider_outage'],expected_revision=item['revision'],operator_confirmed=True)
    item=daily.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)
    camp=campaign.create_evaluation_campaign(campaign_label='PRIVATE_EXPORT_CAMPAIGN_LABEL',objective='PRIVATE_EXPORT_CAMPAIGN_OBJECTIVE',focus_areas=['provider_outage_and_return'],target_evaluation_count=1,minimum_completed_evaluations=1,planned_duration_days=2,required_signals=['provider_outage'],operator_confirmed=True)
    camp=campaign.activate_evaluation_campaign(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    camp=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    follow=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='external_work_item',reference_value='PRIVATE_EXTERNAL_WORK_ITEM_1088_8',expected_revision=camp['revision'],operator_confirmed=True)
    r=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=follow['campaign_revision'],operator_confirmed=True)
    r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='acknowledged',note='PRIVATE_REVIEW_EXPORT_NOTE',expected_revision=r['campaign_revision'],operator_confirmed=True)
    r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='issue_domain',finding_value='provider_transport',disposition='follow_up_required',expected_revision=r['campaign_revision'],operator_confirmed=True)
    r=review.complete_evaluation_campaign_review(camp['campaign_id'],expected_revision=r['campaign_revision'],operator_confirmed=True)
    return r

def test_export_is_deterministic_and_hash_bound():
    r=fixture(); first=export.build_evaluation_campaign_review_export(r['campaign_id']); second=export.build_evaluation_campaign_review_export(r['campaign_id'])
    req(first==second,'nondeterministic'); req(hashlib.sha256(first['document'].encode()).hexdigest()==first['document_sha256'],'hash')

def test_export_contains_bounded_campaign_review_evidence():
    r=fixture(); report=export.build_evaluation_campaign_review_export(r['campaign_id']); doc=report['review']
    req(doc['review_state']=='completed' and doc['review_disposition_counts']['follow_up_required']==1,'review evidence')
    req(doc['issue_domain_counts']['provider_transport']==1 and doc['follow_up_count']==1,'issue/followup evidence')

def test_export_excludes_all_private_values():
    r=fixture(); report=export.build_evaluation_campaign_review_export(r['campaign_id']); encoded=json.dumps(report,sort_keys=True)
    for secret in ('PRIVATE_EXPORT_CAMPAIGN_LABEL','PRIVATE_EXPORT_CAMPAIGN_OBJECTIVE','PRIVATE_EXTERNAL_WORK_ITEM_1088_8','PRIVATE_REVIEW_EXPORT_NOTE','PRIVATE_EVALUATION_EXPORT_NOTE'):
        req(secret not in encoded,f'leaked {secret}')
    req(not export.campaign_review_export_contains_private_fields(report),'private key leaked')

def test_export_has_explicit_exclusion_flags():
    r=fixture(); doc=export.build_evaluation_campaign_review_export(r['campaign_id'])['review']
    for key in ('transcript_included','prompt_included','private_evaluation_notes_included','private_review_notes_included','private_campaign_plan_included','private_follow_up_values_included','memory_content_included','provider_payload_included','credentials_included','vectors_included','hidden_reasoning_included','release_recommendation_produced','campaign_ranking_included','statistical_significance_claimed','automatic_task_created','autonomous_prioritization','provider_invoked','generation_invoked'):
        req(doc[key] is False,key)

def test_get_route_returns_client_download_without_server_write():
    r=fixture(); before=tree_digest(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-review-export',{'campaign_id':[r['campaign_id']]}); data=payload['data']
    req(status==200 and data['client_download_ready'],'route'); req(not data['server_file_written'] and not data['writes_state'],'write')
    req(before==tree_digest(),'source mutation')

def test_export_cannot_certify_install_or_promote():
    r=fixture(); report=export.build_evaluation_campaign_review_export(r['campaign_id'])
    req(not report['release_certified'] and not report['promotion_performed'] and not report['installation_performed'],'authority')
    req(report['review']['release_decision']=='operator_only','release decision')

def test_filename_is_bounded_and_content_free():
    r=fixture(); report=export.build_evaluation_campaign_review_export(r['campaign_id'])
    req(report['filename'].endswith('_privacy_safe_campaign_review.json'),'filename')
    req('/' not in report['filename'] and '\\' not in report['filename'],'path')

def test_no_post_export_route_and_exact_registration():
    source=(ROOT/'conscious_agent'/'api_server.py').read_text(); post=source[source.index('def handle_api_post'):]
    req('parts == ["conversation", "evaluation-campaign-review-export"]' not in post,'POST export route')
    names=[s.name for s in verify.SUITES]; req(names.count('v1088.8-campaign-review-export')==1,'registration')
    req(names.index('v1088.8-campaign-review-export')<names.index('v1088.7-operator-campaign-console'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1088.8-campaign-review-export','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
