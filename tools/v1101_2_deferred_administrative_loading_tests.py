from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-2-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

import dashboard_deferred_services
import dashboard_startup
import post_review_development_verify as verify


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def test_three_bundle_suites_registered_exactly_once() -> None:
    names = [suite.name for suite in verify.SUITES]
    expected = (
        "v1101.0-cold-start-budget-truth",
        "v1101.1-lazy-dashboard-shell",
        "v1101.2-deferred-administrative-loading",
    )
    for name in expected:
        require(names.count(name) == 1, (name, names.count(name)))
    positions = tuple(names.index(name) for name in expected)
    require(positions == tuple(sorted(positions)), positions)


def test_importing_dashboard_does_not_load_administration() -> None:
    script = """
import json,sys
import dashboard
names=['release_installation','release_packaging','controlled_build_cycle','workspace_execution','patch_drafting','conversation_daily_evaluation']
print(json.dumps({name:(name in sys.modules) for name in names}))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AGENT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    require(completed.returncode == 0, completed.stderr)
    states = json.loads(completed.stdout.strip().splitlines()[-1])
    require(not any(states.values()), states)


def test_root_does_not_expand_deferred_module_graph() -> None:
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        ("/api/dashboard-deferred-health", "/", "/api/dashboard-deferred-health", "/overview", "/api/dashboard-deferred-health"),
        timeout_seconds=45,
    )
    require(report["ok"] is True, report)
    health = [row["response_json"] for row in report["routes"] if row["route"] == "/api/dashboard-deferred-health"]
    require(len(health) == 3, health)
    require(health[1]["loaded_module_count"] == health[0]["loaded_module_count"], health)
    require(health[2]["loaded_module_count"] > health[1]["loaded_module_count"], health)


def test_administrative_services_are_route_deferred() -> None:
    modules = set(dashboard_deferred_services.DEFERRED_MODULES)
    for name in (
        "release_packaging", "release_installation", "controlled_build_cycle",
        "workspace_execution", "patch_drafting", "conversation_daily_evaluation",
    ):
        require(name in modules, name)
    require(len(modules) >= 100, len(modules))


def test_existing_full_routes_remain_compatible() -> None:
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        ("/overview", "/chat-console?full=1", "/api/dashboard-chat/active-session"),
        timeout_seconds=60,
    )
    require(report["ok"] is True, report)
    require(all(row["status_code"] == 200 for row in report["routes"]), report)


def test_source_contains_no_automatic_authority_actions() -> None:
    source = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8")
    for forbidden in ("promote_release", "certify_release", "install_release", "delete_model", "download_model"):
        require(forbidden not in source, forbidden)
    require("/api/local-model/readiness" in source, "bounded readiness control missing")
    require("/api/dashboard-chat/stream" in source, "conversation route missing")


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
    value = {"suite": "v1101.2-deferred-administrative-loading", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
