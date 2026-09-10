from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
import conversation_evaluation_campaign as campaign
import post_review_development_verify as verify

def require(value,message):
    if not value: raise AssertionError(message)

def create(label='Campaign Alpha',objective='Private campaign objective',target=2,minimum=1):
    return campaign.create_evaluation_campaign(campaign_label=label,objective=objective,focus_areas=['everyday_consecutive_use','conversation_quality'],target_evaluation_count=target,minimum_completed_evaluations=minimum,planned_duration_days=7,required_signals=['consecutive_use'],operator_confirmed=True)

def test_creation_requires_explicit_confirmation():
    try: campaign.create_evaluation_campaign(campaign_label='No',objective='',focus_areas=['conversation_quality'],target_evaluation_count=1,minimum_completed_evaluations=1,planned_duration_days=1,operator_confirmed=False)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('unconfirmed campaign created')

def test_creation_stores_private_plan_but_public_summary_is_redacted():
    result=create(); require(result['state']=='planned' and result['revision']==1,'campaign not planned')
    require(result['campaign_label_present'] and result['campaign_objective_present'],'presence evidence missing')
    require('Campaign Alpha' not in json.dumps(result) and 'Private campaign objective' not in json.dumps(result),'private plan leaked')
    require(not campaign.evaluation_campaign_summary_contains_private_fields(result),'private keys leaked')
    private=campaign.load_evaluation_campaign(result['campaign_id'],include_private_plan=True)
    require(private['private_campaign_label']=='Campaign Alpha' and private['private_objective']=='Private campaign objective','private plan not stored')

def test_plan_validation_is_bounded():
    cases=[dict(target_evaluation_count=0,minimum_completed_evaluations=1,planned_duration_days=1),dict(target_evaluation_count=33,minimum_completed_evaluations=1,planned_duration_days=1),dict(target_evaluation_count=2,minimum_completed_evaluations=3,planned_duration_days=1),dict(target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=31)]
    for values in cases:
        try: campaign.create_evaluation_campaign(campaign_label='Bad',objective='',focus_areas=['conversation_quality'],operator_confirmed=True,**values)
        except campaign.EvaluationCampaignError: pass
        else: raise AssertionError(f'invalid plan accepted: {values}')

def test_plan_update_uses_optimistic_revision():
    item=create(); updated=campaign.update_evaluation_campaign_plan(item['campaign_id'],campaign_label='Updated',objective='new private objective',focus_areas=['restart_and_resumption'],target_evaluation_count=3,minimum_completed_evaluations=2,planned_duration_days=5,required_signals=['restart_resume'],expected_revision=1,operator_confirmed=True)
    require(updated['revision']==2 and updated['target_evaluation_count']==3,'plan update failed')
    try: campaign.update_evaluation_campaign_plan(item['campaign_id'],campaign_label='Stale',objective='',focus_areas=['conversation_quality'],target_evaluation_count=1,minimum_completed_evaluations=1,planned_duration_days=1,expected_revision=1,operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('stale revision accepted')

def test_activation_and_abort_are_explicit_state_transitions():
    item=create(); active=campaign.activate_evaluation_campaign(item['campaign_id'],expected_revision=1,operator_confirmed=True)
    require(active['state']=='active' and active['revision']==2 and active['activated_at'],'activation failed')
    aborted=campaign.abort_evaluation_campaign(item['campaign_id'],expected_revision=2,operator_confirmed=True)
    require(aborted['state']=='aborted' and aborted['revision']==3 and aborted['aborted_at'],'abort failed')

def test_active_plan_cannot_be_rewritten():
    item=create(); campaign.activate_evaluation_campaign(item['campaign_id'],expected_revision=1,operator_confirmed=True)
    try: campaign.update_evaluation_campaign_plan(item['campaign_id'],campaign_label='Rewrite',objective='',focus_areas=['conversation_quality'],target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=2,expected_revision=2,operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('active campaign plan rewritten')

def test_closed_campaign_cannot_transition_again():
    item=create(); closed=campaign.abort_evaluation_campaign(item['campaign_id'],expected_revision=1,operator_confirmed=True)
    try: campaign.activate_evaluation_campaign(item['campaign_id'],expected_revision=closed['revision'],operator_confirmed=True)
    except campaign.EvaluationCampaignError: pass
    else: raise AssertionError('aborted campaign reactivated')

def test_restart_reload_preserves_redacted_state():
    item=create('Restart Campaign','private restart objective')
    script='''import json,sys\nsys.path.insert(0,sys.argv[1])\nfrom conversation_evaluation_campaign import load_evaluation_campaign\nprint(json.dumps(load_evaluation_campaign(sys.argv[2])))\n'''
    env=dict(os.environ); env['PYTHONPATH']=str(AGENT)+os.pathsep+str(TOOLS)
    raw=subprocess.check_output([sys.executable,'-c',script,str(AGENT),item['campaign_id']],text=True,env=env,timeout=30)
    loaded=json.loads(raw); require(loaded['revision']==1 and loaded['state']=='planned','restart reload failed')
    require('private restart objective' not in raw,'private objective leaked after restart')

def test_concurrent_same_revision_allows_exactly_one_update():
    item=create('Concurrent','private',target=3,minimum=1)
    start=Path(os.environ['EIDOLON_DATA_DIR'])/'start.flag'
    script='''import json,os,sys,time\nsys.path.insert(0,sys.argv[1])\nfrom conversation_evaluation_campaign import update_evaluation_campaign_plan\nwhile not os.path.exists(sys.argv[3]): time.sleep(0.01)\ntry:\n r=update_evaluation_campaign_plan(sys.argv[2],campaign_label=sys.argv[4],objective='',focus_areas=['conversation_quality'],target_evaluation_count=3,minimum_completed_evaluations=1,planned_duration_days=2,expected_revision=1,operator_confirmed=True); print(json.dumps({'ok':True,'revision':r['revision']}))\nexcept Exception as e: print(json.dumps({'ok':False,'type':type(e).__name__,'message':str(e)}))\n'''
    env=dict(os.environ); env['PYTHONPATH']=str(AGENT)+os.pathsep+str(TOOLS)
    procs=[subprocess.Popen([sys.executable,'-c',script,str(AGENT),item['campaign_id'],str(start),f'Worker {i}'],stdout=subprocess.PIPE,text=True,env=env) for i in range(2)]
    start.write_text('go',encoding='utf-8')
    rows=[json.loads(p.communicate(timeout=30)[0]) for p in procs]
    require(sum(bool(row['ok']) for row in rows)==1,'concurrent revision did not serialize exactly once')
    require(campaign.load_evaluation_campaign(item['campaign_id'])['revision']==2,'final revision wrong')

def test_api_post_route_requires_confirmation_and_supports_lifecycle():
    status,payload=api_server.dispatch_api('POST','/api/conversation/evaluation-campaign',body={'action':'create','campaign_label':'API','objective':'private','focus_areas':['conversation_quality'],'target_evaluation_count':1,'minimum_completed_evaluations':1,'planned_duration_days':1,'operator_confirmed':False})
    require(status==409 and not payload['ok'],'API accepted unconfirmed create')
    status,payload=api_server.dispatch_api('POST','/api/conversation/evaluation-campaign',body={'action':'create','campaign_label':'API','objective':'private','focus_areas':['conversation_quality'],'target_evaluation_count':1,'minimum_completed_evaluations':1,'planned_duration_days':1,'operator_confirmed':True})
    item=payload['data']; require(status==200 and item['state']=='planned','API create failed')
    status,payload=api_server.dispatch_api('POST','/api/conversation/evaluation-campaign',body={'action':'activate','campaign_id':item['campaign_id'],'expected_revision':1,'operator_confirmed':True})
    require(status==200 and payload['data']['state']=='active','API activation failed')

def test_public_summary_grants_no_provider_or_release_authority():
    result=create()
    for key in ('automatic_campaign_launch','automatic_evaluation_creation','automatic_evaluation_enrollment','provider_invoked','embedding_provider_invoked','generation_invoked','automatic_replay','automatic_resend','autonomous_scoring','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified'):
        require(result[key] is False,f'authority escalated: {key}')

def test_campaign_identifier_is_bounded_and_opaque():
    item=create(); require(item['campaign_id'].startswith('eval_campaign_') and len(item['campaign_id'])==42,'campaign id format changed')

def test_source_only_tree_contains_no_campaign_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluation_campaigns').exists(),'private campaign runtime packaged in source')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1088.1-evaluation-campaign-lifecycle')==1,'suite registration not exact')
    require(names.index('v1088.1-evaluation-campaign-lifecycle')<names.index('v1088.0-operator-evaluation-campaign-protocol'),'suite order wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({'name':name,'status':'fail','message':f'{type(error).__name__}: {error}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1088.1-evaluation-campaign-lifecycle','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
