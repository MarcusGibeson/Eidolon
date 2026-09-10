from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-3-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import dashboard_first_use
import first_use_runtime
import release_metadata
import startup_coherence


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def test_authoritative_project_self_description_is_path_free() -> None:
    value = startup_coherence.build_active_project_self_description()
    require(value["id"] == "eidolon" and value["name"] == "Eidolon", value)
    require(value["versions"]["working_source"] == release_metadata.WORKING_SOURCE_VERSION, value["versions"])
    require(value["authority"]["working_source"] == "WORKING_SOURCE_VERSION", value["authority"])
    require(value["source_path_included"] is False, value)
    require("source_root" not in json.dumps(value).lower(), value)
    require(value["summary"].startswith("Eidolon is the active project."), value["summary"])


def test_source_unavailable_is_described_without_falsely_disabling_conversation() -> None:
    import project_manager

    original = project_manager.project_source_binding
    project_manager.project_source_binding = lambda selector="": {
        "status": "source_root_missing",
        "source_root_accessible": False,
        "source_identity_matches": False,
        "version_mismatch": False,
        "safe_to_modify": False,
        "capability_state": {
            "conversation_available": True,
            "inspection_available": False,
            "development_available": False,
            "verification_available": False,
        },
    }
    try:
        value = startup_coherence.build_active_project_self_description()
    finally:
        project_manager.project_source_binding = original
    require(value["status"] == "source_unavailable", value)
    require(value["source"]["conversation_available"] is True, value["source"])
    require(value["source"]["development_available"] is False, value["source"])
    require("Conversation is available" in value["summary"], value["summary"])


def test_current_project_capability_names_are_reflected_in_startup_truth() -> None:
    import project_manager

    original = project_manager.project_source_binding
    project_manager.project_source_binding = lambda selector="": {
        "status": "available",
        "source_root_accessible": True,
        "source_identity_matches": True,
        "version_mismatch": False,
        "safe_to_modify": True,
        "capability_state": {
            "ordinary_conversation": True,
            "source_inspection": True,
            "development": True,
            "verification": True,
        },
    }
    try:
        value = startup_coherence.build_active_project_self_description()
    finally:
        project_manager.project_source_binding = original
    require(value["source"]["conversation_available"] is True, value["source"])
    require(value["source"]["inspection_available"] is True, value["source"])
    require(value["source"]["development_available"] is True, value["source"])
    require(value["source"]["verification_available"] is True, value["source"])


def test_bootstrap_refuses_cross_project_session_restoration() -> None:
    import conversation_sessions

    original = conversation_sessions.get_active_conversation_session
    conversation_sessions.get_active_conversation_session = lambda create_if_missing=False: {
        "id": "conversation_session_wrong_project",
        "project_id": "different-project",
        "title": "Wrong project",
        "status": "active",
    }
    try:
        payload = first_use_runtime.build_first_use_bootstrap()
    finally:
        conversation_sessions.get_active_conversation_session = original
    require(payload["selected_session"]["id"] == "", payload["selected_session"])
    require(any(row["error_type"] == "ProjectSessionMismatch" for row in payload["optional_failures"]), payload)
    require(payload["recovery"]["accepted_message_replayed"] is False, payload)


def test_shell_presents_project_description_version_and_capability_truth() -> None:
    html = dashboard_first_use.render_first_use_shell()
    for token in (
        "id='project-description'",
        "id='project-meta'",
        "versions.working_source",
        "source.development_available",
        "project.truth_status",
    ):
        require(token in html, token)


def test_bootstrap_project_truth_keeps_version_roles_separate() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    project = payload["active_project"]
    require(project["status"] == "active", project)
    require(project["truth_status"] in {"ready", "source_unavailable", "source_identity_mismatch", "source_version_mismatch"}, project)
    require(project["versions"]["roles_separate"] is True, project["versions"])
    require(project["authority"]["selection"] == "persisted_project_registry", project["authority"])


def test_startup_self_description_does_not_load_administrative_services() -> None:
    script = """
import json,sys
import first_use_runtime
payload=first_use_runtime.build_first_use_bootstrap()
names=['release_installation','release_packaging','controlled_build_cycle','workspace_execution','patch_drafting','conversation_daily_evaluation']
print(json.dumps({'ok':payload.get('ok'),'loaded':{name:name in sys.modules for name in names}}))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AGENT)
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
    require(completed.returncode == 0, completed.stderr)
    value = json.loads(completed.stdout.strip().splitlines()[-1])
    require(value["ok"] is True and not any(value["loaded"].values()), value)


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
    value = {"suite": "v1101.3-active-project-self-description-repair", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
