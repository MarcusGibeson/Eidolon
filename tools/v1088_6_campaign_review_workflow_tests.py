from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1088c-review-')
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_review as review
import post_review_development_verify as verify

def req(v,m):
    if not v: raise AssertionError(m)
def tree_digest():
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not any(part in {'__pycache__','.git','.venv','venv'} for part in p.parts) and p.suffix!='.pyc':
            h.update(p.relative_to(ROOT).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()
def fixture():
    session=create_conversation_session('Campaign review fixture',select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    item=daily.record_operator_observation(item['evaluation_id'],ratings={'continuity':4},issue_domain='interface',severity='major',reproducible=True,note='PRIVATE_EVALUATION_REVIEW_SENTINEL',signals=['consecutive_use'],expected_revision=item['revision'],operator_confirmed=True)
    item=daily.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)
    camp=campaign.create_evaluation_campaign(campaign_label='PRIVATE_CAMPAIGN_LABEL',objective='PRIVATE_CAMPAIGN_OBJECTIVE',focus_areas=['conversation_quality'],target_evaluation_count=1,minimum_completed_evaluations=1,planned_duration_days=3,required_signals=['consecutive_use','provider_outage'],operator_confirmed=True)
    camp=campaign.activate_evaluation_campaign(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    camp=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    return camp,item

def test_initial_review_is_read_only_and_content_free():
    camp,_=fixture(); before=tree_digest(); report=review.build_evaluation_campaign_review(camp['campaign_id'])
    req(report['review_state']=='not_started' and report['required_finding_count']==3,'initial findings')
    req(not report['writes_state'] and report['read_only'] and report['content_free'],'read boundary')
    req(before==tree_digest(),'source mutation')

def test_start_requires_confirmation_and_exact_revision():
    camp,_=fixture()
    for confirmed,revision in ((False,camp['revision']),(True,camp['revision']+1)):
        try: review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=revision,operator_confirmed=confirmed)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError('unsafe review start accepted')
    started=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    req(started['review_state']=='in_review' and started['campaign_revision']==camp['revision']+1,'start failed')

def test_review_requires_summary_issue_and_missing_signal_dispositions():
    camp,_=fixture(); report=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    keys={(row['finding_kind'],row['finding_value']) for row in report['required_findings']}
    req(keys=={('campaign_summary','overall'),('issue_domain','interface'),('required_signal','provider_outage')},f'findings wrong {keys}')
    req(not report['review_completion_ready'] and report['missing_finding_count']==3,'premature ready')

def test_disposition_note_is_private_and_digest_only():
    camp,_=fixture(); report=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    secret='PRIVATE_REVIEW_NOTE_1088_6'
    report=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='acknowledged',note=secret,expected_revision=report['campaign_revision'],operator_confirmed=True)
    encoded=json.dumps(report,sort_keys=True)
    req(secret not in encoded and report['dispositions'][0]['private_note_present'],'note leaked/missing')
    req(not review.campaign_review_contains_private_fields(report),'private key leaked')

def test_duplicate_disposition_is_idempotent():
    camp,_=fixture(); report=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    report=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='deferred',note='',expected_revision=report['campaign_revision'],operator_confirmed=True)
    duplicate=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='deferred',note='',expected_revision=report['campaign_revision'],operator_confirmed=True)
    req(duplicate['duplicate_disposition'] and duplicate['campaign_revision']==report['campaign_revision'],'duplicate changed revision')

def test_stale_disposition_is_rejected():
    camp,_=fixture(); started=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    first=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='acknowledged',expected_revision=started['campaign_revision'],operator_confirmed=True)
    try: review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='issue_domain',finding_value='interface',disposition='follow_up_required',expected_revision=started['campaign_revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('stale disposition accepted')
    req(first['campaign_revision']==started['campaign_revision']+1,'first revision')

def test_completion_requires_all_explicit_findings():
    camp,_=fixture(); r=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='acknowledged',expected_revision=r['campaign_revision'],operator_confirmed=True)
    try: review.complete_evaluation_campaign_review(camp['campaign_id'],expected_revision=r['campaign_revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('incomplete review completed')
    for kind,value,disposition in [('issue_domain','interface','follow_up_required'),('required_signal','provider_outage','deferred')]:
        r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind=kind,finding_value=value,disposition=disposition,expected_revision=r['campaign_revision'],operator_confirmed=True)
    req(r['review_completion_ready'],'review not ready')
    r=review.complete_evaluation_campaign_review(camp['campaign_id'],expected_revision=r['campaign_revision'],operator_confirmed=True)
    req(r['review_state']=='completed' and not r['review_completion_ready'],'completion failed')

def test_completed_review_can_only_reopen_explicitly():
    camp,_=fixture(); r=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    for kind,value in [('campaign_summary','overall'),('issue_domain','interface'),('required_signal','provider_outage')]:
        r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind=kind,finding_value=value,disposition='acknowledged',expected_revision=r['campaign_revision'],operator_confirmed=True)
    r=review.complete_evaluation_campaign_review(camp['campaign_id'],expected_revision=r['campaign_revision'],operator_confirmed=True)
    reopened=review.reopen_evaluation_campaign_review(camp['campaign_id'],expected_revision=r['campaign_revision'],operator_confirmed=True)
    req(reopened['review_state']=='in_review' and reopened['review_reopened_at'],'reopen failed')

def test_remove_disposition_is_explicit_and_revision_guarded():
    camp,_=fixture(); r=review.start_evaluation_campaign_review(camp['campaign_id'],expected_revision=camp['revision'],operator_confirmed=True)
    r=review.set_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',disposition='acknowledged',expected_revision=r['campaign_revision'],operator_confirmed=True)
    removed=review.remove_evaluation_campaign_review_disposition(camp['campaign_id'],finding_kind='campaign_summary',finding_value='overall',expected_revision=r['campaign_revision'],operator_confirmed=True)
    req(removed['disposition_count']==0 and removed['campaign_revision']==r['campaign_revision']+1,'remove failed')

def test_api_get_and_mutation_actions_are_registered():
    camp,_=fixture(); status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-review',{'campaign_id':[camp['campaign_id']]})
    req(status==200 and payload['data']['review_state']=='not_started','GET route')
    status,payload=api_server.handle_api_post('/api/conversation/evaluation-campaign',{'action':'start_review','campaign_id':camp['campaign_id'],'expected_revision':camp['revision'],'operator_confirmed':True})
    req(status==200 and payload['data']['review_state']=='in_review','POST action')

def test_review_grants_no_task_priority_provider_or_release_authority():
    camp,_=fixture(); report=review.build_evaluation_campaign_review(camp['campaign_id'])
    for key in ('automatic_task_created','automatic_work_item_created','priority_assigned','autonomous_prioritization','release_recommendation_produced','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified'):
        req(report[key] is False,f'authority escalated {key}')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    req(names.count('v1088.6-campaign-review-workflow')==1,'registration')
    req(names.index('v1088.6-campaign-review-workflow')<names.index('v1088.5-bounded-campaign-comparison'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1088.6-campaign-review-workflow','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
