from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"


def _bootstrap() -> None:
    if os.environ.get("EIDOLON_DATA_DIR"):
        return
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1092-9-runtime-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child"],
        env=env,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)


_bootstrap()
sys.path[:0] = [str(AGENT), str(TOOLS)]

from paths import DATA_DIR  # noqa: E402
import conversation_sessions as sessions  # noqa: E402
import dashboard_chat_console as console  # noqa: E402
import project_identity  # noqa: E402
import project_manager  # noqa: E402
import project_recovery_state as recovery  # noqa: E402
import project_root_recovery as roots  # noqa: E402
import project_switching_continuity as switching  # noqa: E402
import release_metadata  # noqa: E402
import source_project_metadata  # noqa: E402


def require(value: Any, message: str) -> None:
    if not value:
        raise AssertionError(message)


def _make_root(path: Path, version: str = "1.0") -> Path:
    (path / "conscious_agent").mkdir(parents=True, exist_ok=True)
    (path / "conscious_agent" / "release_metadata.py").write_text(
        f'RUNTIME_VERSION = "{version}"\n', encoding="utf-8"
    )
    (path / "README_NEXT_STEPS.md").write_text(
        f"# Project {version}\n", encoding="utf-8"
    )
    return path


def _clear_runtime() -> None:
    for path in (
        DATA_DIR / "conversation_sessions",
        DATA_DIR / "conversation_runtime",
        DATA_DIR / "workspaces" / "project_switching",
        DATA_DIR / "workspaces" / "project_root_recovery",
        DATA_DIR / "workspaces" / "conversation_tabs",
        DATA_DIR / "workspaces" / "projects.json",
        DATA_DIR / "workspaces" / "active_project.json",
        DATA_DIR / "memories.json",
        DATA_DIR / "projects.json",
    ):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def _write_projects(*, include_duplicates: bool = False, other_missing: bool = False) -> dict[str, Path]:
    _clear_runtime()
    other = DATA_DIR / "project-roots" / "other"
    if other.parent.exists():
        shutil.rmtree(other.parent)
    if not other_missing:
        _make_root(other)
    projects = [
        {
            "id": "eidolon",
            "name": "Eidolon",
            "root": str(ROOT),
            "working_version": release_metadata.RUNTIME_VERSION,
            "safe_to_modify": True,
            "capabilities": ["conversation", "inspection", "development", "verification"],
        },
        {
            "id": "other",
            "name": "Other Project",
            "root": str(other),
            "working_version": "1.0",
            "safe_to_modify": True,
            "source_identity_markers": ["conscious_agent/release_metadata.py", "README_NEXT_STEPS.md"],
            "source_version_file": "conscious_agent/release_metadata.py",
            "capabilities": ["conversation", "inspection"],
        },
    ]
    if include_duplicates:
        projects.extend([
            {"id": "same-a", "name": "Shared", "root": str(other), "working_version": "1.0"},
            {"id": "same-b", "name": "Shared", "root": str(other), "working_version": "1.0"},
        ])
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.write_text(
        json.dumps({"active_project_id": "eidolon", "active_project": "Eidolon", "projects": projects}, indent=2),
        encoding="utf-8",
    )
    return {"other": other}


def _switch(selector: str, *, revision: int, key: str) -> dict[str, Any]:
    return project_manager.activate_project(
        selector,
        operator_confirmed=True,
        expected_switch_revision=revision,
        switch_key=key,
    )


def _contains_value(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_value(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_value(item, needle) for item in value)
    return needle in str(value)


def test_authoritative_identity_matches_release_and_source_metadata() -> None:
    _write_projects()
    active = project_manager.active_project_identity()
    source = source_project_metadata.load_source_project_metadata(ROOT)["current_project"]
    require(active["project_id"] == source["id"] == "eidolon", "project id drift")
    require(active["project_name"] == source["name"] == "Eidolon", "project name drift")
    require(source["working_version"] == release_metadata.RUNTIME_VERSION, "working version drift")
    require(source["current_milestone"] == release_metadata.RUNTIME_MILESTONE, "milestone drift")
    require(source["next_recommended_arc"] == release_metadata.NEXT_RECOMMENDED_ARC, "next arc drift")


def test_stable_id_selection_rejects_ambiguous_names_without_mutation() -> None:
    _write_projects(include_duplicates=True)
    before = project_manager.PROJECTS_FILE.read_bytes()
    ambiguous = project_manager.preview_active_project_selection("Shared")
    require(not ambiguous["ok"] and ambiguous["status"] == "ambiguous", "ambiguous selection accepted")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "preview mutated registry")
    unconfirmed = project_manager.activate_project("other", operator_confirmed=False)
    require(unconfirmed["status"] == "confirmation_required", "confirmation boundary missing")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "unconfirmed switch mutated registry")


def test_project_sessions_drafts_and_unfinished_state_remain_isolated() -> None:
    _write_projects()
    eidolon = sessions.create_conversation_session("Eidolon work", project_id="eidolon")
    sessions.save_conversation_draft(eidolon["id"], "eidolon private draft", base_revision=0, editor_id="eidolon-editor")
    first = _switch("other", revision=0, key="checkpoint-switch-other-0001")
    require(first["ok"], "switch to other failed")
    other = sessions.create_conversation_session("Other work", project_id="other")
    sessions.save_conversation_draft(other["id"], "other private draft", base_revision=0, editor_id="other-editor")
    second = _switch("eidolon", revision=1, key="checkpoint-switch-eidolon-0001")
    require(second["ok"], "switch back failed")
    require(sessions.get_active_conversation_session(create_if_missing=False)["id"] == eidolon["id"], "eidolon session not restored")
    require(sessions.load_conversation_draft(eidolon["id"])["content"] == "eidolon private draft", "eidolon draft lost")
    require(sessions.load_conversation_draft(other["id"])["content"] == "other private draft", "other draft lost")


def test_stale_tab_state_blocks_project_mutations_and_keeps_read_only_refresh() -> None:
    _write_projects()
    switched = _switch("other", revision=0, key="checkpoint-stale-switch-0001")
    require(switched["ok"], "switch failed")
    current = switching.project_switch_snapshot()["revision"]
    state = recovery.build_project_recovery_state("other", expected_switch_revision=current - 1)
    require(state["status"] == "stale_tab", "stale tab not detected")
    require(not state["controls"]["project_mutations_enabled"], "stale mutations enabled")
    require(state["controls"]["refresh_required"], "refresh not required")
    require(state["provider_contacted"] is False, "provider contacted")


def test_missing_and_mismatched_roots_fail_closed_while_conversation_remains_available() -> None:
    roots_map = _write_projects(other_missing=True)
    switched = _switch("other", revision=0, key="checkpoint-missing-switch-0001")
    require(switched["ok"], "switch failed")
    binding = project_manager.project_source_binding("other")
    state = recovery.build_project_recovery_state("other")
    require(not binding["ok"] and not binding["safe_to_modify"], "missing root trusted")
    require(state["status"] == "source_unavailable", "missing root status")
    require(state["controls"]["conversation_enabled"], "conversation blocked")
    mismatched = _make_root(roots_map["other"], "9.9")
    preview = roots.preview_project_root_correction("other", mismatched)
    require(not preview["ok"] and preview["identity_requirements"]["version_mismatch"], "version mismatch accepted")


def test_root_correction_requires_exact_preview_and_confirmation() -> None:
    roots_map = _write_projects(other_missing=True)
    moved = _make_root(DATA_DIR / "project-roots" / "moved-other")
    preview = roots.preview_project_root_correction("other", moved)
    require(preview["ok"] and preview["operator_confirmation_required"], "safe preview missing")
    wrong = roots.confirm_project_root_correction(
        "other", moved, preview_token="0" * 64, operator_confirmed=True
    )
    require(not wrong["ok"] and not wrong["changed"], "wrong token changed root")
    unconfirmed = roots.confirm_project_root_correction(
        "other", moved, preview_token=preview["preview_token"], operator_confirmed=False
    )
    require(not unconfirmed["ok"] and not unconfirmed["changed"], "unconfirmed correction changed root")
    confirmed = roots.confirm_project_root_correction(
        "other", moved, preview_token=preview["preview_token"], operator_confirmed=True
    )
    require(confirmed["ok"] and confirmed["changed"], "confirmed correction failed")
    require(project_manager.project_source_binding("other")["ok"], "corrected root not trusted")
    require(not roots.pending_project_root_correction("other")["pending"], "preview retained")


def test_restart_state_is_content_free_and_never_replays_operations() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Restart", project_id="eidolon")
    sessions.save_conversation_draft(session["id"], "restart secret draft", base_revision=0, editor_id="restart-editor")
    restored = recovery.restore_project_recovery_state()
    require(restored["status"] == "restart_restored", "restart state")
    require(restored["active_session_id"] == session["id"] and restored["has_draft"], "restart continuity")
    require(not recovery.project_recovery_state_contains_private_fields(restored), "private field exposed")
    require(not _contains_value(restored, str(ROOT)), "absolute source path exposed")
    require(not _contains_value(restored, "restart secret draft"), "draft content exposed")
    require(not restored["accepted_turn_replayed"] and not restored["switch_replayed"] and not restored["root_correction_replayed"], "operation replay")


def test_pending_correction_invalidates_on_revision_identity_and_expiry() -> None:
    _write_projects(other_missing=True)
    moved = _make_root(DATA_DIR / "project-roots" / "pending-other")
    preview = roots.preview_project_root_correction("other", moved)
    require(preview["ok"] and roots.pending_project_root_correction("other")["pending"], "preview not pending")
    claim = switching.claim_project_switch("eidolon", "other", expected_revision=0, switch_key="checkpoint-pending-revision-0001")
    require(claim["ok"], "revision claim")
    pending = roots.pending_project_root_correction("other")
    require(not pending["valid"] and pending["status"] == "stale_revision", "revision did not invalidate")

    _write_projects(other_missing=True)
    moved = _make_root(DATA_DIR / "project-roots" / "identity-other")
    roots.preview_project_root_correction("other", moved)
    (moved / "conscious_agent" / "release_metadata.py").write_text('RUNTIME_VERSION = "2.0"\n', encoding="utf-8")
    pending = roots.pending_project_root_correction("other")
    require(not pending["valid"] and pending["status"] == "stale_identity", "identity did not invalidate")

    _write_projects(other_missing=True)
    moved = _make_root(DATA_DIR / "project-roots" / "expiry-other")
    roots.preview_project_root_correction("other", moved)
    pending = roots.pending_project_root_correction(
        "other", now_epoch=time.time() + roots.RECOVERY_PREVIEW_TTL_SECONDS + 1
    )
    require(not pending["pending"] and pending["status"] == "expired", "preview did not expire")


def test_dashboard_recovery_ux_is_separate_accessible_and_content_free() -> None:
    _write_projects()
    session = sessions.create_conversation_session("Dashboard", project_id="eidolon")
    sessions.save_conversation_draft(session["id"], "dashboard secret", base_revision=0, editor_id="dashboard-editor")
    html = console.render_realtime_chat_panel(None, compact=True)
    panel = html.split("id='chat-project-recovery'", 1)[1].split("</section>", 1)[0]
    require("Refresh project state" in panel and "Active project" in panel, "recovery panel missing")
    require(str(ROOT) not in panel and "dashboard secret" not in panel, "private panel value")
    require("project_recovery" not in console.dashboard_chat_session_snapshot(session["id"])["transcript_html"], "recovery mixed into spoken transcript")
    styles = (ROOT / "conscious_agent" / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    require(".chat-project-recovery button:focus-visible" in styles, "keyboard focus missing")
    require(".chat-project-recovery{grid-template-columns:1fr}" in styles, "narrow layout missing")


def test_release_history_is_newest_first_and_duplicate_free() -> None:
    from release_history import parse_release_history_file
    parsed = parse_release_history_file(ROOT / "README_RELEASE_HISTORY.md")
    require(parsed.get("ok"), parsed)
    entries = parsed.get("public_entries") or []
    require(entries and entries[0].get("version") == release_metadata.RUNTIME_VERSION, "current history heading")
    require(parsed.get("duplicate_version_count") == 0, "duplicate history headings")
    require(parsed.get("ordering_violation_count") == 0, "history ordering")


def test_version_registry_and_source_only_privacy_are_current() -> None:
    require(tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split(".")) >= (1092, 9), "runtime version")
    next_arc = str(release_metadata.NEXT_RECOMMENDED_ARC)
    next_match = re.match(r"v(\d+)\.(\d+)", next_arc)
    explicit_review_boundary = next_arc.startswith("Desktop Codex review of v") and " before v" in next_arc
    require((bool(next_match) and tuple(map(int, next_match.groups())) >= (1093, 0)) or explicit_review_boundary, "next arc")
    verify_source = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    require("v1092.9-active-project-recovery-checkpoint" in verify_source, "checkpoint not registered")
    require(not (ROOT / "data" / "projects.json").exists(), "runtime registry packaged")
    require(not any(path.name == "__pycache__" for path in ROOT.rglob("__pycache__")), "bytecode packaged")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as exc:
            checks.append({"name": name, "status": "fail", "message": f"{type(exc).__name__}: {exc}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1092.9-active-project-recovery-checkpoint",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
        "external_runtime": str(DATA_DIR),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
