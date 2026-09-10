from __future__ import annotations
import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.cognitive_outcome_integration import CognitiveOutcomeIntegrationStore
from conscious_agent.cognitive_cycle_receipts_v2504 import CognitiveCycleReceiptStore
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2504-4-5-') as td:
 root=Path(td);out=CognitiveOutcomeIntegrationStore(root)
 r=out.record('o1',cycle_id='cycle-1',operation='REFLECT',outcome_type='NO_DURABLE_CHANGE',target='none',subject_ref='subject-1');req(r['ok'],'outcome_ok');req(r['outcome_type']=='NO_DURABLE_CHANGE','no_change_type')
 r2=out.record('o2',cycle_id='cycle-2',operation='RECONSIDER_BELIEF',outcome_type='BELIEF_REVISION_CANDIDATE',target='beliefs',subject_ref='belief-1',changed_fields=['confidence'],confidence=.7);req(r2['target']=='beliefs','candidate_target')
 s=out.inspection_summary();req(s['outcome_count']==2,'outcome_count');req(all(not x['applied'] for x in s['recent_outcomes']),'candidates_not_applied');req(not s['authority_boundary']['can_apply_candidate'],'outcome_no_apply_authority')
 try:out.record('bad',cycle_id='c',operation='REFLECT',outcome_type='NO_DURABLE_CHANGE',target='beliefs');raise AssertionError('must reject invalid target')
 except ValueError:checks.append('no_change_target_guard')
 receipts=CognitiveCycleReceiptStore(root);rr=receipts.append('r1',{'cycle_id':'cycle-1','trigger_type':'manual_review','frame_digest':'a'*64,'selected_operation':'REST','selected_utility':.4,'status':'no_useful_cognitive_action','subject_ref':''});req(rr['ok'],'receipt_ok')
 ri=receipts.inspection_summary();req(ri['receipt_count']==1,'receipt_count');req(ri['recent_receipts'][0]['communication']=='none','receipt_no_communication');req(not ri['recent_receipts'][0]['hidden_reasoning_exposed'],'receipt_no_cot');req(not ri['authority_boundary']['receipt_can_execute_action'],'receipt_no_execution')
print(json.dumps({'ok':True,'contract':'v2504.4-v2504.5','passed':len(checks),'checks':checks},sort_keys=True))
