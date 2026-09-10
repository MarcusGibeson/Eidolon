from __future__ import annotations

"""Bridge evidence-bound product plans into the retained isolated coder."""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from isolated_coding_execution import (
    authorize_and_run_isolated_coding_execution,
    load_isolated_coding_execution,
    prepare_isolated_coding_execution,
    public_isolated_coding_execution,
)
from isolated_coding_execution_foundations import (
    _manifest_digest,
    _walk_project,
    cancel_coding_work_request,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from metadata_mutation_coordination import metadata_mutation_lock
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root


CONTRACT_VERSION = "v2503.4.2"
_PLAN_ID = r"devplan_[a-f0-9]{24}"
_REVIEW = re.compile(
    rf"^Review product plan (?P<plan_id>{_PLAN_ID}) digest (?P<digest>[a-f0-9]{{16}})[.!?]*$",
    re.IGNORECASE,
)
_PREPARE = re.compile(
    rf"^Prepare isolated product repair (?P<plan_id>{_PLAN_ID}) digest (?P<digest>[a-f0-9]{{16}})[.!?]*$",
    re.IGNORECASE,
)
_RUN_CYCLE = re.compile(
    rf"^Run one supervised product repair cycle for (?P<plan_id>{_PLAN_ID}) digest (?P<digest>[a-f0-9]{{16}})[.!?]*$",
    re.IGNORECASE,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _plan_path(plan_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "product_candidate_plans" / f"{plan_id}.json"


def _valid(record: Mapping[str, Any]) -> bool:
    stored = str(record.get("product_plan_record_digest") or "")
    return bool(stored and stored == _digest({key: value for key, value in record.items() if key != "product_plan_record_digest"}))


def _seal(record: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result.pop("product_plan_record_digest", None)
    result["product_plan_record_digest"] = _digest(result)
    return result


def _safe_relative(root: Path, value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip().lstrip("/")
    relative = PurePosixPath(text)
    if not text or relative.is_absolute() or ".." in relative.parts:
        return ""
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return ""
    return relative.as_posix() if candidate.is_file() else ""


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_product_candidate_plan(
    plan: Mapping[str, Any], *, source_root: str | Path, runtime_root=None
) -> dict[str, Any]:
    """Persist one deterministic planner result without expanding authority."""

    root = Path(source_root).expanduser().resolve()
    plan_id = str(plan.get("candidate_plan_id") or "").lower()
    plan_digest = str(plan.get("candidate_plan_digest") or "").lower()
    stable = {key: value for key, value in plan.items() if key != "candidate_plan_digest"}
    if not re.fullmatch(_PLAN_ID, plan_id) or len(plan_digest) != 64 or plan_digest != _digest(stable):
        return {"ok": False, "status": "product_plan_identity_invalid", "source_modified": False, "authority_granted": False}
    targets = [_safe_relative(root, value) for value in plan.get("target_files") or ()]
    tests = [_safe_relative(root, value) for value in plan.get("test_files") or ()]
    if not targets or not tests or any(not value for value in [*targets, *tests]):
        return {"ok": False, "status": "product_plan_scope_invalid", "source_modified": False, "authority_granted": False}
    binding = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": "product_plan_registered",
        "plan_id": plan_id,
        "plan_digest": plan_digest,
        "evidence_id": str(plan.get("evidence_id") or ""),
        "evidence_digest": str(plan.get("evidence_digest") or ""),
        "evidence_class": str(plan.get("evidence_class") or ""),
        "issue_domain": str(plan.get("issue_domain") or ""),
        "target_files": targets,
        "test_files": tests,
        "acceptance_criteria": [str(value) for value in plan.get("acceptance_criteria") or ()],
        "source_file_digests": {
            value: _file_digest(root / Path(*PurePosixPath(value).parts)) for value in [*targets, *tests]
        },
        "source_root_digest": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        "lifecycle_state": "registered",
        "coding_request_id": "",
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "workspace_prepared": False,
        "source_modified": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "authority_granted": False,
        "content_free": True,
    }
    path = _plan_path(plan_id, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        existing = _read_json(path)
        if existing:
            if not _valid(existing) or str(existing.get("plan_digest") or "") != plan_digest:
                return {"ok": False, "status": "product_plan_registration_conflict", "source_modified": False, "authority_granted": False}
            return {**existing, "operation_status": "restored"}
        record = _seal(binding)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def _load(plan_id: str, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_plan_path(plan_id, runtime_root)) or {}
    return dict(record) if record and _valid(record) else {}


def _capture_plan_outcome(*, runtime_root, plan_id: str, status: str, validated: bool) -> dict[str, Any]:
    """Best-effort capture of observable planning/governance outcomes only."""
    try:
        try:
            from model_training.training_capture_adapters import capture_validated_outcome
            from model_training.training_policy import resolve_training_evidence_capture_policy
        except ImportError:
            from model_training.training_capture_adapters import capture_validated_outcome
            from model_training.training_policy import resolve_training_evidence_capture_policy
        policy = resolve_training_evidence_capture_policy()
        task_type = "planning" if validated else "governance"
        if not policy.capture_enabled(task_type):
            return {"ok": False, "status": "training_capture_disabled"}
        return capture_validated_outcome(
            runtime_root=runtime_root, capture_authorized=True, task_type=task_type,
            input_payload={"plan_id_digest": _digest(plan_id), "operation": "product_plan_review"},
            model_output={"status": status, "validated": validated},
            validation={"passed": True, "deterministic": True, "status": status},
            source_system="product_plan_lifecycle", auto_sanitize=policy.auto_sanitize_enabled,
        )
    except Exception as exc:
        try:
            from model_training.training_capture_runtime import persist_capture_failure
        except ImportError:
            from model_training.training_capture_runtime import persist_capture_failure
        return persist_capture_failure(
            runtime_root=runtime_root, capability="planning_governance",
            status="training_capture_failed", failure_class=type(exc).__name__,
        )


def review_product_candidate_plan(
    plan_id: str, expected_digest: str, *, source_root: str | Path, runtime_root=None
) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve()
    path = _plan_path(plan_id, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        record = _load(plan_id, runtime_root)
        if not record or not str(record.get("plan_digest") or "").startswith(expected_digest.lower()):
            _capture_plan_outcome(runtime_root=runtime_root, plan_id=plan_id, status="product_plan_missing_or_stale", validated=False)
            return {"active": True, "ok": False, "status": "product_plan_missing_or_stale", "source_modified": False, "authority_granted": False}
        current = {}
        for relative in [*(record.get("target_files") or ()), *(record.get("test_files") or ())]:
            safe = _safe_relative(root, relative)
            if not safe:
                return {"active": True, "ok": False, "status": "product_plan_source_scope_changed", "source_modified": False, "authority_granted": False}
            current[safe] = _file_digest(root / Path(*PurePosixPath(safe).parts))
        if current != dict(record.get("source_file_digests") or {}):
            _capture_plan_outcome(runtime_root=runtime_root, plan_id=plan_id, status="product_plan_source_stale", validated=False)
            return {"active": True, "ok": False, "status": "product_plan_source_stale", "source_modified": False, "authority_granted": False}
        reviewed = dict(record)
        if record.get("lifecycle_state") == "execution_stopped":
            reviewed["retry_lineage_digest"] = _digest({
                "prior_request_id": str(record.get("coding_request_id") or ""),
                "prior_execution_result_digest": str(record.get("execution_result_digest") or ""),
            })
            reviewed["retry_count"] = int(record.get("retry_count") or 0) + 1
        reviewed.update({
            "status": "product_plan_reviewed",
            "lifecycle_state": "scope_reviewed",
            "scope_review_digest": _digest({"plan_digest": record["plan_digest"], "source_file_digests": current}),
        })
        _atomic_json(path, _seal(reviewed))
    _capture_plan_outcome(runtime_root=runtime_root, plan_id=plan_id, status="product_plan_reviewed", validated=True)
    phrase = f"Prepare isolated product repair {plan_id} digest {str(record['plan_digest'])[:16]}."
    return {
        "active": True,
        "event": "product_plan_scope_reviewed",
        "ok": True,
        "status": "product_plan_reviewed",
        "conversation_response": (
            f"I reviewed product plan {plan_id} against its exact evidence and current source snapshot. "
            f"Its {len(record.get('target_files') or ())} target files and {len(record.get('test_files') or ())} focused tests remain present and unchanged. "
            "No provider or test ran and no source changed. To prepare the disposable repair workspace, say exactly: " + phrase
        ),
        "next_phrase": phrase,
        "provider_contacted": False,
        "tests_executed": False,
        "source_modified": False,
        "authority_granted": False,
    }


def prepare_isolated_product_repair(
    plan_id: str, expected_digest: str, *, source_root: str | Path, runtime_root=None
) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve()
    record = _load(plan_id, runtime_root)
    if not record or record.get("lifecycle_state") not in {"scope_reviewed", "workspace_prepared"}:
        return {"active": True, "ok": False, "status": "product_plan_review_required", "source_modified": False, "authority_granted": False}
    if not str(record.get("plan_digest") or "").startswith(expected_digest.lower()):
        return {"active": True, "ok": False, "status": "product_plan_stale", "source_modified": False, "authority_granted": False}
    objective = (
        f"Repair the attributable {record.get('evidence_class')} in {record.get('issue_domain')} bound to "
        f"evidence {record.get('evidence_id')}. Reproduce the current-target failure with a synthetic fixture, "
        "identify the narrow root cause, and make only the smallest evidence-backed repair."
    )
    retry_lineage_digest = str(record.get("retry_lineage_digest") or "")
    source_inventory, _ = _walk_project(root)
    current_source_manifest_digest = _manifest_digest(source_inventory)
    regression_test_path = f"tools/product_repair_{plan_id.removeprefix('devplan_')}_tests.py"
    request = create_or_restore_coding_work_request(
        user_objective=objective,
        target_project=root,
        requirements=[
            objective,
            f"Bind this repair to current source manifest {current_source_manifest_digest}.",
            *([f"Bind this retry to prior stopped-cycle lineage {retry_lineage_digest}."] if retry_lineage_digest else []),
            "Confine source edits to: " + ", ".join(record.get("target_files") or ()),
            "Confine focused test edits to: " + ", ".join(record.get("test_files") or ()),
            f"Create a focused synthetic regression fixture at {regression_test_path} without embedding private conversation content.",
        ],
        acceptance_criteria=record.get("acceptance_criteria") or (),
        constraints=[
            "Preserve conversation, memory, action-routing, privacy, and authority behavior.",
            "Treat listed source files as hypotheses and do not edit unrelated source or test files.",
            "Existing focused tests are immutable verification fixtures; do not modify or delete them.",
            "Use synthetic content-free reproduction evidence.",
        ],
        prohibited_actions=["Do not modify active source, install dependencies, contact another provider, or promote a release."],
        expected_artifacts=["Focused reproduction fixture", "Reviewable isolated diff", "Bounded verification evidence"],
        verification=[*(record.get("test_files") or ()), "Compile changed Python modules", "Verify active source remains unchanged"],
        context_paths=[*(record.get("target_files") or ()), *(record.get("test_files") or ())],
        runtime_root=runtime_root,
    )
    if request.get("ok") is not True:
        return {"active": True, **request}
    request_id = str(request.get("request_id") or "")
    prior_request_id = str(record.get("coding_request_id") or "")
    if prior_request_id and prior_request_id != request_id:
        cancel_coding_work_request(prior_request_id, runtime_root=runtime_root)
    stages = (
        lambda: inspect_coding_project(request_id, runtime_root=runtime_root),
        lambda: create_or_restore_coding_work_plan(request_id, runtime_root=runtime_root),
        lambda: materialize_or_restore_isolated_coding_workspace(request_id, runtime_root=runtime_root),
        lambda: prepare_isolated_coding_execution(request_id, runtime_root=runtime_root),
    )
    result: dict[str, Any] = {}
    for stage in stages:
        result = stage()
        if result.get("ok") is not True:
            return {"active": True, **result}
    path = _plan_path(plan_id, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        latest = _load(plan_id, runtime_root)
        latest.update({
            "status": "product_repair_workspace_prepared",
            "lifecycle_state": "workspace_prepared",
            "coding_request_id": request_id,
            "source_manifest_digest": current_source_manifest_digest,
            "workspace_prepared": True,
        })
        _atomic_json(path, _seal(latest))
    public = public_isolated_coding_execution(result)
    phrase = str(public.get("authorization_phrase") or "")
    return {
        "active": True,
        "event": "product_repair_workspace_prepared",
        "ok": True,
        "status": "product_repair_workspace_prepared",
        "conversation_response": (
            f"I prepared isolated coding request {request_id} for product plan {plan_id}. The source snapshot, target scope, "
            "focused tests, and disposable workspace are bound to the request. No provider or test ran and active source is unchanged. "
            "To authorize one isolated implementation and verification run, say exactly: " + phrase
        ),
        "isolated_coding_execution": public,
        "next_phrase": phrase,
        "provider_contacted": False,
        "tests_executed": False,
        "source_modified": False,
        "authority_granted": False,
    }


def run_one_supervised_product_repair_cycle(
    plan_id: str,
    expected_digest: str,
    *,
    source_root: str | Path,
    runtime_root=None,
    provider_generate=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    """Review, prepare, execute, and verify one isolated repair authorization."""

    prior = _load(plan_id, runtime_root)
    if prior and str(prior.get("plan_digest") or "").startswith(expected_digest.lower()):
        current = {}
        root = Path(source_root).expanduser().resolve()
        for relative in [*(prior.get("target_files") or ()), *(prior.get("test_files") or ())]:
            safe = _safe_relative(root, relative)
            if safe:
                current[safe] = _file_digest(root / Path(*PurePosixPath(safe).parts))
        request_id = str(prior.get("coding_request_id") or "")
        sealed = load_isolated_coding_execution(request_id, runtime_root=runtime_root) if request_id else {}
        public = public_isolated_coding_execution(sealed) if sealed else {}
        if (
            current == dict(prior.get("source_file_digests") or {})
            and public.get("phase") == "sealed"
            and prior.get("lifecycle_state") == "candidate_ready"
        ):
            succeeded = public.get("status") == "isolated_coding_execution_completed" and public.get("ok") is True
            return {
                "active": True,
                "event": "product_repair_cycle_restored",
                "ok": succeeded,
                "status": "product_repair_candidate_ready" if succeeded else str(public.get("status") or "product_repair_cycle_stopped"),
                "conversation_response": (
                    f"I restored the already completed supervised product repair cycle for {plan_id}. "
                    f"Its isolated result for {request_id} remains {'verified and ready for review' if succeeded else 'safely stopped'}. "
                    "No provider or test ran again, active source is unchanged, and application still requires separate authority."
                ),
                "plan_id": plan_id,
                "request_id": request_id,
                "isolated_coding_execution": public,
                "provider_contacted": False,
                "provider_request_count": 0,
                "tests_executed": False,
                "source_modified": False,
                "application_authorized": False,
                "installation_authorized": False,
                "release_authorized": False,
                "authority_granted": False,
                "operator_review_required": True,
                "operation_status": "restored",
            }

    reviewed = review_product_candidate_plan(
        plan_id, expected_digest, source_root=source_root, runtime_root=runtime_root
    )
    if reviewed.get("ok") is not True:
        status = str(reviewed.get("status") or "product_repair_cycle_review_blocked")
        if status == "product_plan_source_stale":
            explanation = (
                f"The supervised product repair cycle for {plan_id} did not run because its bound source snapshot is stale. "
                "The active source changed after this plan was created, so the previous plan and execution authority cannot "
                "be reused. No provider or test ran, active source was not modified, and no authority was created. "
                "Continue supervised development to bind the attributable evidence to a new current-source plan."
            )
        else:
            explanation = (
                f"The supervised product repair cycle for {plan_id} did not run because plan review stopped at {status}. "
                "No provider or test ran, active source was not modified, and no authority was created."
            )
        return {
            "active": True,
            "event": "product_repair_cycle_review_blocked",
            **reviewed,
            "conversation_response": explanation,
            "provider_contacted": False,
            "tests_executed": False,
        }

    prepared = prepare_isolated_product_repair(
        plan_id, expected_digest, source_root=source_root, runtime_root=runtime_root
    )
    if prepared.get("ok") is not True:
        return {"active": True, "event": "product_repair_cycle_prepare_blocked", **prepared}

    execution = dict(prepared.get("isolated_coding_execution") or {})
    request_id = str(execution.get("request_id") or "")
    execution_digest = str(execution.get("execution_digest") or "")
    authorization_phrase = str(prepared.get("next_phrase") or execution.get("authorization_phrase") or "")
    sealed_replay = execution.get("phase") == "sealed" and bool(execution.get("status"))
    if not request_id or not execution_digest or (not authorization_phrase and not sealed_replay):
        return {
            "active": True,
            "event": "product_repair_cycle_execution_binding_missing",
            "ok": False,
            "status": "product_repair_cycle_execution_binding_missing",
            "conversation_response": "The product repair cycle stopped before provider execution because its exact execution binding was unavailable. Active source is unchanged.",
            "source_modified": False,
            "authority_granted": False,
        }

    if sealed_replay:
        result = execution
        public = execution
    else:
        result = authorize_and_run_isolated_coding_execution(
            request_id,
            expected_execution_digest=execution_digest,
            authorization_phrase=authorization_phrase,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            python_executable=python_executable,
            node_executable=node_executable,
        )
        public = public_isolated_coding_execution(result)
    succeeded = result.get("status") == "isolated_coding_execution_completed" and result.get("ok") is True

    path = _plan_path(plan_id, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        current = _load(plan_id, runtime_root)
        if current:
            current.update({
                "status": "product_repair_candidate_ready" if succeeded else "product_repair_cycle_stopped",
                "lifecycle_state": "candidate_ready" if succeeded else "execution_stopped",
                "coding_request_id": request_id,
                "execution_status": str(result.get("status") or "product_repair_cycle_stopped"),
                "execution_result_digest": str(result.get("execution_result_digest") or ""),
                "review_digest": str(result.get("review_digest") or ""),
            })
            _atomic_json(path, _seal(current))

    if succeeded:
        response = (
            f"I completed one supervised product repair cycle for {plan_id}. I revalidated its source scope, prepared "
            f"the disposable workspace, consumed the exact isolated execution authorization for {request_id}, and passed "
            f"bounded verification. A reviewable diff covering {public.get('changed_file_count', 0)} file(s) is ready. "
            "Active source is unchanged; application or installation still requires your separate authority."
        )
    else:
        detail_code = str(public.get("generation_rejection_code") or public.get("provider_context_rejection_code") or "")
        detail = f" ({detail_code})" if detail_code else ""
        response = (
            f"The supervised product repair cycle for {plan_id} stopped safely at "
            f"{result.get('status', 'product_repair_cycle_stopped')}{detail}. The exact execution authorization was "
            "consumed only for this isolated attempt. Active source was not modified and application authority remains denied."
        )
    return {
        "active": True,
        "event": "product_repair_cycle_completed" if succeeded else "product_repair_cycle_stopped",
        "ok": succeeded,
        "status": "product_repair_candidate_ready" if succeeded else str(result.get("status") or "product_repair_cycle_stopped"),
        "conversation_response": response,
        "plan_id": plan_id,
        "request_id": request_id,
        "isolated_coding_execution": public,
        "provider_contacted": bool(result.get("provider_contacted")),
        "provider_request_count": int(result.get("provider_request_count") or 0),
        "tests_executed": bool(result.get("tests_executed")),
        "source_modified": False,
        "application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "operator_review_required": True,
    }


def process_product_plan_control(
    message: str,
    *,
    source_root: str | Path,
    runtime_root=None,
    provider_generate=None,
    python_executable: str | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    text = str(message or "").strip()
    match = _RUN_CYCLE.fullmatch(text)
    if match:
        return run_one_supervised_product_repair_cycle(
            match.group("plan_id").lower(),
            match.group("digest").lower(),
            source_root=source_root,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            python_executable=python_executable,
            node_executable=node_executable,
        )
    match = _REVIEW.fullmatch(text)
    if match:
        return review_product_candidate_plan(match.group("plan_id").lower(), match.group("digest").lower(), source_root=source_root, runtime_root=runtime_root)
    match = _PREPARE.fullmatch(text)
    if match:
        return prepare_isolated_product_repair(match.group("plan_id").lower(), match.group("digest").lower(), source_root=source_root, runtime_root=runtime_root)
    return {"active": False, "event": "inactive"}


__all__ = [
    "CONTRACT_VERSION",
    "register_product_candidate_plan",
    "review_product_candidate_plan",
    "prepare_isolated_product_repair",
    "run_one_supervised_product_repair_cycle",
    "process_product_plan_control",
]
