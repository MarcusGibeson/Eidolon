from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as evaluation
import conversation_evaluation_outcomes as outcomes
import post_review_development_verify as verify

def require(v,m):
    if not v: raise AssertionError(m)
def classify(state='completed',rows=None):return outcomes.classify_evaluation_outcome(evaluation_state=state,observations=rows or [])
def obs(domain='none',severity='none',reproducible=False,note='private text'):return {'issue_domain':domain,'severity':severity,'reproducible':reproducible,'note':note}

def test_successful_session_requires_no_explicit_issue():
    result=classify(rows=[obs()]);require(result['outcome']=='successful_session' and result['reason']=='no_explicit_issue_marked','success classification wrong')

def test_minor_friction_uses_explicit_nonreproducible_issue():
    result=classify(rows=[obs('interface','minor',False)]);require(result['outcome']=='minor_friction','minor friction classification wrong')

def test_reproducible_defect_uses_explicit_reproducibility():
    result=classify(rows=[obs('session_continuity','major',True)]);require(result['outcome']=='reproducible_defect','reproducible defect classification wrong')

def test_provider_failure_is_separate_from_model_quality():
    result=classify(rows=[obs('provider_transport','major',False),obs('model_quality','major',False)])
    require(result['outcome']=='provider_failure','provider failure not separated')
    require(result['provider_transport_issue_count']==1 and result['model_quality_issue_count']==1,'domain counts conflated')

def test_operator_abort_has_precedence_without_claiming_product_failure():
    result=classify(state='aborted',rows=[obs('provider_transport','blocking',True)])
    require(result['outcome']=='operator_aborted' and result['reason']=='explicit_operator_abort','abort precedence wrong')

def test_interface_transport_model_and_continuity_counts_are_distinct():
    result=classify(rows=[obs('interface','minor'),obs('provider_transport','minor'),obs('model_quality','major'),obs('session_continuity','major',True)])
    require(result['interface_issue_count']==1 and result['provider_transport_issue_count']==1 and result['model_quality_issue_count']==1 and result['session_continuity_issue_count']==1,'domain counts merged')

def test_classifier_never_inspects_note_or_transcript_content():
    a=classify(rows=[obs('interface','minor',False,'secret alpha')]);b=classify(rows=[obs('interface','minor',False,'different secret beta')])
    require(a['classification_digest']==b['classification_digest'],'note content affected classification')
    require(not a['note_text_inspected'] and not a['transcript_inspected'],'content inspection claimed')
    require('secret' not in json.dumps(a).lower(),'note leaked')

def test_classification_digest_is_deterministic():
    rows=[obs('provider_transport','major',False),obs('interface','minor',True)]
    require(classify(rows=rows)['classification_digest']==classify(rows=rows)['classification_digest'],'classification digest unstable')

def test_classifier_has_no_autonomous_score_provider_or_release_authority():
    result=classify(rows=[obs()])
    for key in ('autonomous_scoring','provider_invoked','writes_state','release_certified','promotion_performed'):
        require(result[key] is False,f'authority escalated: {key}')

def test_completed_runtime_evaluation_embeds_content_free_outcome():
    session=create_conversation_session('Outcome fixture',select_session=False)
    started=evaluation.start_daily_evaluation(session['id'],operator_confirmed=True)
    observed=evaluation.record_operator_observation(started['evaluation_id'],ratings={'recovery':2},note='private outage note',issue_domain='provider_transport',severity='major',signals=['provider_outage'],expected_revision=1,operator_confirmed=True)
    closed=evaluation.finish_daily_evaluation(started['evaluation_id'],state='completed',expected_revision=observed['revision'],operator_confirmed=True)
    require(closed['outcome']['outcome']=='provider_failure','stored evaluation outcome wrong')
    require('private outage note' not in json.dumps(closed),'private note leaked into outcome')

def test_active_evaluation_classification_is_non_authorizing_snapshot():
    result=classify(state='active',rows=[obs('interface','minor')])
    require(result['outcome']=='minor_friction' and not result['release_certified'],'active snapshot gained authority')

def test_unknown_labels_are_normalized_to_no_issue_without_guessing():
    result=classify(rows=[{'issue_domain':'invented','severity':'catastrophic','reproducible':True}])
    require(result['outcome']=='successful_session','unknown labels were guessed')

def test_outcome_classes_are_bounded_and_complete():
    require(outcomes.OUTCOME_CLASSES==('successful_session','minor_friction','reproducible_defect','provider_failure','operator_aborted'),'outcome vocabulary changed')

def test_suite_registration_is_exact_and_ordered():
    names=[s.name for s in verify.SUITES]
    require(names.count('v1087.2-session-outcome-classification')==1,'suite registration not exact')
    require(names.index('v1087.2-session-outcome-classification')<names.index('v1087.1-operator-observation-capture'),'suite order wrong')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true');checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1087.2-session-outcome-classification','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
