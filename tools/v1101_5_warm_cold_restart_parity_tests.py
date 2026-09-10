from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-5-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import dashboard_first_use
import dashboard_startup
import first_use_runtime
import startup_coherence


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def _runtime_snapshot() -> dict[str, str]:
    from paths import DATA_DIR
    return {
        path.relative_to(DATA_DIR).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DATA_DIR.rglob("*")) if path.is_file()
    }


def test_repeated_bootstrap_has_stable_continuity_digest_and_no_writes() -> None:
    before = _runtime_snapshot()
    cold = first_use_runtime.build_first_use_bootstrap(launch_mode="cold")
    warm = first_use_runtime.build_first_use_bootstrap(launch_mode="warm")
    after = _runtime_snapshot()
    require(before == after, {"before": before, "after": after})
    require(cold["restart"]["continuity_digest"] == warm["restart"]["continuity_digest"], (cold["restart"], warm["restart"]))
    require(cold["restart"]["launch_mode"] == "cold" and warm["restart"]["launch_mode"] == "warm", "launch modes")


def test_continuity_digest_ignores_ownership_and_provider_changes() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    changed = copy.deepcopy(payload)
    changed["coordination"].update({"revision": 999, "owner_present": True, "is_owner": not bool(payload["coordination"].get("is_owner"))})
    changed["provider"].update({"status": "ready", "recovery_proven": True})
    first = startup_coherence.build_restart_continuity_snapshot(payload, launch_mode="cold")
    second = startup_coherence.build_restart_continuity_snapshot(changed, launch_mode="new_tab")
    require(first["continuity_digest"] == second["continuity_digest"], (first, second))
    parity = startup_coherence.compare_restart_continuity(first, second)
    require(parity["ok"] is True and parity["provider_change_allowed"] is True, parity)


def test_continuity_comparison_detects_draft_or_view_drift() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    changed = copy.deepcopy(payload)
    changed["draft"]["revision"] = int(changed["draft"].get("revision") or 0) + 1
    changed["presentation"]["scroll_from_bottom_px"] = int(changed["presentation"].get("scroll_from_bottom_px") or 0) + 90
    first = startup_coherence.build_restart_continuity_snapshot(payload, launch_mode="cold")
    second = startup_coherence.build_restart_continuity_snapshot(changed, launch_mode="restart")
    parity = startup_coherence.compare_restart_continuity(first, second)
    require(parity["ok"] is False and parity["status"] == "drift_detected", parity)
    require(parity["checks"]["draft_revision"] is False or parity["checks"]["scroll_from_bottom_px"] is False, parity)


def test_actual_cold_and_warm_process_restarts_preserve_continuity() -> None:
    report = dashboard_startup.measure_cold_warm_and_fresh_first_use(
        ROOT,
        timeout_seconds=35,
        include_provider_probe=False,
    )
    require(report["ok"] is True, report)
    require(report["cold_warm_continuity_parity"] is True, report)
    require(report["cold"]["cold_health_below_target"] is True, report["cold"])
    warm_seconds = float(report["warm"]["chat_input_interactive_seconds"])
    warm_target = float(report["warm"]["target_chat_interactive_seconds"])
    require(report["warm"]["chat_interactive_below_target"] is (warm_seconds < warm_target), report["warm"])
    require(report["accepted_message_replayed"] is False and report["provider_request_repeated"] is False, report)


def test_launch_context_is_visible_for_refresh_and_reopen() -> None:
    html = dashboard_first_use.render_first_use_shell()
    for token in (
        "navigationType === 'reload' ? 'refresh'",
        "localStorage.getItem(launchMarkerKey) ? 'reopen' : 'cold'",
        "continuity.v2.",
        "restored the same project, conversation, draft, and view state",
    ):
        require(token in html, token)


def test_bootstrap_route_reports_stable_digest_across_launch_modes() -> None:
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        ("/api/first-use/bootstrap?launch=cold", "/api/first-use/bootstrap?launch=refresh", "/api/first-use/bootstrap?launch=reopen"),
        timeout_seconds=40,
    )
    require(report["ok"] is True, report)
    payloads = [row["response_json"] or {} for row in report["routes"]]
    digests = [str((payload.get("restart") or {}).get("continuity_digest") or "") for payload in payloads]
    require(len(set(digests)) == 1 and bool(digests[0]), digests)
    require([payload["restart"]["launch_mode"] for payload in payloads] == ["cold", "refresh", "reopen"], payloads)


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
    value = {"suite": "v1101.5-warm-cold-restart-parity", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
