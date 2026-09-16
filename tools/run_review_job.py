from __future__ import annotations

"""Run one queued experiment-review job in its own process (spec 2.25).

  python tools/run_review_job.py <job record path>

Started by the conversational adapter after the operator confirms, or by an operator directly. It runs the operator-chosen
queue task through the frozen reviewer, then records the outcome in the job record. The record is written before and
after the review only: the reviewer's mutation guard fingerprints the runtime root while it runs, so nothing may write
there in between. The review itself stays read-only and non-authoritative.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_job(job_path: str | Path, *, review: Callable[[str], Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Run the job's queue task once and record the outcome. Returns the final job record."""
    path = Path(job_path)
    job = json.loads(path.read_text(encoding="utf-8"))
    os.environ.setdefault("EIDOLON_DATA_DIR", job["runtime_root"])
    import conversational_experiment_review as adapter
    import experiment_review as er
    import local_research_queue as lrq

    root = job["runtime_root"]
    runner = review or (lambda target: er.review_experiment(target, runtime_root_path=root, protected_roots=[]))
    try:
        task = lrq.run_task(job["task_id"], runner=runner, root=root)
    except Exception as error:  # a failed review is recorded, never hidden, and never retried on its own
        return adapter.save_job({**job, "status": "failed", "failure": f"{type(error).__name__}: {error}"[:300], "finished": _now()}, root)
    review_id = str(task.get("review_id") or "")
    artifact = json.loads((Path(root) / er.REVIEW_AREA / review_id / "review.json").read_text(encoding="utf-8")) if review_id else {}
    coverage = artifact.get("coverage", {})
    levels = coverage.get("levels", {})
    final = {
        **job, "status": "completed", "finished": _now(), "review_id": review_id, "review_status": artifact.get("status", ""),
        "task_status": task.get("status"), "location": str(Path(root) / er.REVIEW_AREA / review_id) if review_id else "",
        "coverage": {k: coverage.get(k) for k in ("complete", "required_parts", "reviewed_required_parts", "required_coverage",
                                                  "grounded_observations")},
        "levels": {k: {kk: vv for kk, vv in (levels.get(k) or {}).items() if isinstance(vv, (int, float, str))} for k in levels},
        "checks": {"mutation_guard_passed": artifact.get("mutation_guard", {}).get("passed"),
                   "authority_flags_all_false": all(v is False for v in (artifact.get("authority") or {}).values()) or None,
                   "non_authoritative": artifact.get("non_authoritative"),
                   "provider_attempts": artifact.get("runtime_accounting", {}).get("provider_attempts")},
    }
    return adapter.save_job(final, root)


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "message": "usage: run_review_job.py <job record path>"}))
        return 2
    record = run_job(sys.argv[1])
    print(json.dumps({"ok": record["status"] == "completed", "job_id": record["job_id"], "status": record["status"],
                      "review_id": record.get("review_id", ""), "review_status": record.get("review_status", "")}, indent=1))
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
