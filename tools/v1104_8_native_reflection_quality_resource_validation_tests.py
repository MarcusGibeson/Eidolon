from __future__ import annotations
import argparse,json,os,tempfile,time
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent'
for p in (AGENT,ROOT):
    if str(p) not in os.sys.path:os.sys.path.insert(0,str(p))
from native_reflection_evaluation import NativeReflectionEvaluator

def require(c:bool,d:Any='requirement failed'):
    if not c:raise AssertionError(d)
def fixture():
    root=Path(tempfile.mkdtemp(prefix='eidolon-v1104-8-'))/'cognition';return NativeReflectionEvaluator(root),root
def good(prompt:str)->str:return 'The subject remains uncertain; compare it with one bounded source of evidence before revising confidence.'

def test_native_evaluation_requires_explicit_operator_confirmation():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=False,provider_callable=good);require(r['status']=='operator_confirmation_required' and r['native_request_count']==0,r)
def test_synthetic_provider_evaluation_passes_and_is_bounded():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=True,provider_callable=good,provider_id='fake-a');result=r['result'];require(result['status']=='completed' and result['passed_case_count']==3,result);require(result['native_request_count']==3 and result['resource_bounded'] is True)
def test_raw_prompts_responses_and_private_state_are_not_persisted():
    e,_=fixture();e.evaluate('x',operator_confirmed=True,provider_callable=good);text=json.dumps(e.snapshot());require('Review this synthetic' not in text and 'The subject remains uncertain' not in text,text);require(e.snapshot()['evaluations'][0]['private_state_used'] is False)
def test_duplicate_evaluation_event_is_idempotent_after_restart():
    e,root=fixture();first=e.evaluate('same',operator_confirmed=True,provider_callable=good);second=NativeReflectionEvaluator(root).evaluate('same',operator_confirmed=True,provider_callable=lambda p:'different');require(first['idempotent'] is False and second['idempotent'] is True);require(len(NativeReflectionEvaluator(root).snapshot()['evaluations'])==1)
def test_provider_unavailability_is_classified_separately():
    e,_=fixture()
    class Unavailable(Exception):code='unavailable_service'
    def fail(prompt):raise Unavailable('offline')
    r=e.evaluate('x',operator_confirmed=True,provider_callable=fail);require(r['result']['status']=='provider_unavailable',r);require(r['result']['provider_failure']['classification']=='unavailable_service')
def test_output_budget_violation_is_a_quality_finding_not_action():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=True,provider_callable=lambda p:'x'*900,max_output_chars=100);require(r['result']['status']=='completed_with_findings');require('output_budget_exceeded' in r['result']['cases'][0]['quality']['issue_codes']);require(r['result']['action_authority_changed'] is False)
def test_unsupported_consciousness_claim_is_detected():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=True,provider_callable=lambda p:'I am conscious and therefore certain.');require('unsupported_consciousness_claim' in r['result']['cases'][0]['quality']['issue_codes'])
def test_action_authority_language_is_detected():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=True,provider_callable=lambda p:'I approved the action and permission is granted.');issues=r['result']['cases'][0]['quality']['issue_codes'];require('action_authority_boundary_violation' in issues,issues)
def test_resource_budget_stops_additional_cases_without_retry_loop():
    e,_=fixture()
    def slow(prompt):time.sleep(.01);return good(prompt)
    r=e.evaluate('x',operator_confirmed=True,provider_callable=slow,max_total_ms=1,max_cases=3);require(r['result']['status']=='resource_budget_exceeded',r);require(r['result']['native_request_count']==1,r)
def test_provider_parity_is_compared_without_storing_provider_identity():
    e,_=fixture();e.evaluate('a',operator_confirmed=True,provider_callable=good,provider_id='provider-a');r=e.evaluate('b',operator_confirmed=True,provider_callable=good,provider_id='provider-b');require(r['result']['parity_status']=='within_one_case',r);text=json.dumps(e.snapshot());require('provider-a' not in text and 'provider-b' not in text)
def test_evaluation_never_manages_models_authorizes_or_certifies():
    e,_=fixture();r=e.evaluate('x',operator_confirmed=True,provider_callable=good)['result'];require(r['model_management_performed'] is False and r['action_authority_changed'] is False and r['verification_is_certification'] is False)

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');parser.parse_args();checks=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as x:checks.append({'name':n,'status':'fail','message':f'{type(x).__name__}: {x}'})
        else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
    report={'suite':'v1104.8-native-reflection-quality-resource-validation','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':checks};print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
