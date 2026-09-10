from __future__ import annotations

import hashlib
import json
from pathlib import Path

from complete_application_construction_foundations import prepare_complete_application_construction
from isolated_coding_execution import prepare_isolated_coding_execution
from isolated_coding_execution_foundations import (
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)


def tree_signature(root: Path) -> str:
    rows = []
    if not root.exists():
        return hashlib.sha256(b"missing").hexdigest()
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().casefold()):
        if path.is_file() and not path.is_symlink():
            rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def make_web_project(base: Path) -> Path:
    project = base / "calculator-web"
    project.mkdir(parents=True, exist_ok=True)
    (project / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Calculator</title></head><body><h1>Calculator</h1></body></html>\n",
        encoding="utf-8",
    )
    return project


def prepare_complete_web_request(project: Path, runtime: Path) -> tuple[dict, dict, dict]:
    request = create_or_restore_coding_work_request(
        user_objective="Build a complete responsive accessible calculator web application.",
        target_project=project,
        requirements=[
            "Build a multi-file calculator web application with addition, subtraction, multiplication, division, and clear.",
            "Provide an accessible labelled interface and visible keyboard focus.",
            "Provide responsive behavior for narrow screens.",
            "Include project-owned tests, configuration, and documentation.",
        ],
        acceptance_criteria=[
            "Calculator operations return correct results.",
            "All local HTML script and stylesheet references resolve.",
            "Accessibility and responsive structural checks pass.",
            "Project-owned tests pass with no network or dependency installation.",
        ],
        constraints=["Use plain HTML, CSS, and JavaScript.", "Keep the application locally runnable without a build step."],
        prohibited_actions=["Do not install dependencies.", "Do not access the network.", "Do not modify the selected project."],
        assumptions=["Node.js is available for the bounded project-owned tests."],
        expected_artifacts=["Complete web application", "Project-owned tests", "README", "package.json", "Reviewable isolated diff"],
        verification=["Run JavaScript syntax and project-owned tests", "Verify cross-file application quality", "Verify accessibility and responsive structural checks"],
        runtime_root=runtime,
    )
    assert request.get("ok")
    inspection = inspect_coding_project(request["request_id"], runtime_root=runtime)
    assert inspection.get("ok")
    plan = create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)
    assert plan.get("ok")
    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    assert workspace.get("ok")
    construction = prepare_complete_application_construction(request["request_id"], runtime_root=runtime, force=True)
    assert construction.get("ok")
    execution = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    assert execution.get("ok")
    return request, construction, execution
