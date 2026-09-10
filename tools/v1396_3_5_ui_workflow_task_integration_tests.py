import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from representative_ui_workflow_task import process_ui_workflow_task_control, record_windows_ui_validation, run_ui_workflow_task
from v1396_test_support import REQUEST, TASK_ID, WINDOWS_CHECKS, require

passed = 0
with tempfile.TemporaryDirectory() as temp_dir:
    result = run_ui_workflow_task(request=REQUEST, runtime_root=temp_dir, task_id=TASK_ID)
    task = result["ui_workflow_task"]
    receipt = record_windows_ui_validation(task, platform="Windows", checks=WINDOWS_CHECKS)
    require(receipt["ok"] and receipt["windows_ui_validation"]["manual_windows_validation_complete"], "Windows validation")
    passed += 1
    require(receipt["windows_ui_validation"]["viewport_count"] == 2, "desktop and narrow viewports")
    passed += 1
    require(not receipt["release_authorized"] and not receipt["independent_authority_granted"], "authority")
    passed += 1
    control = process_ui_workflow_task_control("show ui workflow task", project_state={"ui_workflow_task": task})
    require(control["active"] and control["ok"] and not control["action_executed"], "ordinary inspection")
    passed += 1
    require(all(row["passed"] for row in receipt["windows_ui_validation"]["checks"]), "manual checks")
    passed += 1
print({"ok": passed == 5, "passed": passed, "total": 5, "suite": "v1396-integration"})
