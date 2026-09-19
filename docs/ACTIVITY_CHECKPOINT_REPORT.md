# v2732.2 Activity supervision qualification

Completed 2026-09-19. Feature checkpoint, not full release certification or
installation. Legacy release authority remains v2730.9.3; reviewer contracts
remain v2731.8/v2732.1; Activity uses activity.v1.

## Research closure

See research/G_EVID1_CLOSURE.md. G-EVID1 failed its preregistered zero-unsafe-use
gate (I27 x3, I51 x3). G10 conformed to its frozen inputs/rules. False-clean
semantic judgments are the containment problem, not demonstrated gate bypass.
The I51 numeric-entailment concern remains separate; no gold was changed.
Completed review and external-audit hashes were rechecked unchanged.

## Implementation

One generic runtime snapshot contract supplies stages, bounded event history,
real-unit/indeterminate progress, elapsed time, metrics, identities, warnings,
terminal results and governance. Reads do not start work or refresh/mutate jobs.
Legacy jobs are projected without invented events. Authoritative terminal jobs
can reconcile interrupted telemetry; stale liveness becomes unconfirmed/blocked.

The detached reviewer is the first producer. Scoped owner-thread wrappers
observe existing transitions and restore frozen functions. Prompt/reply content
is not recorded. Instrumentation and final projection failures do not replace a
successful review or mask/retry a provider exception. Confirmation is unchanged.

Web chat/home has an activity rail; /activity supplies history, stages, work
breakdown and events. Mobile collapses the rail without hiding critical warnings
or governance. Native desktop uses the same API, with a persistent rail and
native scrollable inspector. Its former Activity drawer is retained as System.
Existing custom data-tip tooltips remain in use; no privileged listener added.

## Verification results

| Suite | Result |
|---|---|
| tools/activity_tests.py | 15/15 deterministic tests, including clean extraction |
| tools/activity_ui_tests.py | 25/25 browser/mobile/native checks |
| tools/v2732_0_0_hierarchical_reviewer_tests.py | 49/49 |
| tools/v2731_11_0_private_review_runtime_tests.py | 52/52 |
| tools/v2731_4_0_conversational_review_adapter_tests.py | 46/46 |
| tools/v2731_3_5_experiment_review_tests.py | 44/44 |
| tools/v2731_3_6_review_coverage_tests.py | 38/38 |
| tools/desktop_shell_chat_tests.py | 15/15 |
| tools/release_verify.py --profile quick --json | 20/20, 283.665 seconds |
| Disposable whole-tree byte compilation | 4,896 Python files |
| Clean-copy source immutability | 0 writes, 0 deletes; exact tree unchanged |
| Source-only archive inventory | 6,057 entries; 0 forbidden paths |

The retained regression results were completed earlier in this same task; recovery
did not rerun already-verified frozen reviewer suites. New Activity and UI suites
were rerun after the final observability changes. Full release profile was not run.
The expanded final UI test and this report postdate the quick-check snapshot;
production bytes did not change after that snapshot.

Initially quick verification exposed an existing UTF-8 BOM AST-reader defect and
a sandbox Node EPERM path-resolution restriction. Source inspection now parses
bytes, preserving Python encoding behavior and all import checks. A regression
asserts that a forbidden import behind a BOM is still detected. Normal-permission
clean verification passed without changing the calculator or weakening its test.
Installed Edge and Tcl also required normal desktop permissions for UI testing.

## End-to-end qualification

Confirmed synthetic job job_632398609265b93a produced review 2ed6a72d9b3e90b1.
Its 51 deterministic stub calls crossed Observing, Part Synthesis, Document
Synthesis, Consolidating and Final Synthesis. Preparation/verification events
and terminal completion were recorded; the mutation guard passed. Browser and
native inspectors displayed that same artifact ID from the common API/history.
Additional fixtures covered live polling, incomplete, failed and unknown progress.
Separate parity tests compared exact prompts, outputs, coverage, ledgers,
authority and model-call accounting with instrumentation disabled/enabled.

This used real job creation/runner/API/UI code with synthetic provider and process
dispatch. It is not evidence of a newly executed Qwen review or OS-detached live
provider run. No semantic experiment was launched and G-EVID1 was not rerun.
Screenshots, event trace, logs and receipts stay outside product source in the
operator's qualification workspace under activity-qualification/activity-release.

## Privacy and governance

No belief, memory, experiment, policy, model, promotion or installation authority
was added. Frozen G-EVID1 and scientific reviewer files are unchanged. GETs are
read-only; hostile-origin POST rejection and original confirmation are tested.
Provider-error and telemetry-failure tests assert private error/prompt exclusion.
The package inventory excludes all data/, environments, caches, remote uploads,
agent notes, private reviews and runtime reports. Shell launchers retain 0755;
other files use 0644 and deterministic timestamps. Existing source-only checks
are path/inventory checks: their report explicitly has no general source-secret
content scan. This is not a claim of exhaustive secret detection.

## Changed modules

- New: conscious_agent/activity.py, review_activity.py, activity_ui.py,
  desktop_activity.py, static/activity.js and static/activity.css.
- Integration: dashboard.py, api_server.py, dashboard_performance.py,
  desktop_shell.py and tools/run_review_job.py.
- Verification compatibility: release_parity_campaign_binding_checkpoint_v2729_9_2.py.
- Tests: tools/activity_tests.py and tools/activity_ui_tests.py.
- Documentation: this report, ACTIVITY_SUPERVISION.md, research/G_EVID1_CLOSURE.md,
  README_RELEASE_HISTORY.md and README_NEXT_STEPS.md.

## Limitations and next step

Only experiment review publishes detailed live events so far; other operations
need adapters. History/event windows are bounded (100 snapshots, 1,000 events).
Scoped wrappers require one reviewer operation per dedicated runner; this is not
a multi-review-in-one-process API. A wholly unavailable disk cannot retain its
own failure receipt. No cancellation/retry controls or new scheduling authority
were added. No running Eidolon process was restarted or installed in this task.

After a clean implementation commit, prepare a separate design-only semantic
corroboration candidate. Operator gold/construct review and explicit execution
authorization are required before any later semantic-model calls. A passing
Activity qualification is not a passing research experiment.

## Completed checkpoints and proposed experiment

Implementation commit: c49e375. The source index/worktree was clean before
design creation; only the unrelated operator upload directory remained untracked.

The separate experiments/G-CORROB1-candidate/DESIGN.md proposal and candidate
freeze now exist: 28 fresh fictional items, 3 repeats, 2 blinded judgments,
168 planned calls. The model sees semantic fields only. Frozen individual
governance is followed by a conservative second-judge veto; correlated error,
safety containment and useful-evidence retention are separately measured.
Gold remains proposed and requires independent adjudication. The 111 passing
candidate checks verify hashes, binding, balance, prompt-label separation and
prospective policy consistency, NOT semantic truth or experimental success.
The G-EVID1 freeze verifier also passed with no changed/unfrozen artifacts.

No G-CORROB1 runner or launch command was added. No next experiment was launched.
Next operator action: inspect the Activity qualification and review the candidate
design/gold before commissioning runner/scorer implementation and authorization.
Exact final source-only ZIP hash and design commit are recorded in the external
handoff alongside the package to avoid circular archive-hash documentation.
