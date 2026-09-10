import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "conscious_agent"), str(ROOT / "tools")]

from representative_ui_workflow_task import run_ui_workflow_task
from v1396_test_support import REQUEST, TASK_ID, require

passed = 0
with tempfile.TemporaryDirectory() as temp_dir:
    result = run_ui_workflow_task(request=REQUEST, runtime_root=temp_dir, task_id=TASK_ID)
    require(result["ok"], "workflow build")
    passed += 1
    task = result["ui_workflow_task"]
    require(task["file_count"] == 5 and task["node_test_exit_code"] == 0, "artifacts and state tests")
    passed += 1
    require(all(task["structural_checks"].values()), "responsive accessibility structure")
    passed += 1
    require(task["workflow_states"] == ["profile", "preferences", "review", "complete"], "workflow states")
    passed += 1
    require(task["manual_windows_validation_required"] and not task["manual_windows_validation_complete"], "manual validation boundary")
    passed += 1
print({"ok": passed == 5, "passed": passed, "total": 5, "suite": "v1396-foundations"})
