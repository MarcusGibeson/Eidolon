# Work Queue Legacy Adapter

As of v5.1, `task_queue.py` and `data/tasks.json` are Eidolon's canonical work/task store.

As of v5.2, patch-request and patch-follow-up behavior is task-native through `conscious_agent/task_patch_bridge.py`. The older `work_queue_patch_bridge.py` module remains as a compatibility wrapper.

The older v4.6-v5.0 `work_queue.py` API remains available as a compatibility adapter so dashboard/API/CLI routes such as `--work-queue (legacy alias; prefer --task-work)`, `/work-queue (legacy alias; prefer /tasks-work)`, and work-cycle helpers keep working.

Do not add new state here. New queued work should be stored in `data/tasks.json` through `task_queue.py`.

As of v5.3, task execution is also task-native through `conscious_agent/task_work_executor.py`. The older `work_queue_executor.py` module remains only as a compatibility wrapper.

As of v5.4, this directory is explicitly documented as compatibility-only. New task/work state belongs in `data/tasks.json`; this path exists so older commands and records have somewhere honest to point.


As of v5.5, approval-gated task execution is connected to `approval_manager.py` through `conscious_agent/task_approval_bridge.py`. The old work-queue route can still request approval for a task, but new code should use task-centered approval commands and `/api/tasks/...` endpoints.

As of v5.6, dashboard/API lifecycle views are task-centered. Legacy work-queue aliases still read the same task-backed lifecycle data. As of v5.7, lifecycle filters and safe batch approval-request actions are available from /tasks-work and /api/tasks/... endpoints.
