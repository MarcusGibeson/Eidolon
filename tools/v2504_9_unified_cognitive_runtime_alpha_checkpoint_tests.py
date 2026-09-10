from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.unified_cognitive_state_frame import build_unified_cognitive_state_frame
from conscious_agent.cognitive_operation_registry import build_cognitive_operation_registry,verify_cognitive_operation_registry
from conscious_agent.cognitive_operation_arbitration import arbitrate_cognitive_operation
from conscious_agent.cognitive_thought_continuity import CognitiveThoughtContinuityStore
from conscious_agent.cognitive_outcome_integration import CognitiveOutcomeIntegrationStore
from conscious_agent.cognitive_cycle_receipts_v2504 import CognitiveCycleReceiptStore
from conscious_agent.unified_cognitive_runtime_v2504 import UnifiedCognitiveRuntime
from conscious_agent.endogenous_cognitive_cycle import EndogenousCognitiveCycle
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2504-9-') as td:
 root=Path(td)
 # Existing endogenous cycle remains compatible and independent.
 legacy=EndogenousCognitiveCycle(root);legacy_before=legacy.inspection_summary();rt=UnifiedCognitiveRuntime(root)
 idle=rt.begin_cycle('alpha-idle',trigger_type='cadence');req(idle['selected_operation']=='REST','idle_deliberate_rest')
 req(legacy.inspection_summary()['cycle_count']==legacy_before['cycle_count'],'legacy_cycle_not_mutated')
 # Existing cognitive demand becomes visible in one authoritative frame.
 demands=CognitiveDemandStore(root);demands.register('d1',origin_type='objective',origin_id='goal-42',urgency=.9,importance=.9,cognitive_cost=.1,deadline_pressure=.7)
 frame=build_unified_cognitive_state_frame(root,trigger_type='manual_review',trigger_ref='raw private trigger sentence should be digested')
 req(frame['projection']['demands']['candidate_count']==1,'demand_projected');req('raw private trigger sentence' not in json.dumps(frame),'trigger_private_text_absent')
 arb=arbitrate_cognitive_operation(frame);req(arb['selected_operation'] in {'REVIEW_GOAL','PLAN','REFLECT','RECALL_MEMORY'},'demand_drives_cognition')
 # New experience path opens one bounded ticket and can retain continuation across restart.
 start=rt.begin_cycle('alpha-experience',trigger_type='completed_work',subject_ref='This is raw subject text that must not be stored',new_experience=True)
 req(start['requires_completion'],'ticket_required');req(start['subject_ref'].startswith('subject-digest:'),'raw_subject_digest_only')
 cont=rt.complete_cycle('alpha-cont',cycle_id=start['cycle_id'],work_ticket_id=start['work_ticket_id'],outcome_type='THOUGHT_CONTINUATION',evidence_digests=['b'*64])
 req(cont['thought_status']=='unfinished','continuation_retained')
 restarted=UnifiedCognitiveRuntime(root);resume=restarted.begin_cycle('alpha-resume',trigger_type='cadence');req(resume['selected_operation']=='CONTINUE_THOUGHT','restart_resumes_unfinished');req(resume['subject_ref']==start['subject_ref'],'restart_subject_bound')
 done=restarted.complete_cycle('alpha-done',cycle_id=resume['cycle_id'],work_ticket_id=resume['work_ticket_id'],outcome_type='NO_DURABLE_CHANGE')
 req(done['thought_status']=='completed','resume_can_complete')
 # Candidate outcomes remain unapplied and receipts expose no hidden reasoning.
 mem=restarted.begin_cycle('alpha-mem',trigger_type='completed_work',subject_ref='experience-2',new_experience=True)
 result=restarted.complete_cycle('alpha-mem-done',cycle_id=mem['cycle_id'],work_ticket_id=mem['work_ticket_id'],outcome_type='MEMORY_INTEGRATION_CANDIDATE',changed_fields=['summary'],confidence=.8)
 req(result['candidate_target']=='memory' and not result['candidate_applied'],'candidate_only')
 inspection=restarted.inspection_summary();req(inspection['open_cycle_count']==0,'all_cycles_closed');req(inspection['outcomes']['outcome_count']==3,'outcomes_accounted');req(inspection['receipts']['receipt_count']>=4,'receipts_present')
 req(all(not row['hidden_reasoning_exposed'] for row in inspection['receipts']['recent_receipts']),'receipt_privacy')
 req(not inspection['provider_contacted'] and not inspection['message_sent'] and not inspection['external_action_executed'],'no_external_effects')
 req(not inspection['source_mutated'] and not inspection['authority_broadened'],'source_authority_unchanged')
 registry=build_cognitive_operation_registry();req(verify_cognitive_operation_registry(registry),'operation_registry_valid');req(registry['default_operation']=='REST','rest_first_class')
 # Malformed runtime state fails safe to defaults, never broadens authority.
 bad=Path(root)/'malformed';bad.mkdir();(bad/'unified_cognitive_runtime_state.json').write_text('{broken',encoding='utf-8');mal=UnifiedCognitiveRuntime(bad).inspection_summary();req(mal['cycle_count']==0,'malformed_state_defaults');req(not mal['authority_boundary']['can_execute_action'],'malformed_no_authority')
 # Dedicated stores stay separated and content-bounded.
 req(CognitiveThoughtContinuityStore(root).inspection_summary()['raw_chain_of_thought_stored'] is False,'thought_store_no_cot')
 req(CognitiveOutcomeIntegrationStore(root).inspection_summary()['authority_boundary']['can_apply_candidate'] is False,'outcome_store_no_apply')
 req(CognitiveCycleReceiptStore(root).inspection_summary()['authority_boundary']['receipt_can_execute_action'] is False,'receipt_store_no_execute')
print(json.dumps({'ok':True,'checkpoint_version':'2504.9','contract':'Unified Cognitive Runtime Alpha','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
