from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2475-data-')
from autonomous_developer_beta_v2400 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
D='a'*64
contract=build_goal_to_candidate_contract(goal_id='g1',goal_digest=D,baseline_source_digest='b'*64,scope_digest='c'*64,maximum_stage_failures=1,maximum_replans=1)
req(contract['ok'] and contract['stages'][0]=='requirements','goal_contract_ready')
req('goal_id' not in contract and len(contract['goal_id_digest'])==64,'goal_identity_content_free')
req(contract['stage_owners']['implementation']=='supervised_development_coordinator','existing_implementation_owner_reused')
req(contract['final_state']=='review_ready' and contract['installation_is_out_of_scope'],'review_ready_not_installation')
req(not build_goal_to_candidate_contract(goal_id='g',goal_digest='no',baseline_source_digest='b'*64,scope_digest='c'*64)['ok'],'invalid_goal_evidence_rejected')
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2475-runtime-'))
start=start_goal_to_candidate(runtime_root=runtime,event_id='start1',contract=contract)
req(start['ok'] and start['stage']=='requirements','developer_beta_started')
rep=start_goal_to_candidate(runtime_root=runtime,event_id='start1',contract=contract)
req(rep['status']=='developer_beta_start_replayed','start_exactly_once')
fake=record_stage_receipt(runtime_root=runtime,goal_id='g1',event_id='fake',expected_state_digest=start['state_digest'],stage='requirements',evidence_digest='9'*64,evidence_payload={'evidence_digest':'9'*64},outcome='passed')
req(not fake['ok'] and fake['reason']=='stage_or_evidence_invalid','random_digest_cannot_advance_stage')
state=start
for i,stage in enumerate(STAGES[:-1]):
    ev=build_stage_evidence(stage=stage,artifact_digest=f'{i+1:064x}',outcome='passed')
    row=record_stage_receipt(runtime_root=runtime,goal_id='g1',event_id=f'e{i}',expected_state_digest=state['state_digest'],stage=stage,evidence_digest=ev['evidence_digest'],evidence_payload=ev,outcome='passed')
    req(row['ok'],f'{stage}_receipt_accepted')
    state=row
req(state['stage']=='review_ready' and state['campaign_status']=='review_ready','complete_loop_reaches_review_ready')
view=inspect_goal_to_candidate(runtime_root=runtime,goal_id='g1')
req(view['ok'] and view['completed_stage_count']==9,'all_stage_receipts_persisted')
req(view['review_ready_is_not_installation'] and not view['candidate_installed'],'review_ready_boundary_preserved')
stale=record_stage_receipt(runtime_root=runtime,goal_id='g1',event_id='late',expected_state_digest='f'*64,stage='review_ready',evidence_digest=D,evidence_payload={})
req(not stale['ok'] and stale['reason']=='stale_state_digest','stale_state_rejected')
contract2=build_goal_to_candidate_contract(goal_id='g2',goal_digest=D,baseline_source_digest='b'*64,scope_digest='c'*64,maximum_stage_failures=0,maximum_replans=0)
s2=start_goal_to_candidate(runtime_root=runtime,event_id='s2',contract=contract2)
fe=build_stage_evidence(stage='requirements',artifact_digest=D,outcome='failed')
f=record_stage_receipt(runtime_root=runtime,goal_id='g2',event_id='f1',expected_state_digest=s2['state_digest'],stage='requirements',evidence_digest=fe['evidence_digest'],evidence_payload=fe,outcome='failed')
req(f['ok'] and f['campaign_status']=='blocked_failure_budget','failure_budget_enforced')
contract3=build_goal_to_candidate_contract(goal_id='g3',goal_digest=D,baseline_source_digest='b'*64,scope_digest='c'*64,maximum_stage_failures=1,maximum_replans=0)
s3=start_goal_to_candidate(runtime_root=runtime,event_id='s3',contract=contract3)
re=build_stage_evidence(stage='requirements',artifact_digest=D,outcome='replan_required')
rp=record_stage_receipt(runtime_root=runtime,goal_id='g3',event_id='r1',expected_state_digest=s3['state_digest'],stage='requirements',evidence_digest=re['evidence_digest'],evidence_payload=re,outcome='replan_required')
req(rp['campaign_status']=='blocked_replan_budget','replan_budget_enforced')
portfolio=rank_portfolio([
 {'candidate_id':'defect1','class':'defect','evidence_digest':'1'*64,'value':.9,'evidence_quality':.9,'strategic_alignment':.9,'novelty':.6,'reversibility':.9,'risk':.2,'cost_units':.4,'dependencies_satisfied':True},
 {'candidate_id':'cap1','class':'capability','evidence_digest':'2'*64,'value':.8,'evidence_quality':.7,'strategic_alignment':.8,'novelty':.9,'reversibility':.8,'risk':.3,'cost_units':.4,'dependencies_satisfied':True},
 {'candidate_id':'blocked','class':'defect','evidence_digest':'3'*64,'value':1,'evidence_quality':1,'strategic_alignment':1,'novelty':1,'reversibility':1,'risk':0,'cost_units':.1,'dependencies_satisfied':False}],budget_units=1)
req(portfolio['ok'] and portfolio['selected_candidate_id']=='defect1','portfolio_prefers_evidenced_high_value_defect')
req(next(r for r in portfolio['ranked_candidates'] if r['candidate_id']=='blocked')['eligible'] is False,'dependency_block_respected')
req(portfolio['selection_is_advisory_only'],'portfolio_selection_non_authorizing')
req(not rank_portfolio([],budget_units=float('nan'))['ok'],'nonfinite_portfolio_budget_rejected')
req(all(not view[k] for k in ('implementation_executed','tests_executed','candidate_installed','candidate_promoted','authority_expanded')),'developer_beta_coordination_non_executing')
print(json.dumps({'suite':'v2475.9-autonomous-developer-beta','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
