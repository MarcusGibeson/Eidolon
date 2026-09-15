"""Operator tool: supervised, read-only experiment self-review and the operator-chosen local research queue (spec 2.18).

  python tools/review_experiment.py review <package_dir> [--protect PATH ...] [--protect-root DIR ...]
  python tools/review_experiment.py queue list
  python tools/review_experiment.py queue add independent_experiment_review <package_dir> [--note TEXT]
  python tools/review_experiment.py queue run <task_id> [--protect PATH ...] [--protect-root DIR ...]

Reviews are written only to <EIDOLON_DATA_DIR>/research_reviews/<review_id>/. The source tree, the package, every
--protect path and every --protect-root directory (plus the runtime root outside the review area) are fingerprinted
before and after; any change marks the review mutation_guard_failed. The review is a non-authoritative research
artifact and grants no authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as er  # noqa: E402
import local_research_queue as lrq  # noqa: E402


def _review(package: str, protect: list[str], protect_root: list[str]) -> dict:
    artifact = er.review_experiment(package, source_root=ROOT, protected_paths=protect, protected_roots=protect_root)
    coverage = artifact["coverage"]
    print(json.dumps({"review_id": artifact["review_id"], "status": artifact["status"], "mutation_guard_passed": artifact["mutation_guard"]["passed"],
                      "coverage": {k: coverage[k] for k in ("complete", "required_parts", "reviewed_required_parts", "required_coverage",
                                                            "delivered_to_synthesis", "grounded_observations", "missing", "synthesis")},
                      "grounded_observations": len(artifact["grounded_observations"]), "rejected_observations": len(artifact["rejected_observations"]),
                      "runtime_accounting": artifact["runtime_accounting"],
                      "written_to": str(er.runtime_root() / er.REVIEW_AREA / artifact["review_id"])}, indent=1))
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(prog="review_experiment", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rev = sub.add_parser("review")
    rev.add_argument("package")
    rev.add_argument("--protect", action="append", default=[])
    rev.add_argument("--protect-root", action="append", default=[])
    queue = sub.add_parser("queue")
    qsub = queue.add_subparsers(dest="queue_command", required=True)
    qsub.add_parser("list")
    add = qsub.add_parser("add")
    add.add_argument("kind")
    add.add_argument("target")
    add.add_argument("--note", default="")
    run = qsub.add_parser("run")
    run.add_argument("task_id")
    run.add_argument("--protect", action="append", default=[])
    run.add_argument("--protect-root", action="append", default=[])
    args = parser.parse_args()
    if args.command == "review":
        _review(args.package, args.protect, args.protect_root)
    elif args.queue_command == "list":
        q = lrq.load_queue()
        print(json.dumps({"ready_local_read_only": lrq.READY_LOCAL_READ_ONLY, "implemented": sorted(lrq.IMPLEMENTED),
                          "requires_external_or_operator_review": sorted(lrq.REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW), "tasks": q["tasks"]}, indent=1))
    elif args.queue_command == "add":
        print(json.dumps(lrq.add_task(args.kind, args.target, operator_note=args.note), indent=1))
    elif args.queue_command == "run":
        print(json.dumps(lrq.run_task(args.task_id, runner=lambda target: _review(target, args.protect, args.protect_root)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
