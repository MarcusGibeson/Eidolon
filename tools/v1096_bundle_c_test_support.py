from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))

from release_archive_coherence import build_candidate_archive
from release_candidate_identity import freeze_release_candidate, read_json
from release_handoff_inspection import inspect_selected_candidate_archive
from release_installation_plan import create_installation_plan
from release_installation_preview import create_installation_impact_preview
from release_installation_staging import (
    STAGING_CONFIRMATION,
    preview_installation_staging_authorization,
    stage_authorized_installation,
    staging_directory,
)
from release_metadata import WORKING_SOURCE_VERSION


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def prepare_staged_fixture(base: Path) -> dict[str, Any]:
    source = base / "source"
    target = base / "target"
    shutil.copytree(ROOT, source)
    shutil.copytree(ROOT, target)

    # Produce one add, one replace, one remove, and one protected difference.
    (target / "README.md").write_text("fixture target readme before installation\n", encoding="utf-8")
    add_path = target / "tools" / "v1096_4_installation_authorization_external_staging_tests.py"
    add_path.unlink()
    obsolete = target / "tools" / "obsolete_install_fixture.py"
    obsolete.write_text("obsolete = True\n", encoding="utf-8")
    protected = target / "data" / "settings.json"
    protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text(json.dumps({"operator_private_fixture": True}, indent=2) + "\n", encoding="utf-8")

    runtime = base / "runtime"
    candidate_runtime = runtime / "candidate"
    out = base / "out"
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze_release_candidate(source, runtime_root=candidate_runtime, expected_version=WORKING_SOURCE_VERSION)
    if not frozen.get("ok"):
        raise RuntimeError(f"candidate freeze failed: {frozen}")
    package = build_candidate_archive(source, runtime_root=candidate_runtime, destination_dir=out)
    archive = out / str(package["package_filename"])

    handoff_runtime = runtime / "handoff"
    handoff = inspect_selected_candidate_archive(archive, runtime_root=handoff_runtime)
    if not handoff.get("ok"):
        raise RuntimeError(f"handoff failed: {handoff}")

    registry = base / "projects.json"
    registry.write_text(json.dumps({
        "projects": [{
            "id": "fixture-target",
            "name": "Fixture Target",
            "source_root": str(target),
            "source_identity_markers": ["conscious_agent/release_metadata.py"],
        }]
    }, indent=2) + "\n", encoding="utf-8")
    preview = create_installation_impact_preview(
        "fixture-target", runtime_root=handoff_runtime, project_registry_path=registry
    )
    if not preview.get("ok"):
        raise RuntimeError(f"preview failed: {preview}")
    plan = create_installation_plan(runtime_root=handoff_runtime)
    if not plan.get("ok"):
        raise RuntimeError(f"plan failed: {plan}")
    staging_auth = preview_installation_staging_authorization(runtime_root=handoff_runtime)
    stage = stage_authorized_installation(
        str(staging_auth.get("authorization_token") or ""),
        confirm=STAGING_CONFIRMATION,
        runtime_root=handoff_runtime,
    )
    if not stage.get("ok"):
        raise RuntimeError(f"stage failed: {stage}")
    pointer = read_json(staging_directory(handoff_runtime) / "active_stage.json")
    stage_record = read_json(staging_directory(handoff_runtime) / "records" / f"{pointer['stage_id']}.json")
    return {
        "source": source,
        "target": target,
        "runtime": runtime,
        "handoff_runtime": handoff_runtime,
        "archive": archive,
        "registry": registry,
        "stage": stage,
        "stage_record": stage_record,
        "protected_path": protected,
        "protected_bytes": protected.read_bytes(),
        "add_relative": "tools/v1096_4_installation_authorization_external_staging_tests.py",
        "replace_relative": "README.md",
        "remove_relative": "tools/obsolete_install_fixture.py",
        "target_before": snapshot_files(target),
    }
