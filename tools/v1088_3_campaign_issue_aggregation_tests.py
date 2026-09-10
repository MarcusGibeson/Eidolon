from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_issues as issues
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def make_evaluation(*,domain='none',severity='none',reproducible=False,note='',complete=True,signals=None):
    session=create_conversation_session('Issue aggregation session',select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    item=daily.record_operator_observation(item['evaluation_id'],ratings={'continuity':4,'recovery':4},signals=signals or ['consecutive_use'],issue_domain=domain,severity=severity,reproducible=reproducible,note=note,expected_revision=item['revision'],operator_confirmed=True)
    if complete:
        item=daily.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)
    return item

def make_campaign(items):
    camp=campaign.create_evaluation_campaign(campaign_label='Private issue campaign',objective='private objective',focus_areas=['conversation_quality'],target_evaluation_count=max(1,len(items)),minimum_completed_evaluations=1,planned_duration_days=5,required_signals=[],operator_confirmed=True)
    revision=camp['revision']
    for item in items:
        camp=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=revision,operator_confirmed=True); revision=camp['revision']
    return camp

def test_aggregation_counts_domains_severities_outcomes_and_reproducibility():
    first=make_evaluation(domain='model_quality',severity='major',reproducible=True)
    second=make_evaluation(domain='provider_transport',severity='blocking')
    camp=make_campaign([first,second]); report=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id'])
    require(report['evaluation_count']==2 and report['total_observations']==2,'evaluation counts wrong')
    require(report['issue_domain_counts']['model_quality']==1 and report['issue_domain_counts']['provider_transport']==1,'domain counts wrong')
    require(report['severity_counts']['major']==1 and report['severity_counts']['blocking']==1,'severity counts wrong')
    require(report['reproducible_observation_count']==1 and report['affected_evaluation_count']==2,'reproducibility counts wrong')
    require(report['outcome_counts']['reproducible_defect']==1 and report['outcome_counts']['provider_failure']==1,'outcome counts wrong')

def test_missing_evaluation_is_reported_without_recreation():
    item=make_evaluation(); camp=make_campaign([item]); path=daily.DAILY_EVALUATIONS_DIR/f"{item['evaluation_id']}.json"; path.unlink()
    report=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id'])
    require(report['missing_evaluation_count']==1 and report['evidence_rows'][0]['availability']=='missing','missing evaluation not reported')
    require(not path.exists(),'missing evaluation recreated')

def test_private_notes_and_campaign_plan_are_not_returned_or_inspected():
    secret='PRIVATE_NOTE_SENTINEL_1088_3'; item=make_evaluation(domain='interface',severity='minor',note=secret); camp=make_campaign([item])
    report=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id']); encoded=json.dumps(report,sort_keys=True)
    require(secret not in encoded and 'private objective' not in encoded,'private content leaked')
    require(not issues.campaign_issue_aggregation_contains_private_fields(report),'private field key leaked')
    require(not report['private_notes_inspected'] and not report['private_campaign_plan_inspected'],'private inspection claimed')

def test_aggregation_digest_is_deterministic_for_unchanged_evidence():
    item=make_evaluation(domain='session_continuity',severity='major',reproducible=True); camp=make_campaign([item])
    first=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id']); second=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id'])
    require(first['issue_aggregation_digest']==second['issue_aggregation_digest'],'digest changed without evidence change')

def test_aggregation_is_read_only_and_does_not_change_runtime_records():
    item=make_evaluation(domain='interface',severity='minor'); camp=make_campaign([item])
    campaign_path=campaign.EVALUATION_CAMPAIGNS_DIR/f"{camp['campaign_id']}.json"; eval_path=daily.DAILY_EVALUATIONS_DIR/f"{item['evaluation_id']}.json"
    before=(campaign_path.read_bytes(),eval_path.read_bytes()); issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id']); after=(campaign_path.read_bytes(),eval_path.read_bytes())
    require(before==after,'aggregation mutated runtime evidence')

def test_aggregation_grants_no_priority_task_provider_or_release_authority():
    camp=make_campaign([make_evaluation()]); report=issues.build_evaluation_campaign_issue_aggregation(camp['campaign_id'])
    for key in ('priority_assigned','autonomous_prioritization','automatic_task_created','automatic_follow_up_created','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','writes_state'):
        require(report[key] is False,f'authority escalated: {key}')

def test_api_get_issue_aggregation_route():
    camp=make_campaign([make_evaluation(domain='interface',severity='minor')])
    status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-issues',{'campaign_id':[camp['campaign_id']]})
    require(status==200 and payload['data']['issue_domain_counts']['interface']==1,'API issue aggregation failed')

def test_source_only_tree_contains_no_campaign_or_evaluation_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluation_campaigns').exists(),'campaign runtime packaged')
    require(not (ROOT/'data'/'conversation_evaluations').exists(),'evaluation runtime packaged')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.3-campaign-issue-aggregation')==1,'suite registration not exact')
    require(names.index('v1088.3-campaign-issue-aggregation')<names.index('v1088.2-campaign-evaluation-enrollment'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.3-campaign-issue-aggregation','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
