from __future__ import annotations
import os,tempfile
from pathlib import Path
from conscious_agent.decision_review_registry import record_decision_review_candidates,inspect_decision_review_registry
import conscious_agent.conversation_cognitive_backbone as backbone


def _boundary(prop='preview the repair in a sandbox',risk='low',rev='high'):
 return {'cases':[{'boundary_id':'b1','state':'candidate_recommendation','candidate_option_id':'o1','candidate_proposition':prop,'evidence_sufficient':True,'prerequisites_complete':True,'risk_level':risk,'reversibility':rev,'operator_approval_required':True}]}

def run():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition'
  r=record_decision_review_candidates(operation_id='op1',session_id='s1',boundary=_boundary(),runtime_root=root)
  checks += [r['contract_version'] in {'v1154.5','v1154.8','v1154.9'},r['review_item_count']==1,r['operator_review_required']]
  item=r['review_items'][0]
  checks += [item['review_readiness']=='ready_for_operator_review',item['estimated_cost']=='low',item['resource_demand']=='low',item['rollback_plan_quality']=='sufficient_for_review']
  checks += [not item['approval_request_created'],not item['decision_created'],not item['execution_permitted'],not item['action_authority']]
  again=record_decision_review_candidates(operation_id='op1',session_id='s1',boundary=_boundary(),runtime_root=root)
  checks.append(again['review_item_id'] if 'review_item_id' in again else again['review_items'][0]['review_item_id'] == item['review_item_id'])
  blocked=record_decision_review_candidates(operation_id='op2',session_id='s1',boundary=_boundary('replace production immediately','high','unknown'),runtime_root=root)
  checks += [blocked['review_items'][0]['review_readiness']=='blocked_for_more_detail',blocked['review_items'][0]['rollback_plan_quality']=='missing']
  empty=record_decision_review_candidates(operation_id='op3',session_id='s1',boundary={'cases':[]},runtime_root=root)
  checks += [empty['review_item_count']==0,not empty['operator_review_required']]
  inspect=inspect_decision_review_registry(root)
  checks += [inspect['record_count']==3,inspect['review_item_count']==2,inspect['ready_count']==1,inspect['blocked_count']==1,not inspect['content_exposed'],inspect['authority_preserved']]
  os.environ['EIDOLON_DATA_DIR']=td
  old=backbone.build_decision_boundary
  backbone.build_decision_boundary=lambda *a,**k:_boundary()
  try:
   out=backbone.record_turn_completion_safely(operation_id='turn-op',session_id='sess',user_message='what should we do',assistant_response='we should review it',source='test')
  finally: backbone.build_decision_boundary=old
  checks += [out['completion_state']=='completed',out['decision_review_recorded'],out['decision_review_item_count']==1,not out.get('authority_broadened',False)]
 print(f'v1154.3-v1154.5 decision-boundary integration tests: {sum(bool(x) for x in checks)}/{len(checks)}')
 if not all(checks):
  print([i+1 for i,x in enumerate(checks) if not x]); raise SystemExit(1)

if __name__=='__main__': run()
