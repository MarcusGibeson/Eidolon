from __future__ import annotations
import json
from pathlib import Path
from conscious_agent.natural_conversation_continuity import (
    MAX_PROMPT_CHARS, build_natural_continuity_for_turn,
)


def _canonical(**kw):
    value={"selected_intent":"direct_answer","intentional_silence_verified":False}
    value.update(kw); return value


def _discourse(**kw):
    value={"discourse_relation":"respond","context_integrity":"verified","address_explicit_correction":False}
    value.update(kw); return value


def test_v1161_3_prior_question_is_consumed_without_reasking():
    p=build_natural_continuity_for_turn("yes",_canonical(),_discourse(),[{"role":"assistant","content":"Proceed?"}])
    assert p["linkage_target"]=="latest_assistant_question"
    assert p["opening_move"]=="answer_directly"
    assert p["consume_prior_question"] is True
    assert p["avoid_reasking_answered_question"] is True
    assert p["maximum_bridge_sentences"]==0


def test_v1161_3_continuation_resumes_next_unfinished_point():
    p=build_natural_continuity_for_turn("keep going",_canonical(),_discourse(discourse_relation="continue"),[{"role":"assistant","content":"part one"}])
    assert p["linkage_target"]=="current_thread"
    assert p["opening_move"]=="resume_in_place"
    assert p["resume_at_next_unfinished_point"] is True
    assert p["response_progression"]=="continue_from_next_unfinished_point"
    assert p["maximum_bridge_sentences"]==1
    assert p["maximum_recap_sentences"]==0


def test_v1161_4_repair_replaces_only_corrected_element():
    p=build_natural_continuity_for_turn("actually, no",_canonical(),_discourse(discourse_relation="repair",address_explicit_correction=True),[{"role":"assistant","content":"old answer"}])
    assert p["linkage_target"]=="latest_corrected_element"
    assert p["opening_move"]=="acknowledge_correction_once"
    assert p["replace_only_corrected_element"] is True
    assert p["repair_without_replaying_history"] is True
    assert p["avoid_repeating_prior_answer"] is True


def test_v1161_4_adjacent_and_fresh_turns_do_not_force_callbacks():
    adjacent=build_natural_continuity_for_turn("new detail",_canonical(),_discourse(),[{"role":"assistant","content":"earlier"}])
    assert adjacent["continuity_relation"]=="adjacent_turn"
    assert adjacent["opening_move"]=="answer_current_turn"
    assert adjacent["response_progression"]=="use_prior_context_only_if_needed"
    fresh=build_natural_continuity_for_turn("new topic",_canonical(),_discourse(),[])
    assert fresh["linkage_target"]=="none"
    assert fresh["response_progression"]=="treat_as_fresh_turn"


def test_v1161_4_closure_stays_minimal_and_cannot_reopen():
    p=build_natural_continuity_for_turn("thanks",_canonical(),_discourse(discourse_relation="close"),[{"role":"assistant","content":"done"}])
    assert p["opening_move"]=="minimal_closure"
    assert p["response_progression"]=="close_without_reopening"
    assert p["maximum_bridge_sentences"]==0
    assert p["may_initiate_new_turn"] is False


def test_v1161_5_malformed_context_recovers_without_linkage_claims():
    p=build_natural_continuity_for_turn("yes",_canonical(),_discourse(),"bad")
    assert p["policy_recovered"] is True
    assert p["continuity_relation"]=="fresh_turn"
    assert p["linkage_target"]=="none"
    assert p["maximum_prior_turn_references"]==0


def test_v1161_5_prompt_contains_bounded_linkage_plan():
    p=build_natural_continuity_for_turn("continue",_canonical(),_discourse(discourse_relation="continue"),[{"role":"assistant","content":"earlier"}])
    prompt=p["prompt_section"]
    assert len(prompt)<=MAX_PROMPT_CHARS
    payload=json.loads(prompt.split('>',1)[1].rsplit('<',1)[0])
    assert payload["linkage_target"]=="current_thread"
    assert payload["resume_at_next_unfinished_point"] is True
    assert payload["maximum_bridge_sentences"]==1
    assert payload["approval_granted"] is False


def test_v1161_5_both_authoritative_paths_share_integrated_projection():
    source=Path('conscious_agent/conversation_runtime.py').read_text()
    assert source.count('build_natural_continuity_for_turn(')==2
    assert source.count('+ "\\n" + natural_continuity["prompt_section"]')==2
    assert source.count('result.cognitive_context["natural_conversation_continuity"]')==2
