from __future__ import annotations

"""Restart-safe v1501 supervised development initiative queue.

The queue may shortlist and select one evidence-backed improvement for operator
attention. Selection is not a development proposal, approval, implementation,
provider request, source change, installation, or promotion.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from json_storage import load_json_file, write_json_atomic
from initiative_evidence_intake import build_initiative_evidence_intake
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1501.3"
MAX_RECORDS = 128
ACTIVE_STATES = frozenset({
    "queued",
    "ready_for_proposal_review",
    "proposal_created",
    "workspace_prepared",
    "implementation_running",
    "candidate_ready_for_review",
    "implementation_blocked",
})
TERMINAL_STATES = frozenset({"dismissed", "deferred", "operator_installed"})

_CONTROL = re.compile(
    r"^(?P<action>defer|dismiss|advance) supervised initiative "
    r"(?P<initiative_id>devinit_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{16})[.!?]*$",
    re.IGNORECASE,
)
_SHOW = re.compile(r"^(?:show|inspect) supervised initiative queue[.!?]*$", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()


def _path(runtime_root: str | Path | None = None) -> Path:
    return _runtime_root(runtime_root) / "development_campaigns" / "supervised_initiative_queue.json"


def _default() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "records": [],
        "revision": 0,
        "updated_at": "",
        "controls": {"max_records": MAX_RECORDS, "max_active": 1, "shortlist_size": 3},
        "authority_boundary": {
            "proposal_creation_authorized": False,
            "workspace_preparation_authorized": False,
            "provider_contact_authorized": False,
            "source_mutation_authorized": False,
            "project_mutation_authorized": False,
            "approval_granted": False,
            "installation_authorized": False,
            "promotion_authorized": False,
            "independent_authority_granted": False,
        },
    }


def _load(runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = load_json_file(_path(runtime_root), _default(), expected_type=dict)
    if state.get("schema_version") != "1":
        return _default()
    for key, value in _default().items():
        state.setdefault(key, deepcopy(value))
    state["records"] = [dict(row) for row in state.get("records") or () if isinstance(row, Mapping)]
    return state


def _module_name(path: str) -> str:
    return Path(str(path or "unknown.py")).stem.replace("_", " ")


def _family_name(row: Mapping[str, Any]) -> str:
    symbols = [str(value).strip("_").replace("_", " ") for value in row.get("source_symbols") or () if str(value)]
    if not symbols:
        return _module_name(str(row.get("source_module") or ""))
    common = set(symbols[0].split())
    for symbol in symbols[1:]:
        common &= set(symbol.split())
    useful = sorted(word for word in common if len(word) > 3 and word not in {"build", "create", "public", "inspect"})
    return " ".join(useful[:3]) or _module_name(str(row.get("source_module") or ""))


def _risk(row: Mapping[str, Any]) -> tuple[float, str]:
    dependencies = max(0, int(row.get("estimated_dependency_count") or 0))
    symbols = max(1, len(row.get("source_symbols") or ()))
    confidence = max(0.0, min(1.0, float(row.get("confidence") or 0.0)))
    score = round(min(1.0, .45 * min(1.0, dependencies / 36.0) + .30 * min(1.0, symbols / 8.0) + .25 * (1.0 - confidence)), 4)
    return score, "low" if score < .3 else "medium" if score < .6 else "high"


def _operator_candidate(
    row: Mapping[str, Any],
    quality: Mapping[str, Any],
    seen: set[str],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    tests = max(0, int(row.get("test_reference_file_count") or 0))
    dependencies = max(0, int(row.get("estimated_dependency_count") or 0))
    confidence = max(0.0, min(1.0, float(row.get("confidence") or 0.0)))
    quality_score = max(0.0, min(1.0, float(quality.get("quality_score") or 0.0)))
    risk_score, risk_class = _risk(row)
    impact_score = max(0.0, min(1.0, float(evidence.get("impact_score") or 0.0)))
    value_score = impact_score
    novelty_score = 0.0 if str(row.get("candidate_id") or "") in seen else 1.0
    effort_fit = round(max(0.0, 1.0 - (.7 * min(1.0, dependencies / 36.0) + .3 * min(1.0, len(row.get("source_symbols") or ()) / 8.0))), 4)
    selection_score = round(.35 * quality_score + .30 * value_score + .15 * novelty_score + .20 * effort_fit - .10 * risk_score, 4)
    source_module = str(row.get("source_module") or "")
    destination = str(row.get("proposed_destination_module") or "")
    family = _family_name(row)
    title = f"Separate {family} helpers"
    description = (
        f"Move {len(row.get('source_symbols') or ())} related helpers from {Path(source_module).name} "
        f"into {Path(destination).name} while retaining compatible imports."
    )
    reason = (
        f"This is {risk_class} risk, has {tests} attributable test file{'s' if tests != 1 else ''}, "
        f"{dependencies} estimated dependencies, and {confidence:.0%} evidence confidence."
    )
    result = {
        "candidate_id": str(row.get("candidate_id") or ""),
        "evidence_digest": str(row.get("evidence_digest") or ""),
        "eligibility_digest": str(row.get("eligibility_digest") or ""),
        "source_module": source_module,
        "proposed_destination_module": destination,
        "source_symbols": [str(value) for value in row.get("source_symbols") or ()],
        "title": title,
        "description": description,
        "reason": reason,
        "quality_score": quality_score,
        "value_score": value_score,
        "impact_score": impact_score,
        "evidence_class": str(evidence.get("evidence_class") or "structural_debt"),
        "evidence_intake_id": str(evidence.get("evidence_id") or ""),
        "practical_benefit": str(evidence.get("practical_benefit") or "maintainability_and_regression_risk_reduction"),
        "acceptance_criteria": [str(value) for value in evidence.get("acceptance_criteria") or ()],
        "capability_change_expected": bool(evidence.get("capability_change_expected")),
        "structural_only": bool(evidence.get("structural_only", True)),
        "impact_review_required": impact_score < 0.6,
        "novelty_score": novelty_score,
        "effort_fit": effort_fit,
        "risk_score": risk_score,
        "risk_class": risk_class,
        "selection_score": selection_score,
        "content_free": True,
    }
    result["candidate_digest"] = _digest(result)
    return result


def build_supervised_initiative_shortlist(
    hardening: Mapping[str, Any],
    comparison: Mapping[str, Any],
    *,
    prior_candidate_ids: Sequence[str] = (),
    limit: int = 3,
    evidence_intake: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    eligible = {str(row.get("candidate_id") or ""): dict(row) for row in hardening.get("eligible_candidates") or ()}
    quality = {str(row.get("candidate_id") or ""): dict(row) for row in comparison.get("ordered_comparison") or ()}
    seen = {str(value) for value in prior_candidate_ids if str(value)}
    intake = dict(evidence_intake or build_initiative_evidence_intake(structural_candidates=eligible.values()))
    evidence: dict[str, dict[str, Any]] = {}
    for evidence_row in intake.get("records") or ():
        candidate_id = str(evidence_row.get("candidate_id") or "")
        if not candidate_id:
            continue
        current = evidence.get(candidate_id)
        if current is None or float(evidence_row.get("impact_score") or 0.0) > float(current.get("impact_score") or 0.0):
            evidence[candidate_id] = dict(evidence_row)
    candidates = [
        _operator_candidate(row, quality.get(candidate_id, {}), seen, evidence.get(candidate_id, {}))
        for candidate_id, row in eligible.items()
        if candidate_id in quality
    ]
    candidates.sort(key=lambda row: (-row["selection_score"], row["risk_score"], row["candidate_id"]))

    shortlist: list[dict[str, Any]] = []
    used_modules: set[str] = set()
    for row in candidates:
        if row["source_module"] in used_modules:
            continue
        shortlist.append(row)
        used_modules.add(row["source_module"])
        if len(shortlist) >= max(1, min(3, int(limit))):
            break
    if len(shortlist) < max(1, min(3, int(limit))):
        for row in candidates:
            if row in shortlist:
                continue
            shortlist.append(row)
            if len(shortlist) >= max(1, min(3, int(limit))):
                break
    selected = shortlist[0] if shortlist else {}
    result = {
        "ok": bool(shortlist),
        "status": "supervised_initiative_shortlist_ready" if shortlist else "no_eligible_initiative",
        "contract_version": CONTRACT_VERSION,
        "shortlist": shortlist,
        "shortlist_count": len(shortlist),
        "selected_candidate_id": str(selected.get("candidate_id") or ""),
        "selection_made": bool(selected),
        "selection_basis": "quality_value_novelty_effort_and_risk" if selected else "",
        "evidence_intake_digest": str(intake.get("intake_digest") or ""),
        "evidence_class_counts": dict(intake.get("class_counts") or {}),
        "unbound_priority_evidence_count": int(intake.get("unbound_priority_evidence_count") or 0),
        "observed_product_impact_present": any(not bool(row.get("structural_only")) for row in shortlist),
        "proposal_created": False,
        "workspace_prepared": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }
    result["shortlist_digest"] = _digest({**result, "shortlist": [row["candidate_digest"] for row in shortlist]})
    return result


def queue_supervised_initiative(
    shortlist: Mapping[str, Any],
    *,
    discovery_digest: str,
    comparison_digest: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    selected_id = str(shortlist.get("selected_candidate_id") or "")
    selected = next((dict(row) for row in shortlist.get("shortlist") or () if row.get("candidate_id") == selected_id), None)
    if not selected:
        return {"ok": False, "status": "initiative_selection_missing", "runtime_mutated": False}
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        state = _load(runtime_root)
        existing = next((row for row in state["records"] if row.get("candidate_id") == selected_id and row.get("evidence_digest") == selected.get("evidence_digest") and row.get("lifecycle_state") in ACTIVE_STATES | {"deferred"}), None)
        if existing:
            return {"ok": True, "status": "supervised_initiative_reused", "initiative": deepcopy(existing), "idempotent": True, "runtime_mutated": False}
        active = next((row for row in reversed(state["records"]) if row.get("lifecycle_state") in ACTIVE_STATES), None)
        if active:
            return {"ok": True, "status": "existing_supervised_initiative_retained", "initiative": deepcopy(active), "idempotent": True, "runtime_mutated": False}
        identity = {
            "candidate_id": selected_id,
            "evidence_digest": selected.get("evidence_digest"),
            "comparison_digest": comparison_digest,
            "discovery_digest": discovery_digest,
        }
        initiative_id = f"devinit_{_digest(identity)[:24]}"
        now = _now()
        row = {
            "initiative_id": initiative_id,
            "candidate_id": selected_id,
            "evidence_digest": selected.get("evidence_digest"),
            "eligibility_digest": selected.get("eligibility_digest"),
            "comparison_digest": comparison_digest,
            "discovery_digest": discovery_digest,
            "shortlist_digest": shortlist.get("shortlist_digest"),
            "evidence_intake_digest": shortlist.get("evidence_intake_digest"),
            "unbound_priority_evidence_count": int(shortlist.get("unbound_priority_evidence_count") or 0),
            "shortlist": [dict(value) for value in shortlist.get("shortlist") or ()],
            "selected": selected,
            "lifecycle_state": "queued",
            "created_at": now,
            "updated_at": now,
            "history": [{"event": "queued", "occurred_at": now, "content_free": True}],
            "proposal_id": "",
            "proposal_created": False,
            "workspace_prepared": False,
            "provider_contacted": False,
            "source_modified": False,
            "authority_granted": False,
        }
        row["initiative_digest"] = _digest({key: value for key, value in row.items() if key != "initiative_digest"})
        state["records"] = (state["records"] + [row])[-MAX_RECORDS:]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = now
        write_json_atomic(path, state, expected_type=dict, sort_keys=True)
        return {"ok": True, "status": "supervised_initiative_queued", "initiative": deepcopy(row), "idempotent": False, "runtime_mutated": True}


def inspect_supervised_initiative_queue(runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = _load(runtime_root)
    records = state["records"]
    return {
        "ok": True,
        "status": "supervised_initiative_queue_ready",
        "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision") or 0),
        "record_count": len(records),
        "active_count": sum(row.get("lifecycle_state") in ACTIVE_STATES for row in records),
        "recent_records": deepcopy(records[-12:]),
        "controls": deepcopy(state.get("controls") or {}),
        "authority_boundary": deepcopy(state.get("authority_boundary") or {}),
        "runtime_mutated": False,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }


def update_supervised_initiative_lifecycle(
    candidate_id: str,
    evidence_digest: str,
    lifecycle_state: str,
    *,
    proposal_id: str = "",
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Bind one persisted proposal stage back to its exact initiative evidence."""

    allowed = ACTIVE_STATES | {"operator_installed"}
    if lifecycle_state not in allowed:
        return {"ok": False, "status": "initiative_lifecycle_state_invalid", "runtime_mutated": False}
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        state = _load(runtime_root)
        row = next(
            (
                value
                for value in reversed(state["records"])
                if str(value.get("candidate_id") or "") == str(candidate_id or "")
                and str(value.get("evidence_digest") or "") == str(evidence_digest or "")
            ),
            None,
        )
        if not row:
            return {"ok": False, "status": "initiative_evidence_not_found", "runtime_mutated": False}
        if row.get("lifecycle_state") == lifecycle_state and (
            not proposal_id or row.get("proposal_id") == proposal_id
        ):
            return {
                "ok": True,
                "status": "initiative_lifecycle_reused",
                "initiative": deepcopy(row),
                "runtime_mutated": False,
            }
        if row.get("lifecycle_state") in TERMINAL_STATES:
            return {
                "ok": False,
                "status": "initiative_lifecycle_terminal",
                "initiative": deepcopy(row),
                "runtime_mutated": False,
            }
        now = _now()
        row["lifecycle_state"] = lifecycle_state
        row["updated_at"] = now
        if proposal_id:
            row["proposal_id"] = proposal_id
            row["proposal_created"] = True
        row["workspace_prepared"] = lifecycle_state in {
            "workspace_prepared",
            "implementation_running",
            "candidate_ready_for_review",
            "implementation_blocked",
            "operator_installed",
        }
        row["source_modified"] = lifecycle_state == "operator_installed"
        row["history"] = list(row.get("history") or ()) + [
            {"event": lifecycle_state, "occurred_at": now, "content_free": True}
        ]
        row["initiative_digest"] = _digest({key: value for key, value in row.items() if key != "initiative_digest"})
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = now
        write_json_atomic(path, state, expected_type=dict, sort_keys=True)
        return {
            "ok": True,
            "status": f"initiative_{lifecycle_state}",
            "initiative": deepcopy(row),
            "runtime_mutated": True,
            "provider_contacted": False,
            "authority_granted": False,
        }


def reconcile_supervised_initiative_queue(runtime_root: str | Path | None = None) -> dict[str, Any]:
    """Refresh initiative state from content-free persisted proposal receipts."""

    root = _runtime_root(runtime_root)
    proposals = root / "self_development_proposals"
    reconciled: list[str] = []
    state_map = {
        "awaiting_operator_isolated_preparation": "proposal_created",
        "isolated_workspace_prepared": "workspace_prepared",
        "isolated_implementation_running": "implementation_running",
        "isolated_implementation_review_ready": "candidate_ready_for_review",
        "isolated_implementation_blocked": "implementation_blocked",
        "operator_installed": "operator_installed",
    }
    for proposal_path in sorted(proposals.glob("improvement-*.json")):
        proposal = load_json_file(proposal_path, {}, expected_type=dict)
        candidate_id = str(proposal.get("dynamic_candidate_id") or "")
        evidence_digest = str(proposal.get("evidence_digest") or "")
        lifecycle_state = state_map.get(str(proposal.get("state") or ""))
        if not candidate_id or not evidence_digest or not lifecycle_state:
            continue
        updated = update_supervised_initiative_lifecycle(
            candidate_id,
            evidence_digest,
            lifecycle_state,
            proposal_id=str(proposal.get("proposal_id") or ""),
            runtime_root=root,
        )
        if updated.get("runtime_mutated"):
            reconciled.append(str(proposal.get("proposal_id") or ""))
    return {
        "ok": True,
        "status": "supervised_initiative_reconciled",
        "reconciled_count": len(reconciled),
        "proposal_ids": reconciled,
        "initiative_queue": inspect_supervised_initiative_queue(root),
        "provider_contacted": False,
        "authority_granted": False,
    }


def _control_response(action: str, row: Mapping[str, Any]) -> str:
    title = str((row.get("selected") or {}).get("title") or row.get("candidate_id") or "the initiative")
    if action == "defer":
        return f"I deferred {title}. It remains in history but is no longer active. No proposal or implementation was created."
    if action == "dismiss":
        return f"I dismissed {title}. I will exclude this exact evidence from the next shortlist unless the source evidence changes."
    phrase = f"Create dynamic self-development proposal {row.get('candidate_id')} evidence {str(row.get('evidence_digest') or '')[:16]}."
    return f"I advanced {title} to proposal review. No proposal or workspace was created. To create the exact supervised proposal, say: {phrase}"


def control_supervised_initiative(
    action: str,
    initiative_id: str,
    supplied_digest: str,
    *,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    action = str(action or "").lower()
    target_state = {"defer": "deferred", "dismiss": "dismissed", "advance": "ready_for_proposal_review"}.get(action)
    if not target_state:
        return {"active": True, "ok": False, "status": "unsupported_initiative_control", "conversation_response": "That initiative control is unsupported."}
    path = _path(runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=10):
        state = _load(runtime_root)
        row = next((value for value in state["records"] if value.get("initiative_id") == initiative_id), None)
        if not row:
            return {"active": True, "ok": False, "status": "initiative_not_found", "conversation_response": "That supervised initiative was not found. Nothing changed."}
        if str(row.get("initiative_digest") or "")[:16].lower() != str(supplied_digest or "").lower():
            return {"active": True, "ok": False, "status": "initiative_digest_mismatch", "conversation_response": "That initiative digest is stale or mismatched. Nothing changed."}
        if row.get("lifecycle_state") == target_state:
            return {"active": True, "ok": True, "status": "initiative_control_reused", "initiative": deepcopy(row), "conversation_response": _control_response(action, row), "runtime_mutated": False}
        current_state = str(row.get("lifecycle_state") or "")
        dismissible_review_states = {
            "ready_for_proposal_review",
            "proposal_created",
            "workspace_prepared",
            "candidate_ready_for_review",
            "implementation_blocked",
        }
        if current_state != "queued" and not (action == "dismiss" and current_state in dismissible_review_states):
            return {"active": True, "ok": False, "status": "initiative_control_state_blocked", "conversation_response": f"That initiative is already {row.get('lifecycle_state')}. Nothing changed."}
        now = _now()
        row["lifecycle_state"] = target_state
        row["updated_at"] = now
        row["history"] = list(row.get("history") or ()) + [{"event": target_state, "occurred_at": now, "content_free": True}]
        row["initiative_digest"] = _digest({key: value for key, value in row.items() if key != "initiative_digest"})
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = now
        write_json_atomic(path, state, expected_type=dict, sort_keys=True)
        return {"active": True, "ok": True, "status": f"initiative_{target_state}", "initiative": deepcopy(row), "conversation_response": _control_response(action, row), "runtime_mutated": True, "provider_contacted": False, "source_modified": False, "authority_granted": False}


def process_supervised_initiative_control(user_text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    if _SHOW.fullmatch(text):
        queue = inspect_supervised_initiative_queue(runtime_root)
        active = next((row for row in reversed(queue["recent_records"]) if row.get("lifecycle_state") in ACTIVE_STATES), None)
        if active:
            selected = dict(active.get("selected") or {})
            response = (
                f"One supervised initiative is queued: {selected.get('title')}. {selected.get('reason')} "
                f"Initiative {active.get('initiative_id')} digest {str(active.get('initiative_digest') or '')[:16]}. "
                "No proposal, workspace, provider request, or source change has occurred."
            )
        else:
            response = "The supervised initiative queue has no active item. Historical deferred, dismissed, and advanced records remain available for review."
        return {"active": True, "ok": True, "status": queue["status"], "initiative_queue": queue, "conversation_response": response, "runtime_mutated": False, "provider_contacted": False, "source_modified": False, "authority_granted": False}
    match = _CONTROL.fullmatch(text)
    if not match:
        return {"active": False}
    return control_supervised_initiative(match.group("action"), match.group("initiative_id").lower(), match.group("digest").lower(), runtime_root=runtime_root)


def supervised_initiative_response(shortlist: Mapping[str, Any], queued: Mapping[str, Any]) -> str:
    rows = [dict(row) for row in shortlist.get("shortlist") or ()]
    if not rows:
        return "I found no distinct evidence-backed initiative that clears the current quality and risk boundaries. I left the queue unchanged."
    lines = ["I narrowed the current source evidence to three distinct improvements:"]
    for index, row in enumerate(rows, 1):
        lines.append(f"{index}. {row.get('title')}: {row.get('description')} {row.get('reason')}")
    initiative = dict(queued.get("initiative") or {})
    selected = dict(initiative.get("selected") or rows[0])
    if queued.get("status") == "existing_supervised_initiative_retained":
        lines.append(f"I kept the existing queued initiative, {selected.get('title')}, instead of silently replacing active work.")
    else:
        lines.append(
            f"I selected {selected.get('title')} because it has the strongest combined value, evidence quality, novelty, effort fit, and bounded risk."
        )
    lines.append(
        f"It is queued as {initiative.get('initiative_id')} with digest {str(initiative.get('initiative_digest') or '')[:16]}. "
        "This is initiative state only: no development proposal, approval, workspace, provider request, command, test, or source change occurred."
    )
    if selected.get("structural_only"):
        lines.append(
            "Its demonstrated benefit is bounded maintainability and regression-risk reduction, not a proven new user capability. "
            f"Acceptance requires: {', '.join(selected.get('acceptance_criteria') or ())}."
        )
    if int(shortlist.get("unbound_priority_evidence_count") or 0):
        lines.append(
            f"{int(shortlist.get('unbound_priority_evidence_count') or 0)} higher-impact evidence record(s) remain visible but are not yet bound to an implementable candidate; I did not pretend they were executable."
        )
    lines.append(
        f"You can inspect the queue, defer supervised initiative {initiative.get('initiative_id')} digest {str(initiative.get('initiative_digest') or '')[:16]}, "
        f"dismiss it, or advance it to proposal review."
    )
    return "\n".join(lines)


__all__ = [
    "CONTRACT_VERSION",
    "build_supervised_initiative_shortlist",
    "queue_supervised_initiative",
    "inspect_supervised_initiative_queue",
    "update_supervised_initiative_lifecycle",
    "reconcile_supervised_initiative_queue",
    "control_supervised_initiative",
    "process_supervised_initiative_control",
    "supervised_initiative_response",
]
