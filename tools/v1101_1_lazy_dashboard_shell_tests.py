from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-1-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import dashboard_first_use
import dashboard_startup
import first_use_runtime


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def test_shell_is_immediately_interactive() -> None:
    html = dashboard_first_use.render_first_use_shell()
    require("data-first-use-shell='v1101'" in html, "shell marker")
    require("<textarea id='message'" in html, "composer missing")
    composer = html.split("<textarea id='message'", 1)[1].split(">", 1)[0]
    require("disabled" not in composer, composer)
    require("Chat input is interactive" in html, "interactive state missing")


def test_served_shell_preserves_scroll_and_composer_layout() -> None:
    from dashboard_performance import optimize_dashboard_html_assets

    html = optimize_dashboard_html_assets(dashboard_first_use.render_first_use_shell())
    require("#conversation-log { min-height:48vh; max-height:58vh; overflow:auto;" in html, "bounded conversation log")
    require("<div class='composer'>" in html, "composer missing")
    require("/assets/dashboard.css?v=1396.9-r3" not in html, "first-use CSS was replaced")


def test_shell_restores_state_asynchronously() -> None:
    html = dashboard_first_use.render_first_use_shell()
    for token in (
        "/api/first-use/bootstrap",
        "/api/dashboard-chat/active-session",
        "/api/dashboard-chat/coordination",
        "/api/dashboard-chat/draft",
        "/api/dashboard-chat/stream",
    ):
        require(token in html, token)
    require("window.setTimeout" in html and "checkProvider('api_post')" in html, "provider check is not deferred")


def test_shell_never_automatically_resends_uncertain_turn() -> None:
    html = dashboard_first_use.render_first_use_shell()
    require("no automatic resend" in html.lower(), "uncertainty boundary missing")
    require("acceptance_key:acceptanceKey" in html, "acceptance identity missing")
    require("mutationFields(acceptanceKey)" in html, "mutation identity missing")
    require("while (true)" in html, "stream reader missing")
    require("sendMessage();" in html, "explicit send missing")


def test_root_shell_and_bootstrap_routes_are_live() -> None:
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        ("/api/dashboard-health", "/", "/api/first-use/bootstrap", "/api/first-use/timing"),
        timeout_seconds=35,
    )
    require(report["ok"] is True, report)
    root = next(row for row in report["routes"] if row["route"] == "/")
    require("<!doctype html>" in root["body_prefix"].lower(), root)
    bootstrap = next(row for row in report["routes"] if row["route"] == "/api/first-use/bootstrap")
    require((bootstrap.get("response_json") or {}).get("chat_interactive") is True, bootstrap)


def test_fresh_first_explicit_send_creates_exactly_one_session() -> None:
    from dashboard_chat_console import start_dashboard_chat_operation, subscribe_dashboard_chat_operation

    key = "first-use-explicit-1101"
    accepted = start_dashboard_chat_operation("Hello from first use", use_ai=False, session_id="", acceptance_key=key)
    marker = accepted.get("operation") or {}
    session_id = str(marker.get("session_id") or "")
    require(session_id.startswith("conversation_session_"), accepted)
    events = list(subscribe_dashboard_chat_operation(str(marker.get("operation_id") or "")))
    require(any(row.get("event") == "done" for row in events), events)
    repeated = start_dashboard_chat_operation("Hello from first use", use_ai=False, session_id=session_id, acceptance_key=key)
    require(repeated.get("duplicate_acceptance") is True, repeated)
    html = dashboard_first_use.render_first_use_shell()
    require("if (!text || !coordination.is_owner || sending) return;" in html, "fresh first send remains blocked")
    require("Type below to start one explicitly" in html, "fresh first-use guidance missing")


def test_partial_bootstrap_failure_keeps_chat_usable() -> None:
    import project_manager

    original = project_manager.get_active_project
    project_manager.get_active_project = lambda: (_ for _ in ()).throw(RuntimeError("fixture"))
    try:
        payload = first_use_runtime.build_first_use_bootstrap()
    finally:
        project_manager.get_active_project = original
    require(payload["ok"] is True, payload)
    require(payload["status"] == "degraded", payload)
    require(payload["chat_interactive"] is True, payload)
    require(payload["recovery"]["chat_remains_usable"] is True, payload)
    require(payload["recovery"]["accepted_message_replayed"] is False, payload)


def test_first_use_runtime_guidance_skips_private_inventory() -> None:
    import runtime_data_migration

    original = runtime_data_migration.preview_runtime_data_migration
    runtime_data_migration.preview_runtime_data_migration = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("first-use bootstrap must not inventory private runtime contents")
    )
    try:
        payload = first_use_runtime.build_first_use_bootstrap()
    finally:
        runtime_data_migration.preview_runtime_data_migration = original
    require(payload["runtime_guidance"]["migration_inventory_performed"] is False, payload["runtime_guidance"])
    require(payload["runtime_guidance"]["runtime_external"] is True, payload["runtime_guidance"])


def _runtime_snapshot() -> dict[str, str]:
    import hashlib
    from paths import DATA_DIR
    return {
        path.relative_to(DATA_DIR).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DATA_DIR.rglob("*")) if path.is_file()
    }


def test_exact_state_restore_is_read_only_and_multi_tab_safe() -> None:
    from conversation_navigation import save_conversation_presentation_state
    from conversation_sessions import create_conversation_session, save_conversation_draft
    from conversation_tab_coordination import register_dashboard_tab, reconcile_coordination_selection

    session_id = "conversation_session_20260726T120000_1101aa1101"
    tab_owner = "11111111-1111-4111-8111-111111111111"
    tab_follower = "22222222-2222-4222-8222-222222222222"
    browser_id = "33333333-3333-4333-8333-333333333333"
    create_conversation_session("Restored session", session_id=session_id, project_id="eidolon")
    save_conversation_draft(session_id, "private fixture draft", editor_id=tab_owner)
    save_conversation_presentation_state(
        session_id, follow_latest=False, scroll_from_bottom_px=240,
        composer_intentionally_empty=False, view_anchor_turn_id="",
        view_anchor_offset_px=18, last_seen_turn_count=0,
    )
    owner = register_dashboard_tab(tab_owner, browser_id, instance_nonce="owner-instance-1101", lease_seconds=60)
    follower = register_dashboard_tab(tab_follower, browser_id, instance_nonce="follower-instance-1101", lease_seconds=60)
    reconcile_coordination_selection("eidolon", session_id=session_id)
    require(owner["is_owner"] is True, owner)
    require(follower["is_owner"] is False and follower["owner_present"] is True, follower)

    before = _runtime_snapshot()
    payload = first_use_runtime.build_first_use_bootstrap(tab_id=tab_owner)
    repeated = first_use_runtime.build_first_use_bootstrap(tab_id=tab_owner)
    after = _runtime_snapshot()
    require(before == after, {"added_or_changed": sorted(set(after) ^ set(before))})
    require(payload["selected_session"]["id"] == session_id, payload)
    require(payload["draft"]["content"] == "private fixture draft", payload["draft"])
    require(payload["presentation"]["follow_latest"] is False, payload["presentation"])
    require(payload["presentation"]["scroll_from_bottom_px"] == 240, payload["presentation"])
    require(payload["coordination"]["is_owner"] is True, payload["coordination"])
    require(repeated["selected_session"]["id"] == session_id, repeated)
    require(payload["accepted_turn_replayed"] is False, payload)
    require(payload["provider_contacted"] is False, payload)


def test_provider_unavailable_then_returning_is_truthful_without_replay() -> None:
    from provider_recovery_evidence import persist_provider_recovery_evidence

    digest = "a" * 64
    unavailable = {
        "availability": {"state": "temporarily_unavailable", "observed_state": "temporarily_unavailable", "generation_available": False, "embedding_available": False},
        "readiness_state": "temporarily_unavailable", "configuration_digest": digest,
        "evidence_receipt": {"receipt_type": "provider_readiness", "timestamp": "2026-07-26T12:00:00Z", "configuration_digest": digest},
    }
    persist_provider_recovery_evidence(unavailable, configured_configuration_digest=digest, trigger="manual_check")
    first = first_use_runtime.build_first_use_bootstrap()
    require(first["provider"]["status"] == "temporarily_unavailable", first["provider"])
    require(first["provider"]["recovery_proven"] is False, first["provider"])

    ready = {
        "availability": {"state": "ready", "observed_state": "ready", "generation_available": True, "embedding_available": True},
        "readiness_state": "ready", "configuration_digest": digest,
        "evidence_receipt": {"receipt_type": "provider_readiness", "timestamp": "2026-07-26T12:01:00Z", "configuration_digest": digest},
    }
    persist_provider_recovery_evidence(ready, configured_configuration_digest=digest, trigger="manual_check")
    second = first_use_runtime.build_first_use_bootstrap()
    require(second["provider"]["status"] in {"ready", "recovering"}, second["provider"])
    require(second["provider"]["recovery_proven"] is True, second["provider"])
    require(second["recovery"]["accepted_message_replayed"] is False, second)
    require(second["recovery"]["provider_request_repeated"] is False, second)


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    value = {"suite": "v1101.1-lazy-dashboard-shell", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
