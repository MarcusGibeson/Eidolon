# Mutation guard scope for adapter-launched reviews — proposal

**Status: proposed, not implemented. No code has been changed.**
Written 2026-09-16 after job `job_955f1d999e07f538` (review `72a40f4dc8a09ae3`, G-INVAR) finished
`mutation_guard_failed`.

## What happened

The review ran 2h 05m, detached, started by a confirmation in chat. It reached **19/19 parts, 100% package
coverage, 100 grounded observations**, and then failed its mutation guard on **20 changes, every one of them live
application state**:

| path | count |
|---|---|
| `cognition/*.json` | 13 |
| `conversation_policy_state/` | 2 |
| `conversation_runtime/` | 2 |
| `chroma/chroma.sqlite3` | 1 |
| `conversation_sessions/` | 1 |
| `dashboard_chat/` | 1 |

Nothing outside `…\AppData\Local\Eidolon\data` changed. One flagged file is the conversation operation that
*started* the review.

## Why it is structural, not incidental

`experiment_review.py:899` builds the guarded set as:

    guarded_roots = [root, *protected_roots]

`root` is the runtime data directory, and it is included **unconditionally** — a caller cannot opt out, and passing
`protected_roots=[]` (which `tools/run_review_job.py` does) changes nothing.

The adapter's premise is that a review runs detached *while Eidolon keeps being used*. Eidolon writes its cognition,
conversation and vector-store state continuously. So every adapter-launched review trips this guard, always. The
earlier historical reviews passed only because they ran from a harness with the app idle.

Two further facts worth recording:

- `protected.source_tree` was **false** for this run: `run_review_job.py` passes no `source_root`, so the source tree
  was never fingerprinted. The run proves nothing about source changes either way.
- `package` was `true` and clean: the package was verified unchanged.

## Option A (recommended) — give the review a quiescent runtime root

Keep the frozen reviewer byte-identical. Change only `tools/run_review_job.py`, which is adapter code from 2.25:

    er.review_experiment(
        target,
        runtime_root_path=<private review root>,     # today: the live data dir
        source_root=ROOT,                            # today: omitted, so source is unguarded
        protected_roots=[live_data/"research_packages",
                         live_data/"research_reviews"],
    )

**Guarded after the change**

| what | why it is safe to guard |
|---|---|
| the private review root | only this job writes there |
| the package directory | already guarded; only an operator installs packages |
| `research_packages/` in the live data dir | quiescent during a run |
| `research_reviews/` in the live data dir | quiescent; proves no earlier review was altered |
| **the source tree** | newly guarded — a tightening over today |

**No longer guarded:** `cognition/`, `conversation_*`, `dashboard_chat/`, `chroma/`, `research_jobs/` and the rest
of the live data directory — the operator's own application state, which the reviewer has no reason to touch and
which changes for reasons that have nothing to do with the review.

Net effect: the guard gets **stricter** where research integrity lives (source tree added) and stops watching the
one area guaranteed to change. The artifact is copied into the live `research_reviews/` area after the guarded
window closes, so listing and status keep working unchanged.

Cost: the artifact lands in the live area by a copy rather than by being written there directly, and
`reviews_of()`/`job_status()` read it from there as they do today.

## Option B — narrow the scope inside the reviewer

Change `experiment_review.py:899` to guard named subtrees rather than the whole root. This is the direct fix, but it
edits the frozen module: the sha changes, and `v2731.8` / `d158e253…` stops being the module your coworking
validation was accepted against. Every earlier review's "same frozen reviewer" claim would then refer to a retired
version.

## Option C — documented operating procedure

Leave everything as it is and accept that a review only passes cleanly with Eidolon closed. Costs nothing, and
gives up the adapter's main promise: starting a review from chat and carrying on working.

## What is not proposed

No threshold is loosened, no gate is removed, and no past review is rescored. Option A changes which directories are
watched, not what counts as a violation.
