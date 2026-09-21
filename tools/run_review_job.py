from __future__ import annotations

"""Run one queued experiment-review job in its own process and its own private runtime (spec 2.33).

  python tools/run_review_job.py <job record path>

Started by the conversational adapter after the operator confirms, or by an operator directly. It runs the operator-chosen
queue task through the frozen reviewer, then records the outcome in the job record.

The review runs against a **private runtime root** of its own, created for this job and written to by nothing else. The
frozen reviewer always guards its runtime root, so pointing that root at the live data directory meant every ordinary
conversation, cognition or vector-store write during a multi-hour review counted as a mutation. The private root is
quiescent, so live application state may keep changing while the review runs without touching its guard.

What the review guards is therefore wider than before, not narrower:
  - the private runtime root, where only this review's own output directory may appear;
  - the selected package, verified by the reviewer's own loader and digests;
  - the installed package area and the existing review artifacts, both of which nothing writes during a review;
  - the Eidolon source tree, which the live runs did not guard at all.

Ordinary application state is not copied into the private runtime and is not guarded, because the reviewer has no reason
to touch it and it changes for reasons that have nothing to do with the review. The artifact is copied into the live
review area after the guarded window closes, so listing, status and receipts are unchanged. The review itself stays
read-only and non-authoritative.
"""

from datetime import datetime, timezone
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

PRIVATE_RUNTIME_AREA = "research_review_runtimes"
SOURCE_ROOT = ROOT

# Which reviewer architecture runs a job. The job record chooses; this is only the fallback for records written before
# the field existed, which must keep running on the reviewer they were queued against.
REVIEWERS = {"v2731.8": "experiment_review", "v2733.0": "experiment_review_hierarchical"}
# Contracts that existed but no longer resolve to any module. A job record pinned to one of these fails
# loudly rather than being quietly run on a successor whose behaviour differs.
SUPERSEDED = {"v2732.0": "v2732.1", "v2732.1": "v2733.0"}
DEFAULT_REVIEWER_CONTRACT = "v2731.8"


def resolve_reviewer(contract: str):
    """Import the reviewer module a job asks for. An unknown contract fails the job rather than silently substituting."""
    import importlib

    wanted = str(contract or DEFAULT_REVIEWER_CONTRACT)
    name = REVIEWERS.get(wanted)
    if name is None:
        if wanted in SUPERSEDED:
            raise LookupError(f"superseded_reviewer_contract:{wanted}:superseded_by:{SUPERSEDED[wanted]}")
        raise LookupError(f"unknown_reviewer_contract:{contract}")
    module = importlib.import_module(name)
    if module.CONTRACT_VERSION != wanted:
        raise RuntimeError(f"reviewer_contract_mismatch:{module.CONTRACT_VERSION}")
    return module

# Deterministic tests drive the real runner, private runtime and guard through a stub model. Production leaves both
# None, so the reviewer resolves its own configured local model exactly as before.
CALL_MODEL: Callable[[str, int], tuple[str, dict[str, Any]]] | None = None
IDENTITY: Mapping[str, Any] | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def private_runtime_root(job_id: str, root: str | Path) -> Path:
    """The private runtime this job's review owns. Only the review writes here, so the guard has nothing to race."""
    private = Path(root) / PRIVATE_RUNTIME_AREA / str(job_id)
    private.mkdir(parents=True, exist_ok=True)
    return private


def guarded_research_roots(root: str | Path) -> list[Path]:
    """Live areas a review must leave exactly as it found them: installed packages and each existing review artifact.

    Every earlier review is guarded as its own directory rather than through the review area that contains them,
    because the research queue keeps ``local_queue.json`` in that same directory and the adapter deliberately lets
    other deterministic queue work continue while a review runs. Guarding the parent would make that ordinary queue
    write a mutation, which is the class of false failure this design exists to remove.
    """
    import experiment_review as er
    import conversational_experiment_review as adapter

    package_area = Path(root) / adapter.PACKAGE_AREA
    review_area = Path(root) / er.REVIEW_AREA
    for path in (package_area, review_area):
        path.mkdir(parents=True, exist_ok=True)
    return [package_area, *sorted(p for p in review_area.iterdir() if p.is_dir())]


def publish_artifact(private: Path, root: str | Path, review_id: str) -> Path:
    """Copy the finished artifact into the live review area, after the guarded window has closed.

    The copy happens once the reviewer has taken its closing snapshot and returned, so publishing a review can never be
    what a review's own guard reports.
    """
    import experiment_review as er

    source = Path(private) / er.REVIEW_AREA / review_id
    destination = Path(root) / er.REVIEW_AREA / review_id
    if not source.is_dir() or destination.exists():
        return destination
    shutil.copytree(source, destination)
    return destination


def run_job(job_path: str | Path, *, review: Callable[[str], Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Run the job's queue task once and record the outcome. Returns the final job record."""
    path = Path(job_path)
    job = json.loads(path.read_text(encoding="utf-8"))
    os.environ.setdefault("EIDOLON_DATA_DIR", job["runtime_root"])
    import conversational_experiment_review as adapter
    import experiment_review as er
    import local_research_queue as lrq

    root = job["runtime_root"]
    private = private_runtime_root(job["job_id"], root)
    protected = guarded_research_roots(root)
    contract = str(job.get("reviewer_contract") or DEFAULT_REVIEWER_CONTRACT)
    reviewer = resolve_reviewer(contract)
    runner = review or (lambda target: reviewer.review_experiment(target, runtime_root_path=private, source_root=SOURCE_ROOT,
                                                                  protected_roots=protected, call_model=CALL_MODEL, identity=IDENTITY))
    from review_activity import observing_review
    observer = None
    try:
        # Custom legacy runners may guard the entire live runtime. Their existing
        # job record remains observable, but do not write sidecars inside that guard.
        with (observing_review(job, root, reviewer) if review is None else nullcontext()) as observer:
            task = lrq.run_task(job["task_id"], runner=runner, root=root)
    except Exception as error:  # a failed review is recorded, never hidden, and never retried on its own
        failed = adapter.save_job({**job, "status": "failed", "failure": f"{type(error).__name__}: {error}"[:300],
                                   "finished": _now(), "private_runtime_root": str(private)}, root)
        if observer:
            observer.finish(failed)
        return failed
    review_id = str(task.get("review_id") or "")
    location = publish_artifact(private, root, review_id) if review_id else ""
    artifact = json.loads((Path(location) / "review.json").read_text(encoding="utf-8")) if review_id else {}
    coverage = artifact.get("coverage", {})
    levels = coverage.get("levels", {})
    guard = artifact.get("mutation_guard", {})
    final = {
        **job, "status": "completed", "finished": _now(), "review_id": review_id, "review_status": artifact.get("status", ""),
        # Which architecture produced this artifact, taken from the artifact itself rather than from what was asked for.
        "reviewer": {"contract_version": artifact.get("contract_version", ""),
                     "baseline_contract": artifact.get("baseline_contract", ""),
                     "architecture": artifact.get("architecture", "flat_synthesis"),
                     "module_sha256": ((artifact.get("provenance") or {}).get("capability") or {}).get("module_sha256", ""),
                     "review_id_vocabulary": ((artifact.get("provenance") or {}).get("review_id_vocabulary")
                                              or ["O", "PS", "DS"])},
        "task_status": task.get("status"), "location": str(location) if review_id else "",
        "private_runtime_root": str(private),
        "coverage": {k: coverage.get(k) for k in ("complete", "required_parts", "reviewed_required_parts", "required_coverage",
                                                  "grounded_observations")},
        "levels": {k: {kk: vv for kk, vv in (levels.get(k) or {}).items() if isinstance(vv, (int, float, str))} for k in levels},
        "checks": {"mutation_guard_passed": guard.get("passed"),
                   "source_tree_guarded": bool((guard.get("protected") or {}).get("source_tree")),
                   "guarded_roots": [str(p) for p in (guard.get("protected") or {}).get("roots", [])],
                   "authority_flags_all_false": all(v is False for v in (artifact.get("authority") or {}).values()) or None,
                   "non_authoritative": artifact.get("non_authoritative"),
                   "provider_attempts": artifact.get("runtime_accounting", {}).get("provider_attempts")},
    }
    saved = adapter.save_job(final, root)
    if observer:
        observer.finish(saved, artifact)
    return saved


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
