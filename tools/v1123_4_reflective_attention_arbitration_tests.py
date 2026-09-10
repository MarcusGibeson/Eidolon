from pathlib import Path
import tempfile
from conscious_agent.structural_salience_signals import StructuralSalienceSignalStore
from conscious_agent.reflective_attention_review_candidates import ReflectiveAttentionReviewCandidateStore
from conscious_agent.reflective_attention_deliberation import ReflectiveAttentionDeliberationStore
from conscious_agent.reflective_attention_arbitration import ReflectiveAttentionArbitrator
checks=[]
def req(x): checks.append(bool(x))
def session(root,n,operator=False,overlap=False,recovery=.8):
 sig=StructuralSalienceSignalStore(root); sid=sig.register(f's{n}',salience_category='objective_progress',source_type='objective',source_id=f'o{n}',relevance=.8,importance=.8,urgency=.4,uncertainty=.2,persistence=.8,novelty=.2,recovery_compatibility=recovery,confidence=.8,structural_digest=n)['result']['signal_id']; cand=ReflectiveAttentionReviewCandidateStore(root,signals=sig); cid=cand.register(f'c{n}',signal_ids=[sid],cognitive_load=.3,recovery_compatibility=recovery,operator_review_required=operator,confidence=.8,uncertainty=.2,structural_digest=n)['result']['candidate_id']; return ReflectiveAttentionDeliberationStore(root).open(f'e{n}',candidate_id=cid)['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 root=Path(td); arb=ReflectiveAttentionArbitrator(root)
 req(arb.arbitrate('a1',session_id=session(root,'1'),relevance=.9,importance=.9,persistence=.8,uncertainty=.2)['arbitration']['outcome']=='prioritize_for_bounded_attention')
 req(arb.arbitrate('a2',session_id=session(root,'2'),recovery_constraint=.9)['arbitration']['outcome']=='defer_for_recovery')
 req(arb.arbitrate('a3',session_id=session(root,'3'),overlap_strength=.9)['arbitration']['outcome']=='merge_overlap')
 req(arb.arbitrate('a4',session_id=session(root,'4'),relevance=.1,importance=.1,urgency=.1)['arbitration']['outcome']=='deliberate_non_selection')
 req(arb.arbitrate('a5',session_id=session(root,'5'),force_unresolved=True)['arbitration']['outcome']=='unresolved')
 req(arb.arbitrate('a6',session_id=session(root,'6',True))['arbitration']['outcome']=='requires_operator_review')
 req(arb.arbitrate('a7',session_id=session(root,'7'),relevance=.5,importance=.5,persistence=.5,uncertainty=.4)['arbitration']['outcome']=='retain_for_review')
 x=arb.inspection_summary(); req(x['contract_version']=='v1123.4'); req(not any(x[k] for k in ('attention_selected','reflection_created','initiative_created','message_sent','external_action_executed'))); req(not any(x['authority_boundary'].values()))
print(f"v1123.4 reflective attention arbitration: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
