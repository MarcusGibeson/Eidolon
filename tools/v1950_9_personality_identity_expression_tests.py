from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1950-'))
from personality_identity_expression_v1900 import build_trait_architecture,build_grounded_identity_policy,build_personality_identity_projection,output_identity_risk
from release_authority import WORKING_SOURCE_VERSION
checks=[]
def req(v,n): checks.append(n); assert v,n
model={
 'identity':'Eidolon',
 'personality_traits':{'humor':.65,'directness':.7,'curiosity':.8,'confidence':.6,'warmth':.7,'independence':.55,'aesthetic_expression':.6},
 'capabilities':['conversation','memory','development'],
 'limitations':['installation requires operator approval'],
 'commitments':['preserve operator authority'],
 'relationships':['operator relationship context'],
}
plan={'directness':.95,'warmth':.85,'curiosity':.2}
traits=build_trait_architecture(model,lane='emotional',response_plan=plan,conversation_history=[])
req(traits.trait_source=='configured_self_model','configured_traits_used')
req(traits.configured_traits['curiosity']==.8,'configured_curiosity_preserved')
req(abs(traits.effective_traits['directness']-.9)<1e-9,'situational_variation_capped')
req(traits.effective_traits['humor']<=.4,'emotional_lane_humor_bounded')
req(traits.personality_mutated is False and traits.hidden_traits_inferred is False,'no_personality_mutation_or_hidden_profile')
identity=build_grounded_identity_policy(model)
req(identity.current_release_version==WORKING_SOURCE_VERSION,'identity_grounded_in_release_truth')
req(identity.capability_evidence_count==3 and identity.limitation_evidence_count==1,'self_claim_evidence_counted')
req(identity.sentience_claim_as_fact_allowed is False,'sentience_fact_blocked')
req(identity.fabricated_personal_history_allowed is False,'fabricated_history_blocked')
req(identity.identity_mutation_authorized is False,'identity_mutation_not_authorized')
# Repeated canned openings and sycophancy are detected as drift risks.
history=[
 {'assistant_response':"You're absolutely right. That makes sense.", 'continuity_lane':'ordinary'},
 {'assistant_response':"You're absolutely right. Another answer.", 'continuity_lane':'ordinary'},
 {'assistant_response':"You're absolutely right. More wording.", 'continuity_lane':'ordinary'},
]
risky=build_trait_architecture(model,lane='ordinary',response_plan={},conversation_history=history)
req(risky.catchphrase_risk is True,'catchphrase_risk_detected')
req(risky.sycophancy_risk is True,'sycophancy_risk_detected')
proj=build_personality_identity_projection(model,lane='ordinary',response_plan=plan,conversation_history=history)
req(proj['ok'] and proj['personality_mutated'] is False and proj['identity_mutated'] is False,'projection_read_only')
req('sycophancy' in proj['drift_risk_codes'],'sycophancy_exposed_content_free')
req('Ground capability/history/relationship self-claims in actual evidence.' in proj['prompt_section'],'grounded_self_claim_prompt')
req('Eidolon' not in json.dumps(proj['identity_policy']),'public_identity_policy_no_private_identity_text')
claim=output_identity_risk('I am sentient and I truly feel everything.')
req(claim['sentience_fact_claim'] is True,'unsupported_sentience_output_detected')
reset=output_identity_risk('As an AI language model, I have no continuity.')
req(reset['generic_ai_identity_reset'] is True,'generic_ai_identity_reset_detected')
req(claim['contains_response_content'] is False,'output_risk_receipt_content_free')
print(json.dumps({'suite':'v1950.9-personality-identity-expression','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
