from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"


def _bootstrap_external_runtime() -> None:
    if os.environ.get("EIDOLON_DATA_DIR"):
        return
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1092-4-runtime-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child"], env=env, text=True, capture_output=True)
    sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)


_bootstrap_external_runtime()
sys.path[:0] = [str(AGENT), str(TOOLS)]

from paths import DATA_DIR  # noqa: E402
import conversation_sessions as sessions  # noqa: E402
import project_manager  # noqa: E402
import project_root_recovery as recovery  # noqa: E402
import release_metadata  # noqa: E402
import workspace_orchestration as workspace  # noqa: E402


def require(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def _make_root(path: Path, *, project_id: str = "other", version: str = "1.0") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "PROJECT_ID").write_text(project_id + "\n", encoding="utf-8")
    (path / "VERSION.txt").write_text(f"VERSION={version}\n", encoding="utf-8")
    (path / "README.md").write_text(f"# {project_id}\n", encoding="utf-8")
    return path


def _write_registries(tmp: Path, *, current_root: Path, duplicate_name: bool = False) -> None:
    project = {
        "id": "other", "name": "Other Project", "root": str(current_root), "working_version": "1.0",
        "source_identity_markers": ["PROJECT_ID", "README.md"],
        "source_version_file": "VERSION.txt", "source_version_pattern": r"VERSION=([0-9.]+)",
        "readme_path": "README.md", "safe_to_modify": True,
    }
    rows = [
        {"id": "eidolon", "name": "Eidolon", "root": str(ROOT), "working_version": release_metadata.RUNTIME_VERSION, "safe_to_modify": True},
        project,
    ]
    if duplicate_name:
        rows.append({**project, "id": "other-2", "root": str(tmp / "other-2")})
    project_manager.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    project_manager.PROJECTS_FILE.write_text(json.dumps({"active_project_id": "other", "active_project": "Other Project", "projects": rows}), encoding="utf-8")
    workspace.PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    workspace.PROJECTS_FILE.write_text(json.dumps({"projects": rows}), encoding="utf-8")
    workspace.ACTIVE_PROJECT_FILE.write_text(json.dumps({"active_project_id": "other"}), encoding="utf-8")


def test_missing_root_blocks_source_work_but_preserves_sessions_and_drafts() -> None:
    tmp = DATA_DIR / "case-missing"; missing = tmp / "gone"
    _write_registries(tmp, current_root=missing)
    session = sessions.create_conversation_session("Unavailable source", project_id="other")
    sessions.save_conversation_draft(session["id"], "private draft survives", base_revision=0, editor_id="recovery-editor")
    binding = project_manager.project_source_binding("other")
    require(not binding["ok"] and binding["status"] == "missing", "missing root not detected")
    active = sessions.get_active_conversation_session(create_if_missing=False)
    require(active and active["id"] == session["id"], "session unavailable")
    require(sessions.load_conversation_draft(session["id"])["content"] == "private draft survives", "draft lost")


def test_valid_moved_root_preview_is_read_only_and_identity_bound() -> None:
    tmp = DATA_DIR / "case-preview"; old = tmp / "missing"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=old)
    before_runtime = project_manager.PROJECTS_FILE.read_bytes(); before_workspace = workspace.PROJECTS_FILE.read_bytes()
    report = recovery.preview_project_root_correction("other", moved)
    require(report["ok"] and report["status"] == "ready", "valid preview")
    require(report["identity_requirements"]["observed_version"] == "1.0", "version not observed")
    require(report["operator_confirmation_required"] is True and len(report["preview_token"]) == 64, "preview contract")
    require(project_manager.PROJECTS_FILE.read_bytes() == before_runtime, "preview rewrote runtime")
    require(workspace.PROJECTS_FILE.read_bytes() == before_workspace, "preview rewrote workspace")


def test_unconfirmed_and_stale_preview_cannot_write() -> None:
    tmp = DATA_DIR / "case-stale"; old = tmp / "missing"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=old)
    preview = recovery.preview_project_root_correction("other", moved)
    before = project_manager.PROJECTS_FILE.read_bytes()
    unconfirmed = recovery.confirm_project_root_correction("other", moved, preview_token=preview["preview_token"], operator_confirmed=False)
    require(not unconfirmed["ok"] and unconfirmed["status"] == "confirmation_required", "unconfirmed write")
    stale = recovery.confirm_project_root_correction("other", moved, preview_token="0" * 64, operator_confirmed=True)
    require(not stale["ok"] and stale["status"] == "stale_preview", "stale preview write")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "blocked correction rewrote runtime")


def test_confirmed_correction_updates_aligned_registries_with_backups() -> None:
    tmp = DATA_DIR / "case-confirm"; old = tmp / "missing"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=old)
    preview = project_manager.preview_project_source_root_update("other", str(moved))
    result = project_manager.confirm_project_source_root_update(
        "other", str(moved), preview_token=preview["preview_token"], operator_confirmed=True,
    )
    require(result["ok"] and result["changed"], "confirmed correction")
    require(result["runtime_registry_rewritten"] and result["workspace_registry_rewritten"], "aligned registries")
    require(len(result["backup_paths"]) == 2 and all(Path(path).is_file() for path in result["backup_paths"]), "backups")
    runtime = json.loads(project_manager.PROJECTS_FILE.read_text())
    workspace_data = json.loads(workspace.PROJECTS_FILE.read_text())
    runtime_project = next(row for row in runtime["projects"] if row["id"] == "other")
    workspace_project = next(row for row in workspace_data["projects"] if row["id"] == "other")
    require(Path(runtime_project["source_root"]) == moved.resolve(), "runtime root")
    require(Path(workspace_project["source_root"]) == moved.resolve(), "workspace root")
    require(project_manager.project_source_binding("other")["ok"], "corrected root not usable")


def test_marker_and_version_mismatches_are_blocked() -> None:
    tmp = DATA_DIR / "case-mismatch"; old = tmp / "missing"
    missing_marker = tmp / "marker-missing"; missing_marker.mkdir(parents=True); (missing_marker / "VERSION.txt").write_text("VERSION=1.0\n"); (missing_marker / "README.md").write_text("x")
    _write_registries(tmp, current_root=old)
    marker_report = recovery.preview_project_root_correction("other", missing_marker)
    require(not marker_report["ok"] and "PROJECT_ID" in marker_report["identity_requirements"]["missing_markers"], "marker mismatch accepted")
    wrong_version = _make_root(tmp / "wrong-version", version="2.0")
    version_report = recovery.preview_project_root_correction("other", wrong_version)
    require(not version_report["ok"] and version_report["identity_requirements"]["version_mismatch"], "version mismatch accepted")


def test_registry_mismatch_blocks_both_writes() -> None:
    tmp = DATA_DIR / "case-registry-mismatch"; old = tmp / "missing"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=old)
    workspace.PROJECTS_FILE.write_text(json.dumps({"projects": [{"id": "eidolon", "name": "Eidolon", "root": str(ROOT)}]}), encoding="utf-8")
    preview = recovery.preview_project_root_correction("other", moved)
    before_runtime = project_manager.PROJECTS_FILE.read_bytes(); before_workspace = workspace.PROJECTS_FILE.read_bytes()
    report = recovery.confirm_project_root_correction("other", moved, preview_token=preview["preview_token"], operator_confirmed=True)
    require(not report["ok"] and report["status"] == "registry_mismatch", "registry mismatch not blocked")
    require(project_manager.PROJECTS_FILE.read_bytes() == before_runtime and workspace.PROJECTS_FILE.read_bytes() == before_workspace, "partial write")


def test_ambiguous_name_is_rejected_without_guessing() -> None:
    tmp = DATA_DIR / "case-ambiguous"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=tmp / "missing", duplicate_name=True)
    before = project_manager.PROJECTS_FILE.read_bytes()
    report = recovery.preview_project_root_correction("Other Project", moved)
    require(not report["ok"] and report["status"] == "ambiguous", "ambiguous name guessed")
    require(project_manager.PROJECTS_FILE.read_bytes() == before, "ambiguous preview wrote")


def test_recovery_receipts_are_content_free_and_release_boundary_is_current() -> None:
    tmp = DATA_DIR / "case-privacy"; moved = _make_root(tmp / "moved")
    _write_registries(tmp, current_root=tmp / "missing")
    before_receipts = set(recovery.RECOVERY_RECEIPT_DIR.glob("*.json"))
    preview = recovery.preview_project_root_correction("other", moved)
    result = recovery.confirm_project_root_correction("other", moved, preview_token=preview["preview_token"], operator_confirmed=True)
    require(result["ok"], "privacy setup")
    receipts = set(recovery.RECOVERY_RECEIPT_DIR.glob("*.json")) - before_receipts
    require(len(receipts) == 1, "receipt count")
    raw = json.loads(next(iter(receipts)).read_text())
    require(not recovery.root_recovery_record_contains_private_fields(raw), "private recovery receipt")
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split(".")) >= (1092, 4), "version")
    require("# v1092.4 Missing or Moved Project Recovery" in (ROOT / "README_RELEASE_HISTORY.md").read_text(), "history")
    require(not (ROOT / "data" / "projects.json").exists(), "runtime projects packaged")


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--child", action="store_true"); parser.parse_args()
    checks = []; passed = 0
    for name, fn in TESTS:
        try: fn()
        except Exception as error: checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else: passed += 1; checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1092.4-missing-moved-project-recovery", "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail", "passed": passed, "total": len(TESTS), "checks": checks, "external_runtime": str(DATA_DIR)}
    print(json.dumps(report, indent=2)); return 0 if report["ok"] else 1


if __name__ == "__main__": raise SystemExit(main())
