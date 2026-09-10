from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as evaluation
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def session(title='Evaluation fixture'):
    return create_conversation_session(title,select_session=False)['id']
def started(title='Evaluation fixture'):
    return evaluation.start_daily_evaluation(session(title),operator_confirmed=True)

def test_start_requires_explicit_confirmation():
    try:evaluation.start_daily_evaluation(session(),operator_confirmed=False)
    except evaluation.DailyEvaluationError as e:require('confirmation' in str(e).lower(),'wrong error')
    else:raise AssertionError('unconfirmed evaluation started')

def test_start_binds_readiness_digests_and_private_runtime_path():
    result=started('Digest binding')
    require(result['state']=='active' and result['revision']==1,'start state wrong')
    require(len(result['readiness_contract_digest'])==64 and len(result['readiness_areas_digest'])==64,'readiness digests missing')
    require(evaluation.DAILY_EVALUATIONS_DIR.is_relative_to(Path(os.environ['EIDOLON_DATA_DIR']).resolve()),'evaluation storage not external runtime')

def test_observation_records_explicit_ratings_and_redacts_note():
    result=started('Private note')
    updated=evaluation.record_operator_observation(result['evaluation_id'],ratings={'continuity':5,'relevance':4,'tone':3,'responsiveness':5,'recovery':4,'usability':4},note='private operator note alpha',signals=['consecutive_use','restart_resume'],expected_revision=1,operator_confirmed=True)
    require(updated['revision']==2 and updated['observation_count']==1,'observation not recorded')
    require(updated['private_notes_stored']==1 and not updated['private_note_content_returned'],'note privacy flags wrong')
    require('private operator note alpha' not in json.dumps(updated),'private note leaked')
    require(not evaluation.daily_evaluation_summary_contains_private_fields(updated),'summary contains private fields')

def test_private_note_is_recoverable_only_from_private_runtime_load():
    result=started('Private load')
    updated=evaluation.record_operator_observation(result['evaluation_id'],ratings={'usability':4},note='private runtime note beta',expected_revision=1,operator_confirmed=True)
    public=evaluation.load_daily_evaluation(result['evaluation_id'])
    private=evaluation.load_daily_evaluation(result['evaluation_id'],include_private_notes=True)
    require('private runtime note beta' not in json.dumps(public),'public load leaked note')
    require(private['observations'][0]['note']=='private runtime note beta','private note not persisted')
    require(updated['observations'][0]['note_digest']==private['observations'][0]['note_digest'],'note digest mismatch')

def test_rating_validation_rejects_missing_and_out_of_range_values():
    result=started('Rating validation')
    for ratings in ({},{'tone':0},{'tone':6},{'unknown':3}):
        try:evaluation.record_operator_observation(result['evaluation_id'],ratings=ratings,expected_revision=1,operator_confirmed=True)
        except evaluation.DailyEvaluationError:pass
        else:raise AssertionError(f'invalid ratings accepted: {ratings}')

def test_note_limit_and_signal_vocabulary_are_bounded():
    result=started('Bounds')
    try:evaluation.record_operator_observation(result['evaluation_id'],ratings={'tone':3},note='x'*4001,expected_revision=1,operator_confirmed=True)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('oversized note accepted')
    try:evaluation.record_operator_observation(result['evaluation_id'],ratings={'tone':3},signals=['invented_signal'],expected_revision=1,operator_confirmed=True)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('unknown signal accepted')

def test_issue_domain_and_severity_are_explicit_and_consistent():
    result=started('Issue labels')
    updated=evaluation.record_operator_observation(result['evaluation_id'],ratings={'recovery':2},issue_domain='provider_transport',severity='major',reproducible=True,expected_revision=1,operator_confirmed=True)
    row=updated['observations'][0]
    require(row['issue_domain']=='provider_transport' and row['severity']=='major' and row['reproducible'],'issue labels lost')
    try:evaluation.record_operator_observation(result['evaluation_id'],ratings={'tone':3},issue_domain='none',severity='major',expected_revision=2,operator_confirmed=True)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('severity without domain accepted')

def test_stale_revision_is_rejected():
    result=started('Stale revision')
    evaluation.record_operator_observation(result['evaluation_id'],ratings={'continuity':4},expected_revision=1,operator_confirmed=True)
    try:evaluation.record_operator_observation(result['evaluation_id'],ratings={'continuity':3},expected_revision=1,operator_confirmed=True)
    except evaluation.DailyEvaluationError as e:require('another tab' in str(e).lower(),'conflict not explicit')
    else:raise AssertionError('stale revision accepted')

def test_cross_process_same_revision_allows_exactly_one_mutation():
    result=started('Cross process')
    script='''import json,sys\nsys.path.insert(0,sys.argv[1])\nfrom conversation_daily_evaluation import record_operator_observation\ntry:\n r=record_operator_observation(sys.argv[2],ratings={"continuity":4},note=sys.argv[3],expected_revision=1,operator_confirmed=True)\n print(json.dumps({"ok":True,"revision":r["revision"]}))\nexcept Exception as e:\n print(json.dumps({"ok":False,"error":str(e)}))\n'''
    env=dict(os.environ);env['PYTHONPATH']=str(AGENT)+os.pathsep+str(TOOLS)
    p1=subprocess.Popen([sys.executable,'-c',script,str(AGENT),result['evaluation_id'],'one'],stdout=subprocess.PIPE,text=True,env=env)
    p2=subprocess.Popen([sys.executable,'-c',script,str(AGENT),result['evaluation_id'],'two'],stdout=subprocess.PIPE,text=True,env=env)
    rows=[json.loads(p1.communicate(timeout=30)[0]),json.loads(p2.communicate(timeout=30)[0])]
    require(sum(1 for row in rows if row['ok'])==1,f'exactly-one mutation failed: {rows}')
    require(evaluation.load_daily_evaluation(result['evaluation_id'])['observation_count']==1,'duplicate observation persisted')

def test_restart_reload_preserves_evaluation_without_source_state():
    result=started('Restart')
    evaluation.record_operator_observation(result['evaluation_id'],ratings={'continuity':5},expected_revision=1,operator_confirmed=True)
    script='''import json,sys\nsys.path.insert(0,sys.argv[1])\nfrom conversation_daily_evaluation import load_daily_evaluation\nprint(json.dumps(load_daily_evaluation(sys.argv[2])))\n'''
    env=dict(os.environ);env['PYTHONPATH']=str(AGENT)+os.pathsep+str(TOOLS)
    raw=subprocess.check_output([sys.executable,'-c',script,str(AGENT),result['evaluation_id']],text=True,env=env,timeout=30)
    loaded=json.loads(raw);require(loaded['revision']==2 and loaded['observation_count']==1,'restart reload failed')

def test_complete_and_abort_require_confirmation_and_close_mutations():
    complete=started('Complete')
    try:evaluation.finish_daily_evaluation(complete['evaluation_id'],state='completed',expected_revision=1,operator_confirmed=False)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('unconfirmed completion accepted')
    closed=evaluation.finish_daily_evaluation(complete['evaluation_id'],state='completed',expected_revision=1,operator_confirmed=True)
    require(closed['state']=='completed' and closed['revision']==2,'completion failed')
    try:evaluation.record_operator_observation(complete['evaluation_id'],ratings={'tone':4},expected_revision=2,operator_confirmed=True)
    except evaluation.DailyEvaluationError:pass
    else:raise AssertionError('closed evaluation mutated')
    aborted=started('Abort');aborted=evaluation.finish_daily_evaluation(aborted['evaluation_id'],state='aborted',expected_revision=1,operator_confirmed=True)
    require(aborted['state']=='aborted','abort failed')

def test_public_summary_has_no_provider_or_release_authority():
    result=started('Authority')
    for key in ('provider_invoked','embedding_provider_invoked','model_management','provider_switching','generation_settings_changed','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','autonomous_scoring'):
        require(result[key] is False,f'authority escalated: {key}')

def test_dashboard_post_route_uses_multi_tab_mutation_claims():
    source=(AGENT/'dashboard.py').read_text(encoding='utf-8')
    start=source.index('if parsed.path == "/api/dashboard-chat/daily-evaluation"')
    section=source[start:source.index('if parsed.path == "/api/dashboard-chat/conversation-controls"',start)]
    require('_dashboard_coordination_claim' in section and '_dashboard_coordination_finish' in section,'coordination claims missing')
    require('operator_confirmed' in section and 'expected_revision' in section,'explicit mutation guards missing')

def test_source_only_tree_contains_no_packaged_evaluation_runtime_data():
    require(not (ROOT/'data'/'conversation_evaluations').exists(),'private evaluation runtime packaged in source tree')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1087.1-operator-observation-capture')==1,'suite registration not exact')
    require(names.index('v1087.1-operator-observation-capture')<names.index('v1087.0-daily-evaluation-protocol'),'suite order wrong')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.1-operator-observation-capture','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
