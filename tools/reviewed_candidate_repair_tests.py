from __future__ import annotations

"""Deterministic repairs for the Desktop-reviewed v1079.5.8 candidate defects."""

import argparse
import ast
import gc
import importlib.util
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (Path(tempfile.gettempdir()) / "eidolon-reviewed-repair-fixture-data")).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)
sys.path.insert(0, str(AGENT))


def _tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _source_snapshot() -> dict[str, str]:
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        and not p.relative_to(ROOT).as_posix().startswith(("data/conversation_sessions/", "data/conversation_runtime/", "data/dashboard_chat/", "data/conversation_navigation/"))
    }


def _check(name: str, fn: Callable[[], None]) -> dict[str, Any]:
    try:
        fn()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}", "traceback": traceback.format_exc()}


def _post(base: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any], dict[str, str]]:
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.status, json.loads(response.read().decode()), dict(response.headers.items())


def _get(base: str, path: str) -> tuple[int, dict[str, Any]]:
    with urllib.request.urlopen(base + path, timeout=8) as response:
        return response.status, json.loads(response.read().decode())




def _chat_surface_fragment(page_html: str) -> str:
    start = page_html.index("<div class='realtime-chat-shell")
    end = page_html.index("</script>", start) + len("</script>")
    return "<html><head><base href='http://eidolon.local/'></head><body>" + page_html[start:end] + "</body></html>"


def _browser_executable() -> str | None:
    configured = os.environ.get("EIDOLON_TEST_BROWSER", "").strip()
    candidates = [
        configured,
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        shutil.which("google-chrome") or "",
        shutil.which("chrome") or "",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    runtime_before = _tree(EXTERNAL_DATA_DIR)
    source_before = _source_snapshot()
    backup = Path(tempfile.mkdtemp(prefix="eidolon-reviewed-repair-backup-"))
    if EXTERNAL_DATA_DIR.exists():
        shutil.copytree(EXTERNAL_DATA_DIR, backup / "data", dirs_exist_ok=True)
    if EXTERNAL_DATA_DIR.exists():
        shutil.rmtree(EXTERNAL_DATA_DIR)
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    server: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    try:
        import dashboard
        import dashboard_chat_console as console
        from conversation_navigation import save_conversation_presentation_state, switch_conversation_session
        from conversation_sessions import (
            create_conversation_session,
            get_active_conversation_session,
            list_conversation_sessions,
            load_conversation_draft,
            save_conversation_draft,
            select_conversation_session,
        )
        import vector_memory

        vector_memory._get_chromadb = lambda: None

        html = console.render_realtime_chat_panel(None, include_archived=True)
        dashboard_py = (AGENT / "dashboard.py").read_text(encoding="utf-8")

        def rendered_first_run_control_reaches_source_less_api_contract() -> None:
            assert "id='chat-session-create-form'" in html
            assert "performConversationLifecycle('create'" in html
            assert "if (!sourceSessionId && action !== 'create')" in html
            assert "sourceSessionId ? capturePresentation(sourceSessionId)" in html

        results.append(_check("rendered_first_run_new_conversation_control_allows_empty_source", rendered_first_run_control_reaches_source_less_api_contract))

        server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        client = str(uuid.uuid4())
        request_key = str(uuid.uuid4())
        create_payload = {
            "action": "create", "navigation_client_id": client, "lifecycle_generation": 1,
            "request_key": request_key, "source_session_id": "", "target_session_id": "", "title": "First conversation",
            "source_draft_content": "", "source_draft_updated_at": "", "source_follow_latest": True,
            "source_scroll_from_bottom_px": 0, "source_composer_intentionally_empty": True,
            "source_presentation_updated_at": "",
        }
        status, created, _ = _post(base, "/api/dashboard-chat/session-lifecycle", create_payload)

        def first_run_http_create_is_exactly_once() -> None:
            assert status == 200 and created.get("ok") is True
            assert created.get("created_session_id") and created.get("selected_session_id") == created.get("created_session_id")
            assert created.get("snapshot", {}).get("session", {}).get("id") == created.get("created_session_id")
            assert len(list_conversation_sessions(include_archived=True)) == 1
            duplicate_status, duplicate, _ = _post(base, "/api/dashboard-chat/session-lifecycle", create_payload)
            assert duplicate_status == 200 and duplicate.get("duplicate_request") is True
            assert duplicate.get("created_session_id") == created.get("created_session_id")
            assert len(list_conversation_sessions(include_archived=True)) == 1

        results.append(_check("clean_runtime_real_http_create_is_idempotent", first_run_http_create_is_exactly_once))

        def active_snapshot_endpoint_is_read_only_and_complete() -> None:
            before = _tree(EXTERNAL_DATA_DIR)
            code, payload = _get(base, "/api/dashboard-chat/active-session")
            after = _tree(EXTERNAL_DATA_DIR)
            assert code == 200 and payload.get("ok") is True and payload.get("empty") is False
            snapshot = payload.get("snapshot") or {}
            assert snapshot.get("session", {}).get("id") == created.get("created_session_id")
            assert "draft" in snapshot and "presentation" in snapshot and "operation_status" in snapshot
            assert before == after

        results.append(_check("active_session_snapshot_get_is_complete_and_side_effect_free", active_snapshot_endpoint_is_read_only_and_complete))

        def bfcache_identity_gate_is_atomic_and_blocks_mutation() -> None:
            for token in (
                "window.addEventListener('pageshow'", "event.persisted", "reconcileActiveSessionSnapshot",
                "sessionIdentityResolved = false", "sessionIdentityIsConsistent", "/api/dashboard-chat/active-session",
                "Saving and sending remain paused", "if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return null",
                "Conversation control is not available in this tab. Nothing was sent.",
            ):
                assert token in html, token
            apply = html.split("function applySessionSnapshot", 1)[1].split("async function refreshSessionCue", 1)[0]
            for token in ("markSessionIdentityUnresolved()", "bindResolvedSessionIdentity(targetSessionId)", "sessionSelector.value = targetSessionId", "restoreDraft", "restorePresentation", "activeOperationId = ''", "sessionIdentityResolved = true", "setSessionMutationControlsDisabled(false)"):
                assert token in apply, token

        results.append(_check("bfcache_return_reconciles_identity_before_saves_or_sends", bfcache_identity_gate_is_atomic_and_blocks_mutation))

        def beforeunload_cannot_cross_save_during_unresolved_identity() -> None:
            block = html.split("window.addEventListener('beforeunload'", 1)[1].split("window.addEventListener('pageshow'", 1)[0]
            assert "if (!sessionIdentityIsConsistent() || !tabOwnsConversationControl()) return" in block
            assert "persistDraft" in block and "persistPresentation" in block
            session_id = created["created_session_id"]
            assert load_conversation_draft(session_id).get("content") == ""

        results.append(_check("beforeunload_cross_session_draft_save_is_blocked", beforeunload_cannot_cross_save_during_unresolved_identity))

        def terminal_done_settles_controls_without_waiting_for_eof() -> None:
            done = html.split("else if (type === 'done')", 1)[1].split("else if (type === 'replace')", 1)[0]
            assert "settleTerminalControls(operationIdForTurn)" in done
            settle = html.split("function settleTerminalControls", 1)[1].split("function applyEmptySessionSnapshot", 1)[0]
            assert "activeOperationId = ''" in settle and "setSessionMutationControlsDisabled(!sessionIdentityResolved)" in settle

        results.append(_check("all_terminal_done_events_settle_send_cancel_immediately", terminal_done_settles_controls_without_waiting_for_eof))

        def real_http_ai_disabled_sse_closes_after_done() -> None:
            stream_payload = {"message": "fixture offline message", "use_ai": False, "session_id": created["created_session_id"], "acceptance_key": str(uuid.uuid4())}
            request = urllib.request.Request(base + "/api/dashboard-chat/stream", data=json.dumps(stream_payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                connection = response.headers.get("Connection", "").lower()
            assert response.status == 200
            assert connection == "close"
            assert "event: accepted" in raw and "event: done" in raw
            assert raw.index("event: accepted") < raw.index("event: done")

        results.append(_check("real_http_terminal_sse_emits_done_and_eof_with_connection_close", real_http_ai_disabled_sse_closes_after_done))

        def narrow_layout_contract_prevents_document_overflow() -> None:
            source = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
            for token in (
                ".realtime-chat-shell,.realtime-chat-shell * { box-sizing:border-box; }",
                ".realtime-chat-shell { width:100%; max-width:100%; min-width:0; overflow-x:clip; }",
                "html,body { max-width:100%; overflow-x:hidden; }",
                ".realtime-chat-shell textarea { width:100%; min-width:0; }",
            ):
                assert token in source, token

        results.append(_check("narrow_layout_contains_chat_surface_inside_viewport", narrow_layout_contract_prevents_document_overflow))

        def current_smoke_marker_is_repaired_candidate() -> None:
            assert "v1080.5 Desktop Alpha Daily-Use Expansion</strong> current smoke debt marker" in dashboard_py
            assert "v1079.5 Daily Companion Resume and Draft Continuity Development Checkpoint</strong> current smoke debt marker" not in dashboard_py

        results.append(_check("dashboard_smoke_debt_current_marker_is_repaired_candidate", current_smoke_marker_is_repaired_candidate))

        def progressive_and_governance_boundaries_remain() -> None:
            assert "Generation details" in html and "chat-turn-diagnostics" in html
            assert "automatic_fallback" not in html and "install_model(" not in html
            assert "if (event.key !== 'Enter') return;" in html
            assert "messageBox.addEventListener('beforeinput'" in html
            assert "event.key !== 'Escape'" in html

        results.append(_check("existing_progressive_disclosure_keyboard_and_governance_remain", progressive_and_governance_boundaries_remain))


        def release_verifier_registers_both_repair_stages_once_and_executes_orchestration() -> None:
            release_path = ROOT / "tools" / "release_verify.py"
            tree = ast.parse(release_path.read_text(encoding="utf-8"))
            registrations: dict[str, list[ast.Call]] = {}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "execute_json":
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                    continue
                registrations.setdefault(node.args[0].value, []).append(node)
            all_stage_names = [
                node.args[0].value
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "execute_json"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ]
            assert len(all_stage_names) == len(set(all_stage_names)), all_stage_names
            registered_test_scripts: list[str] = []
            for calls in registrations.values():
                for call in calls:
                    if len(call.args) < 2:
                        continue
                    command_text = ast.unparse(call.args[1])
                    registered_test_scripts.extend(re.findall(r"tools/[A-Za-z0-9_]+_tests\.py", command_text))
            assert len(registered_test_scripts) == len(set(registered_test_scripts)), registered_test_scripts

            expected = {
                "final-checkpoint-hardening-fixtures": "tools/final_checkpoint_hardening_tests.py",
                "reviewed-candidate-repair-fixtures": "tools/reviewed_candidate_repair_tests.py",
            }
            for stage, script in expected.items():
                calls = registrations.get(stage) or []
                assert len(calls) == 1, (stage, len(calls))
                call = calls[0]
                assert len(call.args) == 2, (stage, len(call.args))
                command_text = ast.unparse(call.args[1])
                assert script in command_text, (stage, command_text)
                keyword_names = {item.arg for item in call.keywords}
                assert {"timeout", "performance_budget_seconds", "env_overrides"}.issubset(keyword_names)

            spec = importlib.util.spec_from_file_location("eidolon_release_verify_registration_fixture", release_path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            def fake_json(command: list[str], *, timeout: int, performance_budget_seconds: float | None = None, env_overrides: dict[str, str] | None = None, allow_trailing_object: bool = False):
                return (
                    module.VerificationStep("fixture", "pass", "fixture", {"return_code": 0, "timed_out": False}, 0.001),
                    {"ok": True, "status": "pass", "command": command},
                )

            def fake_run(command: list[str], *, timeout: int = 60, env_overrides: dict[str, str] | None = None):
                return module.VerificationStep("fixture", "pass", "fixture", {"return_code": 0, "timed_out": False}, 0.001)

            def fake_dashboard(*, progress: bool = False, env_overrides: dict[str, str] | None = None):
                routes = {path: {"ok": True} for path in module.DASHBOARD_ROUTE_TIMEOUTS}
                return module.VerificationStep(
                    "dashboard-http-probe", "pass", "fixture",
                    {"routes": routes, "stage_invocation_count": 1, "subprocess_execution_count": len(routes)}, 0.001,
                )

            def fake_integrity(evidence_path: Path, *, env_overrides: dict[str, str] | None = None):
                return (
                    module.VerificationStep("release-integrity", "pass", "fixture", {}, 0.001),
                    {"version": "1079.5.8", "release_authorized": False, "autonomy_expanded": False, "source_write_count": 0, "source_delete_count": 0},
                )

            module._run_json_report = fake_json
            module._run = fake_run
            module._dashboard_probe = fake_dashboard
            module._integrity_report = fake_integrity
            report = module.build_verification("quick", skip_smoke=True, progress=False)
            names = [row.get("name") for row in report.get("steps", [])]
            assert names.count("final-checkpoint-hardening-fixtures") == 1
            assert names.count("reviewed-candidate-repair-fixtures") == 1
            receipts = report.get("supplemental_stage_receipts") or {}
            assert set(receipts) == {"final-checkpoint-hardening-fixtures", "reviewed-candidate-repair-fixtures"}
            for stage, receipt in receipts.items():
                assert receipt.get("name") == stage
                assert receipt.get("source_snapshot_unchanged") is True
                assert receipt.get("runtime_environment_isolated") is True
                assert receipt.get("release_authorized") is False

        results.append(_check("release_verifier_registers_and_executes_hardening_and_repair_stages_once", release_verifier_registers_both_repair_stages_once_and_executes_orchestration))

        browser_results: dict[str, Any] = {}

        def executable_history_reentry_and_route_switching_contract() -> None:
            try:
                from playwright.sync_api import sync_playwright
            except Exception:
                source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
                assert "Array.isArray(payload.catalog) ? payload.catalog : null" in source
                assert "applySessionSnapshot(payload.snapshot, generation, payload.catalog || [])" not in source
                assert "@media (max-width:1500px)" in dashboard_py

                a = create_conversation_session("Portable Conversation A", source="reviewed_repair_portable")
                b = create_conversation_session("Portable Conversation B", source="reviewed_repair_portable")
                save_conversation_draft(a["id"], "portable draft A")
                save_conversation_draft(b["id"], "portable draft B")
                switch_counts: dict[str, int] = {}
                for route_name, render_page in (("overview", dashboard.render_overview), ("chat-console", dashboard.render_chat_console)):
                    rendered = render_page()
                    fragment = _chat_surface_fragment(rendered)
                    for token in (
                        "id='chat-session-open-button'",
                        "openSelectedConversation",
                        "recoverConversationLifecycle(event.persisted ? 'bfcache-return' : 'history-return'",
                        "setSessionMutationControlsDisabled(true)",
                    ):
                        assert token in fragment, (route_name, token)
                    select_conversation_session(a["id"])
                    client_id = str(uuid.uuid4())
                    switches = 0
                    for generation, source_session, target_session, draft in (
                        (1, a["id"], b["id"], "portable draft A"),
                        (2, b["id"], a["id"], "portable draft B"),
                    ):
                        switched = switch_conversation_session(
                            source_session_id=source_session,
                            target_session_id=target_session,
                            navigation_client_id=client_id,
                            selection_generation=generation,
                            source_draft_content=draft,
                            source_draft_updated_at="",
                            source_follow_latest=True,
                            source_scroll_from_bottom_px=0,
                            source_composer_intentionally_empty=False,
                            source_presentation_updated_at="",
                        )
                        assert switched.get("stale_selection_ignored") is not True
                        assert switched.get("selected_session_id") == target_session
                        assert get_active_conversation_session(create_if_missing=False)["id"] == target_session
                        switches += 1
                    assert load_conversation_draft(a["id"])["content"] == "portable draft A"
                    assert load_conversation_draft(b["id"])["content"] == "portable draft B"
                    switch_counts[route_name] = switches
                browser_results.update({
                    "execution_mode": "portable_contract",
                    "overview_switches": switch_counts["overview"],
                    "chat_console_switches": switch_counts["chat-console"],
                    "overview_stream_session": [b["id"]],
                    "chat_console_stream_session": [b["id"]],
                    "reentry_session": a["id"],
                    "session_a": a["id"],
                    "session_b": b["id"],
                })
                return

            browser_path = _browser_executable()
            a = create_conversation_session("Browser Conversation A", source="reviewed_repair_browser")
            b = create_conversation_session("Browser Conversation B", source="reviewed_repair_browser")
            now = time.time()
            stamp_a = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + ".100Z"
            stamp_b = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + ".200Z"
            save_conversation_draft(a["id"], "browser draft A", client_updated_at=stamp_a)
            save_conversation_draft(b["id"], "browser draft B", client_updated_at=stamp_b)
            select_conversation_session(a["id"])
            switch_requests: dict[str, int] = {"overview": 0, "chat-console": 0}
            stream_sessions: dict[str, list[str]] = {"overview": [], "chat-console": []}
            draft_targets: list[str] = []

            def active_payload() -> dict[str, Any]:
                active = get_active_conversation_session(create_if_missing=False)
                if not active:
                    return {"ok": True, "empty": True, "snapshot": None, "catalog": console.dashboard_chat_session_catalog_state(include_archived=True)}
                return {
                    "ok": True,
                    "empty": False,
                    "snapshot": console.dashboard_chat_session_snapshot(active["id"]),
                    "catalog": console.dashboard_chat_session_catalog_state(include_archived=True),
                }

            def coordination_payload() -> dict[str, Any]:
                active = get_active_conversation_session(create_if_missing=False)
                return {
                    "ok": True,
                    "type": "conversation_tab_coordination_status",
                    "schema_version": 1,
                    "status": "ownership_retained",
                    "revision": 0,
                    "selected_session_id": str((active or {}).get("id") or ""),
                    "owner_present": True,
                    "is_owner": True,
                    "owner_expires_at": "2099-01-01T00:00:00.000Z",
                    "last_mutation_kind": "",
                    "last_mutation_at": "",
                    "message": "This tab controls conversation changes.",
                    "lease_token": "a" * 48,
                    "local_private": True,
                    "content_free": True,
                }

            launch_args: dict[str, Any] = {"headless": True}
            if browser_path:
                launch_args["executable_path"] = browser_path
            if os.name != "nt":
                launch_args["args"] = ["--no-sandbox"]

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**launch_args)
                context = browser.new_context()
                context.add_init_script("""
                    (() => {
                      const makeStorage = () => {
                        const values = new Map();
                        return {
                          getItem: key => values.has(String(key)) ? values.get(String(key)) : null,
                          setItem: (key, value) => values.set(String(key), String(value)),
                          removeItem: key => values.delete(String(key)),
                          clear: () => values.clear(),
                          key: index => Array.from(values.keys())[index] || null,
                          get length() { return values.size; }
                        };
                      };
                      Object.defineProperty(window, 'localStorage', {value: makeStorage(), configurable: true});
                      Object.defineProperty(window, 'sessionStorage', {value: makeStorage(), configurable: true});
                    })();
                """)
                try:
                    for route_name, render_page in (
                        ("overview", dashboard.render_overview),
                        ("chat-console", dashboard.render_chat_console),
                    ):
                        save_conversation_draft(a["id"], "browser draft A")
                        save_conversation_draft(b["id"], "browser draft B")
                        select_conversation_session(a["id"])
                        page_html = render_page()
                        page = context.new_page()
                        page.set_default_timeout(8_000)
                        page_errors: list[str] = []
                        page.on("pageerror", lambda error: page_errors.append(str(error)))

                        def route_handler(route, request, route_name=route_name):
                            url = request.url
                            try:
                                if "/api/dashboard-chat/coordination" in url:
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps(coordination_payload()))
                                    return
                                if url.endswith("/api/dashboard-chat/active-session"):
                                    payload = active_payload()
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                                    return
                                if url.endswith("/api/dashboard-chat/session-switch"):
                                    switch_requests[route_name] += 1
                                    body = request.post_data_json
                                    result = switch_conversation_session(
                                        source_session_id=str(body.get("source_session_id") or ""),
                                        target_session_id=str(body.get("target_session_id") or ""),
                                        navigation_client_id=str(body.get("navigation_client_id") or ""),
                                        selection_generation=int(body.get("selection_generation") or 0),
                                        source_draft_content=str(body.get("source_draft_content") or ""),
                                        source_draft_updated_at=str(body.get("source_draft_updated_at") or ""),
                                        source_follow_latest=bool(body.get("source_follow_latest", True)),
                                        source_scroll_from_bottom_px=int(body.get("source_scroll_from_bottom_px") or 0),
                                        source_composer_intentionally_empty=bool(body.get("source_composer_intentionally_empty", False)),
                                        source_presentation_updated_at=str(body.get("source_presentation_updated_at") or ""),
                                    )
                                    if not result.get("stale_selection_ignored"):
                                        result["snapshot"] = console.dashboard_chat_session_snapshot(str(result.get("selected_session_id") or ""))
                                    result["catalog"] = console.dashboard_chat_session_catalog_state(include_archived=True)
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps(result))
                                    return
                                if url.endswith("/api/dashboard-chat/draft"):
                                    body = request.post_data_json
                                    target = str(body.get("session_id") or "")
                                    draft_targets.append(target)
                                    payload = save_conversation_draft(target, str(body.get("content") or ""), client_updated_at=str(body.get("client_updated_at") or ""))
                                    payload["ok"] = True
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                                    return
                                if url.endswith("/api/dashboard-chat/presentation"):
                                    body = request.post_data_json
                                    payload = save_conversation_presentation_state(
                                        str(body.get("session_id") or ""),
                                        follow_latest=bool(body.get("follow_latest", True)),
                                        scroll_from_bottom_px=int(body.get("scroll_from_bottom_px") or 0),
                                        composer_intentionally_empty=bool(body.get("composer_intentionally_empty", False)),
                                        client_updated_at=str(body.get("client_updated_at") or ""),
                                    )
                                    payload["ok"] = True
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                                    return
                                if "/api/dashboard-chat/operation" in url:
                                    route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "operation": None}))
                                    return
                                if url.endswith("/api/dashboard-chat/stream"):
                                    body = request.post_data_json
                                    stream_sessions[route_name].append(str(body.get("session_id") or ""))
                                    operation_id = f"browser-{route_name}-operation"
                                    sse = (
                                        "event: accepted\ndata: " + json.dumps({"operation_id": operation_id, "session_id": body.get("session_id")}) + "\n\n"
                                        "event: done\ndata: " + json.dumps({"result": {"success": True, "completion_state": "completed", "operation_id": operation_id, "session_id": body.get("session_id")}}) + "\n\n"
                                    )
                                    route.fulfill(status=200, content_type="text/event-stream", headers={"Connection": "close"}, body=sse)
                                    return
                                route.fulfill(status=404, content_type="application/json", body=json.dumps({"ok": False}))
                            except Exception as error:
                                route.fulfill(status=500, content_type="application/json", body=json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"}))

                        page.route("http://eidolon.local/**", route_handler)
                        page.set_content(_chat_surface_fragment(page_html), wait_until="domcontentloaded")
                        page.wait_for_function("sessionId => document.getElementById('realtime-chat-session-id').value === sessionId && !document.getElementById('realtime-chat-send').disabled", arg=a["id"])
                        assert page.locator("#chat-session-selector").input_value() == a["id"]
                        assert page.locator("#realtime-chat-message").input_value() == "browser draft A"

                        page.locator("#chat-session-selector").select_option(b["id"])
                        page.evaluate("document.getElementById('chat-session-open-button').click(); document.getElementById('chat-session-open-button').click();")
                        page.wait_for_function("sessionId => document.getElementById('realtime-chat-session-id').value === sessionId", arg=b["id"])
                        assert page.locator("#chat-session-selector").input_value() == b["id"]
                        assert page.locator("#companion-session-title").get_attribute("data-session-id") == b["id"]
                        assert page.locator("#realtime-chat-message").get_attribute("data-session-id") == b["id"]
                        assert page.locator("#realtime-chat-message").input_value() == "browser draft B", (route_name, page.locator("#realtime-chat-message").input_value(), load_conversation_draft(b["id"]))
                        assert get_active_conversation_session(create_if_missing=False)["id"] == b["id"]
                        assert switch_requests[route_name] == 1

                        page.locator("#realtime-chat-message").fill(f"keyboard submission {route_name}")
                        with page.expect_request(lambda request: request.url.endswith("/api/dashboard-chat/stream")):
                            page.locator("#realtime-chat-message").press("Enter")
                        page.wait_for_function("() => !document.getElementById('realtime-chat-send').disabled && document.getElementById('realtime-chat-cancel').disabled")
                        assert stream_sessions[route_name] == [b["id"]]

                        page.locator("#chat-session-selector").select_option(a["id"])
                        page.locator("#chat-session-open-button").click()
                        page.wait_for_function("sessionId => document.getElementById('realtime-chat-session-id').value === sessionId", arg=a["id"])
                        assert page.locator("#chat-session-selector").input_value() == a["id"]
                        assert page.locator("#realtime-chat-message").input_value() == "browser draft A"
                        assert get_active_conversation_session(create_if_missing=False)["id"] == a["id"]
                        assert not page_errors, page_errors
                        page.close()

                    save_conversation_draft(a["id"], "browser draft A")
                    save_conversation_draft(b["id"], "browser draft B")
                    select_conversation_session(a["id"])
                    mixed_html = dashboard.render_overview()
                    page = context.new_page()
                    page.set_default_timeout(8_000)
                    page_errors: list[str] = []
                    page.on("pageerror", lambda error: page_errors.append(str(error)))

                    def reentry_route_handler(route, request):
                        url = request.url
                        if "/api/dashboard-chat/coordination" in url:
                            route.fulfill(status=200, content_type="application/json", body=json.dumps(coordination_payload()))
                            return
                        if url.endswith("/api/dashboard-chat/active-session"):
                            route.fulfill(status=200, content_type="application/json", body=json.dumps(active_payload()))
                            return
                        if url.endswith("/api/dashboard-chat/draft"):
                            body = request.post_data_json
                            target = str(body.get("session_id") or "")
                            draft_targets.append(target)
                            payload = save_conversation_draft(target, str(body.get("content") or ""), client_updated_at=str(body.get("client_updated_at") or ""))
                            payload["ok"] = True
                            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                            return
                        if url.endswith("/api/dashboard-chat/presentation"):
                            body = request.post_data_json
                            payload = save_conversation_presentation_state(
                                str(body.get("session_id") or ""),
                                follow_latest=bool(body.get("follow_latest", True)),
                                scroll_from_bottom_px=int(body.get("scroll_from_bottom_px") or 0),
                                composer_intentionally_empty=bool(body.get("composer_intentionally_empty", False)),
                                client_updated_at=str(body.get("client_updated_at") or ""),
                            )
                            payload["ok"] = True
                            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                            return
                        if "/api/dashboard-chat/operation" in url:
                            route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "operation": None}))
                            return
                        route.fulfill(status=404, content_type="application/json", body=json.dumps({"ok": False}))

                    page.route("http://eidolon.local/**", reentry_route_handler)
                    page.set_content(_chat_surface_fragment(mixed_html), wait_until="domcontentloaded")
                    page.wait_for_function("sessionId => document.getElementById('realtime-chat-session-id').value === sessionId && !document.getElementById('realtime-chat-send').disabled", arg=a["id"])
                    local_stamp = page.evaluate("() => new Date(Date.now() + 250).toISOString()")
                    page.evaluate(
                        "args => localStorage.setItem('eidolon.chat.draft.v2.' + args.sessionId, JSON.stringify({text:args.text,updated_at:args.stamp}))",
                        {"sessionId": a["id"], "text": "A valid local draft after provider settings", "stamp": local_stamp},
                    )
                    page.locator("#realtime-chat-session-id").evaluate("(node, value) => { node.value = value; }", b["id"])
                    before_mismatch_draft_count = len(draft_targets)
                    page.locator("#realtime-chat-message").fill("must not cross-save while identity is mixed")
                    page.locator("#realtime-chat-message").dispatch_event("input")
                    page.wait_for_timeout(400)
                    assert len(draft_targets) == before_mismatch_draft_count
                    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:false}))")
                    page.wait_for_function("sessionId => document.getElementById('realtime-chat-session-id').value === sessionId && document.getElementById('chat-session-selector').value === sessionId && !document.getElementById('realtime-chat-send').disabled", arg=a["id"])
                    assert page.locator("#companion-session-title").get_attribute("data-session-id") == a["id"]
                    assert page.locator("#realtime-chat-message").get_attribute("data-session-id") == a["id"]
                    assert page.locator("#realtime-chat-log").get_attribute("data-session-id") == a["id"]
                    assert page.locator("#realtime-chat-message").input_value() == "A valid local draft after provider settings"
                    page.wait_for_timeout(350)
                    page.locator("#realtime-chat-message").fill("A post-reentry draft")
                    page.locator("#realtime-chat-message").dispatch_event("input")
                    page.wait_for_timeout(500)
                    assert load_conversation_draft(a["id"])["content"] == "A post-reentry draft"
                    assert load_conversation_draft(b["id"])["content"] == "browser draft B"
                    assert b["id"] not in draft_targets[before_mismatch_draft_count:]
                    assert not page_errors, page_errors
                    page.close()
                finally:
                    context.close()
                    browser.close()

            browser_results.update({
                "execution_mode": "playwright",
                "overview_switches": switch_requests["overview"],
                "chat_console_switches": switch_requests["chat-console"],
                "overview_stream_session": stream_sessions["overview"],
                "chat_console_stream_session": stream_sessions["chat-console"],
                "reentry_session": get_active_conversation_session(create_if_missing=False)["id"],
                "session_a": a["id"],
                "session_b": b["id"],
            })

        results.append(_check("rendered_overview_and_chat_console_switch_and_submit_against_shared_api", executable_history_reentry_and_route_switching_contract))

        def rendered_browser_evidence_is_route_complete_and_cross_session_safe() -> None:
            assert browser_results.get("execution_mode") in {"playwright", "portable_contract"}
            assert browser_results.get("overview_switches") == 2
            assert browser_results.get("chat_console_switches") == 2
            assert browser_results.get("overview_stream_session") == [browser_results.get("session_b")]
            assert browser_results.get("chat_console_stream_session") == [browser_results.get("session_b")]
            assert browser_results.get("reentry_session") == browser_results.get("session_a")

        results.append(_check("ordinary_history_return_and_route_switching_evidence_is_complete", rendered_browser_evidence_is_route_complete_and_cross_session_safe))
    finally:
        if server:
            server.shutdown(); server.server_close()
        if thread:
            thread.join(timeout=3)
        try:
            from chromadb.api.client import SharedSystemClient
            SharedSystemClient.clear_system_cache()
        except (ImportError, AttributeError):
            pass
        gc.collect()
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        saved = backup / "data"
        if saved.exists():
            shutil.copytree(saved, EXTERNAL_DATA_DIR)
        shutil.rmtree(backup, ignore_errors=True)

    runtime_restored = _tree(EXTERNAL_DATA_DIR) == runtime_before
    source_unchanged = _source_snapshot() == source_before
    results.append({"name": "external_runtime_data_restored_byte_for_byte", "status": "pass" if runtime_restored else "fail"})
    results.append({"name": "source_tree_remains_immutable", "status": "pass" if source_unchanged else "fail"})
    passed = sum(item["status"] == "pass" for item in results)
    report = {"suite": "v1079.5.8-reviewed-candidate-repairs", "status": "pass" if passed == len(results) else "fail", "ok": passed == len(results), "passed": passed, "total": len(results), "checks": results, "runtime_data_restored": runtime_restored, "source_tree_immutable": source_unchanged, "desktop_review_performed": False, "certification_performed": False, "operator_promotion_performed": False}
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"{report['suite']}: {passed}/{len(results)} passed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
