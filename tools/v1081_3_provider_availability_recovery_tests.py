from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterator

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for path in (str(AGENT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import dashboard_chat_console
import dashboard_local_model
import post_review_development_verify as isolated_verify
import release_metadata
from local_model import LocalModelConfig
from local_model_evidence import EVIDENCE_SOURCE_FIXTURE
from local_model_integration_tests import FixtureHandler, STATE, _config, _free_port
from local_model_readiness import provider_readiness
from provider_availability import (
    OFFLINE_CAPABILITIES,
    STATE_CHECKING,
    build_provider_availability_experience,
)


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def fixture_provider(scenario: str = "healthy") -> Iterator[str]:
    STATE.scenario = scenario
    STATE.request_count = 0
    STATE.requests.clear()
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def readiness(config: LocalModelConfig, *, previous_state: str | None = None) -> dict[str, object]:
    return provider_readiness(
        config=config,
        evidence_source=EVIDENCE_SOURCE_FIXTURE,
        previous_state=previous_state,
    )


def render_local_model() -> str:
    return dashboard_local_model.render_local_model_status(
        safe=lambda value: str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;"),
        card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
        layout=lambda _path, body: body,
    )


def rendered_script() -> str:
    html = render_local_model()
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "local-model page contains an unclosed script")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "local-model page contains no rendered script")
    return "\n".join(scripts)


def test_runtime_metadata_is_v1081_3_or_newer() -> None:
    version = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version >= (1081, 3), "runtime metadata predates v1081.3")
    require(release_metadata.RUNTIME_VERSION_TAG == f"v{release_metadata.RUNTIME_VERSION}", "runtime tag and version disagree")
    require("# v1081.3 Provider Availability and Recovery Experience" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1081.3 historical evidence is missing")


def test_healthy_provider_is_ready() -> None:
    with fixture_provider() as endpoint:
        report = readiness(_config("ollama", endpoint))
    availability = report["availability"]
    require(report["status"] == "ready", "healthy provider lost the established ready status")
    require(availability["state"] == "ready", f"healthy availability state is {availability['state']}")
    require(availability["generation_available"] is True, "healthy generation is not available")


def test_recovered_provider_reports_recovering_without_replay() -> None:
    with fixture_provider() as endpoint:
        report = readiness(_config("ollama", endpoint), previous_state="temporarily_unavailable")
    availability = report["availability"]
    require(availability["state"] == "recovering" and availability["recovered"] is True, "provider return was not identified")
    require(availability["automatic_generation_retry"] is False, "provider return can replay generation")
    require(availability["automatic_provider_switch"] is False, "provider return can switch providers")


def test_connection_failure_is_temporary_and_keeps_offline_tools() -> None:
    endpoint = f"http://127.0.0.1:{_free_port()}"
    report = readiness(_config("ollama", endpoint))
    availability = report["availability"]
    require(availability["state"] == "temporarily_unavailable", f"connection failure state is {availability['state']}")
    require(availability["readiness_retry_allowed"] is True, "temporary outage does not allow bounded readiness retry")
    require(set(OFFLINE_CAPABILITIES).issubset(set(availability["offline_capabilities"])), "offline tools were omitted")


def test_missing_generation_model_is_generation_unavailable() -> None:
    with fixture_provider() as endpoint:
        report = readiness(replace(_config("ollama", endpoint), model="absent-model"))
    availability = report["availability"]
    require(availability["state"] == "generation_unavailable", f"missing model state is {availability['state']}")
    require(availability["settings_review_recommended"] is True, "missing model does not recommend explicit settings review")
    require(availability["automatic_model_management"] is False, "missing model can trigger model management")


def test_invalid_configuration_is_misconfigured() -> None:
    report = readiness(LocalModelConfig(provider="unknown", endpoint="http://127.0.0.1:1", model="x", embed_model="y"))
    availability = report["availability"]
    require(availability["state"] == "misconfigured", f"invalid configuration state is {availability['state']}")
    require(availability["readiness_retry_allowed"] is False, "invalid configuration encourages blind retry")
    require(availability["settings_changed"] is False, "readiness changed settings")


def test_embedding_failure_is_degraded_not_generation_blocked() -> None:
    with fixture_provider() as endpoint:
        report = readiness(replace(_config("llama_cpp", endpoint), embed_model="absent-embed"))
    availability = report["availability"]
    require(report["status"] == "degraded", "embedding failure lost established degraded status")
    require(availability["state"] == "degraded", f"embedding failure state is {availability['state']}")
    require(availability["generation_available"] is True, "embedding failure disabled generation")
    require(availability["embedding_available"] is False, "embedding failure was reported available")


def test_checking_state_is_non_mutating() -> None:
    experience = build_provider_availability_experience({}, checking=True)
    require(experience["state"] == STATE_CHECKING, "checking state is not explicit")
    for key in ("automatic_generation_retry", "automatic_provider_switch", "automatic_model_management", "settings_changed"):
        require(experience[key] is False, f"checking can mutate through {key}")


def test_api_carries_previous_state_into_recovery_transition() -> None:
    import api_server
    import provider_recovery_evidence

    captured: dict[str, object] = {}
    original_readiness = api_server.provider_readiness
    original_dir = provider_recovery_evidence.PROVIDER_RECOVERY_DIR
    original_file = provider_recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE

    def fake_provider_readiness(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "status": "ready",
            "availability": {
                "state": "recovering",
                "automatic_provider_switch": False,
            },
        }

    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-3-provider-evidence-") as raw:
        evidence_dir = Path(raw) / "provider_recovery"
        provider_recovery_evidence.PROVIDER_RECOVERY_DIR = evidence_dir
        provider_recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE = evidence_dir / "latest_readiness.json"
        api_server.provider_readiness = fake_provider_readiness
        try:
            status, payload = api_server.handle_api_post(
                "/api/local-model/readiness",
                {"previous_state": "temporarily_unavailable"},
            )
        finally:
            api_server.provider_readiness = original_readiness
            provider_recovery_evidence.PROVIDER_RECOVERY_DIR = original_dir
            provider_recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE = original_file
    require(status == 200 and payload.get("ok") is True, "readiness API failed")
    require(captured.get("previous_state") == "temporarily_unavailable", "API discarded previous readiness state")
    availability = payload["data"]["availability"]
    require(availability["state"] == "recovering", "API lost the recovery transition")
    require(availability["automatic_provider_switch"] is False, "API recovery can switch providers")


def test_dashboard_has_bounded_single_flight_recovery_probes() -> None:
    text = (AGENT / "dashboard_local_model.py").read_text(encoding="utf-8")
    for token in (
        "recoveryProbeDelays = [5000, 10000, 20000]",
        "if (readinessRequestRunning) return null",
        "timeoutMs: 15000",
        "previous_state: lastAvailabilityState || null",
        "document.hidden || readinessRequestRunning",
    ):
        require(token in text, f"provider recovery UI omitted {token}")
    require("/api/dashboard-chat/stream" not in text, "readiness UI can replay a conversation stream")


def test_dashboard_presents_offline_capabilities_and_no_automatic_changes() -> None:
    text = (AGENT / "dashboard_local_model.py").read_text(encoding="utf-8")
    for token in (
        "Offline tools remain available",
        "Automatic provider switch",
        "Automatic generation retry",
        "No generation request, provider switch, model management, or settings mutation",
    ):
        require(token in text, f"availability presentation omitted {token}")


def test_chat_failure_copy_keeps_local_companion_surfaces_available() -> None:
    text = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("History, drafts, search, action evidence, settings, and other local tools remain available." in text, "offline chat copy hides usable local features")
    require("Nothing was switched or installed." in text, "offline chat copy lost provider neutrality")



def test_conversation_catalog_omits_provider_and_model_diagnostics() -> None:
    text = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require('{"last_provider", "last_model"}' in text, "conversation organizer does not strip provider/model diagnostics")
    require("Provider/model diagnostics stay in explicit turn disclosures" in text, "catalog privacy boundary is undocumented")

def test_rendered_local_model_javascript_syntax() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-3-js-") as raw:
        path = Path(raw) / "local-model.js"
        path.write_text(rendered_script(), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered local-model JavaScript failed: {result.stderr.strip()}")


def test_readiness_receipt_remains_redacted_and_provider_neutral() -> None:
    with fixture_provider() as endpoint:
        report = readiness(_config("ollama", endpoint))
    receipt = report.get("evidence_receipt") or {}
    require(receipt.get("native_provider_evidence") is False, "fixture readiness claimed native evidence")
    for key in (
        "contains_prompts", "contains_generated_responses", "contains_credentials",
        "contains_raw_events", "contains_request_payloads", "contains_stack_traces",
    ):
        require(receipt.get(key) is False, f"readiness receipt privacy flag {key} is not false")
    require(report["automatic_model_management"] is False, "readiness can manage models")


def test_core_profile_includes_v1081_3_and_retained_critical_paths() -> None:
    selected = {spec.name for spec in isolated_verify.select_suites("core")}
    required = {
        "v1081.3-provider-availability-recovery",
        "v1081.2-conversation-transport-recovery",
        "v1081.1-daily-use-baseline-soak",
        "v1081.0-consolidated-baseline",
        "provider-neutral-conversation",
        "conversation-runtime-critical-path",
    }
    require(required.issubset(selected), f"core profile omitted suites: {sorted(required - selected)}")


def test_current_docs_metadata_and_release_registration_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in (
        "README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        expected = release_metadata.RUNTIME_VERSION if relative == "data/settings.json" else current
        require(expected in text, f"{relative} omits {expected}")
    verify = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"provider-availability-recovery-fixtures"') == 1, "v1081.3 release stage is not registered exactly once")
    require(verify.count('"tools/v1081_3_provider_availability_recovery_tests.py"') == 1, "v1081.3 suite path is not registered exactly once")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/dashboard_chat", "data/approvals",
        "data/notifications", "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("runtime_metadata_is_v1081_3_or_newer", test_runtime_metadata_is_v1081_3_or_newer),
    ("healthy_provider_is_ready", test_healthy_provider_is_ready),
    ("recovered_provider_reports_recovering_without_replay", test_recovered_provider_reports_recovering_without_replay),
    ("connection_failure_is_temporary_and_keeps_offline_tools", test_connection_failure_is_temporary_and_keeps_offline_tools),
    ("missing_generation_model_is_generation_unavailable", test_missing_generation_model_is_generation_unavailable),
    ("invalid_configuration_is_misconfigured", test_invalid_configuration_is_misconfigured),
    ("embedding_failure_is_degraded_not_generation_blocked", test_embedding_failure_is_degraded_not_generation_blocked),
    ("checking_state_is_non_mutating", test_checking_state_is_non_mutating),
    ("api_carries_previous_state_into_recovery_transition", test_api_carries_previous_state_into_recovery_transition),
    ("dashboard_has_bounded_single_flight_recovery_probes", test_dashboard_has_bounded_single_flight_recovery_probes),
    ("dashboard_presents_offline_capabilities_and_no_automatic_changes", test_dashboard_presents_offline_capabilities_and_no_automatic_changes),
    ("chat_failure_copy_keeps_local_companion_surfaces_available", test_chat_failure_copy_keeps_local_companion_surfaces_available),
    ("conversation_catalog_omits_provider_and_model_diagnostics", test_conversation_catalog_omits_provider_and_model_diagnostics),
    ("rendered_local_model_javascript_syntax", test_rendered_local_model_javascript_syntax),
    ("readiness_receipt_remains_redacted_and_provider_neutral", test_readiness_receipt_remains_redacted_and_provider_neutral),
    ("core_profile_includes_v1081_3_and_retained_critical_paths", test_core_profile_includes_v1081_3_and_retained_critical_paths),
    ("current_docs_metadata_and_release_registration_align", test_current_docs_metadata_and_release_registration_align),
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
        "suite": "v1081.3-provider-availability-and-recovery-experience",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "native_provider_contacted": False,
        "automatic_provider_switch": False,
        "model_management_performed": False,
        "automatic_generation_replay": False,
        "runtime_state_mutated": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
