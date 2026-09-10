from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_followups as followups
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def make_evaluation():
    session=create_conversation_session('Follow-up session',select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    return daily.record_operator_observation(item['evaluation_id'],ratings={'continuity':4},issue_domain='interface',severity='minor',expected_revision=item['revision'],operator_confirmed=True)

def make_campaign(*,enroll_item=True):
    camp=campaign.create_evaluation_campaign(campaign_label='Private follow-up campaign',objective='private follow-up objective',focus_areas=['conversation_quality'],target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=4,required_signals=[],operator_confirmed=True)
    item=make_evaluation()
    if enroll_item: camp=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    return camp,item

def test_add_requires_confirmation_and_exact_revision():
    camp,item=make_campaign()
    for confirmed,revision in [(False,camp['revision']),(True,None),(True,camp['revision']-1)]:
        try: followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=revision,operator_confirmed=confirmed)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError('unguarded follow-up accepted')

def test_evaluation_reference_is_explicit_and_revision_guarded():
    camp,item=make_campaign(); result=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    require(result['campaign_revision']==camp['revision']+1 and result['follow_up_count']==1,'follow-up not persisted')
    row=result['follow_up_refs'][0]; require(row['evaluation_id']==item['evaluation_id'] and row['reference_kind']=='evaluation','evaluation reference wrong')

def test_external_reference_value_is_private_and_digest_only_publicly():
    camp,_=make_campaign(enroll_item=False); secret='PRIVATE_EXTERNAL_WORK_ITEM_1088_4'
    result=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='external_work_item',reference_value=secret,expected_revision=camp['revision'],operator_confirmed=True)
    encoded=json.dumps(result,sort_keys=True); require(secret not in encoded and result['follow_up_refs'][0]['reference_digest'],'external reference leaked or missing digest')
    private=campaign.load_evaluation_campaign_private(camp['campaign_id']); require(private['follow_up_refs'][0]['private_reference_value']==secret,'private external reference not stored')

def test_issue_domain_reference_is_validated():
    camp,_=make_campaign(enroll_item=False)
    for token in ('none','imaginary_domain'):
        try: followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='issue_domain',reference_value=token,expected_revision=camp['revision'],operator_confirmed=True)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError('invalid issue-domain follow-up accepted')
    result=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='issue_domain',reference_value='model_quality',expected_revision=camp['revision'],operator_confirmed=True)
    require(result['follow_up_refs'][0]['issue_domain']=='model_quality','valid issue-domain follow-up rejected')

def test_unenrolled_evaluation_reference_is_rejected():
    camp,item=make_campaign(enroll_item=False)
    try: followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='reproduction_packet',reference_value=item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('unenrolled evaluation follow-up accepted')

def test_duplicate_open_reference_is_idempotent_without_revision_advance():
    camp,item=make_campaign(); first=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    duplicate=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=first['campaign_revision'],operator_confirmed=True)
    require(duplicate['duplicate_reference'] and duplicate['campaign_revision']==first['campaign_revision'] and duplicate['follow_up_count']==1,'duplicate reference mutated state')

def test_follow_up_can_be_explicitly_resolved_or_dismissed():
    camp,item=make_campaign(); added=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True); follow_id=added['follow_up_refs'][0]['follow_up_id']
    resolved=followups.update_evaluation_campaign_follow_up_state(camp['campaign_id'],follow_id,state='resolved',expected_revision=added['campaign_revision'],operator_confirmed=True)
    require(resolved['state_counts']['resolved']==1 and resolved['follow_up_refs'][0]['resolved_at'],'follow-up not resolved')

def test_follow_up_removal_is_explicit_and_revision_guarded():
    camp,item=make_campaign(); added=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='evaluation',reference_value=item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True); follow_id=added['follow_up_refs'][0]['follow_up_id']
    removed=followups.remove_evaluation_campaign_follow_up(camp['campaign_id'],follow_id,expected_revision=added['campaign_revision'],operator_confirmed=True)
    require(removed['follow_up_count']==0 and removed['campaign_revision']==added['campaign_revision']+1,'follow-up removal failed')

def test_public_follow_up_summary_is_redacted_and_non_autonomous():
    camp,_=make_campaign(enroll_item=False); result=followups.add_evaluation_campaign_follow_up(camp['campaign_id'],reference_kind='external_work_item',reference_value='private-token',expected_revision=camp['revision'],operator_confirmed=True)
    require(not followups.campaign_follow_up_summary_contains_private_fields(result),'private follow-up field leaked')
    for key in ('automatic_task_created','automatic_work_item_created','priority_assigned','autonomous_prioritization','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','writes_state'):
        require(result[key] is False,f'authority escalated: {key}')

def test_api_get_and_post_follow_up_routes():
    camp,item=make_campaign(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-campaign',{'action':'add_follow_up','campaign_id':camp['campaign_id'],'reference_kind':'evaluation','reference_value':item['evaluation_id'],'expected_revision':camp['revision'],'operator_confirmed':True},{})
    require(status==200 and payload['data']['follow_up_count']==1,'API follow-up add failed')
    status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-follow-ups',{'campaign_id':[camp['campaign_id']]})
    require(status==200 and payload['data']['follow_up_count']==1,'API follow-up GET failed')

def test_source_only_tree_contains_no_campaign_follow_up_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluation_campaigns').exists(),'campaign follow-up runtime packaged')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.4-campaign-follow-up-references')==1,'suite registration not exact')
    require(names.index('v1088.4-campaign-follow-up-references')<names.index('v1088.3-campaign-issue-aggregation'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.4-campaign-follow-up-references','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
