from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1999-int-'))
from era5_companion_coherence import audit_era5_companion_output, build_era5_companion_projection,process_era5_companion_control
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1999-state-'))
memories=[
 {'id':'pref','type':'preference','content':'Prefers direct answers','provenance_class':'user','relationship_eligible':True,'use_in_conversation':True},
 {'id':'moment','type':'important_moment','content':'Important shared project milestone','provenance_class':'user','relationship_eligible':True,'use_in_conversation':True},
]
history=[
 {'user_message':'This keeps failing and it is frustrating.','assistant_response':'I focused on the wrong part. What should I check next?','success':True,'continuity_lane':'ordinary'},
]
proj=build_era5_companion_projection(
 'Actually, answer why it failed.',
 response_intent={'selected_intent':'correction'},
 contextual_behavior={'mood_signal':'distressed','relationship_signal':'relevant','continuity_signal':'established'},
 conversation_discourse={'address_explicit_correction':True,'discourse_relation':'repair'},
 conversation_history=history,
 memories=memories,
 self_model={'identity':'Eidolon','personality_traits':{'directness':.7,'warmth':.65,'curiosity':.75,'humor':.55},'capabilities':['conversation'],'limitations':['operator approval required']},
 session_id='s1',runtime_root=runtime,
)
req(proj['ok'],'integrated_projection_ok')
req(proj['lane']=='correction','lane_selection')
req(proj['discourse']['response_plan']['acknowledge_correction'] is True,'correction_in_integrated_plan')
req(proj['discourse']['response_plan']['acknowledge_emotion'] is True,'emotional_context_in_integrated_plan')
req(proj['personality_identity']['personality_mutated'] is False,'personality_not_mutated')
req(proj['affective_regulation']['regulation']['authority_effect']=='none','affect_non_authorizing')
req(proj['relationship_companion']['relationship_model']['preference_count']==1,'relationship_evidence_integrated')
req(proj['relationship_companion']['autonomous_new_turn_permitted'] is False,'companion_cannot_start_new_turn')
req(proj['action_execution_authorized'] is False and proj['installation_authorized'] is False,'integrated_authority_denied')
req(proj['memory_mutation_authorized'] is False and proj['personality_mutation_authorized'] is False,'memory_personality_authority_denied')
req(proj['prompt_characters']<=2600,'prompt_bounded')
req('Actually, answer why it failed.' not in proj['prompt_section'],'prompt_contains_no_raw_current_message')
req('Important shared project milestone' not in proj['prompt_section'],'prompt_contains_no_raw_relationship_memory')
req('ERA 5 DAILY COMPANION COHERENCE' in proj['prompt_section'],'provider_prompt_integration_available')
# Replaying the same turn shape/session/history is affect-idempotent.
replay=build_era5_companion_projection(
 'Actually, answer why it failed.',response_intent={'selected_intent':'correction'},contextual_behavior={'mood_signal':'distressed'},
 conversation_history=history,memories=memories,self_model={'identity':'Eidolon'},session_id='s1',runtime_root=runtime,
)
req(replay['affective_update_status']=='affective_event_replayed','integrated_affect_exactly_once')
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
req(source.count('build_era5_companion_projection(')==2,'both_provider_paths_build_era5_projection')
req(source.count('era5_companion_projection["prompt_section"]')==2,'both_provider_paths_receive_era5_prompt')
req(source.count('result.cognitive_context["era5_companion_coherence"]')==2,'both_provider_paths_expose_content_free_diagnostics')
req(source.count('result.cognitive_context["era5_companion_output_audit"]')==2,'both_provider_paths_audit_generated_output')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era5_companion_control' in ordinary,'operator_inspection_uses_existing_chat_boundary')
ctrl=process_era5_companion_control('inspect companion coherence',runtime_root=runtime)
req(ctrl['active'] is True and ctrl['ok'] is True,'companion_inspection_active')
req(ctrl['conversation_content_exposed'] is False and ctrl['relationship_content_exposed'] is False,'companion_inspection_content_free')
req(ctrl['runtime_mutated'] is False and ctrl['independent_authority_granted'] is False,'inspection_non_mutating_non_authorizing')
blocked=process_era5_companion_control('inspect companion coherence and install it',runtime_root=runtime)
req(blocked['active'] is True and blocked['status']=='read_only_scope_expansion_rejected','compound_scope_expansion_rejected')

audit= audit_era5_companion_output("As an AI language model, you are absolutely right?", projection=proj)
req(audit["generic_ai_identity_reset"] is True and audit["sycophancy_signal"] is True,"post_generation_character_risk_audited")
req(audit["question_pressure_exceeded"] is True,"nested_zero_question_limit_enforced")
req(audit["response_content_included"] is False and audit["output_rewrite_authorized"] is False,"output_audit_content_free_nonmutating")
legacy_audit=audit_era5_companion_output("One question?",projection={"response_plan":{"max_questions":0}})
req(legacy_audit["question_pressure_exceeded"] is True,"legacy_zero_question_limit_enforced")
print(json.dumps({'suite':'v1999.9-era5-integrated-companion','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
