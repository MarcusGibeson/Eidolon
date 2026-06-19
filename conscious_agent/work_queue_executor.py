from __future__ import annotations

"""
Legacy work-queue executor compatibility wrapper.

v5.3 consolidation note:
    task_work_executor.py is now the canonical executor. This module only
    re-exports the old v4.7-v5.2 names so existing CLI, dashboard, API, and
    saved references keep working during the naming transition.
"""

from task_work_executor import (  # noqa: F401
    ACTION_DASHBOARD_NOTE,
    ACTION_MANUAL,
    ACTION_REVIEW_FILE,
    ACTION_RUN_COMMAND,
    ACTION_SUGGEST_PATCH,
    ACTION_TEST_PROJECT,
    EXECUTABLE_ACTIONS,
    TaskWorkExecutionResult,
    WorkExecutionResult,
    can_execute_work_item,
    can_execute_task_work,
    classify_work_item,
    classify_task_work,
    execute_next_task_work,
    execute_next_work_item,
    execute_task_work_item,
    execute_work_item,
    get_next_task_work,
    print_execute_next_task_work_item,
    print_execute_next_work_item,
    print_execute_task_work_item,
    print_execute_work_item,
    task_work_execution_text,
    work_execution_text,
)
