from __future__ import annotations

"""Bounded multi-tool orchestration planning and evidence handoffs.

v1237 creates append-only, content-free orchestration plans bound to exact
operator-reviewed upstream evidence. It can validate tool contracts, record
externally produced step results, and prepare operator-reviewed handoff
proposals. It does not invoke tools, contact providers, run commands or tests,
modify projects, continue automatically, retry in the background, or grant
step/session authority.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from goal_motivation_work_priority_integration import _load_assessment as _load_alignment_assessment
from goal_motivation_work_priority_integration import _load_review as _load_alignment_review
from requirement_quality_assessment import load_requirement_quality_assessment
from requirement_quality_assessment import load_requirement_quality_assessment_review

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1237.8"
MAX_RECORDS = 300
PLAN_DISPOSITIONS = {"accept_plan", "hold", "reject", "request_changes"}
HANDOFF_DISPOSITIONS = {"accept_handoff", "hold", "reject", "request_changes"}
STEP_OUTCOMES = {"completed", "failed", "blocked", "timed_out", "cancelled", "inconclusive"}
ORCHESTRATION_STATES = {"ready", "incompatible", "cyclic", "missing_tool", "ambiguous"}
RISK_LEVELS = {"low", "medium", "high"}

AUTHORITY_FLAGS = {
    "orchestration_plan_preparation_authorized": True,
    "orchestration_review_authorized": True,
    "external_step_result_recording_authorized": True,
    "handoff_proposal_preparation_authorized": True,
    "tool_invocation_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "goal_mutation_authorized": False,
    "motivation_mutation_authorized": False,
    "lesson_mutation_authorized": False,
    "requirement_mutation_authorized": False,
    "cognition_write_authorized": False,
    "automatic_continuation_authorized": False,
    "automatic_retry_authorized": False,
    "background_execution_authorized": False,
    "launch_authorized": False,
    "resume_authorized": False,
    "pause_authorized": False,
    "cancel_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_TOKEN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_TOOL_ID = re.compile(r"^tool_[a-z0-9_]{2,48}$")
_STEP_ID = re.compile(r"^step_[a-z0-9_]{2,48}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")

_REVIEW_PLAN = re.compile(
    r"^review multi tool orchestration (?P<decision>accept_plan|hold|reject|request_changes) "
    r"for plan (?P<plan>orchestration_plan_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_RECORD_RESULT = re.compile(
    r"^record multi tool orchestration result (?P<outcome>completed|failed|blocked|timed_out|cancelled|inconclusive) "
    r"for plan (?P<plan>orchestration_plan_[a-f0-9]{24}) digest (?P<plan_digest>[a-f0-9]{64}) "
    r"review (?P<review>orchestration_review_[a-f0-9]{24}) digest (?P<review_digest>[a-f0-9]{64}) "
    r"step (?P<step>step_[a-z0-9_]{2,48}) tool (?P<tool>tool_[a-z0-9_]{2,48}) "
    r"input (?P<input>[a-f0-9]{64}) output (?P<output>[a-f0-9]{64}) evidence (?P<evidence>[a-f0-9]{64})[.!?]*$", re.I,
)
_PREPARE_HANDOFF = re.compile(
    r"^prepare multi tool orchestration handoff for result (?P<result>orchestration_result_[a-f0-9]{24}) "
    r"digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_REVIEW_HANDOFF = re.compile(
    r"^review multi tool orchestration handoff (?P<decision>accept_handoff|hold|reject|request_changes) "
    r"for handoff (?P<handoff>orchestration_handoff_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)
_SHOW_PLANS = re.compile(r"^show multi tool orchestration plans[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show multi tool orchestration reviews[.!?]*$", re.I)
_SHOW_RESULTS = re.compile(r"^show multi tool orchestration results[.!?]*$", re.I)
_SHOW_HANDOFFS = re.compile(r"^show multi tool orchestration handoffs[.!?]*$", re.I)
_SHOW_HANDOFF_REVIEWS = re.compile(r"^show multi tool orchestration handoff reviews[.!?]*$", re.I)
_SHOW_PLAN = re.compile(r"^show multi tool orchestration plan (?P<plan>orchestration_plan_[a-f0-9]{24})[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "multi-tool-orchestration.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for multi-tool orchestration lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "project_scoped": True,
        "operator_review_required": True,
        "historical_records_immutable": True,
        "tool_registry_snapshot_read_only": True,
        "tool_contracts_digest_bound": True,
        "fresh_separate_tool_authority_required": True,
        "fresh_separate_execution_authority_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "goals_modified": False,
        "motivations_modified": False,
        "lessons_modified": False,
        "requirements_modified": False,
        "cognition_written": False,
        "source_modified": False,
        "tool_invoked": False,
        "automatic_continuation_created": False,
        "hidden_retry_created": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_tool_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["multi_tool_orchestration_result_digest"] = _digest(row)
    return row


def _hex(value: Any, reason: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").lower()
    if allow_empty and not text:
        return ""
    if not _HEX64.fullmatch(text):
        raise ValueError(reason)
    return text


def _tokens(values: Iterable[Any], reason: str) -> list[str]:
    result = sorted({str(value or "").lower() for value in values})
    if any(not _TOKEN.fullmatch(value) for value in result):
        raise ValueError(reason)
    return result


def _normalize_tools(values: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values or []:
        tool_id = str(raw.get("tool_id") or "").lower()
        if not _TOOL_ID.fullmatch(tool_id) or tool_id in seen:
            raise ValueError("invalid_or_duplicate_tool_id")
        seen.add(tool_id)
        capabilities = _tokens(raw.get("capability_codes") or [], "invalid_tool_capability")
        if not capabilities:
            raise ValueError("tool_capability_required")
        risk = str(raw.get("risk_level") or "").lower()
        if risk not in RISK_LEVELS:
            raise ValueError("invalid_tool_risk_level")
        rows.append({
            "tool_id": tool_id,
            "capability_codes": capabilities,
            "consumes": _tokens(raw.get("consumes") or [], "invalid_tool_input_type"),
            "produces": _tokens(raw.get("produces") or [], "invalid_tool_output_type"),
            "input_contract_digest": _hex(raw.get("input_contract_digest"), "invalid_tool_input_contract_digest"),
            "output_contract_digest": _hex(raw.get("output_contract_digest"), "invalid_tool_output_contract_digest"),
            "risk_level": risk,
            "provider_required": bool(raw.get("provider_required")),
            "language_runtime_required": bool(raw.get("language_runtime_required")),
            "mutation_capable": bool(raw.get("mutation_capable")),
        })
    if not rows:
        raise ValueError("tool_registry_required")
    rows.sort(key=lambda row: row["tool_id"])
    return rows, _digest(rows)


def _normalize_steps(values: Iterable[Mapping[str, Any]], tools: list[Mapping[str, Any]], initial_artifacts: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tool_map = {row["tool_id"]: row for row in tools}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values or []:
        step_id = str(raw.get("step_id") or "").lower()
        tool_id = str(raw.get("tool_id") or "").lower()
        action = str(raw.get("action_code") or "").lower()
        if not _STEP_ID.fullmatch(step_id) or step_id in seen:
            raise ValueError("invalid_or_duplicate_step_id")
        seen.add(step_id)
        ordinal = int(raw.get("ordinal") or 0)
        if ordinal < 1:
            raise ValueError("invalid_step_ordinal")
        depends = sorted({str(value or "").lower() for value in raw.get("depends_on") or []})
        if any(not _STEP_ID.fullmatch(value) for value in depends):
            raise ValueError("invalid_step_dependency")
        consumes = _tokens(raw.get("consumes") or [], "invalid_step_input_type")
        produces = _tokens(raw.get("produces") or [], "invalid_step_output_type")
        rows.append({
            "step_id": step_id,
            "ordinal": ordinal,
            "tool_id": tool_id,
            "action_code": action,
            "depends_on": depends,
            "consumes": consumes,
            "produces": produces,
            "input_contract_digest": _hex(raw.get("input_contract_digest"), "invalid_step_input_contract_digest"),
            "output_contract_digest": _hex(raw.get("output_contract_digest"), "invalid_step_output_contract_digest"),
            "failure_policy": str(raw.get("failure_policy") or "stop_and_review").lower(),
            "retry_policy": str(raw.get("retry_policy") or "no_automatic_retry").lower(),
            "authorization_mode": str(raw.get("authorization_mode") or "fresh_step_authority_required").lower(),
        })
    if not rows:
        raise ValueError("orchestration_steps_required")
    rows.sort(key=lambda row: (row["ordinal"], row["step_id"]))
    issues: list[str] = []
    if [row["ordinal"] for row in rows] != list(range(1, len(rows) + 1)):
        issues.append("non_contiguous_step_order")
    step_map = {row["step_id"]: row for row in rows}
    for row in rows:
        tool = tool_map.get(row["tool_id"])
        if tool is None:
            issues.append(f"missing_tool:{row['step_id']}")
            continue
        if not _TOKEN.fullmatch(row["action_code"]) or row["action_code"] not in tool["capability_codes"]:
            issues.append(f"unsupported_action:{row['step_id']}")
        if row["input_contract_digest"] != tool["input_contract_digest"]:
            issues.append(f"input_contract_mismatch:{row['step_id']}")
        if row["output_contract_digest"] != tool["output_contract_digest"]:
            issues.append(f"output_contract_mismatch:{row['step_id']}")
        if not set(row["consumes"]).issubset(set(tool["consumes"])):
            issues.append(f"tool_input_type_mismatch:{row['step_id']}")
        if not set(row["produces"]).issubset(set(tool["produces"])):
            issues.append(f"tool_output_type_mismatch:{row['step_id']}")
        if row["failure_policy"] != "stop_and_review":
            issues.append(f"unsafe_failure_policy:{row['step_id']}")
        if row["retry_policy"] != "no_automatic_retry":
            issues.append(f"unsafe_retry_policy:{row['step_id']}")
        if row["authorization_mode"] != "fresh_step_authority_required":
            issues.append(f"unsafe_authorization_mode:{row['step_id']}")
        for dep in row["depends_on"]:
            if dep not in step_map:
                issues.append(f"missing_dependency:{row['step_id']}:{dep}")
            elif step_map[dep]["ordinal"] >= row["ordinal"]:
                issues.append(f"forward_or_cyclic_dependency:{row['step_id']}:{dep}")

    available = set(initial_artifacts)
    for row in rows:
        dependency_outputs: set[str] = set(initial_artifacts)
        for dep in row["depends_on"]:
            dependency_outputs.update(step_map.get(dep, {}).get("produces") or [])
        if not set(row["consumes"]).issubset(dependency_outputs):
            issues.append(f"incompatible_handoff:{row['step_id']}")
        available.update(row["produces"])
        row["step_input_binding_digest"] = _digest({
            "step_id": row["step_id"], "tool_id": row["tool_id"], "depends_on": row["depends_on"],
            "consumes": row["consumes"], "input_contract_digest": row["input_contract_digest"],
        })
        row["step_contract_digest"] = _digest(row)

    state = "ready"
    if any(value.startswith("missing_tool") for value in issues):
        state = "missing_tool"
    elif any("cyclic" in value for value in issues):
        state = "cyclic"
    elif issues:
        state = "incompatible"
    return rows, {
        "orchestration_state": state,
        "issue_codes": sorted(set(issues)),
        "step_count": len(rows),
        "tool_count": len({row["tool_id"] for row in rows}),
        "provider_tool_count": sum(bool(tool_map.get(row["tool_id"], {}).get("provider_required")) for row in rows),
        "mutation_capable_step_count": sum(bool(tool_map.get(row["tool_id"], {}).get("mutation_capable")) for row in rows),
    }


def _alignment_basis(assessment_id: str, assessment_digest: str, review_id: str, review_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    assessment = _load_alignment_assessment(str(assessment_id or "").lower(), runtime_root)
    review = _load_alignment_review(str(assessment_id or "").lower(), runtime_root)
    if not assessment.get("ok") or assessment.get("assessment_digest") != str(assessment_digest or "").lower():
        raise ValueError("stale_or_invalid_alignment_assessment")
    if not review.get("ok") or review.get("review_id") != str(review_id or "").lower() or review.get("review_digest") != str(review_digest or "").lower():
        raise ValueError("stale_or_invalid_alignment_review")
    if review.get("disposition") != "accept_alignment":
        raise ValueError("alignment_review_not_accepted")
    return assessment, review


def _quality_basis(assessment_id: str, assessment_digest: str, review_id: str, review_digest: str, project_reference: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not any((assessment_id, assessment_digest, review_id, review_digest)):
        return {}, {}
    if not all((assessment_id, assessment_digest, review_id, review_digest)):
        raise ValueError("incomplete_quality_reference")
    assessment = load_requirement_quality_assessment(str(assessment_id or "").lower(), runtime_root=runtime_root)
    review = load_requirement_quality_assessment_review(str(review_id or "").lower(), runtime_root=runtime_root)
    if not assessment.get("ok") or assessment.get("assessment_digest") != str(assessment_digest or "").lower():
        raise ValueError("stale_or_invalid_quality_assessment")
    if not review.get("ok") or review.get("review_digest") != str(review_digest or "").lower() or review.get("assessment_id") != assessment.get("assessment_id"):
        raise ValueError("stale_or_invalid_quality_review")
    if assessment.get("project_reference") != project_reference or review.get("project_reference") != project_reference:
        raise ValueError("quality_project_mismatch")
    return assessment, review


def _load_record(directory: str, record_id: str, seal_field: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_path(directory, record_id, runtime_root))
    if not row or not _valid(row, seal_field):
        return _failure(f"{directory.replace('_', '-')}-integrity-blocked")
    return row


def load_multi_tool_orchestration_plan(plan_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("multi_tool_orchestration_plans", plan_id, "orchestration_plan_record_digest", runtime_root)


def load_multi_tool_orchestration_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("multi_tool_orchestration_reviews", review_id, "orchestration_review_record_digest", runtime_root)


def load_multi_tool_orchestration_result(result_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("multi_tool_orchestration_results", result_id, "orchestration_result_record_digest", runtime_root)


def load_multi_tool_orchestration_handoff(handoff_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("multi_tool_orchestration_handoffs", handoff_id, "orchestration_handoff_record_digest", runtime_root)


def load_multi_tool_orchestration_handoff_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("multi_tool_orchestration_handoff_reviews", review_id, "orchestration_handoff_review_record_digest", runtime_root)


def prepare_multi_tool_orchestration_plan(
    alignment_assessment_id: str, *, expected_alignment_assessment_digest: str,
    alignment_review_id: str, expected_alignment_review_digest: str,
    tools: Iterable[Mapping[str, Any]], steps: Iterable[Mapping[str, Any]],
    initial_artifact_types: Iterable[str] = (),
    quality_assessment_id: str = "", expected_quality_assessment_digest: str = "",
    quality_review_id: str = "", expected_quality_review_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            alignment, alignment_review = _alignment_basis(
                alignment_assessment_id, expected_alignment_assessment_digest,
                alignment_review_id, expected_alignment_review_digest, runtime_root,
            )
            project_reference = str(alignment.get("project_reference") or "")
            quality, quality_review = _quality_basis(
                quality_assessment_id, expected_quality_assessment_digest,
                quality_review_id, expected_quality_review_digest, project_reference, runtime_root,
            )
            tool_rows, registry_digest = _normalize_tools(tools)
            initial = _tokens(initial_artifact_types, "invalid_initial_artifact_type")
            step_rows, evaluation = _normalize_steps(steps, tool_rows, initial)
            basis = {
                "alignment_assessment_id": alignment["assessment_id"],
                "alignment_assessment_digest": alignment["assessment_digest"],
                "alignment_review_id": alignment_review["review_id"],
                "alignment_review_digest": alignment_review["review_digest"],
                "quality_assessment_id": str(quality.get("assessment_id") or ""),
                "quality_assessment_digest": str(quality.get("assessment_digest") or ""),
                "quality_review_id": str(quality_review.get("review_id") or ""),
                "quality_review_digest": str(quality_review.get("review_digest") or ""),
                "project_reference": project_reference,
                "queue_item_id": alignment.get("queue_item_id"),
                "tool_registry_digest": registry_digest,
                "initial_artifact_types": initial,
                "steps_digest": _digest(step_rows),
            }
            plan_digest = _digest({"basis": basis, "evaluation": evaluation})
            plan_id = f"orchestration_plan_{plan_digest[:24]}"
            path = _path("multi_tool_orchestration_plans", plan_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _valid(existing, "orchestration_plan_record_digest"):
                    raise ValueError("orchestration_plan_tampered")
                return {**existing, "operation_status": "replayed"}
            row = {
                "ok": True,
                "status": "multi_tool_orchestration_ready_for_operator_review",
                "plan_id": plan_id,
                "plan_digest": plan_digest,
                "basis_digest": _digest(basis),
                **basis,
                "quality_evidence_bound": bool(quality),
                "tool_registry": tool_rows,
                "steps": step_rows,
                **evaluation,
                "plan_acceptable": evaluation["orchestration_state"] == "ready",
                "operator_review_phrase": f"Review multi tool orchestration accept_plan for plan {plan_id} digest {plan_digest}.",
                "step_authority_created": False,
                "next_tool_authorized": False,
                **_base(),
            }
            row = _sealed(row, "orchestration_plan_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError, TypeError) as exc:
        return _failure("multi_tool_orchestration_plan_blocked", str(exc))


def _revalidate_plan_basis(plan: Mapping[str, Any], runtime_root=None) -> None:
    alignment, review = _alignment_basis(
        plan.get("alignment_assessment_id", ""), plan.get("alignment_assessment_digest", ""),
        plan.get("alignment_review_id", ""), plan.get("alignment_review_digest", ""), runtime_root,
    )
    quality, quality_review = _quality_basis(
        plan.get("quality_assessment_id", ""), plan.get("quality_assessment_digest", ""),
        plan.get("quality_review_id", ""), plan.get("quality_review_digest", ""),
        str(plan.get("project_reference") or ""), runtime_root,
    )
    basis = {
        "alignment_assessment_id": alignment["assessment_id"],
        "alignment_assessment_digest": alignment["assessment_digest"],
        "alignment_review_id": review["review_id"],
        "alignment_review_digest": review["review_digest"],
        "quality_assessment_id": str(quality.get("assessment_id") or ""),
        "quality_assessment_digest": str(quality.get("assessment_digest") or ""),
        "quality_review_id": str(quality_review.get("review_id") or ""),
        "quality_review_digest": str(quality_review.get("review_digest") or ""),
        "project_reference": str(plan.get("project_reference") or ""),
        "queue_item_id": plan.get("queue_item_id"),
        "tool_registry_digest": plan.get("tool_registry_digest"),
        "initial_artifact_types": plan.get("initial_artifact_types") or [],
        "steps_digest": _digest(plan.get("steps") or []),
    }
    if _digest(basis) != plan.get("basis_digest"):
        raise ValueError("stale_or_tampered_orchestration_basis")


def review_multi_tool_orchestration_plan(plan_id: str, *, expected_plan_digest: str, disposition: str, exact_phrase: str = "", runtime_root=None) -> dict[str, Any]:
    disposition = str(disposition or "").lower()
    if disposition not in PLAN_DISPOSITIONS:
        return _failure("multi_tool_orchestration_review_invalid", "unsupported_disposition")
    try:
        with _lock(runtime_root):
            plan = load_multi_tool_orchestration_plan(str(plan_id or "").lower(), runtime_root=runtime_root)
            if not plan.get("ok") or plan.get("plan_digest") != str(expected_plan_digest or "").lower():
                raise ValueError("stale_or_invalid_orchestration_plan")
            _revalidate_plan_basis(plan, runtime_root)
            if disposition == "accept_plan" and not plan.get("plan_acceptable"):
                raise ValueError("incompatible_plan_cannot_be_accepted")
            identity = {"plan_digest": plan["plan_digest"], "disposition": disposition}
            review_digest = _digest(identity)
            review_id = f"orchestration_review_{review_digest[:24]}"
            existing_path = _path("multi_tool_orchestration_review_indexes", plan["plan_id"], runtime_root)
            index = _read_json(existing_path)
            if index:
                if not _valid(index, "orchestration_review_index_record_digest"):
                    raise ValueError("orchestration_review_index_tampered")
                existing = load_multi_tool_orchestration_review(index["review_id"], runtime_root=runtime_root)
                if existing.get("ok") and existing.get("disposition") == disposition:
                    return {**existing, "operation_status": "replayed"}
                raise ValueError("conflicting_orchestration_review")
            row = {
                "ok": True,
                "status": "multi_tool_orchestration_review_recorded",
                "review_id": review_id,
                "review_digest": review_digest,
                "plan_id": plan["plan_id"],
                "plan_digest": plan["plan_digest"],
                "project_reference": plan["project_reference"],
                "queue_item_id": plan["queue_item_id"],
                "disposition": disposition,
                "plan_interpretation_accepted": disposition == "accept_plan",
                "operator_follow_up_required": disposition in {"hold", "request_changes"},
                "step_authority_created": False,
                "next_tool_authorized": False,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row = _sealed(row, "orchestration_review_record_digest")
            _atomic_json(_path("multi_tool_orchestration_reviews", review_id, runtime_root), row)
            index = _sealed({"plan_id": plan["plan_id"], "review_id": review_id, "review_digest": review_digest}, "orchestration_review_index_record_digest")
            _atomic_json(existing_path, index)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("multi_tool_orchestration_review_blocked", str(exc))


def _accepted_plan_review(plan: Mapping[str, Any], review_id: str, review_digest: str, runtime_root=None) -> dict[str, Any]:
    review = load_multi_tool_orchestration_review(str(review_id or "").lower(), runtime_root=runtime_root)
    if not review.get("ok") or review.get("review_digest") != str(review_digest or "").lower() or review.get("plan_id") != plan.get("plan_id"):
        raise ValueError("stale_or_invalid_orchestration_review")
    if review.get("disposition") != "accept_plan":
        raise ValueError("orchestration_plan_not_accepted")
    return review


def _step_result_index_path(plan_id: str, step_id: str, runtime_root=None) -> Path:
    return _dir("multi_tool_orchestration_result_indexes", runtime_root) / f"{plan_id}--{step_id}.json"


def _results_for_plan(plan_id: str, runtime_root=None) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    root = _dir("multi_tool_orchestration_results", runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json")):
            row = _read_json(path)
            if row and _valid(row, "orchestration_result_record_digest") and row.get("plan_id") == plan_id:
                rows[str(row.get("step_id") or "")] = row
    return rows


def record_multi_tool_orchestration_step_result(
    plan_id: str, *, expected_plan_digest: str, plan_review_id: str, expected_plan_review_digest: str,
    step_id: str, tool_id: str, expected_input_binding_digest: str,
    output_digest: str, evidence_digest: str, outcome: str,
    exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    outcome = str(outcome or "").lower()
    if outcome not in STEP_OUTCOMES:
        return _failure("multi_tool_orchestration_result_invalid", "unsupported_outcome")
    try:
        with _lock(runtime_root):
            plan = load_multi_tool_orchestration_plan(str(plan_id or "").lower(), runtime_root=runtime_root)
            if not plan.get("ok") or plan.get("plan_digest") != str(expected_plan_digest or "").lower():
                raise ValueError("stale_or_invalid_orchestration_plan")
            _revalidate_plan_basis(plan, runtime_root)
            review = _accepted_plan_review(plan, plan_review_id, expected_plan_review_digest, runtime_root)
            step = next((row for row in plan.get("steps") or [] if row.get("step_id") == str(step_id or "").lower()), None)
            if not step or step.get("tool_id") != str(tool_id or "").lower():
                raise ValueError("step_or_tool_mismatch")
            if step.get("step_input_binding_digest") != str(expected_input_binding_digest or "").lower():
                raise ValueError("stale_or_invalid_step_input_binding")
            output = _hex(output_digest, "invalid_output_digest")
            evidence = _hex(evidence_digest, "invalid_evidence_digest")
            prior = _results_for_plan(plan["plan_id"], runtime_root)
            for dep in step.get("depends_on") or []:
                if prior.get(dep, {}).get("outcome") != "completed":
                    raise ValueError("step_dependency_not_completed")
            index_path = _step_result_index_path(plan["plan_id"], step["step_id"], runtime_root)
            existing_index = _read_json(index_path)
            identity = {
                "plan_digest": plan["plan_digest"], "plan_review_digest": review["review_digest"],
                "step_id": step["step_id"], "tool_id": step["tool_id"],
                "input_binding_digest": step["step_input_binding_digest"], "output_digest": output,
                "evidence_digest": evidence, "outcome": outcome,
            }
            result_digest = _digest(identity)
            result_id = f"orchestration_result_{result_digest[:24]}"
            if existing_index:
                if not _valid(existing_index, "orchestration_result_index_record_digest"):
                    raise ValueError("orchestration_result_index_tampered")
                existing = load_multi_tool_orchestration_result(existing_index["result_id"], runtime_root=runtime_root)
                if existing.get("ok") and existing.get("result_digest") == result_digest:
                    return {**existing, "operation_status": "replayed"}
                raise ValueError("conflicting_step_result")
            downstream = [row["step_id"] for row in plan.get("steps") or [] if step["step_id"] in (row.get("depends_on") or [])]
            row = {
                "ok": True,
                "status": "multi_tool_orchestration_step_result_recorded",
                "result_id": result_id,
                "result_digest": result_digest,
                "plan_id": plan["plan_id"], "plan_digest": plan["plan_digest"],
                "plan_review_id": review["review_id"], "plan_review_digest": review["review_digest"],
                "project_reference": plan["project_reference"], "queue_item_id": plan["queue_item_id"],
                "step_id": step["step_id"], "step_ordinal": step["ordinal"], "tool_id": step["tool_id"],
                "step_contract_digest": step["step_contract_digest"],
                "input_binding_digest": step["step_input_binding_digest"],
                "output_digest": output, "evidence_digest": evidence, "outcome": outcome,
                "downstream_step_ids": downstream,
                "failure_route": "prepare_operator_failure_handoff" if outcome != "completed" else "prepare_bounded_handoff",
                "next_handoff_required": bool(downstream) or outcome != "completed",
                "tool_execution_attested_externally": True,
                "tool_executed_by_orchestration": False,
                "next_tool_authorized": False,
                "automatic_continuation_created": False,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row = _sealed(row, "orchestration_result_record_digest")
            _atomic_json(_path("multi_tool_orchestration_results", result_id, runtime_root), row)
            index = _sealed({"plan_id": plan["plan_id"], "step_id": step["step_id"], "result_id": result_id, "result_digest": result_digest}, "orchestration_result_index_record_digest")
            _atomic_json(index_path, index)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("multi_tool_orchestration_result_blocked", str(exc))


def prepare_multi_tool_orchestration_handoff(result_id: str, *, expected_result_digest: str, runtime_root=None) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            result = load_multi_tool_orchestration_result(str(result_id or "").lower(), runtime_root=runtime_root)
            if not result.get("ok") or result.get("result_digest") != str(expected_result_digest or "").lower():
                raise ValueError("stale_or_invalid_orchestration_result")
            plan = load_multi_tool_orchestration_plan(result["plan_id"], runtime_root=runtime_root)
            if not plan.get("ok") or plan.get("plan_digest") != result.get("plan_digest"):
                raise ValueError("stale_or_invalid_orchestration_plan")
            review = _accepted_plan_review(plan, result["plan_review_id"], result["plan_review_digest"], runtime_root)
            results = _results_for_plan(plan["plan_id"], runtime_root)
            eligible: list[str] = []
            blocked: list[str] = []
            if result.get("outcome") == "completed":
                for step in plan.get("steps") or []:
                    if step["step_id"] in results:
                        continue
                    if all(results.get(dep, {}).get("outcome") == "completed" for dep in step.get("depends_on") or []):
                        eligible.append(step["step_id"])
                    else:
                        blocked.append(step["step_id"])
                route = "next_step_review" if eligible else "orchestration_complete_review"
            else:
                blocked = [step["step_id"] for step in plan.get("steps") or [] if step["step_id"] not in results]
                route = "operator_failure_review"
            identity = {
                "result_digest": result["result_digest"], "plan_digest": plan["plan_digest"],
                "review_digest": review["review_digest"], "eligible": eligible, "blocked": blocked, "route": route,
            }
            handoff_digest = _digest(identity)
            handoff_id = f"orchestration_handoff_{handoff_digest[:24]}"
            path = _path("multi_tool_orchestration_handoffs", handoff_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _valid(existing, "orchestration_handoff_record_digest"):
                    raise ValueError("orchestration_handoff_tampered")
                return {**existing, "operation_status": "replayed"}
            row = {
                "ok": True, "status": "multi_tool_orchestration_handoff_ready_for_operator_review",
                "handoff_id": handoff_id, "handoff_digest": handoff_digest,
                "result_id": result["result_id"], "result_digest": result["result_digest"],
                "plan_id": plan["plan_id"], "plan_digest": plan["plan_digest"],
                "plan_review_id": review["review_id"], "plan_review_digest": review["review_digest"],
                "project_reference": plan["project_reference"], "queue_item_id": plan["queue_item_id"],
                "source_step_id": result["step_id"], "source_outcome": result["outcome"],
                "handoff_route": route, "eligible_step_ids": eligible, "blocked_step_ids": blocked,
                "operator_review_phrase": f"Review multi tool orchestration handoff accept_handoff for handoff {handoff_id} digest {handoff_digest}.",
                "fresh_step_authority_required": bool(eligible),
                "next_tool_authorized": False,
                "automatic_continuation_created": False,
                **_base(),
            }
            row = _sealed(row, "orchestration_handoff_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("multi_tool_orchestration_handoff_blocked", str(exc))


def review_multi_tool_orchestration_handoff(handoff_id: str, *, expected_handoff_digest: str, disposition: str, exact_phrase: str = "", runtime_root=None) -> dict[str, Any]:
    disposition = str(disposition or "").lower()
    if disposition not in HANDOFF_DISPOSITIONS:
        return _failure("multi_tool_orchestration_handoff_review_invalid", "unsupported_disposition")
    try:
        with _lock(runtime_root):
            handoff = load_multi_tool_orchestration_handoff(str(handoff_id or "").lower(), runtime_root=runtime_root)
            if not handoff.get("ok") or handoff.get("handoff_digest") != str(expected_handoff_digest or "").lower():
                raise ValueError("stale_or_invalid_orchestration_handoff")
            result = load_multi_tool_orchestration_result(handoff["result_id"], runtime_root=runtime_root)
            if not result.get("ok") or result.get("result_digest") != handoff.get("result_digest"):
                raise ValueError("stale_or_invalid_orchestration_result")
            identity = {"handoff_digest": handoff["handoff_digest"], "disposition": disposition}
            review_digest = _digest(identity)
            review_id = f"orchestration_handoff_review_{review_digest[:24]}"
            index_path = _path("multi_tool_orchestration_handoff_review_indexes", handoff["handoff_id"], runtime_root)
            existing_index = _read_json(index_path)
            if existing_index:
                if not _valid(existing_index, "orchestration_handoff_review_index_record_digest"):
                    raise ValueError("orchestration_handoff_review_index_tampered")
                existing = load_multi_tool_orchestration_handoff_review(existing_index["review_id"], runtime_root=runtime_root)
                if existing.get("ok") and existing.get("disposition") == disposition:
                    return {**existing, "operation_status": "replayed"}
                raise ValueError("conflicting_orchestration_handoff_review")
            row = {
                "ok": True, "status": "multi_tool_orchestration_handoff_review_recorded",
                "review_id": review_id, "review_digest": review_digest,
                "handoff_id": handoff["handoff_id"], "handoff_digest": handoff["handoff_digest"],
                "plan_id": handoff["plan_id"], "plan_digest": handoff["plan_digest"],
                "project_reference": handoff["project_reference"], "queue_item_id": handoff["queue_item_id"],
                "disposition": disposition,
                "handoff_interpretation_accepted": disposition == "accept_handoff",
                "operator_follow_up_required": disposition in {"hold", "request_changes"},
                "next_tool_authorized": False,
                "fresh_step_authority_still_required": bool(handoff.get("eligible_step_ids")),
                "automatic_continuation_created": False,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row = _sealed(row, "orchestration_handoff_review_record_digest")
            _atomic_json(_path("multi_tool_orchestration_handoff_reviews", review_id, runtime_root), row)
            index = _sealed({"handoff_id": handoff["handoff_id"], "review_id": review_id, "review_digest": review_digest}, "orchestration_handoff_review_index_record_digest")
            _atomic_json(index_path, index)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("multi_tool_orchestration_handoff_review_blocked", str(exc))


def _project(row: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys}


_PLAN_PUBLIC = (
    "ok", "status", "plan_id", "plan_digest", "basis_digest", "alignment_assessment_id", "alignment_assessment_digest",
    "alignment_review_id", "alignment_review_digest", "quality_assessment_id", "quality_assessment_digest", "quality_review_id",
    "quality_review_digest", "quality_evidence_bound", "project_reference", "queue_item_id", "tool_registry_digest",
    "initial_artifact_types", "tool_registry", "steps", "orchestration_state", "issue_codes", "step_count", "tool_count",
    "provider_tool_count", "mutation_capable_step_count", "plan_acceptable", "operator_review_phrase", "content_free",
    "project_scoped", "tool_registry_snapshot_read_only", "tool_contracts_digest_bound", "fresh_separate_tool_authority_required",
    "tool_invocation_authorized", "automatic_continuation_authorized", "automatic_retry_authorized", "old_authority_reusable",
)
_REVIEW_PUBLIC = (
    "ok", "status", "review_id", "review_digest", "plan_id", "plan_digest", "project_reference", "queue_item_id",
    "disposition", "plan_interpretation_accepted", "operator_follow_up_required", "step_authority_created", "next_tool_authorized",
    "content_free", "tool_invocation_authorized", "automatic_continuation_authorized", "old_authority_reusable",
)
_RESULT_PUBLIC = (
    "ok", "status", "result_id", "result_digest", "plan_id", "plan_digest", "plan_review_id", "plan_review_digest",
    "project_reference", "queue_item_id", "step_id", "step_ordinal", "tool_id", "step_contract_digest", "input_binding_digest",
    "output_digest", "evidence_digest", "outcome", "downstream_step_ids", "failure_route", "next_handoff_required",
    "tool_execution_attested_externally", "tool_executed_by_orchestration", "next_tool_authorized", "content_free",
    "tool_invocation_authorized", "automatic_continuation_authorized", "automatic_retry_authorized", "old_authority_reusable",
)
_HANDOFF_PUBLIC = (
    "ok", "status", "handoff_id", "handoff_digest", "result_id", "result_digest", "plan_id", "plan_digest",
    "plan_review_id", "plan_review_digest", "project_reference", "queue_item_id", "source_step_id", "source_outcome",
    "handoff_route", "eligible_step_ids", "blocked_step_ids", "operator_review_phrase", "fresh_step_authority_required",
    "next_tool_authorized", "automatic_continuation_created", "content_free", "tool_invocation_authorized", "old_authority_reusable",
)
_HANDOFF_REVIEW_PUBLIC = (
    "ok", "status", "review_id", "review_digest", "handoff_id", "handoff_digest", "plan_id", "plan_digest",
    "project_reference", "queue_item_id", "disposition", "handoff_interpretation_accepted", "operator_follow_up_required",
    "next_tool_authorized", "fresh_step_authority_still_required", "automatic_continuation_created", "content_free",
    "tool_invocation_authorized", "old_authority_reusable",
)


def inspect_multi_tool_orchestration_plan(plan_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_multi_tool_orchestration_plan(str(plan_id or "").lower(), runtime_root=runtime_root)
    return _project(row, _PLAN_PUBLIC) if row.get("ok") else row


def _public_list(directory: str, seal_field: str, keys: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _dir(directory, runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_RECORDS:]:
            row = _read_json(path)
            if row and _valid(row, seal_field):
                rows.append(_project(row, keys))
    return {"ok": True, "status": f"multi_tool_orchestration_{plural}_ready", f"{plural[:-1]}_count": len(rows), plural: rows, **_base()}


def public_multi_tool_orchestration_plans(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("multi_tool_orchestration_plans", "orchestration_plan_record_digest", _PLAN_PUBLIC, "plans", runtime_root)


def public_multi_tool_orchestration_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("multi_tool_orchestration_reviews", "orchestration_review_record_digest", _REVIEW_PUBLIC, "reviews", runtime_root)


def public_multi_tool_orchestration_results(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("multi_tool_orchestration_results", "orchestration_result_record_digest", _RESULT_PUBLIC, "results", runtime_root)


def public_multi_tool_orchestration_handoffs(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("multi_tool_orchestration_handoffs", "orchestration_handoff_record_digest", _HANDOFF_PUBLIC, "handoffs", runtime_root)


def public_multi_tool_orchestration_handoff_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("multi_tool_orchestration_handoff_reviews", "orchestration_handoff_review_record_digest", _HANDOFF_REVIEW_PUBLIC, "handoff_reviews", runtime_root)


def multi_tool_orchestration_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Multi-tool orchestration was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "ready_for_operator_review" in status:
        return "Prepared a content-free multi-tool orchestration record for operator review. No tool or next step was authorized."
    if "review_recorded" in status:
        return "Recorded the exact orchestration review. No tool, command, test, provider, project, launch, resume, or retry authority was created."
    if "step_result_recorded" in status:
        return "Recorded externally supplied step evidence. The orchestration subsystem did not invoke the tool and did not authorize the next step."
    return "Multi-tool orchestration records are ready for inspection."


def process_multi_tool_orchestration_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _REVIEW_PLAN.fullmatch(text)
    if match:
        row = review_multi_tool_orchestration_plan(match.group("plan"), expected_plan_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    match = _RECORD_RESULT.fullmatch(text)
    if match:
        row = record_multi_tool_orchestration_step_result(
            match.group("plan"), expected_plan_digest=match.group("plan_digest"), plan_review_id=match.group("review"),
            expected_plan_review_digest=match.group("review_digest"), step_id=match.group("step"), tool_id=match.group("tool"),
            expected_input_binding_digest=match.group("input"), output_digest=match.group("output"), evidence_digest=match.group("evidence"),
            outcome=match.group("outcome"), exact_phrase=text, runtime_root=runtime_root,
        )
        return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    match = _PREPARE_HANDOFF.fullmatch(text)
    if match:
        row = prepare_multi_tool_orchestration_handoff(match.group("result"), expected_result_digest=match.group("digest"), runtime_root=runtime_root)
        return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    match = _REVIEW_HANDOFF.fullmatch(text)
    if match:
        row = review_multi_tool_orchestration_handoff(match.group("handoff"), expected_handoff_digest=match.group("digest"), disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root)
        return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    match = _SHOW_PLAN.fullmatch(text)
    if match:
        row = inspect_multi_tool_orchestration_plan(match.group("plan"), runtime_root=runtime_root)
        return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    for regex, factory in (
        (_SHOW_PLANS, public_multi_tool_orchestration_plans),
        (_SHOW_REVIEWS, public_multi_tool_orchestration_reviews),
        (_SHOW_RESULTS, public_multi_tool_orchestration_results),
        (_SHOW_HANDOFFS, public_multi_tool_orchestration_handoffs),
        (_SHOW_HANDOFF_REVIEWS, public_multi_tool_orchestration_handoff_reviews),
    ):
        if regex.fullmatch(text):
            row = factory(runtime_root=runtime_root)
            return {"active": True, "response": multi_tool_orchestration_response(row), "multi_tool_orchestration": row}
    return {"active": False}


def build_multi_tool_orchestration_contract() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "multi_tool_orchestration_contract_ready",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Multi-Tool Orchestration",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "exact_accepted_v1236_alignment_binding": True,
        "optional_exact_v1234_quality_binding": True,
        "sealed_content_free_tool_registry": True,
        "ordered_contract_checked_step_graph": True,
        "deterministic_tool_compatibility_evaluation": True,
        "bounded_external_step_result_recording": True,
        "operator_reviewed_handoff_proposals": True,
        "failure_routes_stop_for_operator_review": True,
        "ordinary_chat_exact_controls": True,
        "get_only_api_inspection": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "accepted_plan_does_not_authorize_tools": True,
        "completed_step_does_not_authorize_next_tool": True,
        "accepted_handoff_does_not_authorize_next_tool": True,
        "no_automatic_continuation_or_retry": True,
        "plan_dispositions": sorted(PLAN_DISPOSITIONS),
        "handoff_dispositions": sorted(HANDOFF_DISPOSITIONS),
        "step_outcomes": sorted(STEP_OUTCOMES),
        "orchestration_states": sorted(ORCHESTRATION_STATES),
        **_base(),
    }
