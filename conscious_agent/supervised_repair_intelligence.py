from __future__ import annotations

"""Portable v1551-v1575 failure taxonomy and bounded repair policy.

The policy classifies content-free isolated-development failures and determines
whether the existing proposal may receive another workspace-only attempt.  It
never creates installation authority, changes the active source tree, or
expands the proposal allowlist.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v1575.9"
FAILURE_TAXONOMY_VERSION = "v1558.9"
BOUNDED_REPAIR_VERSION = "v1566.9"
RECOVERY_CHECKPOINT_VERSION = "v1575.9"
MAX_REPAIR_CYCLES = 2

FAILURE_CLASSES = (
    "syntax",
    "import",
    "test",
    "timeout",
    "stale_baseline",
    "scope",
    "dependency",
    "provider",
    "acceptance_criterion",
    "security_or_authority",
    "unknown",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def classify_failure_code(code: str) -> str:
    token = re.sub(r"[^a-z0-9_.:-]+", "_", str(code or "").strip().lower())[:180]
    if any(key in token for key in ("authority", "secret", "credential", "private_path", "path_traversal")):
        return "security_or_authority"
    if any(key in token for key in ("stale", "source_changed", "candidate_changed", "manifest_mismatch")):
        return "stale_baseline"
    if any(key in token for key in ("timeout", "timed_out")):
        return "timeout"
    if any(key in token for key in ("syntax", "compile", "ast_", "indentation")):
        return "syntax"
    if any(key in token for key in ("import", "modulenotfound", "module_not_found", "no_module_named")):
        return "import"
    if any(key in token for key in ("verification", "test_", "check_", "assertion", "pytest")):
        return "test"
    if any(key in token for key in ("scope", "allowlist", "allowed_path", "outside_workspace", "changed_file_limit")):
        return "scope"
    if any(key in token for key in ("dependency", "package", "executable", "toolchain", "lockfile")):
        return "dependency"
    if any(key in token for key in ("provider", "model", "output_not_json", "provider_output")):
        return "provider"
    if any(key in token for key in ("acceptance", "no_manifest_change", "produced_no_manifest_change", "expected_behavior")):
        return "acceptance_criterion"
    return "unknown"


def failure_taxonomy_contract() -> dict[str, Any]:
    contract = {
        "contract_version": FAILURE_TAXONOMY_VERSION,
        "failure_classes": list(FAILURE_CLASSES),
        "source_fields": ["implementation_blocker", "implementation_failure_codes"],
        "content_free_receipts": True,
        "private_provider_output_returned": False,
        "operator_guidance_required": True,
        "failure_does_not_grant_repair_authority": True,
        "failure_does_not_grant_installation_authority": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def build_failure_receipt(proposal: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id = str(proposal.get("proposal_id") or "")
    proposal_digest = str(proposal.get("proposal_digest") or "")
    raw_codes = [str(value or "")[:180] for value in list(proposal.get("implementation_failure_codes") or []) if str(value or "")]
    blocker = str(proposal.get("implementation_blocker") or "")[:180]
    if blocker and blocker not in raw_codes:
        raw_codes.append(blocker)
    classified = [
        {"failure_code_digest": _digest(code), "failure_class": classify_failure_code(code)}
        for code in raw_codes
    ]
    classes = sorted({row["failure_class"] for row in classified}) or ["unknown"]
    stable = {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "failure_count": len(raw_codes),
        "failure_classes": classes,
        "classified_failures": classified,
        "provider_request_count": max(0, int(proposal.get("provider_request_count") or 0)),
        "implementation_attempt_count": max(0, int(proposal.get("implementation_attempt_count") or 0)),
        "repair_cycle_count": max(0, int(proposal.get("repair_cycle_count") or 0)),
        "affected_scope_digest": _digest(sorted(str(v) for v in list(proposal.get("affected_scope") or []))),
        "private_failure_text_returned": False,
        "provider_payload_returned": False,
        "content_free": True,
    }
    stable["failure_receipt_digest"] = _digest(stable)
    return stable


def bounded_repair_contract() -> dict[str, Any]:
    contract = {
        "contract_version": BOUNDED_REPAIR_VERSION,
        "maximum_repair_cycles": MAX_REPAIR_CYCLES,
        "same_proposal_required": True,
        "same_proposal_digest_required": True,
        "same_workspace_lineage_required": True,
        "same_affected_scope_required": True,
        "scope_expansion_allowed": False,
        "active_source_mutation_allowed": False,
        "installation_allowed": False,
        "promotion_allowed": False,
        "provider_contact_in_browser_checkpoint": False,
        "retry_must_reverify": True,
        "exactly_once_attempt_counter": True,
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


def build_bounded_repair_plan(proposal: Mapping[str, Any]) -> dict[str, Any]:
    receipt = build_failure_receipt(proposal)
    classes = set(receipt["failure_classes"])
    used = max(0, int(proposal.get("repair_cycle_count") or 0))
    remaining = max(0, MAX_REPAIR_CYCLES - used)
    hard_block = bool(classes & {"security_or_authority", "scope"})
    stale = "stale_baseline" in classes
    dependency = "dependency" in classes
    retryable = bool(remaining and not hard_block)
    if hard_block:
        action = "operator_or_desktop_review_required"
    elif not remaining:
        action = "repair_budget_exhausted"
    elif stale:
        action = "refresh_disposable_workspace_then_reverify_same_scope"
    elif dependency:
        action = "retry_only_if_dependency_is_already_available_without_installation"
    else:
        action = "retry_same_workspace_scope_then_reverify"
    stable = {
        "proposal_id": receipt["proposal_id"],
        "proposal_digest": receipt["proposal_digest"],
        "failure_receipt_digest": receipt["failure_receipt_digest"],
        "repair_cycle_count": used,
        "maximum_repair_cycles": MAX_REPAIR_CYCLES,
        "remaining_repair_cycles": remaining,
        "retryable": retryable,
        "requires_workspace_refresh": stale,
        "requires_dependency_availability_check": dependency,
        "operator_or_desktop_review_required": hard_block,
        "next_action": action,
        "affected_scope_digest": receipt["affected_scope_digest"],
        "original_proposal_lineage_preserved": True,
        "scope_expansion_authorized": False,
        "active_source_mutation_authorized": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "content_free": True,
    }
    stable["repair_plan_digest"] = _digest(stable)
    return stable


def advance_repair_cycle(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return the next persisted repair accounting fields, or a fail-closed block."""
    plan = build_bounded_repair_plan(proposal)
    if not plan["retryable"]:
        return {"ok": False, "status": plan["next_action"], "repair_plan": plan, "content_free": True}
    next_count = int(plan["repair_cycle_count"]) + 1
    stable = {
        "repair_cycle_count": next_count,
        "repair_plan_digest": plan["repair_plan_digest"],
        "repair_failure_receipt_digest": plan["failure_receipt_digest"],
        "repair_scope_digest": plan["affected_scope_digest"],
        "repair_lineage_proposal_digest": plan["proposal_digest"],
    }
    return {"ok": True, "status": "bounded_repair_cycle_advanced", **stable, "content_free": True}


def validate_repair_lineage(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    same = {
        "proposal_id": str(before.get("proposal_id") or "") == str(after.get("proposal_id") or ""),
        "proposal_digest": str(before.get("proposal_digest") or "") == str(after.get("proposal_digest") or ""),
        "affected_scope": sorted(str(v) for v in list(before.get("affected_scope") or [])) == sorted(str(v) for v in list(after.get("affected_scope") or [])),
    }
    stable = {
        "ok": all(same.values()),
        "checks": same,
        "scope_expanded": not same["affected_scope"],
        "proposal_lineage_changed": not (same["proposal_id"] and same["proposal_digest"]),
        "active_source_mutation_authorized": False,
        "content_free": True,
    }
    stable["validation_digest"] = _digest(stable)
    return stable


def recovery_checkpoint_contract() -> dict[str, Any]:
    contract = {
        "contract_version": RECOVERY_CHECKPOINT_VERSION,
        "scenarios": [
            "interruption", "restart", "duplicate_retry", "provider_loss",
            "stale_source", "partial_files", "exhausted_repair_budget",
        ],
        "expected_properties": [
            "same_proposal_lineage", "same_scope", "bounded_attempts", "reverification",
            "active_source_unchanged", "installation_authority_unchanged",
        ],
        "native_windows_evidence_deferred": True,
        "content_free": True,
    }
    contract["contract_digest"] = _digest(contract)
    return contract


__all__ = [
    "CONTRACT_VERSION", "FAILURE_CLASSES", "MAX_REPAIR_CYCLES", "classify_failure_code",
    "failure_taxonomy_contract", "build_failure_receipt", "bounded_repair_contract",
    "build_bounded_repair_plan", "advance_repair_cycle", "validate_repair_lineage",
    "recovery_checkpoint_contract",
]
