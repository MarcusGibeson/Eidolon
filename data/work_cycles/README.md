# Work cycles

Saved supervised task/work-cycle records.

v5.0 introduced the bounded cycle around the newer work-queue interface. v5.1 made the queue task-backed. v5.2 keeps the saved-cycle directory but records task aliases (`created_task_ids`, `created_followup_task_ids`, `executed_task_ids`) alongside the older work-id fields for compatibility.

v5.3 moved execution into `conscious_agent/task_work_executor.py`. New cycle events use `execute_task_work`, while old event readers still recognize `execute_work_item` for compatibility.

As of v5.4, new cycle records use task-centered wording. As of v5.5, blocked approval-gated task executions can create approval requests through `task_approval_bridge.py`. Older saved records remain readable.

As of v5.6, new cycle records use version `5.6`, and dashboard/API lifecycle summaries derive readable task stages from task status, approval links, and patch metadata. As of v5.7, dashboard/API lifecycle filters can drive focused task views and safe batch approval requests.
