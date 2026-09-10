from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from first_use_checkpoint import build_first_use_coherence_checkpoint, checkpoint_contains_private_fields
from first_use_runtime import build_first_use_bootstrap


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def _synthetic_bootstrap(*, external: bool = True, replayed: bool = False, optional_failure: bool = False) -> dict[str, object]:
    failure_rows = [{"service": "conversation_restoration", "error_type": "SyntheticFailure"}] if optional_failure else []
    phase_status = "degraded" if optional_failure else "ready"
    return {
        "ok": True,
        "status": "degraded" if optional_failure else "ready",
        "chat_interactive": True,
        "administrative_services_loaded": False,
        "active_project": {"truth_status": "ready", "status": "active"},
        "runtime_guidance": {"runtime_external": external, "runtime_source_local": not external},
        "progress": {"phases": [
            {"name": "chat_shell", "status": "ready"},
            {"name": "active_project_restoration", "status": "ready"},
            {"name": "conversation_restoration", "status": phase_status},
            {"name": "conversation_ownership_restoration", "status": "ready"},
            {"name": "provider_availability_restoration", "status": "pending"},
        ]},
        "provider": {"status": "unknown", "recovery_proven": False, "source": "not_checked"},
        "optional_failures": failure_rows,
        "recovery": {
            "accepted_message_replayed": replayed,
            "provider_request_repeated": False,
            "retry_is_automatic": False,
            "false_ready_state": False,
        },
        "accepted_turn_replayed": replayed,
        "provider_contacted": False,
        "runtime_mutation_performed": False,
    }


def _snapshot(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_health(port: int) -> None:
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/dashboard-health", timeout=0.5) as response:
                if json.loads(response.read().decode("utf-8")).get("service") == "eidolon-dashboard":
                    return
        except Exception:
            time.sleep(0.08)
    raise AssertionError("dashboard health timeout")


def _external_env(runtime: Path, process_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "EIDOLON_DATA_DIR": str(runtime),
        "EIDOLON_PROCESS_RUNTIME_ROOT": str(process_root / "process"),
        "EIDOLON_METADATA_LOCK_DIR": str(process_root / "locks"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(process_root / "pycache"),
        "PYTHONUNBUFFERED": "1",
    })
    return env


def test_checkpoint_report_is_content_free_non_mutating_and_non_authorizing() -> None:
    payload = build_first_use_bootstrap(launch_mode="checkpoint")
    report = payload.get("checkpoint") or {}
    require(report.get("ok") is True, report)
    require(report.get("content_free") is True and report.get("private_values_included") is False, report)
    require(checkpoint_contains_private_fields(report) is False, report)
    for key in (
        "provider_contacted", "accepted_turn_replayed", "provider_request_repeated",
        "runtime_mutation_performed", "models_changed", "automatic_retry",
        "automatic_migration", "automatic_promotion", "automatic_certification",
    ):
        require(report.get(key) is False, (key, report.get(key)))
    require(report.get("operator_authority_required") is True, report)


def test_ready_checkpoint_preserves_provider_and_windows_uncertainty() -> None:
    report = build_first_use_coherence_checkpoint(_synthetic_bootstrap())
    by_name = {row["name"]: row for row in report["checks"]}
    require(report["status"] == "ready_for_native_windows_review", report)
    require(report["current_product_defect_count"] == 0, report)
    require(by_name["provider_truth"]["status"] == "pending", by_name)
    require(by_name["native_windows_evidence"]["status"] == "pending", by_name)


def test_supplied_native_windows_evidence_is_classified_without_certifying() -> None:
    report = build_first_use_coherence_checkpoint(
        _synthetic_bootstrap(),
        native_windows_evidence={"ok": True, "native_windows": True, "native_windows_certified": False},
    )
    by_name = {row["name"]: row for row in report["checks"]}
    require(report["status"] == "ready", report)
    require(by_name["native_windows_evidence"]["status"] == "ready", by_name)
    require(report["automatic_certification"] is False and report["operator_authority_required"] is True, report)


def test_replay_contract_violation_blocks_checkpoint() -> None:
    report = build_first_use_coherence_checkpoint(_synthetic_bootstrap(replayed=True))
    by_name = {row["name"]: row for row in report["checks"]}
    require(report["ok"] is False and report["status"] == "blocked", report)
    require(by_name["replay_and_mutation_safety"]["status"] == "blocked", by_name)


def test_source_local_or_optional_failure_degrades_without_false_block() -> None:
    report = build_first_use_coherence_checkpoint(_synthetic_bootstrap(external=False, optional_failure=True))
    by_name = {row["name"]: row for row in report["checks"]}
    require(report["ok"] is True and report["status"] == "degraded", report)
    require(report["chat_remains_usable"] is True, report)
    require(by_name["source_runtime_boundary"]["status"] == "degraded", by_name)
    require(by_name["continuity_restoration"]["status"] == "degraded", by_name)


def test_dashboard_checkpoint_route_is_repeatable_and_runtime_read_only() -> None:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1101-9-route-"))
    runtime = base / "runtime"
    process_root = base / "external"
    port = _free_port()
    env = _external_env(runtime, process_root)
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "eidolon.py"), "start", "--no-browser", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_health(port)
        before = _snapshot(runtime)
        reports = []
        for _ in range(2):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/first-use/checkpoint", timeout=5) as response:
                reports.append(json.loads(response.read().decode("utf-8")))
        after = _snapshot(runtime)
        require(before == after, "checkpoint GET mutated runtime")
        require(reports[0]["status"] == reports[1]["status"], reports)
        require(reports[0]["provider_contacted"] is False, reports[0])
        require(reports[0]["accepted_turn_replayed"] is False, reports[0])
    finally:
        process.terminate()
        try:
            process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate(timeout=5)


def test_cli_and_shell_expose_one_coherent_checkpoint_surface() -> None:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1101-9-cli-"))
    env = _external_env(base / "runtime", base / "external")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "first-use-checkpoint", "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=45,
    )
    require(completed.returncode == 0, completed.stderr)
    report = json.loads(completed.stdout)
    import release_metadata
    require(report["working_source_version"] == release_metadata.WORKING_SOURCE_VERSION, report)
    require(tuple(int(part) for part in report["working_source_version"].split(".")) >= (1101, 9), report)
    shell = (AGENT / "dashboard_first_use.py").read_text(encoding="utf-8")
    dashboard = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    for token in ("First-use checkpoint", "checkpoint-state", "operator authority preserved"):
        require(token in shell, token)
    require('/api/first-use/checkpoint' in dashboard, "checkpoint route")


def test_metadata_docs_roadmap_and_focused_registration_align() -> None:
    import release_metadata
    current = tuple(int(part) for part in release_metadata.WORKING_SOURCE_VERSION.split("."))
    require(current >= (1101, 9), release_metadata.WORKING_SOURCE_VERSION)
    require(release_metadata.RUNTIME_MILESTONE.startswith(f"v{release_metadata.WORKING_SOURCE_VERSION}"), release_metadata.RUNTIME_MILESTONE)
    next_token = release_metadata.NEXT_RECOMMENDED_ARC.split()[0].removeprefix("v")
    require(tuple(int(part) for part in next_token.split(".")) >= (1102, 0), release_metadata.NEXT_RECOMMENDED_ARC)
    verifier = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    require(verifier.count('"tools/v1101_9_first_use_coherence_checkpoint_tests.py"') == 1, "checkpoint suite registration")
    roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
    require("v1101.9" in roadmap and "**Completed:**" in roadmap.split("v1101.9", 1)[1].split("v1102", 1)[0], "roadmap checkpoint status")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("## v1101.9" in history, "release history checkpoint evidence")
    for name in ("README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        require(release_metadata.WORKING_SOURCE_VERSION in text, name)


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
    report = {
        "suite": "v1101.9-first-use-coherence-checkpoint",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
