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
