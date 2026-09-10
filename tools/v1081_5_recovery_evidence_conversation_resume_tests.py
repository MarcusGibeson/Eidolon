from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for path in (str(AGENT), str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import attention_center
import dashboard
import dashboard_chat_console
import dashboard_local_model
import post_review_development_verify as isolated_verify
import provider_recovery_evidence as recovery_evidence
import release_metadata

DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


@contextmanager
def isolated_evidence_file() -> Iterator[Path]:
    original_dir = recovery_evidence.PROVIDER_RECOVERY_DIR
    original_file = recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-5-evidence-") as temp:
        directory = Path(temp) / "provider_recovery"
        recovery_evidence.PROVIDER_RECOVERY_DIR = directory
        recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE = directory / "latest_readiness.json"
        try:
            yield recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE
        finally:
            recovery_evidence.PROVIDER_RECOVERY_DIR = original_dir
            recovery_evidence.LATEST_PROVIDER_RECOVERY_FILE = original_file


def readiness_report(
    state: str,
    *,
    digest: str = DIGEST,
    checked_at: str = "2026-07-19T16:00:00Z",
    generation_available: bool | None = None,
    embedding_available: bool = True,
    previous_state: str | None = None,
) -> dict:
    if generation_available is None:
        generation_available = state in {"ready", "recovering", "degraded"}
    observed = "ready" if state == "recovering" else state
    return {
        "status": "ready" if observed == "ready" else ("degraded" if observed == "degraded" else "blocked"),
        "configuration_digest": digest,
        "availability": {
            "state": state,
            "observed_state": observed,
            "previous_state": previous_state,
            "generation_available": generation_available,
            "embedding_available": embedding_available,
        },
        "evidence_receipt": {
            "receipt_type": "provider_readiness",
            "timestamp": checked_at,
            "configuration_digest": digest,
            "contains_prompts": False,
            "contains_generated_responses": False,
            "contains_credentials": False,
        },
    }


def test_runtime_metadata_is_v1081_5() -> None:
    current = tuple(map(int, release_metadata.RUNTIME_VERSION.split(".")))
    previous = tuple(map(int, release_metadata.PREVIOUS_RUNTIME_VERSION.split(".")))
    require(current >= (1081, 5), "runtime metadata predates v1081.5")
    require((1081, 4) <= previous < current, "v1081.5 lineage missing")


def test_unavailable_check_persists_content_free_timestamp() -> None:
    with isolated_evidence_file() as path:
        record = recovery_evidence.persist_provider_recovery_evidence(
            readiness_report("temporarily_unavailable", generation_available=False),
            configured_configuration_digest=DIGEST,
            trigger="manual_check",
        )
        require(path.exists(), "latest redacted readiness evidence was not persisted")
        require(record["last_unavailable_at"] == "2026-07-19T16:00:00Z", "unavailable timestamp missing")
        require(record["settings_scope"] == "configured", "configured readiness was misclassified")
        require(record["recovery_proven"] is False, "unavailable provider was marked recovered")


def test_verified_return_requires_persisted_unavailable_state() -> None:
    unavailable = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("temporarily_unavailable", generation_available=False),
        configured_configuration_digest=DIGEST,
    )
    recovered = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready", checked_at="2026-07-19T16:01:00Z"),
        configured_configuration_digest=DIGEST,
        previous=unavailable,
    )
    require(recovered["state"] == "recovering", "verified return did not use canonical recovering state")
    require(recovered["recovered"] is True and recovered["recovery_proven"] is True, "verified return was not proven")
    require(recovered["recovered_at"] == "2026-07-19T16:01:00Z", "recovery timestamp missing")


def test_ready_without_prior_outage_is_not_falsely_called_recovered() -> None:
    ready = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready"), configured_configuration_digest=DIGEST,
    )
    require(ready["state"] == "ready", "ordinary readiness was mislabeled as a recovery transition")
    require(ready["recovered"] is False, "ordinary readiness was falsely called recovered")
    require(ready["recovery_proven"] is True, "configured ready result did not permit explicit composition")


def test_client_claimed_previous_state_cannot_forge_recovery() -> None:
    prior_ready = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready"), configured_configuration_digest=DIGEST,
    )
    forged = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("recovering", checked_at="2026-07-19T16:02:00Z", previous_state="temporarily_unavailable"),
        configured_configuration_digest=DIGEST,
        previous=prior_ready,
    )
    require(forged["state"] == "ready", "unpersisted browser previous state forged a recovery transition")
    require(forged["recovered"] is False, "client-supplied state forged recovered evidence")


def test_unsaved_editor_values_never_prove_configured_recovery() -> None:
    record = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready", digest=OTHER_DIGEST),
        configured_configuration_digest=DIGEST,
    )
    cue = recovery_evidence.provider_resume_cue(record)
    require(record["settings_scope"] == "unsaved_editor", "mismatched values were called configured")
    require(record["recovery_proven"] is False, "unsaved editor values proved configured recovery")
    require(cue["can_resume_composition"] is False, "unsaved readiness enabled configured composition")


def test_resume_cue_is_explicit_and_never_replays() -> None:
    ready = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready"), configured_configuration_digest=DIGEST,
    )
    cue = recovery_evidence.provider_resume_cue(ready)
    require(cue["can_resume_composition"] is True, "verified readiness did not enable explicit composition")
    require(cue["automatic_generation_replay"] is False, "resume cue permits generation replay")
    require(cue["automatic_resend"] is False, "resume cue permits resend")
    require(cue["new_acceptance_identity_created"] is False, "viewing the cue allocated an acceptance identity")


def test_persisted_record_is_bounded_and_private() -> None:
    record = recovery_evidence.build_provider_recovery_evidence(
        readiness_report("ready"), configured_configuration_digest=DIGEST,
    )
    forbidden_keys = {"provider", "model", "endpoint", "models", "prompt", "response", "payload", "credentials", "command_output", "conversation"}
    require(not (forbidden_keys & set(record)), f"private key leaked into recovery evidence: {sorted(forbidden_keys & set(record))}")
    for key in ("contains_provider_payloads", "contains_prompts_or_responses", "contains_credentials", "contains_raw_command_output", "contains_model_inventory", "contains_conversation_content"):
        require(record[key] is False, f"privacy flag failed: {key}")


def test_evidence_write_does_not_touch_conversation_storage() -> None:
    source = (AGENT / "provider_recovery_evidence.py").read_text(encoding="utf-8")
    require("conversation_sessions" not in source, "provider recovery evidence imports conversation storage")
    require("latest_readiness.json" in source, "bounded latest evidence file missing")
    require("uuid.uuid4().hex" in source and ".replace(LATEST_PROVIDER_RECOVERY_FILE)" in source, "atomic unique temporary write missing")


def test_post_readiness_persists_but_get_remains_read_only() -> None:
    source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    get_start = source.index('if parts == ["local-model", "readiness"]:', source.index("def handle_api_get"))
    get_end = source.index('if parts == ["local-model", "configuration"]:', get_start)
    post_start = source.index('if parts == ["local-model", "readiness"]:', source.index("def handle_api_post"))
    post_end = source.index('if parts == ["local-model", "native-smoke"]:', post_start)
    require("persist_provider_recovery_evidence" not in source[get_start:get_end], "GET readiness mutates recovery evidence")
    require(source[post_start:post_end].count("persist_provider_recovery_evidence(") == 1, "POST readiness does not persist exactly once")
    require("persisted_previous_state" in source[post_start:post_end], "POST recovery transition does not use persisted prior evidence")


def test_manual_and_visibility_checks_label_evidence_source() -> None:
    source = (AGENT / "dashboard_local_model.py").read_text(encoding="utf-8")
    require("recovery_trigger: automaticRecovery ? 'visibility_recovery' : 'manual_check'" in source, "readiness trigger is not explicit")
    require("renderRecoveryEvidence" in source, "settings surface does not render persisted evidence")


def test_restored_session_snapshot_includes_provider_resume_cue() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    snapshot_start = source.index("def dashboard_chat_session_snapshot")
    snapshot_end = source.index("def render_realtime_chat_panel", snapshot_start)
    require('"provider_recovery": provider_resume_cue()' in source[snapshot_start:snapshot_end], "restored session snapshot omits provider recovery")
    require("applyProviderRecoveryCue(snapshot.provider_recovery || null)" in source, "conversation switch does not restore provider cue")


def test_chat_resume_cue_uses_canonical_operator_controls() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("provider-recovery-resume-cue" in source, "chat recovery cue missing")
    require("Check configured provider" in source and "Open provider settings" in source, "chat cue lacks bounded handoff controls")
    require("No accepted request is replayed" in source, "chat cue omits exactly-once boundary")


def test_attention_center_uses_same_provider_resume_cue() -> None:
    source = (AGENT / "attention_center.py").read_text(encoding="utf-8")
    require("cue = provider_resume_cue()" in source, "attention center uses a separate provider vocabulary")
    require('kind="provider"' in source, "attention center lacks provider recovery item")
    require('"provider_recovery": len(provider_recovery)' in source, "attention count omits provider recovery")


def test_overview_uses_same_provider_resume_cue() -> None:
    source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    require("provider_recovery = provider_resume_cue()" in source, "overview uses no persisted provider cue")
    require("data-provider-recovery-state" in source, "overview lacks canonical provider state marker")
    require("No accepted provider request is replayed" in source, "overview omits replay boundary")


def test_rendered_javascript_syntax() -> None:
    pages = [
        dashboard_local_model.render_local_model_status(
            safe=lambda value: str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;"),
            card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
            layout=lambda _path, body: body,
            return_to_chat=True,
        ),
        dashboard_chat_console.render_realtime_chat_panel(None, compact=True),
    ]
    scripts: list[str] = []
    for html in pages:
        cursor = 0
        while True:
            start = html.find("<script>", cursor)
            if start < 0:
                break
            end = html.find("</script>", start)
            require(end >= 0, "unterminated rendered script")
            scripts.append(html[start + 8:end])
            cursor = end + 9
    require(scripts, "rendered pages contain no JavaScript")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-5-js-") as temp:
        for index, script in enumerate(scripts):
            path = Path(temp) / f"page-{index}.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run(["node", "--check", str(path)], text=True, capture_output=True, timeout=30)
            require(result.returncode == 0, result.stderr or result.stdout or "node syntax check failed")


def test_narrow_layout_resume_controls_wrap() -> None:
    css = dashboard_chat_console.COMPANION_CHAT_STYLES
    require(".provider-recovery-resume-cue .provider-recovery-actions > * { flex:1 1 100%; text-align:center; }" in css, "provider recovery controls do not wrap narrowly")


def test_core_profile_includes_v1081_5_and_retained_paths() -> None:
    selected = {spec.name for spec in isolated_verify.select_suites("core")}
    required = {"v1081.5-recovery-evidence-resume", "v1081.4-offline-companion-recovery", "v1081.3-provider-availability-recovery", "v1081.2-conversation-transport-recovery", "provider-neutral-conversation", "conversation-runtime-critical-path"}
    require(required.issubset(selected), f"core profile omitted suites: {sorted(required-selected)}")


def test_workspace_package_versions_align() -> None:
    payload = json.loads((ROOT / "data/workspaces/projects.json").read_text(encoding="utf-8"))
    require(str(payload.get("version")) == release_metadata.RUNTIME_VERSION, "workspace root version is stale")
    require(str(payload.get("root_version")) == release_metadata.RUNTIME_VERSION, "workspace root_version is stale")
    projects = [item for item in payload.get("projects", []) if isinstance(item, dict) and item.get("id") == "eidolon"]
    require(len(projects) == 1, "workspace metadata must contain exactly one Eidolon source project")
    require(str(projects[0].get("version")) == release_metadata.RUNTIME_VERSION, "workspace project version is stale")
    require(str(projects[0].get("root_version")) == release_metadata.RUNTIME_VERSION, "workspace project root_version is stale")


def test_docs_and_release_registration_align() -> None:
    current = release_metadata.RUNTIME_VERSION_TAG
    for relative in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")
    require(release_metadata.RUNTIME_VERSION in (ROOT / "data/settings.json").read_text(encoding="utf-8"), "data/settings.json omits runtime version")
    verify = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"recovery-evidence-conversation-resume-fixtures"') == 1, "release stage not registered exactly once")
    require(verify.count('"tools/v1081_5_recovery_evidence_conversation_resume_tests.py"') == 1, "suite path not registered exactly once")


def test_source_tree_is_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = ("data/provider_recovery", "data/chat_actions", "data/conversation_sessions", "data/dashboard_chat", "data/approvals", "data/notifications", "data/tasks.json", "data/memories.json", ".venv", "__pycache__")
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = tuple(
    (name[5:], value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
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
        "suite": "v1081.5-recovery-evidence-conversation-resume-hardening",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "automatic_generation_replay": False,
        "conversation_content_persisted_in_recovery_evidence": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
