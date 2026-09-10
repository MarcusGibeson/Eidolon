from pathlib import Path
import tempfile, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.structural_salience_signals import StructuralSalienceSignalStore, build_structural_salience_signal_inspection
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 root=Path(td); store=StructuralSalienceSignalStore(root)
 r=store.register('e1',salience_category='objective_progress',source_type='objective',source_id='o1',related_source_type='milestone',related_source_id='m1',relevance=.9,importance=.8,urgency=.3,uncertainty=.2,temporal_pressure=.4,persistence=.9,novelty=.2,sensitivity='normal',interruptibility=.7,recovery_compatibility=.8,confidence=.9,structural_digest='d1')
 req(r['status']=='structural_salience_signal_registered'); sid=r['result']['signal_id']
 req(store.register('e1',salience_category='objective_progress',source_type='objective',source_id='o1')['idempotent'])
 req(store.register('e2',salience_category='objective_progress',source_type='objective',source_id='o1',related_source_type='milestone',related_source_id='m1',structural_digest='d1')['status']=='duplicate_salience_signal_ignored')
 n=store.register('e3',salience_category='conversation_relevance',source_type='conversation_relevance_marker',source_id='conversation-marker-1',relevance=.2,importance=.2,urgency=.2,persistence=.1,novelty=.9)['result']['signal_id']
 snap=store.snapshot(); durable=next(x for x in snap['signals'] if x['signal_id']==sid); novelty=next(x for x in snap['signals'] if x['signal_id']==n)
 req(durable['durable_salience'] and not durable['transient_novelty']); req(novelty['transient_novelty'] and not novelty['durable_salience'])
 req(durable['importance']!=durable['urgency'] and durable['uncertainty']!=durable['sensitivity'])
 req(all(not durable[k] for k in ('attention_review_candidate_id','selected_attention_id','reflection_id','intention_id','initiative_id','message_id','notification_id','proposal_id','approval_id','authorization_id','action_id')))
 req(store.revise('e4',sid,new_state='corrected')['status']=='structural_salience_signal_revised')
 info=build_structural_salience_signal_inspection(root); req(info['contract_version']=='v1123.0' and info['signal_count']==2); req(not any(info['authority_boundary'].values())); req(not any(info[k] for k in ('raw_messages_exposed','raw_content_exposed','prompts_exposed','provider_payloads_exposed','evidence_text_exposed','hidden_reasoning_exposed','private_content_exposed')))
print(f"v1123.0 structural salience signals: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==11 else 1)
