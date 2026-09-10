from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-4-runtime-")

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


def test_progress_reports_every_first_use_phase_without_false_ready() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    progress = payload["progress"]
    names = [row["name"] for row in progress["phases"]]
    require(tuple(names) == startup_coherence.STARTUP_PHASE_ORDER, names)
    require(progress["total_phase_count"] == 5 and progress["completed_phase_count"] >= 4, progress)
    provider_row = next(row for row in progress["phases"] if row["name"] == "provider_availability_restoration")
    require(provider_row["status"] in {"ready", "pending", "degraded"}, provider_row)
    require(progress["retry"]["automatic_retry"] is False, progress["retry"])
    require(payload["recovery"]["false_ready_state"] is False, payload["recovery"])


def test_retry_scope_and_attempt_are_strictly_bounded() -> None:
    require(startup_coherence.normalize_retry_services("active_project,conversation_restoration") == ("active_project", "conversation_restoration"), "scope")
    require(startup_coherence.normalize_retry_attempt(3) == 3, "attempt")
    for call in (
        lambda: startup_coherence.normalize_retry_services("release_packaging"),
        lambda: startup_coherence.normalize_retry_attempt(4),
        lambda: startup_coherence.normalize_retry_attempt(-1),
    ):
        try:
            call()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid retry request was accepted")


def test_failed_optional_service_is_retryable_without_replay() -> None:
    original = first_use_runtime.build_active_project_self_description
    first_use_runtime.build_active_project_self_description = lambda: {
        "ok": False, "status": "description_unavailable", "id": "", "name": "Unavailable",
        "description": "", "summary": "", "source": {}, "versions": {}, "authority": {},
        "source_path_included": False, "content_free": True, "error_type": "FixtureFailure",
    }
    try:
        payload = first_use_runtime.build_first_use_bootstrap(retry_services="active_project", retry_attempt=1)
    finally:
        first_use_runtime.build_active_project_self_description = original
    row = next(item for item in payload["progress"]["phases"] if item["name"] == "active_project_restoration")
    require(payload["status"] == "degraded" and row["status"] == "degraded", payload)
    require(row["retry_available"] is True and row["retry_service"] == "active_project", row)
    require(payload["progress"]["retry"]["attempt"] == 1, payload["progress"])
    require(payload["accepted_turn_replayed"] is False and payload["provider_contacted"] is False, payload)


def test_retry_limit_disables_further_optional_retry() -> None:
    original = first_use_runtime.build_active_project_self_description
    first_use_runtime.build_active_project_self_description = lambda: {
        "ok": False, "status": "description_unavailable", "id": "", "name": "Unavailable",
        "description": "", "summary": "", "source": {}, "versions": {}, "authority": {},
        "source_path_included": False, "content_free": True, "error_type": "FixtureFailure",
    }
    try:
        payload = first_use_runtime.build_first_use_bootstrap(retry_services="active_project", retry_attempt=3)
    finally:
        first_use_runtime.build_active_project_self_description = original
    row = next(item for item in payload["progress"]["phases"] if item["name"] == "active_project_restoration")
    require(row["retry_available"] is False, row)
    require(payload["progress"]["retry"]["remaining_attempts"] == 0, payload["progress"])


def test_retry_bootstrap_is_read_only() -> None:
    before = _runtime_snapshot()
    payload = first_use_runtime.build_first_use_bootstrap(retry_services="active_project,conversation_restoration", retry_attempt=1)
    after = _runtime_snapshot()
    require(before == after, {"before": before, "after": after})
    require(payload["runtime_mutation_performed"] is False, payload)
    require(payload["recovery"]["provider_request_repeated"] is False, payload)


def test_route_and_shell_expose_bounded_failure_recovery() -> None:
    report = dashboard_startup.probe_dashboard_routes(
        ROOT,
        ("/api/first-use/bootstrap?retry=release_packaging&attempt=1",),
        timeout_seconds=35,
    )
    row = report["routes"][0]
    require(row["status_code"] == 400, row)
    require((row["response_json"] or {}).get("status") == "invalid_retry_request", row)
    html = dashboard_first_use.render_first_use_shell()
    for token in ("retryMaximum = 3", "Retry failed startup services", "No accepted work is replayed", "automatic retry"):
        require(token.lower() in html.lower(), token)


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
    value = {"suite": "v1101.4-startup-progress-failure-recovery", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
