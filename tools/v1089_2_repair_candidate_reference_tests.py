from __future__ import annotations
import argparse,json,multiprocessing,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import conversation_evaluation_finding_reproducibility as repro
import conversation_evaluation_finding_repair_candidates as repairs
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def make():
 s=create_conversation_session('Repair ref session',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); return finding.create_evaluation_finding(finding_title='PRIVATE_REPAIR_FINDING',finding_details='private',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True)
def add(f,value='PRIVATE_REPAIR_REFERENCE',**kw): return repairs.add_repair_candidate_reference(f['finding_id'],reference_kind=kw.get('kind','patch_candidate'),reference_value=value,label=kw.get('label','PRIVATE_REPAIR_LABEL'),expected_revision=kw.get('expected_revision',f['revision']),operator_confirmed=kw.get('operator_confirmed',True))
def _race_worker(fid,revision,value,start,q):
 start.wait()
 try: r=repairs.add_repair_candidate_reference(fid,reference_kind='external_work_item',reference_value=value,expected_revision=revision,operator_confirmed=True); q.put(('ok',r['finding_revision']))
 except Exception as e: q.put(('error',type(e).__name__))

def test_add_requires_confirmation_and_exact_revision():
 f=make()
 for confirmed,rev in [(False,f['revision']),(True,None),(True,f['revision']-1)]:
  try: add(f,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError: pass
  else: raise AssertionError('unguarded reference accepted')

def test_reference_kind_is_validated():
 f=make()
 try: add(f,kind='automatic_patch')
 except finding.EvaluationFindingError: pass
 else: raise AssertionError('bad kind accepted')

def test_private_reference_and_label_are_digest_only_publicly():
 f=make(); result=add(f); encoded=json.dumps(result,sort_keys=True); require('PRIVATE_REPAIR_REFERENCE' not in encoded and 'PRIVATE_REPAIR_LABEL' not in encoded,'private repair reference leaked'); require(result['references'][0]['reference_digest'] and result['references'][0]['label_digest'],'digests absent')

def test_private_record_retains_reference_content():
 f=make(); add(f); row=finding.load_evaluation_finding_private(f['finding_id'])['repair_candidate_refs'][0]; require(row['private_reference_value']=='PRIVATE_REPAIR_REFERENCE' and row['private_label']=='PRIVATE_REPAIR_LABEL','private reference missing')

def test_reproducibility_status_is_captured_at_link_time():
 f=make(); rr=repro.record_reproduction_attempt(f['finding_id'],outcome='reproduced',environment_kind='same_environment',expected_revision=f['revision'],operator_confirmed=True); result=repairs.add_repair_candidate_reference(f['finding_id'],reference_kind='test_case',reference_value='case-1',expected_revision=rr['finding_revision'],operator_confirmed=True); require(result['references'][0]['reproducibility_status_at_link']=='confirmed','repro status not captured')

def test_duplicate_open_reference_is_idempotent():
 f=make(); first=add(f); duplicate=repairs.add_repair_candidate_reference(f['finding_id'],reference_kind='patch_candidate',reference_value='PRIVATE_REPAIR_REFERENCE',label='different label',expected_revision=first['finding_revision'],operator_confirmed=True); require(duplicate['duplicate_reference'] and duplicate['reference_count']==1 and duplicate['finding_revision']==first['finding_revision'],'duplicate mutated')

def test_reference_state_and_label_update_is_explicit():
 f=make(); first=add(f); rid=first['references'][0]['repair_reference_id']; updated=repairs.update_repair_candidate_reference(f['finding_id'],rid,state='under_review',label='new private label',expected_revision=first['finding_revision'],operator_confirmed=True); require(updated['state_counts']['under_review']==1 and updated['finding_revision']==first['finding_revision']+1,'update failed')

def test_reference_removal_is_explicit():
 f=make(); first=add(f); rid=first['references'][0]['repair_reference_id']; removed=repairs.remove_repair_candidate_reference(f['finding_id'],rid,expected_revision=first['finding_revision'],operator_confirmed=True); require(removed['reference_count']==0,'remove failed')

def test_cross_process_same_revision_allows_exactly_one_writer():
 f=make(); ctx=multiprocessing.get_context('spawn'); start=ctx.Event(); q=ctx.Queue(); ps=[ctx.Process(target=_race_worker,args=(f['finding_id'],f['revision'],f'race-{i}',start,q)) for i in range(2)]
 for p in ps: p.start()
 start.set(); results=[q.get(timeout=15) for _ in ps]
 for p in ps: p.join(15)
 require(sum(1 for x in results if x[0]=='ok')==1 and sum(1 for x in results if x[0]=='error')==1,'race did not serialize')

def test_api_get_and_post_routes():
 f=make(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'add_repair_candidate','finding_id':f['finding_id'],'reference_kind':'source_archive','reference_value':'private-archive-id','expected_revision':f['revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['reference_count']==1,'api add failed'); status,payload=api_server.handle_api_get('/api/conversation/evaluation-finding-repair-candidates',{'finding_id':[f['finding_id']]}); require(status==200 and payload['data']['reference_count']==1,'api get failed')

def test_no_patch_task_or_release_authority():
 f=make(); result=add(f)
 for key in ('automatic_task_created','automatic_work_item_created','autonomous_prioritization','patch_generated','patch_reviewed','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_certified','provider_invoked','writes_state'): require(result[key] is False,f'authority escalated {key}')

def test_source_only_and_registration():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1089.2-repair-candidate-references')==1 and names.index('v1089.2-repair-candidate-references')<names.index('v1089.1-finding-reproducibility-review'),'registration wrong')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
 for name,fn in TESTS:
  try: fn()
  except Exception as e: checks.append({'name':name,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
 report={'suite':'v1089.2-repair-candidate-references','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
