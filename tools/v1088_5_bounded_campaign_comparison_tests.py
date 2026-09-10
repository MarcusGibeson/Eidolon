from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_campaign_comparison as comparison
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def make_campaign(*,domain='none',severity='none',reproducible=False,note=''):
    session=create_conversation_session('Comparison session',select_session=False)
    item=daily.start_daily_evaluation(session['id'],operator_confirmed=True)
    item=daily.record_operator_observation(item['evaluation_id'],ratings={'continuity':4},issue_domain=domain,severity=severity,reproducible=reproducible,note=note,signals=['consecutive_use'],expected_revision=item['revision'],operator_confirmed=True)
    item=daily.finish_daily_evaluation(item['evaluation_id'],state='completed',expected_revision=item['revision'],operator_confirmed=True)
    camp=campaign.create_evaluation_campaign(campaign_label='Private comparison campaign',objective='private comparison objective',focus_areas=['conversation_quality'],target_evaluation_count=1,minimum_completed_evaluations=1,planned_duration_days=3,required_signals=['consecutive_use'],operator_confirmed=True)
    camp=enrollment.enroll_daily_evaluation(camp['campaign_id'],item['evaluation_id'],expected_revision=camp['revision'],operator_confirmed=True)
    return camp

def test_comparison_requires_two_distinct_campaigns():
    first=make_campaign()
    for ids in ([first['campaign_id']],[first['campaign_id'],first['campaign_id']]):
        try: comparison.build_evaluation_campaign_comparison(ids)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError('undersized comparison accepted')

def test_comparison_enforces_eight_campaign_limit():
    ids=[make_campaign()['campaign_id'] for _ in range(9)]
    try: comparison.build_evaluation_campaign_comparison(ids)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('oversized comparison accepted')

def test_comparison_reports_bounded_counts_and_deltas():
    baseline=make_campaign(); second=make_campaign(domain='model_quality',severity='major',reproducible=True)
    report=comparison.build_evaluation_campaign_comparison([baseline['campaign_id'],second['campaign_id']])
    require(report['campaign_count']==2 and len(report['campaigns'])==2 and len(report['deltas'])==1,'comparison shape wrong')
    row=report['campaigns'][1]; require(row['model_quality_issue_count']==1 and row['major_issue_count']==1 and row['reproducible_observation_count']==1,'issue counts missing')
    deltas=report['deltas'][0]['count_deltas']; require(deltas['model_quality_issue_count']==1 and deltas['major_issue_count']==1,'deltas wrong')

def test_comparison_preserves_input_order_as_explicit_baseline():
    first=make_campaign(domain='interface',severity='minor'); second=make_campaign()
    report=comparison.build_evaluation_campaign_comparison([second['campaign_id'],first['campaign_id']])
    require(report['baseline_campaign_id']==second['campaign_id'] and report['campaigns'][0]['campaign_id']==second['campaign_id'],'baseline order changed')

def test_private_notes_and_plans_are_not_returned_or_inspected():
    secret='PRIVATE_COMPARISON_NOTE_1088_5'; first=make_campaign(note=secret); second=make_campaign()
    report=comparison.build_evaluation_campaign_comparison([first['campaign_id'],second['campaign_id']]); encoded=json.dumps(report,sort_keys=True)
    require(secret not in encoded and 'private comparison objective' not in encoded,'private content leaked')
    require(not comparison.campaign_comparison_contains_private_fields(report),'private key leaked')
    require(not report['private_notes_inspected'] and not report['private_campaign_plan_inspected'],'private content inspection claimed')

def test_comparison_digest_is_deterministic_for_unchanged_campaigns():
    first=make_campaign(); second=make_campaign(domain='interface',severity='minor')
    one=comparison.build_evaluation_campaign_comparison([first['campaign_id'],second['campaign_id']]); two=comparison.build_evaluation_campaign_comparison([first['campaign_id'],second['campaign_id']])
    require(one['comparison_digest']==two['comparison_digest'],'comparison digest changed')

def test_comparison_is_read_only_and_mutates_no_campaign_record():
    first=make_campaign(); second=make_campaign(); paths=[campaign.EVALUATION_CAMPAIGNS_DIR/f"{token}.json" for token in (first['campaign_id'],second['campaign_id'])]
    before=[path.read_bytes() for path in paths]; comparison.build_evaluation_campaign_comparison([first['campaign_id'],second['campaign_id']]); after=[path.read_bytes() for path in paths]
    require(before==after,'comparison mutated campaign state')

def test_comparison_assigns_no_ranking_priority_winner_or_release_advice():
    report=comparison.build_evaluation_campaign_comparison([make_campaign()['campaign_id'],make_campaign()['campaign_id']])
    for key in ('campaigns_ranked','winner_selected','priority_assigned','autonomous_prioritization','statistical_significance_claimed','release_recommendation_produced','automatic_task_created','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','writes_state'):
        require(report[key] is False,f'authority escalated: {key}')

def test_api_get_campaign_comparison_route_accepts_repeated_ids():
    first=make_campaign(); second=make_campaign(domain='provider_transport',severity='blocking')
    status,payload=api_server.handle_api_get('/api/conversation/evaluation-campaign-comparison',{'campaign_id':[first['campaign_id'],second['campaign_id']]})
    require(status==200 and payload['data']['campaign_count']==2,'API comparison failed')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.5-bounded-campaign-comparison')==1,'suite registration not exact')
    require(names.index('v1088.5-bounded-campaign-comparison')<names.index('v1088.4-campaign-follow-up-references'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.5-bounded-campaign-comparison','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
