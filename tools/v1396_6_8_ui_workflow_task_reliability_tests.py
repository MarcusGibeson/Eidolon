import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from representative_ui_workflow_task import record_windows_ui_validation, run_ui_workflow_task
from feature_freeze_final_hardening import _is_forbidden_source_entry
from v1396_test_support import REQUEST, TASK_ID, WINDOWS_CHECKS, require

passed = 0
with tempfile.TemporaryDirectory() as temp_dir:
    bad = run_ui_workflow_task(request="Make something", runtime_root=temp_dir, task_id=TASK_ID)
    require(not bad["ok"] and not bad["action_executed"], "unsupported request")
    passed += 1
with tempfile.TemporaryDirectory() as temp_dir:
    result = run_ui_workflow_task(request=REQUEST, runtime_root=temp_dir, task_id=TASK_ID)
    task = result["ui_workflow_task"]
    duplicate = run_ui_workflow_task(request=REQUEST, runtime_root=temp_dir, task_id=TASK_ID)
    require(not duplicate["ok"] and duplicate["status"] == "ui_workflow_task_already_exists", "duplicate")
    passed += 1
    incomplete = record_windows_ui_validation(task, platform="windows", checks=WINDOWS_CHECKS[:-1])
    require(not incomplete["ok"] and incomplete["windows_ui_validation"]["missing_checks"], "missing manual check")
    passed += 1
    failed_checks = [dict(row) for row in WINDOWS_CHECKS]
    failed_checks[1]["passed"] = False
    failed = record_windows_ui_validation(task, platform="windows", checks=failed_checks)
    require(not failed["ok"] and failed["windows_ui_validation"]["failed_checks"] == ["narrow_layout"], "failed viewport")
    passed += 1
    wrong_platform = record_windows_ui_validation(task, platform="linux", checks=WINDOWS_CHECKS)
    require(not wrong_platform["ok"] and not wrong_platform["action_executed"], "platform binding")
    passed += 1
    require(not task["eidolon_source_mutation_authorized"] and not task["provider_contact_authorized"], "authority")
    passed += 1
    require(
        task["content_free_evidence"]
        and not _is_forbidden_source_entry(Path("data/settings.json"))
        and _is_forbidden_source_entry(Path("data/projects.json")),
        "privacy",
    )
    passed += 1
print({"ok": passed == 7, "passed": passed, "total": 7, "suite": "v1396-reliability"})
