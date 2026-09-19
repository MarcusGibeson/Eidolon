# Operational Activity v1

Implementation checkpoint: v2732.2 supervision infrastructure. Scientific
reviewer contracts remain v2731.8 and v2732.1; their files are unchanged.
This is not a release certification or a new experiment result.

## Architecture

`activity.py` is the canonical generic, content-minimized operational record.
Each producer owns an activity ID, ordered events and atomic runtime snapshot.
It supports queued/preparing/running/blocked and terminal
complete/incomplete/failed/cancelled. Blocked is resumable; terminal is immutable.
Unit counts generate percentages only with nonzero known totals. Overall review
progress measures required parts, not a fabricated whole-job ETA. Stage counts
are separately labeled. Consolidation totals describe planned units so far.

Runtime data lives under `<runtime>/activities`, never packaged source. Reads
do not create directories, migrate records, restart work, refresh jobs or call a
provider. Stale heartbeat is projected as blocked/unconfirmed, not persisted.
Terminal authoritative job records override stale nonterminal projections.
Legacy jobs can be viewed without backfilling fabricated events.

`review_activity.py` wraps existing frozen reviewer function boundaries only
inside the detached job. It restores them in `finally`, filters by owner thread,
and never captures prompt/reply text. Original arguments, return values and
exceptions pass through. A sidecar heartbeat reports worker liveness, not model
progress. Telemetry writes occur outside the guarded private review runtime and
outside protected packages/reviews/source. Persistence failures are logged;
later successful snapshots retain the warning. A completely unavailable store
cannot preserve a receipt there; stale telemetry must not be trusted as live.
Legacy injected custom runners, whose guard scope is not known, retain job-only
projection rather than writing new telemetry inside a possibly protected root.

## Operator surfaces

- Chat dashboard: persistent current/latest activity rail, compact on mobile.
- `/activity`: history, stages, work breakdown, events, metrics, governance and
  completion/incomplete/failure reason. Legacy activity page implementation is
  retained for compatibility but no longer owns this route.
- `/api/activities` and `/api/activities/<id>`: same contract on dashboard and
  standalone API; read-only, no new POST actions or authority grants.
- Native desktop: persistent activity rail and native detail/history window,
  consuming the same API via `LocalApiClient`.

Only observed governance flags are displayed. A complete review is not an
experiment passing, nor reliable interpretation. No hidden reasoning, beliefs,
prompts, outputs, operator notes or credentials belong in activity records.
The existing remote origin/authentication model is unchanged; no Ollama port or
new privileged listener is exposed.

## Bounds and limitations

History lists the latest 100 snapshot files and latest 100 legacy jobs; direct
ID lookup reaches older records. The event window retains the last 1000 events
with an explicit omitted count. Other activity types can use the generic
producer, but only independent experiment review is instrumented in this unit.
There is no new cancellation, retry, scheduling or approval control.
Native desktop uses its existing minimum window size, not a new mobile app.

## Verification

`python -B tools/activity_tests.py` runs deterministic fixtures including the
normal confirmed job path, exact prompt/output/coverage/authority parity with
telemetry disabled, retries, rejection counts, history and concurrent reads.
No G-EVID1 rerun, semantic tuning or next-experiment execution is required.
Final validation and qualification results are recorded with the handoff.
