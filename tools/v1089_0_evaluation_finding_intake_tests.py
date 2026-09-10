from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_campaign as campaign
import conversation_evaluation_campaign_enrollment as enrollment
import conversation_evaluation_finding as finding
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def fixture():
 s=create_conversation_session('Finding intake session',select_session=False)
 e=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
 e=daily.record_operator_observation(e['evaluation_id'],ratings={'continuity':3},issue_domain='interface',severity='minor',expected_revision=e['revision'],operator_confirmed=True)
 c=campaign.create_evaluation_campaign(campaign_label='PRIVATE_CAMPAIGN_1089',objective='PRIVATE_OBJECTIVE_1089',focus_areas=['conversation_quality'],target_evaluation_count=2,minimum_completed_evaluations=1,planned_duration_days=3,required_signals=[],operator_confirmed=True)
 c=enrollment.enroll_daily_evaluation(c['campaign_id'],e['evaluation_id'],expected_revision=c['revision'],operator_confirmed=True)
 return c,e
def make():
 c,e=fixture(); f=finding.create_evaluation_finding(finding_title='PRIVATE_FINDING_TITLE_1089',finding_details='PRIVATE_FINDING_DETAILS_1089',issue_domain='interface',severity='major',campaign_id=c['campaign_id'],evaluation_id=e['evaluation_id'],operator_confirmed=True); return c,e,f

def test_create_requires_confirmation_and_reference():
 try: finding.create_evaluation_finding(finding_title='x',issue_domain='interface',severity='minor',operator_confirmed=False)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('unguarded finding created')

def test_enrolled_campaign_evaluation_reference_is_accepted():
 c,e,f=make(); require(f['campaign_id']==c['campaign_id'] and f['evaluation_id']==e['evaluation_id'],'references missing')

def test_unenrolled_campaign_evaluation_is_rejected():
 c,e=fixture(); s=create_conversation_session('Other',select_session=False); other=daily.start_daily_evaluation(s['id'],operator_confirmed=True)
 try: finding.create_evaluation_finding(finding_title='x',issue_domain='interface',severity='minor',campaign_id=c['campaign_id'],evaluation_id=other['evaluation_id'],operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('unenrolled reference accepted')

def test_private_title_and_details_are_digest_only_publicly():
 _,_,f=make(); encoded=json.dumps(f,sort_keys=True); require('PRIVATE_FINDING_TITLE_1089' not in encoded and 'PRIVATE_FINDING_DETAILS_1089' not in encoded,'private finding leaked'); require(f['finding_title_digest'] and f['finding_details_digest'],'digests absent')

def test_private_record_retains_operator_content():
 _,_,f=make(); private=finding.load_evaluation_finding_private(f['finding_id']); require(private['private_title']=='PRIVATE_FINDING_TITLE_1089' and private['private_details']=='PRIVATE_FINDING_DETAILS_1089','private content missing')

def test_duplicate_open_finding_is_idempotent():
 c,e,f=make(); d=finding.create_evaluation_finding(finding_title='PRIVATE_FINDING_TITLE_1089',finding_details='different details ignored for identity',issue_domain='interface',severity='major',campaign_id=c['campaign_id'],evaluation_id=e['evaluation_id'],operator_confirmed=True); require(d['duplicate_finding'] and d['finding_id']==f['finding_id'] and d['revision']==f['revision'],'duplicate mutated state')

def test_update_requires_exact_revision():
 _,_,f=make()
 try: finding.update_evaluation_finding_details(f['finding_id'],finding_title='new',finding_details='',issue_domain='interface',severity='minor',expected_revision=f['revision']-1,operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('stale update accepted')

def test_update_and_state_are_explicit():
 _,_,f=make(); u=finding.update_evaluation_finding_details(f['finding_id'],finding_title='new private title',finding_details='new private details',issue_domain='session_continuity',severity='minor',expected_revision=f['revision'],operator_confirmed=True); r=finding.set_evaluation_finding_state(f['finding_id'],state='resolved',expected_revision=u['revision'],operator_confirmed=True); require(r['state']=='resolved' and r['revision']==u['revision']+1,'state update failed')

def test_list_is_bounded_redacted_and_read_only():
 make(); result=finding.list_evaluation_findings(limit=1); require(result['finding_count']==1 and result['writes_state'] is False and result['redacted'],'list contract wrong'); require(not finding.evaluation_finding_summary_contains_private_fields(result),'private field in list')

def test_api_get_and_post_routes():
 c,e=fixture(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'create','finding_title':'private api title','finding_details':'private api details','issue_domain':'interface','severity':'minor','campaign_id':c['campaign_id'],'evaluation_id':e['evaluation_id'],'operator_confirmed':True},{}); require(status==200,'post failed'); fid=payload['data']['finding_id']; status,payload=api_server.handle_api_get('/api/conversation/evaluation-finding',{'finding_id':[fid]}); require(status==200 and payload['data']['finding_id']==fid,'get failed')

def test_no_authority_escalation_or_provider_work():
 _,_,f=make()
 for key in ('provider_invoked','automatic_reproduction','automatic_task_created','automatic_work_item_created','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','source_tree_written'): require(f[key] is False,f'authority escalated {key}')

def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'finding runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.0-evaluation-finding-intake')==1 and names.index('v1089.0-evaluation-finding-intake')<names.index('v1088.9-desktop-alpha-operator-evaluation-campaign-checkpoint'),'registration wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.0-evaluation-finding-intake','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
