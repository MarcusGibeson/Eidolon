# Task / Work compatibility notes

`task_queue.py` and `data/tasks.json` are the canonical task store. Legacy work-queue commands remain compatibility aliases.

As of v6.8, stable-loop decision follow-up tasks can be reported through completion filters such as `unresolved`, `ready_to_resolve`, `resolved`, and `cleanup_default`. Use `/stable-loop?followup=ready_to_resolve` or `--stable-loop-followup-completion-report ready_to_resolve` to find closure work.

# Legacy work-queue compatibility layer

`work_queue.py` is a compatibility adapter over canonical task storage:

```text
data/tasks.json
conscious_agent/task_queue.py
```

Use task-centered commands first:

```powershell
python conscious_agent/main.py --task-work summary
python conscious_agent/main.py --execute-task-work --dry-run
python conscious_agent/main.py --stable-loop-followup-lifecycle-summary all
```

Old `--work-queue` and `/api/work-queue/...` routes still work as aliases. They are kept so previous dashboard/API commands do not break like brittle little fossils.

As of v6.7, stable-loop decision follow-up tasks are canonical tasks with stable-loop metadata. Use `/tasks-work?stage=stable_loop_followup` or `--show-task-stable-loop-followup task_ID` to inspect which stable-loop decision created a follow-up task.


## v6.9 closure-aware guardrails

Stable-loop live runs now check unresolved decision follow-up chains before live advancement. Preview/preflight remains available, but live execution is blocked until follow-up chains are resolved/closed/archived or the operator explicitly uses the closure-guardrail bypass. Use `python conscious_agent/main.py --stable-loop-guardrails` to inspect the current state.
