from __future__ import annotations
import argparse,concurrent.futures,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-5-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
from conversation_sessions import create_conversation_session
import conversation_daily_evaluation as daily
import conversation_evaluation_finding as finding
import repair_candidate_registration as registration
import repair_candidate_lineage as lineage
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)
def fixture(count=3):
 s=create_conversation_session('candidate lineage',select_session=False); e=daily.start_daily_evaluation(s['id'],operator_confirmed=True); f=finding.create_evaluation_finding(finding_title='PRIVATE_FINDING_1090_5',issue_domain='interface',severity='major',evaluation_id=e['evaluation_id'],operator_confirmed=True); current=f; candidates=[]
 for i in range(count):
  regs=registration.register_repair_candidate(f['finding_id'],candidate_kind='source_archive',artifact_sha256=f'{i+1:x}'*64,label=f'PRIVATE_LABEL_{i}',private_reference=f'PRIVATE_REF_{i}',expected_revision=current['revision'],operator_confirmed=True); current={'revision':regs['finding_revision']}; candidates.append(regs['candidates'][-1])
 return f,current,candidates
def link(f,current,c,**kw):
 return lineage.link_repair_candidate_lineage(f['finding_id'],predecessor_candidate_id=kw.get('predecessor',c[0]['candidate_id']),successor_candidate_id=kw.get('successor',c[1]['candidate_id']),relation_kind=kw.get('relation_kind','replaces'),evidence_digest=kw.get('evidence_digest','a'*64),note=kw.get('note','PRIVATE_LINEAGE_NOTE'),expected_revision=kw.get('expected_revision',current.get('revision',current.get('finding_revision'))),operator_confirmed=kw.get('operator_confirmed',True))

def test_confirmation_and_exact_revision_required():
 f,current,c=fixture()
 for confirmed,rev in ((False,current['revision']),(True,None),(True,current['revision']-1)):
  try:link(f,current,c,operator_confirmed=confirmed,expected_revision=rev)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError('unguarded lineage')
def test_distinct_registered_candidates_and_kind_are_required():
 f,current,c=fixture()
 cases=[{'successor':c[0]['candidate_id']},{'successor':'repair_candidate_'+'f'*16},{'relation_kind':'beats'}]
 for kw in cases:
  try:link(f,current,c,**kw)
  except finding.EvaluationFindingError:pass
  else:raise AssertionError(f'invalid accepted {kw}')
def test_lineage_preserves_history_and_supersedes_only_predecessor():
 f,current,c=fixture(); r=link(f,current,c); private=finding.load_evaluation_finding_private(f['finding_id']); rows={x['candidate_id']:x for x in private['repair_candidate_review_records']}; require(rows[c[0]['candidate_id']]['review_state']=='superseded' and rows[c[1]['candidate_id']]['review_state']=='registered' and len(rows)==3,'states'); require(r['historical_candidates_preserved'],'history')
def test_private_note_is_digest_only_publicly():
 f,current,c=fixture(); r=link(f,current,c); encoded=json.dumps(r,sort_keys=True); require('PRIVATE_LINEAGE_NOTE' not in encoded,'note leak'); require(r['lineage_edges'][0]['private_note_digest'],'digest'); require(not lineage.repair_candidate_lineage_contains_private_fields(r),'private key')
def test_duplicate_edge_is_idempotent():
 f,current,c=fixture(); first=link(f,current,c); dup=link(f,first,c,expected_revision=first['finding_revision']); require(dup['duplicate_lineage_edge'] and dup['finding_revision']==first['finding_revision'] and dup['lineage_edge_count']==1,'duplicate')
def test_predecessor_cannot_gain_ambiguous_second_successor():
 f,current,c=fixture(); first=link(f,current,c)
 try:link(f,first,c,successor=c[2]['candidate_id'],expected_revision=first['finding_revision'])
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('ambiguous successor')
def test_cycles_are_rejected():
 f,current,c=fixture(); first=link(f,current,c); second=link(f,first,c,predecessor=c[1]['candidate_id'],successor=c[2]['candidate_id'],expected_revision=first['finding_revision'])
 try:link(f,second,c,predecessor=c[2]['candidate_id'],successor=c[0]['candidate_id'],expected_revision=second['finding_revision'])
 except finding.EvaluationFindingError:pass
 else:raise AssertionError('cycle')
def test_same_revision_race_allows_one_writer():
 f,current,c=fixture()
 def call(successor):
  try:return link(f,current,c,successor=successor)['lineage_edge_count']
  except finding.EvaluationFindingError:return 'stale'
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: results=list(ex.map(call,[c[1]['candidate_id'],c[2]['candidate_id']]))
 require(results.count('stale')==1 and len([x for x in results if isinstance(x,int)])==1,'race')
def test_get_and_post_api_routes():
 f,current,c=fixture(); status,payload=api_server.handle_api_post('/api/conversation/evaluation-finding',{'action':'link_candidate_lineage','finding_id':f['finding_id'],'predecessor_candidate_id':c[0]['candidate_id'],'successor_candidate_id':c[1]['candidate_id'],'relation_kind':'supersedes','evidence_digest':'b'*64,'expected_revision':current['revision'],'operator_confirmed':True},{}); require(status==200 and payload['data']['lineage_edge_count']==1,'POST'); status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-lineage',{'finding_id':[f['finding_id']]}); require(status==200 and payload['data']['relation_kind_counts']['supersedes']==1,'GET')
def test_lineage_is_append_only_with_no_delete_action():
 source=(ROOT/'conscious_agent'/'api_server.py').read_text(); require('remove_candidate_lineage' not in source and 'delete_candidate_lineage' not in source,'delete action'); f,current,c=fixture(); r=link(f,current,c); require(r['lineage_edges_immutable'],'immutable')
def test_no_selection_ranking_or_protected_authority():
 f,current,c=fixture(); r=link(f,current,c)
 for k in ('automatic_candidate_selection','candidate_ranked','winner_selected','automatic_test_execution','automatic_task_created','automatic_work_item_created','patch_generated','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','writes_state'): require(r[k] is False,k)
def test_registration_order_and_source_only_privacy():
 require(not (ROOT/'data'/'conversation_evaluation_findings').exists(),'runtime packaged'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.5-candidate-supersession-lineage')==1 and names.index('v1090.5-candidate-supersession-lineage')<names.index('v1090.4-bounded-candidate-comparison'),'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.5-candidate-supersession-lineage','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
