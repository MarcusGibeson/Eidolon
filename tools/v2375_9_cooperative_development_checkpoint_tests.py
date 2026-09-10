from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2375-data-')
from cooperative_development_v2300 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2375-runtime-')); A='a'*64; B='b'*64; C='c'*64
l=register_work(work_id='w1',owner_kind='browser',base_manifest_digest=A,intent_digest=B,touched_paths=['conscious_agent/a.py'],event_id='e1',runtime_root=runtime)
req(l['ok'] and l['work']['state']=='active','browser_work_registered')
r=register_work(work_id='w2',owner_kind='desktop_codex',base_manifest_digest=A,intent_digest=C,touched_paths=['conscious_agent/b.py'],event_id='e2',runtime_root=runtime)
req(r['ok'],'codex_work_registered')
req(register_work(work_id='w1',owner_kind='browser',base_manifest_digest=A,intent_digest=B,touched_paths=[],event_id='e3',runtime_root=runtime)['status']=='work_identity_already_active','active_work_not_displaced')
req(register_work(work_id='bad',owner_kind='mystery',base_manifest_digest=A,intent_digest=B,touched_paths=[],event_id='e4',runtime_root=runtime)['ok'] is False,'unknown_owner_rejected')
req(register_work(work_id='bad2',owner_kind='browser',base_manifest_digest=A,intent_digest=B,touched_paths=['../escape'],event_id='e5',runtime_root=runtime)['ok'] is False,'path_traversal_rejected')
cmp=compare_work_candidates(l['work'],r['work'],current_manifest_digest=A)
req(cmp['disposition']=='independent_candidates_mergeable_in_principle' and cmp['overlap_count']==0,'independent_candidates_recognized')
plan=prepare_merge_plan(comparison=cmp,left_candidate_digest=B,right_candidate_digest=C)
req(plan['ok'] and plan['merge_preparation_permitted'] and plan['actual_merge_performed'] is False,'merge_plan_preparation_nonmutating')
over=register_work(work_id='w3',owner_kind='eidolon',base_manifest_digest=A,intent_digest='d'*64,touched_paths=['conscious_agent/a.py'],event_id='e6',runtime_root=runtime)['work']
cmp2=compare_work_candidates(l['work'],over,current_manifest_digest=A)
req(cmp2['disposition']=='manual_conflict_review_required' and cmp2['overlap_count']==1,'overlap_conflict_detected')
req(not prepare_merge_plan(comparison=cmp2,left_candidate_digest=B,right_candidate_digest='d'*64)['merge_preparation_permitted'],'conflict_blocks_merge_plan')
drift=compare_work_candidates(l['work'],r['work'],current_manifest_digest='e'*64)
req(drift['disposition']=='rebase_required' and drift['source_drift'],'source_drift_requires_rebase')
same_intent=register_work(work_id='w4',owner_kind='desktop_codex',base_manifest_digest=A,intent_digest=B,touched_paths=['conscious_agent/c.py'],event_id='e6b',runtime_root=runtime)['work']
dup=compare_work_candidates(l['work'],same_intent,current_manifest_digest=A)
req(dup['disposition']=='duplicate_intent_review_required','duplicate_intent_detected')
stale=revise_work(work_id='w1',expected_lease_digest='f'*64,action='release',event_id='e7',runtime_root=runtime)
req(not stale['ok'] and stale['status']=='stale_work_lease_digest','stale_lease_rejected')
rel=revise_work(work_id='w1',expected_lease_digest=l['work']['lease_digest'],action='release',event_id='e8',runtime_root=runtime)
req(rel['ok'] and rel['work']['state']=='released','digest_bound_release')
state=inspect_work_coordination(runtime_root=runtime)
req(state['coordination_is_advisory_only'] and state['retained_operation_owner']=='ownership_concurrency','existing_execution_owner_preserved')
req(all(not plan[k] for k in ('source_modified','candidate_merged','candidate_applied','installation_authorized','authority_expanded')),'cooperation_authority_inert')
print(json.dumps({'suite':'v2375.9-cooperative-development','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
