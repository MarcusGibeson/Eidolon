from __future__ import annotations

"""Deterministic v1079.6.0 multi-tab conversation coordination fixtures.

The suite uses isolated local runtime data, a fake provider counter, and rendered
JavaScript syntax checks. It never contacts a provider, changes model settings,
installs or deletes models, grants approval, promotes a release, or expands autonomy.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
RUNTIME_PARENT = Path(
    os.environ.get("EIDOLON_DATA_DIR")
    or (Path(tempfile.gettempdir()) / "eidolon-v1079-6-multi-tab-fixture-data")
).resolve()
RUNTIME_PARENT.mkdir(parents=True, exist_ok=True)
EXTERNAL_DATA_DIR = Path(tempfile.mkdtemp(prefix="multi-tab-fixture-", dir=str(RUNTIME_PARENT))).resolve()
os.environ["EIDOLON_DATA_DIR"] = str(EXTERNAL_DATA_DIR)
sys.path.insert(0, str(AGENT))


def _tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _source_snapshot() -> dict[str, str]:
    exercised_sources = (
        Path(__file__).resolve(),
        AGENT / "conversation_tab_coordination.py",
        AGENT / "dashboard_chat_console.py",
        AGENT / "dashboard.py",
        AGENT / "conversation_navigation.py",
        AGENT / "conversation_operations.py",
        AGENT / "conversation_sessions.py",
    )
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in exercised_sources
        if path.is_file()
    }


def _check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {
            "name": name,
            "status": "fail",
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        }


def _uuid() -> str:
    return str(uuid.uuid4())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    runtime_before = _tree(EXTERNAL_DATA_DIR)
    source_before = _source_snapshot()
    backup = Path(tempfile.mkdtemp(prefix="eidolon-v1079-6-multi-tab-backup-"))
    if EXTERNAL_DATA_DIR.exists():
        shutil.copytree(EXTERNAL_DATA_DIR, backup / "data", dirs_exist_ok=True)
        shutil.rmtree(EXTERNAL_DATA_DIR)
    EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    try:
        import conversation_tab_coordination as coordination
        import dashboard_chat_console as console
        from conversation_navigation import perform_conversation_lifecycle
        from conversation_operations import (
            create_operation_marker,
            finalize_operation_marker,
            load_operation_marker,
            new_conversation_operation_id,
        )
        from conversation_sessions import (
            append_conversation_turn,
            conversation_session_turns,
            create_conversation_session,
            list_conversation_sessions,
            load_conversation_draft,
            load_conversation_session,
            save_conversation_draft,
            select_conversation_session,
        )

        def reset_coordination() -> None:
            shutil.rmtree(coordination.TAB_COORDINATION_DIR, ignore_errors=True)

        def register_owner(now: float = 100.0, lease_seconds: float = 10.0) -> tuple[str, str, str]:
            tab_id = _uuid()
            browser_id = _uuid()
            state = coordination.register_dashboard_tab(
                tab_id, browser_id, instance_nonce=_uuid(), now_epoch=now, lease_seconds=lease_seconds
            )
            assert state["is_owner"] is True and state.get("lease_token")
            return tab_id, browser_id, str(state["lease_token"])

        def stable_tab_identity_and_content_free_coordination() -> None:
            reset_coordination()
            tab_a, browser, token = register_owner()
            tab_b = _uuid()
            follower = coordination.register_dashboard_tab(tab_b, browser, now_epoch=101.0, lease_seconds=10.0)
            assert follower["is_owner"] is False and follower["owner_present"] is True
            assert "lease_token" not in follower
            retained = coordination.heartbeat_dashboard_tab(tab_a, token, now_epoch=102.0, lease_seconds=10.0)
            assert retained["is_owner"] is True
            raw_state = json.loads(coordination.TAB_COORDINATION_STATE_FILE.read_text(encoding="utf-8"))
            assert raw_state["content_free"] is True and raw_state["local_private"] is True
            assert coordination.coordination_record_contains_private_fields(raw_state) is False
            encoded = json.dumps(raw_state).lower()
            for forbidden in ("draft text", "prompt", "assistant_response", "provider payload", "credential"):
                assert forbidden not in encoded

            activated = coordination.acquire_dashboard_tab_ownership(
                tab_b, browser, force=True, same_browser_only=True, now_epoch=103.0, lease_seconds=10.0
            )
            assert activated["is_owner"] is True and activated["status"] == "ownership_transferred"

            reset_coordination()
            _tab_owner, _owner_browser, _owner_token = register_owner()
            other_browser = coordination.acquire_dashboard_tab_ownership(
                _uuid(), _uuid(), force=True, same_browser_only=True, now_epoch=101.0, lease_seconds=10.0
            )
            assert other_browser["is_owner"] is False and other_browser["status"] == "ownership_conflict"

            reset_coordination()
            duplicated_tab = _uuid()
            duplicated_browser = _uuid()
            first_instance = coordination.register_dashboard_tab(
                duplicated_tab, duplicated_browser, instance_nonce=_uuid(), now_epoch=200.0
            )
            duplicate_instance = coordination.register_dashboard_tab(
                duplicated_tab, duplicated_browser, instance_nonce=_uuid(), now_epoch=200.1
            )
            assert first_instance["is_owner"] is True
            assert duplicate_instance["is_owner"] is False
            assert duplicate_instance["status"] == "identity_conflict"
            assert duplicate_instance["renew_tab_id"] is True
            assert "lease_token" not in duplicate_instance

        results.append(_check("stable_runtime_tab_identity_and_content_free_lease", stable_tab_identity_and_content_free_coordination))

        def two_tabs_editing_same_draft_preserve_owner_and_newest_write() -> None:
            reset_coordination()
            session = create_conversation_session("Shared draft", source="multi_tab_fixture")
            tab_a, browser, token_a = register_owner()
            tab_b = _uuid()
            coordination.register_dashboard_tab(tab_b, browser, now_epoch=101.0, lease_seconds=10.0)
            callback_count = {"value": 0}
            mutation_key = "draft:" + _uuid()

            def owner_save() -> dict[str, Any]:
                callback_count["value"] += 1
                return save_conversation_draft(
                    session["id"], "owner draft", source="multi_tab_fixture",
                    client_updated_at="2099-01-01T12:00:02.000Z",
                )

            first = coordination.execute_coordinated_mutation(
                tab_id=tab_a, lease_token=token_a, mutation_key=mutation_key,
                mutation_kind="draft.save", session_id=session["id"],
                expected_revision=0, advance_revision=False, callback=owner_save, now_epoch=101.0,
            )
            duplicate = coordination.execute_coordinated_mutation(
                tab_id=tab_a, lease_token=token_a, mutation_key=mutation_key,
                mutation_kind="draft.save", session_id=session["id"],
                expected_revision=0, advance_revision=False, callback=owner_save, now_epoch=101.1,
            )
            follower = coordination.claim_dashboard_tab_mutation(
                tab_id=tab_b, lease_token="", mutation_key="draft:" + _uuid(),
                mutation_kind="draft.save", session_id=session["id"],
                expected_revision=0, advance_revision=False, now_epoch=102.0,
            )
            delayed = save_conversation_draft(
                session["id"], "older delayed draft", source="multi_tab_fixture",
                client_updated_at="2099-01-01T12:00:01.000Z",
            )
            assert first["ok"] is True
            assert duplicate["duplicate_mutation"] is True
            assert callback_count["value"] == 1
            assert follower["ok"] is False and follower["status"] == "ownership_required"
            assert delayed["stale_update_ignored"] is True
            assert load_conversation_draft(session["id"])["content"] == "owner draft"
            mutation_names = [path.name for path in coordination.TAB_COORDINATION_MUTATION_DIR.glob("*.json")]
            assert mutation_names and all(re.fullmatch(r"[a-f0-9]{64}\.json", name) for name in mutation_names)

        results.append(_check("two_tabs_same_draft_owner_and_newest_write_win_once", two_tabs_editing_same_draft_preserve_owner_and_newest_write))

        def simultaneous_and_rapid_sends_start_one_fake_provider_request() -> None:
            reset_coordination()
            session = create_conversation_session("Send race", source="multi_tab_fixture")
            tab_a, browser, token_a = register_owner()
            tab_b = _uuid()
            coordination.register_dashboard_tab(tab_b, browser, now_epoch=100.0, lease_seconds=10.0)
            provider_calls: list[str] = []
            barrier = threading.Barrier(2)

            def attempt(tab_id: str, token: str, key: str) -> dict[str, Any]:
                barrier.wait(timeout=3)
                return coordination.execute_coordinated_mutation(
                    tab_id=tab_id, lease_token=token, mutation_key=key,
                    mutation_kind="turn.send", session_id=session["id"],
                    expected_revision=0, advance_revision=True,
                    callback=lambda: provider_calls.append(key) or {"operation_id": "conversation_20990101T120000_" + "a" * 12, "session_id": session["id"], "status": "accepted"},
                    now_epoch=101.0,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                owner_future = pool.submit(attempt, tab_a, token_a, "send:" + _uuid())
                follower_future = pool.submit(attempt, tab_b, "", "send:" + _uuid())
                pair = [owner_future.result(timeout=5), follower_future.result(timeout=5)]
            assert sum(1 for item in pair if item.get("ok")) == 1
            assert len(provider_calls) == 1

            reset_coordination()
            tab_a, _browser, token_a = register_owner()
            barrier = threading.Barrier(2)
            provider_calls.clear()

            def rapid(key: str) -> dict[str, Any]:
                barrier.wait(timeout=3)
                return coordination.execute_coordinated_mutation(
                    tab_id=tab_a, lease_token=token_a, mutation_key=key,
                    mutation_kind="turn.send", session_id=session["id"],
                    expected_revision=0, advance_revision=True,
                    callback=lambda: provider_calls.append(key) or {"operation_id": "conversation_20990101T120001_" + "b" * 12, "session_id": session["id"], "status": "accepted"},
                    now_epoch=101.0,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                rapid_results = [
                    pool.submit(rapid, "rapid:" + _uuid()),
                    pool.submit(rapid, "rapid:" + _uuid()),
                ]
                rapid_results = [future.result(timeout=5) for future in rapid_results]
            assert sum(1 for item in rapid_results if item.get("ok")) == 1
            assert any(item.get("status") == "stale_revision" for item in rapid_results if not item.get("ok"))
            assert len(provider_calls) == 1

            winning_key = next(item["claim"]["mutation_key"] for item in rapid_results if item.get("ok"))
            replay = coordination.execute_coordinated_mutation(
                tab_id=tab_a, lease_token=token_a, mutation_key=winning_key,
                mutation_kind="turn.send", session_id=session["id"],
                expected_revision=0, advance_revision=True,
                callback=lambda: provider_calls.append("duplicate") or {},
                now_epoch=101.2,
            )
            assert replay["duplicate_mutation"] is True and len(provider_calls) == 1

        results.append(_check("simultaneous_and_rapid_sends_start_one_provider_request", simultaneous_and_rapid_sends_start_one_fake_provider_request))

        def ownership_releases_or_expires_and_transfers_without_deadlock() -> None:
            reset_coordination()
            tab_a, browser, token_a = register_owner(now=100.0, lease_seconds=3.0)
            tab_b = _uuid()
            blocked = coordination.acquire_dashboard_tab_ownership(tab_b, browser, now_epoch=101.0, lease_seconds=3.0)
            assert blocked["is_owner"] is False and blocked["status"] == "ownership_conflict"
            forced = coordination.acquire_dashboard_tab_ownership(
                tab_b, browser, force=True, now_epoch=101.1, lease_seconds=3.0
            )
            assert forced["is_owner"] is True and forced["status"] == "ownership_transferred"

            reset_coordination()
            tab_a, browser, token_a = register_owner(now=100.0, lease_seconds=3.0)
            tab_b = _uuid()
            released = coordination.release_dashboard_tab_ownership(tab_a, token_a, now_epoch=102.0)
            assert released["owner_present"] is False
            acquired = coordination.acquire_dashboard_tab_ownership(tab_b, browser, now_epoch=102.1, lease_seconds=3.0)
            assert acquired["is_owner"] is True

            reset_coordination()
            tab_a, browser, token_a = register_owner(now=150.0, lease_seconds=10.0)
            hidden = coordination.heartbeat_dashboard_tab(
                tab_a, token_a, visible=False, now_epoch=151.0, lease_seconds=10.0
            )
            assert hidden["is_owner"] is True
            tab_b = _uuid()
            visible_transfer = coordination.acquire_dashboard_tab_ownership(
                tab_b, browser, visible=True, now_epoch=151.1, lease_seconds=10.0
            )
            assert visible_transfer["is_owner"] is True
            assert visible_transfer["status"] == "ownership_transferred"

            reset_coordination()
            _tab_a, browser, _token_a = register_owner(now=200.0, lease_seconds=3.0)
            tab_b = _uuid()
            expired_transfer = coordination.acquire_dashboard_tab_ownership(tab_b, browser, now_epoch=204.0, lease_seconds=3.0)
            assert expired_transfer["is_owner"] is True
            assert coordination.coordination_snapshot(tab_id=tab_b, now_epoch=204.1)["is_owner"] is True

        results.append(_check("ownership_transfer_after_close_or_stale_tab", ownership_releases_or_expires_and_transfers_without_deadlock))

        def delayed_provider_result_after_transfer_records_one_terminal_turn() -> None:
            reset_coordination()
            session = create_conversation_session("Delayed result", source="multi_tab_fixture")
            tab_a, browser, token_a = register_owner(now=100.0, lease_seconds=3.0)
            key = _uuid()
            claim = coordination.claim_dashboard_tab_mutation(
                tab_id=tab_a, lease_token=token_a, mutation_key=key,
                mutation_kind="turn.send", session_id=session["id"], expected_revision=0,
                advance_revision=True, now_epoch=100.5,
            )
            assert claim["ok"] is True
            operation_id = new_conversation_operation_id()
            create_operation_marker(operation_id, session["id"], acceptance_key=key)
            coordination.complete_dashboard_tab_mutation(
                key, success=True, selected_session_id=session["id"],
                result={"operation_id": operation_id, "session_id": session["id"], "status": "accepted"},
                now_epoch=100.6,
            )
            tab_b = _uuid()
            transferred = coordination.acquire_dashboard_tab_ownership(tab_b, browser, now_epoch=104.0, lease_seconds=3.0)
            assert transferred["is_owner"] is True

            first_turn = append_conversation_turn(
                session["id"], turn_id=operation_id, user_message="delayed user",
                assistant_response="delayed answer", completion_state="completed", success=True,
                source="multi_tab_delayed_result", select_session=False,
            )
            duplicate_turn = append_conversation_turn(
                session["id"], turn_id=operation_id, user_message="different duplicate",
                assistant_response="different duplicate", completion_state="completed", success=True,
                source="multi_tab_delayed_result", select_session=False,
            )
            final = finalize_operation_marker(
                operation_id, completion_state="completed", success=True,
                final_session_turn_recorded=True,
            )
            late_failure = finalize_operation_marker(
                operation_id, completion_state="failed", success=False,
                failure_category="late_packet", final_session_turn_recorded=True,
            )
            assert first_turn == duplicate_turn
            assert len([turn for turn in conversation_session_turns(session["id"]) if turn["id"] == operation_id]) == 1
            assert final and final["public_state"] == "completed"
            assert late_failure and late_failure["public_state"] == "completed"
            assert load_operation_marker(operation_id)["public_state"] == "completed"
            assert coordination.coordination_snapshot(tab_id=tab_b, now_epoch=104.1)["is_owner"] is True

        results.append(_check("delayed_provider_result_after_transfer_is_reconciled_once", delayed_provider_result_after_transfer_records_one_terminal_turn))

        def competing_lifecycle_actions_are_each_exactly_once() -> None:
            reset_coordination()
            base = create_conversation_session("Lifecycle base", source="multi_tab_fixture")
            select_conversation_session(base["id"])
            tab_a, browser, token_a = register_owner()
            tab_b = _uuid()
            coordination.register_dashboard_tab(tab_b, browser, now_epoch=100.0, lease_seconds=10.0)
            client = _uuid()
            generation = 0
            revision = 0

            def apply(action: str, source_id: str, target_id: str = "", title: str = "") -> dict[str, Any]:
                nonlocal generation, revision
                generation += 1
                key = "life_" + _uuid()
                loser = coordination.claim_dashboard_tab_mutation(
                    tab_id=tab_b, lease_token="", mutation_key="lose:" + _uuid(),
                    mutation_kind="lifecycle." + action, session_id=target_id or source_id,
                    expected_revision=revision, advance_revision=True, now_epoch=101.0 + generation,
                )
                assert loser["ok"] is False and loser["status"] == "ownership_required"
                claim = coordination.claim_dashboard_tab_mutation(
                    tab_id=tab_a, lease_token=token_a, mutation_key=key,
                    mutation_kind="lifecycle." + action, session_id=target_id or source_id,
                    expected_revision=revision, advance_revision=True, now_epoch=101.0 + generation,
                )
                assert claim["ok"] is True
                revision = int(claim["revision"])
                result = perform_conversation_lifecycle(
                    action=action, navigation_client_id=client, lifecycle_generation=generation,
                    request_key=key, source_session_id=source_id, target_session_id=target_id,
                    title=title, source_draft_content="", source_draft_updated_at="",
                    source_follow_latest=True, source_scroll_from_bottom_px=0,
                    source_composer_intentionally_empty=True, source_presentation_updated_at="",
                )
                coordination.complete_dashboard_tab_mutation(
                    key, success=True, selected_session_id=str(result.get("selected_session_id") or ""),
                    result=result, now_epoch=101.5 + generation,
                )
                count_before = len(list_conversation_sessions(include_archived=True))
                replay = coordination.claim_dashboard_tab_mutation(
                    tab_id=tab_a, lease_token=token_a, mutation_key=key,
                    mutation_kind="lifecycle." + action, session_id=target_id or source_id,
                    expected_revision=revision - 1, advance_revision=True, now_epoch=101.6 + generation,
                )
                assert replay["ok"] is True and replay["duplicate_mutation"] is True
                assert len(list_conversation_sessions(include_archived=True)) == count_before
                return result

            created = apply("create", base["id"], title="Created once")
            created_id = str(created["created_session_id"])
            renamed = apply("rename", created_id, created_id, "Renamed once")
            assert renamed["changed"] is True and load_conversation_session(created_id, include_turns=False)["title"] == "Renamed once"
            archived = apply("archive", created_id, created_id)
            fallback = str(archived["selected_session_id"])
            assert load_conversation_session(created_id, include_turns=False)["status"] == "archived"
            restored = apply("restore", fallback, created_id)
            assert restored["selected_session_id"] == fallback
            apply("archive", fallback, created_id)
            restored_open = apply("restore_open", fallback, created_id)
            assert restored_open["selected_session_id"] == created_id
            assert load_conversation_session(created_id, include_turns=False)["status"] == "active"

        results.append(_check("create_rename_archive_restore_and_open_competing_tabs_exact_once", competing_lifecycle_actions_are_each_exactly_once))

        def rendered_browser_coordination_covers_restore_navigation_offline_and_restart() -> None:
            html = console.render_realtime_chat_panel(None, include_archived=True)
            required = (
                "eidolon.chat.tab-coordination.v1", "sessionStorage", "localStorage",
                "BroadcastChannel", "navigator.locks", "coordination_revision",
                "mutation_key", "pagehide", "pageshow", "event.persisted",
                "visibilitychange", "document.hidden", "window.addEventListener('online'",
                "window.addEventListener('offline'", "history-return", "provider settings",
                "postCoordination('register')", "tabOwnsConversationControl() ? 'heartbeat' : 'snapshot'",
                "postCoordination('acquire')", "action:'release'",
                "Another tab controls changes", "Take control", "restore_open",
                "async function confirmConversationControl()", "if (!await confirmConversationControl())",
                "tabCoordination.dataset.tabId = tabIdentity.tab_id",
                "instance_nonce:coordinationInstanceNonce", "payload.renew_tab_id",
            )
            for token in required:
                assert token in html, token
            assert "source_draft_content" in html and "source_presentation_updated_at" in html
            assert "acceptance_key: acceptanceKey" in html and "coordinationMutationFields(acceptanceKey)" in html
            assert "newMutationKey('retry')" in html and "newMutationKey('cancel')" in html
            assert "newMutationKey('acknowledge')" in html

            reset_coordination()
            tab_a, browser, _token = register_owner(now=300.0, lease_seconds=3.0)
            persisted = coordination.coordination_snapshot(tab_id=tab_a, now_epoch=301.0)
            assert persisted["is_owner"] is True
            # Simulate a dashboard process restart by reading the persisted content-free state.
            restarted = coordination.coordination_snapshot(tab_id=tab_a, now_epoch=301.5)
            assert restarted["revision"] == persisted["revision"] and restarted["is_owner"] is True
            tab_b = _uuid()
            after_sleep = coordination.acquire_dashboard_tab_ownership(tab_b, browser, now_epoch=304.0, lease_seconds=3.0)
            assert after_sleep["is_owner"] is True

        results.append(_check("back_provider_return_sleep_offline_and_restart_hooks_render", rendered_browser_coordination_covers_restore_navigation_offline_and_restart))

        def rendered_javascript_and_python_compile() -> None:
            html = console.render_realtime_chat_panel(None, include_archived=True)
            scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
            assert scripts
            node = shutil.which("node")
            if node:
                temporary = Path(tempfile.mkdtemp(prefix="eidolon-multi-tab-js-")) / "dashboard-chat.js"
                temporary.write_text("\n".join(scripts), encoding="utf-8")
                completed = subprocess.run([node, "--check", str(temporary)], capture_output=True, text=True, timeout=20)
                assert completed.returncode == 0, completed.stderr or completed.stdout
                shutil.rmtree(temporary.parent, ignore_errors=True)
            with tempfile.TemporaryDirectory(prefix="eidolon-multi-tab-compile-") as compile_raw:
                compile_root = Path(compile_raw)
                sources = (
                    AGENT / "conversation_tab_coordination.py",
                    AGENT / "dashboard_chat_console.py",
                    AGENT / "dashboard.py",
                )
                command = [
                    sys.executable,
                    "-c",
                    "import py_compile,sys; "
                    "pairs=zip(sys.argv[1::2],sys.argv[2::2]); "
                    "[py_compile.compile(src,cfile=dst,doraise=True) for src,dst in pairs]",
                ]
                for index, source in enumerate(sources):
                    command.extend((str(source), str(compile_root / f"module-{index}.pyc")))
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                assert completed.returncode == 0, completed.stderr or completed.stdout

        results.append(_check("rendered_javascript_syntax_and_python_compilation", rendered_javascript_and_python_compile))

        def receipts_are_bounded_private_and_one_per_mutation() -> None:
            reset_coordination()
            session = create_conversation_session("Receipt fixture", source="multi_tab_fixture")
            tab_id, _browser, token = register_owner(now=500.0, lease_seconds=10.0)
            key = "receipt_" + _uuid()
            claim = coordination.claim_dashboard_tab_mutation(
                tab_id=tab_id, lease_token=token, mutation_key=key,
                mutation_kind="draft.save", session_id=session["id"],
                expected_revision=0, advance_revision=False, now_epoch=501.0,
            )
            assert claim["ok"] is True
            coordination.complete_dashboard_tab_mutation(
                key, success=True, selected_session_id=session["id"],
                result={"session_id": session["id"], "status": "saved"}, now_epoch=501.1,
            )
            files = sorted(coordination.TAB_COORDINATION_MUTATION_DIR.glob("*.json"))
            assert files
            keys: set[str] = set()
            for path in files:
                record = json.loads(path.read_text(encoding="utf-8"))
                assert record["mutation_key"] not in keys
                keys.add(record["mutation_key"])
                assert record["local_private"] is True and record["content_free"] is True
                assert coordination.coordination_record_contains_private_fields(record) is False
                assert set(record.get("result") or {}).issubset(coordination._SAFE_RESULT_FIELDS)
            assert len(keys) == len(files)

        results.append(_check("every_persistent_mutation_has_one_bounded_receipt", receipts_are_bounded_private_and_one_per_mutation))

    finally:
        if EXTERNAL_DATA_DIR.exists():
            shutil.rmtree(EXTERNAL_DATA_DIR)
        if (backup / "data").exists():
            shutil.copytree(backup / "data", EXTERNAL_DATA_DIR, dirs_exist_ok=True)
        shutil.rmtree(backup, ignore_errors=True)

    source_after = _source_snapshot()
    runtime_after = _tree(EXTERNAL_DATA_DIR)
    results.append({
        "name": "source_and_preexisting_runtime_are_unchanged",
        "status": "pass" if source_before == source_after and runtime_before == runtime_after else "fail",
        **({} if source_before == source_after and runtime_before == runtime_after else {
            "error": "The deterministic suite changed source files or did not restore preexisting runtime data."
        }),
    })
    passed = all(item.get("status") == "pass" for item in results)
    report = {
        "type": "multi_tab_conversation_coordination_tests",
        "version": "1079.6.0",
        "ok": passed,
        "status": "pass" if passed else "fail",
        "checks": results,
        "summary": {
            "passed": sum(1 for item in results if item.get("status") == "pass"),
            "failed": sum(1 for item in results if item.get("status") != "pass"),
        },
    }
    print(json.dumps(report, indent=2) if args.json else f"multi-tab conversation coordination: {report['status']} ({report['summary']['passed']} passed, {report['summary']['failed']} failed)")
    if not args.json:
        for item in results:
            print(f"- {item['status']}: {item['name']}" + (f" :: {item.get('error')}" if item.get("error") else ""))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
