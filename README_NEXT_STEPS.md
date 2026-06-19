# Eidolon v5.7 - Task Lifecycle Actions / Filters

v5.7 turns the v5.6 lifecycle view into a controllable operator surface. The dashboard can now filter Tasks / Work by lifecycle stage and safely batch-request approvals for tasks that need approval. No batch execution button was added, because apparently we prefer filesystems that continue existing.

## What changed in v5.7

- Updated `conscious_agent/task_lifecycle.py`
  - added lifecycle stage filter helpers
  - added grouped filters: `open`, `needs_attention`, and `ready_to_act`
  - `task_lifecycle_summary()` now returns filter metadata and filtered rows
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.7`
  - `/tasks-work?stage=...` now filters task tables by lifecycle stage
  - added filter chips for all major lifecycle stages
  - added safe batch action: request approvals for all approval-required tasks
  - added dry-run-next-ready shortcut without adding a dangerous execute-all button
- Updated `conscious_agent/api_server.py`
  - API version is now `5.7`
  - `GET /api/tasks?stage=...` returns tasks matching a lifecycle filter
  - `GET /api/tasks/lifecycle?stage=...` returns lifecycle summaries for a selected filter
  - added `POST /api/tasks/request-approvals`
- Updated version/docs metadata
  - `data/settings.json` and `settings_manager.py` use `settings_version: 5.7`
  - new saved work-cycle records use version `5.7`
  - README files mention lifecycle filters and batch approval requests

## Lifecycle filter examples

Dashboard:

```text
http://127.0.0.1:8765/tasks-work
http://127.0.0.1:8765/tasks-work?stage=needs_attention
http://127.0.0.1:8765/tasks-work?stage=approval_required
http://127.0.0.1:8765/tasks-work?stage=approved_ready
http://127.0.0.1:8765/tasks-work?stage=patch_proposed
```

API:

```text
GET /api/tasks?stage=needs_attention
GET /api/tasks?stage=ready_to_act
GET /api/tasks/lifecycle?stage=approval_required
POST /api/tasks/request-approvals
```

Approval request body example:

```json
{
  "stage": "approval_required",
  "dry_run": true,
  "use_ai": true,
  "reason": "Batch approval request from lifecycle filter."
}
```

## Main checks after v5.7

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full
```

Dashboard:

```text
http://127.0.0.1:8765/tasks-work?stage=needs_attention
```

API:

```text
GET /api/tasks/lifecycle?stage=needs_attention
GET /api/tasks?stage=ready_to_act
POST /api/tasks/request-approvals
```

## Next likely milestone

Next feature work should be **v5.8 - Task Failure Recovery / Retry Logic**. The dashboard can now filter and request approvals; the next pass should help failed/blocked tasks produce explicit recovery options instead of just sitting there like a printer with an attitude problem.

---

# Eidolon v5.6 - Task Lifecycle Dashboard Polish

v5.6 makes the dashboard and API explain task state in plain lifecycle stages instead of forcing you to decode raw status + risk + approval metadata like some cursed office horoscope. The canonical task system remains `task_queue.py`, `task_work_executor.py`, `task_patch_bridge.py`, and `task_approval_bridge.py`.

## What changed in v5.6

- Added `conscious_agent/task_lifecycle.py`
  - derives readable lifecycle stages from task status, risk, approval links, and patch metadata
  - does not mutate task state
  - powers dashboard and API lifecycle summaries
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.6`
  - `/tasks-work` now shows lifecycle summary cards
  - task tables now include a **Lifecycle** column
  - task detail pages now show a lifecycle flow strip
  - lifecycle legend explains the approval path clearly
- Updated `conscious_agent/api_server.py`
  - API version is now `5.6`
  - added `GET /api/tasks/lifecycle`
  - added `GET /api/tasks/{id}/lifecycle`
  - `/api/status` now includes `task_lifecycle` summary data
- Updated `conscious_agent/work_cycle.py`
  - new saved cycle records use version `5.6`
- Updated settings/docs metadata
  - `data/settings.json` and `settings_manager.py` use `settings_version: 5.6`
  - `data/work_queue/README.md` and `data/work_cycles/README.md` mention lifecycle views

## Lifecycle stages

The dashboard now derives these readable stages:

```text
Ready
Active
Needs approval request
Approval pending
Approved, ready to run
Approval rejected
Approval failed
Blocked
Patch proposed
Done
Cancelled
Unknown
```

This is display logic only. The actual source of truth stays in `data/tasks.json`.

## Main checks after v5.6

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full
```

Dashboard:

```text
http://127.0.0.1:8765/tasks-work
```

API:

```text
GET /api/tasks/lifecycle
GET /api/tasks/{id}/lifecycle
GET /api/status
```

## Next likely milestone

Completed by **v5.7 - Task Lifecycle Actions / Filters**. The dashboard can now filter by lifecycle stage and batch-request approval for tasks that are stuck in `Needs approval request`.

---

# Eidolon v5.5 - Approval Flow Consolidation

v5.5 connects approval-gated task execution to the existing `approval_manager.py` instead of leaving risky tasks blocked and silently sulking in `data/tasks.json`. The canonical path is still task-centered: `task_queue.py`, `task_work_executor.py`, and `/api/tasks/...`. This pass makes blocked/risky tasks create real approval requests that can be dry-run, approved, or rejected through the existing approval inbox.

## What changed in v5.5

- Added `conscious_agent/task_approval_bridge.py`.
- Risky or approval-required task execution now creates a pending approval request instead of only blocking the task.
- Approval requests for task execution use the existing `approval_manager.py` flow with `action_type=run_command` and a safe command like:

```powershell
python conscious_agent/main.py --execute-task-work-id task_ID --approve-task-work-execution
```

- Linked task metadata now stores:

```text
approval_id
approval_status
approval_kind
approval_command
approval_reason
```

- Approving or rejecting a linked approval syncs approval status back to the task metadata.
- Dashboard Tasks / Work rows now show linked approvals and include a **Request Approval** button for blocked/risky tasks.
- Task detail pages now show linked approval history.
- Added primary API support for:

```text
GET  /api/tasks/{id}/approvals
POST /api/tasks/{id}/request-approval
POST /api/tasks/next/request-approval
```

- Added CLI support for:

```powershell
python conscious_agent/main.py --request-task-approval task_ID
python conscious_agent/main.py --request-task-approval task_ID --dry-run
python conscious_agent/main.py --request-next-task-approval --task-approval-project eidolon
python conscious_agent/main.py --show-task-approvals task_ID --task-approval-full
```

- Updated version labels:
  - `conscious_agent/api_server.py` now reports API version `5.5`
  - `conscious_agent/dashboard.py` now reports dashboard version `5.5`
  - `conscious_agent/work_cycle.py` now saves new cycle records as version `5.5`
  - `data/settings.json` and `settings_manager.py` now use `settings_version: 5.5`

## Safe approval workflow

Create or find an approval-gated task:

```powershell
python conscious_agent/main.py --task-work add "Run risky supervised task" --project eidolon --priority 7 --risk medium --requires-approval
```

Dry-run the approval request first:

```powershell
python conscious_agent/main.py --request-task-approval task_ID --dry-run --task-approval-full
```

Create the approval request:

```powershell
python conscious_agent/main.py --request-task-approval task_ID --task-approval-full
```

Inspect and dry-run the approval:

```powershell
python conscious_agent/main.py --show-approval latest-pending --approval-full
python conscious_agent/main.py --approve latest-pending --dry-run
```

Approve or reject it:

```powershell
python conscious_agent/main.py --approve latest-pending
python conscious_agent/main.py --reject latest-pending --approval-note "Not safe yet"
```

## Current architecture

```text
task_queue.py / data/tasks.json
        ↑
canonical task/work storage
        ↑
task_work_executor.py
        ↑
blocks risky tasks and requests approvals
        ↑
task_approval_bridge.py
        ↑
approval_manager.py / data/approvals/*.json
```

Legacy aliases still work:

```text
/work-queue
/api/work-queue/...
--work-queue
--execute-work
```

Use the task-centered names for new work. Old names exist so previous buttons and commands do not collapse into dust, which is apparently frowned upon.

## Next milestone

Next feature work should be **v5.6 - Task Lifecycle Dashboard Polish**. The goal is to make the task detail/dashboard pages clearer around `planned → blocked → approval pending → approved/executed → done`, because right now the plumbing works but the signs could still use a less cursed paint job.

---

# Eidolon v5.4 - Dashboard/API Naming Cleanup

v5.4 finishes the visible naming cleanup after the v5.1-v5.3 consolidation. The project already made `task_queue.py`, `task_patch_bridge.py`, and `task_work_executor.py` canonical. This pass makes the dashboard and API lead with the same task-centered names, because having three names for one thing is how software gets haunted.

## What changed in v5.4

- Updated version labels:
  - `conscious_agent/api_server.py` now reports API version `5.4`
  - `conscious_agent/dashboard.py` now reports dashboard version `5.4`
  - `conscious_agent/work_cycle.py` now saves new cycle records as version `5.4`
  - `data/settings.json` and `settings_manager.py` now use `settings_version: 5.4`
- Made `/tasks-work` the primary dashboard route for task-backed work controls.
- Kept `/work-queue` as a legacy alias that renders the same task-backed page.
- Updated dashboard nav, overview links, detail back-links, page headings, and form wording toward **Tasks / Work** and **Task** language.
- Added primary API support for:

```text
GET  /api/tasks/summary
POST /api/tasks/{id}/done
POST /api/tasks/{id}/block
POST /api/tasks/{id}/cancel
```

- Kept legacy API aliases working:

```text
GET  /api/work-queue
GET  /api/work-queue/summary
POST /api/work-queue
POST /api/work-queue/{id}/dry-run
POST /api/work-queue/{id}/execute
POST /api/work-queue/{id}/done
POST /api/work-queue/{id}/block
POST /api/work-queue/{id}/cancel
```

- Updated API docs so `/api/tasks/...` is first-class and `/api/work-queue/...` is clearly compatibility-only.
- Updated `data/projects.json`, `data/work_queue/README.md`, and `data/work_cycles/README.md` to point new work at task-centered names.

## Canonical dashboard/API usage

Prefer these:

```powershell
python conscious_agent/main.py --task-work summary
python conscious_agent/main.py --execute-task-work --dry-run --no-ai-task-work-executor
python conscious_agent/main.py --queue-task-patch conscious_agent/dashboard.py "Describe the patch request"
```

Prefer these browser/API routes:

```text
http://127.0.0.1:8765/tasks-work
GET  /api/tasks
GET  /api/tasks/summary
POST /api/tasks
POST /api/tasks/next/dry-run
POST /api/tasks/next/execute
POST /api/tasks/{id}/dry-run
POST /api/tasks/{id}/execute
POST /api/tasks/{id}/done
POST /api/tasks/{id}/block
POST /api/tasks/{id}/cancel
POST /api/tasks/patch-request
POST /api/tasks/{id}/suggest-patch
```

Legacy aliases still work, but new docs and future code should avoid them unless testing compatibility:

```text
/work-queue
/api/work-queue/...
--work-queue
--execute-work
--queue-patch
--suggest-patch-for-work
```

## Health check order

From the project root on Windows:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe .\tools\smoke_check.py
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full
```

## Next milestone

Next feature work should be **v5.5 - Approval Flow Consolidation**. The goal is to connect blocked/risky tasks, patch application requests, and command execution requests into `approval_manager.py` and the dashboard approvals page, instead of letting blocked tasks sit around like sad office furniture.

---

# Eidolon v5.3.1 - Version / Health Cleanup

v5.3.1 is a stabilization pass after the v5.1-v5.3 consolidation work. No new autonomy layer was added. This update makes the project describe itself accurately, strengthens the smoke check, and clarifies that tasks are now the canonical work system. Yes, we paused the feature conveyor belt long enough to label the boxes. Civilization trembles.

## What changed in v5.3.1

- Updated version labels:
  - `conscious_agent/api_server.py` now reports API version `5.3.1`
  - `conscious_agent/dashboard.py` now reports dashboard version `5.3.1`
  - `conscious_agent/work_cycle.py` now saves new cycle records as version `5.3.1`
  - `data/settings.json` and `settings_manager.py` now use `settings_version: 5.3.1`
- Kept the desktop module version constants at `4.5` because those files are still the v4.5 desktop/onboarding feature modules, not the current whole-project version.
- Updated the default embedding model in `settings_manager.py` to `nomic-embed-text:latest` so defaults match the current setup file.
- Cleaned `main.py` help text so `--task-work` and `--work-cycle` describe the task-backed architecture instead of the older work-queue wording.
- Updated dashboard/API labels so `/api/tasks/...` and `/tasks-work` are described as the canonical path, while `/api/work-queue/...` and `/work-queue` are legacy aliases.
- Updated `data/projects.json` so current goals and next steps point at the task-centered architecture instead of old v4.5/v4.6 desktop milestones.
- Expanded `tools/smoke_check.py` so it now also runs:
  - `py_compile` across `conscious_agent/*.py`
  - `main.py --task-work summary`
- Updated compatibility notes in:
  - `data/work_queue/README.md`
  - `data/work_cycles/README.md`

## Canonical architecture after this cleanup

```text
task_queue.py / data/tasks.json
        ↑
canonical task/work storage
        ↑
task_patch_bridge.py
        ↑
canonical task-to-patch linking
        ↑
task_work_executor.py
        ↑
canonical task execution
```

Compatibility aliases still exist:

```text
work_queue.py
work_queue_patch_bridge.py
work_queue_executor.py
/work-queue
/api/work-queue/...
```

Those should keep old commands and dashboard buttons working, but new code should use the task-centered names. Multiple names for the same thing: mankind's gift to future confusion.

## Recommended health check order

From the project root on Windows:

```powershell
.\setup.ps1
```

Then:

```powershell
.\.venv\Scripts\python.exe .\tools\smoke_check.py
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full
```

If Ollama is not reachable, start Ollama and verify models:

```powershell
ollama list
ollama pull qwen2.5:7b
ollama pull nomic-embed-text:latest
```

Then rerun:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
```

## Troubleshooting map

| Problem | First command to run | What it tells you |
|---|---|---|
| Python import/package issue | `.\.venv\Scripts\python.exe .\tools\smoke_check.py` | Whether dependencies, compile checks, status, settings health, and task summary work |
| Syntax error | `.\.venv\Scripts\python.exe -m py_compile .\conscious_agent\*.py` | Exact file and line Python refuses to tolerate |
| Local AI not responding | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health` | Ollama reachability and configured model status |
| Task/work confusion | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary` | Canonical task-backed work state |
| Executor weirdness | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full` | How the next task would be classified and routed |
| Patch-task bridge issue | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --queue-task-patch conscious_agent/dashboard.py "Test patch request"` | Whether task-to-patch setup works |
| Dashboard issue | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --dashboard` | Opens local dashboard at `http://127.0.0.1:8765` |
| API issue | `.\.venv\Scripts\python.exe .\conscious_agent\main.py --api-server` | Opens standalone API at `http://127.0.0.1:8766/api/status` |

## Next milestone

Next feature work should be **v5.4 - Dashboard/API Naming Cleanup**. The goal is to make `/tasks-work` and `/api/tasks/...` the visible first-class controls everywhere, while keeping `/work-queue` and `/api/work-queue/...` as legacy aliases until the transition is boring enough to trust. Boring is the sound of software not exploding.

---

# Eidolon local setup maintenance - 2026-06-19

This pass fixed the local developer environment and added a repeatable setup check so Eidolon can be brought back to a known-good state without re-discovering the same issues.

## What changed

- Installed the declared Python dependencies into `.venv`
- Added `setup.ps1`
- Added `tools/smoke_check.py`
- Added `.gitignore`
- Initialized a local git repository
- Updated `data/settings.json`:
  - `embed_model`: `nomic-embed-text:latest`
- Verified the dashboard API at:
  - `http://127.0.0.1:8765/api/status`

## New setup command

From the project root:

```powershell
.\setup.ps1
```

The setup script:

- creates `.venv` if it is missing
- installs `requirements.txt`
- runs the smoke check
- prints useful next commands

## New smoke check

Run directly:

```powershell
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

The smoke check verifies:

- `requests` imports
- `chromadb` imports
- `data/settings.json` loads
- `python conscious_agent/main.py --status` works
- `python conscious_agent/main.py --settings-health` works

Known-good output from this pass:

```text
[ok] import requests
[ok] import chromadb
[ok] settings.json local_model=qwen2.5:7b embed_model=nomic-embed-text:latest safe_mode=strict
[ok] main.py --status
[ok] main.py --settings-health
Smoke check passed.
```

## Current run commands

Status:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
```

Onboarding:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --onboarding
```

Dashboard:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --dashboard
```

Then open:

```text
http://127.0.0.1:8765
```

## Git note

The repository was initialized during this pass, but no commit was created. Runtime-heavy paths are ignored in `.gitignore`, including `.venv/`, `__pycache__/`, `*.pyc`, `data/chroma/`, and `data/backups/`.

---

# Eidolon v5.3 - Executor Naming Consolidation

v5.3 finishes the next cleanup step from v5.2: execution is now task-centered too. The canonical executor is `conscious_agent/task_work_executor.py`, and the old `work_queue_executor.py` is now only a compatibility wrapper. The project still accepts the older `--execute-work` commands and `/api/work-queue/...` routes, because breaking working controls for vocabulary purity is how software earns haunting rights.

## What changed in v5.3

- Added `conscious_agent/task_work_executor.py`
  - canonical task-centered execution layer
  - operates directly on `task_queue.py` / `data/tasks.json`
  - supports review-file, run-command, suggest-patch, test-project, dashboard-note, and manual classifications
  - keeps compatibility aliases like `work_id` in result payloads during the transition
- Rewrote `conscious_agent/work_queue_executor.py`
  - now a compatibility wrapper over `task_work_executor.py`
  - old imports such as `execute_work_item` and `work_execution_text` still work
- Updated `conscious_agent/main.py`
  - added `--execute-task-work`
  - added `--execute-task-work-id`
  - added `--execute-task-work-project`
  - added `--approve-task-work-execution`
  - added `--no-ai-task-work-executor`
  - added `--task-work-executor-full`
  - kept old `--execute-work`, `--execute-work-id`, `--execute-work-project`, `--approve-work-execution`, `--no-ai-work-executor`, and `--work-executor-full` aliases
- Updated `conscious_agent/api_server.py`
  - API version is now `5.3`
  - added task-centered executor routes:
    - `POST /api/tasks/next/dry-run`
    - `POST /api/tasks/next/execute`
    - `POST /api/tasks/{id}/dry-run`
    - `POST /api/tasks/{id}/execute`
  - kept old `/api/work-queue/...` executor routes working as aliases
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.3`
  - Tasks / Work page now points at `task_work_executor.py` as the canonical executor
- Updated `conscious_agent/work_cycle.py`
  - calls the task-centered executor directly
  - saved event type is now `execute_task_work`, while old event readers still recognize `execute_work_item`
- Updated `conscious_agent/command_runner.py`
  - added the new task-centered executor flags to the safe command argument list
- Updated README notes in `data/work_queue/README.md` and `data/work_cycles/README.md`

## New task-centered executor commands

Dry-run the next safe task:

```powershell
python conscious_agent/main.py --execute-task-work --dry-run
```

Execute the next safe task:

```powershell
python conscious_agent/main.py --execute-task-work
```

Dry-run one specific task:

```powershell
python conscious_agent/main.py --execute-task-work-id task_YOUR_ID --dry-run
```

Execute one specific task with full output:

```powershell
python conscious_agent/main.py --execute-task-work-id task_YOUR_ID --task-work-executor-full
```

The older `--execute-work` commands still work as compatibility aliases.

## Current source of truth

```text
task_queue.py / data/tasks.json
        ↓
task_patch_bridge.py
        ↓
task_work_executor.py
        ↓
work_queue.py / work_queue_patch_bridge.py / work_queue_executor.py
compatibility adapters only
```

## Next step

Next should be **v5.4 - Dashboard/API Naming Cleanup**, where the visible route names and dashboard form/action names move from `/work-queue` toward `/tasks-work` and `/api/tasks/...` first, while old routes remain aliases.

# Eidolon v5.2 - Task-Centered Patch Follow-up Cleanup

v5.2 finishes the cleanup started in v5.1. The project now treats `task_queue.py` / `data/tasks.json` as the canonical task/work layer, and patch-generation follow-ups now have a task-native bridge instead of living mainly behind the older work-queue names. Basically, fewer duplicate kingdoms. Somewhere, a JSON file can finally sleep.

## What changed in v5.2

- Added `conscious_agent/task_patch_bridge.py`
  - task-native patch request creation
  - task-to-patch linking
  - task-native review/apply/test follow-up creation
  - compatibility aliases for older work-id fields
- Rewrote `conscious_agent/work_queue_patch_bridge.py` as a compatibility wrapper over `task_patch_bridge.py`
- Updated `conscious_agent/main.py`
  - added `--task-work` as a task-centered alias for the transitional work CLI
  - added `--queue-task-patch`
  - added `--suggest-patch-for-task`
  - added `--create-patch-task-followups`
  - kept the older `--work-queue`, `--queue-patch`, `--suggest-patch-for-work`, and `--create-patch-followups` aliases working
- Updated `conscious_agent/api_server.py`
  - API version is now `5.2`
  - added `POST /api/tasks/patch-request`
  - added `POST /api/tasks/{id}/suggest-patch`
  - added `POST /api/patches/{id}/create-task-followups`
  - kept the old `/api/work-queue/...` and `/api/patches/{id}/create-followups` aliases
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.2`
  - visible labels now say **Tasks / Work** and **Patch Task** more consistently
  - `/tasks-work` now opens the same task-backed view as `/work-queue`
  - patch records show linked **Task** IDs instead of presenting them as separate work items
- Updated `conscious_agent/work_cycle.py`
  - uses task-native patch follow-up creation
  - saved cycle records now include task aliases like `created_task_ids`, `created_followup_task_ids`, and `executed_task_ids`
  - older work-id fields are kept for compatibility
- Updated `conscious_agent/command_runner.py` safe command flags for the new task-centered patch commands
- Updated `data/work_queue/README.md` and `data/work_cycles/README.md`

## New task-centered commands

Create a task-backed patch request:

```powershell
python conscious_agent/main.py --queue-task-patch conscious_agent/dashboard.py "Describe the change to propose."
```

Dry-run patch generation from a task:

```powershell
python conscious_agent/main.py --suggest-patch-for-task task_YOUR_ID --dry-run
```

Generate and link the patch proposal from a task:

```powershell
python conscious_agent/main.py --suggest-patch-for-task task_YOUR_ID
```

Create review/apply/test follow-up tasks for a patch:

```powershell
python conscious_agent/main.py --create-patch-task-followups patch_YOUR_ID
```

The older commands still work as aliases, because breaking working commands just to satisfy vocabulary purity is how frameworks are born, and nobody needs that.

## New task-centered API routes

```text
POST /api/tasks/patch-request
POST /api/tasks/{id}/suggest-patch
POST /api/patches/{id}/create-task-followups
```

Legacy aliases still work:

```text
POST /api/work-queue/patch-request
POST /api/work-queue/{id}/suggest-patch
POST /api/patches/{id}/create-followups
```

## Dashboard

Run:

```powershell
python conscious_agent/main.py --dashboard
```

Then open either route:

```text
http://127.0.0.1:8765/work-queue
http://127.0.0.1:8765/tasks-work
```

Both show the same task-backed Tasks / Work page. `/work-queue` remains for compatibility. `/tasks-work` is the cleaner name going forward. Humanity survives another naming migration. Barely.

## Safety notes

- `task_patch_bridge.py` only creates patch proposals and follow-up tasks. It does not directly apply patches.
- Apply-patch follow-up tasks are approval-required.
- Old work-queue fields like `work_item_id` and `linked_work_items` are still written to patch proposal records as aliases so old dashboard/API code can still find links.
- New code should prefer `task_id`, `linked_tasks`, and the task-centered commands/API routes.

## Tested in this patch

- `python3 -m py_compile conscious_agent/*.py`
- `python3 conscious_agent/main.py --task-work summary`
- `python3 conscious_agent/main.py --queue-task-patch conscious_agent/dashboard.py "Dry run test task patch"`
- `python3 conscious_agent/main.py --suggest-patch-for-task task_TEST_ID --dry-run --no-ai-work-executor`
- `python3 conscious_agent/main.py --work-queue summary`
- dashboard render for `/work-queue` and `/tasks-work`
- API smoke checks for task-centered patch routes

Temporary smoke-test tasks were removed before packaging. The project is not being shipped with my little test droppings.

## Next likely step

Next should be **v5.3 - Executor Naming Consolidation**.

That should either rename `work_queue_executor.py` into a task-centered executor or add a thin `task_work_executor.py` facade so the codebase stops using old work-queue names in the execution path. Not urgent, but leaving old names everywhere is how codebases become haunted museums.

---

# Eidolon v5.1 - Architecture Consolidation

v5.1 stops the duplicate-architecture spiral from v4.6-v5.0. Eidolon already had a mature `task_queue.py` / `dev_loop_runner.py` / `autonomous_dev_cycle.py` stack before the newer `work_queue.py` / `work_cycle.py` path was added. This patch consolidates the useful newer ideas back onto the older task system so the project has one canonical task store instead of two tiny governments arguing over JSON files.

## Main decision

`task_queue.py` and `data/tasks.json` are now the canonical source of truth for task/work state.

`work_queue.py` remains, but it is now a compatibility adapter over `task_queue.py`. Existing commands and dashboard/API routes still work:

```powershell
python conscious_agent/main.py --work-queue summary
python conscious_agent/main.py --work-queue list --full
python conscious_agent/main.py --execute-work --dry-run --no-ai-work-executor
```

Those commands now read and write `data/tasks.json`, not a separate independent queue. The old `data/work_queue/work_items.json` file is retained only for legacy reference and should not receive new state.

## What changed in v5.1

- Updated `conscious_agent/task_queue.py`
  - added `requires_approval`
  - added `metadata`
  - added `patch_id` and `patch_status`
  - added `result`
  - added `work_status` compatibility field
  - added public `update_task_fields(...)`
  - added public `delete_task(...)`
  - expanded task detail output to show approval, patch, result, and metadata
- Rewrote `conscious_agent/work_queue.py` as a compatibility layer over `task_queue.py`
- Added `data/work_queue/README.md` explaining that work queue storage is legacy
- Preserved v4.8/v4.9/v5.0 dashboard, API, and CLI routes by mapping them to task-backed records
- Updated this README to document the consolidation

## Why this matters

Before v5.1, these concepts were duplicated:

```text
task_queue.py       ↔ work_queue.py
task_executor.py    ↔ work_queue_executor.py
autonomous_dev_cycle.py / dev_loop_runner.py ↔ work_cycle.py
```

After v5.1, new task/work records should be created through `task_queue.py`, while the newer work-queue interface stays available as a transitional shell. The shell still exists so the dashboard does not crack in half like cheap plastic, but the state underneath is unified.

## Compatibility behavior

Work-queue statuses map to task statuses like this:

```text
pending   -> planned
active    -> active
blocked   -> blocked
done      -> done
cancelled -> cancelled
failed    -> blocked + work_status=failed
```

Task priorities map back to work-queue numeric priorities:

```text
critical -> 10
high     -> 8
medium   -> 5
low      -> 2
```

## Safety notes

- Approval-required fields now live on canonical tasks.
- Patch IDs and patch statuses now live on canonical tasks.
- Existing patch follow-up helpers still work, but their created work items are task-backed.
- The dashboard `/work-queue` page still works, but it is really showing task-backed work now. Naming things remains humanity's longest-running prank.
- Do not add new independent queue state under `data/work_queue/`.

## Tested in this patch

- `python3 -m py_compile conscious_agent/*.py`
- `python3 conscious_agent/main.py --work-queue summary`
- `python3 conscious_agent/main.py --task-status`
- add a work item through `--work-queue add` and verify it appears in `data/tasks.json`
- mark that work item done through `--work-queue done` and verify task status becomes `done`
- show the same record through `--show-task ... --show-task-full`
- restore temporary smoke-test task data before packaging

## Next likely step

Next should be **v5.2 - Task-Centered Patch Follow-up Cleanup**.

That patch should update naming and UI language so the dashboard stops pretending the old work queue is separate. It should gradually rename visible labels toward "Tasks / Work" and move patch follow-up code from compatibility language into task-native language.

---

# Eidolon v5.0 - Supervised Autonomous Work Cycle

v5.0 connects the newer self-directed work queue into a bounded supervised cycle. It observes the queue, previews or advances the next safe work item, can seed the queue when it is empty, and can create patch follow-up work items after a patch proposal appears. This is the first queue-centered loop that feels like Eidolon coordinating its own work instead of waiting for Marcus to manually copy every ID like a haunted office clerk.

This is still supervised. Dry-run is the recommended default. Non-dry-run work still routes through the work queue executor, patch proposal system, command whitelist, approval flags, and existing safety gates.

## What changed in v5.0

- Added `conscious_agent/work_cycle.py`
- Added `data/work_cycles/` for saved supervised work-cycle records
- Updated `conscious_agent/main.py`
- Updated `conscious_agent/api_server.py`
- Updated `conscious_agent/dashboard.py`
- Updated `conscious_agent/command_runner.py`
- Updated `README_NEXT_STEPS.md`
- Updated dashboard/API version strings to `5.0`
- Added CLI commands for running, listing, and showing work cycles
- Added API routes for work cycles
- Added dashboard page `/work-cycle`
- Added dashboard detail support for saved work-cycle records
- Added work-cycle live count to the dashboard nav/status payload
- Added command-runner whitelist entries for safe work-cycle inspection commands

## What the work cycle does

A supervised work cycle performs this bounded loop:

```text
observe work queue
→ create patch follow-ups for proposed patches when safe
→ seed queue if empty, unless disabled
→ dry-run or execute the next safe work item
→ if a patch is generated, create review/apply/test follow-ups
→ save a cycle record
```

When the queue is empty and seeding is enabled, v5.0 can create two low-risk starter items:

- review `README_NEXT_STEPS.md`
- run the general Eidolon test workflow

In dry-run mode, it previews those seed items instead of creating them. Tiny mercy from the machine.

## New CLI commands

Dry-run the supervised cycle, recommended first:

```powershell
python conscious_agent/main.py --work-cycle --dry-run --no-ai-work-cycle
```

Run one non-dry-run supervised cycle step:

```powershell
python conscious_agent/main.py --work-cycle --work-cycle-steps 1 --no-ai-work-cycle
```

Run up to three bounded steps:

```powershell
python conscious_agent/main.py --work-cycle --work-cycle-steps 3
```

List saved work cycles:

```powershell
python conscious_agent/main.py --list-work-cycles
```

Show the latest saved cycle:

```powershell
python conscious_agent/main.py --show-work-cycle latest --work-cycle-full
```

Useful options:

```text
--work-cycle-project eidolon
--work-cycle-steps 3
--dry-run
--no-ai-work-cycle
--no-work-cycle-seed
--no-work-cycle-followups
--approve-work-cycle-actions
--work-cycle-full
```

Use `--approve-work-cycle-actions` carefully. It allows approval-required work items during that cycle run, which is exactly the sort of flag that deserves adult supervision and maybe a chair thrown under the doorknob.

## New dashboard behavior

Start the dashboard:

```powershell
python conscious_agent/main.py --dashboard
```

Then open:

```text
http://127.0.0.1:8765/work-cycle
```

The Work Cycle page includes:

- a form to run a supervised work cycle
- dry-run enabled by default
- max step control
- optional local AI toggle
- seed-if-empty toggle
- patch-follow-up toggle
- approval-required execution toggle
- latest work cycle summary
- saved work cycle table
- work-cycle detail view

## New API endpoints

List saved work cycles:

```text
GET /api/work-cycles
```

Get one saved cycle:

```text
GET /api/work-cycles/{id}
```

Run a supervised cycle:

```text
POST /api/work-cycles/run
```

Example JSON body:

```json
{
  "project_id": "eidolon",
  "max_steps": 1,
  "dry_run": true,
  "use_ai": false,
  "seed_if_empty": true,
  "auto_create_patch_followups": true,
  "approve_work_execution": false
}
```

## Safety notes

- Dry-run mode saves a cycle record but does not execute a work item.
- Non-dry-run mode still uses `work_queue_executor.py`.
- Medium/high-risk work remains blocked unless explicitly approved for the cycle.
- Patch application is not silently approved.
- Patch follow-up apply items are still created as approval-required work.
- Command execution still uses `command_runner.py` validation.
- The cycle is capped at 10 steps per run.

## Tested in this patch

- `python3 -m py_compile conscious_agent/*.py`
- `python3 conscious_agent/main.py --work-cycle --dry-run --no-ai-work-cycle --work-cycle-full`
- `python3 conscious_agent/main.py --work-cycle --work-cycle-steps 1 --no-ai-work-cycle --work-cycle-full`
- local API dispatch for `GET /api/work-cycles`
- local API dispatch for `POST /api/work-cycles/run`
- dashboard rendering for `/work-cycle`
- dashboard rendering for `/work-queue`

Temporary test queue/memory/cycle records were cleaned before packaging. The zip should not come preloaded with my lab-rat work items.

## Next likely step

The next milestone should be **v5.1 - Cycle Approval Inbox Integration**. That should let the work cycle create explicit approval requests for blocked/risky queue items instead of merely blocking them and staring at Marcus like an unpaid intern.

---

# Eidolon v4.9 - Queue-to-Patch Integration

v4.9 connects the self-directed work queue to the patch proposal system. v4.8 made the queue visible in the dashboard. v4.9 lets a queue item intentionally generate a patch proposal, then links the patch back to the work item so the chain is visible instead of buried in separate IDs like some cursed scavenger hunt.

This is still supervised. v4.9 creates patch proposals and follow-up queue items. It does not remove review, approval, dry-run, apply, test, or rollback safety gates.

## What changed in v4.9

- Added `conscious_agent/work_queue_patch_bridge.py`
- Updated `conscious_agent/work_queue_executor.py`
- Updated `conscious_agent/main.py`
- Updated `conscious_agent/api_server.py`
- Updated `conscious_agent/dashboard.py`
- Updated `README_NEXT_STEPS.md`
- Updated dashboard/API version strings to `4.9`
- Added queue-to-patch metadata linking:
  - work items store `patch_id`, `patch_status`, `patch_target_file`, and `patch_request`
  - patch proposals store `work_item_id`, `work_item_relationship`, and `linked_work_items`
- Added dashboard support for creating patch work items from `/work-queue`
- Added dashboard work-item controls for patch-generation queue items
- Added dashboard patch follow-up controls from `/patches` and patch detail pages
- Added API routes for patch work items and patch follow-ups
- Added CLI helpers for queueing patch work and creating patch follow-ups

## New CLI commands

Queue a patch-generation work item:

```powershell
python conscious_agent/main.py --queue-patch conscious_agent/dashboard.py "Add a safer dashboard queue control."
```

Dry-run patch generation from a work item:

```powershell
python conscious_agent/main.py --suggest-patch-for-work work_YOUR_ID --dry-run
```

Generate and link a patch proposal from a work item:

```powershell
python conscious_agent/main.py --suggest-patch-for-work work_YOUR_ID
```

Create review/apply/test follow-up work items for a patch:

```powershell
python conscious_agent/main.py --create-patch-followups patch_YOUR_ID
```

## New dashboard behavior

Open the dashboard:

```powershell
python conscious_agent/main.py --dashboard
```

Then open:

```text
http://127.0.0.1:8765/work-queue
```

The Work Queue page now includes a **Create Patch Work Item** form. A queued patch item carries metadata like this:

```json
{
  "action_type": "suggest_patch",
  "target_file": "conscious_agent/dashboard.py",
  "patch_target_file": "conscious_agent/dashboard.py",
  "patch_request": "Describe the change here.",
  "patch_status": "queued"
}
```

Executing that item through the work queue creates a proposed patch and stores the patch ID back on the work item.

The Patches page now shows linked work items when available and can create follow-up queue items:

- review the patch
- apply the patch after approval
- run tests after applying the patch

## New API endpoints

Create a patch-generation work item:

```text
POST /api/work-queue/patch-request
```

Generate a patch proposal from a work item:

```text
POST /api/work-queue/{id}/suggest-patch
```

Create follow-up work items for a patch:

```text
POST /api/patches/{id}/create-followups
```

## Safety notes

- Patch generation still requires local AI unless running a dry run.
- Patch proposals are still read-only until explicitly applied.
- Applying a patch still uses the existing patch applier checks.
- Follow-up apply items are created as approval-required work.
- The queue does not bypass command validation, patch validation, rollback validation, or approval gates.

## Next likely step

v5.0 should become the **Supervised Autonomous Work Cycle**:

```text
observe project
→ create work items
→ generate patch proposals
→ create follow-ups
→ request approval for risky apply steps
→ run tests
→ review results
→ continue safely
```

That is the point where Eidolon starts feeling less like a toolbelt and more like a tiny supervised developer with a clipboard. Which is both charming and faintly concerning.

---

# Eidolon v4.8 - Dashboard Work Queue Panel

v4.8 gives the self-directed work queue a dashboard page. v4.6 created the queue, v4.7 added the conservative executor, and v4.8 finally makes the whole thing visible from the browser so Marcus does not have to interrogate command output like a cave detective with a PowerShell prompt.

This is still supervised autonomy. The dashboard can create work items, dry-run safe work, execute low-risk queue items, mark work done, block work, or cancel work. It does not bypass the v4.7 executor safety gate. Medium-risk, high-risk, or approval-required work is still blocked before automatic execution.

## Documentation rule

Every future Eidolon code change should update this README or the appropriate project documentation in the same patch. If the code changes and the README does not, assume the patch is incomplete. This rule remains active after v4.8.

## What changed in v4.8

- Updated `conscious_agent/dashboard.py`
- Updated `conscious_agent/api_server.py`
- Updated `README_NEXT_STEPS.md`
- Updated dashboard version strings to `4.8`
- Updated API version strings to `4.8`
- Added dashboard navigation item:
  - `/work-queue`
- Added dashboard Work Queue page with:
  - queue summary cards
  - create-work-item form
  - next recommended work item
  - open work item table
  - all work item table
- Added dashboard work item detail view:
  - `/detail?kind=work_item&id=work_YOUR_ID&full=1`
- Added dashboard controls for work items:
  - dry-run
  - execute
  - mark done
  - block
  - cancel
- Added overview Work Queue card
- Added overview quick link to the Work Queue page
- Added overview quick action:
  - dry-run next work
- Added live dashboard status counts for:
  - `work_queue_total`
  - `work_queue_pending`
  - `work_queue_active`
  - `work_queue_blocked`
  - `work_queue_done`
  - `work_queue_failed`
  - `work_queue_approval_required`
- Added API support for work queue visibility and controls

## New dashboard route

Start the dashboard:

```bash
python conscious_agent/main.py --dashboard
```

Then open:

```text
http://127.0.0.1:8765/work-queue
```

The page shows queue state, next recommended work, and controls for work items. It is the browser-facing control panel for the v4.6/v4.7 queue system.

## New dashboard actions

The dashboard now supports these internal form actions:

```text
dashboard_add_work_item
work_queue_execute_next
work_queue_execute
work_queue_done
work_queue_cancel
work_queue_block
```

These actions route through the existing `work_queue.py` and `work_queue_executor.py` modules. The dashboard does not directly edit files or run commands behind the executor’s back, because that would be how the little gremlin earns a criminal record.

## New API endpoints

Read queue summary:

```bash
curl http://127.0.0.1:8765/api/work-queue/summary
```

List queue items:

```bash
curl http://127.0.0.1:8765/api/work-queue
```

Create a queue item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue \
  -H "Content-Type: application/json" \
  -d '{"title":"Review conscious_agent/dashboard.py","description":"Review the new work queue panel.","project_id":"eidolon","priority":8,"risk":"low"}'
```

Dry-run next work item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue/next/dry-run \
  -H "Content-Type: application/json" \
  -d '{"use_ai":false}'
```

Execute next safe work item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue/next/execute \
  -H "Content-Type: application/json" \
  -d '{"use_ai":true}'
```

Dry-run one item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue/work_YOUR_ID/dry-run \
  -H "Content-Type: application/json" \
  -d '{"use_ai":false}'
```

Execute one safe item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue/work_YOUR_ID/execute \
  -H "Content-Type: application/json" \
  -d '{"use_ai":true}'
```

Mark, block, or cancel one item:

```bash
curl -X POST http://127.0.0.1:8765/api/work-queue/work_YOUR_ID/done
curl -X POST http://127.0.0.1:8765/api/work-queue/work_YOUR_ID/block \
  -H "Content-Type: application/json" \
  -d '{"reason":"Waiting on Marcus approval."}'
curl -X POST http://127.0.0.1:8765/api/work-queue/work_YOUR_ID/cancel
```

## Existing queue commands still work

Show queue summary:

```bash
python conscious_agent/main.py --work-queue summary
```

Add a work item:

```bash
python conscious_agent/main.py --work-queue add "Inspect dashboard.py" --description "Review conscious_agent/dashboard.py for syntax issues." --project eidolon --priority 8 --risk low --source user
```

Dry-run next safe item:

```bash
python conscious_agent/main.py --execute-work --dry-run
```

Execute next safe item:

```bash
python conscious_agent/main.py --execute-work
```

## Good v4.8 test flow

```bash
python conscious_agent/main.py --work-queue summary
python conscious_agent/main.py --work-queue add "Review conscious_agent/dashboard.py" --description "Review conscious_agent/dashboard.py for the v4.8 Work Queue page." --project eidolon --priority 8 --risk low --source user
python conscious_agent/main.py --execute-work --dry-run --execute-work-project eidolon
python conscious_agent/main.py --dashboard
```

Then visit:

```text
http://127.0.0.1:8765/work-queue
```

## Safety

v4.8 does not loosen the v4.7 safety rules. Dashboard execution still uses `work_queue_executor.py`. Low-risk, non-approval work can be dry-run or executed. Medium/high-risk or approval-required work remains blocked unless future approval plumbing explicitly handles it.

## Next likely step

v4.9 should probably be **Queue-to-Patch Integration**:

- let work items intentionally create patch proposals
- show created patch IDs on the work item detail page
- link queue items to patch proposals
- let dashboard move from work item → patch proposal → approval → test review
- keep apply/rollback approval-gated

v4.8 gave the queue a face. v4.9 should connect that face to the patch pipeline without letting it chew through the codebase like an unsupervised termite with a keyboard.

---

# Previous README: Eidolon v4.7 - Work Queue Executor

v4.7 adds a conservative execution layer for the self-directed work queue. v4.6 gave Eidolon a place to store and rank work items; v4.7 lets it pull the next safe item, classify it, run an appropriate existing helper when possible, and update the item status afterward.

This is still supervised autonomy. Low-risk, non-approval work can be dry-run or executed. Medium-risk, high-risk, or approval-required items are blocked instead of being run automatically, because letting a local agent freestyle on your filesystem is how machines earn haunted-house reputations.

## Documentation rule

Starting with v4.7, every future Eidolon code change should update this README or the appropriate project documentation in the same patch. If the code changes and the README does not, assume the patch is incomplete. Tiny rule, large reduction in future archaeological suffering.

## What changed in v4.7

- Added `conscious_agent/work_queue_executor.py`
- Updated `conscious_agent/main.py`
- Added work execution commands:
  - `--execute-work`
  - `--execute-work-id`
  - `--execute-work-project`
  - `--dry-run` with work execution
  - `--no-ai-work-executor` fallback behavior
- Added conservative work item classification:
  - `review_file`
  - `run_command`
  - `suggest_patch`
  - `test_project`
  - `dashboard_note`
  - `manual`
- Added safety gating for queue execution
- Blocks medium/high-risk or approval-required queue items before execution
- Updates queue item status during execution:
  - `pending` → `active`
  - `active` → `done`
  - `active` → `failed`
  - `pending`/`active` → `blocked`
- Stores execution results back onto the work item
- Keeps execution dry-runnable before making changes
- Cleaned a duplicate timestamp assignment in `work_queue.py`

## What changed in v4.6

- Added `conscious_agent/work_queue.py`
- Added persistent queue storage:
  - `data/work_queue/work_items.json`
- Added work queue commands:
  - `add`
  - `list`
  - `show`
  - `next`
  - `update`
  - `done`
  - `fail`
  - `block`
  - `delete`
  - `summary`
- Added work item fields:
  - `id`
  - `title`
  - `description`
  - `project_id`
  - `status`
  - `priority`
  - `risk`
  - `source`
  - `requires_approval`
  - `created_at`
  - `updated_at`
  - `started_at`
  - `completed_at`
  - `blocked_reason`
  - `result`
  - `metadata`
- Added queue summary and next-item selection
- Added basic approval logic for medium/high-risk tasks

## New v4.7 commands

Dry-run the next safe pending work item:

```bash
python conscious_agent/main.py --execute-work --dry-run
```

Execute the next safe pending work item:

```bash
python conscious_agent/main.py --execute-work
```

Dry-run a specific work item:

```bash
python conscious_agent/main.py --execute-work-id work_YOUR_ID_HERE --dry-run
```

Execute work for a specific project:

```bash
python conscious_agent/main.py --execute-work --execute-work-project eidolon
```

Use the non-AI fallback executor path:

```bash
python conscious_agent/main.py --execute-work --dry-run --no-ai-work-executor
```

## New v4.6 queue commands

Show queue summary:

```bash
python conscious_agent/main.py --work-queue summary
```

Add a work item:

```bash
python conscious_agent/main.py --work-queue add "Inspect dashboard.py for syntax issues" --description "Review dashboard.py and identify syntax or rendering problems." --project eidolon --priority 8 --risk low --source user
```

List queue items:

```bash
python conscious_agent/main.py --work-queue list --full
```

Show the next queue item:

```bash
python conscious_agent/main.py --work-queue next --full
```

Mark an item done:

```bash
python conscious_agent/main.py --work-queue done work_YOUR_ID_HERE --result "Completed."
```

Block an item:

```bash
python conscious_agent/main.py --work-queue block work_YOUR_ID_HERE --reason "Requires approval before execution."
```

## Good v4.7 test flow

```bash
python conscious_agent/main.py --work-queue summary
python conscious_agent/main.py --work-queue add "Review README_NEXT_STEPS.md" --description "Inspect the README for outdated version notes." --project eidolon --priority 7 --risk low --source user
python conscious_agent/main.py --execute-work --dry-run --execute-work-project eidolon
python conscious_agent/main.py --work-queue list --full
```

## Safety

v4.7 only executes low-risk, non-approval queue items by default. Anything marked medium risk, high risk, or approval-required gets blocked before execution. Dry-run mode should be used first when testing a new work item type.

## Next likely step

v4.8 should probably be **Dashboard Work Queue Panel**:

- show pending, active, blocked, failed, and done work items
- show next recommended work item
- add queue controls from the dashboard
- dry-run or execute safe items from the dashboard
- make blocked/approval-required items visible
- connect queue status into the dashboard overview

v4.6 gave Eidolon a queue. v4.7 gave it a cautious hand. v4.8 should give you a dashboard view so you do not have to interrogate JSON files like a cave detective.

---

# Previous README: Eidolon v4.5 - Desktop Guided Onboarding Wizard

v4.5 turns the v4.4 setup reports into a guided onboarding runbook. Instead of merely saying “something is wrong” and dropping a diagnostic brick on your foot, Eidolon now orders the setup issues into steps, shows the next recommended action, lists commands to copy, and links you to the relevant dashboard pages.

Safety stays boring on purpose: onboarding is advisory. It saves onboarding runs and setup reports, but it does **not** install packages, change settings, start services, approve actions, apply patches, rollback files, or edit project files.

## What changed

- Added `desktop_onboarding_wizard.py`
- Added `data/onboarding_runs/`
- Added CLI commands:
  - `--onboarding`
  - `--onboarding-full`
  - `--onboarding-use-latest-setup`
  - `--list-onboarding-runs`
  - `--show-onboarding-run`
- Added dashboard `/onboarding` page
- Added onboarding run detail pages
- Added dashboard Onboarding nav item
- Added onboarding quick action on Overview
- Added onboarding reports to Activity
- Added API routes:
  - `GET /api/onboarding`
  - `GET /api/onboarding/latest`
  - `POST /api/onboarding/run`
- Added onboarding counts/latest status to `/api/status`
- Added desktop buttons:
  - Open Onboarding
  - Onboarding
- Added optional tray menu item:
  - Open Onboarding
- Added settings:
  - `desktop_onboarding_check_on_start`
  - `onboarding_refresh_setup_default`
- Updated API version to 4.5
- Updated dashboard version to 4.5
- Updated desktop shell/tray versions to 4.5
- Updated `settings_version` to 4.5
- Updated command whitelist for safe onboarding commands
- Refreshed project metadata
- Refreshed `project_index.json`

## New commands

Run onboarding and create a fresh setup report first:

```bash
python conscious_agent/main.py --onboarding
```

Run onboarding with full setup/report details:

```bash
python conscious_agent/main.py --onboarding --onboarding-full
```

Build onboarding from the latest setup report instead of creating a fresh one:

```bash
python conscious_agent/main.py --onboarding --onboarding-use-latest-setup
```

List saved onboarding runs:

```bash
python conscious_agent/main.py --list-onboarding-runs
```

Show latest onboarding run:

```bash
python conscious_agent/main.py --show-onboarding-run latest
```

Show full latest onboarding run:

```bash
python conscious_agent/main.py --show-onboarding-run latest --onboarding-full
```

## Dashboard

Start the dashboard:

```bash
python conscious_agent/main.py --dashboard
```

Open:

```text
http://127.0.0.1:8765/onboarding
```

The page shows:

- latest onboarding status
- next recommended step
- guided step cards
- commands to copy
- relevant links
- saved onboarding run table
- full detail pages

## API

With the dashboard running:

```bash
curl http://127.0.0.1:8765/api/onboarding
curl http://127.0.0.1:8765/api/onboarding/latest
curl -X POST http://127.0.0.1:8765/api/onboarding/run
```

Use latest setup instead of a fresh setup check:

```bash
curl -X POST http://127.0.0.1:8765/api/onboarding/run -H "Content-Type: application/json" -d "{\"refresh_setup\":false}"
```

Standalone API works too:

```bash
python conscious_agent/main.py --api-server
curl http://127.0.0.1:8766/api/onboarding/latest
```

## Desktop shell

Run:

```bash
python conscious_agent/main.py --desktop
```

New desktop buttons:

```text
Open Onboarding
Onboarding
```

`Open Onboarding` opens the dashboard onboarding page. `Onboarding` runs the guided wizard and prints the runbook in the desktop log.

## New settings

```bash
python conscious_agent/main.py --get-setting desktop_onboarding_check_on_start
python conscious_agent/main.py --get-setting onboarding_refresh_setup_default
```

Defaults:

```text
desktop_onboarding_check_on_start: false
onboarding_refresh_setup_default: true
```

Enable onboarding when the desktop shell opens:

```bash
python conscious_agent/main.py --set-setting desktop_onboarding_check_on_start true
```

## What onboarding checks turn into steps

- broken project layout
- unwritable data folder
- missing required packages
- missing Tkinter
- missing optional tray packages
- unsafe non-local host settings
- Ollama not running
- configured models missing
- dashboard/API port and service state
- first-use flow once setup looks ready

## Good test flow

```bash
python conscious_agent/main.py --onboarding
python conscious_agent/main.py --show-onboarding-run latest --onboarding-full
python conscious_agent/main.py --dashboard
```

Then open:

```text
http://127.0.0.1:8765/onboarding
http://127.0.0.1:8765/api/onboarding/latest
```

API test:

```bash
curl -X POST http://127.0.0.1:8765/api/onboarding/run
```

Desktop test:

```bash
python conscious_agent/main.py --desktop
```

Then click:

```text
Onboarding
Open Onboarding
```

## Safety

v4.5 is a guided setup/onboarding layer. It saves runbooks and suggests commands. It does not install packages, edit settings automatically, change firewall rules, expose ports, approve requests, apply patches, rollback files, or run arbitrary commands. It points at the mess with a clipboard, which is somehow progress.

## Next likely step

v4.6 should probably be **Desktop Command Clipboard Helpers**:

- copy recommended onboarding commands from the desktop shell
- copy setup/package/Ollama commands from dashboard cards
- add safer command preview cards
- keep installation and risky machine changes manual

v4.5 tells you what to do. v4.6 should make copying the exact commands less annoying, because apparently typing is where human morale goes to die.
