from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for path in (str(AGENT), str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import dashboard_chat_console
import dashboard_local_model
import offline_companion
import post_review_development_verify as isolated_verify
import provider_availability
import release_metadata


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_runtime_metadata_preserves_v1081_4_foundation() -> None:
    version = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(version >= (1081, 4), "runtime metadata predates v1081.4")
    require((ROOT / "conscious_agent" / "offline_companion.py").exists(), "v1081.4 offline companion foundation missing")


def test_offline_turn_contract_preserves_draft_without_synthetic_reply() -> None:
    contract = offline_companion.offline_turn_contract()
    require(contract["preserve_unsent_draft"] is True, "offline draft is not preserved")
    require(contract["synthetic_assistant_response"] is False, "offline mode permits synthetic assistant text")


def test_no_assistant_memory_without_generation() -> None:
    contract = offline_companion.offline_turn_contract()
    require(contract["assistant_memory_commit"] is False, "offline response can create assistant memory")


def test_manual_recovery_handoff_is_explicit_and_non_mutating() -> None:
    handoff = offline_companion.manual_recovery_handoff("temporarily_unavailable", readiness_persisted=False)
    require([row["id"] for row in handoff["steps"]] == ["check_provider", "open_settings", "review_diagnostics", "resume_composition"], "handoff steps drifted")
    require(handoff["steps"][-1]["enabled"] is False, "composition resumes before persisted recovery")
    for key in ("automatic_generation_replay", "automatic_resend", "automatic_provider_switch", "automatic_model_selection", "settings_saved"):
        require(handoff[key] is False, f"handoff mutates boundary: {key}")


def test_persisted_recovery_enables_composition_not_replay() -> None:
    handoff = offline_companion.manual_recovery_handoff("recovering", readiness_persisted=True)
    require(handoff["recovery_proven"] is True and handoff["steps"][-1]["enabled"] is True, "persisted recovery does not restore composition")
    require(handoff["automatic_generation_replay"] is False, "recovery replays generation")


def test_explicit_resend_requires_persisted_non_acceptance() -> None:
    require(offline_companion.resend_policy(accepted=False, persisted_not_accepted=True)["explicit_resend_allowed"] is True, "proven unaccepted turn cannot be resent")
    require(offline_companion.resend_policy(accepted=True, persisted_not_accepted=True)["explicit_resend_allowed"] is False, "accepted turn can be resent")
    require(offline_companion.resend_policy(accepted=False, persisted_not_accepted=False)["explicit_resend_allowed"] is False, "uncertain turn can be resent")


def test_resend_uses_new_identity_only_when_allowed() -> None:
    allowed = offline_companion.resend_policy(accepted=False, persisted_not_accepted=True)
    blocked = offline_companion.resend_policy(accepted=True, persisted_not_accepted=False)
    require(allowed["new_acceptance_identity_required"] is True, "explicit resend does not require a new identity")
    require(blocked["new_acceptance_identity_required"] is False, "blocked resend allocates a new identity")


def test_generation_only_failure_keeps_local_and_embedding_surfaces() -> None:
    matrix = offline_companion.dependency_boundaries(generation_available=False, embedding_available=True)
    require(all(matrix["local_surfaces"].values()), "generation outage disabled local surfaces")
    require(matrix["provider_surfaces"]["provider_backed_conversation"] is False, "generation remained enabled")
    require(matrix["provider_surfaces"]["semantic_memory_retrieval"] is True, "embedding surface was disabled")


def test_embedding_only_failure_keeps_generation() -> None:
    matrix = offline_companion.dependency_boundaries(generation_available=True, embedding_available=False)
    require(matrix["provider_surfaces"]["provider_backed_conversation"] is True, "embedding outage disabled generation")
    require(matrix["provider_surfaces"]["semantic_memory_retrieval"] is False, "embedding surface remained enabled")


def test_both_provider_capabilities_unavailable_do_not_disable_local_features() -> None:
    matrix = offline_companion.dependency_boundaries(generation_available=False, embedding_available=False)
    require(all(matrix["local_surfaces"].values()), "combined outage disabled local features")
    require(matrix["unrelated_local_features_disabled"] is False, "global disable flag was set")


def test_invalid_configuration_is_dependency_specific() -> None:
    matrix = offline_companion.dependency_boundaries(generation_available=True, embedding_available=True, configuration_valid=False)
    require(not any(matrix["provider_surfaces"].values()), "invalid configuration left provider surfaces enabled")
    require(all(matrix["local_surfaces"].values()), "invalid configuration disabled local surfaces")


def test_canonical_state_vocabulary_is_complete() -> None:
    expected = {"checking", "ready", "recovering", "temporarily_unavailable", "misconfigured", "degraded", "generation_unavailable"}
    require(expected == set(offline_companion.CANONICAL_STATE_COPY), "canonical state vocabulary drifted")


def test_provider_availability_uses_canonical_copy_and_boundaries() -> None:
    report = {"status": "degraded", "generation_service_available": True, "generation_model_available": True, "embedding_service_available": False, "embedding_model_available": False, "issues": [{"service": "embedding", "classification": "connection_failure"}], "evidence_receipt": {"redacted": True}}
    experience = provider_availability.build_provider_availability_experience(report)
    require((experience["label"], experience["detail"]) == offline_companion.canonical_copy("degraded"), "provider availability copy is not canonical")
    require(experience["dependency_boundaries"]["provider_surfaces"]["provider_backed_conversation"] is True, "degraded state blocked generation")


def test_chat_has_manual_readiness_and_settings_handoff() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("Check configured provider" in source, "chat lacks manual readiness handoff")
    require("run_readiness=1" in source, "chat readiness handoff cannot trigger a bounded check")
    require("Open provider settings" in source, "chat lacks settings handoff")


def test_local_model_handoff_runs_only_bounded_readiness() -> None:
    source = (AGENT / "dashboard_local_model.py").read_text(encoding="utf-8")
    require("query.get('run_readiness') === '1'" in source, "settings page does not honor readiness handoff")
    require("runReadiness(false)" in source, "readiness handoff does not use the bounded readiness path")


def test_multi_tab_readiness_remains_single_flight() -> None:
    source = (AGENT / "dashboard_local_model.py").read_text(encoding="utf-8")
    require("if (readinessRequestRunning) return null" in source, "readiness request is not single flight")
    require("document.hidden || readinessRequestRunning" in source, "visibility-aware recovery guard missing")


def test_no_automatic_replay_tokens_in_recovery_contract() -> None:
    source = (AGENT / "offline_companion.py").read_text(encoding="utf-8")
    require('"automatic_generation_replay": False' in source, "replay boundary missing")
    require('"automatic_resend": False' in source, "automatic resend boundary missing")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_local_model.render_local_model_status(
        safe=lambda value: str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;"),
        card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
        layout=lambda _path, body: body,
        return_to_chat=True,
    )
    scripts = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0: break
        end = html.find("</script>", start)
        require(end >= 0, "unterminated script")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "rendered local-model page has no script")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-4-js-") as temp:
        path = Path(temp) / "page.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        result = subprocess.run(["node", "--check", str(path)], text=True, capture_output=True, timeout=30)
        require(result.returncode == 0, result.stderr or result.stdout or "node syntax check failed")


def test_narrow_layout_recovery_controls_wrap() -> None:
    css = dashboard_chat_console.COMPANION_CHAT_STYLES
    require(
        ".chat-recovery-actions > *" in css and "flex:1 1 100%; text-align:center;" in css,
        "narrow recovery actions do not wrap",
    )


def test_privacy_contract_is_bounded_and_content_free() -> None:
    contract = offline_companion.offline_turn_contract()
    for key in ("provider_payload_persisted", "raw_prompt_or_response_persisted", "private_receipt_in_conversation_history"):
        require(contract[key] is False, f"privacy boundary failed: {key}")


def test_core_profile_includes_v1081_4_and_retained_critical_paths() -> None:
    selected = {spec.name for spec in isolated_verify.select_suites("core")}
    required = {"v1081.4-offline-companion-recovery", "v1081.3-provider-availability-recovery", "v1081.2-conversation-transport-recovery", "provider-neutral-conversation", "conversation-runtime-critical-path"}
    require(required.issubset(selected), f"core profile omitted suites: {sorted(required-selected)}")


def test_docs_and_release_registration_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")
    require(release_metadata.RUNTIME_VERSION in (ROOT / "data/settings.json").read_text(encoding="utf-8"), "data/settings.json omits runtime version")
    verify = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"offline-companion-provider-recovery-fixtures"') == 1, "release stage not registered exactly once")
    require(verify.count('"tools/v1081_4_offline_companion_recovery_tests.py"') == 1, "suite path not registered exactly once")


def test_source_tree_is_immutable_during_suite_and_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = ("data/chat_actions", "data/conversation_sessions", "data/dashboard_chat", "data/approvals", "data/notifications", "data/tasks.json", "data/memories.json", ".venv", "__pycache__")
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = tuple((name[5:], value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks=[]; passed=0
    for name, test in TESTS:
        try: test()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1081.4-offline-companion-provider-recovery-consolidation","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks,"native_provider_contacted":False,"model_management_performed":False,"automatic_generation_replay":False,"runtime_state_mutated":False,"release_authorized":False}
    print(json.dumps(report, indent=2)); return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
