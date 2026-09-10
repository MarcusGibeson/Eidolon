from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1925-'))
from discourse_response_planning import build_discourse_state, build_response_plan, build_discourse_response_projection
checks=[]
def req(v,n): checks.append(n); assert v,n
history=[
 {'user_message':'Tell me about the cache issue.','assistant_response':'The cache used metadata rather than raw bytes.','success':True,'continuity_lane':'ordinary'},
 {'user_message':'Why?','assistant_response':'Because same-size replacements could preserve metadata. What part should I expand?','success':True,'continuity_lane':'ordinary'},
]
state=build_discourse_state('How did the repair prevent that?',response_intent={'selected_intent':'explanation'},contextual_behavior={'mood_signal':'absent','relationship_signal':'absent','continuity_signal':'established'},conversation_discourse={'discourse_relation':'continue'},conversation_history=history)
req(state.target_kind=='answer_current_question','current_question_targeted')
req(state.topic_state=='continuing','topic_continuity')
req('answer_current_question' in state.response_obligations,'question_obligation')
req(state.history_rows_considered==2,'bounded_history_used')
req(state.public_summary()['contains_history_content'] is False,'public_history_content_free')
plan=build_response_plan(state,conversation_history=history)
req(plan.primary_move=='answer_first','answer_first')
req(plan.directness>=.85,'directness_high_for_question')
req(plan.maximum_questions==0,'no_unneeded_question_pressure')
req(plan.avoid_canned_template is True,'canned_template_guard')
correction=build_discourse_state('Actually, that is wrong. Explain the repaired behavior.',response_intent={'selected_intent':'correction'},contextual_behavior={'mood_signal':'absent'},conversation_discourse={'address_explicit_correction':True},conversation_history=history)
correction_plan=build_response_plan(correction,conversation_history=history)
req(correction.correction_active is True,'correction_detected')
req(correction_plan.acknowledge_correction is True,'correction_acknowledged')
req(correction_plan.maximum_questions==0,'correction_does_not_interrogate')
close=build_discourse_state('Thanks.',response_intent={'selected_intent':'acknowledgment'},conversation_history=history)
close_plan=build_response_plan(close,conversation_history=history)
req(close.closure_cue is True,'closure_detected')
req(close_plan.close_without_offer is True,'closure_not_reopened')
req(close_plan.initiative<=.05,'closure_low_initiative')
short=build_discourse_state('Why?',response_intent={'selected_intent':'follow_up'},conversation_history=history)
req(short.target_kind=='resolve_recent_reference','short_reference_resolved_to_recent_turn')
req(short.unresolved_reference_count==1,'reference_count')
emotional=build_discourse_state('I am really frustrated that this keeps failing.',response_intent={'selected_intent':'acknowledgment'},contextual_behavior={'mood_signal':'distressed','relationship_signal':'absent'},conversation_history=history)
emotional_plan=build_response_plan(emotional,conversation_history=history)
req(emotional_plan.acknowledge_emotion is True,'specific_emotional_ack')
req(emotional_plan.warmth>=.75,'warmth_calibrated')
req(emotional_plan.initiative<=.2,'distress_does_not_create_extra_task')
shift=build_discourse_state('Different topic: what is next on the roadmap?',response_intent={'selected_intent':'direct_answer'},conversation_history=history)
req(shift.topic_shift is True and shift.target_kind=='new_topic','explicit_topic_shift')
projection=build_discourse_response_projection('What changed?',response_intent={'selected_intent':'direct_answer'},contextual_behavior={'mood_signal':'absent'},conversation_history=history)
req(projection['ok'] and projection['authority_granted'] is False,'projection_non_authorizing')
req('ERA 5 RESPONSE PLAN' in projection['prompt_section'],'provider_plan_projection')
req('What changed?' not in projection['prompt_section'],'prompt_policy_contains_no_raw_message')
# Repeated opening evidence should trigger structural variation.
repeat=[{'assistant_response':'That makes sense and I understand. A','continuity_lane':'ordinary'},{'assistant_response':'That makes sense and I understand. B','continuity_lane':'ordinary'},{'assistant_response':'That makes sense and I understand. C','continuity_lane':'ordinary'}]
repeat_state=build_discourse_state('Continue.',response_intent={'selected_intent':'follow_up'},conversation_history=repeat)
repeat_plan=build_response_plan(repeat_state,conversation_history=repeat)
req(repeat_plan.avoid_stock_opening is True,'repeated_opening_guard')
req(repeat_plan.may_initiate_new_turn is False and repeat_plan.action_execution_permitted is False,'no_new_turn_or_execution_authority')
print(json.dumps({'suite':'v1925.9-discourse-conversational-flow','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
