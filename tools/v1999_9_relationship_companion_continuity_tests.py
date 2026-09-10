from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from relationship_companion_continuity_v1900 import build_relationship_model,build_continuity_candidates,build_relationship_companion_projection
checks=[]
def req(v,n): checks.append(n); assert v,n
memories=[
 {'id':'n1','type':'nickname','content':'Call the user Ace','provenance_class':'user','relationship_eligible':True},
 {'id':'p1','type':'preference','content':'Prefers concise technical answers','provenance_class':'user','relationship_eligible':True},
 {'id':'b1','type':'boundary','content':'Do not use a certain nickname','provenance_class':'user','relationship_eligible':True},
 {'id':'m1','type':'important_moment','content':'A meaningful shared milestone','provenance_class':'user','relationship_eligible':True},
 {'id':'t1','type':'trust','content':'I trust you with this project','provenance_class':'user','relationship_eligible':True},
 {'id':'bad','type':'relationship','content':'Assistant invented closeness','provenance_class':'assistant','relationship_eligible':True},
 {'id':'stale','type':'preference','content':'Old preference','provenance_class':'user','relationship_eligible':True,'status':'retracted'},
]
history=[
 {'user_message':'Actually, that is wrong.','assistant_response':"You're right, I misunderstood that correction.",'success':True},
 {'user_message':'Tell me what happens next.','assistant_response':'I can explain the next step. What part matters most?','success':True},
]
model=build_relationship_model(memories,conversation_history=history)
req(model.explicit_relationship_evidence_count==5,'only_attributable_active_relationship_evidence')
req(model.trust_basis=='explicitly_recorded','trust_requires_explicit_evidence')
req(model.nickname_count==1 and model.preference_count==1 and model.boundary_count==1,'relationship_dimensions_counted')
req(model.important_moment_count==1,'important_moment_counted')
req(model.correction_count==1 and model.acknowledged_repairs==1,'repair_after_mistake_tracked')
req(model.relationship_progress_inferred is False,'progress_not_inferred')
req(model.user_feelings_inferred is False and model.dependency_or_exclusivity_inferred is False,'feelings_dependency_not_inferred')
public=model.public_summary()
req(public['contains_relationship_content'] is False and 'Ace' not in json.dumps(public),'public_relationship_state_content_free')
none=build_relationship_model([{'type':'relationship','content':'I trust you','provenance_class':'assistant','relationship_eligible':True}],conversation_history=[])
req(none.trust_basis=='not_inferred' and none.explicit_relationship_evidence_count==0,'assistant_trust_claim_not_evidence')
candidates=build_continuity_candidates(model,conversation_history=history)
req(any(c.candidate_kind=='unfinished_thread' for c in candidates),'unfinished_thread_candidate')
req(any(c.candidate_kind=='important_moment_check_in' for c in candidates),'important_moment_candidate')
req(all(not c.autonomous_delivery_authorized for c in candidates),'no_autonomous_delivery')
req(all(not c.relationship_progress_claim_allowed for c in candidates),'no_progress_claim_from_candidate')
# Repeated candidate receipt suppresses nagging check-in.
prior=[{'candidate_kind':'unfinished_thread'},{'candidate_kind':'unfinished_thread'},{'candidate_kind':'important_moment_check_in'}]
suppressed=build_continuity_candidates(model,conversation_history=history,prior_candidate_receipts=prior)
req(not any(c.candidate_kind=='unfinished_thread' for c in suppressed),'repeated_unfinished_attention_suppressed')
req(not any(c.candidate_kind=='important_moment_check_in' for c in suppressed),'repeated_moment_attention_suppressed')
projection=build_relationship_companion_projection(memories,conversation_history=history,prior_candidate_receipts=[])
req(projection['ok'] and projection['proactive_message_sent'] is False,'projection_does_not_send')
req(projection['autonomous_new_turn_permitted'] is False,'no_new_turn_authority')
req(projection['memory_mutated'] is False and projection['authority_granted'] is False,'relationship_projection_non_mutating_non_authorizing')
req('Do not infer trust, feelings, exclusivity, dependence, or relationship progress.' in projection['prompt_section'],'prompt_relationship_boundary')
print(json.dumps({'suite':'v1999.9-relationship-companion-continuity','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
