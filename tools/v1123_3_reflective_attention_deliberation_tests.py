from pathlib import Path
import tempfile
from conscious_agent.structural_salience_signals import StructuralSalienceSignalStore
from conscious_agent.reflective_attention_review_candidates import ReflectiveAttentionReviewCandidateStore
from conscious_agent.reflective_attention_deliberation import ReflectiveAttentionDeliberationStore
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); sig=StructuralSalienceSignalStore(root); sid=sig.register('s1',salience_category='objective_progress',source_type='objective',source_id='o1',relevance=.8,importance=.9,urgency=.4,uncertainty=.2,persistence=.8,novelty=.2,recovery_compatibility=.8,confidence=.9,structural_digest='s')['result']['signal_id']; cand=ReflectiveAttentionReviewCandidateStore(root,signals=sig); cid=cand.register('c1',signal_ids=[sid],cognitive_load=.3,recovery_compatibility=.8,confidence=.9,uncertainty=.2,structural_digest='c')['result']['candidate_id']; store=ReflectiveAttentionDeliberationStore(root); r=store.open('e1',candidate_id=cid); session=r['result']['session_id']; req(r['status']=='reflective_attention_deliberation_opened'); req(store.open('e1',candidate_id=cid)['idempotent']); req(store.open('e2',candidate_id=cid)['status']=='active_attention_review_session_reused'); out=store.record_outcome('e3',session_id=session,outcome='retain_for_review'); req(out['result']['outcome']=='retain_for_review'); req(not out['result']['attention_selected'] and not out['result']['reflection_created']); snap=store.inspection_summary(); req(snap['contract_version']=='v1123.3'); req(snap['session_count']==1); req(snap['outcome_counts'].get('retain_for_review')==1); req(not any(snap['authority_boundary'].values())); req(not snap['hidden_reasoning_exposed'])
print(f"v1123.3 reflective attention deliberation: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)
