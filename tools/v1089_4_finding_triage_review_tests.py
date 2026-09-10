from __future__ import annotations
import argparse,json,multiprocessing,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_triage as triage
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make():
 s=create_conversation_session('Triage session',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title='PRIVATE_TRIAGE_TITLE',finding_details='PRIVATE_TRIAGE_DETAILS',issue_domain='session_continuity',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
def _race(fid,rev,start,q):
 start.wait()
 try: q.put(('ok',triage.start_evaluation_finding_triage(fid,note='PRIVATE_RACE_NOTE',expected_revision=rev,operator_confirmed=True)['finding_revision']))
 except Exception as e: q.put(('error',type(e).__name__))

def test_default_triage_is_not_started_and_redacted():
 f=make(); r=triage.build_evaluation_finding_triage(f['finding_id']); require(r['triage_state']=='not_started' and not r['private_note_returned'] and r['content_free'],'default')
def test_start_requires_confirmation_and_exact_revision():
 f=make()
 for confirmed,rev in [(False,f['revision']),(True,None),(True,f['revision']-1)]:
  try: triage.start_evaluation_finding_triage(f['finding_id'],expected_revision=rev,operator_confirmed=confirmed)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('unguarded start')
def test_private_note_is_digest_only_publicly():
 f=make(); r=triage.start_evaluation_finding_triage(f['finding_id'],note='PRIVATE_TRIAGE_NOTE',expected_revision=f['revision'],operator_confirmed=True); require('PRIVATE_TRIAGE_NOTE' not in json.dumps(r) and r['triage_note_digest'],'note leak')
def test_disposition_requires_in_review_and_supported_value():
 f=make()
 try: triage.set_evaluation_finding_triage_disposition(f['finding_id'],disposition='urgent',expected_revision=f['revision'],operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('bad disposition')
def test_completion_requires_explicit_disposition():
 f=make(); started=triage.start_evaluation_finding_triage(f['finding_id'],expected_revision=f['revision'],operator_confirmed=True)
 try: triage.complete_evaluation_finding_triage(f['finding_id'],expected_revision=started['finding_revision'],operator_confirmed=True)
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('completed without disposition')
def test_disposition_complete_and_reopen_are_explicit():
 f=make(); a=triage.start_evaluation_finding_triage(f['finding_id'],expected_revision=f['revision'],operator_confirmed=True); b=triage.set_evaluation_finding_triage_disposition(f['finding_id'],disposition='repair_candidate_review',note='PRIVATE_REVIEW_NOTE',expected_revision=a['finding_revision'],operator_confirmed=True); c=triage.complete_evaluation_finding_triage(f['finding_id'],expected_revision=b['finding_revision'],operator_confirmed=True); d=triage.reopen_evaluation_finding_triage(f['finding_id'],expected_revision=c['finding_revision'],operator_confirmed=True); require(c['triage_state']=='completed' and d['triage_state']=='in_review' and d['triage_disposition']=='repair_candidate_review','lifecycle')
def test_private_record_retains_note():
 f=make(); triage.start_evaluation_finding_triage(f['finding_id'],note='PRIVATE_STORED_NOTE',expected_revision=f['revision'],operator_confirmed=True); require(finding.load_evaluation_finding_private(f['finding_id'])['triage']['private_note']=='PRIVATE_STORED_NOTE','private note missing')
def test_cross_process_same_revision_allows_exactly_one_writer():
 f=make(); ctx=multiprocessing.get_context('spawn'); start=ctx.Event(); q=ctx.Queue(); ps=[ctx.Process(target=_race,args=(f['finding_id'],f['revision'],start,q)) for _ in range(2)]
 for p in ps:p.start()
 start.set(); results=[q.get(timeout=15) for _ in ps]
 for p in ps:p.join(15)
 require(sum(x[0]=='ok' for x in results)==1 and sum(x[0]=='error' for x in results)==1,'race')
def test_api_get_and_post_actions():
 f=make(); status,p=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'start_triage','finding_id':f['finding_id'],'expected_revision':f['revision'],'operator_confirmed':True},{}); require(status==200,'start api'); rev=p['data']['finding_revision']; status,p=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'set_triage_disposition','finding_id':f['finding_id'],'disposition':'acknowledged','expected_revision':rev,'operator_confirmed':True},{}); require(status==200,'disposition api'); status,p=api_server.handle_api_get('/api/conversation/evaluation-finding-triage',{'finding_id':[f['finding_id']]}); require(status==200 and p['data']['triage_disposition']=='acknowledged','get api')
def test_no_priority_task_patch_or_release_authority():
 f=make(); r=triage.build_evaluation_finding_triage(f['finding_id'])
 for key in ('priority_assigned','autonomous_prioritization','automatic_task_created','automatic_work_item_created','patch_generated','patch_reviewed','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[key] is False,f'authority {key}')
def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.4-finding-triage-review')==1 and names.index('v1089.4-finding-triage-review')<names.index('v1089.3-finding-aggregation'),'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.4-finding-triage-review','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
