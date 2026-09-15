from __future__ import annotations

"""Operator-chosen local research queue (spec 2.18).

Marcus explicitly adds and runs each task; nothing here schedules, loops or runs on its own. Tasks are split into two
fixed categories. Only READY / LOCAL-READ-ONLY kinds can ever be queued, and only kinds with an implementation can run;
today that is the independent experiment review. Every other READY kind is listed so it can be chosen once it is built
under the same read-only boundary. Kinds that require external or operator review are refused outright.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import write_text_atomic
from experiment_review import REVIEW_AREA, runtime_root

CONTRACT_VERSION = "v2731.5"
QUEUE_FILE = "local_queue.json"
READY_LOCAL_READ_ONLY = {
    "independent_experiment_review": "independent self-review of one explicitly selected completed experiment package",
    "summarize_experiment_evidence": "summarize completed experiment evidence",
    "cluster_historical_failures": "cluster historical failures",
    "compare_stable_unstable_examples": "compare stable and unstable examples",
    "generate_candidate_test_cases": "generate candidate unlabeled test cases (provenance-marked, never authoritative gold)",
    "identify_architectural_questions": "identify unresolved architectural questions",
    "propose_competing_hypotheses": "propose competing hypotheses",
    "propose_discriminating_experiments": "propose bounded discriminating experiments",
}
REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW = {
    "authoritative_gold_labelling", "change_registered_experiment_semantics", "change_belief_policy", "change_source_code",
    "install_fixes", "promote_releases", "change_runtime_architecture", "modify_verification_policy", "authorize_self_development",
}
IMPLEMENTED = {"independent_experiment_review"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _path(root: str | Path | None) -> Path:
    return runtime_root(root) / REVIEW_AREA / QUEUE_FILE


def load_queue(root: str | Path | None = None) -> dict[str, Any]:
    path = _path(root)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"contract_version": CONTRACT_VERSION, "tasks": []}


def _save(queue: Mapping[str, Any], root: str | Path | None) -> None:
    write_text_atomic(_path(root), json.dumps(queue, indent=1, ensure_ascii=False))


def add_task(kind: str, target: str, *, operator_note: str = "", root: str | Path | None = None) -> dict[str, Any]:
    """Queue one operator-chosen task. Refuses any kind outside READY / LOCAL-READ-ONLY."""
    if kind in REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW:
        raise PermissionError("task_requires_external_or_operator_review")
    if kind not in READY_LOCAL_READ_ONLY:
        raise ValueError("task_kind_unknown")
    queue = load_queue(root)
    task = {"task_id": "lrq_" + hashlib.sha256(f"{kind}|{target}|{_now()}|{len(queue['tasks'])}".encode()).hexdigest()[:16], "kind": kind,
            "category": "READY_LOCAL_READ_ONLY", "target": str(target), "operator_note": str(operator_note)[:300], "status": "queued",
            "queued": _now(), "chosen_by": "operator", "authority": "read_only_non_authoritative"}
    queue["tasks"].append(task)
    _save(queue, root)
    return task


def run_task(task_id: str, *, runner: Callable[[str], Mapping[str, Any]], root: str | Path | None = None) -> dict[str, Any]:
    """Run one queued task when the operator asks. Only implemented read-only kinds run; the runner must return an artifact."""
    queue = load_queue(root)
    task = next((t for t in queue["tasks"] if t["task_id"] == task_id), None)
    if task is None:
        raise KeyError("task_not_found")
    if task["status"] != "queued":
        raise ValueError("task_not_queued")
    if task["kind"] not in IMPLEMENTED:
        raise NotImplementedError("task_kind_not_implemented")
    artifact = runner(task["target"])
    task.update(status="completed" if artifact.get("status") == "complete" else f"finished_{artifact.get('status')}", finished=_now(),
                review_id=artifact.get("review_id"))
    _save(queue, root)
    return task


__all__ = ["CONTRACT_VERSION", "READY_LOCAL_READ_ONLY", "REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW", "IMPLEMENTED", "load_queue", "add_task", "run_task"]
