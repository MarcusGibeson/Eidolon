from __future__ import annotations

"""Content-free v1198.2 feature-freeze and architecture-consolidation foundations.

The contract validates caller-supplied architecture inventory, freeze declarations,
ownership, duplication, startup-cost, and consolidation evidence. It performs no
file move, module merge, deletion, import rewrite, startup execution, installation,
release, or authority expansion.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1198.2"
ARCHITECTURE_AREAS = (
    "conversation", "cognition", "reasoning", "planning", "campaigns", "approvals",
    "actions", "results", "learning", "queues", "evidence", "verification",
)
FREEZE_STATES = ("frozen", "exception_review_required", "deferred_debt")
CONSOLIDATION_KINDS = ("canonical_owner", "exact_duplicate", "partial_overlap", "startup_hotspot")
DISPOSITIONS = ("retain", "alias_candidate", "merge_candidate", "defer")
PRIVATE_TOKENS = (
    "prompt", "conversation_text", "message", "memory_content", "secret", "password",
    "token_value", "raw_source", "source_text", "patch", "stdout", "stderr",
    "provider_payload", "private_reasoning", "credential", "api_key",
)
MAX_COMPONENTS = 64
MAX_CANDIDATES = 64
MAX_STARTUP_MS = 120_000


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def _private_fields(value: object, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in PRIVATE_TOKENS):
                found.append(label)
            found.extend(_private_fields(item, label))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(_private_fields(item, f"{prefix}[{index}]"))
    return sorted(set(found))


def create_freeze_plan(*, plan_id: str, snapshot_digest: str, context_digest: str, baseline_version: str,
                       architecture_digest: str, purpose_code: str, max_components: int = 32,
                       max_candidates: int = 32, startup_budget_ms: int = 30_000) -> dict[str, Any]:
    plan = {
        "contract_version": CONTRACT_VERSION, "plan_id": str(plan_id),
        "snapshot_digest": str(snapshot_digest), "context_digest": str(context_digest),
        "baseline_version": str(baseline_version), "architecture_digest": str(architecture_digest),
        "purpose_code": str(purpose_code), "max_components": max_components,
        "max_candidates": max_candidates, "startup_budget_ms": startup_budget_ms,
        "content_free": True, "read_only": True, "feature_freeze_active": True,
        "new_feature_authorized": False, "exception_approved": False,
        "files_moved": False, "modules_merged": False, "files_deleted": False,
        "imports_rewritten": False, "startup_executed": False, "runtime_mutated": False,
        "source_modified": False, "approval_created": False, "approval_consumed": False,
        "provider_contacted": False, "model_contacted": False, "process_started": False,
        "thread_started": False, "installation_performed": False, "promotion_performed": False,
        "certification_performed": False, "publication_performed": False,
        "release_performed": False, "automatic_continuation": False,
        "authority_state": "separate_not_granted",
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def create_component(*, component_id: str, area: str, owner: str, sequence: int,
                     snapshot_digest: str, context_digest: str, module_digest: str,
                     interface_digest: str, dependency_digest: str, startup_cost_ms: int,
                     freeze_state: str = "frozen", purpose_code: str = "architecture_inventory") -> dict[str, Any]:
    row = {
        "contract_version": CONTRACT_VERSION, "component_id": str(component_id), "area": str(area),
        "owner": str(owner), "sequence": sequence, "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest), "module_digest": str(module_digest),
        "interface_digest": str(interface_digest), "dependency_digest": str(dependency_digest),
        "startup_cost_ms": startup_cost_ms, "freeze_state": str(freeze_state),
        "purpose_code": str(purpose_code), "content_free": True, "read_only": True,
        "feature_added": False, "file_moved": False, "module_merged": False,
        "file_deleted": False, "import_rewritten": False, "startup_executed": False,
        "runtime_mutated": False, "source_modified": False, "authority_state": "separate_not_granted",
    }
    row["component_digest"] = _digest(row)
    return row


def create_consolidation_candidate(*, candidate_id: str, kind: str, disposition: str,
                                  canonical_component_id: str, related_component_ids: Sequence[str],
                                  sequence: int, evidence_digest: str, purpose_code: str) -> dict[str, Any]:
    row = {
        "contract_version": CONTRACT_VERSION, "candidate_id": str(candidate_id), "kind": str(kind),
        "disposition": str(disposition), "canonical_component_id": str(canonical_component_id),
        "related_component_ids": [str(item) for item in related_component_ids], "sequence": sequence,
        "evidence_digest": str(evidence_digest), "purpose_code": str(purpose_code),
        "content_free": True, "read_only": True, "files_moved": False, "modules_merged": False,
        "files_deleted": False, "imports_rewritten": False, "startup_executed": False,
        "runtime_mutated": False, "source_modified": False, "authority_state": "separate_not_granted",
    }
    row["candidate_digest"] = _digest(row)
    return row


def assess_feature_freeze_architecture(plan: Mapping[str, Any], components: Sequence[Mapping[str, Any]],
                                       candidates: Sequence[Mapping[str, Any]], *,
                                       current_snapshot_digest: str, current_context_digest: str,
                                       verification_summary: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    p = dict(plan); rows = [dict(row) for row in components]; work = [dict(row) for row in candidates]
    verification = dict(verification_summary)
    errors.extend(f"private_field:{field}" for field in _private_fields({"plan": p, "components": rows, "candidates": work, "verification": verification}))
    unsigned = dict(p); supplied = unsigned.pop("plan_digest", None)
    if supplied != _digest(unsigned): errors.append("plan_tamper")
    if p.get("contract_version") != CONTRACT_VERSION: errors.append("unsupported_plan_contract")
    for field in ("snapshot_digest", "context_digest", "architecture_digest"):
        if not _is_digest(p.get(field)): errors.append(f"malformed_plan_{field}")
    if p.get("snapshot_digest") != current_snapshot_digest: errors.append("stale_plan_snapshot")
    if p.get("context_digest") != current_context_digest: errors.append("stale_plan_context")
    if not str(p.get("plan_id") or ""): errors.append("missing_plan_id")
    if not str(p.get("baseline_version") or ""): errors.append("missing_baseline_version")
    for field, maximum in (("max_components", MAX_COMPONENTS), ("max_candidates", MAX_CANDIDATES), ("startup_budget_ms", MAX_STARTUP_MS)):
        value = p.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > maximum: errors.append(f"malformed_{field}")
    if len(rows) > int(p.get("max_components") or 0): errors.append("oversized_component_inventory")
    if len(work) > int(p.get("max_candidates") or 0): errors.append("oversized_candidate_inventory")
    if p.get("content_free") is not True or p.get("read_only") is not True or p.get("feature_freeze_active") is not True: errors.append("freeze_contract_loss")
    forbidden = ("new_feature_authorized", "exception_approved", "files_moved", "modules_merged", "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified", "approval_created", "approval_consumed", "provider_contacted", "model_contacted", "process_started", "thread_started", "installation_performed", "promotion_performed", "certification_performed", "publication_performed", "release_performed", "automatic_continuation")
    for field in forbidden:
        if p.get(field) is not False: errors.append(f"plan_forbidden_claim:{field}")
    if p.get("authority_state") != "separate_not_granted": errors.append("plan_authority_expansion")

    ids: list[str] = []; sequences: list[int] = []; owners: set[str] = set(); areas: set[str] = set(); startup_total = 0
    for index, row in enumerate(rows):
        unsigned_row = dict(row); supplied_row = unsigned_row.pop("component_digest", None)
        if supplied_row != _digest(unsigned_row): errors.append(f"component_tamper:{index}")
        if row.get("contract_version") != CONTRACT_VERSION: errors.append(f"unsupported_component_contract:{index}")
        if row.get("snapshot_digest") != current_snapshot_digest: errors.append(f"stale_component_snapshot:{index}")
        if row.get("context_digest") != current_context_digest: errors.append(f"stale_component_context:{index}")
        for field in ("module_digest", "interface_digest", "dependency_digest"):
            if not _is_digest(row.get(field)): errors.append(f"malformed_component_{field}:{index}")
        component_id = str(row.get("component_id") or ""); ids.append(component_id)
        if not component_id: errors.append(f"missing_component_id:{index}")
        if row.get("area") not in ARCHITECTURE_AREAS: errors.append(f"unsupported_area:{index}")
        else: areas.add(str(row.get("area")))
        owner = str(row.get("owner") or ""); owners.add(owner)
        if not owner: errors.append(f"missing_owner:{index}")
        seq = row.get("sequence"); sequences.append(seq if isinstance(seq, int) and not isinstance(seq, bool) else -1)
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1: errors.append(f"malformed_sequence:{index}")
        cost = row.get("startup_cost_ms")
        if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0 or cost > MAX_STARTUP_MS: errors.append(f"malformed_startup_cost:{index}")
        else: startup_total += cost
        if row.get("freeze_state") not in FREEZE_STATES: errors.append(f"unsupported_freeze_state:{index}")
        for field in ("feature_added", "file_moved", "module_merged", "file_deleted", "import_rewritten", "startup_executed", "runtime_mutated", "source_modified"):
            if row.get(field) is not False: errors.append(f"component_forbidden_claim:{field}:{index}")
        if row.get("content_free") is not True or row.get("read_only") is not True: errors.append(f"component_boundary_loss:{index}")
        if row.get("authority_state") != "separate_not_granted": errors.append(f"component_authority_expansion:{index}")
    if len(ids) != len(set(ids)): errors.append("duplicate_component_id")
    if len(sequences) != len(set(sequences)): errors.append("duplicate_component_sequence")
    if sequences and sequences != list(range(1, len(sequences) + 1)): errors.append("non_contiguous_component_sequence")
    if startup_total > int(p.get("startup_budget_ms") or 0): errors.append("startup_budget_exceeded")

    candidate_ids: list[str] = []; candidate_sequences: list[int] = []
    known = set(ids)
    for index, row in enumerate(work):
        unsigned_row = dict(row); supplied_row = unsigned_row.pop("candidate_digest", None)
        if supplied_row != _digest(unsigned_row): errors.append(f"candidate_tamper:{index}")
        if row.get("contract_version") != CONTRACT_VERSION: errors.append(f"unsupported_candidate_contract:{index}")
        cid = str(row.get("candidate_id") or ""); candidate_ids.append(cid)
        seq = row.get("sequence"); candidate_sequences.append(seq if isinstance(seq, int) and not isinstance(seq, bool) else -1)
        if row.get("kind") not in CONSOLIDATION_KINDS: errors.append(f"unsupported_candidate_kind:{index}")
        if row.get("disposition") not in DISPOSITIONS: errors.append(f"unsupported_disposition:{index}")
        canonical = str(row.get("canonical_component_id") or "")
        related = [str(item) for item in row.get("related_component_ids") or []]
        if canonical not in known: errors.append(f"unknown_canonical_component:{index}")
        if not related or any(item not in known for item in related): errors.append(f"unknown_related_component:{index}")
        if canonical in related: errors.append(f"canonical_in_related:{index}")
        if len(related) != len(set(related)): errors.append(f"duplicate_related_component:{index}")
        if not _is_digest(row.get("evidence_digest")): errors.append(f"malformed_candidate_evidence_digest:{index}")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1: errors.append(f"malformed_candidate_sequence:{index}")
        for field in ("files_moved", "modules_merged", "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified"):
            if row.get(field) is not False: errors.append(f"candidate_forbidden_claim:{field}:{index}")
        if row.get("content_free") is not True or row.get("read_only") is not True: errors.append(f"candidate_boundary_loss:{index}")
        if row.get("authority_state") != "separate_not_granted": errors.append(f"candidate_authority_expansion:{index}")
    if len(candidate_ids) != len(set(candidate_ids)): errors.append("duplicate_candidate_id")
    if len(candidate_sequences) != len(set(candidate_sequences)): errors.append("duplicate_candidate_sequence")
    if candidate_sequences and candidate_sequences != list(range(1, len(candidate_sequences) + 1)): errors.append("non_contiguous_candidate_sequence")
    if verification.get("current_regressions_separate") is not True: errors.append("verification_boundary_loss")
    if verification.get("inherited_debt_visible") is not True: errors.append("inherited_debt_hidden")
    if verification.get("global_profile_pass_claimed") is not False: errors.append("false_global_profile_claim")

    status = "ready_for_operator_review" if not errors else "blocked"
    result = {
        "contract_version": CONTRACT_VERSION, "status": status, "errors": sorted(set(errors)),
        "component_count": len(rows), "candidate_count": len(work), "area_count": len(areas),
        "owner_count": len(owners), "startup_total_ms": startup_total,
        "startup_budget_ms": p.get("startup_budget_ms"), "feature_freeze_active": True,
        "architecture_ownership_explicit": bool(rows) and all(str(row.get("owner") or "") for row in rows),
        "duplicate_visibility_preserved": True, "historical_truth_preserved": True,
        "current_regressions_separate": verification.get("current_regressions_separate") is True,
        "inherited_debt_visible": verification.get("inherited_debt_visible") is True,
        "content_free": True, "read_only": True, "files_moved": False, "modules_merged": False,
        "files_deleted": False, "imports_rewritten": False, "startup_executed": False,
        "runtime_mutated": False, "source_modified": False, "new_feature_authorized": False,
        "exception_approved": False, "approval_created": False, "approval_consumed": False,
        "provider_contacted": False, "model_contacted": False, "process_started": False,
        "thread_started": False, "installation_performed": False, "promotion_performed": False,
        "certification_performed": False, "publication_performed": False,
        "release_performed": False, "automatic_continuation": False,
        "global_profile_pass_claimed": False, "authority_state": "separate_not_granted",
    }
    result["assessment_digest"] = _digest(result)
    return result


def public_feature_freeze_summary(assessment: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "contract_version", "status", "component_count", "candidate_count", "area_count", "owner_count",
        "startup_total_ms", "startup_budget_ms", "feature_freeze_active", "architecture_ownership_explicit",
        "duplicate_visibility_preserved", "historical_truth_preserved", "current_regressions_separate",
        "inherited_debt_visible", "content_free", "read_only", "files_moved", "modules_merged",
        "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified",
        "new_feature_authorized", "exception_approved", "approval_created", "approval_consumed",
        "provider_contacted", "model_contacted", "process_started", "thread_started",
        "installation_performed", "promotion_performed", "certification_performed",
        "publication_performed", "release_performed", "automatic_continuation",
        "global_profile_pass_claimed", "authority_state", "assessment_digest",
    )
    return {key: assessment.get(key) for key in keys}
