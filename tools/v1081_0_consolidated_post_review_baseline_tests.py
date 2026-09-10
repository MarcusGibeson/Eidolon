from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for path in (AGENT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import dashboard_chat_console
import post_review_development_verify as isolated_verify
import release_metadata


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def rendered_panel() -> str:
    return dashboard_chat_console.render_realtime_chat_panel(None, compact=True)


def _write_fixture_source(root: Path, body: str) -> None:
    tools = root / "tools"
    data = root / "data"
    tools.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    (data / "settings.json").write_text('{"settings_version":"fixture"}\n', encoding="utf-8")
    (tools / "isolated_suite_worker.py").write_text(
        (TOOLS / "isolated_suite_worker.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tools / "fixture_suite.py").write_text(body, encoding="utf-8")


def test_runtime_metadata_is_v1081_0() -> None:
    current_parts = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current_parts >= (1081, 0), "runtime metadata predates the v1081.0 consolidated foundation")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag drifted from the current version")
    require("v1081.0" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1081.0 historical milestone disappeared")


def test_dashboard_contract_uses_release_metadata() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    html = rendered_panel()
    expected = f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-{release_metadata.RUNTIME_UI_CONTRACT}'"
    require(expected in html, "rendered chat contract is not aligned to release metadata")
    require("from release_metadata import RUNTIME_UI_CONTRACT, RUNTIME_VERSION_TAG" in source, "dashboard does not import the centralized UI contract")
    require("v1080.9-desktop-alpha-usability-consolidation" not in source, "dashboard retains a hardcoded historical current-version contract")


def test_v1080_9_currentness_fixture_is_forward_compatible() -> None:
    source = (TOOLS / "v1080_9_desktop_alpha_usability_consolidation_tests.py").read_text(encoding="utf-8")
    require('RUNTIME_VERSION == "1080.9"' not in source, "v1080.9 fixture still freezes the runtime at an historical version")
    require("current_parts >= (1080, 9)" in source, "v1080.9 fixture does not preserve a minimum-version assertion")
    require("v1080.9 historical milestone disappeared" in source, "v1080.9 historical evidence assertion disappeared")


def test_isolated_suite_registry_is_unique_and_complete() -> None:
    names = [spec.name for spec in isolated_verify.SUITES]
    require(len(names) == len(set(names)), "isolated verifier contains duplicate suite names")
    required = {
        "v1081.0-consolidated-baseline",
        "v1080.9-usability",
        "v1080.2-control-portal",
        "mood-important-moment-continuity",
        "provider-neutral-conversation",
        "conversation-runtime-critical-path",
    }
    require(required.issubset(set(names)), "isolated verifier omits a required retained suite")


def test_core_profile_is_bounded_and_high_value() -> None:
    names = [spec.name for spec in isolated_verify.SUITES]
    anchor = names.index("v1081.0-consolidated-baseline")
    selected = {spec.name for spec in isolated_verify.SUITES[anchor:] if "core" in spec.profiles}
    required = {
        "v1081.0-consolidated-baseline",
        "provider-neutral-conversation",
        "conversation-runtime-critical-path",
    }
    require(required.issubset(selected), "core profile dropped a required v1081.0 foundation")
    require(len(selected) == 3, "historical v1081.0 core profile drifted")


def test_successful_suite_runs_from_disposable_copy() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-success-") as raw:
        source = Path(raw) / "source"
        _write_fixture_source(
            source,
            "import json, os\nfrom pathlib import Path\nPath(os.environ['EIDOLON_DATA_DIR']).mkdir(parents=True, exist_ok=True)\nPath(os.environ['EIDOLON_DATA_DIR'],'runtime.txt').write_text('ok')\nprint(json.dumps({'ok': True, 'passed': 1, 'total': 1}))\n",
        )
        before = isolated_verify.source_snapshot(source)
        result = isolated_verify.run_suite(
            isolated_verify.SuiteSpec("fixture-success", "tools/fixture_suite.py", arguments=(), timeout_seconds=10),
            source_root=source,
        )
        require(result["ok"] is True, f"isolated success fixture failed: {result}")
        require(result["source_tree_unchanged"] is True, "successful fixture changed its disposable source copy")
        require(before == isolated_verify.source_snapshot(source), "successful fixture changed the caller's source tree")
        require(not (source / "data" / "runtime.txt").exists(), "runtime data escaped into the caller's source tree")


def test_destructive_suite_is_contained_and_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-destructive-") as raw:
        source = Path(raw) / "source"
        _write_fixture_source(
            source,
            "import json\nfrom pathlib import Path\nPath('source-corruption.txt').write_text('bad')\nprint(json.dumps({'ok': True, 'passed': 1, 'total': 1}))\n",
        )
        before = isolated_verify.source_snapshot(source)
        result = isolated_verify.run_suite(
            isolated_verify.SuiteSpec("fixture-destructive", "tools/fixture_suite.py", arguments=(), timeout_seconds=10),
            source_root=source,
        )
        require(result["ok"] is False, "destructive fixture was accepted")
        require(result["source_tree_unchanged"] is False, "destructive fixture mutation was not detected")
        require("source-corruption.txt" in result["source_changes"]["added"], "destructive addition was not reported")
        require(before == isolated_verify.source_snapshot(source), "destructive fixture escaped its disposable source copy")


def test_timeout_is_bounded_and_reported() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-timeout-") as raw:
        source = Path(raw) / "source"
        _write_fixture_source(source, "import time\ntime.sleep(30)\n")
        started = time.perf_counter()
        result = isolated_verify.run_suite(
            isolated_verify.SuiteSpec("fixture-timeout", "tools/fixture_suite.py", arguments=(), timeout_seconds=1),
            source_root=source,
        )
        elapsed = time.perf_counter() - started
        require(result["ok"] is False and result["timed_out"] is True, "timeout fixture was not classified correctly")
        require(elapsed < 12, f"timeout fixture exceeded its bounded cleanup window: {elapsed:.2f}s")


def test_file_backed_worker_handoff_is_explicit() -> None:
    verifier = (TOOLS / "post_review_development_verify.py").read_text(encoding="utf-8")
    worker = (TOOLS / "isolated_suite_worker.py").read_text(encoding="utf-8")
    require("worker-result.json" in verifier, "verifier does not use a file-backed completion handoff")
    require("stdout=subprocess.DEVNULL" in verifier and "stderr=subprocess.DEVNULL" in verifier, "worker orchestration still depends on inherited output pipes")
    require("taskkill" in verifier and "os.killpg" in verifier, "cross-platform process-tree cleanup is missing")
    require("Keep the root PID alive" in worker, "worker does not preserve a killable process-tree root after suite completion")


def test_trailing_json_parser_preserves_valid_report() -> None:
    payload, error = isolated_verify.parse_json_report("human log\n{\"ok\":true,\"passed\":2,\"total\":2}\n")
    require(error is None, f"valid trailing JSON was rejected: {error}")
    require(payload.get("ok") is True and payload.get("passed") == 2, "trailing JSON report was parsed incorrectly")
    legacy = {"status": "pass", "passed": 16, "total": 16}
    require(isolated_verify.report_functional_ok(legacy), "established status/pass report shape is not accepted")
    require(not isolated_verify.report_functional_ok({"status": "pass", "passed": 15, "total": 16}), "mismatched legacy counts were accepted")
    shaped = {"ok": True, "checks": [{"status": "pass"}, {"status": "pass"}], "summary": {"passed": 2, "failed": 0}}
    require(isolated_verify.report_counts(shaped) == (2, 2), "check-list report counts were not normalized")


def test_list_command_is_machine_readable() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOLS / "post_review_development_verify.py"), "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    require(result.returncode == 0, f"isolated verifier list command failed: {result.stderr}")
    payload = json.loads(result.stdout)
    require(len(payload.get("suites") or []) == len(isolated_verify.SUITES), "list command omitted registered suites")


def test_release_verify_registers_v1081_once() -> None:
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count('"consolidated-post-review-development-baseline-fixtures"') == 1, "v1081.0 release stage is not registered exactly once")
    require(source.count('"tools/v1081_0_consolidated_post_review_baseline_tests.py"') == 1, "v1081.0 suite path is not registered exactly once")


def test_current_documents_and_workspace_metadata_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in (
        "README.md",
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
    ):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")


def test_rendered_javascript_syntax() -> None:
    html = rendered_panel()
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag is unclosed")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "rendered panel contains no JavaScript")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-js-") as raw:
        script = Path(raw) / "rendered.js"
        script.write_text("\n".join(scripts), encoding="utf-8")
        result = subprocess.run(["node", "--check", str(script)], capture_output=True, text=True, timeout=30)
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/approvals", "data/notifications",
        "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("runtime_metadata_is_v1081_0", test_runtime_metadata_is_v1081_0),
    ("dashboard_contract_uses_release_metadata", test_dashboard_contract_uses_release_metadata),
    ("v1080_9_currentness_fixture_is_forward_compatible", test_v1080_9_currentness_fixture_is_forward_compatible),
    ("isolated_suite_registry_is_unique_and_complete", test_isolated_suite_registry_is_unique_and_complete),
    ("core_profile_is_bounded_and_high_value", test_core_profile_is_bounded_and_high_value),
    ("successful_suite_runs_from_disposable_copy", test_successful_suite_runs_from_disposable_copy),
    ("destructive_suite_is_contained_and_rejected", test_destructive_suite_is_contained_and_rejected),
    ("timeout_is_bounded_and_reported", test_timeout_is_bounded_and_reported),
    ("file_backed_worker_handoff_is_explicit", test_file_backed_worker_handoff_is_explicit),
    ("trailing_json_parser_preserves_valid_report", test_trailing_json_parser_preserves_valid_report),
    ("list_command_is_machine_readable", test_list_command_is_machine_readable),
    ("release_verify_registers_v1081_once", test_release_verify_registers_v1081_once),
    ("current_documents_and_workspace_metadata_align", test_current_documents_and_workspace_metadata_align),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("source_tree_remains_source_only", test_source_tree_remains_source_only),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, test in TESTS:
        try:
            test()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1081.0-consolidated-post-review-development-baseline",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "runtime_state_mutated": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
