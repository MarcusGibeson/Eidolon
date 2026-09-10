import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from representative_ui_workflow_task import record_windows_ui_validation, run_ui_workflow_task
from v1396_test_support import REQUEST, TASK_ID, WINDOWS_CHECKS, require

passed = 0
with tempfile.TemporaryDirectory() as temp_dir:
    result = run_ui_workflow_task(request=REQUEST, runtime_root=temp_dir, task_id=TASK_ID)
    require(result["ok"], "workflow")
    passed += 1
    task = result["ui_workflow_task"]
    validation = record_windows_ui_validation(task, platform="windows", checks=WINDOWS_CHECKS)
    require(validation["ok"], "manual Windows evidence")
    passed += 1
    receipt = validation["windows_ui_validation"]
    require(receipt["manual_validation_performed"] and receipt["manual_windows_validation_complete"], "manual boundary")
    passed += 1
    require(task["runnable_result_ready"] and all(task["structural_checks"].values()), "quality")
    passed += 1
    require(not validation["release_authorized"] and not validation["promotion_authorized"], "authority")
    passed += 1
print({"ok": passed == 5, "passed": passed, "total": 5, "suite": "v1396-checkpoint"})
