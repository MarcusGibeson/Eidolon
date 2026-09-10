from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"


def _bootstrap_external_runtime() -> None:
    if os.environ.get("EIDOLON_DATA_DIR"):
        return
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1092-5-runtime-"))
    env = dict(os.environ); env["EIDOLON_DATA_DIR"] = str(runtime); env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child"], env=env, text=True, capture_output=True)
    sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)


_bootstrap_external_runtime()
sys.path[:0] = [str(AGENT), str(TOOLS)]

from paths import DATA_DIR  # noqa: E402
import conversation_sessions as sessions  # noqa: E402
import conversation_tab_coordination as tabs  # noqa: E402
import project_manager  # noqa: E402
import project_switching_continuity as continuity  # noqa: E402
import release_metadata  # noqa: E402


def require(value: object, message: str) -> None:
    if not value: raise AssertionError(message)


def _tab_id() -> str: return str(uuid.uuid4())
def _browser_id() -> str: return str(uuid.uuid4())


def _reset() -> None:
    for path in [
        DATA_DIR / "conversation_sessions", DATA_DIR / "conversation_runtime", DATA_DIR / "workspaces" / "project_switching",
        DATA_DIR / "memories.json",
    ]:
        if path.is_dir(): shutil.rmtree(path)
        elif path.exists(): path.unlink()
    other = DATA_DIR / "other-source"; other.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.write_text(json.dumps({
        "active_project_id": "eidolon", "active_project": "Eidolon", "projects": [
            {"id": "eidolon", "name": "Eidolon", "root": str(ROOT), "working_version": release_metadata.RUNTIME_VERSION, "safe_to_modify": True},
            {"id": "other", "name": "Other Project", "root": str(other), "working_version": "1.0", "safe_to_modify": False},
        ],
    }), encoding="utf-8")


def _owner() -> tuple[str, dict]:
    tab = _tab_id(); state = tabs.register_dashboard_tab(tab, _browser_id(), instance_nonce="instance-1234567890abcdef")
    require(state["is_owner"], "owner registration")
    return tab, state


def _coordinated_switch(tab: str, owner: dict, *, key: str, target: str = "other", switch_revision: int | None = None, coordination_revision: int | None = None) -> dict:
    return project_manager.activate_project(
        target,
        operator_confirmed=True,
        expected_switch_revision=continuity.project_switch_snapshot()["revision"] if switch_revision is None else switch_revision,
        switch_key=key,
        switch_source_tab_id=tab,
        switch_lease_token=str(owner.get("lease_token") or ""),
        coordination_revision=int(owner.get("revision") or 0) if coordination_revision is None else coordination_revision,
    )


def test_owner_coordinated_switch_updates_one_authoritative_revision() -> None:
    _reset(); tab, owner = _owner()
    result = _coordinated_switch(tab, owner, key="coordinated-project-switch-0001")
    require(result["ok"] and result["changed"], "coordinated switch")
    require(result["coordination"]["selected_project_id"] == "other", "selected project coordination")
    require(result["coordination"]["revision"] == owner["revision"] + 1, "coordination revision")
    require(continuity.project_switch_snapshot()["revision"] == 1, "switch revision")


def test_follower_tab_cannot_switch_project() -> None:
    _reset(); owner_tab, owner = _owner(); follower_tab = _tab_id()
    follower = tabs.register_dashboard_tab(follower_tab, _browser_id(), instance_nonce="instance-fedcba0987654321")
    require(not follower["is_owner"], "follower registration")
    before = project_manager.PROJECTS_FILE.read_bytes()
    report = project_manager.activate_project(
        "other", operator_confirmed=True, expected_switch_revision=0,
        switch_key="follower-project-switch-0001", switch_source_tab_id=follower_tab,
        switch_lease_token="", coordination_revision=follower["revision"],
    )
    require(not report["ok"] and report["status"] == "ownership_required", "follower switch accepted")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "follower rewrote registry")
    require(tabs.coordination_snapshot(tab_id=owner_tab)["is_owner"], "owner lost")


def test_stale_coordination_revision_and_stale_project_are_rejected() -> None:
    _reset(); tab, owner = _owner()
    stale = _coordinated_switch(tab, owner, key="stale-coordination-switch-0001", coordination_revision=99)
    require(not stale["ok"] and stale["status"] == "stale_revision", "stale coordination switch")
    result = _coordinated_switch(tab, owner, key="current-coordination-switch-0001")
    require(result["ok"], "current switch")
    current = tabs.coordination_snapshot(tab_id=tab)
    rejected = tabs.claim_dashboard_tab_mutation(
        tab_id=tab, lease_token=current["lease_token"], mutation_key="stale-project-session-select-0001",
        mutation_kind="select_session", project_id="eidolon", expected_revision=current["revision"],
    )
    require(not rejected["ok"] and rejected["status"] == "stale_project", "stale project tab mutation")


def test_cross_project_session_mutation_is_rejected() -> None:
    _reset(); eidolon_session = sessions.create_conversation_session("Eidolon")
    tab, owner = _owner(); result = _coordinated_switch(tab, owner, key="cross-project-switch-0001")
    require(result["ok"], "switch")
    current = tabs.coordination_snapshot(tab_id=tab)
    claim = tabs.claim_dashboard_tab_mutation(
        tab_id=tab, lease_token=current["lease_token"], mutation_key="cross-project-session-mutation-0001",
        mutation_kind="select_session", session_id=eidolon_session["id"], project_id="other",
        expected_revision=current["revision"],
    )
    require(not claim["ok"] and claim["status"] == "session_project_mismatch", "cross-project session mutation")


def test_restart_restores_exact_project_session_and_draft_without_replay() -> None:
    _reset(); eidolon = sessions.create_conversation_session("Eidolon")
    sessions.save_conversation_draft(eidolon["id"], "eidolon draft", base_revision=0, editor_id="eidolon-editor")
    tab, owner = _owner(); require(_coordinated_switch(tab, owner, key="restart-switch-0001")["ok"], "switch")
    other = sessions.get_active_conversation_session(create_if_missing=True)
    sessions.save_conversation_draft(other["id"], "other draft", base_revision=0, editor_id="other-editor")
    importlib.reload(continuity); importlib.reload(tabs)
    restored = project_manager.restore_active_project_continuity()
    require(restored["project_id"] == "other" and restored["active_session_id"] == other["id"], "restart selection")
    require(restored["has_draft"] and restored["draft_revision"] == 1, "restart draft")
    require(not restored["switch_replayed"] and not restored["accepted_turn_replayed"], "restart replay")
    require(restored["coordination"]["selected_project_id"] == "other", "restart coordination")


def test_interrupted_switch_reconciles_from_registry_without_replay() -> None:
    _reset()
    claim = continuity.claim_project_switch("eidolon", "other", expected_revision=0, switch_key="interrupted-after-write-0001")
    require(claim["ok"], "claim")
    data = project_manager.load_projects_data(); data["active_project_id"] = "other"; data["active_project"] = "Other Project"; project_manager.save_projects_data(data)
    recovered = continuity.reconcile_project_switch_state("other")
    require(recovered["restart_reconciled"] and recovered["last_switch_status"] == "completed", "after-write reconciliation")
    require(not recovered["switch_replayed"], "switch replayed")


def test_interrupted_prewrite_switch_fails_closed_without_replay() -> None:
    _reset()
    claim = continuity.claim_project_switch("eidolon", "other", expected_revision=0, switch_key="interrupted-before-write-0001")
    require(claim["ok"], "claim")
    recovered = continuity.reconcile_project_switch_state("eidolon")
    require(recovered["restart_reconciled"] and recovered["last_switch_status"] == "failed", "prewrite reconciliation")
    require(not recovered["switch_replayed"] and project_manager.get_active_project()["id"] == "eidolon", "prewrite replay")


def test_duplicate_coordinated_switch_is_not_reapplied() -> None:
    _reset(); tab, owner = _owner(); key = "duplicate-coordinated-switch-0001"
    first = _coordinated_switch(tab, owner, key=key); require(first["ok"], "first")
    before = project_manager.PROJECTS_FILE.read_bytes(); switch_revision = continuity.project_switch_snapshot()["revision"]
    second = project_manager.activate_project(
        "other", operator_confirmed=True, expected_switch_revision=0, switch_key=key,
        switch_source_tab_id=tab, switch_lease_token=first["coordination"]["lease_token"], coordination_revision=0,
    )
    require(second["ok"] and second["status"] == "already_active" and not second["changed"], "duplicate result")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "duplicate registry write")
    require(continuity.project_switch_snapshot()["revision"] == switch_revision, "duplicate switch revision")
    require(tabs.coordination_snapshot(tab_id=tab)["revision"] == 1, "duplicate coordination revision")


def test_switch_status_is_content_free_accessible_and_provider_free() -> None:
    _reset(); snapshot = continuity.project_switch_snapshot(project_id="eidolon")
    require(snapshot["controls"]["keyboard_accessible"] and snapshot["controls"]["narrow_layout_safe"], "control semantics")
    require(snapshot["controls"]["confirmation_required"] and snapshot["controls"]["stale_revision_rejected"], "authority semantics")
    require(snapshot["provider_contacted"] is False and snapshot["content_free"] is True, "provider/privacy")
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split("."))) >= tuple(map(int, "1092.5".split("."))), "version")
    require("# v1092.5 Restart and Multi-Tab Switching Hardening" in (ROOT / "README_RELEASE_HISTORY.md").read_text(), "history")
    require(not (ROOT / "data" / "projects.json").exists(), "runtime projects packaged")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--child", action="store_true"); parser.parse_args()
    checks=[]; passed=0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name":name,"status":"fail","message":f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name":name,"status":"pass","message":""})
    report={"suite":"v1092.5-restart-multi-tab-switching-hardening","ok":passed==len(TESTS),"status":"pass" if passed==len(TESTS) else "fail","passed":passed,"total":len(TESTS),"checks":checks,"external_runtime":str(DATA_DIR)}
    print(json.dumps(report,indent=2)); return 0 if report["ok"] else 1


if __name__ == "__main__": raise SystemExit(main())
