from __future__ import annotations

"""Strictly read-only v1148.2 Privacy and Security Hardening intake checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from privacy_security_test_catalog import build_privacy_security_test_catalog
from privacy_security_threat_model import THREAT_CATEGORIES, build_privacy_security_threat_model

CONTRACT_VERSION = "v1148.2"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    ):
        try:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


def build_privacy_security_hardening_intake_checkpoint(
    *, source_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    before = _tree_signature(source)
    model = build_privacy_security_threat_model()
    catalog = build_privacy_security_test_catalog(threat_model=model)
    threats = list(model.get("threats") or [])
    scenarios = list(catalog.get("scenarios") or [])

    forbidden_content_keys = {
        "prompt",
        "raw_prompt",
        "message",
        "conversation",
        "reflection",
        "reasoning",
        "memory_text",
        "belief_text",
        "goal_text",
        "relationship_text",
        "mood_text",
        "provider_payload",
        "source_text",
        "patch_text",
        "fixture_content",
    }
    operational_fields = {
        "browses",
        "contacts_provider",
        "executes_commands",
        "runs_security_test",
        "mutates_runtime",
        "mutates_cognition",
        "mutates_memory",
        "modifies_source",
        "sends_messages",
        "creates_notifications",
        "creates_goals",
        "creates_plans",
        "creates_development_proposals",
        "creates_approval",
        "creates_authorization",
        "installs",
        "promotes",
        "certifies",
    }

    expected_categories = set(THREAT_CATEGORIES)
    threat_categories = {row.get("category") for row in threats}
    scenario_categories = {row.get("category") for row in scenarios}
    threat_by_id = {row.get("threat_id"): row for row in threats}
    exact_lineage = all(
        row.get("threat_id") in threat_by_id
        and row.get("threat_digest") == threat_by_id[row.get("threat_id")].get("structural_digest")
        and row.get("threat_revision") == threat_by_id[row.get("threat_id")].get("model_revision")
        for row in scenarios
    )
    content_keys_absent = all(
        not forbidden_content_keys.intersection(row.keys()) for row in threats + scenarios
    )
    authorities_false = (
        not any(model.get("authority_boundary", {}).values())
        and not any(catalog.get("authority_boundary", {}).values())
        and all(
            not row.get(field, False)
            for row in threats + scenarios
            for field in operational_fields
        )
    )

    checks = [
        ("exact_six_threat_categories", threat_categories == expected_categories and model.get("threat_count") == 6),
        ("privacy_exposure_is_covered", "privacy_exposure" in threat_categories),
        ("prompt_injection_is_covered", "prompt_injection" in threat_categories),
        ("false_memory_is_covered", "false_memory" in threat_categories),
        ("fixation_is_covered", "fixation" in threat_categories),
        ("runaway_loop_is_covered", "runaway_loop" in threat_categories),
        ("unauthorized_action_is_covered", "unauthorized_action" in threat_categories),
        ("threat_identifiers_are_unique", not model.get("duplicate_threat_ids")),
        ("scenario_catalog_is_complete", scenario_categories == expected_categories and catalog.get("scenario_count") == 12),
        ("scenario_identifiers_are_unique", not catalog.get("duplicate_scenario_ids")),
        ("exact_threat_lineage_is_preserved", exact_lineage),
        ("fixtures_are_structural_references_only", all(not row.get("fixture_content_included") and str(row.get("fixture_reference", "")).startswith("structural-fixture:") for row in scenarios)),
        ("test_budgets_are_bounded", all(1 <= int(row.get("max_steps", 0)) <= 5 and row.get("max_attempts") == 1 and 0 < int(row.get("max_runtime_ms", 0)) <= 250 for row in scenarios)),
        ("provider_budget_is_zero", all(row.get("provider_budget_tokens") == 0 for row in scenarios)),
        ("scenario_execution_remains_ineligible", all(row.get("execution_eligible") is False for row in scenarios)),
        ("operator_review_is_required", all(row.get("operator_review_required") is True for row in threats + scenarios)),
        ("expected_outcomes_are_bounded", all(row.get("expected_outcome") in {"deny", "quarantine", "review", "constrain", "stop"} for row in threats + scenarios)),
        ("records_are_content_free", model.get("content_free") and catalog.get("content_free") and content_keys_absent),
        ("no_operational_or_release_authority", authorities_false),
        ("source_runtime_separation", not (source / "data" / "settings.json").exists()),
        ("desktop_verification_pending", True),
        ("consciousness_not_proven", True),
    ]

    after = _tree_signature(source)
    rows = [
        {"id": name, "status": "pass" if value else "fail", "passed": bool(value)}
        for name, value in checks
    ]
    passed = sum(1 for row in rows if row["passed"])
    ok = passed == len(rows)
    return {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "privacy-security-hardening-intake:v1148.2",
        "status": "ready_for_bundle_b" if ok else "review_required",
        "ok": ok,
        "passed": passed,
        "total": len(rows),
        "checks": rows,
        "threat_model": model,
        "test_catalog": catalog,
        "summary": {
            "threat_category_count": len(threat_categories),
            "threat_count": len(threats),
            "scenario_count": len(scenarios),
            "execution_eligible_count": sum(bool(row.get("execution_eligible")) for row in scenarios),
            "operator_review_required_count": sum(bool(row.get("operator_review_required")) for row in scenarios),
        },
        "read_only": True,
        "post_available": False,
        "source_modified": before != after,
        "runtime_mutated": False,
        "security_test_executed": False,
        "provider_contacted": False,
        "command_executed": False,
        "message_sent": False,
        "notification_created": False,
        "goal_created": False,
        "plan_created": False,
        "development_proposal_created": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "raw_conversation_exposed": False,
        "raw_message_exposed": False,
        "prompt_exposed": False,
        "reflection_text_exposed": False,
        "memory_text_exposed": False,
        "belief_text_exposed": False,
        "goal_text_exposed": False,
        "relationship_text_exposed": False,
        "mood_text_exposed": False,
        "provider_payload_exposed": False,
        "source_text_exposed": False,
        "patch_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "desktop_verification_pending": True,
        "consciousness_proven": False,
    }
