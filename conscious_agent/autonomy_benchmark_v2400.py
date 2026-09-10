from __future__ import annotations

"""Portable v2500 benchmark-preparation and autonomy-boundary contracts."""

import hashlib
import json
from typing import Any, Mapping, Sequence

from release_authority import WORKING_SOURCE_VERSION, MILESTONE

CONTRACT_VERSION = "v2499.9"
AUTONOMY_LEVELS = {"independent", "review_required", "prohibited"}
DEFAULT_AUTONOMY_MATRIX = {
    "inspect_source": "independent",
    "inspect_runtime_health": "independent",
    "prepare_read_only_research_plan": "independent",
    "prepare_isolated_development_ticket": "independent",
    "prepare_review_ready_candidate": "review_required",
    "execute_local_tool": "review_required",
    "contact_provider_for_new_external_action": "review_required",
    "install_candidate": "review_required",
    "promote_candidate": "review_required",
    "modify_private_memory_without_owner": "prohibited",
    "read_secrets_without_explicit_scope": "prohibited",
    "destructive_operation_without_explicit_authority": "prohibited",
    "expand_own_authority": "prohibited",
    "manage_models_without_explicit_operator_decision": "prohibited",
}

_DENIED = {
    "benchmark_certified": False,
    "native_evidence_collected": False,
    "operator_benchmark_completed": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> bool:
    s = str(value or "").lower(); return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _safe_code(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or len(text) > 160:
        return None
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
    return text if all(ch in allowed for ch in text) else None


def build_autonomy_matrix(overrides: Mapping[str, str] | None = None) -> dict[str, Any]:
    matrix = dict(DEFAULT_AUTONOMY_MATRIX)
    errors = []
    for action, level in dict(overrides or {}).items():
        action = str(action or "").strip(); level = str(level or "").strip().lower()
        if action not in matrix or level not in AUTONOMY_LEVELS:
            errors.append("unsupported_autonomy_override"); continue
        # Browser preparation can only make an existing action more restrictive.
        order = {"independent": 2, "review_required": 1, "prohibited": 0}
        if order[level] > order[matrix[action]]:
            errors.append("authority_expansion_override_rejected"); continue
        matrix[action] = level
    result = {
        "ok": not errors, "status": "autonomy_matrix_ready" if not errors else "autonomy_matrix_restricted_with_errors",
        "contract_version": CONTRACT_VERSION, "matrix": matrix, "errors": sorted(set(errors)),
        "matrix_is_benchmark_description_only": True, "matrix_does_not_change_live_authority": True,
        "content_free": True, **_DENIED,
    }
    result["matrix_digest"] = _digest(result); return result


def freeze_benchmark_claims(
    *, source_manifest_digest: str, capability_claims: Sequence[Mapping[str, Any]],
    known_limitations: Sequence[str], deferred_local_evidence: Sequence[str],
) -> dict[str, Any]:
    if not _hex64(source_manifest_digest):
        return {"ok": False, "status": "benchmark_claim_freeze_blocked", "reason": "invalid_source_manifest_digest", "content_free": True, **_DENIED}
    claims = []; rejected = 0; seen_claim_codes: set[str] = set(); seen_evidence: set[str] = set()
    for row in capability_claims:
        if not isinstance(row, Mapping): rejected += 1; continue
        code = _safe_code(row.get("claim_code")); evidence = str(row.get("evidence_digest") or "").lower(); status = str(row.get("status") or "").lower()
        if (
            code is None or not _hex64(evidence) or status not in {"verified_portable", "deferred_native", "known_limit"}
            or code in seen_claim_codes or evidence in seen_evidence
        ):
            rejected += 1; continue
        seen_claim_codes.add(code); seen_evidence.add(evidence)
        claims.append({"claim_code": code, "status": status, "evidence_digest": evidence})
    safe_limits = sorted(set(code for x in known_limitations if (code := _safe_code(x))))[:128]
    safe_deferred = sorted(set(code for x in deferred_local_evidence if (code := _safe_code(x))))[:128]
    rejected_inventory = len(list(known_limitations)) + len(list(deferred_local_evidence)) - len(safe_limits) - len(safe_deferred)
    all_valid = rejected == 0 and rejected_inventory == 0
    result = {
        "ok": all_valid, "status": "benchmark_claims_frozen" if all_valid else "benchmark_claims_frozen_with_rejections",
        "contract_version": CONTRACT_VERSION, "working_source_version": WORKING_SOURCE_VERSION, "milestone": MILESTONE,
        "source_manifest_digest": str(source_manifest_digest).lower(), "claims": sorted(claims, key=lambda x: x["claim_code"]),
        "rejected_claim_count": rejected,
        "rejected_inventory_text_count": rejected_inventory,
        "known_limitations": safe_limits,
        "deferred_local_evidence": safe_deferred,
        "browser_cannot_certify_native_claims": True, "claims_are_frozen_for_gate_review": True,
        "content_free": True, **_DENIED,
    }
    result["claim_freeze_digest"] = _digest(result); return result


def build_benchmark_fixture(*, fixture_id: str, scenario_codes: Sequence[str], expected_boundary_codes: Sequence[str]) -> dict[str, Any]:
    safe_fixture_id = _safe_code(fixture_id)
    raw_scenarios = list(scenario_codes); raw_boundaries = list(expected_boundary_codes)
    scenarios = sorted(set(code for x in raw_scenarios if (code := _safe_code(x))))
    boundaries = sorted(set(code for x in raw_boundaries if (code := _safe_code(x))))
    if (
        safe_fixture_id is None or not scenarios or not boundaries
        or len(scenarios) != len(raw_scenarios) or len(boundaries) != len(raw_boundaries)
    ):
        return {"ok": False, "status": "benchmark_fixture_blocked", "content_free": True, **_DENIED}
    result = {
        "ok": True, "status": "deterministic_benchmark_fixture_ready", "fixture_id": safe_fixture_id,
        "scenario_codes": scenarios, "expected_boundary_codes": boundaries,
        "privacy_safe_no_prompt_or_response_content": True, "deterministic": True,
        "content_free": True, **_DENIED,
    }
    result["fixture_digest"] = _digest(result); return result


def score_portable_benchmark(*, fixture: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fd = str(fixture.get("fixture_digest") or ""); unsigned = dict(fixture); unsigned.pop("fixture_digest", None)
    if not fixture.get("ok") or not _hex64(fd) or fd != _digest(unsigned):
        return {"ok": False, "status": "portable_benchmark_blocked", "reason": "fixture_invalid_or_tampered", "content_free": True, **_DENIED}
    expected = set(fixture.get("scenario_codes") or []); seen = set(); passed = 0; malformed = 0
    for row in outcomes:
        if not isinstance(row, Mapping): malformed += 1; continue
        code = str(row.get("scenario_code") or ""); evidence = str(row.get("evidence_digest") or "")
        if code not in expected or code in seen or not _hex64(evidence) or not isinstance(row.get("passed"), bool): malformed += 1; continue
        seen.add(code); passed += int(bool(row.get("passed")))
    total = len(expected); complete = seen == expected and malformed == 0
    result = {
        "ok": complete, "status": "portable_benchmark_scored" if complete else "portable_benchmark_incomplete",
        "fixture_digest": fd, "scenario_count": total, "evidenced_scenario_count": len(seen), "passed_count": passed,
        "pass_rate": round(passed / total, 6) if total else 0.0, "malformed_outcome_count": malformed,
        "native_certification_required": True, "content_free": True, **_DENIED,
    }
    result["score_digest"] = _digest(result); return result


def assemble_v2500_gate_packet(
    *, claim_freeze: Mapping[str, Any], autonomy_matrix: Mapping[str, Any],
    portable_score: Mapping[str, Any], release_packet_digest: str,
) -> dict[str, Any]:
    cf = str(claim_freeze.get("claim_freeze_digest") or ""); am = str(autonomy_matrix.get("matrix_digest") or ""); ps = str(portable_score.get("score_digest") or "")
    cf_unsigned = dict(claim_freeze); cf_unsigned.pop("claim_freeze_digest", None)
    am_unsigned = dict(autonomy_matrix); am_unsigned.pop("matrix_digest", None)
    ps_unsigned = dict(portable_score); ps_unsigned.pop("score_digest", None)
    valid_inputs = (
        _hex64(cf) and cf == _digest(cf_unsigned)
        and _hex64(am) and am == _digest(am_unsigned)
        and _hex64(ps) and ps == _digest(ps_unsigned)
        and _hex64(release_packet_digest)
        and claim_freeze.get("ok") is True and claim_freeze.get("status") == "benchmark_claims_frozen"
        and autonomy_matrix.get("ok") is True and autonomy_matrix.get("status") == "autonomy_matrix_ready"
        and portable_score.get("ok") is True and portable_score.get("status") == "portable_benchmark_scored"
    )
    if not valid_inputs:
        return {"ok": False, "status": "v2500_gate_packet_blocked", "content_free": True, **_DENIED}
    result = {
        "ok": True, "status": "v2500_desktop_gate_packet_ready", "contract_version": CONTRACT_VERSION,
        "claim_freeze_digest": cf, "autonomy_matrix_digest": am, "portable_score_digest": ps,
        "release_packet_digest": str(release_packet_digest).lower(),
        "required_desktop_evidence": [
            "native_windows_long_soak", "sleep_resume_and_network_loss", "native_provider_latency_and_failure",
            "operator_daily_use_trial", "held_out_native_projects", "installer_upgrade_rollback",
            "accessibility_multi_monitor_remote_phone_if_in_scope", "privacy_and_authority_adversarial_campaign",
        ],
        "operator_decision_required": True, "next_research_roadmap_required": True,
        "content_free": True, **_DENIED,
    }
    result["gate_packet_digest"] = _digest(result); return result


__all__ = [
    "CONTRACT_VERSION", "DEFAULT_AUTONOMY_MATRIX", "build_autonomy_matrix", "freeze_benchmark_claims",
    "build_benchmark_fixture", "score_portable_benchmark", "assemble_v2500_gate_packet",
]
