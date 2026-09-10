from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from autonomous_developer_gamma_scorecard import build_gamma_outcome_record, build_gamma_scorecard
from no_prompt_gamma_session import run_no_prompt_session
from representative_bug_report_task import run_bug_report_task
from representative_data_migration_task import rollback_data_migration, run_data_migration_task
from representative_existing_project_feature import run_existing_project_feature
from representative_greenfield_task import run_small_greenfield_task
from representative_provider_backed_task import run_provider_backed_task
from representative_refactoring_task import run_refactoring_task
from representative_ui_workflow_task import record_windows_ui_validation, run_ui_workflow_task
from v1391_test_support import REQ as GREENFIELD_REQUEST
from v1392_test_support import REQ as FEATURE_REQUEST, project as feature_project
from v1393_test_support import REPORT as BUG_REPORT, V as VISUAL_DIGEST, project as bug_project
from v1394_test_support import REQ as REFACTOR_REQUEST, project as refactor_project
from v1395_test_support import db as migration_db
from v1396_test_support import REQUEST as UI_REQUEST, WINDOWS_CHECKS
from v1397_test_support import CONFIG as PROVIDER_CONFIG, REQUEST as PROVIDER_REQUEST, local_provider
from v1398_test_support import BACKLOG, active_grant, executor_factory


def require(condition, message):
    if not condition:
        raise AssertionError(message)


WINDOWS = {
    key: True
    for key in (
        "desktop_layout",
        "narrow_layout",
        "keyboard_forward",
        "keyboard_backward",
        "focus_visible",
        "error_announcement",
        "completion_announcement",
        "no_horizontal_overflow",
    )
}
CHANGED = [
    "README.md",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "archive/docs/legacy_dependencies/roadmaps/README_V1500_ROADMAP.md",
    "archive/docs/legacy_dependencies/validation/V1397_9_PROVIDER_BACKED_TASK_FINAL_VALIDATION.md",
    "archive/docs/legacy_dependencies/validation/V1398_9_NO_PROMPT_SESSION_FINAL_VALIDATION.md",
    "archive/docs/legacy_dependencies/validation/V1399_9_GAMMA_SCORECARD_FINAL_VALIDATION.md",
    "archive/docs/legacy_dependencies/validation/V1400_9_AUTONOMOUS_DEVELOPER_GAMMA_CHECKPOINT_FINAL_VALIDATION.md",
    "conscious_agent/checkpoint_registry.py",
    "conscious_agent/release_authority.py",
    "conscious_agent/release_metadata.py",
    "docs/release/release_metadata_manifest.json",
    "release_metadata.py",
    "data/settings.json",
    "conscious_agent/representative_provider_backed_task.py",
    "conscious_agent/no_prompt_gamma_session.py",
    "conscious_agent/autonomous_developer_gamma_scorecard.py",
    "conscious_agent/autonomous_developer_gamma_checkpoint.py",
]


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _task_row(task_class: str, evidence_digest: str, ok: bool) -> dict:
    return {"task_class": task_class, "evidence_digest": evidence_digest, "ok": ok}


def _scorecard(task_rows: list[dict], iteration: int) -> dict:
    records = []
    for index, row in enumerate(task_rows, 1):
        records.append(
            build_gamma_outcome_record(
                task_id=f"gamma-{iteration}-{index}",
                task_class=row["task_class"],
                success=row["ok"],
                duration_ms=index,
                evidence_checks={"tests": row["ok"], "result": row["ok"], "lineage": True, "rollback": True},
                boundary_checks={"authority": True, "privacy": True, "source": True},
                workflow_evidence_digest=row["evidence_digest"],
            )
        )
    return build_gamma_scorecard(records)["gamma_scorecard"]


def windows_validation_receipt(iteration: int = 0) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_ui_workflow_task(
            request=UI_REQUEST,
            runtime_root=temp_dir,
            task_id=f"gamma_{iteration + 1:012x}",
        )
        require(result["ok"], "Windows receipt workflow failed")
        validation = record_windows_ui_validation(
            result["ui_workflow_task"], platform="windows", checks=WINDOWS_CHECKS
        )
        require(validation["ok"], "Windows receipt failed")
        return validation["windows_ui_validation"]


def iteration_runner(iteration: int) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix=f"eidolon-gamma-{iteration:03d}-") as temp_dir:
            root = Path(temp_dir)
            task_id = f"gamma_{iteration + 1:012x}"
            rows: list[dict] = []

            greenfield = run_small_greenfield_task(
                request=GREENFIELD_REQUEST,
                runtime_root=root / "greenfield",
                task_id=task_id,
            )
            rows.append(_task_row("small_greenfield", str(greenfield.get("greenfield_task", {}).get("task_digest") or ""), greenfield.get("ok") is True))

            feature = run_existing_project_feature(
                project_root=feature_project(root / "feature"),
                request=FEATURE_REQUEST,
                operator_authorized=True,
            )
            rows.append(_task_row("existing_project_feature", str(feature.get("existing_project_feature", {}).get("task_digest") or ""), feature.get("ok") is True))

            bug = run_bug_report_task(
                project_root=bug_project(root / "bug"),
                bug_report=BUG_REPORT,
                visual_evidence_digest=VISUAL_DIGEST,
                operator_authorized=True,
            )
            rows.append(_task_row("bug_report", str(bug.get("bug_report_task", {}).get("task_digest") or ""), bug.get("ok") is True))

            refactor = run_refactoring_task(
                project_root=refactor_project(root / "refactor"),
                request=REFACTOR_REQUEST,
                operator_authorized=True,
            )
            rows.append(_task_row("refactoring", str(refactor.get("refactoring_task", {}).get("task_digest") or ""), refactor.get("ok") is True))

            migration_root = root / "migration"
            migration_root.mkdir()
            database = migration_db(migration_root)
            interrupted = run_data_migration_task(
                db_path=database,
                operator_authorized=True,
                simulate_interrupt_at="after_copy",
            )
            migration = run_data_migration_task(db_path=database, operator_authorized=True)
            migration_row = migration.get("data_migration", {})
            rollback = rollback_data_migration(
                db_path=database,
                migration=migration_row,
                expected_migration_digest=str(migration_row.get("migration_digest") or ""),
                operator_authorized=True,
            )
            migration_ok = interrupted.get("status") == "data_migration_interrupted_safely" and migration.get("ok") is True and rollback.get("ok") is True
            migration_evidence = _digest([migration_row.get("migration_digest"), rollback.get("data_migration_rollback", {}).get("rollback_digest")])
            rows.append(_task_row("data_migration", migration_evidence, migration_ok))

            ui = run_ui_workflow_task(
                request=UI_REQUEST,
                runtime_root=root / "ui",
                task_id=task_id,
            )
            ui_validation = record_windows_ui_validation(
                ui.get("ui_workflow_task", {}), platform="windows", checks=WINDOWS_CHECKS
            )
            ui_ok = ui.get("ok") is True and ui_validation.get("ok") is True
            ui_evidence = _digest([ui.get("ui_workflow_task", {}).get("task_digest"), ui_validation.get("windows_ui_validation", {}).get("validation_digest")])
            rows.append(_task_row("ui_workflow", ui_evidence, ui_ok))

            provider = run_provider_backed_task(
                request=PROVIDER_REQUEST,
                runtime_root=root / "provider",
                task_id=task_id,
                provider_config=PROVIDER_CONFIG,
                provider_call=local_provider,
                provider_use_authorized=True,
            )
            rows.append(_task_row("provider_backed", str(provider.get("provider_backed_task", {}).get("task_digest") or ""), provider.get("ok") is True))

            executor, calls = executor_factory(root / "no_prompt")
            session = run_no_prompt_session(
                grant=active_grant(1000 + iteration * 10),
                backlog=BACKLOG,
                executor=executor,
                now_unix=1002 + iteration * 10,
                max_items=3,
            )
            session_ok = session.get("ok") is True and len(calls) == 3
            rows.append(_task_row("no_prompt_session", str(session.get("no_prompt_session", {}).get("session_digest") or ""), session_ok))

            card = _scorecard(rows, iteration)
            ok = all(row["ok"] for row in rows) and card.get("gamma_ready") is True
            return {
                "ok": ok,
                "completed_tasks": len(rows) if ok else sum(row["ok"] for row in rows),
                "task_evidence": rows,
                "scorecard": card,
                "evidence_digest": _digest([rows, card.get("scorecard_digest"), iteration]),
                "failure_class": None if ok else "representative_workflow_failed",
            }
    except Exception as exc:
        return {
            "ok": False,
            "completed_tasks": 0,
            "task_evidence": [],
            "evidence_digest": "",
            "failure_class": type(exc).__name__,
        }


def scorecard() -> dict:
    result = iteration_runner(9000)
    require(result["ok"], "representative scorecard campaign failed")
    return dict(result["scorecard"])
