from pathlib import Path
import tempfile, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.structural_salience_signals import StructuralSalienceSignalStore
from conscious_agent.reflective_attention_review_candidates import ReflectiveAttentionReviewCandidateStore, build_reflective_attention_review_candidate_inspection
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); signals=StructuralSalienceSignalStore(root)
 a=signals.register('s1',salience_category='objective_progress',source_type='objective',source_id='o1',relevance=.9,importance=.8,urgency=.4,persistence=.9,novelty=.2,structural_digest='a')['result']['signal_id']
 b=signals.register('s2',salience_category='inquiry_uncertainty',source_type='active_inquiry',source_id='q1',relevance=.8,importance=.7,urgency=.3,persistence=.8,novelty=.3,structural_digest='b')['result']['signal_id']
 c=ReflectiveAttentionReviewCandidateStore(root,signals=signals)
 r=c.register('c1',signal_ids=[a,b],cognitive_load=.4,recovery_compatibility=.8,confidence=.9,uncertainty=.2,structural_digest='c'); req(r['status']=='reflective_attention_review_candidate_registered'); cid=r['result']['candidate_id']
 req(c.register('c1',signal_ids=[a,b])['idempotent']); req(c.register('c2',signal_ids=[a,b],structural_digest='c')['status']=='duplicate_attention_review_candidate_ignored')
 d=signals.register('s3',salience_category='scheduled_cognitive_work',source_type='scheduled_cognitive_work',source_id='w1',relevance=.7,importance=.7,urgency=.4,persistence=.8,novelty=.2,structural_digest='d')['result']['signal_id']
 req(c.register('c3',signal_ids=[b,d],structural_digest='overlap')['status']=='semantic_overlap_detected')
 n=signals.register('s4',salience_category='conversation_relevance',source_type='conversation_relevance_marker',source_id='m1',relevance=.2,importance=.2,urgency=.3,persistence=.1,novelty=.9,structural_digest='n')['result']['signal_id']
 req(c.register('c4',signal_ids=[n])['status']=='novelty_only_suppressed')
 u=signals.register('s5',salience_category='operator_review',source_type='operator_review_requirement',source_id='r1',relevance=.6,importance=.3,urgency=.95,persistence=.2,novelty=.4,structural_digest='u')['result']['signal_id']
 req(c.register('c5',signal_ids=[u])['status']=='false_urgency_suppressed')
 req(c.revise('c6',cid,new_state='retracted')['status']=='reflective_attention_review_candidate_revised')
 info=build_reflective_attention_review_candidate_inspection(root); req(info['contract_version']=='v1123.1' and info['candidate_count']==4); req(info['state_counts'].get('suppressed')==2); req(not any(info['authority_boundary'].values())); req(all(not (info['recent_candidates'][0].get(k)) for k in ('selected_attention_id','reflection_id','intention_id','initiative_id','message_id','notification_id','proposal_id','approval_id','authorization_id','action_id')))
print(f"v1123.1 reflective attention review candidates: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==11 else 1)
