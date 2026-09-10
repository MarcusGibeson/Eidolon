from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

import dashboard_startup
import release_metadata

CORE = (
    "conversation_sessions",
    "conversation_navigation",
    "conversation_tab_coordination",
    "dashboard_chat_console",
)
PROVIDERS = ("local_model", "conversation_runtime", "brain", "chat")
ADMINS = (
    "release_installation",
    "release_packaging",
    "controlled_build_cycle",
    "workspace_execution",
    "patch_drafting",
    "conversation_daily_evaluation",
)


def require(value, message):
    if not value:
        raise AssertionError(message)


def child_env(runtime: Path) -> dict[str, str]:
    env = os.environ.copy()
    process_runtime = runtime / "process_runtime"
    metadata_locks = runtime / "metadata_locks"
    bytecode = runtime / "bytecode"
    temp_root = runtime / "tmp"
    for path in (process_runtime, metadata_locks, bytecode, temp_root):
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "EIDOLON_DATA_DIR": str(runtime),
            "EIDOLON_PROCESS_RUNTIME_ROOT": str(process_runtime),
            "EIDOLON_METADATA_LOCK_DIR": str(metadata_locks),
            "PYTHONPYCACHEPREFIX": str(bytecode),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "TMPDIR": str(temp_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(
                part for part in (str(AGENT), str(TOOLS), env.get("PYTHONPATH", "")) if part
            ),
        }
    )
    return env


def run_child(script: str, *, runtime: Path | None = None, timeout: float = 60.0) -> dict:
    owned = runtime is None
    runtime = runtime or Path(tempfile.mkdtemp(prefix="eidolon-v1091-9-"))
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=child_env(runtime),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        require(
            completed.returncode == 0,
            f"child failed: {completed.stderr[-3000:]} {completed.stdout[-1500:]}",
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])
    finally:
        if owned:
            shutil.rmtree(runtime, ignore_errors=True)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(port: int, path: str) -> tuple[int, dict]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as response:
        return int(response.code), json.loads(response.read().decode("utf-8"))


def start_server(runtime: Path):
    port = free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            str(AGENT / "main.py"),
            "--dashboard",
            "--dashboard-host",
            "127.0.0.1",
            "--dashboard-port",
            str(port),
        ],
        cwd=ROOT,
        env=child_env(runtime),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return port, process
        except OSError:
            time.sleep(0.03)
    if process.poll() is None:
        process.kill()
    stdout, stderr = process.communicate(timeout=5)
    raise AssertionError(f"server failed: {stdout[-1000:]} {stderr[-2000:]}")


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)


def test_cold_dashboard_startup_remains_below_target():
    report = dashboard_startup.build_dashboard_startup_report(
        ROOT,
        runs=3,
        route="/api/dashboard-health",
        profile_imports=False,
    )
    require(report["ok"], report)
    require(report["all_server_runs_below_target"] is True, report)
    require(report["maximum_first_response_seconds"] < 15.0, report)
    for row in report["server_runs"]:
        health = row["response_json"]
        require(health["provider_contacted"] is False, health)
        require(health["runtime_mutation_performed"] is False, health)
        require(health["conversation_startup"]["status"] == "uninitialized", health)


def test_fresh_dashboard_health_keeps_conversation_provider_and_admin_unloaded():
    payload = run_child(
        """import json,sys,dashboard
names=%r
health=dashboard.dashboard_health_payload()
print(json.dumps({'health':health,'loaded':{name:name in sys.modules for name in names}}))"""
        % (CORE + PROVIDERS + ADMINS,)
    )
    require(payload["health"]["ok"] is True, payload)
    require(not any(payload["loaded"].values()), payload)


def test_conversation_route_initializes_only_lightweight_core():
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        (
            "/api/dashboard-health",
            "/api/conversation-runtime-health",
            "/api/dashboard-chat/active-session",
            "/api/dashboard-health",
        ),
        timeout_seconds=45,
    )
    require(report["ok"], report)
    before, runtime_health, active, after = report["routes"]
    require(before["response_json"]["conversation_startup"]["status"] == "uninitialized", before)
    require(runtime_health["response_json"]["status"] == "uninitialized", runtime_health)
    require(active["response_json"]["ok"] is True, active)
    state = after["response_json"]["conversation_startup"]
    require(state["status"] in {"ready", "degraded"}, state)
    require(not state["missing_core_modules"], state)
    require(not any(state["provider_modules_loaded"].values()), state)
    require(not any(state["administrative_modules_loaded"].values()), state)


def test_session_draft_render_and_tab_fencing_are_provider_free():
    payload = run_child(
        """import json,sys
from conversation_startup_runtime import ensure_conversation_startup
ensure_conversation_startup()
from conversation_sessions import create_conversation_session, save_conversation_draft
from dashboard_chat_console import dashboard_chat_session_snapshot
from conversation_tab_coordination import register_dashboard_tab, claim_dashboard_tab_mutation
session=create_conversation_session('Checkpoint session',source='v1091.9-test')
draft=save_conversation_draft(session['id'],'checkpoint draft',editor_id='checkpoint-editor')
snapshot=dashboard_chat_session_snapshot(session['id'])
owner=register_dashboard_tab('123e4567-e89b-42d3-a456-426614174100','123e4567-e89b-42d3-a456-426614174101',instance_nonce='checkpoint-instance-0001')
claim=claim_dashboard_tab_mutation(tab_id='123e4567-e89b-42d3-a456-426614174100',lease_token=owner['lease_token'],mutation_key='v1091.9-checkpoint-claim',mutation_kind='select_session',session_id=session['id'],expected_revision=owner['revision'])
names=%r
print(json.dumps({'draft':draft,'snapshot':snapshot,'owner':owner,'claim':claim,'loaded':{name:name in sys.modules for name in names}}))"""
        % (PROVIDERS + ADMINS,)
    )
    require(payload["draft"]["content"] == "checkpoint draft", payload)
    require(payload["snapshot"]["draft"]["content"] == "checkpoint draft", payload)
    require(payload["owner"]["status"] == "ownership_acquired", payload)
    require(payload["claim"]["status"] == "pending", payload)
    require(payload["claim"]["coordination"]["status"] == "mutation_claimed", payload)
    require(not any(payload["loaded"].values()), payload)


def test_deferred_administrative_first_use_preserves_route_parity():
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        (
            "/api/dashboard-deferred-health",
            "/dashboard-route-registry-extraction",
            "/api/dashboard-deferred-health",
        ),
        timeout_seconds=45,
    )
    require(report["ok"], report)
    before, route, after = report["routes"]
    require(route["status_code"] == 200 and "Eidolon Dashboard" in route["body_prefix"], route)
    initial = before["response_json"]["modules"]["dashboard_route_registry"]
    final = after["response_json"]["modules"]["dashboard_route_registry"]
    require(initial["loaded"] is False and initial["resolved_export_count"] == 0, initial)
    require(final["loaded"] is True and final["resolved_export_count"] == 3, final)
    for name in ADMINS:
        require(after["response_json"]["modules"][name]["loaded"] is False, (name, after))


def test_required_failure_retries_and_optional_failure_degrades_safely():
    payload = run_child(
        """import json,sys
import conversation_startup_runtime as runtime
original=runtime.importlib.import_module
failed={'required':False}
def flaky(name,*args,**kwargs):
    if name=='conversation_sessions' and not failed['required']:
        failed['required']=True
        raise ModuleNotFoundError('required startup unavailable once')
    return original(name,*args,**kwargs)
runtime.importlib.import_module=flaky
first=runtime.ensure_conversation_startup()
second=runtime.ensure_conversation_startup()
runtime._reset_conversation_startup_for_tests()
def optional(name,*args,**kwargs):
    if name=='conversation_offline_durability':
        raise ModuleNotFoundError('optional startup unavailable')
    return original(name,*args,**kwargs)
runtime.importlib.import_module=optional
third=runtime.ensure_conversation_startup()
print(json.dumps({'first':first,'second':second,'third':third,'providers':{name:name in sys.modules for name in %r}}))"""
        % (PROVIDERS,)
    )
    require(payload["first"]["status"] == "failed" and payload["first"]["retry_available"], payload)
    require(payload["second"]["status"] in {"ready", "degraded"}, payload)
    require(payload["second"]["last_recovery_reason"] == "retry_after_failure", payload)
    require(payload["third"]["status"] == "degraded", payload)
    require(payload["third"]["optional_failures"][0]["module"] == "conversation_offline_durability", payload)
    require(not any(payload["providers"].values()), payload)


def test_live_owner_wait_is_bounded_without_duplicate_initialization():
    payload = run_child(
        """import json,threading,time
import conversation_startup_runtime as runtime
original=runtime.importlib.import_module
entered=threading.Event(); release=threading.Event(); calls={'conversation_sessions':0}
def slow(name,*args,**kwargs):
    if name=='conversation_sessions':
        calls[name]+=1
        entered.set()
        release.wait(timeout=2)
    return original(name,*args,**kwargs)
runtime.importlib.import_module=slow
owner=[]
def initialize_owner(): owner.append(runtime.ensure_conversation_startup(stale_seconds=.15))
thread=threading.Thread(target=initialize_owner)
thread.start(); entered.wait(timeout=1)
started=time.monotonic(); follower=runtime.ensure_conversation_startup(stale_seconds=.05); waited=time.monotonic()-started
release.set(); thread.join(timeout=2)
final=runtime.conversation_startup_status()
print(json.dumps({'owner':owner,'follower':follower,'final':final,'calls':calls,'waited':waited,'thread_alive':thread.is_alive()}))"""
    )
    require(payload["follower"]["status"] == "initializing", payload)
    require(payload["follower"]["active_owner_wait_timeouts"] == 1, payload)
    require(payload["follower"]["stale_takeovers"] == 0, payload)
    require(payload["calls"]["conversation_sessions"] == 1, payload)
    require(payload["final"]["attempts"] == 1 and payload["final"]["generation"] == 1, payload)
    require(payload["final"]["status"] in {"ready", "degraded"}, payload)
    require(payload["thread_alive"] is False, payload)
    require(0.04 <= payload["waited"] < 0.5, payload)


def test_abandoned_owner_is_reclaimed_without_turn_replay():
    payload = run_child(
        """import json,time
import conversation_startup_runtime as runtime
with runtime._CONDITION:
    runtime._STATE['status']='initializing'
    runtime._STATE['owner_thread_id']=999999999
    runtime._STATE['owner_token']='abandoned'
    runtime._STATE['started_monotonic']=time.monotonic()-20
state=runtime.ensure_conversation_startup(stale_seconds=.05)
print(json.dumps(state))"""
    )
    require(payload["status"] in {"ready", "degraded"}, payload)
    require(payload["stale_takeovers"] == 1 and payload["recoveries"] == 1, payload)
    require(payload["accepted_turn_replayed"] is False, payload)


def test_restart_restores_active_session_and_draft_without_replay():
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1091-9-restart-"))
    try:
        created = run_child(
            """import json
from conversation_sessions import create_conversation_session, save_conversation_draft
session=create_conversation_session('Checkpoint restart',source='v1091.9-test')
draft=save_conversation_draft(session['id'],'restart checkpoint draft',editor_id='restart-checkpoint')
print(json.dumps({'session':session,'draft':draft}))""",
            runtime=runtime,
        )
        port, process = start_server(runtime)
        try:
            code, active = request_json(port, "/api/dashboard-chat/active-session")
            health_code, health = request_json(port, "/api/dashboard-health")
        finally:
            stop_server(process)
        require(code == 200 and active["selected_session_id"] == created["session"]["id"], active)
        require(active["snapshot"]["draft"]["content"] == "restart checkpoint draft", active)
        state = health["conversation_startup"]
        require(health_code == 200 and state["status"] in {"ready", "degraded"}, health)
        require(state["accepted_turn_replayed"] is False, state)
        require(not any(state["provider_modules_loaded"].values()), state)
        require(not any(state["administrative_modules_loaded"].values()), state)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_release_metadata_registry_docs_and_history_are_coherent():
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1091, 9), release_metadata.RUNTIME_VERSION)
    require(tuple(int(part) for part in release_metadata.PREVIOUS_RUNTIME_VERSION.split(".")) < current, release_metadata.PREVIOUS_RUNTIME_VERSION)
    registry = (TOOLS / "post_review_development_verify.py").read_text(encoding="utf-8")
    require("v1091.9-startup-foundation-checkpoint" in registry, "checkpoint registration missing")
    from release_history import parse_release_history_file
    parsed = parse_release_history_file(ROOT / "README_RELEASE_HISTORY.md")
    require(parsed.get("ok"), parsed)
    entries = parsed.get("public_entries") or []
    versions = [tuple(int(part) for part in str(entry.get("version") or "").split(".")) for entry in entries]
    require(versions and versions[0] == current, versions[:3])
    require((1091, 9) in versions, "historical v1091.9 checkpoint missing")
    require(parsed.get("duplicate_version_count") == 0, "duplicate release-history versions")
    require(parsed.get("ordering_violation_count") == 0, "release history out of order")
    for name in ("README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        require(f"v{release_metadata.RUNTIME_VERSION}" in text, f"{name} missing current version")
        require("v1150" in text, f"{name} missing Codex schedule")


def test_source_only_runtime_privacy_contract_is_intact():
    forbidden = (
        ROOT / "data" / "projects.json",
        ROOT / "data" / "conversations",
        ROOT / "data" / "approvals",
        ROOT / "data" / "memories.json",
        ROOT / "data" / "tasks.json",
    )
    require(not any(path.exists() for path in forbidden), [str(path) for path in forbidden if path.exists()])
    generated = [path for path in ROOT.rglob("*") if path.is_file() and (path.suffix in {".pyc", ".zip"} or "__pycache__" in path.parts)]
    require(not generated, [str(path.relative_to(ROOT)) for path in generated[:20]])


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    argparse.ArgumentParser().add_argument("--json", action="store_true")
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
        "suite": "v1091.9-startup-foundation-checkpoint",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
