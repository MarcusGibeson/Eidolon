from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def make_evaluation(title='Campaign evaluation',complete=False,signals=None):
    session=create_conversation_session(title,select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    if signals is not None:
        item=daily.record_operator_observation(item['evaluation_id'],ratings={'continuity':4,'recovery':4},signals=signals,issue_domain='none',severity='none',expected_revision=item['revision'],operator_confirmed=True)
    if complete:
        item=daily.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)
    return item

def make_campaign(target=2,minimum=1,required=None):
    return campaign.create_evaluation_campaign(campaign_label='Enrollment campaign',objective='private enrollment objective',focus_areas=['everyday_consecutive_use','restart_and_resumption'],target_evaluation_count=target,minimum_completed_evaluations=minimum,planned_duration_days=7,required_signals=required or [],operator_confirmed=True)

def test_enrollment_requires_confirmation_and_expected_revision():
    camp=make_campaign(); item=make_evaluation()
    for confirmed,expected in [(False,1),(True,None)]:
        try: enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=expected,operator_confirmed=confirmed)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError('unguarded enrollment accepted')

def test_enrollment_adds_only_existing_daily_evaluation_reference():
    camp=make_campaign(); item=make_evaluation(); result=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    require(result['revision']==2 and result['evaluation_count']==1,'enrollment failed')
    ref=result['evaluation_refs'][0]; require(ref['evaluation_id']==item['evaluation_id'] and ref['session_id']==item['session_id'],'wrong evaluation reference')
    require(result['progress']['state_counts']['active']==1,'active progress missing')

def test_missing_evaluation_is_rejected_without_creation():
    camp=make_campaign()
    try: enrollment.enroll_daily_evaluation(camp['campaign_id'],'daily_eval_20260722T000000_aaaaaaaaaaaa',expected_revision=1,operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('missing evaluation enrolled or created')
    require(campaign.load_evaluation_campaign(camp['campaign_id'])['evaluation_count']==0,'missing evaluation changed campaign')

def test_duplicate_enrollment_is_idempotent_without_revision_advance():
    camp=make_campaign(); item=make_evaluation(); first=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    duplicate=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=2,operator_confirmed=True)
    require(first['revision']==2 and duplicate['revision']==2 and duplicate['duplicate_enrollment'],'duplicate enrollment mutated state')

def test_cross_campaign_duplicate_is_rejected():
    item=make_evaluation(); first=make_campaign(); second=make_campaign()
    enrollment.enroll_daily_evaluation(first['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    try: enrollment.enroll_daily_evaluation(second['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('same evaluation enrolled in two open campaigns')

def test_target_capacity_is_enforced():
    camp=make_campaign(target=1); first=make_evaluation('First'); second=make_evaluation('Second')
    enrolled=enrollment.enroll_daily_evaluation(camp['campaign_id'],first['evaluation_id'],expected_revision=1,operator_confirmed=True)
    try: enrollment.enroll_daily_evaluation(camp['campaign_id'],second['evaluation_id'],expected_revision=enrolled['revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('campaign target capacity exceeded')

def test_progress_tracks_current_evaluation_state_and_outcome():
    camp=make_campaign(target=1); item=make_evaluation(complete=True,signals=['consecutive_use'])
    enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    progress=enrollment.build_evaluation_campaign_progress(camp['campaign_id'])
    require(progress['state_counts']['completed']==1 and progress['outcome_counts']['successful_session']==1,'completed progress wrong')
    require(progress['current_evaluations'][0]['observation_count']==1,'observation count missing')

def test_required_signal_coverage_is_explicit_and_content_free():
    camp=make_campaign(target=1,required=['provider_outage','provider_return']); item=make_evaluation(complete=True,signals=['provider_outage'])
    enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    progress=enrollment.build_evaluation_campaign_progress(camp['campaign_id'])
    require(progress['covered_required_signals']==['provider_outage'] and progress['missing_required_signals']==['provider_return'],'signal coverage wrong')
    require(not progress['required_signal_coverage_complete'] and not progress['completion_ready'],'incomplete coverage marked ready')

def test_completion_is_blocked_until_minimum_and_signals_are_met():
    camp=make_campaign(target=1,required=['restart_resume']); active=campaign.activate_evaluation_campaign(camp['campaign_id'],expected_revision=1,operator_confirmed=True)
    item=make_evaluation(complete=True,signals=['consecutive_use']); enrolled=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=active['revision'],operator_confirmed=True)
    try: enrollment.complete_evaluation_campaign(camp['campaign_id'],expected_revision=enrolled['revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('incomplete campaign completed')

def test_operator_can_complete_ready_active_campaign():
    camp=make_campaign(target=1,required=['restart_resume']); active=campaign.activate_evaluation_campaign(camp['campaign_id'],expected_revision=1,operator_confirmed=True)
    item=make_evaluation(complete=True,signals=['restart_resume']); enrolled=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=active['revision'],operator_confirmed=True)
    closed=enrollment.complete_evaluation_campaign(camp['campaign_id'],expected_revision=enrolled['revision'],operator_confirmed=True)
    require(closed['state']=='completed' and closed['progress']['completion_ready'],'ready campaign not completed')

def test_unenrollment_is_explicit_and_revision_guarded():
    camp=make_campaign(); item=make_evaluation(); enrolled=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=1,operator_confirmed=True)
    removed=enrollment.unenroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=enrolled['revision'],operator_confirmed=True)
    require(removed['evaluation_count']==0 and removed['revision']==3,'unenrollment failed')

def test_progress_is_read_only_redacted_and_provider_free():
    camp=make_campaign(); progress=enrollment.build_evaluation_campaign_progress(camp['campaign_id'])
    require(not enrollment.evaluation_campaign_progress_contains_private_fields(progress),'private field leaked')
    for key in ('automatic_campaign_completion','automatic_evaluation_creation','automatic_evaluation_enrollment','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','autonomous_scoring','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','writes_state'):
        require(progress[key] is False,f'authority escalated: {key}')

def test_api_get_and_post_campaign_enrollment_routes():
    camp=make_campaign(target=1); item=make_evaluation(complete=True,signals=['consecutive_use'])
    status,payload=api_server.handle_api_post('/api/conversation/evaluation-campaign',{'action':'enroll','campaign_id':camp['campaign_id'],'evaluation_id':item['evaluation_id'],'expected_revision':1,'operator_confirmed':True},{})
    require(status==200 and payload['data']['evaluation_count']==1,'API enrollment failed')
    status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-progress',{'campaign_id':[camp['campaign_id']]})
    require(status==200 and payload['data']['state_counts']['completed']==1,'API progress failed')

def test_campaign_completion_does_not_start_replay_or_provider_work():
    camp=make_campaign(target=1); item=make_evaluation(complete=True); active=campaign.activate_evaluation_campaign(camp['campaign_id'],expected_revision=1,operator_confirmed=True); enrolled=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=active['revision'],operator_confirmed=True); closed=enrollment.complete_evaluation_campaign(camp['campaign_id'],expected_revision=enrolled['revision'],operator_confirmed=True)
    progress=closed['progress']; require(not progress['provider_invoked'] and not progress['automatic_replay'] and not progress['automatic_resend'],'completion triggered protected work')

def test_source_only_tree_contains_no_campaign_or_evaluation_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluation_campaigns').exists(),'campaign runtime packaged')
    require(not (ROOT/'data'/'conversation_evaluations').exists(),'evaluation runtime packaged')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.2-campaign-evaluation-enrollment')==1,'suite registration not exact')
    require(names.index('v1088.2-campaign-evaluation-enrollment')<names.index('v1088.1-evaluation-campaign-lifecycle'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.2-campaign-evaluation-enrollment','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
