from __future__ import annotations
import json
from pathlib import Path
from conscious_agent.natural_conversation_continuity import (
    MAX_HISTORY_RECORDS, MAX_PROMPT_CHARS,
    build_natural_continuity_evidence, build_natural_continuity_policy,
    build_natural_continuity_for_turn,
)


def _canonical(**kw):
    value={"selected_intent":"direct_answer","intentional_silence_verified":False}
    value.update(kw); return value


def _discourse(**kw):
    value={"discourse_relation":"respond","context_integrity":"verified","address_explicit_correction":False}
    value.update(kw); return value


def test_v1161_0_evidence_is_structural_and_content_free():
    secret="PRIVATE_CONTINUITY_CANARY"
    ev=build_natural_continuity_evidence("yes "+secret,_canonical(),_discourse(),[{"role":"assistant","content":"Question "+secret+"?"}])
    assert ev["latest_assistant_asked_question"] is True
    assert ev["contains_conversation_text"] is False
    assert secret not in json.dumps(ev)


def test_v1161_0_history_is_bounded_and_malformed_fails_closed():
    ev=build_natural_continuity_evidence("answer",_canonical(),_discourse(),"bad")
    assert ev["history_malformed"] is True
    rows=({"role":"assistant","content":"x"} for _ in range(10000))
    bounded=build_natural_continuity_evidence("answer",_canonical(),_discourse(),rows)
    assert bounded["history_count"]==MAX_HISTORY_RECORDS
    assert bounded["history_truncated"] is True


def test_v1161_1_short_reply_answers_prior_question_without_recap():
    p=build_natural_continuity_for_turn("yes",_canonical(),_discourse(),[{"role":"assistant","content":"Proceed?"}])
    assert p["continuity_relation"]=="answer_prior_question"
    assert p["answer_prior_question_directly"] is True
    assert p["maximum_recap_sentences"]==0


def test_v1161_1_continuation_and_repair_are_distinct():
    cont=build_natural_continuity_for_turn("keep going",_canonical(),_discourse(discourse_relation="continue"),[{"role":"assistant","content":"part one"}])
    assert cont["continuity_relation"]=="continue_thread"
    assert cont["continue_without_restart"] is True
    repair=build_natural_continuity_for_turn("actually no",_canonical(),_discourse(discourse_relation="repair",address_explicit_correction=True),[{"role":"assistant","content":"old"}])
    assert repair["continuity_relation"]=="repair_thread"
    assert repair["repair_without_replaying_history"] is True


def test_v1161_1_stale_or_suspicious_history_cannot_create_continuity():
    rows=[{"role":"assistant","content":"secret?","status":"stale"},{"role":"assistant","content":"x?","provider_payload":"bad"}]
    p=build_natural_continuity_for_turn("yes",_canonical(),_discourse(),rows)
    assert p["continuity_relation"]=="fresh_turn"
    assert p["maximum_prior_turn_references"]==0


def test_v1161_1_silence_and_closure_do_not_reopen():
    p=build_natural_continuity_for_turn("do not respond",_canonical(intentional_silence_verified=True),_discourse(discourse_relation="close"),[{"role":"assistant","content":"done"}])
    assert p["continuity_relation"]=="close_thread"
    assert p["close_without_reopening"] is True
    assert p["may_initiate_new_turn"] is False


def test_v1161_2_prompt_is_complete_bounded_and_non_authorizing():
    p=build_natural_continuity_for_turn("continue",_canonical(),_discourse(discourse_relation="continue"),[{"role":"assistant","content":"earlier"}])
    prompt=p["prompt_section"]
    assert len(prompt)<=MAX_PROMPT_CHARS
    assert prompt.startswith('<natural_conversation_continuity data_only="true" authority="none">')
    assert prompt.endswith('</natural_conversation_continuity>')
    payload=json.loads(prompt.split('>',1)[1].rsplit('<',1)[0])
    assert payload["approval_granted"] is False
    assert payload["authorization_granted"] is False
    assert payload["execution_permitted"] is False


def test_v1161_2_both_authoritative_paths_share_projection_and_receipts():
    source=Path('conscious_agent/conversation_runtime.py').read_text()
    assert source.count('build_natural_continuity_for_turn(')==2
    assert source.count('+ "\\n" + natural_continuity["prompt_section"]')==2
    assert source.count('result.cognitive_context["natural_conversation_continuity"]')==2
    assert source.count('result.cognitive_context["natural_conversation_continuity_evidence"]')==2
