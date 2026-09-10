from pathlib import Path
import tempfile
from conscious_agent.selected_attention_records import SelectedAttentionStore

def main():
 checks=[]
 def ck(name,ok): checks.append((name,bool(ok)))
 with tempfile.TemporaryDirectory() as td:
  s=SelectedAttentionStore(Path(td))
  r=s.select('e1',outcome_id='o1',candidate_id='c1',session_id='s1',outcome='retain_for_review',importance=.9,relevance=.9)
  ck('ineligible outcome restrained',not r['attention_selected'])
  r=s.select('e2',outcome_id='o2',candidate_id='c2',session_id='s2',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,operator_review_required=True)
  ck('operator review boundary',r['status']=='requires_operator_review')
  r=s.select('e3',outcome_id='o3',candidate_id='c3',session_id='s3',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,recovery_compatible=False)
  ck('recovery boundary',r['status']=='deferred_for_recovery')
  r=s.select('e4',outcome_id='o4',candidate_id='c4',session_id='s4',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,uncertainty=.2)
  ck('selection recorded',r['status']=='selected_attention_recorded' and r['attention_selected'])
  d=s.select('e4',outcome_id='o4',candidate_id='c4',session_id='s4',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9)
  ck('event idempotency',d['idempotent'])
  x=s.select('e5',outcome_id='o4',candidate_id='c4',session_id='s4',outcome='prioritize_for_bounded_attention',importance=.9,relevance=.9,uncertainty=.2)
  ck('semantic duplicate suppression',x['status']=='duplicate_selection_suppressed')
  aid=r['attention_id']; t=s.transition('e6',attention_id=aid,state='suspended')
  ck('lifecycle transition',t['state']=='suspended')
  snap=s.snapshot(); ck('history preserved',len(snap['records'][0]['history'])==2)
  info=s.inspection_summary(); ck('authority separation',not info['reflection_created'] and not info['external_action_executed'])
  ck('content free record','text' not in str(snap['records'][0]).lower())
 for n,ok in checks: print(('PASS' if ok else 'FAIL')+': '+n)
 print(f'{sum(ok for _,ok in checks)}/{len(checks)}')
 return 0 if all(ok for _,ok in checks) else 1
if __name__=='__main__': raise SystemExit(main())
