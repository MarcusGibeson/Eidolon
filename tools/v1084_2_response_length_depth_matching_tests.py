from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AGENT=ROOT/"conscious_agent"
TOOLS=ROOT/"tools"
sys.path.insert(0,str(AGENT)); sys.path.insert(0,str(TOOLS))

import post_review_development_verify as isolated_verify
import release_metadata
from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from conversation_response_shape import classify_response_shape
from conversation_turn_intent import classify_turn_intent


def require(value,message:str)->None:
    if not value: raise AssertionError(message)


def test_explicit_brief_cue_wins() -> None:
    shape=classify_response_shape("Briefly explain photosynthesis.",classify_turn_intent("Briefly explain photosynthesis."))
    require(shape.length_mode=="brief" and shape.depth_mode=="answer_only", "brief cue ignored")
    require(shape.target_max_words==80 and shape.explicit_length_cue, "brief target wrong")


def test_explicit_detail_cue_wins() -> None:
    text="Walk me through this step-by-step in detail."
    shape=classify_response_shape(text,classify_turn_intent(text))
    require(shape.length_mode=="deep" and shape.depth_mode=="structured", "detail cue ignored")
    require(shape.structured and shape.target_max_words==500, "deep target wrong")


def test_short_conversation_stays_natural() -> None:
    greeting=classify_conversation_quality("hello").response_shape
    casual=classify_conversation_quality("That was funny.").response_shape
    require(greeting.length_mode=="brief", "greeting became an essay")
    require(casual.length_mode=="concise" and not casual.structured, "casual remark became a report")


def test_complex_operator_and_brainstorming_turns_expand() -> None:
    operator=classify_conversation_quality("Review conscious_agent/conversation_context.py and explain the risks, tests, and implementation plan.").response_shape
    brainstorm=classify_conversation_quality("Brainstorm several options and compare their pros and cons.").response_shape
    require(operator.length_mode=="detailed" and operator.structured, "operator complexity not matched")
    require(brainstorm.length_mode=="detailed" and brainstorm.structured, "brainstorming depth not matched")


def test_prompt_uses_temporary_dynamic_shape() -> None:
    packet=build_conversation_prompt(
        user_message="Give me a deep, comprehensive explanation of context windows.", self_model={"name":"Eidolon"}, desires={}, memories=[],
        project_context="",goal_context="",task_context="",conversation_history=[],context_size=8192,max_tokens=768,
    )
    require("RESPONSE LENGTH AND DEPTH" in packet.prompt, "response shape block missing")
    require("temporary response-shape instruction" in packet.prompt, "temporary scope missing")
    require("one fixed length" in packet.prompt, "system contract still imposes fixed 250-word rule")
    require(packet.metrics.conversation_response_length=="deep", "length metric missing")
    require(packet.metrics.conversation_response_target_max_words==500, "target metric wrong")


def test_shape_never_mutates_personality_or_calls_provider() -> None:
    shape=classify_conversation_quality("Explain that briefly.").response_shape
    summary=shape.public_summary()
    require(summary["mutates_personality"] is False and summary["writes_state"] is False, "response shape mutates state/personality")
    require(summary["contacts_provider"] is False, "response shape contacted provider")
    require(summary["contains_message_content"] is False, "shape receipt claims content")


def test_release_registration_metadata_and_source_privacy() -> None:
    current=tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1084,2), "runtime regressed before v1084.2")
    require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.RUNTIME_VERSION}"), "runtime milestone/version mismatch")
    require(release_metadata.PREVIOUS_RUNTIME_VERSION != release_metadata.RUNTIME_VERSION, "previous version cannot equal current version")
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].lstrip("v")
    next_version = tuple(int(part) for part in next_token.split(".")[:2])
    require(next_version >= (1084, 3), "next objective regressed before the remaining conversation-quality arc")
    core=[suite.name for suite in isolated_verify.select_suites("core")]
    full=[suite.name for suite in isolated_verify.select_suites("full")]
    for name in ("v1084.0-conversation-quality-foundation","v1084.1-turn-intent-alignment","v1084.2-response-length-depth-matching"):
        require(core.count(name)==1 and full.count(name)==1, f"registration wrong for {name}")
    release=(TOOLS/"release_verify.py").read_text(encoding="utf-8")
    for script in ("v1084_0_conversation_quality_foundation_tests.py","v1084_1_turn_intent_alignment_tests.py","v1084_2_response_length_depth_matching_tests.py"):
        require(release.count(script)==1, f"release registration wrong for {script}")
    forbidden=("data/projects.json","data/tasks.json","data/memories.json","data/approvals/","data/conversation_runtime/")
    files=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    require(not [name for name in files if any(name==item or name.startswith(item) for item in forbidden)], "private runtime state present")


TESTS=[
    ("explicit_brief_cue_wins",test_explicit_brief_cue_wins),
    ("explicit_detail_cue_wins",test_explicit_detail_cue_wins),
    ("short_conversation_stays_natural",test_short_conversation_stays_natural),
    ("complex_operator_and_brainstorming_turns_expand",test_complex_operator_and_brainstorming_turns_expand),
    ("prompt_uses_temporary_dynamic_shape",test_prompt_uses_temporary_dynamic_shape),
    ("shape_never_mutates_personality_or_calls_provider",test_shape_never_mutates_personality_or_calls_provider),
    ("release_registration_metadata_and_source_privacy",test_release_registration_metadata_and_source_privacy),
]

def main()->int:
    argparse.ArgumentParser().add_argument("--json",action="store_true")
    checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed+=1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1084.2-response-length-depth-matching","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1
if __name__=="__main__": raise SystemExit(main())
