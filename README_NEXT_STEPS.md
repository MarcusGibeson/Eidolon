# Eidolon v20.0 - Verified Release Package Loop

v20.0 bundles the v19.1 through v20.0 release-packaging roadmap into one packaged release. Eidolon can now verify release metadata, classify package contents, generate file checksums, create release notes and handoff reports, dry-run a guarded zip builder, verify extracted packages, audit the approval-to-package chain, and run one bounded verified release package loop. The machine can finally prepare its own suitcase without packing a live approval grenade, which is a touching little milestone in robot maturity.

## What changed in v20.0

- Added `conscious_agent/release_packaging.py`
  - v19.1 release manifest integrity
  - v19.2 package file inventory
  - v19.3 package checksum builder
  - v19.4 release notes generator
  - v19.5 release handoff report
  - v19.6 guarded zip builder
  - v19.7 install/unzip verification
  - v19.9 release pipeline audit
  - v20.0 verified release package loop
- Updated `conscious_agent/approval_release_workflow.py`
  - bumped approval/release workflow metadata for the v20 package line
  - kept validated apply bound to the exact reviewed artifact manifest
  - added operator-facing binding text/print helper for validated approval manifests
  - review integrity now explains how to refresh/save the review bundle when legitimate artifact drift blocks approval
- Updated `conscious_agent/release_pipeline.py`
  - release readiness no longer hard-codes stale v15.0 checks
  - readiness now compares README, settings, and project metadata to the current configured version
- Updated `conscious_agent/main.py`
  - added `--bind-validated-approval`
  - added `--refresh-ai-patch-review-bundle`
  - added v19.1-v20.0 release package CLI commands
- Updated `conscious_agent/api_server.py`
  - API version is now `20.0`
  - added read-only GET preview endpoints for v20 release package reports
  - added POST-only mutation endpoints for refreshing the review bundle, binding validated approval, and guarded release zip/package operations
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `20.0`
  - `/code-patches` now includes refresh/save review bundle and bind validated approval controls
  - added `/release-package` for v20 manifest, inventory, checksum, notes, handoff, zip, unzip, audit, and verified loop reports
- Updated `conscious_agent/command_runner.py`
  - whitelisted the v20 release packaging commands
- Updated `tools/smoke_check.py`
  - validates the v20 release packaging module and report shapes
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v20.0`
  - `data/projects.json` marks the active Eidolon project as v20.0
  - workspace project metadata marks the current milestone as v20.0

## Findings fixed during v20.0

- The validated real-apply path is no longer effectively unreachable from normal operator surfaces. Use `--bind-validated-approval`, POST `/api/code-patches/bind-validated-approval`, or the `/code-patches` dashboard control after approval and review-bundle refresh.
- Review integrity drift now has an obvious repair path: refresh/save the current review bundle before approval with `--refresh-ai-patch-review-bundle` or POST `/api/code-patches/refresh-review-bundle`.
- Release readiness no longer assumes `last_updated_for == v15.0`; it uses the current settings/project version markers.

## Post-review hardening added after v20.0

- Release package inventory now excludes private and runtime-heavy state folders by default, including chat actions, diagnostics, maintenance scans, notifications, patch workspaces, patches, session plans, stable loops, test reports, watch reports, work cycles, workspace runtime state, `memories.json`, and live approval state.
- The verified package loop now reuses manifest, inventory, checksum, handoff, zip, and audit reports inside a single run instead of rebuilding the same full-tree reports repeatedly.
- The legacy release package metadata path now derives `Eidolon_v{current_version}.zip` from settings instead of falling back to `Eidolon_v15_0.zip`.

## Version-by-version roadmap completed

### v19.1 - Release Manifest Integrity

Added release manifest consistency checks through:

```bash
python conscious_agent/main.py --release-manifest-integrity
```

The report verifies settings, project metadata, README section, dashboard version, API version, approval/review artifacts, release readiness, and package plan consistency. It exists to stop mismatched version ghosts from crawling back into the dashboard wearing old badges.

### v19.2 - Package File Inventory

Added package inventory through:

```bash
python conscious_agent/main.py --package-inventory
```

The inventory classifies included and excluded files. It excludes `.git`, `.venv`, `__pycache__`, `.pyc`, logs, nested zips, generated package reports, live approval state, private memory files, and runtime report folders so release zips are source/handoff packages instead of snapshots of the operator's local history.

### v19.3 - Package Checksum Builder

Added checksum generation through:

```bash
python conscious_agent/main.py --package-checksums
```

The report generates SHA-256 hashes and sizes for included release files so the handoff package contents can be verified instead of trusted because the zip looked polite.

### v19.4 - Release Notes Generator

Added release notes through:

```bash
python conscious_agent/main.py --release-notes
```

The report summarizes major changes, new commands, known warnings, and README release content for the packaged version.

### v19.5 - Release Handoff Report

Added final handoff reporting through:

```bash
python conscious_agent/main.py --release-handoff-report
```

The handoff report includes package name, manifest status, checksum status, README status, approval state, known warnings, tested commands, and recommended first commands after unzip.

### v19.6 - Guarded Zip Builder

Added guarded zip builder through:

```bash
python conscious_agent/main.py --build-release-zip --dry-run
```

Real zip writing requires explicit confirmation:

```bash
python conscious_agent/main.py --build-release-zip --approve-controlled-self-build
```

The builder runs manifest, inventory, checksum, and handoff prechecks before writing. Dry-runs do not create archives. One small victory for not producing mystery zips.

### v19.7 - Install / Unzip Verification

Added unzip verification through:

```bash
python conscious_agent/main.py --verify-release-unzip
```

If a guarded zip exists, Eidolon extracts it to a temporary verification folder and checks for required files, neutral approval state, and portable package structure. If no guarded zip exists yet, the report stays as a warning instead of pretending there was something to verify.

### v19.8 - Release Dashboard Page

Added `/release-package` to the dashboard. It shows manifest integrity, package inventory, checksums, release notes, handoff report, zip readiness, unzip verification, pipeline audit, and the verified package loop. The page uses read-only GET previews and POST-only mutation controls because apparently that commandment needed another marble tablet.

### v19.9 - Release Pipeline Audit

Added release pipeline audit through:

```bash
python conscious_agent/main.py --release-pipeline-audit
```

The audit checks the approval-to-package chain: review bundle, validated manifest binding, approval readiness, post-apply review, release readiness, manifest integrity, checksums, handoff, and zip builder readiness.

### v20.0 - Verified Release Package Loop

Added the bounded package workflow through:

```bash
python conscious_agent/main.py --verified-release-package-loop
```

The loop runs manifest integrity, inventory, checksums, release notes, handoff report, pipeline audit, guarded zip dry-run, unzip verification, then stops.

Real zip creation remains explicit:

```bash
python conscious_agent/main.py --verified-release-package-loop --approve-controlled-self-build
```

## New CLI commands

```bash
python conscious_agent/main.py --bind-validated-approval
python conscious_agent/main.py --refresh-ai-patch-review-bundle
python conscious_agent/main.py --release-manifest-integrity
python conscious_agent/main.py --package-inventory
python conscious_agent/main.py --package-checksums
python conscious_agent/main.py --release-notes
python conscious_agent/main.py --release-handoff-report
python conscious_agent/main.py --build-release-zip --dry-run
python conscious_agent/main.py --verify-release-unzip
python conscious_agent/main.py --release-pipeline-audit
python conscious_agent/main.py --verified-release-package-loop
```

## New API routes

Read-only previews:

```text
GET /api/release/manifest-integrity
GET /api/release/package-inventory
GET /api/release/package-checksums
GET /api/release/notes
GET /api/release/handoff
GET /api/release/build-zip
GET /api/release/verify-unzip
GET /api/release/pipeline-audit
GET /api/release/verified-package-loop
```

Mutation routes:

```text
POST /api/code-patches/refresh-review-bundle
POST /api/code-patches/bind-validated-approval
POST /api/release/manifest-integrity
POST /api/release/package-inventory
POST /api/release/package-checksums
POST /api/release/notes
POST /api/release/handoff
POST /api/release/build-zip
POST /api/release/verify-unzip
POST /api/release/pipeline-audit
POST /api/release/verified-package-loop
```

Real zip writing requires confirmation through POST or the CLI approval flag. GET routes remain preview-only and read-only.

## Dashboard

Start the dashboard:

```bash
python conscious_agent/main.py --dashboard
```

Open:

```text
http://127.0.0.1:8765/code-patches
http://127.0.0.1:8765/release-package
```

`/code-patches` now has controls for refreshing the saved review bundle and binding an approved draft to the validated AI manifest. `/release-package` shows the v20 release packaging reports.

## Verification commands

Recommended checks:

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --bind-validated-approval
python conscious_agent/main.py --release-manifest-integrity
python conscious_agent/main.py --package-inventory
python conscious_agent/main.py --package-checksums
python conscious_agent/main.py --release-notes
python conscious_agent/main.py --release-handoff-report
python conscious_agent/main.py --build-release-zip --dry-run
python conscious_agent/main.py --verify-release-unzip
python conscious_agent/main.py --release-pipeline-audit
python conscious_agent/main.py --verified-release-package-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python -u tools/smoke_check.py
```

## Safety notes

- The package ships with neutral approval state.
- Dry-runs do not write release zips.
- Real zip writing requires explicit approval.
- Package inventory excludes live approval state, generated release reports, `.venv`, cache folders, logs, pyc files, and nested zips.
- The validated AI apply path still requires exact artifact-manifest binding before real apply.

## Next likely step

v20.1 should probably start the **Release Installation and Upgrade Workflow** phase:

- verify an extracted package against checksums
- compare installed version to release manifest
- provide upgrade/restore instructions
- improve dashboard release handoff controls
- add package provenance checks

v20.0 makes the release package verifiable. v20.1 should make installing or replacing a local project folder less like swapping organs by candlelight.

---

# Eidolon v19.0 - Approval-to-Release Loop

v19.0 bundles the v18.1 through v19.0 approval-to-release roadmap into one packaged release. Eidolon can now collect validated AI patch artifacts into one authoritative review bundle, verify bundle integrity, decide approval readiness, keep an approval ledger, dry-run or guard real validated AI applies, compare post-apply state, prepare package handoff metadata, and run one bounded approval-to-release loop. The robot now needs receipts before touching anything, which is annoying until you remember files can be destroyed.

## What changed in v19.0

- Added `conscious_agent/approval_release_workflow.py`
  - v18.1 AI patch review bundle
  - v18.2 review bundle integrity check
  - v18.3 approval-ready gate
  - v18.5 human approval ledger
  - v18.6 apply validated AI patch
  - v18.7 post-apply review comparison
  - v18.9 package build plan
  - v19.0 approval-to-release loop
- Updated `conscious_agent/validated_ai_patch_loop.py`
  - real approved apply paths now require a validated patch approval manifest, not only the older draft approval binding
- Updated `conscious_agent/main.py`
  - added CLI commands for the v18.1-v19.0 approval-to-release workflow
- Updated `conscious_agent/api_server.py`
  - API version is now `19.0`
  - added read-only GET preview endpoints for v19 review/release reports
  - added POST-only mutation endpoints for validated AI apply and approval-to-release loop
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `19.0`
  - `/code-patches` now shows v18/v19 review, integrity, approval, apply, post-apply, and package reports instead of being stuck around v17
  - added `/release-review` as a release control surface
- Updated `conscious_agent/command_runner.py`
  - whitelisted the v18.1-v19.0 workflow commands
- Updated `tools/smoke_check.py`
  - validates `approval_release_workflow.py` report shapes in-process
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v19.0`
  - `data/projects.json` updates stale `current_milestone` and `version` values to v19.0
  - `data/workspaces/active_project.json` and workspace project metadata mark the current workspace state as v19.0

## Findings fixed during v19.0

- Real validated AI apply now requires a validated patch approval manifest containing hashes for the exact reviewed artifact set: objective refinement, context ranking, safety envelope, validation, simulation, review score, recovery plan, release artifact, audit trail, and related bundle data.
- Project metadata no longer reports stale v14/v15 milestone/version values while the API, settings, and README report v19.0.
- `/code-patches` no longer labels itself around v17 or points release package metadata at `Eidolon_v17_0.zip`.

## Version-by-version roadmap completed

### v18.1 - AI Patch Review Bundle

Added one authoritative review bundle through:

```bash
python conscious_agent/main.py --ai-patch-review-bundle
```

The bundle includes objective refinement, ranked code context, safety envelope, generated edits validation, simulation, test stub plan, review score, recovery plan, approval state, release readiness preview, and recommended next action.

### v18.2 - Review Bundle Integrity Check

Added integrity checks through:

```bash
python conscious_agent/main.py --ai-patch-review-integrity
```

The integrity check compares saved and current validated AI patch artifact hashes so review and approval cannot quietly drift apart. Tiny paperwork. Large safety value.

### v18.3 - Approval-Ready Gate

Added approval readiness through:

```bash
python conscious_agent/main.py --approval-ready
```

The gate checks review bundle presence, bundle integrity, validation, simulation, review score, test planning, README impact, and stale approval state before the system asks for human approval.

### v18.4 - Dashboard Approval Workflow

Updated `/code-patches` to show approval readiness, review bundle summary, integrity status, generated edit/simulation status, test planning, review score, recovery state, dry-run apply controls, and package/release links. GET routes remain read-only because apparently we need to keep saying that until the APIs behave.

### v18.5 - Human Approval Ledger

Added approval ledger reporting through:

```bash
python conscious_agent/main.py --approval-ledger
```

The ledger records approval status, patch id, draft id, request id, artifact hashes, consumed state, and accepted risk against the current validated patch manifest.

### v18.6 - Apply Validated AI Patch

Added validated AI apply through:

```bash
python conscious_agent/main.py --apply-validated-ai-patch --dry-run
```

Real apply remains blocked unless the review bundle passes, the approval-ready gate passes, the approval is unconsumed, and the approval includes the exact validated patch manifest. Dry-runs never overwrite real apply pointers.

### v18.7 - Post-Apply Review Comparison

Added post-apply review through:

```bash
python conscious_agent/main.py --post-apply-review
```

The report compares the approved manifest, apply report, dry-run separation, transaction status, rollback state, and release readiness.

### v18.8 - Dashboard Release Review

Added `/release-review` to show latest review bundle, integrity, approval readiness, apply preview, post-apply review, release readiness, package plan, audit trail, and known warnings. The dashboard is becoming a control center, or at least a prettier pile of guardrails.

### v18.9 - Package Builder Command

Added package build planning through:

```bash
python conscious_agent/main.py --package-build-plan
```

The plan lists version, source root, included roots, excluded patterns, README sections, verification commands, known warnings, release readiness, and recommended zip filename.

### v19.0 - Approval-to-Release Loop

Added the bounded approval-to-release loop through:

```bash
python conscious_agent/main.py --approval-to-release-loop
```

The loop loads the review bundle, checks integrity, checks approval readiness, records the approval ledger, dry-runs or applies the validated AI patch, runs post-apply review, semantic checks, release readiness, package build planning, audit trail, learning notes, then stops. One project. One patch. One approval. One loop. Then it stops, because that is how repositories stay out of therapy.

## Core verification commands

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --ai-patch-review-bundle
python conscious_agent/main.py --ai-patch-review-integrity
python conscious_agent/main.py --approval-ready
python conscious_agent/main.py --approval-ledger
python conscious_agent/main.py --apply-validated-ai-patch --dry-run
python conscious_agent/main.py --post-apply-review
python conscious_agent/main.py --package-build-plan
python conscious_agent/main.py --approval-to-release-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python -u tools/smoke_check.py
```

## Safety notes

- GET endpoints are preview/read-only.
- Real validated AI apply is POST/CLI-confirmation gated.
- Real validated AI apply requires a manifest bound to the exact reviewed artifact hashes.
- Dry-run apply writes separate dry-run reports and does not replace real apply pointers.
- Packaged approval state should stay neutral; do not ship a zip with a live unconsumed approval.
- `chromadb` and Ollama warnings remain environment warnings unless the local setup is expected to provide them.

## Next likely step

v19.1 should probably start **Release Packaging Writer / Handoff Builder**:

- create a guarded internal zip builder
- use the package build plan as the source of truth
- verify included/excluded file lists
- attach release audit metadata
- prevent live approvals from shipping inside package state
- keep README and package metadata locked together

Right now v19.0 can plan and verify the handoff. v19.1 should make the actual package writing less dependent on a human remembering which files not to throw into the digital suitcase.

---

# Eidolon v18.0 - Validated AI Code Patch Loop

v18.0 bundles the v17.1 through v18.0 validation-centered AI code patch roadmap into one packaged release. Eidolon can now refine patch objectives, rank code context, wrap prompts in a safety envelope, validate generated edits, simulate patch effects without source writes, plan test stubs, score review readiness, create recovery plans, and run one bounded validated AI code patch loop. The model may suggest a patch, but it still has to pass through the little turnstile of reality first.

## What changed in v18.0

- Added `conscious_agent/validated_ai_patch_loop.py`
  - v17.1 patch objective refinement
  - v17.2 code context ranking
  - v17.3 prompt safety envelope
  - v17.4 generated patch validator
  - v17.5 patch simulation runner
  - v17.6 test stub planner
  - v17.7 patch review scoring
  - v17.9 patch failure recovery plan
  - v18.0 validated AI code patch loop
- Updated `conscious_agent/main.py`
  - added CLI commands for the v17.1-v18.0 validated AI patch pipeline
- Updated `conscious_agent/api_server.py`
  - API version is now `18.0`
  - added read-only GET preview endpoints for validated AI patch reports
  - added POST endpoints for saving validated AI patch review artifacts
  - real apply paths remain POST-only and require explicit confirmation
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `18.0`
  - upgraded `/code-patches` to show objective refinement, ranked context, safety envelope, validation, simulation, test stubs, review score, recovery plan, and validated loop state
- Updated `conscious_agent/command_runner.py`
  - whitelisted the v17.1-v18.0 validated AI patch review commands
- Updated `tools/smoke_check.py`
  - validates `validated_ai_patch_loop.py` report shapes in-process
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v18.0`
  - `data/projects.json` includes v18 goals and description updates
  - workspace metadata marks the Eidolon project as version `18.0`

## Version-by-version roadmap completed

### v17.1 - Patch Objective Refinement

Added objective refinement through:

```bash
python conscious_agent/main.py --refine-patch-objective
```

This sharpens task-to-code patch objectives into specific behavior change, affected command/API/dashboard/documentation surfaces, allowed files, blocked files, success criteria, failure criteria, README impact, and test expectations.

### v17.2 - Code Context Ranking

Added ranked code context through:

```bash
python conscious_agent/main.py --rank-code-context
```

It scores focused code snippets by task relevance, surface connection, file risk, and symbol/snippet coverage so prompt context is not just a wheelbarrow of code dumped at the model's feet.

### v17.3 - Prompt Safety Envelope

Added prompt safety envelopes through:

```bash
python conscious_agent/main.py --patch-safety-envelope
```

The envelope enforces allowed files, expected old text, no default full-file rewrites, README/test impact, read-only GET routes, dry-run pointer separation, and approval artifact binding.

### v17.4 - Generated Patch Validator

Added generated patch validation through:

```bash
python conscious_agent/main.py --validate-generated-patch
```

It validates parsed generated edits against project boundaries, allowed files, expected old text, README impact, test impact, and explicit safety intent for guardrail/recovery files.

### v17.5 - Patch Simulation Runner

Added patch simulation through:

```bash
python conscious_agent/main.py --patch-simulation
```

The simulation performs in-memory replacements, computes before/after hashes, identifies files that would change, builds backup/rollback expectations, and never writes source files.

### v17.6 - Test Stub Planner

Added test stub planning through:

```bash
python conscious_agent/main.py --test-stub-plan
```

It recommends compile checks, smoke checks, semantic checks, dashboard import checks, API GET/POST safety checks, and CLI regression checks based on touched files.

### v17.7 - Patch Review Scoring

Added patch review scoring through:

```bash
python conscious_agent/main.py --patch-review-score
```

The score covers objective clarity, context quality, prompt safety, schema validity, boundary safety, simulation, test coverage, README coverage, rollback safety, and approval safety.

### v17.8 - Dashboard Code Patch Approval UI

Upgraded dashboard review at:

```text
/code-patches
```

The page now shows the validation-centered v18 reports and keeps GET views preview-only. POST is still required for saved artifacts or mutation paths, because hyperlinks do not get to operate on live organs.

### v17.9 - Patch Failure Recovery Plan

Added recovery planning through:

```bash
python conscious_agent/main.py --patch-recovery-plan
```

It turns validation, simulation, and failure analysis signals into safe retry strategies, future prompt constraints, files to avoid, tests to add, and human-review requirements.

### v18.0 - Validated AI Code Patch Loop

Added the validated AI code patch loop through:

```bash
python conscious_agent/main.py --validated-ai-code-patch-loop
```

The loop refines the objective, ranks context, builds the safety envelope, parses edits, checks consistency, validates generated edits, simulates the patch, plans tests, scores review readiness, builds diff/semantic/recovery artifacts, and stops for approval. If a valid artifact-bound approval already exists, it can continue through the existing generated-code release path under explicit confirmation rules.

## New API routes

Read-only preview routes:

```text
GET /api/code-patches/objective-refinement
GET /api/code-patches/context-ranking
GET /api/code-patches/safety-envelope
GET /api/code-patches/validate-generated-patch
GET /api/code-patches/simulation
GET /api/code-patches/test-stub-plan
GET /api/code-patches/review-score
GET /api/code-patches/recovery-plan
GET /api/code-patches/validated-ai-loop
```

Saved-artifact routes:

```text
POST /api/code-patches/objective-refinement
POST /api/code-patches/context-ranking
POST /api/code-patches/safety-envelope
POST /api/code-patches/validate-generated-patch
POST /api/code-patches/simulation
POST /api/code-patches/test-stub-plan
POST /api/code-patches/review-score
POST /api/code-patches/recovery-plan
POST /api/code-patches/validated-ai-loop
```

Real apply behavior still requires explicit POST confirmation through the existing generated-code release/apply gates. GET stays read-only, because apparently we keep having to remind software not to perform surgery when someone asks for a chart.

## Recommended verification commands

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --refine-patch-objective
python conscious_agent/main.py --rank-code-context
python conscious_agent/main.py --patch-safety-envelope
python conscious_agent/main.py --validate-generated-patch
python conscious_agent/main.py --patch-simulation
python conscious_agent/main.py --test-stub-plan
python conscious_agent/main.py --patch-review-score
python conscious_agent/main.py --patch-recovery-plan
python conscious_agent/main.py --validated-ai-code-patch-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python -u tools/smoke_check.py
```

## Next recommended step

v18.0 makes generated AI patches validatable and simulatable before approval. The next likely phase should make the approved apply/release review more operator-friendly: stronger dashboard approve/reject controls, more explicit artifact locking, better local-model integration, and release packaging that can be prepared directly from the validated patch bundle.

---

# Previous README: # Eidolon v17.0 - AI-Assisted Human-Approved Code Patch Loop

v17.0 bundles the v16.1 through v17.0 AI-assisted generated-code patch roadmap into one packaged release. Eidolon can now translate a task into a concrete code patch objective, extract focused code context, build a bounded patch prompt, parse generated edit objects, check edit consistency, run an AI patch dry-run, classify failures, store learning notes, and run a one-task AI-assisted human-approved code patch loop. The gremlin is now allowed to suggest edits, but only through a cage made of JSON, approval binding, expected text, and the crushing weight of consequences.

## What changed in v17.0

- Added `conscious_agent/ai_patch_assistance.py`
  - v16.1 task-to-code patch translator
  - v16.2 focused code context extractor
  - v16.3 structured patch prompt builder
  - v16.4 generated edit parser
  - v16.5 multi-edit consistency checker
  - v16.6 AI-assisted code patch dry-run
  - v16.8 patch failure classifier
  - v16.9 patch learning notes
  - v17.0 AI-assisted human-approved code patch loop
- Updated `conscious_agent/main.py`
  - added CLI commands for the v16.1-v17.0 AI-assisted code patch pipeline
- Updated `conscious_agent/api_server.py`
  - API version is now `17.0`
  - added read-only GET preview endpoints for AI-assisted code patch reports
  - added POST endpoints for saving AI-assisted patch review artifacts
  - real apply paths remain POST-only and require explicit confirmation
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `17.0`
  - added `/code-patches` generated patch review page
  - added dashboard cards for task objective, code context, patch prompt, parsed edits, consistency, AI dry-run, semantic checks, and AI-assisted loop state
- Updated `conscious_agent/command_runner.py`
  - whitelisted the v16.1-v17.0 AI-assisted patch review commands
- Updated `tools/smoke_check.py`
  - validates `ai_patch_assistance.py` report shapes in-process
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v17.0`
  - `data/projects.json` marks `last_updated_for: v17.0`
  - workspace metadata marks the Eidolon project as version `17.0`

## Version-by-version roadmap completed

### v16.1 - Task-to-Code Patch Translator

Added task objective translation through:

```bash
python conscious_agent/main.py --task-to-code-patch
```

This turns the active draft request into a bounded code patch objective with target behavior, expected files, likely symbols, README impact, test impact, risk level, and patch strategy.

### v16.2 - Code Context Extractor

Added focused code context extraction through:

```bash
python conscious_agent/main.py --code-context
```

It extracts target files, symbol spans, nearby snippets, README context, and symbol scan summaries so patch generation does not have to swallow the whole project like a python with ambition.

### v16.3 - Patch Prompt Builder

Added structured prompt generation through:

```bash
python conscious_agent/main.py --patch-prompt
```

The prompt includes task objective, constraints, allowed files, blocked files, current code context, README requirements, test requirements, safety rules, and a strict JSON output schema.

### v16.4 - Generated Edit Parser

Added generated edit parsing through:

```bash
python conscious_agent/main.py --parse-generated-edits
```

It parses edit objects with `file`, `symbol`, `expected_old_text`, `replacement_text`, `reason`, tests, and README impact. It rejects unsafe paths, missing expected text, missing replacements, large blind full-file rewrites, unapproved guardrail edits, and expected text that does not match the current file.

### v16.5 - Multi-Edit Consistency Checker

Added generated edit consistency checks through:

```bash
python conscious_agent/main.py --edit-consistency
```

It detects duplicate target regions, rejected generated edits, missing README/test impact, and API edits that need GET/POST safety coverage.

### v16.6 - AI Patch Draft Dry-Run

Added an AI-assisted dry-run path through:

```bash
python conscious_agent/main.py --ai-code-patch-dry-run
```

The dry-run performs task translation, code context extraction, prompt building, generated patch artifact review, edit parsing, consistency checks, diff bundle generation, and semantic checks without source writes, approval consumption, or rollback pointer changes.

### v16.7 - Generated Patch Review Dashboard

Added dashboard support at:

```text
/code-patches
```

The page shows task objective, code context, patch prompt, parsed edits, consistency checks, dry-run state, semantic checks, failure analysis, learning notes, and AI-assisted loop status. The page uses read-only GET previews and POST-only save actions, because links should not be able to operate heavy machinery.

### v16.8 - Patch Failure Classifier

Added generated patch failure analysis through:

```bash
python conscious_agent/main.py --patch-failure-analysis
```

It classifies context mismatch, symbol issues, compile failures, dashboard import failures, API safety failures, README gate failures, approval mismatches, rollback problems, test failures, and environment warnings.

### v16.9 - Patch Learning Notes

Added generated patch learning notes through:

```bash
python conscious_agent/main.py --patch-learning-notes
```

It stores lessons from failures, rejected edits, and human review notes so future patch prompts can carry forward constraints instead of rediscovering the same rake with its face.

### v17.0 - AI-Assisted Human-Approved Code Patch Loop

Added the bounded AI-assisted code patch loop through:

```bash
python conscious_agent/main.py --ai-assisted-code-patch-loop
```

The loop performs one project, one task, one generated patch review, one approval check, one optional apply path, one verification path, one release artifact path, and then stops. Without an artifact-bound approval, it prepares review artifacts and stops for human approval.

## New API routes

Read-only preview routes:

```text
GET /api/code-patches/task-to-code-patch
GET /api/code-patches/code-context
GET /api/code-patches/patch-prompt
GET /api/code-patches/parse-generated-edits
GET /api/code-patches/edit-consistency
GET /api/code-patches/ai-dry-run
GET /api/code-patches/failure-analysis
GET /api/code-patches/learning-notes
GET /api/code-patches/ai-assisted-loop
```

Saved-artifact routes:

```text
POST /api/code-patches/task-to-code-patch
POST /api/code-patches/code-context
POST /api/code-patches/patch-prompt
POST /api/code-patches/parse-generated-edits
POST /api/code-patches/edit-consistency
POST /api/code-patches/ai-dry-run
POST /api/code-patches/failure-analysis
POST /api/code-patches/learning-notes
POST /api/code-patches/ai-assisted-loop
```

Live apply behavior still requires explicit POST confirmation through the existing generated-code release/apply gates. GET stays read-only. Yes, we are still saying this out loud because APIs keep trying to do crimes when nobody is looking.

## Recommended verification commands

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --task-to-code-patch
python conscious_agent/main.py --code-context
python conscious_agent/main.py --patch-prompt
python conscious_agent/main.py --parse-generated-edits
python conscious_agent/main.py --edit-consistency
python conscious_agent/main.py --ai-code-patch-dry-run
python conscious_agent/main.py --patch-failure-analysis
python conscious_agent/main.py --patch-learning-notes
python conscious_agent/main.py --ai-assisted-code-patch-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python -u tools/smoke_check.py
```

## Next recommended step

v17.0 gives Eidolon AI-assisted generated patch content in a safe review lane. The next major phase should make this more practical: improve real local-model integration, strengthen generated edit validation, add dashboard approval controls for generated code patches, and prepare a human-approved real apply path that can produce release packages with fewer manual terminal hops.

---

# Eidolon v16.0 - Generated Code Patch Release Loop

v16.0 bundles the v15.1 through v16.0 generated-code release roadmap into one packaged release. The release lane now has a dedicated generated-code patch workspace, symbol-aware file scans, targeted rewrite plans, conflict detection, diff bundles, guarded apply transactions, semantic safety checks, release artifact manifests, audit trails, and a bounded generated-code release loop. The robot now has a clipboard, a map, and a lockbox. Still not allowed near scissors without permission.

## What changed in v16.0

- Added `conscious_agent/code_patch_release.py`
  - v15.1 generated-code patch workspace status
  - v15.2 symbol-aware target file scanner
  - v15.3 targeted rewrite planner
  - v15.4 rewrite conflict detector
  - v15.5 generated patch diff bundle
  - v15.6 guarded code patch transaction dry-run/apply gate
  - v15.7 post-apply semantic checks
  - v15.8 release artifact manifest builder
  - v15.9 release audit trail
  - v16.0 generated code patch release loop
- Updated `conscious_agent/main.py`
  - added CLI commands for the v15.1-v16.0 generated-code patch release pipeline
- Updated `conscious_agent/api_server.py`
  - API version is now `16.0`
  - added read-only GET preview endpoints for generated-code patch/release reports
  - added POST endpoints for saving generated-code patch/release artifacts
  - real apply paths remain POST-only and require explicit confirmation
- Updated `conscious_agent/command_runner.py`
  - whitelisted the v15.1-v16.0 generated-code patch release commands
- Updated `tools/smoke_check.py`
  - validates `code_patch_release.py` report shapes in-process
  - keeps the full CLI sequence out of smoke_check so nested compile/readiness checks do not fight the outer smoke run like tiny multiprocessing goblins
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v16.0`
  - `data/projects.json` marks `last_updated_for: v16.0`
  - workspace metadata marks the Eidolon project as version `16.0`

## Version-by-version roadmap completed

### v15.1 - Real Patch Workspace Files

Added generated-code patch workspace reporting through:

```bash
python conscious_agent/main.py --code-patch-status
```

The workspace lives under:

```text
data/code_patches/
  current_patch.json
  proposed_edits.json
  rewrite_previews.json
  apply_transaction_report.json
  verification_report.json
  symbol_scan.json
  rewrite_plan.json
  rewrite_conflicts.json
  code_patch_diff_bundle.json
  release_artifact.json
  release_audit_trail.json
```

This separates real code patch artifacts from draft review metadata, because piling every artifact into one drawer is how software grows mushrooms.

### v15.2 - Symbol-Aware File Scanner

Added target-file symbol scanning through:

```bash
python conscious_agent/main.py --symbol-scan
```

It detects Python functions, classes, imports, constants, CLI arguments, and likely API/dashboard route markers. Non-Python files are handled as text targets.

### v15.3 - Targeted Rewrite Planner

Added targeted rewrite planning through:

```bash
python conscious_agent/main.py --rewrite-plan
```

The planner links code edit proposals to target files, expected hashes, symbol targets when available, backup requirements, README impact, and test requirements. Full-file rewrites remain hash-guarded instead of blindly overwriting files like a caffeinated copier.

### v15.4 - Rewrite Conflict Detector

Added rewrite conflict checks through:

```bash
python conscious_agent/main.py --rewrite-conflicts
```

It detects missing target files, changed file hashes, missing target symbols, blocked safe-rewrite previews, and approval binding problems. Approval binding warnings do not block dry-run review, but real apply still requires a valid artifact-bound approval.

### v15.5 - Generated Patch Diff Bundle

Added a generated patch diff bundle through:

```bash
python conscious_agent/main.py --code-patch-diff-bundle
```

The bundle collects draft verification, code edit proposals, rewrite plans, safe rewrite previews, generated patch summaries, rewrite conflict checks, test suggestions, boundary checks, and approval binding status into one review artifact.

### v15.6 - Patch Apply Transaction

Added guarded transaction-style apply reporting through:

```bash
python conscious_agent/main.py --apply-code-patch-transaction --dry-run
```

Real apply remains gated behind:

```bash
python conscious_agent/main.py --apply-code-patch-transaction --approve-controlled-self-build
```

Rules:

- all prechecks must pass before any source write
- approval must bind to the current artifact set for real apply
- dry-runs do not consume approval
- dry-runs do not overwrite real apply pointers
- failures block before source writes

### v15.7 - Post-Apply Semantic Checks

Added semantic safety checks through:

```bash
python conscious_agent/main.py --semantic-checks
```

Checks include:

- API GET/POST separation markers
- artifact-bound approval validation
- dry-run pointer separation
- rollback stale/hash guard markers
- single-use approval markers
- compile coverage

This catches the class of bugs that made earlier versions look green while holding a rake behind their back.

### v15.8 - Release Artifact Builder

Added release artifact manifest generation through:

```bash
python conscious_agent/main.py --release-artifact
```

The manifest records package name, changed files, previewed files, excluded files, README sections, verification commands, known warnings, rollback status, and release readiness.

### v15.9 - Release Audit Trail

Added release audit trail assembly through:

```bash
python conscious_agent/main.py --release-audit-trail
```

The audit trail links draft verification, approval state, code patch diff bundle, apply transaction report, semantic checks, release readiness, package metadata, and release artifact manifest.

### v16.0 - Generated Code Patch Release Loop

Added the bounded generated-code release loop through:

```bash
python conscious_agent/main.py --generated-code-release-loop
```

The loop performs one dry-run path by default:

```text
load/generated code patch workspace
scan target symbols
build rewrite plan
detect rewrite conflicts
build generated patch diff bundle
run guarded apply transaction as dry-run
run semantic checks
run release readiness
build release artifact manifest
write release audit trail
stop
```

Real apply still requires an approved draft, valid artifact binding, explicit confirmation, and one bounded run.

## New CLI commands

```bash
python conscious_agent/main.py --code-patch-status
python conscious_agent/main.py --symbol-scan
python conscious_agent/main.py --rewrite-plan
python conscious_agent/main.py --rewrite-conflicts
python conscious_agent/main.py --code-patch-diff-bundle
python conscious_agent/main.py --apply-code-patch-transaction --dry-run
python conscious_agent/main.py --semantic-checks
python conscious_agent/main.py --release-artifact
python conscious_agent/main.py --release-audit-trail
python conscious_agent/main.py --generated-code-release-loop
```

## New API endpoints

Read-only GET preview endpoints:

```text
GET /api/code-patches/status
GET /api/code-patches/symbol-scan
GET /api/code-patches/rewrite-plan
GET /api/code-patches/rewrite-conflicts
GET /api/code-patches/diff-bundle
GET /api/code-patches/apply-transaction
GET /api/code-patches/semantic-checks
GET /api/release/artifact
GET /api/release/audit-trail
GET /api/release/generated-code-loop
```

POST endpoints save artifacts or run guarded actions. Real apply paths require explicit confirmation.

## Verification used for v16.0

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --patch-draft-request --patch-draft-target-version 16.0
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --draft-quality
python conscious_agent/main.py --draft-verification-bundle
python conscious_agent/main.py --draft-review-checklist
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --code-edit-proposal
python conscious_agent/main.py --safe-rewrite-preview
python conscious_agent/main.py --generate-code-patch
python conscious_agent/main.py --code-patch-status
python conscious_agent/main.py --symbol-scan
python conscious_agent/main.py --rewrite-plan
python conscious_agent/main.py --rewrite-conflicts
python conscious_agent/main.py --code-patch-diff-bundle
python conscious_agent/main.py --apply-code-patch-transaction --dry-run
python conscious_agent/main.py --semantic-checks
python conscious_agent/main.py --release-artifact
python conscious_agent/main.py --release-audit-trail
python conscious_agent/main.py --generated-code-release-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

## Known environment warnings

- `chromadb` may be missing until `pip install -r requirements.txt` is run.
- Ollama must be running locally for AI health to pass.
- Release readiness can report `READY WITH WARNINGS` when no real approved code patch has been applied yet. That is expected for a packaged handoff.

---

# Eidolon v15.0 - Human-Approved Release Loop

v15.0 bundles the v14.1 through v15.0 release-readiness roadmap into one packaged release. The draft system can now move from review artifacts into release preparation: code edit proposals, safe rewrite previews, generated patch artifacts, test suggestions, dashboard approval controls, inline review notes, guarded approved code apply, package metadata, release readiness, and a one-stop human-approved release loop. The leash remains attached, because software with scissors should not be trusted unsupervised.

## What changed in v15.0

- Added `conscious_agent/release_pipeline.py`
  - v14.1 real code edit proposal format
  - v14.2 safe file rewrite preview engine
  - v14.3 AI-assisted code patch generation artifact
  - v14.4 unit/manual test suggestion generator
  - v14.6 inline patch review comments
  - v14.7 human-approved real apply pipeline
  - v14.8 commit/package preparation metadata
  - v14.9 release readiness gate
  - v15.0 human-approved release loop
- Updated `conscious_agent/patch_drafting.py`
  - version marker is now `15.0`
  - approval now captures a saved artifact snapshot for request, draft, diff, test impact, quality, checklist, and verification bundle
  - approved draft apply now rejects stale or mismatched approval artifacts
  - approval must bind to the current diff `draft_id`
  - verification bundles now use saved request/draft state instead of creating a fresh preview request id
  - review checklists now include request/draft identifiers so approval artifacts can be checked as one bundle
- Updated `conscious_agent/main.py`
  - added v14.1-v15.0 CLI commands for release preparation and approved code apply
- Updated `conscious_agent/api_server.py`
  - API version is now `15.0`
  - added read-only GET endpoints for release proposal/readiness previews
  - added POST endpoints for saving release artifacts and running approved release actions
  - mutation-capable paths remain POST-only
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `15.0`
  - expanded `/patch-drafts` with release proposal, rewrite preview, generated patch, test suggestions, release readiness, and package status
  - approve/reject/reopen/apply controls stay behind POST actions
- Updated versioned readiness surfaces
  - `controlled_build_cycle.py` version is now `15.0`
  - `operational_readiness.py` version is now `15.0`
  - `stabilization_checkpoint.py` version is now `15.0`
  - `project_intelligence.py` version is now `15.0`
  - `workspace_orchestration.py` version is now `15.0`
  - `workspace_execution.py` version is now `15.0`
  - README gate now checks through v15.0
- Updated `conscious_agent/command_runner.py`
  - whitelisted the new release/readiness/report commands through the safe command gate
- Updated `tools/smoke_check.py`
  - validates v15.0 release pipeline report shapes
  - runs the new draft/release review CLI commands
- Updated metadata
  - `data/settings.json` marks `last_updated_for: v15.0`
  - `data/projects.json` marks `last_updated_for: v15.0`

## Version-by-version roadmap completed

### v14.1 - Real Code Edit Proposal Format

Added structured code edit proposal reporting through:

```bash
python conscious_agent/main.py --code-edit-proposal
```

The proposal lists target files, change type, intent, risk, expected symbols, README requirements, and source draft metadata.

### v14.2 - Safe File Rewrite Engine

Added hash-checked safe rewrite previews through:

```bash
python conscious_agent/main.py --safe-rewrite-preview
```

The preview checks target paths, expected hashes, backup requirements, boundary status, and line-level diff summaries. It does not blindly overwrite files, because apparently the file system enjoys keeping its organs.

### v14.3 - AI-Assisted Code Patch Generation

Added generated code patch artifacts through:

```bash
python conscious_agent/main.py --generate-code-patch
```

This assembles proposed rewrite rows, risk data, boundary status, and review metadata without applying source edits.

### v14.4 - Unit Test Suggestion Generator

Added context-sensitive test suggestions through:

```bash
python conscious_agent/main.py --test-suggestions
```

It recommends compile checks, dashboard import checks, doctor mode, stabilization checkpoint, smoke check, draft status checks, and manual API/dashboard review items based on touched files.

### v14.5 - Dashboard Approve / Reject Controls

Expanded `/patch-drafts` with browser-accessible approve, reject, reopen, save proposal, save rewrite preview, save generated patch, save test suggestions, dry-run apply, readiness, package, and release loop controls.

### v14.6 - Inline Patch Review Comments

Added inline review notes through:

```bash
python conscious_agent/main.py --inline-review-note --patch-review-note "Keep GET routes read-only."
```

Notes can be attached to a file or intent block and are saved separately from the general draft review notes.

### v14.7 - Human-Approved Real Apply Pipeline

Added approved code apply through:

```bash
python conscious_agent/main.py --apply-approved-code-patch --dry-run
```

Real apply requires explicit approval, safe rewrite preview, boundary pass, backup planning, and an unconsumed approval. Dry-runs write to the dry-run report and do not overwrite the real apply pointer.

### v14.8 - Commit / Package Preparation

Added package metadata through:

```bash
python conscious_agent/main.py --prepare-release-package
```

It reports changed files, previewed files, required README sections, verification commands, known warnings, rollback availability, package name, and zip readiness.

### v14.9 - Release Readiness Gate

Added release readiness checks through:

```bash
python conscious_agent/main.py --release-readiness
```

The gate checks compile status, README/version metadata, approval state, dry-run separation, rollback availability, and test suggestions. It reports `READY`, `READY WITH WARNINGS`, or `FAILED`.

### v15.0 - Human-Approved Release Loop

Added the one-stop release loop through:

```bash
python conscious_agent/main.py --human-approved-release-loop
```

The loop loads or prepares one project, one draft, one proposal, one safe rewrite preview, one generated patch artifact, one test suggestion bundle, one readiness report, one package metadata report, and then stops. If an approval already exists, it preserves the approved draft artifacts instead of generating a new request that invalidates approval.

## Safety fixes included during v15.0

- Approval now binds to the exact saved draft artifacts, not just an approval flag.
- `approve_draft()` stores artifact hashes for the request, draft, diff, test impact, quality report, review checklist, and verification bundle.
- `build_apply_approved_draft()` rejects mismatched `approval.draft_id` vs `current_diff.draft_id`.
- Draft apply and release apply validate the saved approval artifact snapshot before doing even a dry-run apply.
- `build_draft_verification_bundle()` no longer creates a fresh preview request next to the saved current draft.
- Human-approved release loop preserves existing approved artifacts instead of silently replacing them.
- Dry-run release apply writes `latest_approved_code_apply_dry_run_report.json`; real apply writes `latest_approved_code_apply_report.json`.

## New CLI commands

```bash
python conscious_agent/main.py --code-edit-proposal
python conscious_agent/main.py --safe-rewrite-preview
python conscious_agent/main.py --generate-code-patch
python conscious_agent/main.py --test-suggestions
python conscious_agent/main.py --inline-review-note --patch-review-note "Keep GET routes read-only."
python conscious_agent/main.py --apply-approved-code-patch --dry-run
python conscious_agent/main.py --prepare-release-package
python conscious_agent/main.py --release-readiness
python conscious_agent/main.py --human-approved-release-loop
```

## Verification commands run for v15.0

```bash
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --patch-draft-request --patch-draft-target-version 15.0
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --draft-quality
python conscious_agent/main.py --draft-verification-bundle
python conscious_agent/main.py --draft-review-checklist
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --apply-approved-draft --dry-run
python conscious_agent/main.py --code-edit-proposal
python conscious_agent/main.py --safe-rewrite-preview
python conscious_agent/main.py --generate-code-patch
python conscious_agent/main.py --test-suggestions
python conscious_agent/main.py --inline-review-note --patch-review-note "Bind approval to the exact draft artifacts."
python conscious_agent/main.py --apply-approved-code-patch --dry-run
python conscious_agent/main.py --prepare-release-package
python conscious_agent/main.py --release-readiness
python conscious_agent/main.py --human-approved-release-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

## Known environment warnings

- `chromadb` may warn if it is not installed in the active Python environment. It remains listed in `requirements.txt`.
- Ollama health warns if the local Ollama service is not running.

## Next likely step

v15.1 should probably start **Release Review Dashboard Hardening**:

- make release readiness easier to inspect from the browser
- show approval artifact binding details
- show stale/mismatched draft artifacts clearly
- add one-card release package status
- improve manual verification checklist display
- keep all mutation buttons POST-only

v15.0 can prepare a release. v15.1 should make reviewing that release less like reading a court transcript written by a printer.

---

# Eidolon v14.0 - Review-Centered Patch Loop

v14.0 bundles the v13.1 through v14.0 draft review roadmap into one packaged release. The big shift is that patch drafts now have quality scoring, file target resolution, intent blocks, conflict detection, verification bundles, human review checklists, approved draft execution reports, and a review-centered loop. In other words, the patch process now has enough paperwork to become a small municipal office, but at least it stops previews from lying.

## What changed in v14.0

- Updated `conscious_agent/patch_drafting.py`
  - v13.1 draft quality scoring
  - v13.2 draft file target resolver
  - v13.3 draft change intent blocks
  - v13.4 draft conflict detector
  - v13.7 draft verification bundle
  - v13.8 human review checklist
  - v13.9 approved draft execution report
  - v14.0 review-centered patch loop
  - dry-run approved draft apply now writes `latest_approved_apply_dry_run_report.json` instead of overwriting the real apply pointer
- Updated `conscious_agent/main.py`
  - added all v13.1-v14.0 draft review CLI commands
- Updated `conscious_agent/api_server.py`
  - API version is now `14.0`
  - added read-only GET review endpoints under `/api/patch-drafts/...`
  - added POST endpoints for saving review artifacts and running the review-centered loop
  - mutation-capable paths remain POST-only
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `14.0`
  - expanded `/patch-drafts` into a review-centered page with quality, targets, intent blocks, conflicts, bundle, checklist, execution report, and loop status
- Updated versioned readiness surfaces
  - `controlled_build_cycle.py` version is now `14.0`
  - `operational_readiness.py` version is now `14.0`
  - `stabilization_checkpoint.py` version is now `14.0`
  - `project_intelligence.py` version is now `14.0`
  - `workspace_orchestration.py` version is now `14.0`
  - `workspace_execution.py` version is now `14.0`
  - README gate now checks through v14.0
- Updated `conscious_agent/command_runner.py`
  - whitelisted the new review/report commands through the existing safe command gate
- Updated `tools/smoke_check.py`
  - validates v14.0 draft review report shapes
  - runs the new draft review CLI commands
- Updated metadata:
  - `data/settings.json`
  - `data/projects.json`
  - `data/workspaces/projects.json`
  - `data/workspaces/active_project.json`

## v13.1 - Draft Quality Scoring

v13.1 adds a draft readiness score.

New CLI:

```powershell
python conscious_agent/main.py --draft-quality
```

New API:

```text
GET  /api/patch-drafts/quality
POST /api/patch-drafts/quality
```

The score considers request completeness, project context, file targets, intent blocks, diff readiness, test impact, README coverage, boundary status, and conflicts.

## v13.2 - Draft File Target Resolver

v13.2 resolves likely files and files to avoid.

New CLI:

```powershell
python conscious_agent/main.py --draft-file-targets
```

New API:

```text
GET  /api/patch-drafts/file-targets
POST /api/patch-drafts/file-targets
```

The resolver uses draft request text, proposed files, task wording, and known risky surfaces. It also calls out files like command runner, guardrails, workspace registry, and real apply pointers as avoid-unless-explicit targets.

## v13.3 - Draft Change Intent Blocks

v13.3 breaks a draft into reviewable intent blocks.

New CLI:

```powershell
python conscious_agent/main.py --draft-intent-blocks
```

New API:

```text
GET  /api/patch-drafts/intent-blocks
POST /api/patch-drafts/intent-blocks
```

Each block includes purpose, files affected, risk, tests required, README impact, and approval notes.

## v13.4 - Draft Conflict Detector

v13.4 detects stale, overlapping, or unsafe draft state.

New CLI:

```powershell
python conscious_agent/main.py --draft-conflicts
```

New API:

```text
GET  /api/patch-drafts/conflicts
POST /api/patch-drafts/conflicts
```

The detector checks approval state, consumed approvals, mismatched draft/diff ids, stale apply reports, dry-run apply reports, and existing controlled/workspace staged work.

## v13.5 - Dashboard Draft Review Page

v13.5 upgrades the dashboard page:

```text
/patch-drafts
```

The page now shows:

- draft workspace status
- quality score
- file targets
- conflict status
- verification bundle
- review-centered loop status
- command examples
- read-only JSON links

## v13.6 - API Draft Review Endpoints

v13.6 adds read-only GET review endpoints:

```text
GET /api/patch-drafts/status
GET /api/patch-drafts/request
GET /api/patch-drafts/draft
GET /api/patch-drafts/notes
GET /api/patch-drafts/diff
GET /api/patch-drafts/test-impact
GET /api/patch-drafts/approval-gate
GET /api/patch-drafts/quality
GET /api/patch-drafts/file-targets
GET /api/patch-drafts/intent-blocks
GET /api/patch-drafts/conflicts
GET /api/patch-drafts/verification-bundle
GET /api/patch-drafts/review-checklist
GET /api/patch-drafts/execution-report
GET /api/patch-drafts/review-loop
```

Mutation-capable review endpoints are POST-only. GET reads. POST changes. Somehow civilization required this sentence.

## v13.7 - Draft Verification Bundle

v13.7 bundles review artifacts into one report.

New CLI:

```powershell
python conscious_agent/main.py --draft-verification-bundle
```

New API:

```text
GET  /api/patch-drafts/verification-bundle
POST /api/patch-drafts/verification-bundle
```

The bundle includes status, request, draft, file targets, intent blocks, conflicts, diff, test impact, quality, and approval gate results.

## v13.8 - Human Review Checklist

v13.8 generates a checklist before approval.

New CLI:

```powershell
python conscious_agent/main.py --draft-review-checklist
```

New API:

```text
GET  /api/patch-drafts/review-checklist
POST /api/patch-drafts/review-checklist
```

Checklist items cover intended files, GET/POST safety, README update, rollback/apply pointer behavior, tests, single-use approval, risk limit, and conflicts.

## v13.9 - Approved Draft Execution Report

v13.9 reports what happened after an approved draft apply or dry-run apply.

New CLI:

```powershell
python conscious_agent/main.py --approved-draft-execution-report
```

New API:

```text
GET  /api/patch-drafts/execution-report
POST /api/patch-drafts/execution-report
```

Dry-run apply reports do not imply rollback availability and do not overwrite the real apply pointer. This keeps rollback status honest, a concept APIs find personally offensive.

## v14.0 - Review-Centered Patch Loop

v14.0 combines the review workflow.

New CLI:

```powershell
python conscious_agent/main.py --review-centered-patch-loop
```

New API:

```text
GET  /api/patch-drafts/review-loop
POST /api/patch-drafts/review-loop
```

Flow:

```text
load/create draft request
create draft
resolve file targets
create intent blocks
detect conflicts
generate diff
plan test impact
score draft quality
build verification bundle
build human checklist
stop for review

if already approved and explicitly allowed:
apply once
generate execution report
clear/consume approval
stop
```

Hard limits:

```text
one project
one task
one approval
one patch
GET endpoints read-only
dry-run apply never replaces real apply pointer
README must be updated
then stop
```

## v14.0 CLI summary

```powershell
python conscious_agent/main.py --patch-draft-request --patch-draft-target-version 14.0
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --draft-file-targets
python conscious_agent/main.py --draft-intent-blocks
python conscious_agent/main.py --draft-conflicts
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --draft-quality
python conscious_agent/main.py --draft-verification-bundle
python conscious_agent/main.py --draft-review-checklist
python conscious_agent/main.py --approved-draft-execution-report
python conscious_agent/main.py --review-centered-patch-loop
```

Existing v13 commands still work:

```powershell
python conscious_agent/main.py --patch-draft-status
python conscious_agent/main.py --patch-review-notes --patch-review-note "Keep GET routes read-only."
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --apply-approved-draft --dry-run
python conscious_agent/main.py --rollback-approved-draft
python conscious_agent/main.py --reopen-draft
python conscious_agent/main.py --human-approved-patch-loop
```

## v14.0 API summary

Read-only preview routes:

```text
GET /api/patch-drafts/status
GET /api/patch-drafts/quality
GET /api/patch-drafts/file-targets
GET /api/patch-drafts/intent-blocks
GET /api/patch-drafts/conflicts
GET /api/patch-drafts/verification-bundle
GET /api/patch-drafts/review-checklist
GET /api/patch-drafts/execution-report
GET /api/patch-drafts/review-loop
```

Saved/mutation routes:

```text
POST /api/patch-drafts/quality
POST /api/patch-drafts/file-targets
POST /api/patch-drafts/intent-blocks
POST /api/patch-drafts/conflicts
POST /api/patch-drafts/verification-bundle
POST /api/patch-drafts/review-checklist
POST /api/patch-drafts/execution-report
POST /api/patch-drafts/review-loop
```

Apply still requires explicit confirmation through the existing approved draft apply path:

```text
POST /api/apply-approved-draft
```

## v14.0 dashboard

Run:

```powershell
python conscious_agent/main.py --dashboard
```

Open:

```text
http://127.0.0.1:8765/patch-drafts
```

The dashboard page is read-only and shows the review-centered draft reports in one place.

## Verification performed for v14.0

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --patch-draft-request --patch-draft-target-version 14.0
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --draft-file-targets
python conscious_agent/main.py --draft-intent-blocks
python conscious_agent/main.py --draft-conflicts
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --draft-quality
python conscious_agent/main.py --draft-verification-bundle
python conscious_agent/main.py --draft-review-checklist
python conscious_agent/main.py --approved-draft-execution-report
python conscious_agent/main.py --review-centered-patch-loop
python conscious_agent/main.py --human-approved-patch-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

## Safety notes

v14.0 still does not turn Eidolon loose. It prepares review artifacts, exposes them through CLI/API/dashboard, keeps GET routes read-only, keeps dry-run apply reports separate from real apply pointers, and stops unless a single-use approval already exists and live apply is explicitly allowed. The robot gets a clipboard, not a chainsaw. A tiny mercy.

---

# Eidolon v13.0 - Human-Approved Autonomous Patch Loop

v13.0 bundles the v12.1 through v13.0 human-approved patch drafting roadmap into one packaged release. The big shift is that Eidolon can now turn a structured patch request into a draft, preserve review notes, generate a draft diff, plan test impact, run an approval gate, apply one approved draft, support safe rollback/reopen flows, and run a human-approved patch loop that stops unless approval already exists. We have officially invented paperwork for robots, which is both depressing and exactly what keeps the file goblins supervised.

## What changed in v13.0

- Added `conscious_agent/patch_drafting.py`
  - v12.1 patch draft request format
  - v12.2 AI patch drafting interface
  - v12.3 patch draft workspace
  - v12.4 human patch review notes
  - v12.5 draft diff generator
  - v12.6 draft test impact planner
  - v12.7 approval gate
  - v12.8 apply approved draft
  - v12.9 draft rollback and reopen
  - v13.0 human-approved autonomous patch loop
- Updated `conscious_agent/main.py`
  - added all v12.1-v13.0 patch drafting CLI commands
- Updated `conscious_agent/api_server.py`
  - API version is now `13.0`
  - added read-only GET preview endpoints for patch draft status, request, draft, notes, diff, test impact, approval gate, and human-approved loop
  - added POST endpoints for saved draft requests, draft generation, notes, diff/test-impact generation, approval/rejection, approved apply, rollback, reopen, and human-approved loop execution
  - mutation-capable endpoints remain POST-only with explicit confirmation where writes or rollback can occur
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `13.0`
  - added `/patch-drafts` read-only dashboard page
  - added API docs for patch draft endpoints
- Updated versioned readiness surfaces
  - `controlled_build_cycle.py` version is now `13.0`
  - `operational_readiness.py` version is now `13.0`
  - `stabilization_checkpoint.py` version is now `13.0`
  - `project_intelligence.py` version is now `13.0`
  - `workspace_orchestration.py` version is now `13.0`
  - `workspace_execution.py` version is now `13.0`
  - README gate now checks through v13.0
- Updated `conscious_agent/command_runner.py`
  - whitelisted patch draft status/review/preview commands and approval/apply commands behind the existing safe command gate
- Updated `tools/smoke_check.py`
  - validates patch drafting report shapes and human-approved loop text
  - checks v13.0 versions
- Updated metadata:
  - `data/settings.json`
  - `data/projects.json`
  - `data/workspaces/projects.json`
  - `data/workspaces/active_project.json`

## v12.1 - Patch Draft Request Format

v12.1 adds the structured patch draft request.

New CLI:

```powershell
python conscious_agent/main.py --patch-draft-request
python conscious_agent/main.py --patch-draft-request --patch-draft-task "Improve API safety" --patch-draft-intent "Keep GET routes read-only"
```

New API:

```text
GET  /api/patch-draft-request
POST /api/patch-draft-request
```

The request captures project id, target version, task, intent, constraints, expected files, and risk limit. GET previews are read-only. POST saves the request under `data/patch_drafts/draft_request.json`.

## v12.2 - AI Patch Drafting Interface

v12.2 adds the draft patch interface.

New CLI:

```powershell
python conscious_agent/main.py --draft-patch
```

New API:

```text
GET  /api/draft-patch
POST /api/draft-patch
```

The draft loads project context, identifies likely files, marks source files as impact surfaces, and plans a README update without applying source edits.

## v12.3 - Patch Draft Workspace

v12.3 adds a dedicated patch draft workspace.

New CLI:

```powershell
python conscious_agent/main.py --patch-draft-status
```

New API:

```text
GET /api/patch-draft-status
```

Workspace files live under:

```text
data/patch_drafts/
  draft_request.json
  current_draft.json
  current_diff.json
  test_impact.json
  review_notes.json
  approval_state.json
  proposed_files/
  backups/
```

## v12.4 - Human Patch Review Notes

v12.4 adds review notes for patch drafts.

New CLI:

```powershell
python conscious_agent/main.py --patch-review-notes
python conscious_agent/main.py --patch-review-notes --patch-review-note "Reject dashboard changes. Keep API read-only."
```

New API:

```text
GET  /api/patch-review-notes
POST /api/patch-review-notes
```

Notes are preserved and included in approval review. A note containing rejection language produces an approval warning, because apparently even machines need to learn when humans are waving a red flag.

## v12.5 - Draft Diff Generator

v12.5 adds draft diff previews.

New CLI:

```powershell
python conscious_agent/main.py --draft-diff
```

New API:

```text
GET  /api/draft-diff
POST /api/draft-diff
```

The diff generator creates preview rows, boundary status, README update status, and draft proposed-file artifacts. GET is preview-only. POST saves artifacts.

## v12.6 - Draft Test Impact Planner

v12.6 adds test impact planning.

New CLI:

```powershell
python conscious_agent/main.py --draft-test-impact
```

New API:

```text
GET  /api/draft-test-impact
POST /api/draft-test-impact
```

It maps touched files to required verification commands. Dashboard changes require a dashboard import check. API changes require route/README safety review. Patch drafting changes require patch draft status verification.

## v12.7 - Approval Gate

v12.7 adds a formal approval gate.

New CLI:

```powershell
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --reject-draft --patch-review-note "Needs another pass."
```

New API:

```text
GET  /api/approval-gate
POST /api/approve-draft
POST /api/reject-draft
```

Approval requires a draft, diff, test impact report, boundary pass, README update, and risk within limit. Approval is single-use.

## v12.8 - Apply Approved Draft

v12.8 adds approved draft application.

New CLI:

```powershell
python conscious_agent/main.py --apply-approved-draft --dry-run
python conscious_agent/main.py --apply-approved-draft
```

New API:

```text
POST /api/apply-approved-draft
```

The apply path requires an unconsumed approval. API live apply requires explicit JSON confirmation. Successful non-dry-run apply consumes the approval and creates backup metadata.

## v12.9 - Draft Rollback and Reopen

v12.9 adds rollback and reopen support.

New CLI:

```powershell
python conscious_agent/main.py --rollback-approved-draft
python conscious_agent/main.py --rollback-approved-draft --approve-controlled-self-build
python conscious_agent/main.py --reopen-draft
```

New API:

```text
POST /api/rollback-approved-draft
POST /api/reopen-draft
```

Rollback verifies current file hashes before restoring backups so newer manual edits are not overwritten. Reopen clears approval and preserves review notes.

## v13.0 - Human-Approved Autonomous Patch Loop

v13.0 adds the human-approved patch loop.

New CLI:

```powershell
python conscious_agent/main.py --human-approved-patch-loop
```

New API:

```text
GET  /api/human-approved-patch-loop
POST /api/human-approved-patch-loop
```

Flow:

```text
load active project
create one patch draft request
draft one patch
generate one diff
run boundary check
create one test impact plan
run approval gate
stop unless an unconsumed approval already exists
if approved and explicitly allowed, apply once
consume approval
stop
```

Important limit:

```text
One project. One task. One approval. One patch. Then stop.
```

## v13.0 CLI summary

```powershell
python conscious_agent/main.py --patch-draft-request
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --patch-draft-status
python conscious_agent/main.py --patch-review-notes --patch-review-note "Keep GET routes read-only."
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --reject-draft
python conscious_agent/main.py --apply-approved-draft --dry-run
python conscious_agent/main.py --rollback-approved-draft
python conscious_agent/main.py --reopen-draft
python conscious_agent/main.py --human-approved-patch-loop
```

## v13.0 API summary

Read-only GET preview/report endpoints:

```text
GET /api/patch-draft-status
GET /api/patch-draft-request
GET /api/draft-patch
GET /api/patch-review-notes
GET /api/draft-diff
GET /api/draft-test-impact
GET /api/approval-gate
GET /api/human-approved-patch-loop
```

Mutation-capable POST endpoints:

```text
POST /api/patch-draft-request
POST /api/draft-patch
POST /api/patch-review-notes
POST /api/draft-diff
POST /api/draft-test-impact
POST /api/approve-draft
POST /api/reject-draft
POST /api/apply-approved-draft
POST /api/rollback-approved-draft
POST /api/reopen-draft
POST /api/human-approved-patch-loop
```

Live write/rollback POST behavior requires explicit JSON confirmation where source files can be modified. GET stays read-only, because we are not reenacting the v10 haunted preview-route situation.

## Verification performed for v13.0

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --patch-draft-request
python conscious_agent/main.py --draft-patch
python conscious_agent/main.py --patch-draft-status
python conscious_agent/main.py --patch-review-notes --patch-review-note "Keep GET routes read-only."
python conscious_agent/main.py --draft-diff
python conscious_agent/main.py --draft-test-impact
python conscious_agent/main.py --approve-draft
python conscious_agent/main.py --apply-approved-draft --dry-run
python conscious_agent/main.py --rollback-approved-draft
python conscious_agent/main.py --reopen-draft
python conscious_agent/main.py --human-approved-patch-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

Known sandbox warnings remain:

- `chromadb` may be missing in this sandbox but remains listed in `requirements.txt`.
- Ollama may not be running in this sandbox, so AI health reports an environment warning.

## Safety

v13.0 keeps patch generation human-approved. Drafts can be prepared and previewed without source edits. Approval is single-use. Apply checks hashes before writing. Rollback checks hashes before restoring. GET endpoints are read-only. The loop stops after one patch lane because infinite autonomy is how codebases become abandoned theme parks.

---

# Eidolon v12.0 - Guarded Workspace Development Loop

v12.0 bundles the v11.1 through v12.0 guarded-workspace roadmap into one packaged release. The big shift is that Eidolon can now audit the workspace registry, suggest workspace repairs, preview project registration, enforce project boundaries, build workspace patch plans, preview workspace diffs, dry-run or explicitly apply one guarded workspace patch, verify the latest workspace patch, and run a guarded workspace development loop that stops after one project, one task, and one patch lane. We keep the brakes installed because apparently software prefers not to be surprised by its own ambition.

This release also folds in review findings from the v11.0 package and the desktop launch blocker:

- Fixed a dashboard f-string quoting bug that caused `python conscious_agent/main.py --desktop` to fail while importing `dashboard.py`; dashboard import now compiles cleanly before desktop launch.
- GET `/api/project-registry` is now read-only and no longer repairs/seeds command profiles or writes timeline events.
- GET `/api/command-profiles` is now read-only and no longer writes profile files.
- GET `/api/workspace-dev-loop` is now read-only and no longer writes a preview timeline event.
- GET workspace planning/preview endpoints use non-saving preview paths.
- Workspace dashboard rendering uses read-only report builders so opening the page does not mutate workspace state.
- Patch workspace status no longer looks green when `latest_apply_report.json` is stale or rollback-unusable.
- Latest patch verification now fails if the latest apply pointer is stale/dry-run-only and rollback would be unusable.
- Workspace registry audit can archive stale latest apply pointers during repair/audit CLI paths.

## What changed in v12.0

- Added `conscious_agent/workspace_execution.py`
  - v11.1 workspace registry persistence audit
  - v11.2 workspace repair suggestions
  - v11.3 project registration wizard preview
  - v11.4 project boundary guard
  - v11.5 workspace patch plan
  - v11.6 workspace diff preview
  - v11.7 workspace apply dry-run
  - v11.8 workspace apply guarded
  - v11.9 workspace verification pipeline
  - v12.0 guarded workspace development loop
- Updated `conscious_agent/main.py`
  - added all v11.1-v12.0 guarded workspace CLI commands
- Updated `conscious_agent/api_server.py`
  - API version is now `12.0`
  - added guarded workspace GET preview endpoints
  - added POST-only guarded workspace apply/dev-loop endpoints
  - kept GET/preview routes read-only
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `12.0`
  - fixed desktop-blocking f-string syntax error
  - updated `/workspace` with guarded workspace execution cards
  - dashboard workspace reports now use read-only builders
- Updated `conscious_agent/controlled_build_cycle.py`
  - controlled-build version is now `12.0`
  - patch workspace status marks stale/unusable latest apply pointers as not OK
  - latest patch verification fails when rollback integrity is broken
  - README gate now checks through v12.0
- Updated `conscious_agent/workspace_orchestration.py`
  - workspace orchestration version is now `12.0`
  - registry/profile/dev-loop preview builders can run read-only
  - timeline initialization no longer happens from read-only preview calls
- Updated `conscious_agent/project_intelligence.py`
  - project-intelligence version is now `12.0`
  - README memory warnings now check for v12.0
- Updated `conscious_agent/operational_readiness.py`
  - operational readiness version is now `12.0`
  - hardening/readiness checks include v11.1-v12.0 README coverage
- Updated `conscious_agent/stabilization_checkpoint.py`
  - checkpoint version is now `12.0`
  - includes workspace execution surfaces in verification recommendations
- Updated `conscious_agent/command_runner.py`
  - whitelisted guarded workspace commands
- Updated `tools/smoke_check.py`
  - validates workspace execution report shapes and CLI commands
  - checks v12.0 versions
- Updated metadata:
  - `data/settings.json`
  - `data/projects.json`
  - `data/workspaces/projects.json`
  - `data/workspaces/active_project.json`
  - `data/workspaces/command_profiles/*.json`

## v11.1 - Workspace Registry Persistence Audit

v11.1 adds a workspace registry audit.

New CLI:

```powershell
python conscious_agent/main.py --workspace-registry-audit
```

New API:

```text
GET /api/workspace-registry-audit
```

The audit checks registered projects, active project pointers, project root resolution, README paths, safe command profiles, invalid/stale roots, duplicate project IDs, JSON registry files, and stale rollback pointers.

## v11.2 - Workspace Repair Suggestions

v11.2 adds workspace-level repair suggestions.

New CLI:

```powershell
python conscious_agent/main.py --workspace-repair-suggestions
```

New API:

```text
GET /api/workspace-repair-suggestions
```

It does not automatically repair project files. It explains what should be fixed, because automatically fixing the wrong registry is how machines earn side-eye.

## v11.3 - Project Registration Wizard

v11.3 adds a preview-only project registration wizard.

New CLI:

```powershell
python conscious_agent/main.py --project-registration-wizard "My App" --workspace-project-root C:\Projects\MyApp
```

New API:

```text
GET /api/project-registration-wizard?name=My%20App&root=C:\Projects\MyApp
```

It infers language/framework hints from files like `requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, and Gradle build files. Saving still uses the existing explicit project registration path.

## v11.4 - Project Boundary Guard

v11.4 adds a project boundary check.

New CLI:

```powershell
python conscious_agent/main.py --project-boundary-check
```

New API:

```text
GET /api/project-boundary-check
```

It checks staged changes against the active project root and blocks accidental edits outside the selected project or unsafe workspace registry/profile edits without explicit workspace intent.

## v11.5 - Workspace Patch Plan

v11.5 adds a workspace patch planner.

New CLI:

```powershell
python conscious_agent/main.py --workspace-patch-plan
```

New API:

```text
GET /api/workspace-patch-plan
```

The plan combines registry audit, project health, project context, dependency map, task inbox, controlled patch plan, boundary guard, and README gate.

## v11.6 - Workspace Diff Preview

v11.6 adds a workspace diff preview.

New CLI:

```powershell
python conscious_agent/main.py --workspace-preview-diff
```

New API:

```text
GET /api/workspace-preview-diff
```

The preview shows staged changes with boundary status before source files are modified.

## v11.7 - Workspace Apply Dry-Run

v11.7 adds a dry-run workspace apply path.

New CLI:

```powershell
python conscious_agent/main.py --workspace-apply --dry-run
```

Dry-run validates gates and runs through the apply path without modifying source files.

## v11.8 - Workspace Apply Guarded

v11.8 adds guarded workspace apply.

New CLI:

```powershell
python conscious_agent/main.py --workspace-apply --approve-controlled-self-build
```

New API:

```text
POST /api/workspace/apply
```

Live guarded apply requires explicit confirmation from the API body and still targets one active project only.

## v11.9 - Workspace Verification Pipeline

v11.9 adds workspace verification.

New CLI:

```powershell
python conscious_agent/main.py --workspace-verify-latest
```

New API:

```text
GET /api/workspace-verify-latest
```

It combines latest patch verification, README gate, boundary check, project health, rollback integrity, and rollback recommendation state.

## v12.0 - Guarded Workspace Development Loop

v12.0 adds the guarded workspace loop.

New CLI:

```powershell
python conscious_agent/main.py --guarded-workspace-dev-loop
```

New API:

```text
GET  /api/guarded-workspace-dev-loop
POST /api/workspace/guarded-dev-loop
```

Flow:

```text
audit workspace registry
check project health
review workspace task inbox
select one project
build project context
generate workspace patch plan
preview workspace diff
run boundary check
apply dry-run by default
run workspace verification
update timeline only on CLI/POST execution paths
stop
```

## v12.0 CLI summary

```powershell
python conscious_agent/main.py --workspace-registry-audit
python conscious_agent/main.py --workspace-repair-suggestions
python conscious_agent/main.py --project-registration-wizard "My App" --workspace-project-root C:\Projects\MyApp
python conscious_agent/main.py --project-boundary-check
python conscious_agent/main.py --workspace-patch-plan
python conscious_agent/main.py --workspace-preview-diff
python conscious_agent/main.py --workspace-apply --dry-run
python conscious_agent/main.py --workspace-apply --approve-controlled-self-build
python conscious_agent/main.py --workspace-verify-latest
python conscious_agent/main.py --guarded-workspace-dev-loop
```

## v12.0 API summary

Read-only GET preview/report endpoints:

```text
GET /api/workspace-registry-audit
GET /api/workspace-repair-suggestions
GET /api/project-registration-wizard
GET /api/project-boundary-check
GET /api/workspace-patch-plan
GET /api/workspace-preview-diff
GET /api/workspace-verify-latest
GET /api/guarded-workspace-dev-loop
```

Mutation-capable POST endpoints:

```text
POST /api/workspace/apply
POST /api/workspace/guarded-dev-loop
```

Live POST behavior requires explicit JSON confirmation. GET stays read-only. Society briefly improves.

## Verification performed for v12.0

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
PYTHONPATH=conscious_agent python -c "import dashboard; print(dashboard.DASHBOARD_VERSION)"
python conscious_agent/main.py --workspace-registry-audit
python conscious_agent/main.py --workspace-repair-suggestions
python conscious_agent/main.py --project-registration-wizard "Eidolon" --workspace-project-root .
python conscious_agent/main.py --project-boundary-check
python conscious_agent/main.py --workspace-patch-plan
python conscious_agent/main.py --workspace-preview-diff
python conscious_agent/main.py --workspace-apply --dry-run
python conscious_agent/main.py --workspace-verify-latest
python conscious_agent/main.py --guarded-workspace-dev-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

Known sandbox warnings remain:

- `chromadb` may be missing in this sandbox but remains listed in `requirements.txt`.
- Ollama may not be running in this sandbox, so AI health reports an environment warning.

## Safety

v12.0 keeps workspace mutation explicit and narrow. GET endpoints are read-only. The guarded workspace loop handles one project, one task, one patch lane, and then stops. This is not unlimited autonomy; it is a fenced workbench with labels, which is apparently what we need to keep the code goblins from redecorating the house.

---

# Eidolon v11.0 - Workspace-Orchestrated Development Loop

v11.0 bundles the v10.1 through v11.0 workspace-orchestration roadmap into one packaged release. The big shift is that Eidolon now has a real workspace control layer: it can register projects, derive the Eidolon root from `ROOT_DIR`, check health per project, manage safe command profiles, map cross-project dependencies, build a multi-project task inbox, block unsafe project switching, assemble project context bundles, record a workspace timeline, and run a workspace development-loop preview that stops before touching files. Stopping before mutation remains the humble seatbelt of software, which is embarrassing but useful.

This release also folds in review findings from the v10.0 package:

- Rollback now fails fast if `latest_apply_report.json` is missing, stale, dry-run-only, or has zero real applied file rows.
- Existing stale v9.0 dry-run rollback pointers are archived under `data/patch_workspace/stale_apply_reports/` if present instead of being left as the active rollback pointer.
- `patch_workspace_status()` and verification now surface stale latest-apply pointers as integrity warnings.
- Workspace project roots now store Eidolon as `.` and resolve it from `ROOT_DIR`, so a freshly unzipped Windows project does not inherit `/mnt/data/...` sandbox paths. Tiny victory over haunted absolute paths.

## What changed in v11.0

- Added `conscious_agent/workspace_orchestration.py`
  - v10.1 project registry upgrade
  - v10.2 per-project health checks
  - v10.3 project-specific command profiles
  - v10.4 cross-project dependency map
  - v10.5 multi-project task inbox
  - v10.6 safe project switching
  - v10.7 project context bundles
  - v10.8 workspace timeline
  - v10.9 multi-project dashboard
  - v11.0 workspace-orchestrated development loop preview
- Updated `conscious_agent/main.py`
  - added all v10.1-v11.0 workspace CLI commands
- Updated `conscious_agent/api_server.py`
  - API version is now `11.0`
  - added workspace registry, health, profile, dependency, inbox, context, timeline, and dev-loop endpoints
  - workspace mutation endpoints are POST-only
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `11.0`
  - added `/workspace`
  - updated API documentation with workspace endpoints
- Updated `conscious_agent/controlled_build_cycle.py`
  - controlled-build version is now `11.0`
  - rollback rejects stale/dry-run/non-applied latest apply reports
  - latest apply integrity is reported from patch workspace and verification reports
  - README gate now checks through v11.0
- Updated `conscious_agent/project_intelligence.py`
  - project-intelligence version is now `11.0`
  - workspace roots resolve `.` / `ROOT_DIR` dynamically
- Updated `conscious_agent/operational_readiness.py`
  - readiness version is now `11.0`
  - hardening checks include workspace CLI/API/dashboard/README surfaces
- Updated `conscious_agent/stabilization_checkpoint.py`
  - checkpoint version is now `11.0`
  - checks `workspace_orchestration.py`, workspace CLI flags, API endpoints, dashboard route, and smoke coverage
- Updated `conscious_agent/command_runner.py`
  - whitelisted the new workspace commands
- Updated `tools/smoke_check.py`
  - validates workspace orchestration reports and CLI commands
  - checks v11.0 versions
- Updated metadata:
  - `data/settings.json`
  - `data/projects.json`
  - `data/workspaces/projects.json`
  - `data/workspaces/active_project.json`
  - `data/workspaces/timeline.json`
  - `data/workspaces/command_profiles/*.json`

## v10.1 - Project Registry Upgrade

v10.1 makes the multi-project workspace registry explicit.

New CLI:

```powershell
python conscious_agent/main.py --project-registry
python conscious_agent/main.py --register-project "My App" --workspace-project-root C:\path\to\project --workspace-project-language Python
python conscious_agent/main.py --set-active-workspace-project eidolon
```

New API:

```text
GET  /api/project-registry
POST /api/projects/register
POST /api/projects/active
```

The seeded Eidolon entry uses:

```json
{
  "id": "eidolon",
  "root": ".",
  "root_resolves_from": "ROOT_DIR"
}
```

That means the root is derived from wherever the zip is unpacked, not from the build sandbox. Astonishingly, software works better when it knows where it lives.

## v10.2 - Per-Project Health Checks

v10.2 checks registered project health independently.

New CLI:

```powershell
python conscious_agent/main.py --project-health
python conscious_agent/main.py --project-health --project-health-all
```

New API:

```text
GET /api/project-health
GET /api/project-health?all=true
```

Health checks include:

- project root exists
- README exists
- test commands are configured
- safe command profile exists
- project is marked safe or blocked

## v10.3 - Project-Specific Command Profiles

v10.3 seeds command profiles under:

```text
data/workspaces/command_profiles/
```

Seeded profiles:

```text
eidolon.json
default_python.json
default_node.json
default_java.json
```

New CLI:

```powershell
python conscious_agent/main.py --command-profiles
```

New API:

```text
GET /api/command-profiles
```

Profiles define allowed compile/test commands and approval rules for package installs, destructive commands, and shell commands.

## v10.4 - Cross-Project Dependency Map

v10.4 adds a read-only dependency/coupling hint report.

New CLI:

```powershell
python conscious_agent/main.py --workspace-dependency-map
```

New API:

```text
GET /api/workspace-dependency-map
```

It checks shared roots, README references, configured dependencies, and risky coupling hints.

## v10.5 - Multi-Project Task Inbox

v10.5 centralizes task availability across registered projects.

New CLI:

```powershell
python conscious_agent/main.py --workspace-task-inbox
```

New API:

```text
GET /api/workspace-task-inbox
```

It ranks task rows by project, priority, blocked state, AI need, offline availability, and recommended action.

## v10.6 - Safe Project Switching

v10.6 blocks project switching when patch workspace state is dirty.

New CLI:

```powershell
python conscious_agent/main.py --switch-project eidolon
python conscious_agent/main.py --switch-project eidolon --force-switch-project
```

New API:

```text
POST /api/workspace/switch-project
```

Switching can be blocked by:

- staged patch plan
- proposed changes
- validation report
- stale latest apply pointer

This prevents cross-project confusion, the classic “I patched the wrong repo” flavor of despair.

## v10.7 - Project Context Bundles

v10.7 builds a project-specific context bundle.

New CLI:

```powershell
python conscious_agent/main.py --project-context
python conscious_agent/main.py --project-context --workspace-project-id eidolon
```

New API:

```text
GET /api/project-context
GET /api/project-context?project=eidolon
```

The bundle includes:

- registry entry
- health
- dependency map
- task inbox selection
- test plan
- risk profile
- memory index

## v10.8 - Workspace Timeline

v10.8 records and displays workspace-level events.

New CLI:

```powershell
python conscious_agent/main.py --workspace-timeline
```

New API:

```text
GET /api/workspace-timeline
```

Timeline events include registry checks, registration, active project changes, project switches, and workspace dev-loop previews.

## v10.9 - Multi-Project Dashboard

v10.9 adds the dashboard page:

```text
/workspace
```

The page shows:

- registry status
- project health
- command profiles
- dependency map
- task inbox
- context bundle
- timeline
- workspace dev-loop preview

## v11.0 - Workspace-Orchestrated Development Loop

v11.0 adds a preview-only workspace loop.

New CLI:

```powershell
python conscious_agent/main.py --workspace-dev-loop
python conscious_agent/main.py --workspace-dev-loop --readiness-json
```

New API:

```text
GET /api/workspace-dev-loop
```

Flow:

```text
scan registered projects
run per-project health checks
rank workspace tasks
select one project
load project context bundle
prepare patch plan preview
prepare staging preview
prepare diff preview
stop before mutation
```

Important limit:

```text
Only one project may be selected per run, and v11.0 does not apply patches from the workspace loop.
```

## v11.0 CLI summary

```powershell
python conscious_agent/main.py --project-registry
python conscious_agent/main.py --register-project "My App" --workspace-project-root C:\path\to\project
python conscious_agent/main.py --set-active-workspace-project eidolon
python conscious_agent/main.py --project-health --project-health-all
python conscious_agent/main.py --command-profiles
python conscious_agent/main.py --workspace-dependency-map
python conscious_agent/main.py --workspace-task-inbox
python conscious_agent/main.py --switch-project eidolon
python conscious_agent/main.py --project-context
python conscious_agent/main.py --workspace-timeline
python conscious_agent/main.py --workspace-dev-loop
```

## v11.0 API summary

```text
GET  /api/project-registry
POST /api/projects/register
POST /api/projects/active
GET  /api/project-health?all=true
GET  /api/command-profiles
GET  /api/workspace-dependency-map
GET  /api/workspace-task-inbox
POST /api/workspace/switch-project
GET  /api/project-context
GET  /api/workspace-timeline
GET  /api/workspace-dev-loop
```

## Verification performed for v11.0

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --project-registry
python conscious_agent/main.py --project-health --project-health-all
python conscious_agent/main.py --command-profiles
python conscious_agent/main.py --workspace-dependency-map
python conscious_agent/main.py --workspace-task-inbox
python conscious_agent/main.py --project-context
python conscious_agent/main.py --workspace-timeline
python conscious_agent/main.py --workspace-dev-loop
python conscious_agent/main.py --rollback-latest-patch --dry-run --readiness-json
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

Known environment warnings in the build sandbox:

- `chromadb` is not installed here, but it remains listed in `requirements.txt`.
- Ollama is not running here, so AI health reports an environment warning.

## Next likely step

v11.1 should probably be **Workspace Patch Review Queue**:

- save workspace dev-loop preview records
- list pending workspace patch plans
- mark workspace plans reviewed/rejected/ready
- connect `/workspace` to patch-review records
- keep multi-project changes preview-first until review history is boring

Boring review history is good. Exciting review history means something is on fire.

---

# Eidolon v10.0 - Asymmetric Multi-Project Development Loop

v10.0 bundles the v9.1 through v10.0 project-intelligence roadmap into one packaged release. The big shift is that Eidolon can now map its own codebase, infer task dependencies, plan verification by file impact, score patch risk, review staged patches from the dashboard/API, index its project history, understand a multi-project workspace foundation, compare task queues across projects, and run an asymmetric multi-project development preview that stops before mutation. Stopping remains the most underrated feature in software, right behind "not deleting the user's work."

This release also hardens the v9.0 controlled-build API and rollback behavior based on review findings:

- GET routes are preview-only and no longer trigger live controlled work.
- `GET /api/supervised-dev-loop` is disabled with a 405 response; supervised loop execution is POST-only.
- Live POST routes now require explicit JSON confirmation strings.
- GET planner/stage/diff routes are read-only preview surfaces; POST routes save workspace state.
- Dry-run apply reports now write to `latest_dry_run_apply_report.json` instead of overwriting the latest real apply report.
- Rollback now verifies the current file hash still matches the recorded applied hash before restoring a backup, so newer manual edits are not quietly flattened by the rollback bulldozer.

## What changed in v10.0

- Added `conscious_agent/project_intelligence.py`
  - v9.1 codebase map
  - v9.2 dependency-aware task planning
  - v9.3 test planner
  - v9.4 patch risk analyzer
  - v9.5 patch review report
  - v9.7 project memory index
  - v9.8 multi-project workspace status
  - v9.9 cross-project task review
  - v10.0 asymmetric multi-project development loop preview
- Updated `conscious_agent/controlled_build_cycle.py`
  - controlled-build version is now `10.0`
  - dry-run apply no longer overwrites the real latest apply report
  - rollback checks current file hashes before restoring backups
  - GET-compatible preview helpers can avoid saving workspace state
  - README gate now checks v8.1 through v10.0 sections
- Updated `conscious_agent/api_server.py`
  - API version is now `10.0`
  - live controlled work is POST-only
  - live POST calls require explicit JSON confirmation
  - added project-intelligence endpoints
  - disabled GET execution of `/api/supervised-dev-loop`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `10.0`
  - added `/patch-review`
  - added `/intelligence`
  - updated `/api-info` to document preview-only GET and POST mutation boundaries
- Updated `conscious_agent/main.py`
  - added v9.1-v10.0 project-intelligence CLI commands
- Updated `conscious_agent/operational_readiness.py`
  - operational readiness version is now `10.0`
  - hardening checks include project-intelligence CLI/API/README surfaces
- Updated `conscious_agent/stabilization_checkpoint.py`
  - checkpoint version is now `10.0`
  - checks `project_intelligence.py`, the new CLI flags, API routes, and dashboard pages
- Updated `conscious_agent/command_runner.py`
  - whitelisted the new read-only project-intelligence commands
- Updated `tools/smoke_check.py`
  - validates project intelligence reports and commands
  - checks controlled-build version `10.0`
- Updated `conscious_agent/settings_manager.py`, `data/settings.json`, `data/projects.json`
  - metadata now reflects `10.0`
- Added workspace foundation files:
  - `data/workspaces/projects.json`
  - `data/workspaces/active_project.json`

## v9.1 - Codebase Map

v9.1 gives Eidolon a structured view of its own files. This is where it learns where its limbs are before trying to juggle tools with them.

New CLI:

```powershell
python conscious_agent/main.py --codebase-map
python conscious_agent/main.py --codebase-map --readiness-json
```

New API:

```text
GET /api/codebase-map
```

New dashboard surface:

```text
/intelligence
```

The map reports:

- project file counts
- Python module counts
- major module roles
- module imports
- CLI flags
- API route hints
- dashboard routes
- data file samples
- risky files

## v9.2 - Dependency-Aware Task Planning

v9.2 adds task dependency hints. It does not solve software planning forever, because nothing does, but it at least stops pretending every task is a decorative sticky note.

New CLI:

```powershell
python conscious_agent/main.py --task-dependencies
python conscious_agent/main.py --task-dependencies --readiness-json
```

New API:

```text
GET /api/task-dependencies
```

It infers likely affected files and required checks from task text:

- dashboard work implies dashboard route review
- API work implies API route review
- CLI work implies `main.py` and command checks
- controlled-build or rollback work implies controlled-build verification
- every real project patch still requires README review

## v9.3 - Test Planner

v9.3 adds a targeted test-plan report.

New CLI:

```powershell
python conscious_agent/main.py --test-plan
python conscious_agent/main.py --test-plan --readiness-json
```

New API:

```text
GET /api/test-plan
```

The planner looks at current controlled-build plan/staged files and recommends checks such as:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --readme-gate
python tools/smoke_check.py
```

File-specific checks are added for CLI, API, dashboard, controlled-build, and project-intelligence changes.

## v9.4 - Patch Risk Analyzer

v9.4 scores the risk of the current staged/controlled patch.

New CLI:

```powershell
python conscious_agent/main.py --patch-risk
python conscious_agent/main.py --patch-risk --readiness-json
```

New API:

```text
GET /api/patch-risk
```

Risk factors include:

- changes to safety-sensitive files
- changes to CLI/API/dashboard routing
- changes to settings or command runner behavior
- proposed file deletion
- large multi-file patches
- code/data changes without README involvement

Risk levels:

```text
LOW
MEDIUM
HIGH
BLOCKED
```

## v9.5 - Dashboard Patch Review UI

v9.5 adds a browser-facing patch review page.

New dashboard route:

```text
/patch-review
```

New CLI:

```powershell
python conscious_agent/main.py --patch-review
python conscious_agent/main.py --patch-review --readiness-json
```

New API:

```text
GET /api/patch-review
```

The patch review combines:

- patch workspace status
- staged diff preview
- patch risk score
- targeted test plan
- README enforcement gate

The page is read-only. It reviews the patch instead of applying it, which is the dashboard equivalent of touching the stove with a thermometer instead of a hand.

## v9.6 - API Build Control Hardening

v9.6 tightens the local API build-control boundary.

Changed API behavior:

```text
GET  /api/controlled-self-build        # preview-only
POST /api/controlled-self-build       # live requires confirm=LIVE_CONTROLLED_BUILD
GET  /api/controlled-build/plan-patch # preview-only
POST /api/controlled-build/plan-patch # saves workspace state
GET  /api/controlled-build/stage-patch # preview-only
POST /api/controlled-build/stage-patch # saves workspace state
GET  /api/controlled-build/preview-diff # preview-only
POST /api/controlled-build/preview-diff # saves validation state
POST /api/controlled-build/cycle      # live requires confirm=LIVE_CONTROLLED_BUILD_CYCLE
POST /api/supervised-dev-loop         # live requires confirm=LIVE_SUPERVISED_DEV_LOOP
```

Removed unsafe behavior:

- GET no longer accepts `live=true` as a path to live work.
- GET `/api/supervised-dev-loop` no longer runs the supervised loop.
- GET planning/staging/diff routes no longer write workspace state.

Explicit live confirmations:

```json
{"live": true, "approve": true, "confirm": "LIVE_CONTROLLED_BUILD"}
```

```json
{"live": true, "approve": true, "confirm": "LIVE_CONTROLLED_BUILD_CYCLE"}
```

```json
{"live": true, "approve": true, "confirm": "LIVE_SUPERVISED_DEV_LOOP"}
```

## v9.7 - Project Memory Index

v9.7 adds a project memory index over README history and controlled-build records.

New CLI:

```powershell
python conscious_agent/main.py --project-memory-index
python conscious_agent/main.py --project-memory-index --readiness-json
```

New API:

```text
GET /api/project-memory-index
```

It reports:

- README version markers
- controlled-build report count
- patch workspace state files
- latest report file sample
- recurring documentation gaps

This helps Eidolon avoid rediscovering its own history like a goldfish with a sprint board.

## v9.8 - Multi-Project Workspace Foundation

v9.8 adds the first workspace foundation for multiple projects.

New files:

```text
data/workspaces/projects.json
data/workspaces/active_project.json
```

New CLI:

```powershell
python conscious_agent/main.py --workspace-status
python conscious_agent/main.py --workspace-status --readiness-json
```

New API:

```text
GET /api/workspace-status
```

It reports:

- known projects
- active project
- project roots
- project versions
- project priority
- whether the root exists
- whether the project is marked safe to modify

No multi-project editing is enabled here. It is awareness first, tools later, chaos ideally never.

## v9.9 - Cross-Project Task Scheduler

v9.9 compares task availability across known projects.

New CLI:

```powershell
python conscious_agent/main.py --cross-project-task-review
python conscious_agent/main.py --cross-project-task-review --readiness-json
```

New API:

```text
GET /api/cross-project-task-review
```

It reviews:

- project priority
- safe-to-modify status
- available task count
- top task candidates per project
- selected project candidate

This is still planning-only. It does not modify multiple projects, because mixing project state is how you get a software smoothie nobody ordered.

## v10.0 - Asymmetric Multi-Project Development Loop

v10.0 adds the asymmetric loop preview.

New CLI:

```powershell
python conscious_agent/main.py --asymmetric-dev-loop
python conscious_agent/main.py --asymmetric-dev-loop --readiness-json
```

New API:

```text
GET /api/asymmetric-dev-loop
```

The preview does this:

1. Scans known workspaces.
2. Reviews task availability across projects.
3. Selects one safe project candidate.
4. Maps the active codebase.
5. Builds dependency and test summaries.
6. Scores current patch risk.
7. Stops before mutation.

Important limit:

```text
Only one project may be selected per run, and the v10.0 loop preview does not write project files.
```

That gives Eidolon asymmetric awareness without letting it swing a hammer in three rooms at once. Sensible, which is always suspicious but useful.

## API safety fixes included in v10.0

### GET routes are preview-only

`GET /api/controlled-self-build` now always calls controlled self-build in preview mode. If `live=true` or `approve=true` appears in the query string, the response includes a warning instead of doing live work.

### Supervised loop is POST-only

`GET /api/supervised-dev-loop` now returns a 405-style API error. Use POST with JSON instead.

### Planning/staging GET routes do not mutate workspace state

These are preview-only now:

```text
GET /api/controlled-build/plan-patch
GET /api/controlled-build/stage-patch
GET /api/controlled-build/preview-diff
```

These are the mutating versions:

```text
POST /api/controlled-build/plan-patch
POST /api/controlled-build/stage-patch
POST /api/controlled-build/preview-diff
```

### Dry-run apply no longer replaces rollback target

Dry-run apply reports are saved separately:

```text
data/patch_workspace/latest_dry_run_apply_report.json
```

The real rollback pointer remains:

```text
data/patch_workspace/latest_apply_report.json
```

### Rollback now protects newer edits

Rollback checks:

```text
current file sha256 == applied_sha256 from latest apply report
```

If the file changed after apply, rollback refuses to overwrite it and reports the mismatch.

## v10.0 CLI summary

```powershell
python conscious_agent/main.py --codebase-map
python conscious_agent/main.py --task-dependencies
python conscious_agent/main.py --test-plan
python conscious_agent/main.py --patch-risk
python conscious_agent/main.py --patch-review
python conscious_agent/main.py --project-memory-index
python conscious_agent/main.py --workspace-status
python conscious_agent/main.py --cross-project-task-review
python conscious_agent/main.py --asymmetric-dev-loop
```

## v10.0 API summary

```text
GET  /api/codebase-map
GET  /api/task-dependencies
GET  /api/test-plan
GET  /api/patch-risk
GET  /api/patch-review
GET  /api/project-memory-index
GET  /api/workspace-status
GET  /api/cross-project-task-review
GET  /api/asymmetric-dev-loop
```

## Verification performed for v10.0

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --codebase-map
python conscious_agent/main.py --task-dependencies
python conscious_agent/main.py --test-plan
python conscious_agent/main.py --patch-risk
python conscious_agent/main.py --patch-review
python conscious_agent/main.py --project-memory-index
python conscious_agent/main.py --workspace-status
python conscious_agent/main.py --cross-project-task-review
python conscious_agent/main.py --asymmetric-dev-loop
python conscious_agent/main.py --controlled-self-build --select-task
python conscious_agent/main.py --controlled-self-build --plan-patch
python conscious_agent/main.py --controlled-self-build --stage-patch
python conscious_agent/main.py --controlled-self-build --preview-diff
python conscious_agent/main.py --controlled-self-build --apply-staged-patch --dry-run
python conscious_agent/main.py --readme-gate
python conscious_agent/main.py --supervised-dev-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

Known environment warnings in this sandbox remain boring but honest:

- `chromadb` may be missing if dependencies were not installed, but it remains listed in `requirements.txt`.
- Ollama may be unreachable if the local Ollama service is not running.
- Older patch records can still report missing backup paths; the integrity system surfaces those instead of pretending the attic is clean.

---

# Eidolon v9.0 - Supervised Autonomous Development Loop

v9.0 bundles the full v8.1 through v9.0 controlled-build roadmap into one packaged release. The major shift is that Eidolon now has a real staged development lane: it can select a safe task, create a patch plan, stage proposed changes in a workspace, preview diffs, apply only with explicit approval, verify the latest patch, roll back the latest controlled patch, enforce README updates, run a full controlled build cycle, and stop after one supervised development loop. That last word, stop, is doing heroic work here.

This is still preview-first. Live writes require explicit operator approval and use backups. The system does not silently self-modify, does not bypass guardrails, and does not run forever like a cursed office printer.

## What changed in v9.0

- Added `conscious_agent/controlled_build_cycle.py`
  - v8.1 controlled task selection
  - v8.2 controlled patch planning
  - v8.3 patch workspace and staging support under `data/patch_workspace/`
  - v8.4 staged diff preview
  - v8.5 guarded staged patch apply
  - v8.6 latest patch verification
  - v8.7 latest controlled patch rollback
  - v8.8 README enforcement gate
  - v8.9 full controlled build cycle
  - v9.0 one-cycle supervised autonomous development loop
- Updated `conscious_agent/main.py`
  - added `--select-task`
  - added `--plan-patch`
  - added `--patch-workspace-status`
  - added `--stage-patch`
  - added `--preview-diff`
  - added `--apply-staged-patch`
  - added `--verify-latest-patch`
  - added `--rollback-latest-patch`
  - added `--readme-gate`
  - added `--controlled-self-build-cycle`
  - added `--supervised-dev-loop`
- Updated `conscious_agent/api_server.py`
  - API version is now `9.0`
  - added controlled-build endpoints under `/api/controlled-build/...`
  - added `/api/supervised-dev-loop`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `9.0`
  - added `/build-cycle`
  - updated `/api-info` with the v8.1-v9.0 surfaces
- Updated `conscious_agent/operational_readiness.py`
  - operational readiness version is now `9.0`
  - hardening checks now include the v8.1-v9.0 CLI/API/dashboard/README surfaces
- Updated `conscious_agent/stabilization_checkpoint.py`
  - checkpoint version is now `9.0`
  - checks `controlled_build_cycle.py` and the new CLI/API/dashboard surfaces
- Updated `conscious_agent/command_runner.py`
  - whitelisted the new read-only/preview controlled-build commands
  - live write actions still require explicit approval in their own command path
- Updated `tools/smoke_check.py`
  - validates `controlled_build_cycle.py`
  - checks report shapes and CLI commands for v8.1-v9.0
- Updated `conscious_agent/settings_manager.py`, `data/settings.json`, and `data/projects.json`
  - metadata now reflects `9.0`

## v8.1 - Controlled Self-Build Task Selection

v8.1 lets Eidolon choose the next safe task instead of grabbing work like a raccoon in a parts bin.

New CLI:

```powershell
python conscious_agent/main.py --controlled-self-build --select-task
python conscious_agent/main.py --controlled-self-build --select-task --readiness-json
```

New API:

```text
GET /api/controlled-build/select-task
```

The selector evaluates:

- task status
- priority
- risk
- approval requirement
- whether the task is safe for controlled self-build

If no safe queued task exists, it selects a synthetic low-risk README/workspace probe so the loop can still be tested without pretending there is real work. Fake work is bad. Synthetic safety probes are acceptable little training wheels.

## v8.2 - Controlled Patch Planner

v8.2 adds a structured patch plan before anything stages or writes.

New CLI:

```powershell
python conscious_agent/main.py --controlled-self-build --plan-patch
python conscious_agent/main.py --controlled-self-build --plan-patch --readiness-json
```

New API:

```text
GET /api/controlled-build/plan-patch
```

The plan is saved to:

```text
data/patch_workspace/current_plan.json
```

It records:

- selected task
- target version
- expected files to change
- expected verification commands
- README sections required
- rollback strategy
- risk rating
- approval requirement
- staging policy

## v8.3 - Patch Workspace / Staging Area

v8.3 adds the staging workspace:

```text
data/patch_workspace/
  current_plan.json
  proposed_changes.json
  file_diffs/
  validation_report.json
  latest_apply_report.json
  latest_rollback_report.json
```

New CLI:

```powershell
python conscious_agent/main.py --patch-workspace-status
python conscious_agent/main.py --controlled-self-build --stage-patch
```

New API:

```text
GET /api/controlled-build/workspace
GET /api/controlled-build/stage-patch
```

Staging writes proposal metadata and diff files only. It does not touch source files. Imagine a robot holding a wrench behind glass. Somehow, safer.

## v8.4 - File Diff Preview System

v8.4 adds staged diff preview.

New CLI:

```powershell
python conscious_agent/main.py --controlled-self-build --preview-diff
python conscious_agent/main.py --controlled-self-build --preview-diff --doctor-full
```

New API:

```text
GET /api/controlled-build/preview-diff
```

The preview shows:

- files staged
- action type
- added/removed line counts
- diff preview text
- metadata-only impact surfaces
- warnings before apply

Rule introduced:

```text
No staged patch should be applied until a diff preview exists.
```

## v8.5 - Apply Controlled Patch

v8.5 adds guarded staged patch apply.

New CLI:

```powershell
python conscious_agent/main.py --controlled-self-build --apply-staged-patch --dry-run
python conscious_agent/main.py --controlled-self-build --apply-staged-patch --approve-controlled-self-build
```

New API:

```text
POST /api/controlled-build/apply-staged-patch
```

Apply behavior:

- requires a staged patch
- validates current file hashes before writing
- creates backups under `data/controlled_build_backups/`
- records latest apply metadata
- skips metadata-only source impact rows
- blocks live write unless `--approve-controlled-self-build` is present

This is where “controlled” earns its paycheck.

## v8.6 - Auto-Verify Applied Patch

v8.6 adds verification for the latest controlled patch/apply report.

New CLI:

```powershell
python conscious_agent/main.py --verify-latest-patch
python conscious_agent/main.py --verify-latest-patch --doctor-full
```

New API:

```text
POST /api/controlled-build/verify-latest-patch
```

Verification runs fixed safe checks:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --readme-gate
```

It reports:

```text
passed
passed_with_warnings
failed
rollback_recommended
```

## v8.7 - Rollback Latest Patch

v8.7 adds rollback for the latest controlled patch.

New CLI:

```powershell
python conscious_agent/main.py --rollback-latest-patch --dry-run
python conscious_agent/main.py --rollback-latest-patch --approve-controlled-self-build
```

New API:

```text
POST /api/controlled-build/rollback-latest-patch
```

Rollback behavior:

- reads `latest_apply_report.json`
- verifies backup paths
- restores only files that were actually applied
- skips metadata-only rows
- records latest rollback metadata
- blocks live restore unless `--approve-controlled-self-build` is present

Rollback remains boring. Boring is what you want when undoing file edits.

## v8.8 - README Enforcement Gate

v8.8 adds a README gate.

New CLI:

```powershell
python conscious_agent/main.py --readme-gate
python conscious_agent/main.py --readme-gate --readiness-json
```

New API:

```text
GET /api/controlled-build/readme-gate
```

It checks:

- README includes v8.1 through v9.0 notes
- settings metadata is on v9.0
- latest applied controlled patch included a README update when files changed

This matches Marcus's rule: every code/project patch must update the README unless told otherwise. Software has enough amnesia already.

## v8.9 - Full Controlled Build Cycle

v8.9 chains the pieces together.

New CLI:

```powershell
python conscious_agent/main.py --controlled-self-build-cycle
python conscious_agent/main.py --controlled-self-build-cycle --readiness-json
```

Live write path remains explicit:

```powershell
python conscious_agent/main.py --controlled-self-build-cycle --controlled-self-build-live --approve-controlled-self-build
```

New API:

```text
POST /api/controlled-build/cycle
```

Cycle flow:

```text
select task
create patch plan
stage patch
preview diff
apply dry-run by default
verify latest patch
check patch integrity
run README gate
save cycle report
stop
```

Default behavior is preview/dry-run. Live apply requires approval.

## v9.0 - Supervised Autonomous Development Loop

v9.0 adds the one-cycle supervised dev loop.

New CLI:

```powershell
python conscious_agent/main.py --supervised-dev-loop
python conscious_agent/main.py --supervised-dev-loop --readiness-json
```

Live path:

```powershell
python conscious_agent/main.py --supervised-dev-loop --controlled-self-build-live --approve-controlled-self-build
```

New API:

```text
POST /api/supervised-dev-loop
```

The supervised loop:

1. Runs doctor/guardrail context.
2. Runs controlled self-build preview context.
3. Runs one full controlled build cycle.
4. Applies only if live mode and explicit approval are provided.
5. Stops after one bounded cycle.
6. Reports the next recommended task.

The stop behavior is intentional. No recursive self-improvement spiral. No infinite loop. No “I upgraded my upgrader and now it wants stock options.”

## New dashboard/API paths after v9.0

Dashboard:

```text
http://127.0.0.1:8765/build-cycle
```

API:

```text
GET  /api/controlled-build/select-task
GET  /api/controlled-build/plan-patch
GET  /api/controlled-build/workspace
GET  /api/controlled-build/stage-patch
GET  /api/controlled-build/preview-diff
POST /api/controlled-build/apply-staged-patch
POST /api/controlled-build/verify-latest-patch
POST /api/controlled-build/rollback-latest-patch
GET  /api/controlled-build/readme-gate
POST /api/controlled-build/cycle
POST /api/supervised-dev-loop
```

## Recommended verification after v9.0

Run these from the project root:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --doctor --doctor-full
python conscious_agent/main.py --controlled-self-build --select-task
python conscious_agent/main.py --controlled-self-build --plan-patch
python conscious_agent/main.py --patch-workspace-status
python conscious_agent/main.py --controlled-self-build --stage-patch
python conscious_agent/main.py --controlled-self-build --preview-diff
python conscious_agent/main.py --controlled-self-build --apply-staged-patch --dry-run
python conscious_agent/main.py --verify-latest-patch
python conscious_agent/main.py --readme-gate
python conscious_agent/main.py --controlled-self-build-cycle
python conscious_agent/main.py --supervised-dev-loop
python tools/smoke_check.py
```

## Verification performed for v9.0

These checks were run after patching:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --controlled-self-build --select-task
python conscious_agent/main.py --controlled-self-build --plan-patch
python conscious_agent/main.py --patch-workspace-status
python conscious_agent/main.py --controlled-self-build --stage-patch
python conscious_agent/main.py --controlled-self-build --preview-diff
python conscious_agent/main.py --controlled-self-build --apply-staged-patch --dry-run
python conscious_agent/main.py --verify-latest-patch
python conscious_agent/main.py --readme-gate
python conscious_agent/main.py --controlled-self-build-cycle
python conscious_agent/main.py --supervised-dev-loop
python conscious_agent/main.py --doctor
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

Known sandbox warnings remain expected:

- `chromadb` may be missing if the active Python environment has not installed `requirements.txt`.
- Ollama may be unreachable if the local service is not running.
- Older patch records can still report missing backup paths. The integrity report surfaces that instead of pretending rollback is guaranteed. Because lying to yourself is cheaper only until restore day.

## Next likely step

v9.1 should improve the staged patch generator so it can turn selected low-risk tasks into real source-file proposals instead of mostly README/workspace probes. The apply/verify/rollback lane now exists; next, the patch generator needs better hands.

---

# Eidolon v8.0 - Controlled Self-Build Checkpoint Suite

v8.0 bundles the full v7.1 through v8.0 stabilization roadmap into one packaged release. It keeps the project in the same safety posture: read-only diagnostics by default, explicit approval for live controlled work, and no silent patch/application behavior. The exciting part is that Eidolon can now inspect the floor before trying to walk across it. Revolutionary, if you ignore every toddler ever.

## What changed in v8.0

- Added `conscious_agent/operational_readiness.py`
  - centralizes the v7.1-v8.0 operational reports
  - keeps reports read-only by default
  - exposes human-readable text and JSON-ready report dictionaries
  - adds one controlled self-build entrypoint that gates live behavior behind doctor status, confidence score, closure guardrails, and explicit approval
- Updated `conscious_agent/main.py`
  - added `--doctor`
  - added `--doctor-full`
  - added `--readiness-json`
  - added `--repair-suggestions`
  - added `--patch-integrity`
  - added `--project-snapshot`
  - added `--task-review`
  - added `--recovery-drill`
  - added `--stable-loop-confidence`
  - added `--hardening-report`
  - added `--controlled-self-build`
  - added `--controlled-self-build-live`
  - added `--approve-controlled-self-build`
  - added `--controlled-self-build-steps`
- Updated `conscious_agent/api_server.py`
  - API version is now `8.0`
  - added `GET /api/doctor`
  - added `GET /api/repair-suggestions`
  - added `GET /api/patch-integrity`
  - added `GET /api/project-snapshot`
  - added `GET /api/tasks/review`
  - added `GET /api/recovery-drill`
  - added `GET /api/stable-loops/confidence`
  - added `GET /api/hardening-report`
  - added `GET /api/controlled-self-build`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `8.0`
  - polished `/stabilization` with confidence and repair suggestion cards
  - added `/doctor` as a dashboard hub for all new operational reports
  - updated `/api-info` to list the new local API surfaces
- Updated `conscious_agent/stabilization_checkpoint.py`
  - checkpoint version is now `8.0`
  - checks the new CLI flags, API endpoints, dashboard route, and `operational_readiness.py`
  - recommended commands now include doctor mode, repair suggestions, confidence scoring, and controlled self-build preview
- Updated `conscious_agent/command_runner.py`
  - whitelisted all new read-only operational commands
  - whitelisted the explicit controlled self-build flags
- Updated `tools/smoke_check.py`
  - validates `operational_readiness.py`
  - checks the new report shapes and text output
  - runs the new CLI commands in the smoke sequence
- Updated `conscious_agent/settings_manager.py`, `data/settings.json`, and `data/projects.json`
  - metadata now reflects `8.0`

## v7.1 - Stabilization Dashboard Polish

v7.1 improves the dashboard view for the checkpoint added in v7.0.

- `/stabilization` now groups:
  - checkpoint status
  - pass/warn/fail counts
  - blocker list
  - warning list
  - stable-loop confidence
  - repair suggestions
  - recommended commands
- The page links directly to:
  - `/api/stabilization-checkpoint?full=true`
  - `/api/doctor?full=true`
- The goal is visual clarity, not new autonomy. Because apparently reading a giant raw JSON blob is not everyone’s idea of a fulfilling evening.

## v7.2 - One-Command Doctor Mode

v7.2 adds doctor mode.

New CLI:

```powershell
python conscious_agent/main.py --doctor
python conscious_agent/main.py --doctor --doctor-full
python conscious_agent/main.py --doctor --readiness-json
```

New API:

```text
GET /api/doctor
GET /api/doctor?full=true
```

New dashboard:

```text
http://127.0.0.1:8765/doctor
```

Doctor mode combines:

- stabilization checkpoint
- stable-loop confidence
- repair suggestions
- patch integrity
- project snapshot
- task review
- recovery drill
- hardening report

It returns:

```text
READY
READY_WITH_WARNINGS
BLOCKED
```

## v7.3 - Self-Repair Suggestions

v7.3 adds suggestion-only repair guidance.

New CLI:

```powershell
python conscious_agent/main.py --repair-suggestions
python conscious_agent/main.py --repair-suggestions --readiness-json
```

New API:

```text
GET /api/repair-suggestions
```

The report turns checkpoint and settings-health problems into plain fixes. Examples:

- missing `chromadb` -> install requirements
- Ollama unreachable -> start Ollama and rerun settings health
- malformed JSON -> repair or restore that file
- unresolved stable-loop follow-ups -> resolve or close follow-up chains

This does not automatically install packages, start services, rewrite JSON, or pretend warnings are confetti.

## v7.4 - Patch Integrity System

v7.4 adds patch metadata and rollback integrity review.

New CLI:

```powershell
python conscious_agent/main.py --patch-integrity
python conscious_agent/main.py --patch-integrity --doctor-full
```

New API:

```text
GET /api/patch-integrity
```

The report checks patch records for:

- patch id
- target file
- patch status
- proposed hash
- applied hash
- backup path for applied patches
- missing rollback metadata
- README notes for the current release

This gives Eidolon a way to inspect whether its patch history is trustworthy before leaning on rollback like it is a magic undo button. It is not magic. It is just files wearing a helmet.

## v7.5 - Project State Snapshot

v7.5 adds a single “where are we?” report.

New CLI:

```powershell
python conscious_agent/main.py --project-snapshot
python conscious_agent/main.py --project-snapshot --readiness-json
```

New API:

```text
GET /api/project-snapshot
```

The snapshot includes:

- active project
- settings version
- task totals and status counts
- pending approval count
- patch count
- test report count
- test review count
- work-cycle count
- stable-loop count
- stabilization status
- stable-loop confidence score
- next recommended commands

## v7.6 - Better Task Queue Review

v7.6 adds task lifecycle/risk review.

New CLI:

```powershell
python conscious_agent/main.py --task-review
python conscious_agent/main.py --task-review --doctor-full
```

New API:

```text
GET /api/tasks/review
```

The task review reports:

- task id
- title
- task status
- lifecycle stage
- estimated risk
- approval requirement
- warnings for medium/high-risk tasks

This gives controlled self-build a task-facing checkpoint instead of just grabbing the next item and hoping the universe is gentle. It is not.

## v7.7 - Recovery Drill Mode

v7.7 adds read-only recovery drills.

New CLI:

```powershell
python conscious_agent/main.py --recovery-drill
python conscious_agent/main.py --recovery-drill --doctor-full
```

New API:

```text
GET /api/recovery-drill
```

It simulates recovery expectations for:

- failed patch apply
- failed test run
- missing dependency
- unresolved stable-loop follow-up
- unavailable AI/Ollama

It does not intentionally break files. A bold and controversial design choice.

## v7.8 - Stable Loop Confidence Score

v7.8 adds a readiness score for stable-loop and self-build workflows.

New CLI:

```powershell
python conscious_agent/main.py --stable-loop-confidence
python conscious_agent/main.py --stable-loop-confidence --readiness-json
```

New API:

```text
GET /api/stable-loops/confidence
```

Scoring considers:

- stabilization blockers
- stabilization warnings
- closure guardrails
- recoverable task backlog
- Ollama health

Statuses:

```text
90-100  ready
75-89   ready_with_warnings
50-74   limited_mode
0-49    blocked
```

## v7.9 - Pre-v8 Hardening Pass

v7.9 adds a hardening report across the new surface area.

New CLI:

```powershell
python conscious_agent/main.py --hardening-report
python conscious_agent/main.py --hardening-report --doctor-full
```

New API:

```text
GET /api/hardening-report
```

It checks that the new version surfaces exist in:

- CLI parser
- command whitelist
- API route docs
- dashboard route surfaces
- README notes
- Python compile surface

This is the release that checks whether all the release machinery remembered to show up. The bar is underground, yet software keeps tripping on it.

## v8.0 - Controlled Self-Build Loop

v8.0 adds the first controlled self-build entrypoint.

Preview mode:

```powershell
python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop
```

JSON preview:

```powershell
python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop --readiness-json
```

Bounded step preview:

```powershell
python conscious_agent/main.py --controlled-self-build --controlled-self-build-steps 3 --no-ai-stable-loop
```

Live mode requires all of this:

```powershell
python conscious_agent/main.py --controlled-self-build --controlled-self-build-live --approve-controlled-self-build --controlled-self-build-steps 1
```

Live controlled self-build is gated by:

- doctor mode not blocked
- confidence score at least 90%
- closure guardrails allowing live advancement
- explicit `--approve-controlled-self-build`
- existing stable-loop safety behavior
- existing approval gates for risky work

This is not unrestricted self-modification. It is a supervised, bounded, inspected route into the existing stable loop. The robot gets a leash, a checklist, and absolutely no flamethrower.

## New recommended verification after v8.0

Run these from the project root:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --doctor --doctor-full
python conscious_agent/main.py --repair-suggestions
python conscious_agent/main.py --patch-integrity
python conscious_agent/main.py --project-snapshot
python conscious_agent/main.py --task-review
python conscious_agent/main.py --recovery-drill
python conscious_agent/main.py --stable-loop-confidence
python conscious_agent/main.py --hardening-report --doctor-full
python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop
python tools/smoke_check.py
```

## Verification performed for v8.0

These checks were run after patching:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --doctor
python conscious_agent/main.py --repair-suggestions
python conscious_agent/main.py --patch-integrity
python conscious_agent/main.py --project-snapshot
python conscious_agent/main.py --task-review
python conscious_agent/main.py --recovery-drill
python conscious_agent/main.py --stable-loop-confidence
python conscious_agent/main.py --hardening-report
python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python tools/smoke_check.py
```

API/dashboard surface checks were also exercised in-process for:

```text
/api/doctor
/api/repair-suggestions
/api/patch-integrity
/api/project-snapshot
/api/tasks/review
/api/recovery-drill
/api/stable-loops/confidence
/api/hardening-report
/api/controlled-self-build
/stabilization
/doctor
```

Observed sandbox warnings:

- `chromadb` is not installed in this sandbox environment, but it is listed in `requirements.txt`.
- Ollama is not running in this sandbox, so local AI health reports warn correctly.
- Existing older patch records report some missing backup paths in `--patch-integrity`; the new integrity system surfaces those instead of pretending rollback is guaranteed.

## Known environment notes

- Missing `chromadb` is reported as an environment/setup warning when the current Python environment has not installed `requirements.txt`.
- Ollama being unreachable is a local service/model setup warning unless an AI-dependent command is being run live.
- The controlled self-build path should be used in preview/no-AI mode until the doctor report and confidence score are clean enough to justify live work.

## Next likely step

v8.1 should use controlled self-build only on a tiny, low-risk README or report-format task first. No big feature jumps yet. Make the little robot prove it can carry a paperclip before handing it the toolbox.

---

# Eidolon v7.0 - Stabilization Checkpoint

v7.0 stops feature expansion for one pass and adds a read-only stabilization checkpoint across the whole current loop. It checks files, JSON storage, Python compile health, core imports, environment dependencies, settings, command whitelist coverage, task lifecycle, recovery, cycle policy, stable-loop preflight, closure guardrails, follow-up completion, dashboard/API route surfaces, and smoke-test readiness. It does not apply patches, approve actions, run live stable loops, archive records, or start services. An actual checkpoint, not a motivational poster taped over a broken build.

## What changed in v7.0

- Added `conscious_agent/stabilization_checkpoint.py`
  - builds a read-only PASS/WARN/FAIL checkpoint report
  - separates code blockers from environment warnings such as missing optional/local packages
  - checks required files, JSON parse health, compile/import health, settings strictness, command whitelist coverage, task lifecycle/recovery/cycle policy, stable-loop preflight, stable-loop closure guardrails, follow-up lifecycle/completion, API/dashboard surfaces, and smoke readiness
  - returns recommended verification commands for the operator
- Updated `conscious_agent/main.py`
  - added `--stabilization-checkpoint`
  - added `--stabilization-full`
  - added `--stabilization-json`
- Updated `conscious_agent/api_server.py`
  - API version is now `7.0`
  - added `GET /api/stabilization-checkpoint`
  - supports `?full=true` and `?project=eidolon`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `7.0`
  - added `/stabilization`
  - added a nav tab for Stabilization
  - shows pass/warn/fail counts, blockers, warnings, recommended commands, and a full report block
- Updated `tools/smoke_check.py`
  - includes stabilization checkpoint checks
  - runs the new checkpoint CLI command
  - classifies missing `chromadb` as an environment/setup warning instead of making the smoke check look like project code is broken when the package simply is not installed in the current Python environment
- Updated `conscious_agent/command_runner.py`
  - whitelisted the read-only stabilization CLI flags
- Updated `data/settings.json`, `settings_manager.py`, and `data/projects.json` for v7.0 metadata.

## New CLI commands

Run the checkpoint:

```powershell
python conscious_agent/main.py --stabilization-checkpoint
```

Run the full checkpoint with every item shown:

```powershell
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
```

Emit the checkpoint as JSON:

```powershell
python conscious_agent/main.py --stabilization-checkpoint --stabilization-json
```

## New dashboard/API paths

Dashboard:

```text
http://127.0.0.1:8765/stabilization
```

API:

```text
GET /api/stabilization-checkpoint
GET /api/stabilization-checkpoint?full=true
```

## Recommended troubleshooting after v7.0

Run these from the project root:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --stable-loop-guardrails
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --stable-loop-followup-completion-report unresolved
python tools/smoke_check.py
```

If the checkpoint returns `WARN` only because `chromadb` is missing, install the project requirements in the active environment:

```powershell
.\setup.ps1
```

or manually:

```powershell
python -m pip install -r requirements.txt
```

If the checkpoint returns `WARN` because stable-loop closure guardrails are blocking live advancement, resolve or close the unresolved follow-up chains before running live:

```powershell
python conscious_agent/main.py --list-stable-loop-followup-completions unresolved
python conscious_agent/main.py --create-stable-loop-decision-followups action_required --dry-run
python conscious_agent/main.py --resolve-stable-loop-followups stableloop_ID
python conscious_agent/main.py --mark-stable-loop-followup-closed stableloop_ID
```

## Verification performed for v7.0

These checks were run after patching:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stabilization-checkpoint --stabilization-full
python conscious_agent/main.py --stabilization-checkpoint --stabilization-json
python conscious_agent/main.py --stable-loop-guardrails
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --stable-loop-followup-completion-report all
python tools/smoke_check.py
```

Known environment note from this sandbox: Ollama is not running here, so `--settings-health` reports a local service connection failure. That is expected outside the user's local Ollama setup. The checkpoint/smoke path now reports missing `chromadb` as an environment warning rather than a project-code compile failure.

## Next likely step

v7.1 should build on the checkpoint by adding a lightweight dashboard/API "run verification plan" view that launches only approved read-only checks and stores the result as a saved stabilization report. Still no new live autonomy until the checkpoint is boringly green. Boring is good. Boring is how files survive.

---

# Eidolon v6.9 - Stable Loop Closure-Aware Work Cycle Guardrails

v6.9 adds live-run guardrails around the stable supervised loop. v6.8 made decision follow-up chains reportable; v6.9 makes those reports matter by blocking new live stable-loop advancement while unresolved action-required follow-up chains still exist. Preview/preflight still works, because seeing the next move is useful. Live runs now need either clear closure guardrails or an explicit bypass flag, because apparently one mess should be cleaned before starting another. Revolutionary little chore chart.

## What changed in v6.9

- Added `conscious_agent/stable_loop_guardrails.py`
  - reports unresolved follow-up chains
  - counts missing follow-up tasks, open follow-up chains, ready-to-resolve chains, resolved chains, and cleanup candidates
  - explains whether preview and live advancement are allowed
  - provides recommended operator actions
- Updated `conscious_agent/stable_supervised_loop.py`
  - version is now `6.9`
  - preflight now includes `closure_guardrails`
  - live runs are blocked when unresolved follow-up chains exist
  - preview-only runs still work normally
  - explicit bypass is available with `--stable-loop-bypass-closure-guardrails`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.9`
  - `/stable-loop` now shows a Live Run Closure Guardrails card
  - stable-loop run form includes an explicit bypass checkbox
- Updated `conscious_agent/api_server.py`
  - API version is now `6.9`
  - added `GET /api/stable-loops/guardrails`
  - `POST /api/stable-loops/run` accepts `bypass_closure_guardrails`
- Updated `conscious_agent/main.py`
  - added `--stable-loop-guardrails`
  - added `--stable-loop-bypass-closure-guardrails`
- Updated smoke checks, settings version, project metadata, stable-loop docs, work-cycle docs, and command whitelist.
- Cleaned a duplicated line in `stable_loop_followup_completion.py`.

## New CLI commands

Show closure guardrails:

```powershell
python conscious_agent/main.py --stable-loop-guardrails
```

Show full guardrail details:

```powershell
python conscious_agent/main.py --stable-loop-guardrails --stable-loop-full
```

Run a normal preview:

```powershell
python conscious_agent/main.py --stable-loop --no-ai-stable-loop --stable-loop-full
```

Attempt a live run only when guardrails are clear:

```powershell
python conscious_agent/main.py --stable-loop --stable-loop-live --no-ai-stable-loop --stable-loop-full
```

Explicitly bypass unresolved follow-up guardrails for a live run:

```powershell
python conscious_agent/main.py --stable-loop --stable-loop-live --stable-loop-bypass-closure-guardrails --no-ai-stable-loop --stable-loop-full
```

Use the bypass only when you have intentionally reviewed the unresolved follow-up chain. It exists for operator override, not for pretending warnings are decorative.

## New dashboard/API paths

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
```

API:

```text
GET  /api/stable-loops/guardrails
GET  /api/stable-loops/preflight
POST /api/stable-loops/run
```

Example live run body with explicit bypass:

```json
{
  "project_id": "eidolon",
  "max_steps": 1,
  "live": true,
  "use_ai": false,
  "bypass_closure_guardrails": true
}
```

## Recommended troubleshooting after v6.9

Run these from the project root:

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stable-loop-guardrails
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --stable-loop-followup-completion-report unresolved
```

If `--stable-loop-guardrails` says live is blocked, resolve or close follow-up chains before running live:

```powershell
python conscious_agent/main.py --list-stable-loop-followup-completions unresolved
python conscious_agent/main.py --create-stable-loop-decision-followups action_required --dry-run
python conscious_agent/main.py --resolve-stable-loop-followups stableloop_ID
python conscious_agent/main.py --mark-stable-loop-followup-closed stableloop_ID
```

## Next likely step

v7.0 should be a stabilization/checkpoint release: run the dashboard, API, CLI, task lifecycle, stable loop guardrails, follow-up closure, and smoke checks as one pass before adding more autonomy. Yes, a checkpoint. Boring. That is why it might actually save us.

---

# Eidolon v6.8 - Follow-Up Completion Reports / Decision Closure Dashboard Polish

v6.8 makes stable-loop decision follow-up chains easier to report, filter, close, and archive. v6.7 could create and resolve follow-up tasks; v6.8 adds completion reporting so the dashboard and CLI can clearly distinguish missing follow-ups, open follow-up tasks, ready-to-resolve chains, resolved chains, and cleanup candidates. It also fixes the dashboard API nav bug where `/api-info` was incorrectly routed as `/api...` because the dashboard checked `path.startswith("/api")` before the exact `/api-info` route. Tiny prefix goblin defeated.

## What changed in v6.8

- Added `conscious_agent/stable_loop_followup_completion.py`
  - reports stable-loop follow-up completion state
  - filters `all`, `action_required`, `missing_followups`, `open`, `unresolved`, `ready_to_resolve`, `resolved`, `cleanup_default`, and `archived`
  - supports closure confirmation after a follow-up chain is resolved
  - supports cleanup/archive previews for resolved completion records
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.8`
  - fixed `/api-info` routing so it no longer gets swallowed by the `/api` dispatcher
  - `/stable-loop?followup=...` now filters by follow-up completion state
  - stable-loop rows show follow-up closure status, linked task counts, open task counts, and next recommended action
  - added Follow-up Closure cards, filters, cleanup controls, and Mark Closed controls
- Updated `conscious_agent/api_server.py`
  - API version is now `6.8`
  - added follow-up completion report and cleanup endpoints
- Updated `conscious_agent/main.py`
  - added CLI commands for follow-up completion reporting, listing, closing, and cleanup
- Updated smoke checks, settings version, project metadata, and stable-loop/work-cycle docs.

## New dashboard filters

Open the dashboard:

```powershell
python conscious_agent/main.py --dashboard
```

Then use:

```text
http://127.0.0.1:8765/stable-loop?followup=unresolved
http://127.0.0.1:8765/stable-loop?followup=ready_to_resolve
http://127.0.0.1:8765/stable-loop?followup=resolved
http://127.0.0.1:8765/stable-loop?followup=cleanup_default
http://127.0.0.1:8765/api-info
```

The `/api-info` tab should now render the API documentation page instead of returning a 404 JSON response from the API dispatcher.

## New CLI commands

Show a completion report:

```powershell
python conscious_agent/main.py --stable-loop-followup-completion-report all
```

List unresolved completion rows:

```powershell
python conscious_agent/main.py --list-stable-loop-followup-completions unresolved
```

List chains ready to resolve:

```powershell
python conscious_agent/main.py --list-stable-loop-followup-completions ready_to_resolve
```

Mark a resolved follow-up chain closed:

```powershell
python conscious_agent/main.py --mark-stable-loop-followup-closed stableloop_ID --stable-loop-followup-note "Follow-up tasks reviewed and closure confirmed."
```

Mark closed and archive the source stable-loop record:

```powershell
python conscious_agent/main.py --mark-stable-loop-followup-closed stableloop_ID --archive-resolved-stable-loop
```

Preview cleanup of resolved completion records:

```powershell
python conscious_agent/main.py --cleanup-stable-loop-followup-completions --stable-loop-followup-completion-filter cleanup_default --stable-loop-followup-completion-full
```

Actually archive cleanup candidates:

```powershell
python conscious_agent/main.py --cleanup-stable-loop-followup-completions --cleanup-stable-loop-confirm --stable-loop-followup-completion-filter cleanup_default
```

## New API endpoints

```text
GET  /api/stable-loops/followups/completion?completion=unresolved
GET  /api/stable-loops/followups/completion/report?completion=ready_to_resolve
POST /api/stable-loops/followups/completion/cleanup
POST /api/stable-loops/{id}/mark-followups-closed
```

Example cleanup body:

```json
{
  "completion": "cleanup_default",
  "limit": 25,
  "dry_run": true
}
```

## Main checks after v6.8

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --stable-loop-followup-completion-report all
python conscious_agent/main.py --list-stable-loop-followup-completions unresolved
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
```

If running on Windows with the project environment:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

## Next likely step

Next feature work should be **v6.9 - Stable Loop Closure-Aware Work Cycle Guardrails**. v6.8 reports and closes follow-up chains. v6.9 should make stable-loop preflight and work-cycle decisions aware of unresolved follow-up chains so the agent avoids starting new work while previous live-run follow-up decisions still need closure. Because nothing says "bad automation" like sprinting forward while old mistakes are still smoking politely in the corner.

---

# Eidolon v6.7 - Decision Follow-Up Task Lifecycle Integration

v6.7 connects the stable-loop decision follow-up tasks from v6.6 back into the task lifecycle view. Follow-up tasks now visibly show which stable-loop record, final decision, and follow-up kind created them. Once those follow-up tasks are done or cancelled, the source stable-loop decision can be marked resolved and optionally archived. Tiny family reunification for JSON goblins.

## What changed in v6.7

- Added `conscious_agent/stable_loop_followup_lifecycle.py`
  - detects stable-loop decision follow-up tasks
  - summarizes follow-up lifecycle state
  - shows task → stable-loop → final decision links
  - resolves a stable-loop decision follow-up chain after linked follow-up tasks are finished
  - can optionally archive the source stable-loop record after resolution
- Updated `conscious_agent/task_lifecycle.py`
  - lifecycle rows now include stable-loop follow-up fields:
    - `is_stable_loop_followup`
    - `stable_loop_id`
    - `stable_loop_decision`
    - `stable_loop_followup_kind`
    - `stable_loop_followup_resolution_status`
  - added `/tasks-work?stage=stable_loop_followup` support
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.7`
  - `/tasks-work` shows stable-loop follow-up origin hints on task rows
  - task detail pages show a stable-loop decision follow-up card when applicable
  - stable-loop pages show follow-up lifecycle summaries and resolve/archive controls
- Updated `conscious_agent/api_server.py`
  - API version is now `6.7`
  - added stable-loop follow-up lifecycle endpoints
- Updated `conscious_agent/main.py`
  - added CLI commands for follow-up lifecycle summaries, task inspection, and resolution
- Updated `conscious_agent/command_runner.py`
  - added the new safe read/resolve CLI flags to the command allow-list
- Updated `tools/smoke_check.py`
  - added a stable-loop follow-up lifecycle shape/text/version check
- Updated docs and metadata:
  - `README_NEXT_STEPS.md`
  - `data/projects.json`
  - `data/project_index.json`
  - `data/stable_loops/README.md`
  - `data/work_cycles/README.md`
  - `data/work_queue/README.md`
  - `data/settings.json` / `settings_manager.py` use `settings_version: 6.7`

## New CLI commands

Show the follow-up lifecycle summary:

```powershell
python conscious_agent/main.py --stable-loop-followup-lifecycle-summary all
```

Show one follow-up task's stable-loop source decision:

```powershell
python conscious_agent/main.py --show-task-stable-loop-followup task_ID --stable-loop-followup-full
```

Resolve a stable-loop decision follow-up chain after linked follow-up tasks are complete:

```powershell
python conscious_agent/main.py --resolve-stable-loop-followups stableloop_ID --stable-loop-followup-note "Follow-up tasks completed."
```

Resolve using one completed follow-up task:

```powershell
python conscious_agent/main.py --resolve-task-stable-loop-followup task_ID --stable-loop-followup-note "Follow-up task completed."
```

Resolve and archive the source stable-loop record:

```powershell
python conscious_agent/main.py --resolve-task-stable-loop-followup task_ID --archive-resolved-stable-loop --stable-loop-followup-note "Closed and archived after follow-up completion."
```

Force resolution even when linked follow-up tasks are still open:

```powershell
python conscious_agent/main.py --resolve-stable-loop-followups stableloop_ID --force-stable-loop-followup-resolution
```

Use force carefully. It exists for operator cleanup, not for pretending unfinished tasks are magically done. Computers already lie enough.

## New dashboard usage

Open:

```text
http://127.0.0.1:8765/tasks-work?stage=stable_loop_followup
```

Useful dashboard areas:

- `/tasks-work` now shows stable-loop follow-up metadata in task rows.
- Task details show the source stable-loop decision and resolution controls.
- `/stable-loop` shows follow-up lifecycle summaries.
- Stable-loop detail pages include Resolve Follow-ups and Resolve + Archive controls.

## New API endpoints

```text
GET  /api/tasks/stable-loop-followups
GET  /api/tasks/{id}/stable-loop-followup
POST /api/tasks/{id}/stable-loop-followup/resolve
GET  /api/stable-loops/{id}/followup-lifecycle
POST /api/stable-loops/{id}/resolve-followups
```

Example resolve body:

```json
{
  "archive": true,
  "force": false,
  "note": "Follow-up tasks completed and decision record archived."
}
```

## Main checks after v6.7

```powershell
python -m py_compile conscious_agent/*.py tools/smoke_check.py
python conscious_agent/main.py --status
python conscious_agent/main.py --settings-health
python conscious_agent/main.py --task-work summary
python conscious_agent/main.py --stable-loop-followup-lifecycle-summary all
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --index-project
```

On Windows after unpacking a fresh zip:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

## Current architecture note

Canonical task/work state still lives in:

```text
data/tasks.json
conscious_agent/task_queue.py
```

Stable-loop decision follow-up tasks are canonical tasks with metadata like:

```json
{
  "source": "stable_loop_decision",
  "stable_loop_id": "stableloop_...",
  "final_decision": "fix_forward",
  "followup_kind": "fix_forward_plan"
}
```

The old work-queue compatibility layer still exists so earlier dashboard/API/CLI routes do not snap in half like cheap plastic.

## Next likely step

Next feature work should be **v6.8 - Follow-Up Completion Reports / Decision Closure Dashboard Polish**. v6.7 can resolve follow-up chains. v6.8 should add cleaner reporting for resolved vs unresolved decision follow-ups, plus dashboard filters for "ready to resolve" and "resolved/archived" records.

---

# Eidolon v6.5 - Stable Loop Decision-Aware Cleanup / Reporting

v6.5 turns stable-loop final decisions into searchable/reportable history. v6.4 let the operator save `keep`, `fix_forward`, `rollback`, and `needs_review` decisions. v6.5 makes those decisions show up in CLI reports, dashboard filters, API summaries, and archive cleanup. Because JSON that nobody can query is just a diary with worse handwriting.

## What changed in v6.5

- Added `conscious_agent/stable_loop_decision_report.py`
  - builds decision summaries from saved stable-loop records
  - supports filters for `undecided`, `keep`, `fix_forward`, `rollback`, `needs_review`, `action_required`, `decided`, `complete`, `incomplete`, `cleanup_default`, and `archived`
  - recommends a next operator action for each record
  - archives cleanup candidates without deleting JSON history
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.5`
  - `/stable-loop?decision=...` now filters by final decision
  - stable-loop rows show final decision, checklist progress, and recommended next action
  - added decision summary cards, decision filter chips, and decision cleanup controls
- Updated `conscious_agent/api_server.py`
  - API version is now `6.5`
  - added decision report endpoints
  - `/api/stable-loops?decision=...` can now list decision-filtered rows
  - `/api/status` includes stable-loop decision counts
- Updated `conscious_agent/main.py`
  - added decision report/list/cleanup CLI commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new decision-reporting flags
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.5`
  - `tools/smoke_check.py` imports and checks `stable_loop_decision_report.py`

## Stable-loop decision CLI examples

Show all final-decision counts:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-decision-report all
```

List records that need action:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loop-decisions action_required
```

List rollback decisions:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loop-decisions rollback
```

Preview decision-aware cleanup:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-decisions --stable-loop-decision-filter cleanup_default --stable-loop-decision-full
```

Archive decision cleanup candidates:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-decisions --cleanup-stable-loop-confirm --stable-loop-decision-filter cleanup_default
```

## Stable-loop decision dashboard/API

Dashboard filters:

```text
http://127.0.0.1:8765/stable-loop?decision=action_required
http://127.0.0.1:8765/stable-loop?decision=keep
http://127.0.0.1:8765/stable-loop?decision=rollback
http://127.0.0.1:8765/stable-loop?decision=cleanup_default
```

API:

```text
GET  /api/stable-loops?decision=action_required
GET  /api/stable-loops/decisions?decision=all
GET  /api/stable-loops/decisions/report?decision=cleanup_default
POST /api/stable-loops/decisions/cleanup
```

Example cleanup body:

```json
{
  "decision": "cleanup_default",
  "limit": 25,
  "dry_run": true,
  "include_live": true
}
```

## Main checks after v6.5

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --no-ai-stable-loop
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-decision-report all
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-decisions --stable-loop-decision-filter cleanup_default
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.6 - Decision-Aware Stable Loop Follow-Up Tasks**. v6.5 can tell you which stable-loop decisions need action. v6.6 should help convert `fix_forward`, `rollback`, and `needs_review` decisions into task-backed follow-ups so the operator does not have to manually translate decisions into work.

---

# Eidolon v6.4 - Stable Loop Post-Run Checklist / Operator Notes

v6.4 turns v6.3 audit notes into an operator workflow. Stable-loop records can now carry a post-run checklist, manual operator notes, and a final decision: keep the result, fix forward, rollback, or continue reviewing. Because an audit trail without a decision is just paperwork doing cosplay.

## What changed in v6.4

- Added `conscious_agent/stable_loop_operator_notes.py`
  - builds default post-run checklist items from stable-loop audit recommendations
  - stores checklist state directly on each stable-loop JSON record under `operator_notes`
  - supports operator notes and final decisions
  - supports checklist item statuses: `pending`, `done`, and `skipped`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.4`
  - `/stable-loop` and stable-loop detail pages show post-run checklist / operator notes
  - added checklist buttons for **Done** and **Skip**
  - added operator note form
  - added final decision form for `keep`, `fix_forward`, `rollback`, and `needs_review`
- Updated `conscious_agent/api_server.py`
  - API version is now `6.4`
  - added operator-note and checklist endpoints
- Updated `conscious_agent/main.py`
  - added stable-loop operator note/checklist/final-decision CLI commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new stable-loop operator flags through the safe command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.4`
  - `tools/smoke_check.py` imports and checks `stable_loop_operator_notes.py`

## Stable-loop operator CLI examples

Show post-run checklist and operator notes:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-operator-notes latest
```

Add an operator note:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --add-stable-loop-operator-note stableloop_ID --stable-loop-operator-note "Reviewed dashboard and task summary."
```

Mark a checklist item complete:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --complete-stable-loop-check stableloop_ID status --stable-loop-operator-note "Status check passed."
```

Skip a checklist item with a note:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --skip-stable-loop-check stableloop_ID rollback_dry_run_patch_ID --stable-loop-operator-note "No patch was applied, rollback preview not needed."
```

Set the final decision:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --set-stable-loop-final-decision stableloop_ID --stable-loop-final-decision keep --stable-loop-operator-note "Post-run checks passed. Keeping result."
```

Valid final decisions:

```text
undecided
keep
fix_forward
rollback
needs_review
```

## Stable-loop operator dashboard/API

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
```

API:

```text
GET  /api/stable-loops/{id}/operator-notes
POST /api/stable-loops/{id}/operator-notes
POST /api/stable-loops/{id}/checklist/{check_id}
POST /api/stable-loops/{id}/decision
```

Example checklist update body:

```json
{
  "status": "done",
  "note": "Status check passed."
}
```

Example final decision body:

```json
{
  "decision": "needs_review",
  "note": "Need to inspect patch output before keeping."
}
```

## Main checks after v6.4

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --no-ai-stable-loop
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-audit latest
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-operator-notes latest
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.5 - Stable Loop Decision-Aware Cleanup / Reporting**. v6.4 lets the operator save decisions; v6.5 should use those decisions in filters, reports, and cleanup so kept/fix-forward/rollback records are easier to find later.

---

# Eidolon v6.3 - Stable Loop Live Run Safeguards / Rollback Notes

v6.3 makes live stable-loop records easier to audit after they run. v6.2 cleaned up stable-loop review history; v6.3 adds an audit layer that summarizes what changed, which approvals were involved, which patches may need rollback notes, and which verification commands should be run afterward. Tiny paperwork, yes. Also the difference between debugging and folklore.

## What changed in v6.3

- Added `conscious_agent/stable_loop_audit.py`
  - builds audit summaries for saved stable-loop records
  - records changed task ids, created task ids, executed task ids, approval ids, patch ids, and command notes
  - derives rollback dry-run commands for applied patches when backup metadata exists
  - produces recommended post-run check commands
- Updated `conscious_agent/stable_supervised_loop.py`
  - stable-loop record version is now `6.3`
  - new stable-loop records include an `audit` block
  - full stable-loop output now includes audit summaries
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.3`
  - `/stable-loop` rows show audit summaries and warning counts
  - stable-loop detail pages show audit / rollback notes
  - added a **Refresh audit** action
- Updated `conscious_agent/api_server.py`
  - API version is now `6.3`
  - added `GET /api/stable-loops/{id}/audit`
  - added `GET /api/stable-loops/{id}/audit?refresh=true`
  - added `POST /api/stable-loops/{id}/refresh-audit`
- Updated `conscious_agent/main.py`
  - added stable-loop audit CLI commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new audit flags through the safe command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.3`
  - `tools/smoke_check.py` imports and checks `stable_loop_audit.py`

## Stable-loop audit CLI examples

Show the latest stable-loop audit:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-audit latest
```

Show full raw audit JSON:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-audit latest --stable-loop-audit-full
```

Refresh and save audit notes for one record:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --refresh-stable-loop-audit stableloop_ID --stable-loop-audit-full
```

## Stable-loop audit dashboard/API

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
```

API:

```text
GET  /api/stable-loops/{id}/audit
GET  /api/stable-loops/{id}/audit?refresh=true
POST /api/stable-loops/{id}/refresh-audit
```

## Recommended post-live-run checks

After a live stable loop, inspect the audit and then run the listed check commands. The audit usually recommends commands like:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-applied-patches
```

If a live run applied a patch and the patch still has backup metadata, the audit will include rollback commands like:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --rollback-patch patch_ID --dry-run
.\.venv\Scripts\python.exe .\conscious_agent\main.py --rollback-patch patch_ID
```

Run the dry-run rollback first. Always. The computer is not your friend, it is a fast idiot with electricity.

## Main checks after v6.3

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --no-ai-stable-loop
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-audit latest
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.4 - Stable Loop Post-Run Checklist / Operator Notes**. v6.3 creates audit notes; v6.4 should let the operator mark post-run checks complete, save manual review notes, and attach final keep/fix/rollback decisions to each live run.

---

# Eidolon v6.2 - Stable Loop Review Filters / History Cleanup

v6.2 makes stable-loop history easier to manage. v6.1 added review actions; v6.2 adds filters for review states and safe archive-based cleanup so old preview/live records stop turning `/stable-loop` into a JSON fossil museum. Records are archived, not deleted, because future-you may still need evidence when the goblin claims innocence.

## What changed in v6.2

- Updated `conscious_agent/stable_loop_review.py`
  - added stable-loop review filters: `all`, `open`, `unreviewed`, `reviewed`, `approved_ready`, `rejected`, `superseded`, `failed`, `cleanup_default`, and `archived`
  - added archive/restore support through review metadata
  - added dry-run history cleanup for superseded/rejected/live cleanup candidates
  - expanded review summaries with archived counts and filter counts
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.2`
  - `/stable-loop?review=...` filters stable-loop history
  - added filter chips for review/history views
  - added Archive / Restore actions per stable-loop row
  - added a history cleanup panel with dry-run preview and explicit archive action
- Updated `conscious_agent/api_server.py`
  - API version is now `6.2`
  - `GET /api/stable-loops` now supports `?review=...&include_archived=true`
  - added `GET /api/stable-loops/history`
  - added archive/restore and cleanup endpoints
- Updated `conscious_agent/main.py`
  - added stable-loop history listing, archive/restore, and cleanup CLI commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new stable-loop history flags
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.2`
  - stable-loop/work-cycle docs now describe the v6.2 review history layer

## Stable-loop history filters

```text
all              Visible, non-archived stable-loop records
open             Unreviewed/reviewed/approved preview records still relevant to review flow
unreviewed       Records waiting for review
reviewed         Records marked reviewed
approved_ready   Approved preview records ready for explicit live run
rejected         Rejected records
superseded       Preview records already used to launch a live loop
failed           Records with failed preflight/preview/live status
cleanup_default  Superseded, rejected, and live records that are usually safe to archive
archived         Records hidden from default history views
```

## Stable-loop history CLI examples

List filtered review/history rows:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loop-reviews open
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loop-reviews archived --include-archived-stable-loops
```

Archive or restore one record:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --archive-stable-loop stableloop_ID --stable-loop-review-note "Old preview archived."
.\.venv\Scripts\python.exe .\conscious_agent\main.py --restore-stable-loop stableloop_ID --stable-loop-review-note "Restored for inspection."
```

Preview cleanup candidates:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-history --stable-loop-review-filter cleanup_default --stable-loop-review-full
```

Archive cleanup candidates after preview:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-history --cleanup-stable-loop-confirm --stable-loop-review-filter cleanup_default
```

## Stable-loop dashboard/API

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
http://127.0.0.1:8765/stable-loop?review=unreviewed
http://127.0.0.1:8765/stable-loop?review=cleanup_default
http://127.0.0.1:8765/stable-loop?review=archived
```

API:

```text
GET  /api/stable-loops?review=open
GET  /api/stable-loops?review=archived&include_archived=true
GET  /api/stable-loops/reviews?review=cleanup_default
GET  /api/stable-loops/history?review=rejected
POST /api/stable-loops/{id}/archive
POST /api/stable-loops/{id}/restore
POST /api/stable-loops/history/cleanup
```

Example cleanup body:

```json
{
  "review": "cleanup_default",
  "limit": 25,
  "dry_run": true,
  "include_live": true
}
```

## Main checks after v6.2

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-review-summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loop-reviews open
.\.venv\Scripts\python.exe .\conscious_agent\main.py --cleanup-stable-loop-history --stable-loop-review-filter cleanup_default
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.3 - Stable Loop Live Run Safeguards / Rollback Notes**. v6.2 cleans up review history; v6.3 should make live stable-loop records easier to audit by summarizing what changed, what approvals were used, and what rollback/check commands apply afterward.

---

# Eidolon v6.1 - Stable Loop Dashboard Review Actions

v6.1 makes stable-loop records reviewable from the dashboard/API/CLI before using a preview to launch an explicit live stable loop. v6.0 gave Eidolon a stable operator loop; v6.1 adds the review gate so preview records do not just pile up like tiny JSON fossils.

## What changed in v6.1

- Added `conscious_agent/stable_loop_review.py`
  - stores operator review metadata directly inside saved stable-loop records
  - supports review states: `unreviewed`, `reviewed`, `approved_for_live`, `rejected`, and `superseded`
  - summarizes the stable-loop review queue
  - can run a live stable loop only from an approved preview record
- Updated `conscious_agent/stable_supervised_loop.py`
  - stable-loop record version is now `6.1`
  - new records include a default `review` block
  - stable-loop ids now include microseconds
- Updated `conscious_agent/work_cycle.py`
  - work-cycle record version is now `6.1`
  - work-cycle ids now include microseconds so preview/live records cannot overwrite each other when created in the same second
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.1`
  - `/stable-loop` now shows review summary cards
  - saved-loop table now includes review status and review actions
  - stable-loop detail pages show review metadata and controls
  - dashboard actions can mark reviewed, approve for live, reject, or run approved live
- Updated `conscious_agent/api_server.py`
  - API version is now `6.1`
  - added stable-loop review endpoints
- Updated `conscious_agent/main.py`
  - added stable-loop review CLI commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new review flags through the approved command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.1`
  - `tools/smoke_check.py` imports and exercises the stable-loop review module

## Stable loop review states

```text
unreviewed        A preview/live record exists but has not been reviewed.
reviewed          Operator inspected it and left it as reviewed.
approved_for_live A preview record is approved for one explicit live run.
rejected          Operator rejected the record or wants changes before live use.
superseded        An approved preview was used to create a live stable loop.
```

## Stable loop review CLI examples

Review queue summary:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-review-summary
```

Show one review record:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop-review latest --stable-loop-review-full
```

Mark a loop reviewed:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --mark-stable-loop-reviewed stableloop_ID --stable-loop-review-note "Preview inspected."
```

Approve a preview for live execution:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --approve-stable-loop-live stableloop_ID --stable-loop-review-note "Approved after preview review."
```

Run a live stable loop from an approved preview:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --run-approved-stable-loop-live stableloop_ID --stable-loop-review-full
```

Reject a loop:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --reject-stable-loop stableloop_ID --stable-loop-review-note "Needs adjustment before live run."
```

## Stable loop review dashboard/API

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
```

API:

```text
GET  /api/stable-loops/reviews
GET  /api/stable-loops/{id}/review
POST /api/stable-loops/{id}/review
POST /api/stable-loops/{id}/approve-live
POST /api/stable-loops/{id}/reject
POST /api/stable-loops/{id}/run-approved-live
```

Example API review body:

```json
{
  "status": "reviewed",
  "note": "Preview inspected from API."
}
```

## Main checks after v6.1

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --stable-loop-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop --no-ai-stable-loop --stable-loop-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-review-summary
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.2 - Stable Loop Review Filters / History Cleanup**. v6.1 adds review actions; v6.2 should add dashboard filters for unreviewed/approved/rejected loops and optional cleanup/archive controls for older stable-loop records.

---

# Eidolon v6.0 - Stable Supervised Agent Loop

v6.0 stabilizes the supervised agent loop around a predictable operator path:

```text
preflight -> lifecycle decision -> dry-run preview -> optional live cycle -> saved review record
```

The existing lifecycle-aware `work_cycle.py` still performs the actual task advancement. The new stable loop wraps it with preflight checks and review records so the system behaves like a supervised local agent instead of a pile of buttons trying to become a workflow. Tiny standards, huge relief.

## What changed in v6.0

- Added `conscious_agent/stable_supervised_loop.py`
  - builds a read-only stable-loop preflight snapshot
  - records the selected lifecycle decision from `task_cycle_policy.py`
  - always runs/saves a dry-run work-cycle preview first
  - optionally runs a live work cycle only when explicitly requested
  - saves review records under `data/stable_loops/`
- Updated `conscious_agent/main.py`
  - added stable-loop CLI commands:
    - `--stable-loop-preflight`
    - `--stable-loop`
    - `--stable-loop-live`
    - `--list-stable-loops`
    - `--show-stable-loop`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `6.0`
  - added `/stable-loop`
  - added a preflight card, stable-loop run form, latest stable loop card, and saved-loop table
- Updated `conscious_agent/api_server.py`
  - API version is now `6.0`
  - added:
    - `GET /api/stable-loops`
    - `GET /api/stable-loops/preflight`
    - `GET /api/stable-loops/{id}`
    - `POST /api/stable-loops/run`
- Updated safety/docs metadata
  - `command_runner.py` allows stable-loop flags through the approved command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 6.0`
  - `tools/smoke_check.py` imports and exercises the stable loop module

## Stable loop CLI examples

Preview health and the next lifecycle decision:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --stable-loop-full
```

Run the default stable loop preview:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop --no-ai-stable-loop --stable-loop-full
```

Run a live stable loop after the preview, still capped and approval-gated:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop --stable-loop-live --stable-loop-steps 1 --no-ai-stable-loop --stable-loop-full
```

Review saved loops:

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-stable-loops
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-stable-loop latest --stable-loop-full
```

## Stable loop dashboard/API examples

Dashboard:

```text
http://127.0.0.1:8765/stable-loop
```

API:

```text
GET  /api/stable-loops/preflight
POST /api/stable-loops/run
GET  /api/stable-loops/latest
```

Preview-only request body:

```json
{
  "project_id": "eidolon",
  "max_steps": 1,
  "live": false,
  "use_ai": false
}
```

Live request body:

```json
{
  "project_id": "eidolon",
  "max_steps": 1,
  "live": true,
  "use_ai": false,
  "approve_work_execution": false,
  "auto_retry_recovery": false
}
```

## Main checks after v6.0

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop-preflight --stable-loop-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --stable-loop --no-ai-stable-loop --stable-loop-full
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.1 - Stable Loop Dashboard Review Actions**. v6.0 creates stable loop records; v6.1 should make reviewing preview/live cycle results easier from the dashboard before allowing more live advancement.

---

# Eidolon v5.9 - Lifecycle-Aware Work Cycle

v5.9 makes the supervised work cycle choose actions from task lifecycle state instead of blindly grabbing the next ready task like a confused office printer. The cycle can now decide whether the next safe move is to request approval, review recovery, create patch follow-ups, or execute a ready low-risk task.

## What changed in v5.9

- Added `conscious_agent/task_cycle_policy.py`
  - derives cycle candidates from `task_lifecycle.py`
  - ranks lifecycle stages for supervised cycle work
  - maps lifecycle stages to cycle actions such as `request_approval`, `review_recovery`, `create_patch_followups`, and `execute_task`
- Updated `conscious_agent/work_cycle.py`
  - saved cycle records now use version `5.9`
  - cycle events now include `lifecycle_decision` records
  - records now track `approval_ids`, `recovered_task_ids`, and `lifecycle_decisions`
  - empty queues still seed safe starter tasks, but non-empty queues now use lifecycle-aware selection
- Updated `conscious_agent/main.py`
  - added `--no-work-cycle-approval-requests`
  - added `--work-cycle-auto-retry-recovery`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.9`
  - the Work Cycle form includes lifecycle-aware approval and recovery toggles
- Updated `conscious_agent/api_server.py`
  - API version is now `5.9`
  - `POST /api/work-cycles/run` accepts `auto_request_approvals` and `auto_retry_recovery`
- Updated safety/docs metadata
  - `command_runner.py` allows the new work-cycle flags through the safe command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 5.9`
  - `tools/smoke_check.py` imports/checks the cycle policy module

## Lifecycle-aware cycle policy

The cycle now prioritizes decisions roughly like this:

```text
approval_required      -> request approval
recovery_needed        -> show recovery plan / dry-run retry preview
approval_rejected      -> show recovery plan
approval_failed        -> show recovery plan
patch_proposed         -> create patch review/apply/test follow-up tasks
approved_ready         -> execute only if approval-required execution is allowed
ready / active         -> dry-run or execute through task_work_executor.py
approval_pending       -> wait for approval resolution
blocked / unknown      -> stop for manual review
```

The default cycle still starts in dry-run mode. This remains a supervised system, not a button labeled “trust me bro.”

## Work cycle CLI examples

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --work-cycle --dry-run --no-ai-work-cycle --work-cycle-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --work-cycle --work-cycle-steps 3 --no-ai-work-cycle
.\.venv\Scripts\python.exe .\conscious_agent\main.py --work-cycle --no-work-cycle-approval-requests --dry-run
.\.venv\Scripts\python.exe .\conscious_agent\main.py --work-cycle --work-cycle-auto-retry-recovery --dry-run --work-cycle-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-work-cycle latest --work-cycle-full
```

Use `--work-cycle-auto-retry-recovery` carefully. By default, v5.9 only reports recovery plans and dry-run retry previews. With that flag, the cycle may mark a recovery-needed task ready for retry, which is safe-ish but still a state change, and state changes are where bugs build vacation homes.

## Work cycle dashboard/API examples

Dashboard:

```text
http://127.0.0.1:8765/work-cycle
```

API:

```text
POST /api/work-cycles/run
```

Request body example:

```json
{
  "dry_run": true,
  "project_id": "eidolon",
  "max_steps": 1,
  "use_ai": false,
  "auto_request_approvals": true,
  "auto_retry_recovery": false
}
```

## Main checks after v5.9

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-recovery-summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --work-cycle --dry-run --no-ai-work-cycle --work-cycle-full
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v6.0 - Stable Supervised Agent Loop**. v5.9 finally connects lifecycle state to the supervised cycle; v6.0 should stabilize the full loop around observe -> decide -> act safely -> record -> dashboard review.

---

# Eidolon v5.8 - Task Failure Recovery / Retry Logic

v5.8 teaches Eidolon what to do when a task fails or blocks instead of letting it sulk in `blocked` forever like a printer with a tiny grudge. The canonical task system now has a recovery layer that classifies failure causes, suggests safe recovery actions, and supports dry-run retry / mark-ready-for-retry controls.

## What changed in v5.8

- Added `conscious_agent/task_recovery.py`
  - classifies failed/blocked task causes such as missing target files, missing commands, blocked commands, command failure, test failure, patch failure, approval rejection, and manual-required cases
  - builds recovery plans with recommended safe next actions
  - supports `mark_task_ready_for_retry(...)` and `retry_task_work(...)`
- Updated `conscious_agent/task_lifecycle.py`
  - added `recovery_needed` lifecycle stage
  - `failed`, `recovery`, and `needs_recovery` stage aliases now map to recovery-needed tasks
  - recovery-needed tasks are included in `needs_attention`
- Updated `conscious_agent/dashboard.py`
  - dashboard version is now `5.8`
  - `/tasks-work?stage=recovery_needed` filters to tasks that need recovery
  - task rows and task detail pages show recovery-plan controls
  - added safe buttons for **Recovery Plan**, **Dry-run Retry**, and **Mark Ready for Retry**
- Updated `conscious_agent/api_server.py`
  - API version is now `5.8`
  - added task recovery API endpoints
  - `/api/status` now includes task recovery summary data
- Updated CLI wiring in `conscious_agent/main.py`
  - added recovery summary/list/show/retry commands
- Updated safety/docs metadata
  - `command_runner.py` allows the new recovery CLI flags through the command whitelist
  - `data/settings.json` and `settings_manager.py` use `settings_version: 5.8`
  - new saved work-cycle records use version `5.8`

## Recovery CLI examples

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-recovery-summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --list-task-recoveries
.\.venv\Scripts\python.exe .\conscious_agent\main.py --show-task-recovery latest-blocked --task-recovery-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --retry-task-work latest-blocked --dry-run --task-recovery-full
.\.venv\Scripts\python.exe .\conscious_agent\main.py --mark-task-ready-for-retry latest-blocked --task-recovery-note "Reviewed failure and ready to retry."
```

Use `--dry-run` before a real retry. Yes, every time. Computers punish optimism.

## Recovery dashboard examples

```text
http://127.0.0.1:8765/tasks-work?stage=recovery_needed
http://127.0.0.1:8765/tasks-work?stage=needs_attention
```

Task detail pages now include a recovery plan card when a task is blocked, failed, or otherwise recoverable.

## Recovery API examples

```text
GET  /api/tasks/recovery
GET  /api/tasks/recovery/summary
GET  /api/tasks/{id}/recovery
POST /api/tasks/{id}/ready-for-retry
POST /api/tasks/{id}/retry
```

Retry request body example:

```json
{
  "dry_run": true,
  "use_ai": false,
  "allow_approval_required": false
}
```

## Main checks after v5.8

```powershell
.\.venv\Scripts\python.exe .\conscious_agent\main.py --status
.\.venv\Scripts\python.exe .\conscious_agent\main.py --settings-health
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-work summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --task-recovery-summary
.\.venv\Scripts\python.exe .\conscious_agent\main.py --execute-task-work --dry-run --no-ai-task-work-executor --task-work-executor-full
.\.venv\Scripts\python.exe .\tools\smoke_check.py
```

Next feature work should be **v5.9 - Work Cycle Uses Lifecycle Decisions**. The recovery layer exists now; the supervised work cycle should start using lifecycle/recovery summaries when choosing the next safe step instead of only asking for the next ready task.

---

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
.\.venv\Scripts\python.exe .\tools\smoke_check.py
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
