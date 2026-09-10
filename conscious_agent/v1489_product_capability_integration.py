from __future__ import annotations

"""Production adapter for the v1489 planning and development capability bundles.

The bundle modules remain small deterministic contracts. This adapter connects
them to the retained conversation lifecycle without adding a second executor or
granting source, installation, approval, or release authority.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from practical_coding_capability import bounded_implementation_plan, inventory_project
from reasoning_planning_quality_contract import (
    authority_stop,
    build_requirements,
    candidate_approaches,
    epistemic_partition,
    missing_prerequisites,
    score_tradeoff,
)
from supervised_self_development_contract import (
    create_isolated_workspace,
    source_manifest,
)
from dynamic_improvement_discovery import (
    build_dynamic_improvement_discovery,
    public_dynamic_discovery_projection,
)
from dynamic_improvement_eligibility import harden_dynamic_discovery
from dynamic_candidate_quality import compare_dynamic_candidates
from initiative_evidence_intake import build_initiative_evidence_intake
from initiative_evidence_review import (
    is_initiative_evidence_review_control,
    process_initiative_evidence_review_control,
)
from initiative_value_prioritization import (
    build_value_prioritized_initiative_shortlist,
    value_prioritized_initiative_response,
)
from evidence_to_candidate_planner import build_evidence_to_candidate_plans, evidence_to_candidate_response
from operator_development_findings import (
    is_operator_development_finding_command,
    list_operator_development_findings,
    record_operator_development_finding,
)
from product_plan_lifecycle import process_product_plan_control, register_product_candidate_plan
from supervised_repair_intelligence import (
    advance_repair_cycle,
    build_bounded_repair_plan,
    build_failure_receipt,
)
from supervised_initiative_campaign import (
    bind_shortlist_selection,
    create_or_reuse_campaign,
    current_active_campaign_candidate,
    is_campaign_control,
    process_campaign_control,
    record_campaign_candidate_state,
    select_next_campaign_candidate,
)
from supervised_initiative_queue import (
    build_supervised_initiative_shortlist,
    control_supervised_initiative,
    inspect_supervised_initiative_queue,
    process_supervised_initiative_control,
    queue_supervised_initiative,
    reconcile_supervised_initiative_queue,
    supervised_initiative_response,
    update_supervised_initiative_lifecycle,
)
from development_authority import issue_operator_authorization
from supervised_development_coordinator import record_review_ready, record_workspace_prepared, start_selected_campaign
from supervised_candidate_installation import install_reviewed_candidate, review_isolated_candidate
from supervised_development_continuation import is_supervised_development_continuation
from v1489_generic_self_development_execution import (
    GenericSelfDevelopmentError,
    execute_generic_isolated_proposal,
)


_SELF_INSPECTION = re.compile(
    r"\b(?:inspect|review|analy[sz]e|assess)\b.{0,80}"
    r"\b(?:your|eidolon(?:'s)?)\b.{0,40}\b(?:project|source|code|development)\b"
    r"|\b(?:propose|identify|suggest)\b.{0,60}\b(?:your|eidolon(?:'s)?)\b"
    r".{0,40}\b(?:next|improvement|development)\b",
    re.IGNORECASE,
)


def _dynamic_candidate_family_name(candidate: Mapping[str, Any]) -> str:
    symbols = [
        str(value).strip("_").replace("_", " ")
        for value in candidate.get("source_symbols") or ()
        if str(value)
    ]
    if not symbols:
        return Path(str(candidate.get("source_module") or "helpers.py")).stem.replace("_", " ")
    common = set(symbols[0].split())
    for symbol in symbols[1:]:
        common &= set(symbol.split())
    useful = sorted(
        word
        for word in common
        if len(word) > 3 and word not in {"build", "create", "public", "inspect"}
    )
    return " ".join(useful[:3]) or Path(str(candidate.get("source_module") or "helpers.py")).stem.replace("_", " ")


def _dynamic_candidate_review_handoff(
    top: Mapping[str, Any],
    hardening: Mapping[str, Any],
) -> str:
    """Explain ranked structural evidence without turning ranking into authority."""
    candidate_id = str(top.get("candidate_id") or "")
    candidate = next(
        (
            dict(row)
            for row in hardening.get("eligible_candidates") or ()
            if str(row.get("candidate_id") or "") == candidate_id
        ),
        dict(top),
    )
    source_module = str(candidate.get("source_module") or top.get("source_module") or "unknown")
    destination_module = str(
        candidate.get("proposed_destination_module")
        or top.get("proposed_destination_module")
        or "unknown"
    )
    symbol_count = len(candidate.get("source_symbols") or ()) or int(top.get("source_symbol_count") or 0)
    test_file_count = int(candidate.get("test_reference_file_count") or 0)
    dependency_count = int(candidate.get("estimated_dependency_count") or 0)
    family = _dynamic_candidate_family_name(candidate)
    title = f"Separate {family} helpers"
    digest = str(top.get("evidence_digest") or candidate.get("evidence_digest") or "")[:16]
    return (
        f"\n\nHighest-value current candidate: {title} ({candidate_id}, quality score {top.get('quality_score')}).\n"
        f"Why it matters: {symbol_count} related helpers are still concentrated in {source_module}. Moving that cohesive family "
        f"behind compatible imports should reduce maintenance and regression risk. The evidence includes {test_file_count} attributable "
        f"test file{'s' if test_file_count != 1 else ''} and {dependency_count} estimated dependenc{'ies' if dependency_count != 1 else 'y'}.\n"
        f"Affected files: {source_module}; {destination_module}.\n"
        f"Verification plan: run the attributable focused tests, compile both modules, exercise retained imports, and verify source "
        f"immutability and privacy boundaries.\n"
        "Authority still needed: this inspection changed nothing. Your next phrase authorizes only creation of the supervised proposal; "
        "workspace preparation, isolated implementation, review, installation, and promotion remain separate decisions.\n"
        f"Next phrase: Create dynamic self-development proposal {candidate_id} evidence {digest}."
    )
_PREPARE_SELF_PROPOSAL = re.compile(
    r"Prepare isolated self-development proposal (?P<proposal_id>improvement-[a-f0-9]{20}) "
    r"digest (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_IMPLEMENT_SELF_PROPOSAL = re.compile(
    r"Implement isolated self-development proposal (?P<proposal_id>improvement-[a-f0-9]{20}) "
    r"digest (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_REVIEW_SELF_CANDIDATE = re.compile(
    r"Review (?:self-development )?candidate (?P<proposal_id>improvement-[a-f0-9]{20})[.!?]*$",
    re.IGNORECASE,
)
_INSTALL_REVIEWED_CANDIDATE = re.compile(
    r"Install reviewed candidate (?P<proposal_id>improvement-[a-f0-9]{20}) "
    r"review (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_REVIEW_AND_INSTALL_CANDIDATE = re.compile(
    r"Review and install (?:self-development )?candidate "
    r"(?P<proposal_id>improvement-[a-f0-9]{20})[.!?]*$",
    re.IGNORECASE,
)
_CREATE_DYNAMIC_PROPOSAL = re.compile(
    r"Create dynamic self-development proposal (?P<candidate_id>discovery-[a-f0-9]{20}) "
    r"evidence (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_SELF_DEVELOPMENT_FAILURE_QUESTION = re.compile(
    r"^\s*(?:what happened|why did (?:that|it|the (?:implementation|proposal)) fail|"
    r"what (?:went wrong|failed))(?:\s+with (?:that|it))?[.!?]*\s*$",
    re.IGNORECASE,
)
_SELF_DEVELOPMENT_FAILURE_FOLLOWUP = re.compile(
    r"^\s*(?:explain (?:that )?(?:further|more)|tell me (?:the )?command (?:you )?(?:need|want)|"
    r"what command (?:do you need|should i use)|how (?:do|can) i retry)(?:\s+that)?[.!?]*\s*$",
    re.IGNORECASE,
)

_HELPER_IMPORT = """from self_maintenance_helpers import (\n    _json_print,\n    _read_json,\n    _read_text,\n    _report_path,\n    _sha256_file,\n    _sha256_text,\n)\n"""
_HELPER_DEFINITIONS = (
    """def _read_text(path: Path) -> str:\n    return path.read_text(encoding=\"utf-8\", errors=\"replace\") if path.exists() else \"\"\n\n""",
    """def _read_json(path: Path, default: Any) -> Any:\n    try:\n        return json.loads(path.read_text(encoding=\"utf-8\"))\n    except (OSError, json.JSONDecodeError):\n        return default\n\n""",
    """def _sha256_text(value: Any) -> str:\n    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode(\"utf-8\")).hexdigest()\n\n""",
    """def _sha256_file(path: Path) -> str:\n    h = hashlib.sha256()\n    with path.open(\"rb\") as handle:\n        for chunk in iter(lambda: handle.read(1024 * 1024), b\"\"):\n            h.update(chunk)\n    return h.hexdigest()\n\n""",
    """def _json_print(value: Any) -> None:\n    print(json.dumps(value, indent=2, default=str))\n\n""",
    """def _report_path(path: str) -> str:\n    return path.replace(os.sep, \"/\")\n\n""",
)
_HELPER_MODULE = '''from __future__ import annotations

"""Shared file and digest helpers extracted from the maintenance runtime."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _report_path(path: str) -> str:
    return path.replace(os.sep, "/")
'''
_TASK_QUEUE_IMPORT = """from self_maintenance_task_queue import (\n    _queue_sort_key,\n    _score_maintenance_goal_components,\n    _select_next_maintenance_task,\n)\n"""
_TASK_SCORE_DEFINITION = '''def _score_maintenance_goal(goal: str | None = None, files: list[str] | None = None) -> dict[str, Any]:
    text = _autonomy_goal(goal).lower()
    selected = files or _select_autonomy_targets(text)
    priority = 40
    risk = 20
    reasons: list[str] = []
    if any(token in text for token in ("safety", "privacy", "source-only", "package", "release")):
        priority += 25; risk += 20; reasons.append("release/privacy boundary")
    if any(token in text for token in ("dashboard", "api", "queue", "visibility")):
        priority += 18; risk += 15; reasons.append("operator surface")
    if any(token in text for token in ("performance", "slow", "cache", "render")):
        priority += 15; risk += 10; reasons.append("operator performance")
    if any(token in text for token in ("apply", "rollback", "approval", "destructive", "live")):
        priority += 5; risk += 35; reasons.append("mutation boundary")
    if "conscious_agent/self_maintenance.py" in selected:
        risk += 10
    if any(path.startswith("data/") for path in selected):
        risk += 30; reasons.append("runtime data touch")
    priority = min(100, max(0, priority))
    risk = min(100, max(0, risk))
    risk_level = "high" if risk >= 70 else "medium" if risk >= 35 else "low"
    return {"priority_score": priority, "risk_score": risk, "risk_level": risk_level, "reasons": reasons or ["bounded maintenance goal"], "planned_files": selected}


'''
_TASK_SELECTION_DEFINITIONS = '''def _queue_sort_key(task: dict[str, Any]) -> tuple[int, int, str]:
    return (-int(task.get("priority_score") or 0), int(task.get("risk_score") or 0), str(task.get("task_id", "")))


def _select_next_maintenance_task(tasks: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    active = [task for task in tasks if str(task.get("state")) in {"selected", "cycle_running", "checkpoint_required", "apply_handoff_ready"}]
    candidates = sorted([task for task in tasks if str(task.get("state", "queued")) in {"queued", "blocked"}], key=_queue_sort_key)
    return (None if active else (candidates[0] if candidates else None)), active, candidates


'''
_TASK_QUEUE_MODULE = '''from __future__ import annotations

"""Scoring and selection helpers for the supervised maintenance task queue."""

from typing import Any


def _score_maintenance_goal_components(text: str, selected: list[str]) -> dict[str, Any]:
    priority = 40
    risk = 20
    reasons: list[str] = []
    if any(token in text for token in ("safety", "privacy", "source-only", "package", "release")):
        priority += 25
        risk += 20
        reasons.append("release/privacy boundary")
    if any(token in text for token in ("dashboard", "api", "queue", "visibility")):
        priority += 18
        risk += 15
        reasons.append("operator surface")
    if any(token in text for token in ("performance", "slow", "cache", "render")):
        priority += 15
        risk += 10
        reasons.append("operator performance")
    if any(token in text for token in ("apply", "rollback", "approval", "destructive", "live")):
        priority += 5
        risk += 35
        reasons.append("mutation boundary")
    if "conscious_agent/self_maintenance.py" in selected:
        risk += 10
    if any(path.startswith("data/") for path in selected):
        risk += 30
        reasons.append("runtime data touch")
    priority = min(100, max(0, priority))
    risk = min(100, max(0, risk))
    risk_level = "high" if risk >= 70 else "medium" if risk >= 35 else "low"
    return {
        "priority_score": priority,
        "risk_score": risk,
        "risk_level": risk_level,
        "reasons": reasons or ["bounded maintenance goal"],
        "planned_files": selected,
    }


def _queue_sort_key(task: dict[str, Any]) -> tuple[int, int, str]:
    return (-int(task.get("priority_score") or 0), int(task.get("risk_score") or 0), str(task.get("task_id", "")))


def _select_next_maintenance_task(
    tasks: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    active = [
        task
        for task in tasks
        if str(task.get("state")) in {"selected", "cycle_running", "checkpoint_required", "apply_handoff_ready"}
    ]
    candidates = sorted(
        [task for task in tasks if str(task.get("state", "queued")) in {"queued", "blocked"}],
        key=_queue_sort_key,
    )
    return (None if active else (candidates[0] if candidates else None)), active, candidates
'''


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _runtime_root() -> Path:
    override = os.environ.get("EIDOLON_DATA_DIR")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parents[1] / "data"


def _proposal_path(proposal_id: str) -> Path:
    return _runtime_root() / "self_development_proposals" / f"{proposal_id}.json"


def _implementation_phrase(proposal: Mapping[str, Any]) -> str:
    return (
        f"Implement isolated self-development proposal {proposal.get('proposal_id')} "
        f"digest {str(proposal.get('proposal_digest') or '')[:16]}."
    )


def _python_module_evidence(source_root: Path) -> dict[str, Any]:
    modules: list[tuple[int, Path]] = []
    agent_root = source_root / "conscious_agent"
    for path in agent_root.glob("*.py"):
        if path.is_file():
            modules.append((path.stat().st_size, path))
    if not modules:
        raise ValueError("self_development_python_inventory_empty")
    modules.sort(key=lambda row: (-row[0], row[1].name.casefold()))
    size, target = modules[0]
    data = target.read_bytes()
    relative = target.relative_to(source_root).as_posix()
    return {
        "python_module_count": len(modules),
        "target_relative_path": relative,
        "target_size_bytes": size,
        "target_line_count": data.count(b"\n") + (1 if data else 0),
        "target_top_level_function_count": data.count(b"\ndef ") + (1 if data.startswith(b"def ") else 0),
        "target_digest": hashlib.sha256(data).hexdigest(),
        "evidence_class": "largest_python_module_by_bytes",
        "content_free": True,
    }


def _installed_proposal_history() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    directory = _runtime_root() / "self_development_proposals"
    for path in sorted(directory.glob("improvement-*.json")):
        proposal = load_json_file(path, {}, expected_type=dict)
        if proposal.get("state") != "operator_installed":
            continue
        result = dict(proposal.get("implementation_result") or {})
        changed_files = [str(value).replace("\\", "/") for value in result.get("changed_files") or []]
        source_symbols = [
            str(value)
            for value in (
                proposal.get("source_symbols")
                or proposal.get("selected_symbols")
                or result.get("source_symbols")
                or result.get("selected_symbols")
                or []
            )
            if value
        ]
        destination_module = str(
            proposal.get("destination_module")
            or (proposal.get("development_plan") or {}).get("destination_module")
            or result.get("destination_module")
            or next((value for value in changed_files if value.startswith("conscious_agent/") and value.endswith(".py") and value != "conscious_agent/self_maintenance.py"), "")
        ).replace("\\", "/")
        rows.append(
            {
                "proposal_id": proposal.get("proposal_id"),
                "proposal_digest": proposal.get("proposal_digest"),
                "evidence_digest": proposal.get("evidence_digest"),
                "improvement_class": proposal.get("improvement_class"),
                "proposed_change": proposal.get("proposed_change"),
                "implementation_result_digest": proposal.get("implementation_result_digest"),
                "changed_file_count": result.get("changed_file_count", 0),
                "changed_files": changed_files,
                "source_symbols": source_symbols,
                "destination_module": destination_module,
                "checks_passed": result.get("checks_passed") is True,
                "installed_at": proposal.get("installed_at"),
                "operator_installed": True,
                "content_free": True,
            }
        )
    return sorted(
        rows,
        key=lambda row: (str(row.get("installed_at") or ""), str(row.get("proposal_id") or "")),
    )


def _next_improvement_spec(installed: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    completed = {str(row.get("improvement_class") or "") for row in installed}
    choices = [
        {
            "improvement_class": "bounded_maintainability_extraction",
            "proposed_change": "Extract one cohesive helper family behind retained imports.",
            "expected_benefit": "Reduce review and regression risk without changing public behavior.",
            "new_module": "one new helper module",
        },
        {
            "improvement_class": "maintenance_task_queue_boundary_extraction",
            "proposed_change": "Extract the maintenance task queue scoring and selection family behind retained imports.",
            "expected_benefit": "Separate task prioritization from the maintenance command surface and make queue behavior independently testable.",
            "new_module": "conscious_agent/self_maintenance_task_queue.py",
        },
        {
            "improvement_class": "approval_record_boundary_extraction",
            "proposed_change": "Extract approval-record discovery and validation helpers behind retained imports.",
            "expected_benefit": "Reduce coupling in approval review while preserving operator authority and existing record formats.",
            "new_module": "conscious_agent/self_maintenance_approval_records.py",
        },
        {
            "improvement_class": "approval_revocation_boundary_extraction",
            "proposed_change": "Extract approval-revocation lookup and validation helpers behind retained imports.",
            "expected_benefit": "Separate revocation discovery and binding checks while preserving approval authority and record behavior.",
            "new_module": "conscious_agent/self_maintenance_approval_revocations.py",
        },
    ]
    return next((row for row in choices if row["improvement_class"] not in completed), None)


def _load_or_create_concrete_proposal(source_root: Path) -> dict[str, Any]:
    evidence = _python_module_evidence(source_root)
    installed = _installed_proposal_history()
    specification = _next_improvement_spec(installed)
    if specification is None:
        return {
            "state": "no_distinct_improvement_available",
            "operation_status": "not_created",
            "evidence": evidence,
            "completed_predecessor_count": len(installed),
            "completed_predecessors": installed,
            "content_free": True,
            "source_modified": False,
            "installation_authorized": False,
            "promotion_authorized": False,
        }
    issue_digest = _digest(
        {
            "evidence_class": evidence["evidence_class"],
            "target_relative_path": evidence["target_relative_path"],
            "target_digest": evidence["target_digest"],
            "improvement_class": specification["improvement_class"],
            "completed_proposal_digests": [row.get("implementation_result_digest") for row in installed],
        }
    )
    proposal_id = f"improvement-{issue_digest[:20]}"
    path = _proposal_path(proposal_id)
    with metadata_mutation_lock(path, timeout_seconds=5):
        existing = load_json_file(path, {}, expected_type=dict)
        if existing and existing.get("issue_digest") == issue_digest:
            refreshed = dict(existing)
            refreshed["completed_predecessor_count"] = len(installed)
            refreshed["completed_predecessors"] = installed
            if refreshed != existing:
                write_json_atomic(path, refreshed, expected_type=dict, sort_keys=True, coordinate=False)
                return {**refreshed, "operation_status": "synchronized"}
            return {**existing, "operation_status": "restored"}
        base = {
            "schema_version": "1",
            "contract_version": "v1489-trial7",
            "proposal_id": proposal_id,
            "state": "awaiting_operator_isolated_preparation",
            "issue_digest": issue_digest,
            "evidence_digest": _digest(evidence),
            "evidence": evidence,
            "improvement_class": specification["improvement_class"],
            "proposed_change": specification["proposed_change"],
            "expected_benefit": specification["expected_benefit"],
            "affected_scope": [evidence["target_relative_path"], specification["new_module"], "focused tests"],
            "completed_predecessor_count": len(installed),
            "completed_predecessors": installed,
            "verification_commands": [
                "python tools/verification_compile.py --json",
                "python tools/v1489_product_capability_integration_tests.py",
                "focused self-maintenance tests selected after helper boundary inspection",
                "source immutability and privacy verification",
            ],
            "operator_review_required": True,
            "isolated_preparation_authorized": False,
            "isolated_workspace_created": False,
            "provider_contacted": False,
            "tests_executed": False,
            "source_modified": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "content_free": True,
        }
        proposal_digest = _digest(base)
        base["proposal_digest"] = proposal_digest
        base["isolated_preparation_phrase"] = (
            f"Prepare isolated self-development proposal {proposal_id} digest {proposal_digest[:16]}."
        )
        write_json_atomic(path, base, expected_type=dict, sort_keys=True, coordinate=False)
        return {**base, "operation_status": "created"}


def _create_dynamic_proposal(
    control: re.Match[str],
    source_root: Path,
    *,
    operator_authorization_text: str = "",
) -> dict[str, Any]:
    """Persist one operator-selected dynamic candidate as a supervised proposal."""
    candidate_id = control.group("candidate_id").lower()
    supplied_digest = control.group("digest").lower()
    installed = _installed_proposal_history()
    discovery = build_dynamic_improvement_discovery(source_root, completed_lineages=installed)
    hardening = harden_dynamic_discovery(discovery, completed_lineages=installed)
    comparison = compare_dynamic_candidates(hardening)
    candidate = next((dict(row) for row in hardening.get("eligible_candidates") or () if str(row.get("candidate_id") or "").lower() == candidate_id), None)
    if not candidate:
        return {"active": True, "event": "dynamic_self_development_candidate_not_eligible", "conversation_response": "That dynamic candidate is not currently eligible under the latest source evidence. I stopped without creating a proposal or workspace.", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False}
    evidence_digest = str(candidate.get("evidence_digest") or "")
    if supplied_digest != evidence_digest[:16].lower():
        return {"active": True, "event": "dynamic_self_development_candidate_digest_mismatch", "conversation_response": "That candidate evidence digest does not match the current discovery evidence. I stopped without creating a proposal or workspace.", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False}
    issue_digest = _digest({
        "candidate_id": candidate_id,
        "evidence_digest": evidence_digest,
        "eligibility_digest": candidate.get("eligibility_digest"),
        "comparison_digest": comparison.get("comparison_digest"),
        "inventory_digest": discovery.get("inventory_digest"),
        "completed_lineages": [row.get("implementation_result_digest") for row in installed],
    })
    proposal_id = f"improvement-{issue_digest[:20]}"
    path = _proposal_path(proposal_id)
    with metadata_mutation_lock(path, timeout_seconds=5):
        existing = load_json_file(path, {}, expected_type=dict)
        if existing and existing.get("issue_digest") == issue_digest:
            return {"active": True, "event": "dynamic_self_development_proposal_reused", "conversation_response": f"Dynamic proposal {proposal_id} already exists with the same evidence. No duplicate proposal or workspace was created. To prepare its isolated workspace, say exactly: {existing.get('isolated_preparation_phrase')}", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False, "self_development_proposal": existing}
    selection_phrase = f"Create dynamic self-development proposal {candidate_id} evidence {evidence_digest[:16]}."
    authorized_text = operator_authorization_text or selection_phrase
    selection_receipt = issue_operator_authorization(
        stage="candidate_selection",
        subject_id=candidate_id,
        subject_digest=str(candidate.get("eligibility_digest") or evidence_digest),
        explicit_operator_text=authorized_text,
        expected_operator_text=authorized_text,
    )
    campaign = start_selected_campaign(
        _runtime_root(),
        event_id=issue_digest[:32],
        comparison=comparison,
        candidate=candidate,
        baseline_source_digest=str(discovery.get("inventory_digest") or ""),
        operator_selection_receipt=selection_receipt,
        available_test_files=(
            "tools/v1489_product_capability_integration_tests.py",
            "tools/v1489_generic_self_development_execution_tests.py",
            "tools/v1489_symbol_level_refactoring_tests.py",
        ),
    )
    if not campaign.get("ok"):
        return {"active": True, "event": "dynamic_self_development_campaign_blocked", "conversation_response": "The candidate evidence could not enter the sealed supervised-development campaign. I stopped without creating a proposal or workspace.", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False, "campaign_status": campaign.get("status")}
    with metadata_mutation_lock(path, timeout_seconds=5):
        existing = load_json_file(path, {}, expected_type=dict)
        if existing and existing.get("issue_digest") == issue_digest:
            return {"active": True, "event": "dynamic_self_development_proposal_reused", "conversation_response": f"Dynamic proposal {proposal_id} already exists with the same evidence. No duplicate proposal or workspace was created. To prepare its isolated workspace, say exactly: {existing.get('isolated_preparation_phrase')}", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False, "self_development_proposal": existing}
        symbols = [str(x) for x in candidate.get("source_symbols") or ()]
        base = {
            "schema_version": "1",
            "contract_version": "v1500-supervised-dynamic-development",
            "proposal_id": proposal_id,
            "state": "awaiting_operator_isolated_preparation",
            "issue_digest": issue_digest,
            "evidence_digest": evidence_digest,
            "eligibility_digest": candidate.get("eligibility_digest"),
            "comparison_digest": comparison.get("comparison_digest"),
            "dynamic_candidate_id": candidate_id,
            "improvement_class": "dynamic_symbol_refactoring",
            "proposed_change": "Extract the exact dynamically discovered symbol family " + ", ".join(symbols) + " behind retained wrappers/imports.",
            "expected_benefit": "Reduce bounded source coupling using current attributable structural and test evidence.",
            "affected_scope": [candidate.get("source_module"), candidate.get("proposed_destination_module")],
            "source_symbols": symbols,
            "estimated_dependency_count": candidate.get("estimated_dependency_count"),
            "test_reference_file_count": candidate.get("test_reference_file_count"),
            "reversibility_classification": candidate.get("reversibility_classification"),
            "operator_review_required": True,
            "operator_selection_authorization": selection_receipt,
            "development_plan": campaign.get("plan"),
            "development_plan_digest": (campaign.get("plan") or {}).get("plan_digest"),
            "development_campaign": campaign.get("campaign"),
            "isolated_preparation_authorized": False,
            "isolated_workspace_created": False,
            "provider_contacted": False,
            "tests_executed": False,
            "source_modified": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "content_free": True,
        }
        proposal_digest = _digest(base)
        base["proposal_digest"] = proposal_digest
        base["isolated_preparation_phrase"] = f"Prepare isolated self-development proposal {proposal_id} digest {proposal_digest[:16]}."
        write_json_atomic(path, base, expected_type=dict, sort_keys=True, coordinate=False)
    return {"active": True, "event": "dynamic_self_development_proposal_created", "conversation_response": f"I created supervised proposal {proposal_id} from the exact dynamic candidate evidence. I did not prepare a workspace, contact a provider, or modify source. To prepare its isolated workspace, say exactly: {base['isolated_preparation_phrase']}", "provider_contacted": False, "runtime_mutated": True, "source_modified": False, "authority_granted": False, "self_development_proposal": base}


def _prepare_isolated_proposal(
    control: re.Match[str],
    source_root: Path,
    *,
    operator_authorization_text: str = "",
) -> dict[str, Any]:
    proposal_id = control.group("proposal_id").lower()
    supplied_digest = control.group("digest").lower()
    path = _proposal_path(proposal_id)
    with metadata_mutation_lock(path, timeout_seconds=30):
        proposal = load_json_file(path, {}, expected_type=dict)
        if not proposal:
            return {"active": True, "event": "self_development_proposal_not_found", "conversation_response": "I could not find that self-development proposal. No workspace or source was changed.", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False}
        expected = str(proposal.get("proposal_digest") or "")[:16]
        if supplied_digest != expected:
            return {"active": True, "event": "self_development_proposal_digest_mismatch", "conversation_response": "That authorization digest does not match the stored proposal. I stopped without creating a workspace or changing source.", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False}
        workspace = _runtime_root() / "self_development_proposals" / "workspaces" / proposal_id / "Eidolon"
        if proposal.get("state") == "isolated_implementation_blocked" and proposal.get("isolated_workspace_created"):
            repair_plan = build_bounded_repair_plan(proposal)
            repair_advance = advance_repair_cycle(proposal)
            if not repair_advance.get("ok"):
                blocked = dict(proposal)
                blocked["bounded_repair_plan"] = repair_plan
                return {
                    "active": True,
                    "event": "isolated_self_development_repair_blocked",
                    "conversation_response": (
                        f"The bounded repair policy stopped proposal {proposal_id}: {repair_plan.get('next_action')}. "
                        "Active source is unchanged and no installation or promotion was authorized."
                    ),
                    "provider_contacted": False,
                    "runtime_mutated": False,
                    "source_modified": False,
                    "authority_granted": False,
                    "self_development_proposal": blocked,
                }
            current_source = source_manifest(source_root)
            current_workspace = source_manifest(workspace)
            source_is_stale = _digest(current_source) != proposal.get("source_manifest_digest")
            workspace_is_clean = _digest(current_workspace) == proposal.get("workspace_manifest_digest")
            if source_is_stale or not workspace_is_clean:
                workspace_parent = workspace.parent.resolve()
                expected_parent = (_runtime_root() / "self_development_proposals" / "workspaces" / proposal_id).resolve()
                if workspace_parent != expected_parent:
                    raise RuntimeError("isolated_self_development_workspace_boundary_rejected")
                archive = workspace_parent / f"Eidolon.stale-{str(proposal.get('source_manifest_digest') or '')[:8]}"
                if archive.exists():
                    raise RuntimeError("isolated_self_development_stale_archive_exists")
                os.replace(workspace, archive)
                try:
                    created = create_isolated_workspace(source_root, workspace, authorized=True)
                    copied = source_manifest(workspace)
                    if not created.get("created") or copied != current_source:
                        raise RuntimeError("isolated_self_development_refresh_verification_failed")
                except Exception:
                    if workspace.exists():
                        os.replace(workspace, workspace_parent / "Eidolon.failed-refresh")
                    os.replace(archive, workspace)
                    raise
                refreshed = dict(proposal)
                for key in (
                    "implementation_blocker", "implementation_failure_codes", "provider_request_count",
                    "implementation_result", "implementation_result_digest",
                ):
                    refreshed.pop(key, None)
                refreshed.update(
                    {
                        "state": "isolated_workspace_prepared",
                        "workspace_digest": created["workspace_digest"],
                        "workspace_manifest_digest": _digest(copied),
                        "source_manifest_digest": _digest(current_source),
                        "provider_contacted": False,
                        "tests_executed": False,
                        "source_modified": False,
                        **{key: value for key, value in repair_advance.items() if key.startswith("repair_")},
                        "bounded_repair_plan": repair_plan,
                    }
                )
                write_json_atomic(path, refreshed, expected_type=dict, sort_keys=True, coordinate=False)
                return {
                    "active": True,
                    "event": "isolated_self_development_preparation_refreshed",
                    "conversation_response": f"I refreshed the failed proposal's disposable workspace from current source and preserved the same bounded authorization. Active source is unchanged. To retry implementation, say exactly: {_implementation_phrase(refreshed)}",
                    "provider_contacted": False,
                    "runtime_mutated": True,
                    "source_modified": False,
                    "authority_granted": False,
                    "self_development_proposal": refreshed,
                }
        if proposal.get("state") == "isolated_implementation_blocked" and proposal.get("isolated_workspace_created"):
            # The failed executor restores its disposable workspace to the verified
            # baseline. Re-arm that same workspace under the original proposal
            # lineage and bounded repair budget instead of dead-ending continuation.
            repaired = dict(proposal)
            for key in (
                "implementation_blocker", "implementation_failure_codes", "implementation_failure_receipt",
                "implementation_result", "implementation_result_digest",
            ):
                repaired.pop(key, None)
            repaired.update({
                "state": "isolated_workspace_prepared",
                "provider_contacted": False,
                "tests_executed": False,
                "source_modified": False,
                **{key: value for key, value in repair_advance.items() if key.startswith("repair_")},
                "bounded_repair_plan": repair_plan,
            })
            write_json_atomic(path, repaired, expected_type=dict, sort_keys=True, coordinate=False)
            return {
                "active": True,
                "event": "isolated_self_development_repair_prepared",
                "conversation_response": (
                    f"I re-armed the same disposable workspace for bounded repair cycle {repaired.get('repair_cycle_count')} "
                    f"of {repair_plan.get('maximum_repair_cycles')}. Proposal identity and affected scope are unchanged. "
                    f"Active source is unchanged. To retry, say exactly: {_implementation_phrase(repaired)}"
                ),
                "provider_contacted": False,
                "runtime_mutated": True,
                "source_modified": False,
                "authority_granted": False,
                "self_development_proposal": repaired,
            }
        if proposal.get("isolated_workspace_created"):
            return {"active": True, "event": "isolated_self_development_preparation_replayed", "conversation_response": f"Isolated preparation for proposal {proposal_id} was already completed. I reused the same preparation and did not create a duplicate or modify active source. To implement only inside that workspace, say exactly: {_implementation_phrase(proposal)}", "provider_contacted": False, "runtime_mutated": False, "source_modified": False, "authority_granted": False, "self_development_proposal": proposal}
        baseline = source_manifest(source_root)
        created = create_isolated_workspace(source_root, workspace, authorized=True)
        copied = source_manifest(workspace)
        current = source_manifest(source_root)
        if not created.get("created") or copied != baseline or current != baseline:
            raise RuntimeError("isolated_self_development_preparation_verification_failed")
        updated = dict(proposal)
        updated.update(
            {
                "state": "isolated_workspace_prepared",
                "isolated_preparation_authorized": True,
                "isolated_workspace_created": True,
                "workspace_digest": created["workspace_digest"],
                "workspace_manifest_digest": _digest(copied),
                "source_manifest_digest": _digest(baseline),
                "isolated_implementation_phrase": _implementation_phrase(proposal),
                "source_modified": False,
            }
        )
        if proposal.get("dynamic_candidate_id") and proposal.get("development_plan_digest"):
            preparation_phrase = f"Prepare isolated self-development proposal {proposal_id} digest {proposal.get('proposal_digest', '')[:16]}."
            authorized_text = operator_authorization_text or preparation_phrase
            preparation_receipt = issue_operator_authorization(
                stage="workspace_preparation",
                subject_id=str(proposal.get("dynamic_candidate_id")),
                subject_digest=str(proposal.get("development_plan_digest")),
                explicit_operator_text=authorized_text,
                expected_operator_text=authorized_text,
            )
            coordinated = record_workspace_prepared(
                _runtime_root(),
                event_id=str(proposal.get("issue_digest") or proposal_id)[:32],
                candidate_id=str(proposal.get("dynamic_candidate_id")),
                plan_digest=str(proposal.get("development_plan_digest")),
                workspace_manifest_digest=str(updated.get("workspace_manifest_digest")),
                operator_authorization_receipt=preparation_receipt,
            )
            if not coordinated.get("ok"):
                raise RuntimeError("supervised_development_workspace_coordination_failed")
            updated["workspace_preparation_authorization"] = preparation_receipt
            updated["development_campaign"] = coordinated.get("campaign")
        write_json_atomic(path, updated, expected_type=dict, sort_keys=True, coordinate=False)
        return {
            "active": True,
            "event": "isolated_self_development_prepared",
            "conversation_response": f"I prepared one verified disposable workspace for proposal {proposal_id}. Active source is unchanged; no provider, tests, installation, or promotion ran. To implement only inside that workspace, say exactly: {_implementation_phrase(updated)}",
            "provider_contacted": False,
            "runtime_mutated": True,
            "source_modified": False,
            "authority_granted": False,
            "self_development_proposal": updated,
        }


def _apply_maintenance_helper_extraction(workspace: Path) -> list[str]:
    target = workspace / "conscious_agent" / "self_maintenance.py"
    helper = workspace / "conscious_agent" / "self_maintenance_helpers.py"
    original = target.read_text(encoding="utf-8")
    if helper.exists() or any(original.count(block) != 1 for block in _HELPER_DEFINITIONS):
        raise RuntimeError("bounded_helper_extraction_precondition_failed")
    anchor = "from typing import Any\n"
    if original.count(anchor) != 1 or _HELPER_IMPORT in original:
        raise RuntimeError("bounded_helper_import_precondition_failed")
    revised = original.replace(anchor, anchor + "\n" + _HELPER_IMPORT, 1)
    for block in _HELPER_DEFINITIONS:
        revised = revised.replace(block, "", 1)
    try:
        helper.write_text(_HELPER_MODULE, encoding="utf-8")
        target.write_text(revised, encoding="utf-8")
    except Exception:
        target.write_text(original, encoding="utf-8")
        helper.unlink(missing_ok=True)
        raise
    return ["conscious_agent/self_maintenance.py", "conscious_agent/self_maintenance_helpers.py"]


def _apply_maintenance_task_queue_extraction(workspace: Path) -> list[str]:
    target = workspace / "conscious_agent" / "self_maintenance.py"
    helper = workspace / "conscious_agent" / "self_maintenance_task_queue.py"
    original = target.read_text(encoding="utf-8")
    if (
        helper.exists()
        or original.count(_TASK_SCORE_DEFINITION) != 1
        or original.count(_TASK_SELECTION_DEFINITIONS) != 1
        or _TASK_QUEUE_IMPORT in original
    ):
        raise RuntimeError("bounded_task_queue_extraction_precondition_failed")
    anchor = "from self_maintenance_helpers import (\n"
    if original.count(anchor) != 1:
        raise RuntimeError("bounded_task_queue_import_precondition_failed")
    import_end = original.index(")\n", original.index(anchor)) + 2
    revised = original[:import_end] + "\n" + _TASK_QUEUE_IMPORT + original[import_end:]
    replacement = '''def _score_maintenance_goal(goal: str | None = None, files: list[str] | None = None) -> dict[str, Any]:
    text = _autonomy_goal(goal).lower()
    selected = files or _select_autonomy_targets(text)
    return _score_maintenance_goal_components(text, selected)


'''
    revised = revised.replace(_TASK_SCORE_DEFINITION, replacement, 1)
    revised = revised.replace(_TASK_SELECTION_DEFINITIONS, "", 1)
    try:
        helper.write_text(_TASK_QUEUE_MODULE, encoding="utf-8")
        target.write_text(revised, encoding="utf-8")
    except Exception:
        target.write_text(original, encoding="utf-8")
        helper.unlink(missing_ok=True)
        raise
    return ["conscious_agent/self_maintenance.py", "conscious_agent/self_maintenance_task_queue.py"]


def _apply_proposal_implementation(workspace: Path, improvement_class: str) -> list[str]:
    if improvement_class == "bounded_maintainability_extraction":
        return _apply_maintenance_helper_extraction(workspace)
    if improvement_class == "maintenance_task_queue_boundary_extraction":
        return _apply_maintenance_task_queue_extraction(workspace)
    raise RuntimeError("unsupported_isolated_improvement_class")


def _run_isolated_implementation_checks(workspace: Path, proposal_id: str, improvement_class: str) -> list[dict[str, Any]]:
    cache = _runtime_root() / "self_development_proposals" / "verification_cache" / proposal_id
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": str(cache)})
    if improvement_class == "maintenance_task_queue_boundary_extraction":
        module = "conscious_agent/self_maintenance_task_queue.py"
        behavior = "import sys;sys.path.insert(0,'conscious_agent');import self_maintenance_task_queue as q;rows=[{'task_id':'low','priority_score':40,'risk_score':10,'state':'queued'},{'task_id':'high','priority_score':80,'risk_score':20,'state':'queued'}];selected,active,candidates=q._select_next_maintenance_task(rows);assert selected['task_id']=='high' and not active and len(candidates)==2;score=q._score_maintenance_goal_components('privacy queue performance',['conscious_agent/self_maintenance.py']);assert score['priority_score']==98 and score['risk_level']=='high'"
    else:
        module = "conscious_agent/self_maintenance_helpers.py"
        behavior = "import hashlib,json,os,sys,tempfile;from pathlib import Path;sys.path.insert(0,'conscious_agent');import self_maintenance_helpers as h;assert h._sha256_text({'b':2,'a':1})==hashlib.sha256(json.dumps({'b':2,'a':1},sort_keys=True,default=str).encode()).hexdigest();assert h._report_path('a'+os.sep+'b')=='a/b';p=Path(tempfile.gettempdir())/'eidolon-v1489-helper-check.json';p.write_text('{\\\"ok\\\":true}',encoding='utf-8');assert h._read_json(p,{})=={'ok':True};p.unlink(missing_ok=True)"
    commands = [
        [sys.executable, "-m", "py_compile", "conscious_agent/self_maintenance.py", module],
        [sys.executable, "-c", behavior],
        [sys.executable, "tools/v1489_product_capability_integration_tests.py"],
    ]
    receipts: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=150,
            check=False,
        )
        receipt = {
            "check_index": index,
            "return_code": completed.returncode,
            "passed": completed.returncode == 0,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "output_recorded": False,
            "content_free": True,
        }
        receipts.append(receipt)
        if completed.returncode != 0:
            raise RuntimeError(f"isolated_implementation_check_{index}_failed")
    return receipts


def _implement_isolated_proposal(
    control: re.Match[str],
    source_root: Path,
    *,
    provider_generate=None,
    operator_authorization_text: str = "",
) -> dict[str, Any]:
    proposal_id = control.group("proposal_id").lower()
    supplied_digest = control.group("digest").lower()
    path = _proposal_path(proposal_id)
    with metadata_mutation_lock(path, timeout_seconds=5):
        proposal = load_json_file(path, {}, expected_type=dict)
        expected = str(proposal.get("proposal_digest") or "")[:16]
        if not proposal:
            return {"active": True, "event": "self_development_proposal_not_found", "conversation_response": "I could not find that self-development proposal. No workspace or source was changed.", "provider_contacted": False, "source_modified": False, "authority_granted": False}
        if supplied_digest != expected:
            return {"active": True, "event": "self_development_proposal_digest_mismatch", "conversation_response": "That implementation digest does not match the stored proposal. I stopped without changing the workspace or active source.", "provider_contacted": False, "source_modified": False, "authority_granted": False}
        if proposal.get("state") == "operator_installed":
            return {"active": True, "event": "isolated_self_development_operator_install_replayed", "conversation_response": f"Proposal {proposal_id} was already reviewed and installed by the operator. I did not repeat the implementation or modify source.", "provider_contacted": False, "source_modified": False, "authority_granted": False, "self_development_proposal": proposal}
        if proposal.get("state") == "isolated_implementation_review_ready":
            return {"active": True, "event": "isolated_self_development_implementation_replayed", "conversation_response": f"Isolated implementation for proposal {proposal_id} was already completed and verified. I reused its review receipt; no duplicate implementation or active-source change occurred.", "provider_contacted": False, "source_modified": False, "authority_granted": False, "self_development_proposal": proposal}
        if proposal.get("state") == "isolated_implementation_running":
            return {"active": True, "event": "isolated_self_development_implementation_running", "conversation_response": f"Isolated implementation for proposal {proposal_id} is already running. I did not start a duplicate.", "provider_contacted": False, "source_modified": False, "authority_granted": False, "self_development_proposal": proposal}
        if not proposal.get("isolated_workspace_created"):
            return {"active": True, "event": "isolated_self_development_workspace_required", "conversation_response": "The verified isolated workspace has not been prepared, so I stopped without modifying anything.", "provider_contacted": False, "source_modified": False, "authority_granted": False}
        workspace = _runtime_root() / "self_development_proposals" / "workspaces" / proposal_id / "Eidolon"
        active_before = source_manifest(source_root)
        workspace_before = source_manifest(workspace)
        if _digest(active_before) != proposal.get("source_manifest_digest") or _digest(workspace_before) != proposal.get("workspace_manifest_digest"):
            return {"active": True, "event": "isolated_self_development_stale_baseline", "conversation_response": "The active source or isolated workspace changed after preparation. I stopped without implementing the proposal.", "provider_contacted": False, "source_modified": False, "authority_granted": False}
        running = dict(proposal)
        if proposal.get("dynamic_candidate_id"):
            implementation_phrase = f"Implement isolated self-development proposal {proposal_id} digest {proposal.get('proposal_digest', '')[:16]}."
            authorized_text = operator_authorization_text or implementation_phrase
            implementation_receipt = issue_operator_authorization(
                stage="workspace_implementation",
                subject_id=str(proposal.get("dynamic_candidate_id")),
                subject_digest=str(proposal.get("development_plan_digest")),
                explicit_operator_text=authorized_text,
                expected_operator_text=authorized_text,
            )
        else:
            implementation_receipt = {}
        running.update({"state": "isolated_implementation_running", "implementation_authorized": True, "implementation_authorization": implementation_receipt, "implementation_attempt_count": max(0, int(proposal.get("implementation_attempt_count") or 0)) + 1, "provider_contacted": False, "tests_executed": False, "source_modified": False})
        write_json_atomic(path, running, expected_type=dict, sort_keys=True, coordinate=False)
    try:
        improvement_class = str(proposal.get("improvement_class") or "")
        if improvement_class in {"bounded_maintainability_extraction", "maintenance_task_queue_boundary_extraction"}:
            changed_files = _apply_proposal_implementation(workspace, improvement_class)
            checks = _run_isolated_implementation_checks(workspace, proposal_id, improvement_class)
            provider_request_count = 0
            repair_attempt_count = 0
            candidate = source_manifest(workspace)
            result = {
                "changed_files": changed_files,
                "changed_file_count": len(changed_files),
                "check_receipts": checks,
                "checks_passed": all(row["passed"] for row in checks),
                "candidate_manifest_digest": _digest(candidate),
                "active_source_unchanged": True,
                "provider_request_count": provider_request_count,
                "repair_attempt_count": repair_attempt_count,
                "content_free": True,
            }
        else:
            result = execute_generic_isolated_proposal(
                workspace,
                proposal,
                provider_generate=provider_generate,
                baseline_content_digests=workspace_before,
            )
            changed_files = list(result.get("changed_files") or [])
            checks = list(result.get("check_receipts") or [])
        active_after = source_manifest(source_root)
        if active_after != active_before:
            raise RuntimeError("active_source_changed_during_isolated_implementation")
        with metadata_mutation_lock(path, timeout_seconds=5):
            completed = load_json_file(path, {}, expected_type=dict)
            implementation_result_digest = _digest(result)
            verification_digest = _digest({"checks": checks, "candidate_manifest_digest": result.get("candidate_manifest_digest"), "active_source_unchanged": True})
            review_digest = _digest({"proposal_id": proposal_id, "implementation_result_digest": implementation_result_digest, "verification_digest": verification_digest})
            completed.update({"state": "isolated_implementation_review_ready", "tests_executed": True, "isolated_workspace_modified": True, "source_modified": False, "operator_review_required": True, "installation_authorized": False, "promotion_authorized": False, "implementation_result": result, "implementation_result_digest": implementation_result_digest, "verification_digest": verification_digest, "review_digest": review_digest})
            if proposal.get("dynamic_candidate_id"):
                coordinated = record_review_ready(
                    _runtime_root(),
                    event_id=str(proposal.get("issue_digest") or proposal_id)[:32],
                    candidate_id=str(proposal.get("dynamic_candidate_id")),
                    implementation_digest=implementation_result_digest,
                    verification_digest=verification_digest,
                    review_digest=review_digest,
                )
                if not coordinated.get("ok"):
                    raise RuntimeError("supervised_development_review_coordination_failed")
                completed["development_campaign"] = coordinated.get("campaign")
            write_json_atomic(path, completed, expected_type=dict, sort_keys=True, coordinate=False)
        provider_count = int(result.get("provider_request_count") or 0)
        provider_text = f" The configured local model made {provider_count} bounded coding request{'s' if provider_count != 1 else ''}." if provider_count else " No provider ran."
        return {"active": True, "event": "isolated_self_development_implementation_review_ready", "conversation_response": f"I implemented proposal {proposal_id} only in its disposable workspace, changed {len(changed_files)} bounded source files, and passed all {len(checks)} verification checks.{provider_text} Active source is unchanged; no installation or promotion ran, and the candidate is ready for operator review.", "provider_contacted": provider_count > 0, "runtime_mutated": True, "source_modified": False, "authority_granted": False, "self_development_proposal": completed}
    except Exception as exc:
        provider_count = int(getattr(exc, "provider_request_count", 0) or 0)
        failure_codes = list(getattr(exc, "failure_codes", []) or [])
        blocker = str(getattr(exc, "code", "") or "").strip()
        if not blocker and isinstance(exc, (ValueError, RuntimeError)):
            blocker = str(exc).strip()
        if not blocker:
            blocker = type(exc).__name__
        blocker = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", blocker)[:160]
        if not failure_codes:
            failure_codes = [blocker]
        with metadata_mutation_lock(path, timeout_seconds=5):
            failed = load_json_file(path, {}, expected_type=dict)
            failed.update({"state": "isolated_implementation_blocked", "implementation_blocker": blocker, "implementation_failure_codes": failure_codes, "provider_contacted": provider_count > 0, "provider_request_count": provider_count, "tests_executed": False, "source_modified": False, "installation_authorized": False, "promotion_authorized": False})
            failure_receipt = build_failure_receipt(failed)
            failed["implementation_failure_receipt"] = failure_receipt
            failed["bounded_repair_plan"] = build_bounded_repair_plan(failed)
            write_json_atomic(path, failed, expected_type=dict, sort_keys=True, coordinate=False)
        retry = f" To rebuild the same disposable workspace before retrying, say exactly: {proposal.get('isolated_preparation_phrase')}" if proposal.get("isolated_preparation_phrase") else ""
        return {"active": True, "event": "isolated_self_development_implementation_blocked", "conversation_response": f"The isolated implementation for proposal {proposal_id} failed safely at {blocker}. Active source was not modified, and no installation or promotion occurred.{retry}", "provider_contacted": provider_count > 0, "runtime_mutated": True, "source_modified": False, "authority_granted": False, "self_development_proposal": failed}


def _selected_project_root(project_state: Mapping[str, Any] | None) -> Path | None:
    project = dict(project_state or {})
    raw = project.get("path") or project.get("root") or project.get("workspace")
    if not raw:
        return None
    try:
        path = Path(str(raw)).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    return path if path.is_dir() else None


def _reasoning_projection(message: str, lifecycle: Mapping[str, Any]) -> dict[str, Any]:
    requirements = build_requirements([message])
    epistemic = epistemic_partition(
        facts=["A supervised development lifecycle is available."],
        assumptions=["The selected project state is current."],
        uncertainties=["Implementation evidence is unavailable before isolated verification."],
    )
    approaches = candidate_approaches(
        ["inspect then make one bounded change", "prepare a reversible isolated candidate"]
    )
    event = str(lifecycle.get("event") or "inactive")
    requires_approval = event not in {"rejected", "cancelled", "inactive"}
    return {
        "requirement_count": len(requirements),
        "testable_requirement_count": sum(row.testable for row in requirements),
        "requirement_digests": [row.requirement_id for row in requirements],
        "known_fact_count": len(epistemic["known_facts"]),
        "assumption_count": len(epistemic["assumptions"]),
        "uncertainty_count": len(epistemic["uncertainties"]),
        "candidate_approach_count": len(approaches["approaches"]),
        "sufficient_approach_variety": approaches["sufficient_variety"],
        "selected_approach_class": "bounded_reversible_change",
        "selected_approach_score": score_tradeoff(
            evidence_strength=0.7, reversibility=1.0, testability=1.0, scope_cost=0.25
        ),
        "missing_prerequisite_count": len(
            missing_prerequisites(["operator approval", "isolated verification"], [])
        ),
        "authority_boundary": authority_stop(
            next_step="existing supervised development lifecycle",
            requires_operator=True,
            requires_approval=requires_approval,
        ),
        "raw_request_exposed": False,
        "content_free": True,
    }


def _coding_projection(message: str, project_state: Mapping[str, Any] | None) -> dict[str, Any]:
    root = _selected_project_root(project_state)
    if root is None:
        return {
            "status": "isolated_workspace_required",
            "project_inventory_available": False,
            "execution_owner": "isolated_coding_execution",
            "provider_contacted": False,
            "project_modified": False,
            "content_free": True,
        }
    inventory = inventory_project(root, limit=200)
    plan = bounded_implementation_plan(message, inventory)
    return {
        "status": "selected_project_inspected",
        "project_inventory_available": True,
        "project_root_digest": inventory["root_digest"],
        "project_file_count": inventory["file_count"],
        "inventory_truncated": inventory["truncated"],
        "planned_file_count": len(plan["selected_files"]),
        "request_digest": plan["request_digest"],
        "test_required": plan["test_required"],
        "execution_owner": "isolated_coding_execution",
        "provider_contacted": False,
        "project_modified": False,
        "content_free": True,
    }


def _self_development_projection(source_root: Path, proposal: Mapping[str, Any]) -> dict[str, Any]:
    evidence = dict(proposal.get("evidence") or {})
    return {
        "status": "concrete_proposal_persisted",
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "proposal_state": proposal.get("state"),
        "improvement_class": proposal.get("improvement_class"),
        "proposed_change": proposal.get("proposed_change"),
        "completed_predecessor_count": proposal.get("completed_predecessor_count", 0),
        "evidence_digest": proposal.get("evidence_digest"),
        "evidence_class": evidence.get("evidence_class"),
        "python_module_count": evidence.get("python_module_count", 0),
        "target_relative_path": evidence.get("target_relative_path", ""),
        "target_size_bytes": evidence.get("target_size_bytes", 0),
        "target_line_count": evidence.get("target_line_count", 0),
        "target_top_level_function_count": evidence.get("target_top_level_function_count", 0),
        "verification_count": len(proposal.get("verification_commands") or []),
        "isolated_preparation_phrase": proposal.get("isolated_preparation_phrase"),
        "reversible": True,
        "source_modified": False,
        "modification_authorized": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "private_paths_exposed": False,
        "content_free": True,
    }


def _latest_blocked_self_development_proposal() -> dict[str, Any]:
    directory = _runtime_root() / "self_development_proposals"
    paths = sorted(
        directory.glob("improvement-*.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    ) if directory.is_dir() else []
    for path in paths:
        proposal = load_json_file(path, {}, expected_type=dict)
        if proposal.get("state") == "isolated_implementation_blocked":
            return proposal
    return {}


def _blocked_self_development_explanation() -> dict[str, Any]:
    proposal = _latest_blocked_self_development_proposal()
    if not proposal:
        return {
            "active": True,
            "event": "self_development_failure_receipt_not_found",
            "conversation_response": "I do not have a blocked self-development receipt to explain, so I cannot claim a failure occurred.",
            "provider_contacted": False,
            "source_modified": False,
            "authority_granted": False,
        }
    proposal_id = str(proposal.get("proposal_id") or "unknown proposal")
    codes = [str(code) for code in proposal.get("implementation_failure_codes") or []]
    provider_count = int(proposal.get("provider_request_count") or 0)
    if "symbol_refactoring_scope_requires_one_source_and_destination" in codes:
        reason = (
            "The proposal repeated an extraction whose destination helper already existed, "
            "so the deterministic refactoring gate could not bind one existing source to one new destination."
        )
    else:
        reason = "The isolated executor stopped at its recorded verification boundary"
        if codes:
            reason += f" ({', '.join(codes)})"
        reason += "."
    provider_text = (
        f"The configured provider received {provider_count} bounded request{'s' if provider_count != 1 else ''}."
        if provider_count else "The provider was not called."
    )
    retry_phrase = str(proposal.get("isolated_preparation_phrase") or "")
    retry_text = f" To retry from a refreshed disposable workspace, say exactly: {retry_phrase}" if retry_phrase else ""
    return {
        "active": True,
        "event": "self_development_failure_receipt_explained",
        "conversation_response": (
            f"Implementation {proposal_id} failed safely. {reason} {provider_text} "
            f"Active source was unchanged, and no installation or promotion occurred.{retry_text}"
        ),
        "provider_contacted": provider_count > 0,
        "source_modified": False,
        "authority_granted": False,
        "self_development_proposal": proposal,
    }


def _current_initiative_evidence_intake(hardening: Mapping[str, Any]) -> dict[str, Any]:
    """Combine current structural evidence with redacted operator findings."""

    findings: list[dict[str, Any]] = []
    try:
        from conversation_evaluation_finding_aggregation import build_evaluation_finding_aggregation
        from development_finding_intelligence import build_development_finding_projection

        aggregation = build_evaluation_finding_aggregation()
        projection = build_development_finding_projection(aggregation)
        findings = [
            {
                "finding_id": row.get("finding_id"),
                "record_digest": row.get("finding_digest"),
                "state": row.get("state"),
                "issue_domain": row.get("issue_domain"),
                "severity": row.get("severity"),
                "frequency": row.get("reproduction_attempt_count"),
                "confidence": row.get("confidence"),
                "freshness": row.get("freshness"),
                "candidate_id": row.get("candidate_id"),
                "source_module": row.get("source_module"),
                "operator_confirmed": True,
            }
            for row in projection.get("findings") or ()
        ]
    except (OSError, RuntimeError, ValueError):
        findings = []
    conversation_domains = {"model_quality", "interface", "session_continuity"}
    conversation = [row for row in findings if str(row.get("issue_domain") or "") in conversation_domains]
    operator = [row for row in findings if row not in conversation]
    recorded = list_operator_development_findings()
    recorded_by_class: dict[str, list[dict[str, Any]]] = {}
    for row in recorded:
        recorded_by_class.setdefault(str(row.get("evidence_class") or "operator_reported_defect"), []).append(row)
    return build_initiative_evidence_intake(
        structural_candidates=hardening.get("eligible_candidates") or (),
        operator_findings=[*operator, *recorded_by_class.get("operator_reported_defect", ())],
        failing_tests=recorded_by_class.get("failing_test", ()),
        diagnostics=recorded_by_class.get("diagnostic_finding", ()),
        performance_regressions=recorded_by_class.get("performance_regression", ()),
        conversation_findings=[*conversation, *recorded_by_class.get("conversation_quality_finding", ())],
        capability_gaps=recorded_by_class.get("missing_capability", ()),
        security_findings=recorded_by_class.get("security_debt", ()),
    )


def _continue_supervised_development(message: str, source_root: Path) -> dict[str, Any]:
    """Advance one reversible initiative cycle to its next operator boundary."""

    authorization_text = str(message or "").strip()
    reconciliation = reconcile_supervised_initiative_queue()
    queue = reconciliation["initiative_queue"]
    # Reconcile terminal queue receipts into the durable multi-cycle campaign.
    # Missing campaigns are harmless; campaign bookkeeping never owns install authority.
    for recorded in queue.get("recent_records") or ():
        if recorded.get("lifecycle_state") == "operator_installed":
            record_campaign_candidate_state(
                str(recorded.get("candidate_id") or ""),
                str(recorded.get("evidence_digest") or ""),
                "installed",
                proposal_id=str(recorded.get("proposal_id") or ""),
            )
    active_states = {
        "queued",
        "ready_for_proposal_review",
        "proposal_created",
        "workspace_prepared",
        "implementation_running",
        "candidate_ready_for_review",
        "implementation_blocked",
    }
    initiative = next(
        (row for row in reversed(queue.get("recent_records") or ()) if row.get("lifecycle_state") in active_states),
        None,
    )
    stages: list[str] = []

    if initiative is None:
        installed = _installed_proposal_history()
        discovery = build_dynamic_improvement_discovery(source_root, completed_lineages=installed)
        hardening = harden_dynamic_discovery(discovery, completed_lineages=installed)
        comparison = compare_dynamic_candidates(hardening)
        evidence_intake = _current_initiative_evidence_intake(hardening)
        prior_ids = [str(row.get("candidate_id") or "") for row in queue.get("recent_records") or ()]
        shortlist = build_value_prioritized_initiative_shortlist(
            hardening,
            comparison,
            prior_candidate_ids=prior_ids,
            recent_initiatives=queue.get("recent_records") or (),
            limit=3,
            evidence_intake=evidence_intake,
        )
        if not shortlist.get("ok"):
            value_response = value_prioritized_initiative_response(shortlist)
            if shortlist.get("selection_blocked_by_unbound_value"):
                event = "supervised_development_value_selection_blocked"
            elif shortlist.get("selection_blocked_by_maintenance_budget"):
                event = "supervised_development_portfolio_rebalance_required"
            else:
                event = "supervised_development_no_eligible_initiative"
            product_planning: dict[str, Any] = {}
            if shortlist.get("selection_blocked_by_maintenance_budget"):
                product_planning = build_evidence_to_candidate_plans(evidence_intake, source_root=source_root)
                ready_plan = next(
                    (dict(row) for row in product_planning.get("plans") or () if row.get("implementation_ready")),
                    None,
                )
                if ready_plan:
                    registration = register_product_candidate_plan(ready_plan, source_root=source_root)
                    product_planning["registration_status"] = registration.get("status")
                    product_planning["registration_operation"] = registration.get("operation_status")
                value_response += "\n" + evidence_to_candidate_response(product_planning)
                if ready_plan and product_planning.get("registration_status") == "product_plan_registered":
                    value_response += (
                        " To validate this exact plan against the current source, say: Review product plan "
                        f"{ready_plan.get('candidate_plan_id')} digest "
                        f"{str(ready_plan.get('candidate_plan_digest') or '')[:16]}."
                    )
            return {
                "active": True,
                "event": event,
                "conversation_response": value_response,
                "provider_contacted": False,
                "runtime_mutated": bool(reconciliation.get("reconciled_count")),
                "source_modified": False,
                "authority_granted": False,
                "v1525_value_prioritized_shortlist": shortlist,
                "v2500_evidence_to_candidate_planning": product_planning,
            }
        source_digest = _digest(source_manifest(source_root))
        campaign_record = create_or_reuse_campaign(shortlist, source_digest=source_digest)
        if campaign_record.get("ok"):
            active_campaign = current_active_campaign_candidate(current_shortlist=shortlist)
            if active_campaign.get("ok"):
                shortlist = bind_shortlist_selection(shortlist, str((active_campaign.get("candidate") or {}).get("candidate_id") or ""))
            else:
                campaign_selection = select_next_campaign_candidate(current_shortlist=shortlist)
                if campaign_selection.get("ok"):
                    shortlist = bind_shortlist_selection(shortlist, str((campaign_selection.get("candidate") or {}).get("candidate_id") or ""))
                elif campaign_selection.get("status") not in {"campaign_missing_or_invalid", "campaign_requires_three_meaningful_initiatives"}:
                    return {
                        "active": True,
                        "event": "supervised_development_campaign_selection_blocked",
                        "conversation_response": "The supervised campaign could not select a still-current dependency-ready initiative. No proposal or source change was made.",
                        "provider_contacted": False,
                        "runtime_mutated": bool(campaign_record.get("runtime_mutated")),
                        "source_modified": False,
                        "authority_granted": False,
                        "supervised_campaign": campaign_selection.get("campaign"),
                    }
        queued = queue_supervised_initiative(
            shortlist,
            discovery_digest=str(discovery.get("discovery_digest") or ""),
            comparison_digest=str(comparison.get("comparison_digest") or ""),
        )
        initiative = dict(queued.get("initiative") or {})
        stages.append("initiative_selected")

    if initiative.get("lifecycle_state") == "candidate_ready_for_review":
        proposal_id = str(initiative.get("proposal_id") or "")
        record_campaign_candidate_state(str(initiative.get("candidate_id") or ""), str(initiative.get("evidence_digest") or ""), "review_ready", proposal_id=proposal_id)
        return {
            "active": True,
            "event": "supervised_development_operator_review_required",
            "conversation_response": (
                f"Candidate {proposal_id} is already implemented and verified in its disposable workspace. "
                f"Active source is unchanged. To exercise your installation authority, say: Review and install candidate {proposal_id}."
            ),
            "provider_contacted": False,
            "runtime_mutated": bool(reconciliation.get("reconciled_count")),
            "source_modified": False,
            "authority_granted": False,
            "operator_review_required": True,
        }

    if initiative.get("lifecycle_state") == "queued":
        advanced = control_supervised_initiative(
            "advance",
            str(initiative.get("initiative_id") or ""),
            str(initiative.get("initiative_digest") or "")[:16],
        )
        if not advanced.get("ok"):
            return {**advanced, "event": "supervised_development_advance_blocked"}
        initiative = dict(advanced.get("initiative") or {})
        stages.append("initiative_advanced")

    proposal: dict[str, Any] = {}
    proposal_id = str(initiative.get("proposal_id") or "")
    if proposal_id:
        proposal = load_json_file(_proposal_path(proposal_id), {}, expected_type=dict)

    if not proposal:
        selection_phrase = (
            f"Create dynamic self-development proposal {initiative.get('candidate_id')} "
            f"evidence {str(initiative.get('evidence_digest') or '')[:16]}."
        )
        selection_control = _CREATE_DYNAMIC_PROPOSAL.fullmatch(selection_phrase)
        if selection_control is None:
            raise RuntimeError("supervised_development_selection_control_invalid")
        created = _create_dynamic_proposal(
            selection_control,
            source_root,
            operator_authorization_text=authorization_text,
        )
        proposal = dict(created.get("self_development_proposal") or {})
        if not proposal:
            return {**created, "event": "supervised_development_proposal_blocked"}
        proposal_id = str(proposal.get("proposal_id") or "")
        update_supervised_initiative_lifecycle(
            str(initiative.get("candidate_id") or ""),
            str(initiative.get("evidence_digest") or ""),
            "proposal_created",
            proposal_id=proposal_id,
        )
        stages.append("proposal_created")

    if proposal.get("state") in {"awaiting_operator_isolated_preparation", "isolated_implementation_blocked"}:
        preparation_phrase = str(proposal.get("isolated_preparation_phrase") or "") or (
            f"Prepare isolated self-development proposal {proposal_id} digest {str(proposal.get('proposal_digest') or '')[:16]}."
        )
        preparation_control = _PREPARE_SELF_PROPOSAL.fullmatch(preparation_phrase)
        if preparation_control is None:
            raise RuntimeError("supervised_development_preparation_control_invalid")
        prepared = _prepare_isolated_proposal(
            preparation_control,
            source_root,
            operator_authorization_text=authorization_text,
        )
        proposal = dict(prepared.get("self_development_proposal") or {})
        if not proposal or proposal.get("state") != "isolated_workspace_prepared":
            return {**prepared, "event": "supervised_development_preparation_blocked"}
        update_supervised_initiative_lifecycle(
            str(initiative.get("candidate_id") or ""),
            str(initiative.get("evidence_digest") or ""),
            "workspace_prepared",
            proposal_id=proposal_id,
        )
        stages.append("workspace_prepared")

    if proposal.get("state") == "isolated_workspace_prepared":
        implementation_phrase = _implementation_phrase(proposal)
        implementation_control = _IMPLEMENT_SELF_PROPOSAL.fullmatch(implementation_phrase)
        if implementation_control is None:
            raise RuntimeError("supervised_development_implementation_control_invalid")
        update_supervised_initiative_lifecycle(
            str(initiative.get("candidate_id") or ""),
            str(initiative.get("evidence_digest") or ""),
            "implementation_running",
            proposal_id=proposal_id,
        )
        implemented = _implement_isolated_proposal(
            implementation_control,
            source_root,
            operator_authorization_text=authorization_text,
        )
        proposal = dict(implemented.get("self_development_proposal") or {})
        if proposal.get("state") != "isolated_implementation_review_ready":
            update_supervised_initiative_lifecycle(
                str(initiative.get("candidate_id") or ""),
                str(initiative.get("evidence_digest") or ""),
                "implementation_blocked",
                proposal_id=proposal_id,
            )
            record_campaign_candidate_state(str(initiative.get("candidate_id") or ""), str(initiative.get("evidence_digest") or ""), "blocked", proposal_id=proposal_id)
            return {
                **implemented,
                "event": "supervised_development_implementation_blocked",
                "completed_stages": stages,
            }
        update_supervised_initiative_lifecycle(
            str(initiative.get("candidate_id") or ""),
            str(initiative.get("evidence_digest") or ""),
            "candidate_ready_for_review",
            proposal_id=proposal_id,
        )
        record_campaign_candidate_state(str(initiative.get("candidate_id") or ""), str(initiative.get("evidence_digest") or ""), "review_ready", proposal_id=proposal_id)
        stages.append("candidate_implemented_and_verified")

    selected = dict(initiative.get("selected") or {})
    result = dict(proposal.get("implementation_result") or {})
    benefit = str(selected.get("practical_benefit") or "bounded maintainability improvement")
    criteria = ", ".join(selected.get("acceptance_criteria") or ())
    return {
        "active": True,
        "event": "supervised_development_cycle_ready_for_operator_review",
        "conversation_response": (
            f"I continued one supervised development cycle for {selected.get('title') or proposal.get('proposed_change')}. "
            f"I selected current evidence, created the bounded proposal, prepared its disposable workspace, and "
            f"implemented and verified candidate {proposal_id}. The candidate changed {result.get('changed_file_count', 0)} "
            f"bounded source files and passed {len(result.get('check_receipts') or ())} checks. Its recorded benefit is {benefit}; "
            f"its acceptance criteria are {criteria or 'recorded in the initiative receipt'}. Active source is unchanged. "
            f"To exercise your installation authority, say: Review and install candidate {proposal_id}."
        ),
        "completed_stages": stages,
        "proposal_id": proposal_id,
        "provider_contacted": int(result.get("provider_request_count") or 0) > 0,
        "provider_request_count": int(result.get("provider_request_count") or 0),
        "runtime_mutated": True,
        "source_modified": False,
        "authority_granted": False,
        "operator_review_required": True,
        "self_development_proposal": proposal,
    }


def integrate_v1489_product_capabilities(
    message: str,
    lifecycle: Mapping[str, Any] | None,
    *,
    project_state: Mapping[str, Any] | None = None,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return an enriched lifecycle while preserving its existing authority owner."""

    result = dict(lifecycle or {})
    root = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    if is_operator_development_finding_command(str(message or "")):
        return record_operator_development_finding(str(message or ""))
    product_plan_control = process_product_plan_control(str(message or ""), source_root=root)
    if product_plan_control.get("active"):
        return product_plan_control
    combined_candidate_control = _REVIEW_AND_INSTALL_CANDIDATE.fullmatch(str(message or "").strip())
    if combined_candidate_control:
        return install_reviewed_candidate(
            combined_candidate_control.group("proposal_id").lower(),
            source_root=root,
            combined_review_and_install=True,
        )
    installation_control = _INSTALL_REVIEWED_CANDIDATE.fullmatch(str(message or "").strip())
    if installation_control:
        return install_reviewed_candidate(
            installation_control.group("proposal_id").lower(),
            source_root=root,
            expected_review_digest=installation_control.group("digest").lower(),
        )
    review_control = _REVIEW_SELF_CANDIDATE.fullmatch(str(message or "").strip())
    if review_control:
        return review_isolated_candidate(review_control.group("proposal_id").lower(), source_root=root)
    if is_initiative_evidence_review_control(str(message or "")):
        installed = _installed_proposal_history()
        discovery = build_dynamic_improvement_discovery(root, completed_lineages=installed)
        hardening = harden_dynamic_discovery(discovery, completed_lineages=installed)
        evidence_intake = _current_initiative_evidence_intake(hardening)
        return process_initiative_evidence_review_control(str(message or ""), evidence_intake)
    if is_campaign_control(str(message or "")):
        return process_campaign_control(str(message or ""))
    if is_supervised_development_continuation(str(message or "")):
        return _continue_supervised_development(str(message or ""), root)
    initiative_control = process_supervised_initiative_control(str(message or ""))
    if initiative_control.get("active"):
        return initiative_control
    if (
        _SELF_DEVELOPMENT_FAILURE_QUESTION.fullmatch(str(message or "").strip())
        or _SELF_DEVELOPMENT_FAILURE_FOLLOWUP.fullmatch(str(message or "").strip())
    ):
        return _blocked_self_development_explanation()
    dynamic_proposal_control = _CREATE_DYNAMIC_PROPOSAL.fullmatch(str(message or "").strip())
    if dynamic_proposal_control:
        return _create_dynamic_proposal(dynamic_proposal_control, root)
    implementation_control = _IMPLEMENT_SELF_PROPOSAL.fullmatch(str(message or "").strip())
    if implementation_control:
        return _implement_isolated_proposal(implementation_control, root)
    preparation_control = _PREPARE_SELF_PROPOSAL.fullmatch(str(message or "").strip())
    if preparation_control:
        return _prepare_isolated_proposal(preparation_control, root)
    self_inspection_requested = bool(_SELF_INSPECTION.search(str(message or "")))
    initiative_queue_requested = bool(
        self_inspection_requested
        and re.search(r"\b(?:three|3)\b", str(message or ""), re.IGNORECASE)
        and re.search(r"\b(?:select|choose)\b", str(message or ""), re.IGNORECASE)
        and re.search(r"\b(?:initiative\s+queue|queue)\b", str(message or ""), re.IGNORECASE)
    )

    if self_inspection_requested:
        installed = _installed_proposal_history()
        discovery = build_dynamic_improvement_discovery(root, completed_lineages=installed)
        public_discovery = public_dynamic_discovery_projection(discovery)
        hardening = harden_dynamic_discovery(discovery, completed_lineages=installed)
        comparison = compare_dynamic_candidates(hardening)
        evidence_intake = _current_initiative_evidence_intake(hardening)
        initiative_queue: dict[str, Any] = {}
        initiative_shortlist: dict[str, Any] = {}
        focus = list(public_discovery.get("focus_candidates") or [])
        focus_summary = dict(public_discovery.get("focus_module_summary") or {})
        candidate_count = int(public_discovery.get("eligible_candidate_count") or 0)
        rejected_count = int(public_discovery.get("rejected_candidate_count") or 0)
        focus_text = (
            f" The mandated conscious_agent/self_maintenance.py review surface is {focus_summary.get('line_count', 0):,} lines, "
            f"{focus_summary.get('module_size_bytes', 0):,} bytes, and {focus_summary.get('top_level_symbol_count', 0)} top-level symbols; "
            f"{focus_summary.get('retained_extraction_wrapper_count', 0)} installed retained wrappers are explicitly excluded from rediscovery."
        )
        if focus:
            descriptions = [
                f"{item.get('proposed_destination_module')} from {len(item.get('source_symbols') or [])} adjacent symbols"
                for item in focus[:3]
            ]
            focus_text += " Bounded self_maintenance families include " + "; ".join(descriptions) + "."
        else:
            focus_rejections = list(discovery.get("focus_rejections") or [])
            insufficient_testability = sum(
                "insufficient_existing_test_reference" in set(item.get("rejection_codes") or [])
                for item in focus_rejections
            )
            focus_text += (
                f" No self_maintenance family currently meets attributable-test eligibility; "
                f"{insufficient_testability} bounded focus families were rejected for insufficient module-specific test evidence."
            )
        if candidate_count and initiative_queue_requested:
            prior_queue = inspect_supervised_initiative_queue()
            prior_ids = [str(row.get("candidate_id") or "") for row in prior_queue.get("recent_records") or ()]
            initiative_shortlist = build_value_prioritized_initiative_shortlist(
                hardening,
                comparison,
                prior_candidate_ids=prior_ids,
                limit=3,
                evidence_intake=evidence_intake,
            )
            if initiative_shortlist.get("ok"):
                initiative_queue = queue_supervised_initiative(
                    initiative_shortlist,
                    discovery_digest=str(discovery.get("discovery_digest") or ""),
                    comparison_digest=str(comparison.get("comparison_digest") or ""),
                )
                response = supervised_initiative_response(initiative_shortlist, initiative_queue)
                response += "\n" + value_prioritized_initiative_response(initiative_shortlist)
                event = "supervised_initiative_queued" if initiative_queue.get("ok") else "supervised_initiative_queue_blocked"
            else:
                initiative_queue = {
                    "ok": False,
                    "status": str(initiative_shortlist.get("status") or "value_selection_blocked"),
                    "runtime_mutated": False,
                    "provider_contacted": False,
                    "source_modified": False,
                    "authority_granted": False,
                }
                response = value_prioritized_initiative_response(initiative_shortlist)
                event = "supervised_initiative_value_selection_blocked"
        elif candidate_count:
            hardened_count = int(hardening.get("eligible_count") or 0)
            compared_count = int(comparison.get("candidate_count") or 0)
            response = (
                f"I inspected {public_discovery.get('module_count', 0)} Python modules read-only and found "
                f"{candidate_count} structurally eligible discovery families plus {rejected_count} explicitly rejected families."
                + focus_text
                + f" After overlap, duplicate-lineage, protected-boundary, testability, and confidence hardening, {hardened_count} remain eligible for quality comparison; {compared_count} were compared for operator review."
                + " The comparison may order evidence, but it did not select a candidate, create a proposal, prepare a workspace, request approval, contact a provider, or modify source. "
                "Each surviving candidate has stable discovery, eligibility, and comparison evidence for later operator-selected planning."
            )
            if comparison.get("top_candidate_is_unique") and comparison.get("ordered_comparison"):
                top = comparison["ordered_comparison"][0]
                response += _dynamic_candidate_review_handoff(top, hardening)
            event = "dynamic_improvement_discovery_candidates_available"
        else:
            response = (
                f"I inspected {public_discovery.get('module_count', 0)} Python modules read-only and found no qualifying bounded discovery candidate. "
                f"I rejected {rejected_count} weak, ambiguous, protected, duplicate, overly broad, or insufficiently testable families rather than inventing work. "
                "No provider, proposal, workspace, approval, source change, installation, or promotion occurred."
            )
            event = "dynamic_improvement_discovery_honest_stop"
        result.update(
            {
                "active": True,
                "event": event,
                "conversation_response": response,
                "provider_contacted": False,
                "runtime_mutated": bool(initiative_queue.get("runtime_mutated")),
                "source_modified": False,
                "authority_granted": False,
                "v1489_self_inspection_requested": True,
                "v1490_dynamic_improvement_discovery": public_discovery,
                "v1490_dynamic_improvement_eligibility": hardening,
                "v1491_dynamic_candidate_quality": comparison,
                "v1501_supervised_initiative_shortlist": initiative_shortlist,
                "v1501_supervised_initiative_queue": initiative_queue,
                "v1489_supervised_self_development": {
                    "status": "supervised_initiative_queued" if initiative_queue.get("ok") else "dynamic_discovery_only",
                    "candidate_count": candidate_count,
                    "rejected_candidate_count": rejected_count,
                    "selection_made": bool(initiative_shortlist.get("selection_made")),
                    "proposal_created": False,
                    "workspace_prepared": False,
                    "provider_contacted": False,
                    "source_modified": False,
                    "modification_authorized": False,
                    "installation_authorized": False,
                    "promotion_authorized": False,
                    "initiative_queued": bool(initiative_queue.get("ok")),
                    "content_free": True,
                },
            }
        )

    if result.get("active"):
        result["v1489_reasoning_planning"] = _reasoning_projection(str(message or ""), result)
        result["v1489_practical_coding"] = _coding_projection(str(message or ""), project_state)
        result.setdefault(
            "v1489_supervised_self_development",
            {
                "status": "not_requested",
                "source_modified": False,
                "modification_authorized": False,
                "installation_authorized": False,
                "promotion_authorized": False,
                "content_free": True,
            },
        )
        result["v1489_integration_digest"] = _digest(
            {
                "event": result.get("event"),
                "reasoning": result["v1489_reasoning_planning"],
                "coding": result["v1489_practical_coding"],
                "self_development": result["v1489_supervised_self_development"],
                "dynamic_discovery": result.get("v1490_dynamic_improvement_discovery"),
                "dynamic_eligibility": result.get("v1490_dynamic_improvement_eligibility"),
                "dynamic_candidate_quality": result.get("v1491_dynamic_candidate_quality"),
                "supervised_initiative_shortlist": result.get("v1501_supervised_initiative_shortlist"),
                "supervised_initiative_queue": result.get("v1501_supervised_initiative_queue"),
            }
        )
    return result


def public_v1489_product_capabilities(lifecycle: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(lifecycle or {})
    return {
        "reasoning_planning": dict(row.get("v1489_reasoning_planning") or {}),
        "practical_coding": dict(row.get("v1489_practical_coding") or {}),
        "supervised_self_development": dict(row.get("v1489_supervised_self_development") or {}),
        "dynamic_improvement_discovery": dict(row.get("v1490_dynamic_improvement_discovery") or {}),
        "dynamic_improvement_eligibility": dict(row.get("v1490_dynamic_improvement_eligibility") or {}),
        "dynamic_candidate_quality": dict(row.get("v1491_dynamic_candidate_quality") or {}),
        "supervised_initiative_shortlist": dict(row.get("v1501_supervised_initiative_shortlist") or {}),
        "supervised_initiative_queue": dict(row.get("v1501_supervised_initiative_queue") or {}),
        "integration_digest": str(row.get("v1489_integration_digest") or ""),
        "content_free": True,
    }
