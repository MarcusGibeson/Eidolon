from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (AGENT, ROOT):
    if str(value) not in os.sys.path:
        os.sys.path.insert(0, str(value))

from endogenous_cognitive_cycle import EndogenousCognitiveCycle
from persistent_motivation import MotivationStore
from proactive_communication import CognitiveInitiativeService, ProactiveCommunicationStore, build_cognition_inspection


def require(condition: bool, detail: Any = "requirement failed") -> None:
    if not condition:
        raise AssertionError(detail)


def fixture() -> tuple[MotivationStore, EndogenousCognitiveCycle, ProactiveCommunicationStore, Path]:
    root = Path(tempfile.mkdtemp(prefix="eidolon-v1104-5-")) / "cognition"
    motivation = MotivationStore(root)
    cycle = EndogenousCognitiveCycle(root, motivation_store=motivation)
    cycle.set_control(
        "fixture-proactive-cycle-budget",
        action="adjust_budget",
        max_cycles_per_hour=60,
        max_cycles_per_day=1000,
    )
    communication = ProactiveCommunicationStore(root, motivation_store=motivation)
    return motivation, cycle, communication, root


def add(store: MotivationStore, event_id: str, *, kind: str = "concern", summary: str = "A meaningful unresolved subject", urgency: float = 0.95, confidence: float = 0.85, valence: float = -0.7) -> str:
    result = store.record_motivation(
        event_id,
        kind=kind,
        summary=summary,
        cognitive_state="intention" if "goal" in kind else "desire",
        urgency=urgency,
        confidence=confidence,
        valence=valence,
        origin_type="fixture_event",
        origin_ref=f"origin-{event_id}",
    )
    return str(result["result"]["motivation_id"])


def cycle_for(cycle: EndogenousCognitiveCycle, event_id: str, motivation_id: str, *, trigger: str = "event", now_epoch: float = 1000) -> dict[str, Any]:
    return cycle.run_cycle(
        event_id,
        trigger_type=trigger,
        perceived_events=[{"event_type": trigger if trigger != "event" else "memory_change", "event_ref": f"ref-{event_id}", "motivation_id": motivation_id}],
        provider_available=False,
        now_epoch=now_epoch,
    )


def test_state_grounded_message_and_reason_are_queued_from_cycle() -> None:
    motivation, cycle, communication, _ = fixture()
    motivation_id = add(motivation, "grounded", kind="concern", summary="The release boundary still needs attention")
    result = cycle_for(cycle, "cycle-grounded", motivation_id, trigger="failure", now_epoch=1000)
    proactive = communication.consider_cycle(result, tone="practical", now_epoch=1000)
    message = proactive["message"]
    require(proactive["status"] == "proactive_message_queued", proactive)
    require(message["motivation_id"] == motivation_id and message["source_grounded"] is True, message)
    require("release boundary" in message["body"].lower(), message)
    require("I brought this up because" in message["reason"], message)
    require(message["action_authorized"] is False and message["action_executed"] is False, message)


def test_persistent_curiosity_can_generate_a_question_without_incoming_message() -> None:
    motivation, cycle, communication, _ = fixture()
    motivation_id = add(motivation, "curiosity", kind="curiosity", summary="Why the restart fixture diverged", valence=0.4)
    result = cycle_for(cycle, "cycle-curiosity", motivation_id, trigger="memory_change", now_epoch=2000)
    proactive = communication.consider_cycle(result, now_epoch=2000)
    message = proactive["message"]
    require(message["message_type"] == "curiosity_question", message)
    require(message["body"].endswith("?"), message["body"])
    require(result["receipt"]["provider_contacted"] is False, result)


def test_quiet_request_and_timed_quiet_select_silence_without_erasing_continuity() -> None:
    motivation, cycle, communication, _ = fixture()
    motivation_id = add(motivation, "quiet")
    communication.apply_user_boundary("quiet-on", quiet=True)
    first = communication.consider_cycle(cycle_for(cycle, "quiet-cycle-1", motivation_id, now_epoch=3000), now_epoch=3000)
    require(first["decision"] == "silence" and "quiet request" in first["reason"], first)
    communication.apply_user_boundary("quiet-timed", quiet=False, quiet_until_epoch=4000)
    second = communication.consider_cycle(cycle_for(cycle, "quiet-cycle-2", motivation_id, now_epoch=3500), now_epoch=3500)
    require(second["decision"] == "silence" and "time-bounded" in second["reason"], second)
    require(motivation.inspection_summary()["active_motivation_count"] == 1, motivation.inspection_summary())


def test_topic_boundary_and_form_of_address_correction_are_respected() -> None:
    motivation, cycle, communication, _ = fixture()
    blocked_id = add(motivation, "blocked-topic", summary="Discuss the private topic boundary")
    communication.apply_user_boundary("boundary", add_blocked_topics=["private topic"], form_of_address="Captain", relationship_correction=True)
    blocked = communication.consider_cycle(cycle_for(cycle, "blocked-cycle", blocked_id, now_epoch=5000), now_epoch=5000)
    require(blocked["decision"] == "silence" and "topic boundary" in blocked["reason"], blocked)
    allowed_id = add(motivation, "allowed-topic", summary="Review the next bounded test")
    allowed = communication.consider_cycle(cycle_for(cycle, "allowed-cycle", allowed_id, now_epoch=5001), now_epoch=5001)
    require(allowed["decision"] == "communicate", allowed)
    require(allowed["message"]["body"].startswith("Captain,"), allowed["message"])


def test_unread_non_response_awareness_blocks_message_stacking() -> None:
    motivation, cycle, communication, _ = fixture()
    first_id = add(motivation, "first-unread", summary="First unresolved concern")
    second_id = add(motivation, "second-unread", summary="Second unresolved concern")
    first = communication.consider_cycle(cycle_for(cycle, "unread-cycle-1", first_id, now_epoch=6000), now_epoch=6000)
    require(first["decision"] == "communicate", first)
    second = communication.consider_cycle(cycle_for(cycle, "unread-cycle-2", second_id, now_epoch=7000), now_epoch=7000)
    require(second["decision"] == "silence" and "unread" in second["reason"], second)
    require(communication.inspection_summary()["unread_count"] == 1, communication.inspection_summary())


def test_cooldown_daily_budget_and_repeated_question_suppression() -> None:
    motivation, cycle, communication, _ = fixture()
    communication.set_preferences("fast", frequency="high", cooldown_seconds=60, max_per_day=2)
    first_id = add(motivation, "cooldown-first", summary="First bounded concern")
    first_cycle = cycle_for(cycle, "cooldown-cycle-1", first_id, now_epoch=8000)
    first = communication.consider_cycle(first_cycle, now_epoch=8000)
    message_id = first["message"]["message_id"]
    communication.claim_delivery("deliver-first", message_id=message_id, delivery_id="delivery-1", tab_id="tab-a", now_epoch=8000)
    communication.mark_read("read-first", message_id=message_id)
    second_id = add(motivation, "cooldown-second", summary="Second bounded concern")
    cooldown = communication.consider_cycle(cycle_for(cycle, "cooldown-cycle-2", second_id, now_epoch=8030), now_epoch=8030)
    require(cooldown["decision"] == "silence" and "cooldown" in cooldown["reason"], cooldown)
    repeated = communication.consider_cycle(cycle_for(cycle, "repeat-cycle", first_id, now_epoch=9000), now_epoch=9000)
    require(repeated["decision"] == "silence" and "already raised" in repeated["reason"], repeated)
    third_id = add(motivation, "daily-third", summary="Third bounded concern")
    second_message = communication.consider_cycle(cycle_for(cycle, "daily-cycle-2", second_id, now_epoch=9001), now_epoch=9001)
    require(second_message["decision"] == "communicate", second_message)
    communication.claim_delivery("deliver-second", message_id=second_message["message"]["message_id"], delivery_id="delivery-2", tab_id="tab-a", now_epoch=9001)
    communication.mark_read("read-second", message_id=second_message["message"]["message_id"])
    daily = communication.consider_cycle(cycle_for(cycle, "daily-cycle-3", third_id, now_epoch=10000), now_epoch=10000)
    require(daily["decision"] == "silence" and "daily" in daily["reason"], daily)


def test_exactly_once_delivery_survives_tabs_retries_and_restart() -> None:
    motivation, cycle, communication, root = fixture()
    motivation_id = add(motivation, "delivery")
    queued = communication.consider_cycle(cycle_for(cycle, "delivery-cycle", motivation_id, now_epoch=11000), now_epoch=11000)
    message_id = queued["message"]["message_id"]
    first = communication.claim_delivery("claim-a", message_id=message_id, delivery_id="delivery-a", tab_id="tab-a", now_epoch=11000)
    second = ProactiveCommunicationStore(root, motivation_store=MotivationStore(root)).claim_delivery("claim-b", message_id=message_id, delivery_id="delivery-b", tab_id="tab-b", now_epoch=11001)
    retry = ProactiveCommunicationStore(root, motivation_store=MotivationStore(root)).claim_delivery("claim-a", message_id=message_id, delivery_id="delivery-a", tab_id="tab-a", now_epoch=11002)
    require(first["status"] == "delivered" and first["result"]["delivered"] is True, first)
    require(second["status"] == "already_delivered" and second["result"]["delivered"] is False, second)
    require(retry["status"] == "duplicate_delivery_event_ignored", retry)
    snapshot = ProactiveCommunicationStore(root, motivation_store=MotivationStore(root)).snapshot()
    require(len(snapshot["delivery_receipts"]) == 1, snapshot["delivery_receipts"])


def test_proactive_decision_deduplicates_after_restart() -> None:
    motivation, cycle, communication, root = fixture()
    motivation_id = add(motivation, "decision-dedupe")
    cycle_result = cycle_for(cycle, "decision-cycle", motivation_id, now_epoch=12000)
    first = communication.consider_cycle(cycle_result, now_epoch=12000)
    restarted = ProactiveCommunicationStore(root, motivation_store=MotivationStore(root))
    second = restarted.consider_cycle(cycle_result, now_epoch=12001)
    require(first["status"] == "proactive_message_queued", first)
    require(second["status"] == "duplicate_proactive_decision_ignored", second)
    require(len(restarted.snapshot()["messages"]) == 1, restarted.snapshot())


def test_thought_can_continue_naturally_after_user_response() -> None:
    motivation, cycle, communication, _ = fixture()
    motivation_id = add(motivation, "continuation", kind="unresolved_subject", summary="The unfinished architecture question")
    first = communication.consider_cycle(cycle_for(cycle, "continuation-cycle-1", motivation_id, now_epoch=13000), now_epoch=13000)
    first_id = first["message"]["message_id"]
    communication.claim_delivery("continuation-deliver", message_id=first_id, delivery_id="cont-delivery", tab_id="tab-a", now_epoch=13000)
    communication.record_user_response("continuation-response", in_reply_to_message_id=first_id, now_epoch=13001)
    second_cycle = cycle_for(cycle, "continuation-cycle-2", motivation_id, now_epoch=13002)
    second = communication.consider_cycle(second_cycle, continuation_of=first_id, now_epoch=13002)
    require(second["decision"] == "communicate", second)
    message = second["message"]
    require(message["message_type"] == "continuation" and message["part_number"] == 2, message)
    require(message["continuation_of"] == first_id and message["thread_id"] == first["message"]["thread_id"], message)


def test_affectionate_and_playful_tones_require_relationship_context() -> None:
    motivation, cycle, communication, _ = fixture()
    first_id = add(motivation, "warm-no-context", kind="unresolved_subject", summary="A shared meaningful conversation")
    no_context = communication.consider_cycle(cycle_for(cycle, "warm-cycle-1", first_id, now_epoch=14000), tone="affectionate", now_epoch=14000)
    require(no_context["message"]["tone"] == "thoughtful", no_context["message"])
    communication.claim_delivery("warm-deliver", message_id=no_context["message"]["message_id"], delivery_id="warm-delivery", tab_id="tab-a", now_epoch=14000)
    communication.record_user_response("warm-response", in_reply_to_message_id=no_context["message"]["message_id"], now_epoch=14001)
    second_id = add(motivation, "warm-context", kind="unresolved_subject", summary="Another shared meaningful conversation")
    with_context = communication.consider_cycle(
        cycle_for(cycle, "warm-cycle-2", second_id, now_epoch=18000),
        tone="affectionate",
        relationship_context_refs=["relationship-memory-1"],
        now_epoch=18000,
    )
    require(with_context["message"]["tone"] == "affectionate", with_context["message"])
    require(with_context["message"]["relationship_ref_digests"], with_context["message"])


def test_corrections_withdraw_messages_without_erasing_history() -> None:
    motivation, cycle, communication, _ = fixture()
    motivation_id = add(motivation, "withdraw")
    queued = communication.consider_cycle(cycle_for(cycle, "withdraw-cycle", motivation_id, now_epoch=19000), now_epoch=19000)
    message_id = queued["message"]["message_id"]
    withdrawn = communication.withdraw_for_correction("withdraw-event", message_id=message_id, reason_code="relationship_correction")
    require(withdrawn["result"]["active_influence"] is False, withdrawn)
    snapshot = communication.snapshot()
    require(snapshot["messages"][0]["state"] == "withdrawn", snapshot)
    require(len(snapshot["processed_events"]) == 1, snapshot["processed_events"])


def test_initiative_service_and_inspection_preserve_action_boundary() -> None:
    motivation, cycle, communication, root = fixture()
    motivation_id = add(motivation, "service")
    service = CognitiveInitiativeService(root, cycle=cycle, communication=communication, poll_seconds=5)
    result = service.process_event(
        "service-event",
        trigger_type="memory_change",
        perceived_events=[{"event_type": "memory_change", "event_ref": "memory-service", "motivation_id": motivation_id}],
        provider_available=False,
        now_epoch=20000,
    )
    require(result["communication"]["decision"] == "communicate", result)
    inspection = build_cognition_inspection(root)
    require(inspection["motivation"]["active_motivation_count"] == 1, inspection)
    require(inspection["cycle"]["recent_reflections"], inspection)
    require(inspection["communication"]["queued_count"] == 1, inspection)
    require(all(row["authority"] != "internal" for row in inspection["state_boundaries"]), inspection)
    require(inspection["action_authority_changed"] is False, inspection)
    message = inspection["communication"]["recent_messages"][0]
    require(message["action_authorized"] is False and message["action_executed"] is False, message)
    text = json.dumps(inspection)
    require("memory-service" not in text, text)


def test_dashboard_inspection_surface_is_responsive_keyboard_safe_and_reasoning_redacted() -> None:
    from dashboard_first_use import render_first_use_shell
    html = render_first_use_shell()
    required = [
        "id='cognition-panel'",
        "id='cognition-motivations'",
        "id='cognition-reflections'",
        "id='cognition-frequency'",
        "/api/cognition/inspection",
        "/api/cognition/proactive/claim",
        "Internal state cannot authorize or execute an action.",
        "@media (max-width:560px)",
    ]
    require(all(token in html for token in required), [token for token in required if token not in html])
    cognition_section = html.split("id='cognition-panel'", 1)[1].split("</section>", 1)[0]
    require("title=" not in cognition_section, cognition_section)
    require("raw_chain" not in cognition_section and "provider_payload" not in cognition_section, cognition_section)
    match = re.search(r"<script>(.*)</script>", html, re.S)
    require(match is not None, "dashboard script missing")
    if subprocess.run(["node", "--version"], capture_output=True, text=True).returncode == 0:
        js_path = Path(tempfile.mkdtemp(prefix="eidolon-v1104-5-js-")) / "dashboard.js"
        js_path.write_text(match.group(1), encoding="utf-8")
        check = subprocess.run(["node", "--check", str(js_path)], capture_output=True, text=True)
        require(check.returncode == 0, check.stderr)


def test_cognition_api_routes_preserve_exactly_once_delivery_and_action_boundary() -> None:
    from api_server import dispatch_api
    data_root = Path(tempfile.mkdtemp(prefix="eidolon-v1104-5-api-")) / "runtime"
    previous = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(data_root)
    try:
        cognition_root = data_root / "cognition"
        motivation = MotivationStore(cognition_root)
        motivation_id = add(motivation, "api-route", summary="API inspection boundary")
        service = CognitiveInitiativeService(cognition_root)
        event_result = service.process_event(
            "api-cycle",
            trigger_type="memory_change",
            perceived_events=[{"event_type": "memory_change", "event_ref": "api-ref", "motivation_id": motivation_id}],
            provider_available=False,
            now_epoch=21000,
        )
        message_id = event_result["communication"]["message"]["message_id"]
        status, inspection = dispatch_api("GET", "/api/cognition/inspection")
        require(status == 200 and inspection["data"]["action_authority_changed"] is False, inspection)
        status, paused = dispatch_api("POST", "/api/cognition/control", body={"event_id": "api-pause", "action": "pause"})
        require(status == 200 and paused["data"]["result"]["mode"] == "paused", paused)
        status, preference = dispatch_api("POST", "/api/cognition/communication/preferences", body={"event_id": "api-frequency", "frequency": "low"})
        require(status == 200 and preference["data"]["result"]["frequency"] == "low", preference)
        claim_body = {"event_id": "api-claim-a", "message_id": message_id, "delivery_id": "api-delivery-a", "tab_id": "tab-a"}
        status, first = dispatch_api("POST", "/api/cognition/proactive/claim", body=claim_body)
        status2, second = dispatch_api("POST", "/api/cognition/proactive/claim", body={**claim_body, "event_id": "api-claim-b", "delivery_id": "api-delivery-b", "tab_id": "tab-b"})
        require(status == 200 and first["data"]["result"]["delivered"] is True, first)
        require(status2 == 200 and second["data"]["status"] == "already_delivered", second)
        require(first["data"]["message"]["action_authorized"] is False, first)
        status, read = dispatch_api("POST", "/api/cognition/proactive/read", body={"event_id": "api-read", "message_id": message_id})
        require(status == 200 and read["data"]["result"]["read"] is True, read)
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous


def test_cli_inspection_and_communication_controls_are_provider_free() -> None:
    data_root = Path(tempfile.mkdtemp(prefix="eidolon-v1104-5-cli-")) / "runtime"
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(data_root)
    status = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "cognition-status", "--json"], cwd=ROOT, env=env, capture_output=True, text=True)
    require(status.returncode == 0, status.stderr)
    payload = json.loads(status.stdout)
    require(payload["communication"]["authority_boundary"]["can_execute_action"] is False, payload)
    control = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "communication-control", "--frequency", "minimal", "--json"], cwd=ROOT, env=env, capture_output=True, text=True)
    require(control.returncode == 0, control.stderr)
    changed = json.loads(control.stdout)
    require(changed["result"]["frequency"] == "minimal" and changed["result"]["continuity_erased"] is False, changed)


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1104.5-proactive-communication-continuity",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
