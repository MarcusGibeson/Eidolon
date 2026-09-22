from __future__ import annotations

"""Run one governed failed-unit recovery in its own process, with an Activity and an operator control.

  python tools/run_recovery_job.py <job record path>

Started by ``review_recovery.start_recovery`` after the operator confirms, or by the research control when an
operator resumes a paused recovery. It adds visibility, never authority: admissibility, compatibility and the
operator's acknowledgement were all settled before the job record existed, and the work itself is the same
``review_recovery.recover`` operation, called once, with the Activity observer wired to the reviewer's own events.

The recovery writes into a private runtime of its own and guards the live package area and every existing review
directory - including the source review it is continuing - so the mutation guard proves the original was untouched.
The derived artifact is published into the live review area after the guarded window closes.
"""

import json
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import run_review_job as review_runner  # noqa: E402


def run_job(job_path: str | Path) -> dict[str, Any]:
    """Perform the recovery this job record describes and record its outcome."""
    import os

    path = Path(job_path)
    job = json.loads(path.read_text(encoding="utf-8"))
    os.environ.setdefault("EIDOLON_DATA_DIR", job["runtime_root"])

    import conversational_experiment_review as adapter
    import experiment_review as base
    import review_recovery as rec
    from review_activity import observing_review

    root = job["runtime_root"]
    recovery = dict(job.get("recovery") or {})
    private = Path(job.get("private_runtime_root") or review_runner.private_runtime_root(job["job_id"], root))
    protected = review_runner.guarded_research_roots(root)
    source_id = str(recovery.get("source_review_id") or "")

    # The source artifact is staged read-only into the private runtime, so the recovery reads it there while the live
    # original stays guarded and provably untouched.
    staged = private / base.REVIEW_AREA / source_id
    staged.mkdir(parents=True, exist_ok=True)
    live_source = Path(root) / base.REVIEW_AREA / source_id / "review.json"
    if not (staged / "review.json").is_file():
        shutil.copy2(live_source, staged / "review.json")
    if base._sha256_file(staged / "review.json") != str(recovery.get("source_review_digest") or ""):
        failed = adapter.save_job({**job, "status": "failed", "failure": "staged_source_does_not_match_authorized_digest",
                                   "finished": review_runner._now()}, root)
        return failed

    # A recovery whose worker stopped leaves a live checkpoint; recover() continues it rather than re-sealing.
    resuming = bool(rec.resumable_checkpoint(job, root).get("resumable")) or str(job.get("status")) == "paused"
    observer = None
    holder: dict[str, Any] = {}
    try:
        with observing_review(job, root, rec, resuming=resuming) as observer:
            holder["observer"] = observer
            result = rec.recover(
                source_id, root=private, package_dir=job["package_dir"], confirmed=True,
                acknowledge_module_change=str(recovery.get("acknowledged_reviewer_module_change") or ""),
                units=list(recovery.get("units_planned") or []) or None,
                source_root=review_runner.SOURCE_ROOT, protected_roots=protected,
                call_model=review_runner.CALL_MODEL, identity=review_runner.IDENTITY,
                on_state=observer.on_reviewer_event)
            holder["result"] = result
    except Exception as error:  # a failed recovery is recorded, never hidden, and never retried on its own
        failed = adapter.save_job({**job, "status": "failed", "failure": f"{type(error).__name__}: {error}"[:300],
                                   "finished": review_runner._now()}, root)
        if observer:
            observer.finish(failed)
        return failed

    result = holder.get("result") or {}
    derived_id = str(result.get("derived_review_id") or recovery.get("derived_review_id") or "")
    if str(result.get("status")) == "paused":
        # Paused, not finished: the job stays alive, holds its identity, and publishes no artifact yet.
        paused = adapter.save_job({**job, "status": "paused", "paused": review_runner._now(),
                                   "review_id": derived_id, "recovery_result": result}, root)
        if observer:
            observer.finish(paused, result)
        return paused

    published = review_runner.publish_artifact(private, root, derived_id)
    artifact = {}
    if (published / "review.json").is_file():
        artifact = json.loads((published / "review.json").read_text(encoding="utf-8"))
    lineage = private / base.REVIEW_AREA / derived_id / rec.LINEAGE_NAME
    if lineage.is_file() and not (published / rec.LINEAGE_NAME).is_file():
        shutil.copy2(lineage, published / rec.LINEAGE_NAME)
    done = adapter.save_job({**job, "status": "completed", "finished": review_runner._now(),
                             "review_id": derived_id, "review_status": str(artifact.get("status") or ""),
                             "location": str(published), "recovery_result": result}, root)
    if observer:
        observer.finish(done, artifact)
    return done


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"ok": False, "message": "usage: run_recovery_job.py <job record path>"}))
        raise SystemExit(2)
    outcome = run_job(sys.argv[1])
    print(json.dumps({"ok": outcome.get("status") in ("completed", "paused"), "status": outcome.get("status"),
                      "review_id": outcome.get("review_id", ""), "failure": outcome.get("failure", "")}))
