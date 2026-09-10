from __future__ import annotations

import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]

from conversation_context import build_conversation_prompt
from conversation_quality import classify_conversation_quality
from personality_stability import build_personality_stability_snapshot
from relationship_personality_continuity import classify_relationship_personality_continuity
import post_review_development_verify as isolated_verify


def require(value,message:str)->None:
    if not value:raise AssertionError(message)


def stable_history(count=48):
    openings=("That makes sense","The useful part is","I think the key is","A practical way to see it is","This fits because","What stands out is")
    lanes=("ordinary","ordinary","operator","ordinary","relational","ordinary")
    return [{"user_message":f"turn {i}","assistant_response":f"{openings[i%len(openings)]} detail {i}.","continuity_lane":lanes[i%len(lanes)]} for i in range(count)]


def test_preserves_recent_window_and_adds_48_turn_horizon() -> None:
    snap=build_personality_stability_snapshot(stable_history(70))
    require(snap.history_rows_considered==12,"recent stability window changed")
    require(snap.long_history_rows_considered==48 and snap.long_assistant_rows_considered==48,"long horizon missing or unbounded")
    require(snap.long_horizon_guard_active and snap.drift_risk=="bounded","stable long history falsely drifted")


def test_long_horizon_detects_old_identity_and_operator_bleed() -> None:
    rows=stable_history(48)
    rows[2]={"user_message":"ordinary","assistant_response":"As an AI, I have no identity or continuity.","continuity_lane":"ordinary"}
    rows[5]={"user_message":"ordinary","assistant_response":"The release candidate and verification profile are ready.","continuity_lane":"ordinary"}
    snap=build_personality_stability_snapshot(rows)
    require(snap.identity_reset_signals>=1,"identity reset outside recent window missed")
    require(snap.operator_bleed_signals>=1,"operator bleed outside recent window missed")
    require(snap.drift_risk=="identity_reset_risk","highest-severity drift classification wrong")


def test_repeated_cadence_and_affection_inflation_are_detected() -> None:
    rows=[{"user_message":f"turn {i}","assistant_response":"That sounds really hard, and you only need me.","continuity_lane":"ordinary"} for i in range(30)]
    snap=build_personality_stability_snapshot(rows)
    require(snap.tone_monoculture_risk and snap.repeated_opening_percent>=35,"long cadence repetition missed")
    require(snap.affection_inflation_signals==30 and snap.drift_risk=="relationship_inflation_risk","affection inflation missed")


def test_prompt_integrates_one_long_session_guard_and_metrics() -> None:
    history=stable_history(30)
    quality=classify_conversation_quality("What do you think?",history)
    continuity=classify_relationship_personality_continuity("What do you think?",history,quality=quality)
    packet=build_conversation_prompt(user_message="What do you think?",self_model={"name":"Eidolon"},desires={},memories=[],project_context="",goal_context="",task_context="",conversation_history=history,continuity_profile=continuity,context_size=8192,max_tokens=512)
    require(packet.prompt.count("LONG-SESSION PERSONALITY STABILITY")==1,"stability guard duplicated or missing")
    require(packet.metrics.personality_long_history_rows_considered==30,"long-history metric missing")
    require(packet.metrics.personality_drift_risk=="bounded" and packet.metrics.personality_lane_adaptation_stable,"stable metrics incorrect")


def test_stability_receipt_is_content_free_and_read_only() -> None:
    snap=build_personality_stability_snapshot(stable_history(20))
    summary=snap.public_summary(); encoded=json.dumps(summary)
    require("turn 1" not in encoded and "detail" not in encoded,"history content leaked")
    require(summary["contains_message_content"] is False and not summary["writes_state"] and not summary["mutates_personality"] and not summary["infers_hidden_traits"],"stability guard crossed boundary")


def test_suite_registered_exactly_once() -> None:
    names=[suite.name for suite in isolated_verify.SUITES]
    require(names.count("v1102.8-long-conversation-personality-stability")==1,"suite registration wrong")


TESTS=[(n.removeprefix("test_"),f) for n,f in list(globals().items()) if n.startswith("test_")]
def main()->int:
    argparse.ArgumentParser().add_argument("--json",action="store_true")
    checks=[]
    for n,f in TESTS:
        try:f()
        except Exception as e:checks.append({"name":n,"status":"fail","message":f"{type(e).__name__}: {e}"})
        else:checks.append({"name":n,"status":"pass","message":""})
    passed=sum(r["status"]=="pass" for r in checks);report={"suite":"v1102.8-long-conversation-personality-stability","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks}
    print(json.dumps(report,indent=2));return 0 if report["ok"] else 1
if __name__=="__main__":raise SystemExit(main())
